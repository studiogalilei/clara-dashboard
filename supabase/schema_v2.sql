-- ODYN Studio - schema v2 (3 lug 2026): Anagrafe ID + Soppressioni + Liste
-- Da eseguire nel SQL Editor di Supabase, una volta sola, DOPO schema.sql.

-- ============ 1. PROSPECT ID (P-NNNNN) ============
-- numero eterno: mai riusato, mai cambiato, nessun significato dentro.
create sequence if not exists pid_seq start 1;

alter table prospects add column if not exists pid integer;

-- battesimo dei prospect esistenti, in ordine deterministico di ingresso
-- (created_at, poi email come spareggio: rifatto darebbe gli stessi numeri)
with numerati as (
  select id, row_number() over (order by created_at, email) as rn
  from prospects
  where pid is null
)
update prospects p set pid = n.rn from numerati n where p.id = n.id;

-- il contatore riparte dal primo numero libero
select setval('pid_seq', coalesce((select max(pid) from prospects), 0) + 1, false);

-- da ora in poi ogni nuovo prospect riceve il PID automaticamente
alter table prospects alter column pid set default nextval('pid_seq');
alter table prospects alter column pid set not null;
create unique index if not exists idx_prospects_pid on prospects(pid);

-- ============ 2. CLIENT ID (C-NNN) ============
-- si assegna SOLO alla firma; si AGGIUNGE al PID, non lo sostituisce.
create sequence if not exists cid_seq start 1;
alter table prospects add column if not exists cid integer;
create unique index if not exists idx_prospects_cid on prospects(cid) where cid is not null;

-- ============ 3. SOPPRESSIONI (il sistema sa chi non toccare) ============
create table if not exists suppressions (
  id uuid primary key default gen_random_uuid(),
  kind text not null,                -- gdpr | rimozione | lamentela | no_esplicito | non_target | deceduto
  email text,                        -- almeno una tra email e domain
  domain text,
  pid integer,                       -- aggancio all'anagrafe se noto
  reason text not null,              -- il motivo, in parole
  source text,                       -- da dove arriva la decisione (es. "mail del 2/7", "audit Lorenzo")
  created_at timestamptz default now(),
  check (email is not null or domain is not null)
);
create unique index if not exists idx_suppr_email on suppressions(lower(email)) where email is not null;
create unique index if not exists idx_suppr_domain on suppressions(lower(domain)) where domain is not null;

comment on table suppressions is 'Registro NON CONTATTARE, per sempre, su ogni canale. Ogni tool lo consulta prima di qualsiasi contatto. Blocca anche i rientri dalla porta (validazione liste).';

-- ============ 4. LISTE (L-NNN) ============
create sequence if not exists lid_seq start 1;

create table if not exists lists (
  id uuid primary key default gen_random_uuid(),
  lid integer not null default nextval('lid_seq'),
  name text not null,
  purpose text,                      -- outbound smartlead | linkedin | visite | altro
  source text,                       -- da dove viene la lista grezza (scraper/fonte)
  status text not null default 'attiva',   -- attiva | chiusa
  created_at timestamptz default now()
);
create unique index if not exists idx_lists_lid on lists(lid);

create table if not exists list_members (
  list_id uuid not null references lists(id) on delete cascade,
  prospect_id uuid not null references prospects(id) on delete cascade,
  added_at timestamptz default now(),
  status text default 'attivo',      -- attivo | uscito | soppresso_dopo
  primary key (list_id, prospect_id)
);
create index if not exists idx_list_members_prospect on list_members(prospect_id);

-- ============ 5. RLS ============
alter table suppressions enable row level security;
alter table lists enable row level security;
alter table list_members enable row level security;

drop policy if exists "auth full suppressions" on suppressions;
create policy "auth full suppressions" on suppressions for all to authenticated using (true) with check (true);
drop policy if exists "auth full lists" on lists;
create policy "auth full lists" on lists for all to authenticated using (true) with check (true);
drop policy if exists "auth full list_members" on list_members;
create policy "auth full list_members" on list_members for all to authenticated using (true) with check (true);
