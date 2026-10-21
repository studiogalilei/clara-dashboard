-- schema_v100 (notte del 22/10/2026): il fumo del mattino.
-- Dre: «arriva alla radice». Le prove passavano col finto e cadevano col vero (la Master Inbox
-- chiesta con limit 50 il 21/10, giornata.py partita prima del suo file il 20/10, i crediti OpenAI
-- finiti il 16/10 visti da nessuno). Ogni mattina alle 7:45 scripts/fumo.py chiama dal vivo, in
-- sola lettura, ogni servizio esterno con i parametri veri e guarda che ogni operazione accesa abbia
-- il suo file; chi cade va nel semaforo della scheda Clara prima che Dre si svegli.
-- Nessuna tabella nuova: i guasti stanno in snella_numeri «guasti_segnale» (stanza.guasto).
-- La riga si accende DOPO che il file e' su main (la radice del 20/10).

insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ora_preferita, ordine, attiva) values
  ('fumo', 'Il fumo del mattino',
   'Alle 7:45 prova dal vivo, in sola lettura, Supabase, Smartlead (campagne, export, un filo, Master Inbox), Gmail, Calendar e Sheets di Dre, Anthropic, OpenAI e SearchAPI, e che ogni operazione accesa abbia il suo file. Chi cade va nel semaforo prima che Dre si svegli.',
   'python3 scripts/fumo.py', 1440, '07:45', 27, true)
on conflict (chiave) do nothing;
