-- CLARA MANDA (24/9/2026)
--
-- Dre: «fai che Clara invia i messaggi: io clicco Approva e lei invia, avendo
-- a disposizione tutto il necessario per farlo bene». Fino a oggi Clara
-- preparava e Dre copiava e mandava da Smartlead. Da oggi la bozza approvata
-- passa in stato «approvata», l'operazione `manda` (scripts/manda.py) la
-- spedisce dal thread giusto di Smartlead (stessa casella, stessa
-- conversazione), e la proposta diventa «fatta» con l'ora dell'invio.
-- «in_invio» e' il lucchetto: una bozza non parte due volte.
alter table proposte drop constraint if exists proposte_stato_check;
alter table proposte add constraint proposte_stato_check
  check (stato in ('aperta', 'approvata', 'in_invio', 'si', 'no', 'fatta'));
create index if not exists idx_proposte_approvate on proposte (at) where stato in ('approvata', 'in_invio');

insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ordine) values
  ('manda', 'Clara manda le risposte approvate', 'Le bozze che Dre ha approvato partono da Smartlead, nel thread della persona, con la firma della casella.', 'python3 scripts/manda.py', 5, 3)
on conflict (chiave) do update set cosa = excluded.cosa, comando = excluded.comando, cadenza_minuti = excluded.cadenza_minuti;
