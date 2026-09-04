-- ODYN CRM v5b (4 settembre 2026): la scheda del cliente contiene TUTTO.
-- Manca un solo aggancio: una task deve poter appartenere a un cliente, se
-- no la sua scheda non puo' mostrare cosa c'e' da fare per lui.
-- Non cancella niente, si puo' rilanciare.

alter table task add column if not exists prospect_id uuid
  references prospects(id) on delete set null;

create index if not exists idx_task_prospect on task (prospect_id)
  where prospect_id is not null;
