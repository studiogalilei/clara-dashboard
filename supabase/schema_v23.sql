-- ODYN CRM schema v23 (12 set 2026) — i perimetri, e «vedi come»
--
-- Dre, 11/9: «Carlo entra dalla call tecnica in poi, prima non vede i
-- prospect». Ogni widget e' una vista sugli stessi dati con un perimetro:
-- per ruolo (i ceo vedono tutto), per fase (gli altri vedono le aziende
-- dalla call tecnica in poi), per persona (le task e la chat sono di chi
-- le ha). La regola sta qui, nel database, non nell'interfaccia.
--
-- «Voglio vedere cosa vedono gli altri» (Dre, 12/9): un ceo puo' mettersi
-- nei panni di una persona (tabella vista_come). Da li' in poi ogni policy
-- ragiona con uid_eff(), l'utente effettivo: il Workspace diventa davvero
-- quello di Carlo, non un'imitazione. La riga la scrive e la toglie solo il
-- ceo vero (auth.uid()), cosi' non si chiude mai fuori.

create table if not exists vista_come (
  ceo_id  uuid primary key references auth.users(id) on delete cascade,
  come_id uuid not null references auth.users(id) on delete cascade,
  da      timestamptz not null default now()
);
alter table vista_come enable row level security;
drop policy if exists "solo il ceo vero, per se'" on vista_come;
create policy "solo il ceo vero, per se'" on vista_come
  for all to authenticated
  using (ceo_id = auth.uid() and exists (select 1 from profili where id = auth.uid() and ruolo = 'ceo'))
  with check (ceo_id = auth.uid() and exists (select 1 from profili where id = auth.uid() and ruolo = 'ceo'));

create or replace function uid_eff() returns uuid
language sql stable security definer set search_path = public as $$
  select coalesce((select come_id from vista_come where ceo_id = auth.uid()), auth.uid());
$$;

create or replace function sono_ceo() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from profili where id = uid_eff() and ruolo = 'ceo');
$$;

create or replace function nome_eff() returns text
language sql stable security definer set search_path = public as $$
  select nome from profili where id = uid_eff();
$$;

-- il perimetro sulle aziende: tutto ai ceo; agli altri dalla call tecnica in
-- poi, e chi seguono loro (chi_segue col loro nome di battesimo)
create or replace function vedo_prospect(p_fuori boolean, p_stage text, p_chi_segue text) returns boolean
language sql stable security definer set search_path = public as $$
  select sono_ceo()
      or (coalesce(p_fuori, false) and p_stage in ('tecnica', 'avvio', 'prova', 'cliente'))
      or (p_chi_segue is not null and nome_eff() is not null
          and p_chi_segue ilike '%' || split_part(nome_eff(), ' ', 1) || '%');
$$;

-- prospects
drop policy if exists "auth full access prospects" on prospects;
drop policy if exists "aziende nel perimetro" on prospects;
create policy "aziende nel perimetro" on prospects
  for select to authenticated using (vedo_prospect(fuori, pipeline_stage, chi_segue));
drop policy if exists "aziende: scrive chi le vede" on prospects;
create policy "aziende: scrive chi le vede" on prospects
  for update to authenticated using (vedo_prospect(fuori, pipeline_stage, chi_segue)) with check (true);
drop policy if exists "aziende: crea e cancella il ceo" on prospects;
create policy "aziende: crea e cancella il ceo" on prospects
  for insert to authenticated with check (sono_ceo());
drop policy if exists "aziende: cancella il ceo" on prospects;
create policy "aziende: cancella il ceo" on prospects
  for delete to authenticated using (sono_ceo());

-- quello che pende da un'azienda segue il suo perimetro
drop policy if exists "auth full access interactions" on interactions;
drop policy if exists "storia nel perimetro" on interactions;
create policy "storia nel perimetro" on interactions
  for all to authenticated
  using (exists (select 1 from prospects p where p.id = prospect_id and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue)))
  with check (exists (select 1 from prospects p where p.id = prospect_id and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue)));

drop policy if exists "auth full access agenda" on agenda;
drop policy if exists "agenda nel perimetro" on agenda;
create policy "agenda nel perimetro" on agenda
  for all to authenticated
  using (prospect_id is null or exists (select 1 from prospects p where p.id = prospect_id and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue)))
  with check (prospect_id is null or exists (select 1 from prospects p where p.id = prospect_id and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue)));

drop policy if exists "auth full access vault" on vault_file;
drop policy if exists "documenti nel perimetro" on vault_file;
create policy "documenti nel perimetro" on vault_file
  for all to authenticated
  using (prospect_id is null or exists (select 1 from prospects p where p.id = prospect_id and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue)))
  with check (prospect_id is null or exists (select 1 from prospects p where p.id = prospect_id and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue)));

-- i soldi: solo i ceo
drop policy if exists "auth full access preventivi" on preventivi;
drop policy if exists "preventivi: i ceo" on preventivi;
create policy "preventivi: i ceo" on preventivi
  for all to authenticated using (sono_ceo()) with check (sono_ceo());

-- la chat e le proposte: di chi le ha; quelle senza nome (di Clara per la direzione) ai ceo
drop policy if exists "auth full access clara" on clara_messaggi;
drop policy if exists "chat: la propria" on clara_messaggi;
create policy "chat: la propria" on clara_messaggi
  for all to authenticated
  using (owner = uid_eff() or (owner is null and sono_ceo()))
  with check (owner = uid_eff() or (owner is null and sono_ceo()));

drop policy if exists "auth full access proposte" on proposte;
drop policy if exists "proposte: le proprie" on proposte;
create policy "proposte: le proprie" on proposte
  for all to authenticated
  using (owner = uid_eff() or (owner is null and sono_ceo()))
  with check (owner = uid_eff() or owner is null);

-- le task: le proprie; quelle senza nome ai ceo
drop policy if exists "auth full access task" on task;
drop policy if exists "task: le proprie" on task;
create policy "task: le proprie" on task
  for all to authenticated
  using (owner = uid_eff() or (owner is null and sono_ceo()))
  with check (owner = uid_eff() or (owner is null and sono_ceo()));

-- gli accessi ai widget: con l'utente effettivo
drop policy if exists "i propri accessi e, se ceo, tutti" on widget_accessi;
create policy "i propri accessi e, se ceo, tutti" on widget_accessi
  for select to authenticated using (user_id = uid_eff() or sono_ceo());
drop policy if exists "ognuno chiede per se'" on widget_accessi;
create policy "ognuno chiede per se'" on widget_accessi
  for insert to authenticated with check ((user_id = uid_eff() and stato = 'richiesto') or sono_ceo());

-- chi sono, in una chiamata sola: utente effettivo, nome, ruolo, widget concessi, e se sto vedendo come qualcun altro
create or replace function chi_sono() returns json
language sql stable security definer set search_path = public as $$
  select json_build_object(
    'uid', uid_eff(),
    'nome', nome_eff(),
    'ruolo', coalesce((select ruolo from profili where id = uid_eff()), 'coordinamento'),
    'concessi', coalesce((select json_agg(widget) from widget_accessi where user_id = uid_eff() and stato = 'approvato'), '[]'::json),
    'vista', (select json_build_object('id', v.come_id, 'nome', pr.nome) from vista_come v join profili pr on pr.id = v.come_id where v.ceo_id = auth.uid())
  );
$$;

select 'schema v23 applicato: perimetri e vedi come' as esito;

-- aggiunta: la vecchia policy delle task aveva ancora il nome di quando la tabella si chiamava task_dre
drop policy if exists "auth full access task_dre" on task;
