-- schema_v101 (notte del 22/10/2026): si spegne la roba accesa che non fa niente.
-- Dre: «togli stronzate, senza aumentare la complessità». Misurato sulle corse degli ultimi 30 giorni:
-- queste operazioni giravano (fino a ogni 5 minuti) senza un effetto, o scrivevano in una chat che
-- nessuno legge giudizi che il semaforo della scheda Clara da' gia' con le sue regole.
-- Si spengono e basta: i file restano, si riaccendono da qui se serve. Nessun dato si cancella.

update operazioni set attiva = false, ultimo_dettaglio = 'Spenta il 22/10: 3.468 giri in 30 giorni, l''ultima call letta il 30/9 (Granola spento)' where chiave = 'transcript';
update operazioni set attiva = false, ultimo_dettaglio = 'Spenta il 22/10: 3.461 giri in 30 giorni, l''ultimo appunto messo il 22/9' where chiave = 'appunti';
update operazioni set attiva = false, ultimo_dettaglio = 'Spenta il 22/10: 620 giri in 30 giorni, l''ultimo promemoria il 1/10' where chiave = 'azioni';
-- «posta» resta accesa: sembra ferma («scritte 0»), ma il 19/10 ha messo nel sistema mail scritte a mano da Gmail
update operazioni set attiva = false, ultimo_dettaglio = 'Spenta il 22/10: contava le proposte aperte e basta (le chiude il Revisore)' where chiave = 'posta_ordine';
update operazioni set attiva = false, ultimo_dettaglio = 'Spenta il 22/10: rifaceva il «sì senza analisi» del semaforo con regole sue, in una chat che nessuno legge' where chiave = 'battito';
update operazioni set attiva = false, ultimo_dettaglio = 'Spenta il 22/10: controlli in una chat che nessuno legge; i guasti che costano lead li dice il semaforo' where chiave = 'salute';
