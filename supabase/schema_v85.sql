-- schema_v85 (13/10/2026): la memoria delle letture nel database.
-- La cache delle letture stava in ~/.odyn-letture.json: sul Mac regge, nel cloud muore col
-- runner, e ogni 15 minuti Clara rileggeva (e ripagava) le stesse risposte. Misurato la notte
-- del 13/10 col contatore: 26 chiamate in due ore per una bozza sola. Una risposta letta
-- una volta resta letta: la chiave e' l'impronta di testo, domande e modello.
create table if not exists memoria_letture (
  chiave  text primary key,
  valore  jsonb not null,
  il      timestamptz not null default now()
);
comment on table memoria_letture is 'Le letture del modello gia'' pagate: la stessa risposta non si rilegge (13/10).';
alter table memoria_letture enable row level security;
notify pgrst, 'reload schema';
