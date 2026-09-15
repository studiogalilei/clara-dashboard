-- ODYN CRM schema v32 (15 set 2026) — i dati dello Studio, e il ricorrente in un posto solo
--
-- I dati che la controparte legge sul documento firmato (ragione sociale, P.IVA,
-- sede, IBAN, aliquota, termini). Si scrivono in Preventivi, stanno qui.
insert into istruzioni (chiave, titolo, testo) values
  ('studio', 'Dati dello Studio', '{"iva":22,"giorni":15,"preavviso":30}')
  on conflict (chiave) do nothing;

-- il canone del cliente e' quello del preventivo che ha accettato: si allinea
-- una volta sola, poi ci pensa il widget Preventivi a ogni «Ha accettato»
update prospects p set canone = q.mensile
  from preventivi q
  where q.prospect_id = p.id and q.stato = 'accettato' and q.mensile is not null
    and (p.canone is null or p.canone = 0);

select 'schema v32 applicato: dati dello Studio e canone dai preventivi' as esito;
