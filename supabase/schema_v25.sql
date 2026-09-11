-- ODYN CRM schema v25 (12 set 2026) — il diario aziendale
-- Dre (9/9): Clara chiede a ognuno 1-2 volte a settimana com'e' andata,
-- in modo genuino, non ogni giorno. Le risposte le leggono solo Dre e
-- Giacomo; il lunedi' Clara fa il recap. E' la memoria dell'azienda.
create table if not exists diario (
  id        bigint generated always as identity primary key,
  user_id   uuid not null references auth.users(id) on delete cascade,
  at        timestamptz not null default now(),
  domanda   text,
  testo     text not null
);
create index if not exists idx_diario_at on diario(at desc);
alter table diario enable row level security;
drop policy if exists "diario: scrive chi lo vive" on diario;
create policy "diario: scrive chi lo vive" on diario
  for insert to authenticated with check (user_id = uid_eff());
drop policy if exists "diario: lo leggono i ceo, e ognuno il suo" on diario;
create policy "diario: lo leggono i ceo, e ognuno il suo" on diario
  for select to authenticated using (user_id = uid_eff() or sono_ceo());
select 'schema v25 applicato: il diario' as esito;
