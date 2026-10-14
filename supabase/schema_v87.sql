-- schema_v87 (14/10/2026): il segnale provvisorio.
-- Dre, 14/10: «mi dai un modo piccolo per gestirmi questi che arrivano nel frattempo, mentre
-- continui a costruire quello serio». scripts/segnale_provvisorio.py legge le risposte dei lead
-- e scrive a Dre (solo a lui) quando uno e' caldo o un si' resta senza risposta. E' PROVVISORIO:
-- quando arriva il sistema nuovo si buttano il file, questa tabella e la riga in `operazioni`.
-- (v86 e' gia' preso dal ramo fix/smartlead-pulito: qui v87 per non scontrarsi.)

-- Una riga per segnale mandato: la stessa risposta e la stessa azienda non tornano mai due volte.
create table if not exists segnali_provvisori (
  id              bigint generated always as identity primary key,
  interaction_id  uuid not null unique references interactions(id) on delete cascade,
  prospect_id     uuid not null unique references prospects(id) on delete cascade,
  quando          timestamptz not null default now(),
  tipo            text not null check (tipo in ('caldo', 'si', 'da_guardare')),
  come            text not null default 'segnale'          -- 'segnale' (il giro) o 'prova' (la mail di prova)
);
comment on table segnali_provvisori is 'Il segnale provvisorio (14/10): a chi ha gia'' scritto a Dre. Si butta col sistema nuovo.';
alter table segnali_provvisori enable row level security;
drop policy if exists "segnali provvisori: solo i ceo" on segnali_provvisori;
create policy "segnali provvisori: solo i ceo" on segnali_provvisori for select to authenticated using ((select sono_ceo()));

-- Il giro: dopo sync, prima risposta, bozze e manda (ordine 4), a ogni passaggio del direttore.
-- Nasce spenta: si accende dopo la prova a secco e la mail di prova.
insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ora_preferita, ordine, attiva) values
  ('segnale', 'Il segnale provvisorio',
   'Una mail a Dre (solo a lui) quando un lead e'' caldo o un si'' resta 10 minuti senza risposta. Provvisorio: si butta col sistema nuovo.',
   'python3 scripts/segnale_provvisorio.py', 5, null, 4, false)
on conflict (chiave) do nothing;

notify pgrst, 'reload schema';
