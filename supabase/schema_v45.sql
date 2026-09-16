-- LE AZIONI DI CLARA (16/9/2026)
--
-- Dre: «quando faccio una cosa, tipo inviare un preventivo, lei si mette in
-- automatico un promemoria di tot giorni e controlla se sono arrivati i
-- soldi; se passa una settimana e non sono arrivati me lo ricorda. Vorrei
-- piu' azioni: pensa alle cose che spesso si dimenticano».
--
-- Ogni azione e' una regola scritta qui: si accende, si spegne, si cambiano
-- i giorni. Il codice che la esegue sta in scripts/azioni.py. La regola sta
-- nel database e non nel codice per la stessa ragione di sempre: chi decide
-- deve poterla cambiare senza chiamare nessuno.
create table if not exists azioni (
  chiave text primary key,
  nome text not null,
  cosa text not null,               -- cosa fa, detto come lo direbbe una persona
  giorni int not null default 7,    -- dopo quanto guarda
  attiva boolean not null default true,
  ordine int not null default 100,
  ultima_corsa timestamptz,
  ultimo_esito text
);

alter table azioni enable row level security;
drop policy if exists "le azioni: le vedono tutti, le cambia il ceo" on azioni;
create policy "le azioni: le vedono tutti, le cambia il ceo" on azioni
  for all to authenticated using (true) with check (sono_ceo());

-- il promemoria che nasce da un'azione: si riconosce, e non si ripete
alter table proposte add column if not exists ref text;
create unique index if not exists proposte_ref_unica on proposte (ref) where ref is not null;
