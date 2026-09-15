-- v34 (15/9): la coda di Oggi non vive piu' nel browser.
-- «Da rispondere / Follow-up / Ricontatti / Rientri» erano spuntati in
-- localStorage: spuntavi dal telefono la mattina e sul Mac erano ancora da
-- fare (QA Dre, 15/9). Una verita' sola, come tutto il resto.

create table if not exists coda_fatte (
  owner uuid not null default uid_eff(),
  chiave text not null,
  giorno date not null default (now() at time zone 'Europe/Rome')::date,
  at timestamptz not null default now(),
  primary key (owner, chiave)
);

create index if not exists idx_coda_fatte_giorno on coda_fatte (owner, giorno);

alter table coda_fatte enable row level security;

drop policy if exists coda_fatte_mie on coda_fatte;
create policy coda_fatte_mie on coda_fatte
  for all to authenticated
  using (owner = uid_eff())
  with check (owner = uid_eff());

-- le spunte di ieri non servono a nessuno: si puliscono da sole
-- (la coda si ricalcola ogni giorno, le chiavi vecchie restano appese)
delete from coda_fatte where giorno < (now() at time zone 'Europe/Rome')::date - 7;
