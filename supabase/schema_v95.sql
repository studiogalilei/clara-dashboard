-- schema_v95 (20/10/2026): la Clara intelligente, il lettore delle risposte.
-- Il lettore del mattone 5 di Clara nuova portato nel vecchio (scripts/lettore.py): il senso di una
-- risposta lo decide l'AI (Sonnet), le liste di parole restano la rete dei casi gravi. Nessuna tabella
-- nuova:
--   operazioni     chiave «lettore»: l'interruttore (attiva). Spento, il sync legge solo con le liste.
--                  Il comando scrive il conto del giorno nella scheda (spesa, ricadute, disaccordi).
--   snella_numeri  chiave «lettore»: dati.modo «ombra» (il lettore scrive accanto, in enriched.lettore,
--                  la classe resta delle liste) o «acceso» (la classe la decide il lettore).
--   uso_modelli    scopo «lettore»: ogni chiamata; il tetto di spesa del giorno si conta da qui.

insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ora_preferita, ordine, attiva) values
  ('lettore', 'Il lettore delle risposte',
   'Interruttore della Clara intelligente: quando e'' acceso il sync legge ogni risposta nuova col modello AI (Sonnet) invece che con le liste di parole. Questo giro scrive solo il conto del giorno: quanto ha speso, quante risposte ha letto, quante volte e'' ricaduto sulle liste. Nessuna mail.',
   'python3 scripts/lettore.py --conto', 60, null, 24, true)
on conflict (chiave) do nothing;

insert into snella_numeri (chiave, dati, aggiornato_il) values
  ('lettore', '{"modo": "ombra", "tetto_giorno": 2.0}'::jsonb, now())
on conflict (chiave) do nothing;
