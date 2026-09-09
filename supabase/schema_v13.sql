-- ODYN CRM schema v13 (9 set 2026) — preventivi e pagamenti, e le tappe dei progetti
--
-- Dre (9/9): «Tutti» come il foglio di Giacomo, con lo stato selezionabile
-- (Prospect / Preventivo inviato / Cliente) e i pagamenti tracciati a mano
-- per ogni preventivo; una sezione «Tutti i preventivi» dal primo all'ultimo.
-- E la Roadmap dei progetti con i checkpoint di Giacomo. Tutto appeso all'SG-ID.

-- 1) i preventivi: uno per offerta, con il pagamento sopra
create table if not exists preventivi (
  id           bigint generated always as identity primary key,
  prospect_id  uuid not null references prospects(id) on delete cascade,
  progetto_id  bigint references progetti(id) on delete set null,
  titolo       text,                              -- «Google Ads trial 2 mesi»
  importo      numeric,                           -- euro, iva esclusa
  inviato_il   date not null default current_date,
  stato        text not null default 'inviato',   -- inviato | accettato | rifiutato
  pagato_il    date,                              -- lo spunta Giacomo quando arriva
  pagamento_atteso_il date,
  note         text,
  owner        uuid references auth.users(id) default null,
  creato_il    timestamptz not null default now()
);
alter table preventivi drop constraint if exists preventivi_stato_check;
alter table preventivi add constraint preventivi_stato_check
  check (stato in ('inviato', 'accettato', 'rifiutato'));
create index if not exists idx_preventivi_prospect on preventivi (prospect_id);
create index if not exists idx_preventivi_inviato on preventivi (inviato_il);
alter table preventivi enable row level security;
drop policy if exists "auth full access preventivi" on preventivi;
create policy "auth full access preventivi" on preventivi
  for all to authenticated using (true) with check (true);

-- 2) le tappe (checkpoint) dei progetti, per la Roadmap
create table if not exists tappe (
  id           bigint generated always as identity primary key,
  progetto_id  bigint not null references progetti(id) on delete cascade,
  titolo       text not null,                     -- «Accessi ricevuti», «Prima campagna viva»
  data         date not null,
  fatta        boolean not null default false,
  fatta_il     timestamptz,
  creato_il    timestamptz not null default now()
);
create index if not exists idx_tappe_progetto on tappe (progetto_id);
alter table tappe enable row level security;
drop policy if exists "auth full access tappe" on tappe;
create policy "auth full access tappe" on tappe
  for all to authenticated using (true) with check (true);

select 'schema v13 applicato: preventivi e tappe' as esito;
