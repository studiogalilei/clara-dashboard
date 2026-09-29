-- I SEGUITI AUTOMATICI (Dre, 29/9/2026: strada A)
--
-- I follow-up col template (FOLLOW UP 1, MINI FOLLOW UP, RIPRESA, RINVIO SCADUTO)
-- li scrive il codice, parola per parola (scripts/seguiti.py). Questa operazione
-- li approva da soli con la stessa porta della prima risposta: il codice riscrive
-- il testo e deve venire identico, e basta una traccia di contatto fuori da
-- Smartlead negli ultimi 60 giorni (Gmail, call, transcript, note, calendario,
-- task, «Fuori binario», presa in carico) perche' resti a Dre.
--
-- PARTE IN OMBRA (--ombra): decide e scrive cosa avrebbe fatto, non approva.

insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ora_preferita, ordine, attiva) values
  ('seguiti', 'I follow-up partono da soli',
   'Approva da soli i follow-up scritti dal codice col template di Dre, se nessuno sta già sentendo quell''azienda fuori da Smartlead. Per ora in ombra: decide e scrive, non approva.',
   'python3 scripts/prima_risposta.py --seguiti --ombra', 15, null, 2, true)
on conflict (chiave) do update set nome = excluded.nome, cosa = excluded.cosa, comando = excluded.comando,
  cadenza_minuti = excluded.cadenza_minuti, ordine = excluded.ordine;

select 'schema v64 applicato: i seguiti automatici, in ombra' as esito;
