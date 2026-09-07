-- ODYN CRM schema v8 (7 set 2026) — la stanza di Clara
--
-- Clara legge ovunque e capisce, ma nella pipeline non scrive mai da sola:
-- mette una PROPOSTA nella sua stanza (cosa vuole fare, su chi, perche') e
-- Dre dice si' o no. Solo sul si' si scrive. Ogni risposta le insegna una
-- regola. Vedi docs/LA-STANZA-DI-CLARA.md.
--
-- E una sola scheda per persona: chi risponde da un'altra mail e' lo stesso
-- prospect, stesso SG-ID; la seconda mail va in email_alt.
--
-- ISTRUZIONI: incollare nell'editor SQL di Supabase e premere Run.

create table if not exists proposte (
  id          bigint generated always as identity primary key,
  at          timestamptz not null default now(),
  tipo        text not null,              -- classifica | scarta | perso | tornato | stessa_persona | richiesta | data | avanza
  prospect_id uuid references prospects(id) on delete cascade,
  titolo      text not null,              -- una riga: cosa vuole fare
  perche      text,                       -- perche' lo propone
  azione      jsonb not null default '{}'::jsonb,  -- cosa scrivere sul si': {"prospects": {...}, "task": {...}}
  stato       text not null default 'aperta',
  risposta    text,                       -- se Dre aggiunge due parole
  risposta_il timestamptz,
  owner       uuid                        -- a chi e' rivolta; null = a tutti
);
alter table proposte drop constraint if exists proposte_stato_check;
alter table proposte add constraint proposte_stato_check
  check (stato in ('aperta', 'si', 'no', 'fatta'));
create index if not exists idx_proposte_aperte on proposte (at) where stato = 'aperta';
create index if not exists idx_proposte_prospect on proposte (prospect_id) where prospect_id is not null;

alter table proposte enable row level security;
drop policy if exists "auth full access proposte" on proposte;
create policy "auth full access proposte" on proposte
  for all to authenticated using (true) with check (true);

-- la seconda mail della stessa persona
alter table prospects add column if not exists email_alt text[];

-- le risposte di Clara nella chat: un tipo in piu' per clara_messaggi
-- (nessun vincolo da cambiare: tipo e' testo libero)

select 'schema v8 applicato' as esito;
