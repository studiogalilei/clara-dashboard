-- ODYN CRM schema v17 (10 set 2026) — gli incassi da Stripe
--
-- Dre, 10/9: «dopo connettiamo Stripe». Clara legge Stripe ogni ora con una
-- chiave di sola lettura (scripts/stripe_sync.py) e mette qui addebiti,
-- fatture pagate e abbonamenti, collegati all'azienda quando la mail torna.
-- Se un incasso combacia con un preventivo accettato e non ancora pagato,
-- lo segna pagato da sola; se non e' sicura, lo chiede nella stanza.
--
-- I soldi li vedono solo Dre e Giacomo (ruolo ceo): la regola sta qui nel
-- database, non solo nell'interfaccia.

create table if not exists incassi (
  id             text primary key,                 -- l'id di Stripe: ch_, in_, sub_
  genere         text not null,                    -- addebito | fattura | abbonamento
  importo        numeric not null default 0,       -- euro (o valuta), gia' diviso per 100
  valuta         text not null default 'eur',
  stato          text,                             -- succeeded, paid, active, canceled, ...
  quando         timestamptz,                      -- creato su Stripe
  ricorrenza     text,                             -- month | year, per gli abbonamenti
  cliente_nome   text,
  cliente_email  text,
  stripe_cliente text,                             -- cus_...
  descrizione    text,
  prospect_id    uuid references prospects(id) on delete set null,
  preventivo_id  bigint references preventivi(id) on delete set null,
  letto_il       timestamptz not null default now()
);
create index if not exists incassi_quando on incassi (quando desc);
create index if not exists incassi_prospect on incassi (prospect_id);

create or replace function sono_ceo() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from profili where id = auth.uid() and ruolo = 'ceo');
$$;

alter table incassi enable row level security;
drop policy if exists "i soldi li vedono i ceo" on incassi;
create policy "i soldi li vedono i ceo" on incassi
  for select to authenticated using (sono_ceo());
-- scrive solo il runner (service role, che salta le policy)

select 'schema v17 applicato: incassi da Stripe' as esito;
