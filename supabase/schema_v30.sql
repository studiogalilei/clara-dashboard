-- ODYN CRM schema v30 (15 set 2026) — Storage: si aggiorna, e il brand non si cancella
--
-- QA (backend): rigenerare un PDF sullo stesso path e' un update per le RLS
-- di Storage, e la policy non c'era: il secondo «Genera il PDF» falliva.
-- E chiunque poteva cancellare i loghi e i modelli dalla cassaforte.

drop policy if exists "vault aggiornamento" on storage.objects;
create policy "vault aggiornamento" on storage.objects
  for update to authenticated using (bucket_id = 'vault') with check (bucket_id = 'vault');

-- si cancella solo la roba dei clienti che si vede; brand, modelli e azienda sono dei ceo
drop policy if exists "vault cancellazione" on storage.objects;
create policy "vault cancellazione" on storage.objects
  for delete to authenticated
  using (bucket_id = 'vault' and (
    sono_ceo()
    or (split_part(name, '/', 1) = 'clienti'
        and exists (select 1 from prospects p where p.id::text = split_part(name, '/', 2) and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue)))));

-- le righe dei Documenti: il brand e i modelli li tocca solo la direzione
drop policy if exists "documenti nel perimetro" on vault_file;
create policy "documenti: leggo cio' che vedo" on vault_file
  for select to authenticated
  using (prospect_id is null or exists (select 1 from prospects p where p.id = prospect_id and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue)));
drop policy if exists "documenti: aggiungo" on vault_file;
create policy "documenti: aggiungo" on vault_file
  for insert to authenticated
  with check (sono_ceo() or (prospect_id is not null and exists (select 1 from prospects p where p.id = prospect_id and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue))));
drop policy if exists "documenti: cambio e tolgo" on vault_file;
create policy "documenti: cambio e tolgo" on vault_file
  for update to authenticated
  using (sono_ceo() or (prospect_id is not null and exists (select 1 from prospects p where p.id = prospect_id and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue))))
  with check (sono_ceo() or (prospect_id is not null and exists (select 1 from prospects p where p.id = prospect_id and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue))));
drop policy if exists "documenti: tolgo" on vault_file;
create policy "documenti: tolgo" on vault_file
  for delete to authenticated
  using (sono_ceo() or (prospect_id is not null and exists (select 1 from prospects p where p.id = prospect_id and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue))));

select 'schema v30 applicato: storage aggiornabile, brand e modelli protetti' as esito;
