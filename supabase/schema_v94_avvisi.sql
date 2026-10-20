-- GLI AVVISI DI GUASTO (20/10/2026, «io più il sistema»).
-- L'operazione «avvisi» (scripts/avvisi.py) faceva solo le notifiche delle task; ora suona anche
-- i guasti del semaforo della scheda «Clara» del foglio (una volta, poi ogni 2 ore, poi «Risolto»).
-- Ogni 10 minuti, come il foglio. Lo stato degli avvisi sta in snella_numeri, chiave «avvisi».
update operazioni
   set cadenza_minuti = 10,
       nome = 'Le notifiche: task e guasti',
       cosa = 'Una task nuova arriva sul telefono di chi la deve fare. E un guasto che costa lead (un sì fermo, l''invio fermo, crediti finiti, il foglio fermo) arriva sul telefono di Dre: una volta, poi ogni 2 ore, poi «Risolto». Di notte aspetta le 7:30.'
 where chiave = 'avvisi';
