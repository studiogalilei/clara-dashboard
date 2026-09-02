-- ODYN CRM — schema v1
-- Da eseguire nel SQL Editor di Supabase (una volta sola).

create table if not exists prospects (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  name text,
  role text,
  phone text,
  linkedin text,
  company text,
  website text,
  sector text,
  city text,
  socials jsonb default '{}'::jsonb,
  owner_name text,
  campaign text,
  campaign_id bigint,
  lead_id bigint,
  stage text not null default 'nuovo',
  first_reply_at timestamptz,
  last_reply_at timestamptz,
  analysis_sent boolean default false,
  analysis_sent_at timestamptz,
  analysis_pdf text,
  next_action text,
  next_action_date date,
  no_followup boolean default false,
  deal_value numeric,
  lost_reason text,
  notes text,
  enriched jsonb default '{}'::jsonb,
  source text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

comment on column prospects.stage is 'nuovo | risposto | analisi_inviata | in_follow_up | call_fissata | cliente | perso | rinviato';
comment on column prospects.enriched is 'mappa campo -> auto|manual (chi ha compilato la casella)';
comment on column prospects.no_followup is 'true = escluso dai follow-up automatici (skip)';

create table if not exists interactions (
  id uuid primary key default gen_random_uuid(),
  prospect_id uuid not null references prospects(id) on delete cascade,
  at timestamptz not null,
  kind text not null,
  body text,
  created_at timestamptz default now()
);

comment on column interactions.kind is 'email_in | email_out | analisi | followup | call | nota';

create index if not exists idx_prospects_stage on prospects(stage);
create index if not exists idx_prospects_next_action on prospects(next_action_date);
create index if not exists idx_prospects_last_reply on prospects(last_reply_at desc);
create index if not exists idx_interactions_prospect on interactions(prospect_id, at desc);
create unique index if not exists idx_interactions_dedup on interactions(prospect_id, at, kind);

create or replace function set_updated_at() returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_prospects_updated on prospects;
create trigger trg_prospects_updated before update on prospects
  for each row execute function set_updated_at();

alter table prospects enable row level security;
alter table interactions enable row level security;

drop policy if exists "auth full access prospects" on prospects;
create policy "auth full access prospects" on prospects
  for all to authenticated using (true) with check (true);

drop policy if exists "auth full access interactions" on interactions;
create policy "auth full access interactions" on interactions
  for all to authenticated using (true) with check (true);
