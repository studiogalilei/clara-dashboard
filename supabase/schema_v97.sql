-- schema_v97 (21/10/2026 notte): le strade. Dre: «quando il sistema e' indeciso, mi da' 2 o 3 strade
-- e io scelgo, e lui procede. Cosi' lo alleno anche».
-- Nessuna tabella nuova: una riga in operazioni (scripts/strade.py, ogni 15 minuti, corsia leggera).
-- Le strade vivono in proposte.azione.strade (lista, max 3) con strade_il; la scelta di Dre in
-- proposte.azione.scelta (caso del lettore, intento, le strade proposte, quale ha scelto, quando);
-- lo specchio leggibile delle ultime 30 scelte in snella_numeri «scelte_di_dre», il conto e il tetto
-- di spesa (3 $ al giorno, uso_modelli scopo «strade») in snella_numeri «strade».
-- (La riga e' stata inserita anche via REST la notte del 21/10: qui resta per lo storico e per chi
-- rifa' il database da zero.)

insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ora_preferita, ordine, attiva) values
  ('strade', 'Le strade, quando il sistema e'' indeciso',
   'Per ogni risposta ferma «Da guardare tu» e per chi e'' in conversazione senza una nostra risposta da piu'' di un giorno, il modello propone a Dre 2 o 3 strade (manda con la bozza, ricontatta a una data, chiudi, chiama, niente). Dre ne tocca una nella scheda e il sistema la esegue; la scelta insegna al sistema. Tetto di spesa 3 $ al giorno.',
   'python3 scripts/strade.py', 15, null, 3, true)
on conflict (chiave) do nothing;

comment on table snella_numeri is 'La versione snella (15/10): i numeri gia'' fatti dagli script (oggi, call, campagne, lettore, guasti, strade, scelte_di_dre).';

select 'schema v97 applicato: le strade' as esito;
