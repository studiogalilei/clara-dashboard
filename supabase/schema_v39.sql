-- COSA ABBIAMO IMPARATO (15/9/2026)
--
-- Dre: lo Studio vale quanto quello che impara, ma finora quello che si
-- impara su un progetto resta nella testa di chi l'ha fatto. Una riga sola,
-- chiesta nell'unico momento in cui uno ce l'ha in mente: quando segna il
-- progetto consegnato. Niente campo obbligatorio, niente form: si scrive o
-- si salta.
alter table progetti add column if not exists imparato text;
comment on column progetti.imparato is 'Cosa abbiamo imparato, scritto alla consegna: serve a contare i problemi che tornano, per settore.';
