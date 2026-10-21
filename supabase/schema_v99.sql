-- schema_v99 (21/10/2026 pomeriggio): la strada veloce.
-- Dre: «TUTTE le cose le voglio in realtime». Quando un lead risponde, Smartlead bussa e parte
-- risposta.yml (scripts/risposta.py): un lead solo, subito, sotto i 3 minuti. Non e' un'operazione
-- del direttore (parte da GitHub, come il backup), ma le sue corse si scrivono in `corse` perche' la
-- scheda Clara e il semaforo le vedano: serve la riga in operazioni (corse.operazione la referenzia).
-- Nessuna tabella nuova. La misura «risposta entrata dopo N minuti» sta in snella_numeri
-- «risposte_veloci» (la legge clara_foglio per il diario).

insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ordine, attiva) values
  ('risposta', 'La strada veloce',
   'Un lead che risponde entra subito: filo da Smartlead, lettore AI, notifica se tocca a Dre, scheda, foglio, e il lampo se e'' un si'' senza analisi. Parte da GitHub (risposta.yml) quando Smartlead bussa; non ha cadenza.',
   null, 525600, 26, true)
on conflict (chiave) do nothing;
