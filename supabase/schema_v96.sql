-- schema_v96 (20/10/2026 sera): «La giornata», una mail sola a Dre alle 19.
-- Dre: «metti delle regole anche alle mail che mi arrivano, perché me le manda un po' a caso. A chiusura
-- della giornata voglio UNA mail, alle 19, che mi dica cosa è stato completato, per andare a letto sereno».
-- Le mail di giornata del segnale provvisorio («Sì da servire», «Vuole sentirti», «Da guardare»,
-- «Prenotato/Spostata/Cancellata») non partono piu'; resta solo la scheda prima di una call.
-- Nessuna tabella nuova: una riga in operazioni (scripts/giornata.py, ore 19) e lo storico dei guasti
-- risolti nel giorno dentro snella_numeri «guasti» (dati.risolti), che tiene guasti.py.

insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ora_preferita, ordine, attiva) values
  ('giornata', 'La giornata, alle 19',
   'Una mail sola a Dre a fine giornata: se il sistema ha funzionato (o cosa si e'' rotto e la soluzione), i numeri di oggi, cosa aspetta lui, le call di domani. L''unica mail di giornata insieme alla scheda prima di una call.',
   'python3 scripts/giornata.py', 1440, '19:00', 25, true)
on conflict (chiave) do nothing;
