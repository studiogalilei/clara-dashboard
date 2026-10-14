-- schema_v88 (14/10/2026): il segnale provvisorio, una volta per lead E PER TIPO.
-- Il collaudatore, 14/10: con `prospect_id unique` un lead gia' segnalato come si' non poteva
-- piu' arrivare come caldo («mi chiami al 333...»): Dre non l'avrebbe saputo. Adesso il blocco e'
-- per azienda e tipo: un si' e poi un caldo fanno due mail, due caldi una sola.
-- `oggetto`: quando Gmail non risponde (timeout) la mail forse e' partita; il segnale resta
-- «incerto» con l'oggetto, e il giro dopo lo cerca nella posta inviata di Dre prima di rimandarlo.
-- Provvisorio come la v87: si butta col sistema nuovo.

alter table segnali_provvisori drop constraint if exists segnali_provvisori_prospect_id_key;
create unique index if not exists segnali_provvisori_prospect_tipo on segnali_provvisori (prospect_id, tipo);
alter table segnali_provvisori add column if not exists oggetto text;
comment on column segnali_provvisori.come is '''segnale'' (il giro), ''prova'' (la mail di prova), ''incerto'' (Gmail non ha risposto: il giro dopo guarda nella posta inviata)';

notify pgrst, 'reload schema';
