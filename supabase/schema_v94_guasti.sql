-- GLI AVVISI DI GUASTO (20/10/2026, «io più il sistema»).
-- L'operazione «guasti» (scripts/guasti.py) suona sul telefono di Dre i guasti del semaforo della
-- scheda «Clara» del foglio: una volta, poi ogni 2 ore, poi «Risolto»; di notte aspetta le 7:30.
-- Ogni 10 minuti, come il foglio. Lo stato sta in snella_numeri, chiave «guasti».
-- «avvisi» resta com'era: le notifiche delle task fra colleghi.
update operazioni
   set cadenza_minuti = 5,
       nome = 'Le notifiche a chi deve fare',
       cosa = 'Una task nuova arriva sul telefono di chi la deve fare, con la scadenza.'
 where chiave = 'avvisi';

insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ora_preferita, ordine, attiva) values
  ('guasti', 'Gli avvisi di guasto',
   'Un guasto che costa lead (un sì fermo, l''invio fermo, crediti finiti, il foglio fermo, i guasti del segnale) arriva sul telefono di Dre: una volta, poi ogni 2 ore, poi «Risolto». Di notte aspetta le 7:30.',
   'python3 scripts/guasti.py', 10, null, 4, true)
on conflict (chiave) do nothing;
