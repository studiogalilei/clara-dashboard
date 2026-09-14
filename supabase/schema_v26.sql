-- ODYN CRM schema v26 (14 set 2026) — i ruoli veri e il pod
--
-- Dal documento «Divisioni e responsabilita'» di Giacomo (Q4 2026): un pod
-- e' un manager con i suoi ad specialist e un frontend. Il manager vede il
-- calendario e le task del suo pod (richiesta di Carlo, 14/9). I ruoli:
-- ceo, manager, specialist, frontend, coordinamento (chi non e' in un pod).

alter table profili drop constraint if exists profili_ruolo_check;
alter table profili add constraint profili_ruolo_check
  check (ruolo in ('ceo', 'coordinamento', 'manager', 'specialist', 'frontend'));

create table if not exists pod (
  manager_id uuid not null references auth.users(id) on delete cascade,
  membro_id  uuid not null references auth.users(id) on delete cascade,
  dal        date not null default current_date,
  primary key (manager_id, membro_id)
);
alter table pod enable row level security;
drop policy if exists "il pod lo vedono tutti, lo scrive il ceo" on pod;
create policy "il pod lo vedono tutti, lo scrive il ceo" on pod for select to authenticated using (true);
drop policy if exists "pod: scrive il ceo" on pod;
create policy "pod: scrive il ceo" on pod for all to authenticated using (sono_ceo()) with check (sono_ceo());

-- e' nel mio pod? (io manager, lui membro)
create or replace function nel_mio_pod(persona uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from pod where manager_id = uid_eff() and membro_id = persona);
$$;

-- l'agenda ha un proprietario: null = il calendario dello Studio (Dre), altrimenti quello della persona
alter table agenda add column if not exists owner uuid references auth.users(id) on delete cascade;
create index if not exists idx_agenda_owner on agenda(owner, at);

drop policy if exists "agenda nel perimetro" on agenda;
create policy "agenda nel perimetro" on agenda
  for all to authenticated
  using (
    (owner is null and (prospect_id is null or exists (select 1 from prospects p where p.id = prospect_id and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue))))
    or owner = uid_eff() or nel_mio_pod(owner) or sono_ceo())
  with check (
    (owner is null and (prospect_id is null or exists (select 1 from prospects p where p.id = prospect_id and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue))))
    or owner = uid_eff() or nel_mio_pod(owner) or sono_ceo());

-- le task: le mie, quelle del mio pod, e per i ceo tutte
drop policy if exists "task: le proprie" on task;
create policy "task: le proprie" on task
  for all to authenticated
  using (owner = uid_eff() or (owner is null and sono_ceo()) or nel_mio_pod(owner) or sono_ceo())
  with check (owner = uid_eff() or (owner is null and sono_ceo()) or nel_mio_pod(owner) or sono_ceo());

-- chi_sono: anche il pod (i membri, se sono manager; il manager, se sono membro)
create or replace function chi_sono() returns json
language sql stable security definer set search_path = public as $$
  select json_build_object(
    'uid', uid_eff(),
    'nome', nome_eff(),
    'ruolo', coalesce((select ruolo from profili where id = uid_eff()), 'coordinamento'),
    'concessi', coalesce((select json_agg(widget) from widget_accessi where user_id = uid_eff() and stato = 'approvato'), '[]'::json),
    'pod', coalesce((select json_agg(json_build_object('id', pr.id, 'nome', pr.nome, 'ruolo', pr.ruolo)) from pod po join profili pr on pr.id = po.membro_id where po.manager_id = uid_eff()), '[]'::json),
    'vista', (select json_build_object('id', v.come_id, 'nome', pr.nome) from vista_come v join profili pr on pr.id = v.come_id where v.ceo_id = auth.uid())
  );
$$;

-- il pod di oggi: Carlo manager, Salvatore specialist, Alex frontend (Dre, 14/9)
update profili set ruolo = 'manager' where id = '4d5a857e-f0b3-43d3-8b1a-8e24c7102d8a';
update profili set ruolo = 'specialist', nome = 'Salvatore' where id = '880f4e94-2f2f-48da-aa28-ddac04b7d61f';
update profili set ruolo = 'frontend', nome = 'Alex' where id = 'e6276dd0-b940-48fc-a808-09b05ab3830b';
insert into pod (manager_id, membro_id) values
  ('4d5a857e-f0b3-43d3-8b1a-8e24c7102d8a', '880f4e94-2f2f-48da-aa28-ddac04b7d61f'),
  ('4d5a857e-f0b3-43d3-8b1a-8e24c7102d8a', 'e6276dd0-b940-48fc-a808-09b05ab3830b')
  on conflict do nothing;

select 'schema v26 applicato: ruoli veri e pod' as esito;
