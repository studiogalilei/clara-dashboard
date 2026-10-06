-- v75 (6/10): i referenti del Vault del cliente.
--
-- Dre, a voce: «subito sotto ci sono i referenti, posso cliccare e aprire
-- ulteriormente quella parte, mettere anche altri referenti, oppure
-- aggiungere informazioni ulteriori». Il referente principale resta nelle
-- colonne di prospects (name, role, email, phone); qui stanno gli ALTRI:
-- il tecnico, l'amministrazione, il socio. Una riga per persona.

create table if not exists referenti (
  id bigserial primary key,
  at timestamptz not null default now(),
  prospect_id uuid not null references prospects(id) on delete cascade,
  nome text not null,
  ruolo text,
  email text,
  telefono text,
  nota text
);

create index if not exists idx_referenti_prospect on referenti (prospect_id);

alter table referenti enable row level security;

-- stesso perimetro dei Documenti (v30): vedi i referenti delle aziende che vedi
drop policy if exists "referenti: leggo cio' che vedo" on referenti;
create policy "referenti: leggo cio' che vedo" on referenti
  for select to authenticated
  using (exists (select 1 from prospects p where p.id = prospect_id and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue)));
drop policy if exists "referenti: aggiungo" on referenti;
create policy "referenti: aggiungo" on referenti
  for insert to authenticated
  with check (exists (select 1 from prospects p where p.id = prospect_id and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue)));
drop policy if exists "referenti: cambio e tolgo" on referenti;
create policy "referenti: cambio e tolgo" on referenti
  for update to authenticated
  using (exists (select 1 from prospects p where p.id = prospect_id and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue)))
  with check (exists (select 1 from prospects p where p.id = prospect_id and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue)));
drop policy if exists "referenti: tolgo" on referenti;
create policy "referenti: tolgo" on referenti
  for delete to authenticated
  using (exists (select 1 from prospects p where p.id = prospect_id and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue)));

select 'schema v75 applicato: i referenti del Vault' as esito;
