-- ════════════════════════════════════════════════════════════════════
-- ODYN CRM: schema completo, per un progetto Supabase vergine.
-- Tutte le versioni una dopo l'altra. Non cancella niente.
--
-- GENERATO da scripts/schema-completo.sh: non si modifica a mano.
-- Si aggiunge un file numerato in supabase/ e si rilancia lo script.
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

-- ─── schema_v5.sql ────────────────────────────────────────────

-- ════════════════════════════════════════════════════════════════════
-- ODYN CRM schema v5 (3 settembre 2026): due persone dentro la Dashboard
--
-- Da qui la Dashboard non e' piu' di uno solo. Le task hanno un proprietario
-- e un mittente, i lead si possono prendere in carico o passare a qualcun
-- altro, e ognuno ha le sue preferenze.
--
-- Non cancella niente e si puo' rilanciare senza danni.
-- ════════════════════════════════════════════════════════════════════

-- 1) LE TASK non sono piu' «di Dre»: hanno un proprietario e un mittente.
--    Il nome della tabella cambia di conseguenza, se no fra sei mesi nessuno
--    capisce perche' le task di Giacomo stanno in task_dre.
alter table if exists task_dre rename to task;

alter table task add column if not exists owner uuid references auth.users(id) default null;
alter table task add column if not exists da    uuid references auth.users(id) default null;

-- una task che arriva non entra nella lista di nessuno finche' non la accetta:
-- se no la lista smette di essere sua e viene ignorata
alter table task drop constraint if exists task_stato_check;
alter table task add column if not exists stato text not null default 'accettata';
alter table task add constraint task_stato_check
  check (stato in ('proposta', 'accettata', 'rimandata', 'fatta'));

alter table task add column if not exists motivo text;      -- perche' l'ha rimandata indietro
alter table task add column if not exists colore text;      -- facoltativo, per la Week picture

create index if not exists idx_task_owner on task (owner);
create index if not exists idx_task_da on task (da) where da is not null;

-- 2) LA TERZA USCITA DALLA PIPELINE: passato a qualcun altro.
--    Non e' ne' vinto ne' perso. Oggi quei lead o restano dentro a gonfiare i
--    numeri o spariscono, e con loro il rapporto con chi li ha ricevuti.
alter table prospects add column if not exists passato_a  text;
alter table prospects add column if not exists passato_il timestamptz;

-- 3) IL PRESO IN CARICO: con due persone sulla stessa casella, o rispondono
--    in due o non risponde nessuno perche' ognuno pensa all'altro.
alter table prospects add column if not exists preso_da uuid references auth.users(id) default null;
alter table prospects add column if not exists preso_il timestamptz;

-- 4) CHI LO SEGUE: il cuore del POD di Giacomo senza costruire la gestione
--    della delivery. Un campo, e i clienti si raggruppano per persona.
alter table prospects add column if not exists chi_segue text;

create index if not exists idx_prospects_preso on prospects (preso_da) where preso_da is not null;
create index if not exists idx_prospects_passato on prospects (passato_a) where passato_a is not null;

-- 5) LE PREFERENZE di ognuno: quali widget vede, in che ordine, come si apre.
--    Stanno qui e non nel browser cosi' ti seguono sul telefono.
create table if not exists preferenze (
  owner  uuid not null references auth.users(id) on delete cascade,
  chiave text not null,
  valore jsonb not null,
  primary key (owner, chiave)
);
alter table preferenze enable row level security;
drop policy if exists "ognuno le sue preferenze" on preferenze;
create policy "ognuno le sue preferenze" on preferenze
  for all to authenticated using (owner = auth.uid()) with check (owner = auth.uid());

-- 6) LE PERSONE: chi c'e' dentro la Dashboard. Serve per mandarsi le task,
--    per sapere chi ha preso in carico un lead, e per mostrare un nome
--    invece di un codice. Il nome se lo scrive ognuno nel suo profilo.
create table if not exists profili (
  id    uuid primary key references auth.users(id) on delete cascade,
  nome  text,
  ruolo text not null default 'coordinamento'
);
alter table profili drop constraint if exists profili_ruolo_check;
alter table profili add constraint profili_ruolo_check
  check (ruolo in ('ceo', 'coordinamento'));
alter table profili enable row level security;

-- tutti vedono chi c'e' (se no non sai a chi mandare una task),
-- ma ognuno modifica solo se stesso
drop policy if exists "le persone si vedono" on profili;
create policy "le persone si vedono" on profili
  for select to authenticated using (true);
drop policy if exists "ognuno il suo profilo" on profili;
create policy "ognuno il suo profilo" on profili
  for all to authenticated using (id = auth.uid()) with check (id = auth.uid());

-- chi si iscrive entra da solo nell'elenco
create or replace function crea_profilo()
returns trigger language plpgsql security definer as $$
begin
  insert into profili (id, nome) values (new.id, split_part(new.email, '@', 1))
  on conflict (id) do nothing;
  return new;
end $$;

drop trigger if exists al_nuovo_utente on auth.users;
create trigger al_nuovo_utente after insert on auth.users
  for each row execute function crea_profilo();

-- e chi c'e' gia' ci entra adesso
insert into profili (id, nome)
  select id, split_part(email, '@', 1) from auth.users
  on conflict (id) do nothing;

-- ─── schema_v5b.sql ────────────────────────────────────────────

-- ODYN CRM v5b (4 settembre 2026): la scheda del cliente contiene TUTTO.
-- Manca un solo aggancio: una task deve poter appartenere a un cliente, se
-- no la sua scheda non puo' mostrare cosa c'e' da fare per lui.
-- Non cancella niente, si puo' rilanciare.

alter table task add column if not exists prospect_id uuid
  references prospects(id) on delete set null;

create index if not exists idx_task_prospect on task (prospect_id)
  where prospect_id is not null;

-- ─── schema_v6.sql ────────────────────────────────────────────

-- ODYN CRM v6 (4 settembre 2026): i progetti.
--
-- Il lavoro di Studio Galilei e' di due tipi che finora stavano mescolati:
-- il RETAINER (ricorrente, mensile, senza scadenza: il canone) e il PROGETTO
-- (una cosa sola, con una scadenza e un valore: il sito, la landing, il setup).
-- Il ricorrente da solo era meta' della verita'.
--
-- Un progetto nasce dal pedaggio quando una carta arriva su Cliente: e' il
-- passaggio di consegne dal commerciale alla delivery, fatto nell'unico
-- istante in cui l'informazione ce l'ha in testa qualcuno.
--
-- Non cancella niente, si puo' rilanciare.

create table if not exists progetti (
  id          bigint generated always as identity primary key,
  at          timestamptz not null default now(),
  prospect_id uuid not null references prospects(id) on delete cascade,
  nome        text not null,              -- cosa gli abbiamo venduto
  natura      text,                       -- sito vetrina, campagna, setup...
  chi_segue   text,                       -- chi ce l'ha in mano
  scadenza    date,
  valore      numeric,                    -- quanto vale, in euro
  stato       text not null default 'da_iniziare',
  note        text,
  owner       uuid references auth.users(id) default null
);

alter table progetti drop constraint if exists progetti_stato_check;
alter table progetti add constraint progetti_stato_check
  check (stato in ('da_iniziare', 'in_corso', 'consegnato'));

alter table progetti enable row level security;
drop policy if exists "auth full access progetti" on progetti;
create policy "auth full access progetti" on progetti
  for all to authenticated using (true) with check (true);

create index if not exists idx_progetti_prospect on progetti (prospect_id);
create index if not exists idx_progetti_scadenza on progetti (scadenza)
  where stato <> 'consegnato';

-- i documenti si agganciano al progetto: il preventivo e' un file, non una
-- cosa che costruiamo noi
alter table vault_file add column if not exists progetto_id bigint
  references progetti(id) on delete set null;
create index if not exists idx_vault_progetto on vault_file (progetto_id)
  where progetto_id is not null;

-- ─── schema_v7.sql ────────────────────────────────────────────

-- ODYN CRM schema v7 (4 set 2026) — la vista «oggi» torna a dire la verità
--
-- v_oggi esiste dalla v3 e non la usa nessuno. Nel frattempo la Dashboard ha
-- imparato quattro ragioni per cui una persona finisce nella coda di oggi, e
-- la vista ne conosceva solo tre e per giunta diverse: era una quarta
-- definizione di «cosa devo fare oggi», addormentata nello schema, pronta a
-- dare un quinto numero il giorno che qualcuno l'avesse interrogata.
--
-- Adesso è la copia esatta di codaDiOggi() in src/lib/regole.ts:
--   1 rispondi    ha scritto lui e aspetta te
--   2 followup    la sua data è arrivata, oppure silenzio da 5 giorni
--   3 ricontatto  next_action_date arrivata
--   4 rientro     è tornato dalle ferie
-- Chi ha più di una ragione compare una volta sola, con la prima.
-- Chi è cliente, perso o passato a qualcun altro non ha una coda.
--
-- Se cambia la regola nel browser, cambia anche qui.
--
-- ISTRUZIONI: incollare nell'editor SQL di Supabase e premere Run.

-- non «create or replace»: la v3 aveva altre colonne, e Postgres rifiuta di
-- sostituire una vista cambiandole. Si butta e si rifà.
drop view if exists v_oggi;
create view v_oggi as
select id, email, name, company, stage, classificazione, awaiting_us,
       analysis_sent_at, followup_due, ooo_until, next_action, next_action_date,
       last_reply_at, fuori, pipeline_stage, passato_a,
       case
         when awaiting_us and not fuori then 1
         when stage in ('analisi_inviata', 'in_follow_up')
              and not awaiting_us and not fuori
              and (
                (followup_due is not null and followup_due <= current_date)
                or (followup_due is null
                    and analysis_sent_at is not null
                    and analysis_sent_at < now() - interval '5 days')
              ) then 2
         when next_action_date is not null and next_action_date <= current_date then 3
         when ooo_until is not null and ooo_until <= current_date and not fuori then 4
       end as ragione
from prospects
where no_followup = false
  and coalesce(classificazione, '') not in ('soppresso', 'fuori_target', 'negativo')
  and passato_a is null
  -- né cliente né perso, nelle due strade (pipeline e vecchio stile)
  and not (fuori and pipeline_stage in ('cliente', 'perso'))
  and not (not fuori and stage in ('cliente', 'perso'))
  and (
    (awaiting_us and not fuori)
    or (stage in ('analisi_inviata', 'in_follow_up') and not awaiting_us and not fuori
        and (
          (followup_due is not null and followup_due <= current_date)
          or (followup_due is null
              and analysis_sent_at is not null
              and analysis_sent_at < now() - interval '5 days')
        ))
    or (next_action_date is not null and next_action_date <= current_date)
    or (ooo_until is not null and ooo_until <= current_date and not fuori)
  );

select 'schema v7 applicato' as esito;

-- ─── schema_v8.sql ────────────────────────────────────────────

-- ODYN CRM schema v8 (7 set 2026) — la stanza di Clara
--
-- Clara legge ovunque e capisce, ma nella pipeline non scrive mai da sola:
-- mette una PROPOSTA nella sua stanza (cosa vuole fare, su chi, perche') e
-- Dre dice si' o no. Solo sul si' si scrive. Ogni risposta le insegna una
-- regola. Vedi docs/LA-STANZA-DI-CLARA.md.
--
-- E una sola scheda per persona: chi risponde da un'altra mail e' lo stesso
-- prospect, stesso SG-ID; la seconda mail va in email_alt.
--
-- ISTRUZIONI: incollare nell'editor SQL di Supabase e premere Run.

create table if not exists proposte (
  id          bigint generated always as identity primary key,
  at          timestamptz not null default now(),
  tipo        text not null,              -- classifica | scarta | perso | tornato | stessa_persona | richiesta | data | avanza
  prospect_id uuid references prospects(id) on delete cascade,
  titolo      text not null,              -- una riga: cosa vuole fare
  perche      text,                       -- perche' lo propone
  azione      jsonb not null default '{}'::jsonb,  -- cosa scrivere sul si': {"prospects": {...}, "task": {...}}
  stato       text not null default 'aperta',
  risposta    text,                       -- se Dre aggiunge due parole
  risposta_il timestamptz,
  owner       uuid                        -- a chi e' rivolta; null = a tutti
);
alter table proposte drop constraint if exists proposte_stato_check;
alter table proposte add constraint proposte_stato_check
  check (stato in ('aperta', 'si', 'no', 'fatta'));
create index if not exists idx_proposte_aperte on proposte (at) where stato = 'aperta';
create index if not exists idx_proposte_prospect on proposte (prospect_id) where prospect_id is not null;

alter table proposte enable row level security;
drop policy if exists "auth full access proposte" on proposte;
create policy "auth full access proposte" on proposte
  for all to authenticated using (true) with check (true);

-- la seconda mail della stessa persona
alter table prospects add column if not exists email_alt text[];

-- le risposte di Clara nella chat: un tipo in piu' per clara_messaggi
-- (nessun vincolo da cambiare: tipo e' testo libero)

select 'schema v8 applicato' as esito;

-- ─── schema_v9.sql ────────────────────────────────────────────

-- ODYN CRM schema v9 (7 set 2026) — la sala di controllo
--
-- Dre, 7/9: «non voglio che i processi siano legati al Mac, voglio in cloud,
-- che non si perda nulla, un sync autonomo, e scegliere la cadenza da li'».
--
-- Tre tabelle:
--   operazioni   cosa gira, ogni quanto, com'e' andata l'ultima volta.
--                La cadenza la cambia Dre dalla Dashboard; il direttore in
--                cloud (scripts/direttore.py, ogni 15 minuti) legge qui e fa
--                partire quello che e' dovuto. Nessun orologio da riscrivere.
--   corse        il registro: ogni esecuzione lascia una riga, anche se fallisce
--   istruzioni   le regole scritte da Dre che il cervello legge prima di tutto:
--                come classificare, come parlare in chat, cosa mettere nel brief
--   widget_richieste  i widget chiesti da Dre, con il loro stato
--
-- ISTRUZIONI: incollare nell'editor SQL di Supabase e premere Run.

create table if not exists operazioni (
  chiave           text primary key,
  nome             text not null,
  cosa             text,
  comando          text,                       -- lo script che gira; null = gira altrove (backup)
  cadenza_minuti   int  not null default 60,
  ora_preferita    text,                       -- per le giornaliere: "08:00" (ora di Roma)
  attiva           boolean not null default true,
  richiesta_ora    boolean not null default false,   -- «fai ora» dalla Dashboard
  ultima_corsa     timestamptz,
  ultimo_esito     text,                       -- ok | errore
  ultimo_dettaglio text,
  ultima_durata_ms int,
  ordine           int not null default 0
);
alter table operazioni enable row level security;
drop policy if exists "auth full access operazioni" on operazioni;
create policy "auth full access operazioni" on operazioni
  for all to authenticated using (true) with check (true);

create table if not exists corse (
  id         bigint generated always as identity primary key,
  operazione text not null references operazioni(chiave) on delete cascade,
  at         timestamptz not null default now(),
  esito      text not null,                    -- ok | errore
  dettaglio  text,
  righe      int,
  durata_ms  int
);
create index if not exists idx_corse_op on corse (operazione, at desc);
alter table corse enable row level security;
drop policy if exists "auth full access corse" on corse;
create policy "auth full access corse" on corse
  for all to authenticated using (true) with check (true);

create table if not exists istruzioni (
  chiave     text primary key,                 -- lettura | chat | brief
  titolo     text not null,
  testo      text not null default '',
  aggiornata timestamptz not null default now()
);
alter table istruzioni enable row level security;
drop policy if exists "auth full access istruzioni" on istruzioni;
create policy "auth full access istruzioni" on istruzioni
  for all to authenticated using (true) with check (true);

create table if not exists widget_richieste (
  id       bigint generated always as identity primary key,
  at       timestamptz not null default now(),
  nome     text not null,
  cosa     text not null,                      -- cosa deve mostrare o tenere d'occhio
  per_chi  text,                               -- ceo | coordinamento | tutti
  fonte    text,                               -- da dove prende i dati
  cadenza  text,                               -- ogni quanto guarda
  tipo     text not null default 'monitoraggio',  -- monitoraggio | interfaccia
  stato    text not null default 'richiesto',  -- richiesto | in_costruzione | attivo | scartato
  note     text
);
alter table widget_richieste enable row level security;
drop policy if exists "auth full access widget_richieste" on widget_richieste;
create policy "auth full access widget_richieste" on widget_richieste
  for all to authenticated using (true) with check (true);

-- le operazioni di partenza: si possono cambiare dalla Dashboard
insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ora_preferita, ordine) values
  ('sync_smartlead', 'Sincronizza Smartlead', 'Legge tutte le risposte e le mette nella Dashboard. Era fermo un mese, ad agosto.', 'python3 scripts/sync_v2.py', 60, null, 1),
  ('rilettura',      'Clara rilegge le risposte', 'Corregge il sicuro da sola, il resto lo chiede nella sua stanza.', 'python3 scripts/rilettura.py', 1440, '06:30', 2),
  ('brief',          'Il punto del mattino', 'Il saluto in testata e il brief nella chat di Clara.', 'python3 scripts/clara.py', 1440, '08:00', 3),
  ('backup',         'Backup notturno', 'Una copia cifrata di tutto, fuori da Supabase, tenuta 30 giorni.', null, 1440, '03:00', 4),
  ('calendar',       'Legge Google Calendar', 'Le call con data, invitati e link. Arriva con l''utenza tecnica di Workspace.', null, 60, null, 5),
  ('granola',        'Legge Granola', 'I transcript delle call. Arriva con la chiave API di Granola.', null, 120, null, 6)
on conflict (chiave) do nothing;
update operazioni set attiva = false where chiave in ('calendar', 'granola') and ultima_corsa is null;

insert into istruzioni (chiave, titolo, testo) values
  ('lettura', 'Come classificare le risposte', ''),
  ('chat',    'Come parlare con me in chat', ''),
  ('brief',   'Cosa mettere nel punto del mattino', '')
on conflict (chiave) do nothing;

select 'schema v9 applicato' as esito;
