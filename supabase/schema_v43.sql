-- CLARA PREPARA LE CALL (16/9/2026)
--
-- Dre: «Clara deve essere come una che cerca di rendersi il piu' utile
-- possibile: se abbiamo una call, in modo proattivo fa ricerche sul cliente,
-- prepara cose che possono servire e le mette li'».
--
-- La preparazione vive sulla riga dell'agenda, non in una tabella nuova:
-- e' una proprieta' di quell'appuntamento e muore con lui.
alter table agenda add column if not exists preparazione text;
alter table agenda add column if not exists preparata_il timestamptz;
comment on column agenda.preparazione is 'Il punto della situazione che Clara scrive prima della call: chi sono, a che punto siamo, cosa chiedere.';
