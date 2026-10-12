-- schema_v84 (12/10/2026): il contatore della spesa dei modelli, nel database.
-- Dre, 12/10 notte: «ho messo 60 dollari, facciamolo bastare per il mese», e prima ancora
-- «vedi in cosa li spendiamo». Il contatore stava in un file che muore col runner del
-- direttore: il costo di un giorno non si poteva dire. Stessa tabella del ramo senso-v2 (v81).
create table if not exists uso_modelli (
  id         bigint generated always as identity primary key,
  il         timestamptz not null default now(),
  script     text,
  scopo      text,
  modello    text,
  token_in   int not null default 0,
  token_out  int not null default 0
);
create index if not exists idx_uso_modelli_il on uso_modelli (il desc);
comment on table uso_modelli is 'Ogni chiamata a un modello, coi token: il costo si misura invece di temerlo (12/10).';
alter table uso_modelli enable row level security;
drop policy if exists "uso modelli: solo i ceo" on uso_modelli;
create policy "uso modelli: solo i ceo" on uso_modelli for select to authenticated using ((select sono_ceo()));
notify pgrst, 'reload schema';
