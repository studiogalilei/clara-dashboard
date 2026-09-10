-- ODYN CRM schema v18 (10 set 2026) — il blocco Pagamenti nel foglio
-- Per dire, sulla riga del cliente: come paga (SEPA, carta, bonifico),
-- quando e' il prossimo addebito e quando finisce (la prova finisce da sola).
alter table incassi add column if not exists metodo      text;          -- sepa | carta | bonifico | altro
alter table incassi add column if not exists prossimo_il timestamptz;   -- prossimo addebito (abbonamenti)
alter table incassi add column if not exists fine_il     timestamptz;   -- quando finisce o e' finito
select 'schema v18 applicato: pagamenti nel foglio' as esito;
