-- ODYN CRM schema v24 (12 set 2026) — le tabelle interne (outbound, runner, istruzioni) solo ai ceo
drop policy if exists "auth full access corse" on corse;
drop policy if exists "corse: i ceo" on corse;
create policy "corse: i ceo" on corse for all to authenticated using (sono_ceo()) with check (sono_ceo());
drop policy if exists "auth full access istruzioni" on istruzioni;
drop policy if exists "istruzioni: i ceo" on istruzioni;
create policy "istruzioni: i ceo" on istruzioni for all to authenticated using (sono_ceo()) with check (sono_ceo());
drop policy if exists "auth full list_members" on list_members;
drop policy if exists "list_members: i ceo" on list_members;
create policy "list_members: i ceo" on list_members for all to authenticated using (sono_ceo()) with check (sono_ceo());
drop policy if exists "auth full lists" on lists;
drop policy if exists "lists: i ceo" on lists;
create policy "lists: i ceo" on lists for all to authenticated using (sono_ceo()) with check (sono_ceo());
drop policy if exists "auth full access operazioni" on operazioni;
drop policy if exists "operazioni: i ceo" on operazioni;
create policy "operazioni: i ceo" on operazioni for all to authenticated using (sono_ceo()) with check (sono_ceo());
drop policy if exists "auth full suppressions" on suppressions;
drop policy if exists "suppressions: i ceo" on suppressions;
create policy "suppressions: i ceo" on suppressions for all to authenticated using (sono_ceo()) with check (sono_ceo());
drop policy if exists "auth full access sync_runs" on sync_runs;
drop policy if exists "sync_runs: i ceo" on sync_runs;
create policy "sync_runs: i ceo" on sync_runs for all to authenticated using (sono_ceo()) with check (sono_ceo());
drop policy if exists "auth full access tappe" on tappe;
drop policy if exists "tappe: i ceo" on tappe;
create policy "tappe: i ceo" on tappe for all to authenticated using (sono_ceo()) with check (sono_ceo());
drop policy if exists "auth full access widget_richieste" on widget_richieste;
drop policy if exists "widget_richieste: i ceo" on widget_richieste;
create policy "widget_richieste: i ceo" on widget_richieste for all to authenticated using (sono_ceo()) with check (sono_ceo());
select 'schema v24 applicato: tabelle interne ai ceo' as esito;

-- correzione: le tappe dei progetti sono di tutti, come i progetti
drop policy if exists "tappe: i ceo" on tappe;
drop policy if exists "auth full access tappe" on tappe;
create policy "auth full access tappe" on tappe for all to authenticated using (true) with check (true);
select 'tappe riaperte' as esito;
