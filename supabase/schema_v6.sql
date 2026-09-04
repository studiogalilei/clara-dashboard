-- ODYN CRM v6 (4 settembre 2026): i progetti.
--
-- Il lavoro di Studio Galilei e' di due tipi che finora stavano mescolati:
-- il RETAINER (ricorrente, mensile, senza scadenza: il canone) e il PROGETTO
-- (una cosa sola, con una scadenza e un valore: il sito, la landing, il setup).
-- Il ricorrente da solo era meta' della verita'.
--
-- Un progetto nasce dal pedaggio quando una carta arriva su Cliente: e' il
-- passaggio di consegne dal commerciale alla delivery, fatto nell'unico
-- istante in cui l'informazione ce l'ha in testa qualcuno.
--
-- Non cancella niente, si puo' rilanciare.

create table if not exists progetti (
  id          bigint generated always as identity primary key,
  at          timestamptz not null default now(),
  prospect_id uuid not null references prospects(id) on delete cascade,
  nome        text not null,              -- cosa gli abbiamo venduto
  natura      text,                       -- sito vetrina, campagna, setup...
  chi_segue   text,                       -- chi ce l'ha in mano
  scadenza    date,
  valore      numeric,                    -- quanto vale, in euro
  stato       text not null default 'da_iniziare',
  note        text,
  owner       uuid references auth.users(id) default null
);

alter table progetti drop constraint if exists progetti_stato_check;
alter table progetti add constraint progetti_stato_check
  check (stato in ('da_iniziare', 'in_corso', 'consegnato'));

alter table progetti enable row level security;
drop policy if exists "auth full access progetti" on progetti;
create policy "auth full access progetti" on progetti
  for all to authenticated using (true) with check (true);

create index if not exists idx_progetti_prospect on progetti (prospect_id);
create index if not exists idx_progetti_scadenza on progetti (scadenza)
  where stato <> 'consegnato';

-- i documenti si agganciano al progetto: il preventivo e' un file, non una
-- cosa che costruiamo noi
alter table vault_file add column if not exists progetto_id bigint
  references progetti(id) on delete set null;
create index if not exists idx_vault_progetto on vault_file (progetto_id)
  where progetto_id is not null;
