-- ODYN CRM schema v22 (11 set 2026) — i widget a richiesta
--
-- Dre: «le persone vedono i widget con i loro nomi, mi mandano la richiesta,
-- io accetto e basta». Le voci di base le hanno tutti; il resto si chiede.
-- Una riga per persona e widget: richiesto, approvato o negato. Chiede
-- ognuno per se'; decide chi ha il ruolo ceo (Dre e Giacomo), e la regola
-- sta qui, non solo nell'interfaccia.

create table if not exists widget_accessi (
  user_id     uuid not null references auth.users(id) on delete cascade,
  widget      text not null,
  stato       text not null default 'richiesto' check (stato in ('richiesto', 'approvato', 'negato')),
  chiesto_il  timestamptz not null default now(),
  deciso_il   timestamptz,
  deciso_da   uuid references auth.users(id),
  primary key (user_id, widget)
);
alter table widget_accessi enable row level security;

drop policy if exists "i propri accessi e, se ceo, tutti" on widget_accessi;
create policy "i propri accessi e, se ceo, tutti" on widget_accessi
  for select to authenticated using (user_id = auth.uid() or sono_ceo());

drop policy if exists "ognuno chiede per se'" on widget_accessi;
create policy "ognuno chiede per se'" on widget_accessi
  for insert to authenticated with check (user_id = auth.uid() and stato = 'richiesto' or sono_ceo());

drop policy if exists "decide chi e' ceo" on widget_accessi;
create policy "decide chi e' ceo" on widget_accessi
  for update to authenticated using (sono_ceo()) with check (sono_ceo());

drop policy if exists "toglie chi e' ceo" on widget_accessi;
create policy "toglie chi e' ceo" on widget_accessi
  for delete to authenticated using (sono_ceo() or user_id = auth.uid());

select 'schema v22 applicato: widget a richiesta' as esito;
