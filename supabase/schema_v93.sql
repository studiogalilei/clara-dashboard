-- schema_v93 (19/10/2026): il foglio della pipeline.
-- Dre, 19/10: un colpo d'occhio in un foglio Google, otto fasi da sinistra a destra, un po' di gioco
-- (docs/superpowers/specs/2026-10-19-foglio-pipeline-design.md). Nessuna tabella nuova:
--   snella_numeri  chiave «foglio»: lo stato del foglio (dove sta, cosa ci ha scritto il sistema, cosa
--                  ha scritto Dre con la data, le fasi decise a mano, chi e' «In attesa di risposta»,
--                  gli appunti delle call gia' visti). Solo i ceo lo leggono (la RLS di snella_numeri).
--                  chiave «fasi»: la fase di ogni lead, che la scheda dell'app mostra («nel foglio: ...»).
--   gli effetti delle scelte di Dre vanno nelle colonne che ci sono gia': prospects.pipeline_stage, stage,
--   prova_inizio, prova_fine, canone (che va in cassaforte da solo, schema_v67), snella_lead, snella_note.
-- La corrispondenza fra i 12 stati e le 8 fasi sta nel codice (src/snella/stati.json), non nel database.
--
-- Il giro: ogni 10 minuti, nella corsia leggera del direttore. Legge prima le celle di Dre, poi
-- riscrive il resto. Non manda mail.

insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ora_preferita, ordine, attiva) values
  ('foglio', 'Il foglio della pipeline',
   'Aggiorna il foglio «Pipeline Studio Galilei» in 2 Commerciale: legge prima quello che ha scritto Dre (lo salva e non lo riscrive mai), poi le 8 fasi, i numeri della settimana e il MRR. Mette gli appunti delle call di Dre in Chiamate e avvisa se manca il link della call concordata. Nessuna mail.',
   'python3 scripts/foglio.py', 10, null, 23, true)
on conflict (chiave) do nothing;
