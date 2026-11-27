-- v127 (27/11, Dre: «colleghiamo i post automatici, andiamo»). Ogni persona collega il suo profilo LinkedIn dal Desk
-- (app «Desk Studio Galilei», prodotti Share on LinkedIn + OpenID Connect). Il permesso dura due mesi: poi si ricollega.
-- La funzione linkedin-pubblica gira ogni 5 minuti e pubblica i post «programmato» arrivati alla loro ora.
create table if not exists linkedin_collegamento (
  utente uuid primary key references auth.users (id) on delete cascade,
  sub text not null,                 -- l'id della persona su LinkedIn (urn:li:person:<sub>)
  nome text,
  token text not null,               -- il permesso: lo legge solo la funzione (nessuna regola per il browser)
  scade_il timestamptz not null,
  collegato_il timestamptz not null default now()
);
alter table linkedin_collegamento enable row level security;

create table if not exists linkedin_stati (   -- il «biglietto» del giro di collegamento, vale 15 minuti
  stato text primary key,
  utente uuid not null references auth.users (id) on delete cascade,
  creato_il timestamptz not null default now()
);
alter table linkedin_stati enable row level security;

-- il Desk chiede solo «sono collegato? fino a quando?», mai il permesso
create or replace function linkedin_collegato()
returns table (nome text, scade_il timestamptz)
language sql security definer set search_path = public stable as $$
  select nome, scade_il from linkedin_collegamento where utente = auth.uid()
$$;
grant execute on function linkedin_collegato() to authenticated;

-- ogni 5 minuti: pubblica i post arrivati alla loro ora (il segreto della chiamata sta nel vault)
create extension if not exists pg_net;
select cron.unschedule('linkedin_pubblica') where exists (select 1 from cron.job where jobname = 'linkedin_pubblica');
select cron.schedule('linkedin_pubblica', '*/5 * * * *', $$
  select net.http_post(
    url := 'https://tqssfcuzezlczfceqsmk.supabase.co/functions/v1/linkedin-pubblica',
    headers := jsonb_build_object('Content-Type', 'application/json',
      'x-segreto', (select decrypted_secret from vault.decrypted_secrets where name = 'linkedin_pubblica')),
    body := '{}'::jsonb, timeout_milliseconds := 60000)
$$);
