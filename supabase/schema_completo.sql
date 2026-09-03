-- ════════════════════════════════════════════════════════════════════
-- ODYN CRM: schema completo per il trasloco (3/9/2026)
-- Le quattro versioni una dopo l'altra, per un progetto Supabase vergine.
-- Non cancella niente e non tocca le candidature gia' presenti.
-- ════════════════════════════════════════════════════════════════════


-- ─── schema.sql ────────────────────────────────────────────

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

-- ─── schema_v2.sql ────────────────────────────────────────────

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

-- ─── schema_v3.sql ────────────────────────────────────────────

-- ODYN CRM schema v3 (7 lug 2026)
-- Il modello: Smartlead = aggancio. Il lead maturo si PORTA FUORI e vive nella
-- pipeline agenzia dentro questo CRM. Il sync automatico tiene aggiornato tutto,
-- Dre segna a mano il "fuori" e i next step dopo le call.
-- ISTRUZIONI: nell'editor SQL di Supabase fare Cmd+A e cancellare prima di incollare.

-- 1) Conversazione: chi deve muoversi adesso
alter table prospects add column if not exists awaiting_us boolean not null default false;
-- true = l'ultimo messaggio del thread e' del LEAD: tocca a noi rispondere

alter table prospects add column if not exists classificazione text
  check (classificazione in ('da_classificare','positivo','tiepido','negativo','ooo','rinvio','fuori_target','soppresso'))
  default null;
-- classificazione euristica del sync, correggibile a mano dalla Scheda

alter table prospects add column if not exists followup_due date;
-- quando scade il follow-up (5gg dopo analisi, o data OOO/rinvio)

alter table prospects add column if not exists ooo_until date;
-- se OOO: quando rientra (il sync la propone, Dre la corregge)

-- 2) Porta fuori da Smartlead: la pipeline agenzia
alter table prospects add column if not exists fuori boolean not null default false;
-- true = Dre l'ha portato fuori da Smartlead: si gestisce SOLO da qui

alter table prospects add column if not exists fuori_at timestamptz;

alter table prospects add column if not exists pipeline_stage text
  check (pipeline_stage in ('call_fatta','proposta_inviata','pilota','cliente','perso_fuori'))
  default null;
-- lo stato del lead DENTRO la pipeline agenzia (solo se fuori=true)

-- 3) Salute del sync: il registro delle corse (mai piu' buchi silenziosi)
create table if not exists sync_runs (
  id bigint generated always as identity primary key,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  campaigns_checked int not null default 0,
  leads_scanned int not null default 0,
  replies_found int not null default 0,
  updated int not null default 0,
  reconciliation_ok boolean,
  anomalies text,          -- se i conteggi non tornano, QUI c'e' scritto cosa manca
  ok boolean not null default false
);
alter table sync_runs enable row level security;
drop policy if exists "auth full access sync_runs" on sync_runs;
create policy "auth full access sync_runs" on sync_runs
  for all to authenticated using (true) with check (true);

-- 4) Indici per la vista Oggi
create index if not exists idx_prospects_awaiting on prospects (awaiting_us) where awaiting_us = true;
create index if not exists idx_prospects_followup_due on prospects (followup_due) where followup_due is not null;
create index if not exists idx_prospects_fuori on prospects (pipeline_stage) where fuori = true;

-- 5) Vista "oggi": tutto cio' che chiede attenzione, in una query
create or replace view v_oggi as
select id, email, name, company, stage, classificazione, awaiting_us,
       followup_due, ooo_until, next_action, next_action_date, last_reply_at,
       fuori, pipeline_stage,
       case
         when awaiting_us then 1                                     -- da rispondere
         when followup_due is not null and followup_due <= current_date then 2  -- follow-up scaduto
         when next_action_date is not null and next_action_date <= current_date then 3 -- ricontatto/next step
         when ooo_until is not null and ooo_until <= current_date then 4        -- rientrato da OOO
         else 99
       end as priorita
from prospects
where no_followup = false
  and coalesce(classificazione,'') not in ('soppresso','fuori_target','negativo')
  and (
    awaiting_us
    or (followup_due is not null and followup_due <= current_date)
    or (next_action_date is not null and next_action_date <= current_date)
    or (ooo_until is not null and ooo_until <= current_date)
  );

select 'schema v3 applicato' as esito;

-- ─── schema_v4.sql ────────────────────────────────────────────

-- ODYN CRM schema v4 (28 ago 2026) — il Cruscotto
-- Le fasi della pipeline diventano quelle vere di Dre:
--   prospect -> conoscitiva -> tecnica -> avvio -> cliente (| perso)
-- e arrivano i due cancelli: fuori_binario e il transcript delle call.
-- ISTRUZIONI: nell'editor SQL di Supabase fare Cmd+A e cancellare prima di incollare.

-- 0) L'ID permanente (Dre, 31/8): SG-000001. L'ID identifica il SOGGETTO
--    e non cambia mai; lo status (prospect -> client) dice la relazione.
--    LO ASSEGNA CLARA NEL MOMENTO IN CUI IL LEAD DIVENTA PROSPECT (prima
--    risposta su Smartlead): smartlead -> dashboard+Clara -> cliente.
--    I lead che non hanno mai risposto NON hanno un ID.
create sequence if not exists sg_id_seq;
alter table prospects add column if not exists sg_id bigint;
create unique index if not exists idx_prospects_sg_id on prospects (sg_id);

-- chi ha gia' risposto riceve l'ID adesso, in ordine di prima risposta:
-- la numerazione racconta la storia dell'agenzia
with ordinati as (
  select id from prospects
  where sg_id is null and first_reply_at is not null
  order by first_reply_at
)
update prospects p set sg_id = nextval('sg_id_seq')
from ordinati o where p.id = o.id;

-- da qui in poi ci pensa il trigger: prima risposta = ID
create or replace function assegna_sg_id() returns trigger as $$
begin
  if new.sg_id is null and new.first_reply_at is not null then
    new.sg_id := nextval('sg_id_seq');
  end if;
  return new;
end $$ language plpgsql;
drop trigger if exists trg_sg_id on prospects;
create trigger trg_sg_id before insert or update on prospects
  for each row execute function assegna_sg_id();

-- 1) Le fasi nuove: si allarga il vincolo, si migrano i valori vecchi
alter table prospects drop constraint if exists prospects_pipeline_stage_check;

update prospects set pipeline_stage = 'conoscitiva'     where pipeline_stage = 'call_fatta';
update prospects set pipeline_stage = 'tecnica'          where pipeline_stage = 'proposta_inviata';
update prospects set pipeline_stage = 'avvio'            where pipeline_stage = 'pilota';
update prospects set pipeline_stage = 'perso'            where pipeline_stage = 'perso_fuori';

alter table prospects add constraint prospects_pipeline_stage_check
  check (pipeline_stage in ('conoscitiva','tecnica','avvio','cliente','perso'));

-- 2) Il cancello "fuori binario": Dre l'ha gia' sentito fuori dai sistemi?
--    null = mai chiesto (la mail resta ferma) · 'si' · 'no'
alter table prospects add column if not exists fuori_binario text
  check (fuori_binario in ('si','no')) default null;

-- 2bis) Chi sono: descrizione breve dell'azienda e del referente
alter table prospects add column if not exists descrizione text;

-- 3) Il mercato del prospect (dalla base precalcolata 333 combinazioni)
--    {ricerche, cpc, mesi_vivi, bars: [[altezza_pct, e_picco] x12],
--     fit: 'si'|'no', zona, misurato_il}
alter table prospects add column if not exists market jsonb;

-- 4) Modello economico cliente (Periodo di prova 1500 x 2 mesi | Stable 1400/mese)
alter table prospects add column if not exists contratto text
  check (contratto in ('prova','stable')) default null;
alter table prospects add column if not exists canone numeric;

-- 5) Il transcript delle call viaggia come interaction kind='transcript'
--    (kind e' testo libero, nessuna migrazione). L'avanzamento di fase senza
--    transcript lo blocca l'interfaccia: e' il pedaggio.
comment on column interactions.kind is
  'email_in | email_out | analisi | followup | call | nota | transcript';

-- 6) Agenda: gli impegni che Achille legge dal calendario e serve interpretati
create table if not exists agenda (
  id bigint generated always as identity primary key,
  at timestamptz not null,
  titolo text not null,
  tipo text,                    -- conoscitiva | tecnica | avvio | invio | altro
  prospect_id uuid references prospects(id) on delete set null,
  link text,                    -- l'evento su Google Calendar / il Meet
  fonte text not null default 'gcal',
  creato_il timestamptz not null default now()
);
alter table agenda enable row level security;
drop policy if exists "auth full access agenda" on agenda;
create policy "auth full access agenda" on agenda
  for all to authenticated using (true) with check (true);
create index if not exists idx_agenda_at on agenda (at);

-- 7) Indice per gli avvisi (fermi da troppo)
create index if not exists idx_prospects_last_reply on prospects (last_reply_at)
  where last_reply_at is not null;

-- 8) Clara, la segretaria: i suoi messaggi (brief del mattino, promemoria,
--    domande, controlli). Lei scrive, Dre legge dalla Dashboard.
create table if not exists clara_messaggi (
  id bigint generated always as identity primary key,
  at timestamptz not null default now(),
  tipo text not null default 'promemoria',  -- brief | promemoria | domanda | controllo
  testo text not null,
  prospect_id uuid references prospects(id) on delete set null,
  letto boolean not null default false
);
alter table clara_messaggi enable row level security;
drop policy if exists "auth full access clara" on clara_messaggi;
create policy "auth full access clara" on clara_messaggi
  for all to authenticated using (true) with check (true);
create index if not exists idx_clara_at on clara_messaggi (at desc);

-- 9) Il Vault: la cassaforte dei file. Nome suo, aggancio facoltativo a un
--    prospect/cliente, dentro il bucket Storage 'vault'.
create table if not exists vault_file (
  id bigint generated always as identity primary key,
  at timestamptz not null default now(),
  nome text not null,
  path text not null,
  mime text,
  dimensione bigint,
  prospect_id uuid references prospects(id) on delete set null
);
alter table vault_file enable row level security;
drop policy if exists "auth full access vault" on vault_file;
create policy "auth full access vault" on vault_file
  for all to authenticated using (true) with check (true);

insert into storage.buckets (id, name, public)
  values ('vault', 'vault', true)
  on conflict (id) do nothing;
drop policy if exists "vault lettura" on storage.objects;
create policy "vault lettura" on storage.objects
  for select using (bucket_id = 'vault');
drop policy if exists "vault scrittura" on storage.objects;
create policy "vault scrittura" on storage.objects
  for insert to authenticated with check (bucket_id = 'vault');
drop policy if exists "vault cancellazione" on storage.objects;
create policy "vault cancellazione" on storage.objects
  for delete to authenticated using (bucket_id = 'vault');

-- 10) Le attività personali di Dre nella sezione Task (stile Google Tasks):
--     le crea lui (o Clara sotto dettatura), si spuntano, restano in
--     «Completate».
create table if not exists task_dre (
  id bigint generated always as identity primary key,
  at timestamptz not null default now(),
  titolo text not null,
  dettagli text,
  scadenza date,
  ordine int not null default 0,
  fatta boolean not null default false,
  fatta_il timestamptz
);
alter table task_dre enable row level security;
drop policy if exists "auth full access task_dre" on task_dre;
create policy "auth full access task_dre" on task_dre
  for all to authenticated using (true) with check (true);

select 'schema v4 applicato' as esito;

-- ────────────────────────────────────────────────────────────────────
-- v4.1 (2/9/2026): le manopole di Clara e il campo owner.
-- Deciso in ARCHITETTURA-CLARA.md. Aggiunto qui invece che in un file
-- nuovo cosi' Dre incolla una volta sola.
-- ────────────────────────────────────────────────────────────────────

-- 12) Agenti e Skills: la scheda di ogni capacita' sta in un file JSON nel
--     progetto (skills/<chiave>.json). Qui ci sta solo cio' che CAMBIA:
--     l'interruttore di Dre e com'e' andato l'ultimo giro. La riga nasce da
--     sola alla prima accensione: una capacita' nuova non richiede che
--     qualcuno tocchi il database.
create table if not exists clara_skills (
  chiave text primary key,
  acceso boolean not null default true,
  ultimo_giro timestamptz,
  ultimo_esito text,
  owner uuid references auth.users(id) default null
);
alter table clara_skills enable row level security;
drop policy if exists "auth full access skills" on clara_skills;
create policy "auth full access skills" on clara_skills
  for all to authenticated using (true) with check (true);

-- 13) owner: chi possiede la riga. Oggi vuoto ovunque e vuol dire
--     «dell'azienda», e nessuna schermata cambia. E' il gancio a cui domani
--     si attaccano le regole per dividere chi vede cosa, senza dover
--     toccare 13.000 righe quel giorno.
--     L'abitudine che vale piu' del campo: ogni tabella nuova nasce con owner.
alter table prospects       add column if not exists owner uuid references auth.users(id) default null;
alter table interactions    add column if not exists owner uuid references auth.users(id) default null;
alter table agenda          add column if not exists owner uuid references auth.users(id) default null;
alter table clara_messaggi  add column if not exists owner uuid references auth.users(id) default null;
alter table vault_file      add column if not exists owner uuid references auth.users(id) default null;
alter table task_dre        add column if not exists owner uuid references auth.users(id) default null;

-- 14) La cartella del prospect (Dre, 2/9): non e' una tabella nuova.
--     La cartella E' il suo contenuto, cioe' l'analisi agganciata, chi sono,
--     il verdetto sul mercato e tutto quello che si allega dopo. Creare un
--     record «cartella» vuoto sarebbe solo una cosa in piu' che puo'
--     disallinearsi. Serve solo poter cercare in fretta per prospect.
create index if not exists idx_vault_prospect on vault_file (prospect_id)
  where prospect_id is not null;
