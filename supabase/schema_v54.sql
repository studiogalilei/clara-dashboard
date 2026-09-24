-- IL FOLLOW-UP COME FLUSSO (24/9/2026): ogni mattina Clara mette in Posta i
-- FOLLOW UP 1 dovuti (analisi ricevuta da 5+ giorni, silenzio), massimo 10.
insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ora_preferita, ordine, attiva) values
  ('followup', 'I follow-up dopo l''analisi', 'Chi ha ricevuto l''analisi da 5 giorni e non ha più scritto: FOLLOW UP 1 in Posta, parola per parola, da approvare uno alla volta.', 'python3 scripts/followup.py', 1440, '08:30', 3, false)
on conflict (chiave) do update set cosa = excluded.cosa, comando = excluded.comando, cadenza_minuti = excluded.cadenza_minuti, ora_preferita = excluded.ora_preferita;
