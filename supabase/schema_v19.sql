-- ODYN CRM schema v19 (11 set 2026) — la firma di ognuno
-- Dre: «la possibilità di avere la propria firma lì, comoda». La firma
-- (PNG, come data URL) sta nel profilo; il timbro dell'azienda nel bucket
-- vault (timbro/timbro.png). Serve allo strumento «Compila PDF».
alter table profili add column if not exists firma text;
drop policy if exists "ognuno scrive il suo profilo" on profili;
create policy "ognuno scrive il suo profilo" on profili
  for update to authenticated using (id = auth.uid()) with check (id = auth.uid());
select 'schema v19 applicato: la firma nel profilo' as esito;
