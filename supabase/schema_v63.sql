-- LA PRIMA RISPOSTA AUTOMATICA (Dre, 29/9/2026)
--
-- «La prima risposta parte da sola, con l'analisi e la presentazione.»
-- scripts/prima_risposta.py approva solo le prime risposte semplici (positivo
-- o tiepido, analisi pronta, seconda testa COERENTE, Revisore OK, lun-ven 9-17,
-- max 5 per giro e 15 al giorno); l'invio resta a manda.py.
--
-- NASCE SPENTA. Si accende dalla sala di controllo insieme a «manda», la prima
-- volta guardando partire una mail insieme (regola del 28/9). Lo script non
-- approva niente se uno dei due interruttori e' spento. Ordine 2: gira prima
-- di manda (3), cosi' l'approvata parte nello stesso giro.
--
-- PARTE IN OMBRA (--ombra): decide e scrive cosa avrebbe fatto, non approva.
-- Si toglie --ombra dopo ~50 casi confrontati con quello che Dre ha mandato.

insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ora_preferita, ordine, attiva) values
  ('prima_risposta', 'La prima risposta parte da sola',
   'Approva da sola le prime risposte semplici (positivi e tiepidi con l''analisi pronta), dopo il Revisore. Manda le spedisce con analisi e presentazione. I no, i rinvii e i casi strani restano a Dre.',
   'python3 scripts/prima_risposta.py', 5, null, 2, false)
on conflict (chiave) do update set nome = excluded.nome, cosa = excluded.cosa, comando = excluded.comando,
  cadenza_minuti = excluded.cadenza_minuti, ordine = excluded.ordine;

select 'schema v63 applicato: la prima risposta automatica, spenta' as esito;
