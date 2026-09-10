-- ODYN CRM schema v16 (10 set 2026) — Clara si sveglia da sola, in cloud
--
-- Due cose, entrambe per non dipendere piu' ne' dal Mac di Dre ne' dal solo
-- cron di GitHub (che ritarda e costa minuti).
--
-- 1) L'orologio di riserva (era v10, mai applicato): pg_cron ogni ora chiede
--    a GitHub di far partire il direttore, sfasato di mezz'ora rispetto al
--    cron di GitHub (7 * * * *). Le risposte di Smartlead non aspettano
--    nessuno dei due: arrivano via webhook (functions/smartlead-webhook).
--    Il token GitHub sta nel Vault, nome github_direttore: lo mette Claude
--    con un comando a parte, qui non c'e'.
--
-- 2) Clara risponde in chat dal cloud: a ogni riga nuova in clara_messaggi
--    con tipo 'dre', un trigger chiama la funzione clara-risponde. Prima
--    lo faceva scripts/clara_ascolta.py sul Mac (spento il 10/9).

create extension if not exists pg_cron;
create extension if not exists pg_net;

create or replace function chiama_direttore(forza text default '')
returns void language plpgsql security definer set search_path = public as $$
declare
  tok text;
begin
  select decrypted_secret into tok from vault.decrypted_secrets where name = 'github_direttore';
  if tok is null then
    raise notice 'manca il token github_direttore nel Vault';
    return;
  end if;
  perform net.http_post(
    url := 'https://api.github.com/repos/studiogalilei/clara-dashboard/actions/workflows/direttore.yml/dispatches',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || tok,
      'Accept', 'application/vnd.github+json',
      'User-Agent', 'clara-dashboard',
      'Content-Type', 'application/json'),
    body := jsonb_build_object('ref', 'main', 'inputs', jsonb_build_object('forza', forza))
  );
end $$;

select cron.unschedule(jobid) from cron.job where jobname in ('direttore', 'backup');
select cron.schedule('direttore', '37 * * * *', $$select chiama_direttore()$$);

-- 2) la chat: ogni messaggio di Dre sveglia clara-risponde
create or replace function sveglia_clara()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.tipo = 'dre' then
    perform net.http_post(
      url := 'https://tqssfcuzezlczfceqsmk.supabase.co/functions/v1/clara-risponde',
      headers := jsonb_build_object('Content-Type', 'application/json'),
      body := jsonb_build_object('type', 'INSERT', 'table', 'clara_messaggi', 'record', to_jsonb(new))
    );
  end if;
  return new;
end $$;

drop trigger if exists clara_messaggi_sveglia on clara_messaggi;
create trigger clara_messaggi_sveglia after insert on clara_messaggi
  for each row execute function sveglia_clara();

select 'schema v16 applicato: Clara si sveglia da sola' as esito;
