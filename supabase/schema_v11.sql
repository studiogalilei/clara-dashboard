-- ODYN CRM schema v11 (8 set 2026) — il foglio dei progetti di Giacomo
--
-- Dre (8/9): «un excel con selettore, serve per seguire i progetti in corso».
-- E' il foglio "Delivery" di Giacomo portato dentro la Dashboard: una riga
-- per progetto, con il selettore Trial / Retainer / onboarding, la data di
-- inizio e il nome del cliente scritto libero (non tutti i clienti sono
-- prospect del CRM: Dän Ink, GR box…). Se il prospect c'e', si aggancia.

alter table progetti add column if not exists tipo text;              -- trial | retainer | onboarding
alter table progetti add column if not exists data_inizio date;
alter table progetti add column if not exists cliente text;           -- il nome scritto a mano, quando non e' un prospect
alter table progetti alter column prospect_id drop not null;

alter table progetti drop constraint if exists progetti_tipo_check;
alter table progetti add constraint progetti_tipo_check
  check (tipo is null or tipo in ('trial', 'retainer', 'onboarding'));

comment on column progetti.tipo is 'trial | retainer | onboarding: il selettore del foglio di Giacomo';

select 'schema v11 applicato: il foglio dei progetti' as esito;
