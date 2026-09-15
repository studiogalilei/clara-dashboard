-- ODYN CRM schema v29 (14 set 2026) — le trovate del QA (Carlo, Giacomo)

-- 1. una task si puo' PROPORRE a chiunque (entra nella sua lista quando accetta):
--    prima il manager poteva mandarne solo al pod, e la squadra non poteva rispondere a Dre
drop policy if exists "task: le proprie" on task;
create policy "task: le proprie" on task
  for all to authenticated
  using (owner = uid_eff() or (owner is null and sono_ceo()) or nel_mio_pod(owner) or sono_ceo())
  with check (owner = uid_eff() or (owner is null and sono_ceo()) or nel_mio_pod(owner) or sono_ceo()
              or (stato = 'proposta' and da = uid_eff()));

-- 2. un'azienda non si scrive in una fase che poi non vedi: se no un clic la fa sparire
drop policy if exists "aziende: scrive chi le vede" on prospects;
create policy "aziende: scrive chi le vede" on prospects
  for update to authenticated
  using (vedo_prospect(fuori, pipeline_stage, chi_segue))
  with check (vedo_prospect(fuori, pipeline_stage, chi_segue));

-- 3. «chi segue» vive sui progetti: si copia sull'azienda, cosi' il perimetro scatta
create or replace function progetti_chi_segue_sync() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.chi_segue is not null and new.prospect_id is not null then
    update prospects set chi_segue = new.chi_segue where id = new.prospect_id and (chi_segue is null or chi_segue = '');
  end if;
  return new;
end $$;
drop trigger if exists progetti_chi_segue_sync on progetti;
create trigger progetti_chi_segue_sync after insert or update of chi_segue on progetti
  for each row execute function progetti_chi_segue_sync();
update prospects p set chi_segue = g.chi_segue
  from progetti g
  where g.prospect_id = p.id and g.chi_segue is not null and g.chi_segue <> '' and (p.chi_segue is null or p.chi_segue = '');

-- 4. l'agenda senza azienda e senza proprietario e' la vita privata di Dre: solo ceo
drop policy if exists "agenda nel perimetro" on agenda;
create policy "agenda nel perimetro" on agenda
  for all to authenticated
  using (
    (owner is null and prospect_id is not null and exists (select 1 from prospects p where p.id = prospect_id and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue)))
    or (owner is null and prospect_id is null and sono_ceo())
    or owner = uid_eff() or nel_mio_pod(owner) or sono_ceo())
  with check (
    (owner is null and prospect_id is not null and exists (select 1 from prospects p where p.id = prospect_id and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue)))
    or (owner is null and prospect_id is null and sono_ceo())
    or owner = uid_eff() or nel_mio_pod(owner) or sono_ceo());

-- 5. il bucket dei Documenti non e' pubblico: chi legge deve essere dentro, e i file
--    dei clienti li vede solo chi vede il cliente (URL firmate dal browser)
update storage.buckets set public = false where id = 'vault';
drop policy if exists "vault lettura" on storage.objects;
create policy "vault lettura" on storage.objects
  for select to authenticated
  using (bucket_id = 'vault' and (
    split_part(name, '/', 1) <> 'clienti'
    or exists (select 1 from prospects p where p.id::text = split_part(name, '/', 2) and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue))));

-- 6. pulizia: il preventivo 1 (azienda persa, senza importo) non e' «accettato da incassare»
update preventivi set stato = 'rifiutato', rifiutato_il = current_date, motivo = 'azienda persa in pipeline (pulizia 14/9)'
  where id = 1 and stato = 'accettato' and importo is null;
-- il puntino «·» nelle note dei progetti
update progetti set note = replace(note, ' · ', ', ') where note like '% · %';
update progetti set note = replace(note, '·', ',') where note like '%·%';

select 'schema v29 applicato: task proponibili, perimetro in scrittura, chi segue dai progetti, agenda privata, bucket privato' as esito;
