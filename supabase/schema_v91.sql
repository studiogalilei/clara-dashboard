-- schema_v91 (17/10/2026): il ponte per entrare nell'app del telefono con un codice.
-- Dre, 17/10: la web app sulla Home dell'iPhone ha una memoria sua, separata da Safari, e il
-- link magico per mail si apre in Safari. Chi e' gia' dentro (computer, Safari) chiede un codice
-- di 6 cifre, e nell'app lo scrive: la funzione supabase/functions/ponte lo cambia in un accesso.
--
-- Due tabelle, e nessuno dal browser le legge o le scrive: RLS accesa e nessuna policy, le tocca
-- solo la funzione con la chiave di servizio.
--   ponti            un codice valido (solo l'impronta), di chi e', fino a quando, se e' gia' usato
--   ponti_tentativi  i tentativi, per fermare chi prova codici a caso (oltre 20 sbagliati in 10 minuti)

create table if not exists ponti (
  codice_hash  text primary key,
  user_id      uuid not null references auth.users(id) on delete cascade,
  email        text not null,
  creato_il    timestamptz not null default now(),
  scade_il     timestamptz not null,
  usato_il     timestamptz
);
create index if not exists ponti_user on ponti (user_id);
alter table ponti enable row level security;

create table if not exists ponti_tentativi (
  id        bigserial primary key,
  il        timestamptz not null default now(),
  riuscito  boolean not null
);
create index if not exists ponti_tentativi_il on ponti_tentativi (il) where not riuscito;
alter table ponti_tentativi enable row level security;

-- niente si accumula: i codici e i tentativi di piu' di un giorno se ne vanno ogni notte
do $$
begin
  if exists (select 1 from pg_extension where extname = 'pg_cron') then
    perform cron.unschedule(jobid) from cron.job where jobname = 'ponti_pulizia';
    perform cron.schedule('ponti_pulizia', '17 3 * * *',
      $q$delete from ponti where creato_il < now() - interval '1 day';
         delete from ponti_tentativi where il < now() - interval '1 day'$q$);
  end if;
end $$;
