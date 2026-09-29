-- I FOLLOW-UP IN ARRIVO, GIORNO PER GIORNO (Dre, 29/9/2026)
--
-- «Per i follow-up ci deve essere una sezione apribile dove vedo in ordine,
-- giorno dopo giorno, quelli in arrivo, e un sistema in leverage per gestirli.»
--
-- Le date le calcola UNA sola regola, quella di scripts/followup.py (la stessa
-- che mette in coda): lo script le scrive qui, lo schermo le legge. Nessuna
-- seconda copia della regola nel Workspace, nessun numero diverso per la stessa
-- domanda. Una riga per azienda: il prossimo follow-up che le spetta.

create table if not exists seguiti_calendario (
  prospect_id   uuid primary key references prospects(id) on delete cascade,
  gruppo        text not null,          -- FOLLOW UP 1, MINI FOLLOW UP, RINVIO SCADUTO
  il            date not null,          -- quando tocca (nel passato = dovuto)
  perche        text,                   -- «analisi del 24/9, nessuna risposta»
  aggiornato_il timestamptz not null default now()
);

create index if not exists idx_seguiti_calendario_il on seguiti_calendario (il);

alter table seguiti_calendario enable row level security;

-- vede la riga chi vede l'azienda: la regola resta quella di prospects
drop policy if exists seguiti_calendario_leggi on seguiti_calendario;
create policy seguiti_calendario_leggi on seguiti_calendario for select to authenticated
  using (exists (select 1 from prospects p where p.id = seguiti_calendario.prospect_id));

select 'schema v65 applicato: il calendario dei follow-up' as esito;

-- il ricalcolo ogni ora (applicato il 29/9 dalla sala di controllo)
insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ora_preferita, ordine, attiva) values
  ('calendario_seguiti', 'Il calendario dei follow-up',
   'Chi riceve un follow-up nei prossimi 21 giorni e quando, con la stessa regola di followup.py. Lo legge la sezione «Follow-up in arrivo» della Posta.',
   'python3 scripts/followup.py --calendario', 60, null, 4, true)
on conflict (chiave) do nothing;
