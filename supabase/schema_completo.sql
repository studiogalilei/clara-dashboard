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

-- ─── schema_v10.sql ────────────────────────────────────────────

-- ODYN CRM schema v10 (7 set 2026) — l'orologio di riserva
--
-- Il direttore gira su GitHub ogni 15 minuti. Ma il cron di GitHub, il 7/9,
-- non e' partito da solo per ore: e' noto che ritarda, e per un sistema che
-- deve durare anni un orologio solo non basta. Questo e' il secondo orologio:
-- pg_cron, dentro Supabase, che ogni 15 minuti chiede a GitHub di far
-- partire il direttore (workflow_dispatch). Se GitHub parte da solo, il
-- direttore trova gia' tutto fatto e non fa niente: i due orologi non si
-- pestano i piedi (il workflow ha «concurrency: direttore»).
--
-- SERVE UN TOKEN: un «fine-grained personal access token» di GitHub, creato
-- da Dre, con permesso Actions: Read and write SOLO sul repo
-- studiogalilei/clara-dashboard. Si mette nel Vault di Supabase, mai qui.
--
-- ISTRUZIONI:
--   1) sostituire IL_TOKEN qui sotto col token (una volta sola), incollare, Run
--   2) poi cancellare il token dalla riga: resta nel Vault, cifrato

create extension if not exists pg_cron;
create extension if not exists pg_net;

-- il token nel Vault (cifrato). Se esiste gia', lo aggiorna.
do $$
declare v_id uuid;
begin
  select id into v_id from vault.secrets where name = 'github_direttore';
  if v_id is null then
    perform vault.create_secret('IL_TOKEN', 'github_direttore', 'token GitHub per far partire il direttore');
  else
    perform vault.update_secret(v_id, 'IL_TOKEN');
  end if;
end $$;

-- la funzione che bussa a GitHub
create or replace function chiama_direttore(forza text default '')
returns void language plpgsql security definer as $$
declare
  tok text;
begin
  select decrypted_secret into tok from vault.decrypted_secrets where name = 'github_direttore';
  if tok is null then
    raise notice 'manca il token github_direttore nel Vault';
    return;
  end if;
  perform net.http_post(
    url := 'https://api.github.com/repos/studiogalilei/clara-dashboard/actions/workflows/direttore.yml/dispatches',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || tok,
      'Accept', 'application/vnd.github+json',
      'User-Agent', 'clara-dashboard',
      'Content-Type', 'application/json'),
    body := jsonb_build_object('ref', 'main', 'inputs', jsonb_build_object('forza', forza))
  );
end $$;

-- ogni 15 minuti: il direttore. Ogni notte alle 01:10 UTC: il backup.
select cron.unschedule(jobid) from cron.job where jobname in ('direttore', 'backup');
select cron.schedule('direttore', '*/15 * * * *', $$select chiama_direttore()$$);
select cron.schedule('backup', '10 1 * * *', $$
  select net.http_post(
    url := 'https://api.github.com/repos/studiogalilei/clara-dashboard/actions/workflows/backup.yml/dispatches',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || (select decrypted_secret from vault.decrypted_secrets where name = 'github_direttore'),
      'Accept', 'application/vnd.github+json', 'User-Agent', 'clara-dashboard', 'Content-Type', 'application/json'),
    body := '{"ref":"main"}'::jsonb)
$$);

select 'schema v10 applicato: due orologi' as esito;

-- ─── schema_v11.sql ────────────────────────────────────────────

-- ODYN CRM schema v11 (8 set 2026) — il foglio dei progetti di Giacomo
--
-- Dre (8/9): «un excel con selettore, serve per seguire i progetti in corso».
-- E' il foglio "Delivery" di Giacomo portato dentro la Dashboard: una riga
-- per progetto, con il selettore Trial / Retainer / onboarding, la data di
-- inizio e il nome del cliente scritto libero (non tutti i clienti sono
-- prospect del CRM: Dän Ink, GR box…). Se il prospect c'e', si aggancia.

alter table progetti add column if not exists tipo text;              -- trial | retainer | onboarding
alter table progetti add column if not exists data_inizio date;
alter table progetti add column if not exists cliente text;           -- il nome scritto a mano, quando non e' un prospect
alter table progetti alter column prospect_id drop not null;

alter table progetti drop constraint if exists progetti_tipo_check;
alter table progetti add constraint progetti_tipo_check
  check (tipo is null or tipo in ('trial', 'retainer', 'onboarding'));

comment on column progetti.tipo is 'trial | retainer | onboarding: il selettore del foglio di Giacomo';

select 'schema v11 applicato: il foglio dei progetti' as esito;

-- ─── schema_v12.sql ────────────────────────────────────────────

-- ODYN CRM schema v12 (9 set 2026) — il contatore dei PID era rimasto indietro
--
-- Creando un cliente nuovo dal foglio di Giacomo il database ha risposto
-- «pid 1 esiste gia'»: la sequenza pid_seq era ferma a 1 perche' gli import
-- di massa scrivevano i pid a mano. Ogni inserimento nuovo (sync, stanza,
-- foglio) si rompeva. Qui la si riallinea al massimo vero.

select setval('pid_seq', coalesce((select max(pid) from prospects), 0) + 1, false);

select 'schema v12 applicato: pid_seq riallineata a ' || (select last_value from pid_seq) as esito;

-- ─── schema_v13.sql ────────────────────────────────────────────

-- ODYN CRM schema v13 (9 set 2026) — preventivi e pagamenti, e le tappe dei progetti
--
-- Dre (9/9): «Tutti» come il foglio di Giacomo, con lo stato selezionabile
-- (Prospect / Preventivo inviato / Cliente) e i pagamenti tracciati a mano
-- per ogni preventivo; una sezione «Tutti i preventivi» dal primo all'ultimo.
-- E la Roadmap dei progetti con i checkpoint di Giacomo. Tutto appeso all'SG-ID.

-- 1) i preventivi: uno per offerta, con il pagamento sopra
create table if not exists preventivi (
  id           bigint generated always as identity primary key,
  prospect_id  uuid not null references prospects(id) on delete cascade,
  progetto_id  bigint references progetti(id) on delete set null,
  titolo       text,                              -- «Google Ads trial 2 mesi»
  importo      numeric,                           -- euro, iva esclusa
  inviato_il   date not null default current_date,
  stato        text not null default 'inviato',   -- inviato | accettato | rifiutato
  pagato_il    date,                              -- lo spunta Giacomo quando arriva
  pagamento_atteso_il date,
  note         text,
  owner        uuid references auth.users(id) default null,
  creato_il    timestamptz not null default now()
);
alter table preventivi drop constraint if exists preventivi_stato_check;
alter table preventivi add constraint preventivi_stato_check
  check (stato in ('inviato', 'accettato', 'rifiutato'));
create index if not exists idx_preventivi_prospect on preventivi (prospect_id);
create index if not exists idx_preventivi_inviato on preventivi (inviato_il);
alter table preventivi enable row level security;
drop policy if exists "auth full access preventivi" on preventivi;
create policy "auth full access preventivi" on preventivi
  for all to authenticated using (true) with check (true);

-- 2) le tappe (checkpoint) dei progetti, per la Roadmap
create table if not exists tappe (
  id           bigint generated always as identity primary key,
  progetto_id  bigint not null references progetti(id) on delete cascade,
  titolo       text not null,                     -- «Accessi ricevuti», «Prima campagna viva»
  data         date not null,
  fatta        boolean not null default false,
  fatta_il     timestamptz,
  creato_il    timestamptz not null default now()
);
create index if not exists idx_tappe_progetto on tappe (progetto_id);
alter table tappe enable row level security;
drop policy if exists "auth full access tappe" on tappe;
create policy "auth full access tappe" on tappe
  for all to authenticated using (true) with check (true);

select 'schema v13 applicato: preventivi e tappe' as esito;

-- ─── schema_v14.sql ────────────────────────────────────────────

-- ODYN CRM schema v14 (9 set 2026) — il periodo di prova
--
-- Dre (9/9): «la pipeline da prospect non passa subito a cliente: passa
-- prima al periodo di prova, due mesi, con inizio e fine. Quando finisce
-- mi riaccordo con loro (alzo il prezzo) e si passa al retainer. Il 97% dei
-- clienti comincia dal trial.» Fase nuova `prova` fra avvio e cliente, con
-- le due date sul prospect.

alter table prospects add column if not exists prova_inizio date;
alter table prospects add column if not exists prova_fine   date;

alter table prospects drop constraint if exists prospects_pipeline_stage_check;
alter table prospects add constraint prospects_pipeline_stage_check
  check (pipeline_stage in ('conoscitiva','tecnica','avvio','prova','cliente','perso'));

create index if not exists idx_prospects_prova_fine on prospects (prova_fine) where prova_fine is not null;

-- chi oggi e' «cliente in prova» (contratto = prova) passa nella fase nuova con le date
update prospects
   set pipeline_stage = 'prova',
       prova_inizio = coalesce(prova_inizio, fuori_at::date),
       prova_fine   = coalesce(prova_fine, (coalesce(fuori_at::date, current_date) + interval '2 months')::date)
 where fuori and pipeline_stage = 'cliente' and contratto = 'prova';

select 'schema v14 applicato: periodo di prova' as esito;

-- ─── schema_v15.sql ────────────────────────────────────────────

-- ODYN CRM schema v15 (9 set 2026) — gli accessi del team
--
-- Creando gli utenti di Carlo, Lorenzo, Okay e Giacomo il database ha risposto
-- «Database error creating new user»: il trigger che crea il profilo
-- (crea_profilo) gira come utente di auth, che non vede lo schema public.
-- Gli si dice dove guardare, e da qui in poi ogni utente nuovo nasce col suo
-- profilo.

alter function crea_profilo() set search_path = public;

select 'schema v15 applicato: gli utenti nuovi si creano' as esito;

-- ─── schema_v16.sql ────────────────────────────────────────────

-- ODYN CRM schema v16 (10 set 2026) — Clara si sveglia da sola, in cloud
--
-- Due cose, entrambe per non dipendere piu' ne' dal Mac di Dre ne' dal solo
-- cron di GitHub (che ritarda e costa minuti).
--
-- 1) L'orologio di riserva (era v10, mai applicato): pg_cron ogni ora chiede
--    a GitHub di far partire il direttore, sfasato di mezz'ora rispetto al
--    cron di GitHub (7 * * * *). Le risposte di Smartlead non aspettano
--    nessuno dei due: arrivano via webhook (functions/smartlead-webhook).
--    Il token GitHub sta nel Vault, nome github_direttore: lo mette Claude
--    con un comando a parte, qui non c'e'.
--
-- 2) Clara risponde in chat dal cloud: a ogni riga nuova in clara_messaggi
--    con tipo 'dre', un trigger chiama la funzione clara-risponde. Prima
--    lo faceva scripts/clara_ascolta.py sul Mac (spento il 10/9).

create extension if not exists pg_cron;
create extension if not exists pg_net;

create or replace function chiama_direttore(forza text default '')
returns void language plpgsql security definer set search_path = public as $$
declare
  tok text;
begin
  select decrypted_secret into tok from vault.decrypted_secrets where name = 'github_direttore';
  if tok is null then
    raise notice 'manca il token github_direttore nel Vault';
    return;
  end if;
  perform net.http_post(
    url := 'https://api.github.com/repos/studiogalilei/clara-dashboard/actions/workflows/direttore.yml/dispatches',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || tok,
      'Accept', 'application/vnd.github+json',
      'User-Agent', 'clara-dashboard',
      'Content-Type', 'application/json'),
    body := jsonb_build_object('ref', 'main', 'inputs', jsonb_build_object('forza', forza))
  );
end $$;

select cron.unschedule(jobid) from cron.job where jobname in ('direttore', 'backup');
select cron.schedule('direttore', '37 * * * *', $$select chiama_direttore()$$);

-- 2) la chat: ogni messaggio di Dre sveglia clara-risponde
create or replace function sveglia_clara()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.tipo = 'dre' then
    perform net.http_post(
      url := 'https://tqssfcuzezlczfceqsmk.supabase.co/functions/v1/clara-risponde',
      headers := jsonb_build_object('Content-Type', 'application/json'),
      body := jsonb_build_object('type', 'INSERT', 'table', 'clara_messaggi', 'record', to_jsonb(new))
    );
  end if;
  return new;
end $$;

drop trigger if exists clara_messaggi_sveglia on clara_messaggi;
create trigger clara_messaggi_sveglia after insert on clara_messaggi
  for each row execute function sveglia_clara();

select 'schema v16 applicato: Clara si sveglia da sola' as esito;

-- ─── schema_v17.sql ────────────────────────────────────────────

-- ODYN CRM schema v17 (10 set 2026) — gli incassi da Stripe
--
-- Dre, 10/9: «dopo connettiamo Stripe». Clara legge Stripe ogni ora con una
-- chiave di sola lettura (scripts/stripe_sync.py) e mette qui addebiti,
-- fatture pagate e abbonamenti, collegati all'azienda quando la mail torna.
-- Se un incasso combacia con un preventivo accettato e non ancora pagato,
-- lo segna pagato da sola; se non e' sicura, lo chiede nella stanza.
--
-- I soldi li vedono solo Dre e Giacomo (ruolo ceo): la regola sta qui nel
-- database, non solo nell'interfaccia.

create table if not exists incassi (
  id             text primary key,                 -- l'id di Stripe: ch_, in_, sub_
  genere         text not null,                    -- addebito | fattura | abbonamento
  importo        numeric not null default 0,       -- euro (o valuta), gia' diviso per 100
  valuta         text not null default 'eur',
  stato          text,                             -- succeeded, paid, active, canceled, ...
  quando         timestamptz,                      -- creato su Stripe
  ricorrenza     text,                             -- month | year, per gli abbonamenti
  cliente_nome   text,
  cliente_email  text,
  stripe_cliente text,                             -- cus_...
  descrizione    text,
  prospect_id    uuid references prospects(id) on delete set null,
  preventivo_id  bigint references preventivi(id) on delete set null,
  letto_il       timestamptz not null default now()
);
create index if not exists incassi_quando on incassi (quando desc);
create index if not exists incassi_prospect on incassi (prospect_id);

create or replace function sono_ceo() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from profili where id = auth.uid() and ruolo = 'ceo');
$$;

alter table incassi enable row level security;
drop policy if exists "i soldi li vedono i ceo" on incassi;
create policy "i soldi li vedono i ceo" on incassi
  for select to authenticated using (sono_ceo());
-- scrive solo il runner (service role, che salta le policy)

select 'schema v17 applicato: incassi da Stripe' as esito;

-- ─── schema_v18.sql ────────────────────────────────────────────

-- ODYN CRM schema v18 (10 set 2026) — il blocco Pagamenti nel foglio
-- Per dire, sulla riga del cliente: come paga (SEPA, carta, bonifico),
-- quando e' il prossimo addebito e quando finisce (la prova finisce da sola).
alter table incassi add column if not exists metodo      text;          -- sepa | carta | bonifico | altro
alter table incassi add column if not exists prossimo_il timestamptz;   -- prossimo addebito (abbonamenti)
alter table incassi add column if not exists fine_il     timestamptz;   -- quando finisce o e' finito
select 'schema v18 applicato: pagamenti nel foglio' as esito;

-- ─── schema_v19.sql ────────────────────────────────────────────

-- ODYN CRM schema v19 (11 set 2026) — la firma di ognuno
-- Dre: «la possibilità di avere la propria firma lì, comoda». La firma
-- (PNG, come data URL) sta nel profilo; il timbro dell'azienda nel bucket
-- vault (timbro/timbro.png). Serve allo strumento «Compila PDF».
alter table profili add column if not exists firma text;
drop policy if exists "ognuno scrive il suo profilo" on profili;
create policy "ognuno scrive il suo profilo" on profili
  for update to authenticated using (id = auth.uid()) with check (id = auth.uid());
select 'schema v19 applicato: la firma nel profilo' as esito;

-- ─── schema_v20.sql ────────────────────────────────────────────

-- ODYN CRM schema v20 (11 set 2026) — il login con Google e la chiave per agire a nome tuo
--
-- Dre: accessi come Google. Si entra nel Workspace con l'account
-- @studiogalilei.com (provider Google in Supabase Auth, progetto Cloud
-- «SG Workspace»). Al primo accesso Google consegna anche un refresh token
-- con i permessi su Drive, Chat e Calendar: lo teniamo qui, uno per
-- persona, cosi' Clara puo' leggere il Drive e scrivere in SG Chat a nome
-- di chi ha dato il permesso. Lo scrive solo il proprietario; lo legge
-- solo il runner (service role): nessuna policy di lettura per gli utenti.

create table if not exists google_token (
  user_id        uuid primary key references auth.users(id) on delete cascade,
  email          text,
  refresh_token  text not null,
  scopes         text,
  aggiornato_il  timestamptz not null default now()
);
alter table google_token enable row level security;
drop policy if exists "ognuno scrive il suo token google" on google_token;
create policy "ognuno scrive il suo token google" on google_token
  for insert to authenticated with check (user_id = auth.uid());
drop policy if exists "ognuno aggiorna il suo token google" on google_token;
create policy "ognuno aggiorna il suo token google" on google_token
  for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
-- e vede solo se ce l'ha (non il valore: la select espone solo le colonne che il client chiede, ma per prudenza si legge via funzione)
create or replace function ho_il_token_google() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from google_token where user_id = auth.uid());
$$;

select 'schema v20 applicato: login con Google' as esito;

-- aggiunta (11/9 sera): l'upsert (on conflict do update) deve poter leggere la propria riga
drop policy if exists "ognuno vede il suo token google" on google_token;
create policy "ognuno vede il suo token google" on google_token
  for select to authenticated using (user_id = auth.uid());

-- ─── schema_v21.sql ────────────────────────────────────────────

-- ODYN CRM schema v21 (11 set 2026) — da dove viene un'interazione
-- Gli appunti di Gemini entrano come interazioni «transcript»; per non
-- importarli due volte serve sapere da quale file di Drive vengono.
alter table interactions add column if not exists ref text;   -- es. gemini:<id del Google Doc>
create index if not exists idx_interactions_ref on interactions(ref);
select 'schema v21 applicato: interactions.ref' as esito;

-- ─── schema_v22.sql ────────────────────────────────────────────

-- ODYN CRM schema v22 (11 set 2026) — i widget a richiesta
--
-- Dre: «le persone vedono i widget con i loro nomi, mi mandano la richiesta,
-- io accetto e basta». Le voci di base le hanno tutti; il resto si chiede.
-- Una riga per persona e widget: richiesto, approvato o negato. Chiede
-- ognuno per se'; decide chi ha il ruolo ceo (Dre e Giacomo), e la regola
-- sta qui, non solo nell'interfaccia.

create table if not exists widget_accessi (
  user_id     uuid not null references auth.users(id) on delete cascade,
  widget      text not null,
  stato       text not null default 'richiesto' check (stato in ('richiesto', 'approvato', 'negato')),
  chiesto_il  timestamptz not null default now(),
  deciso_il   timestamptz,
  deciso_da   uuid references auth.users(id),
  primary key (user_id, widget)
);
alter table widget_accessi enable row level security;

drop policy if exists "i propri accessi e, se ceo, tutti" on widget_accessi;
create policy "i propri accessi e, se ceo, tutti" on widget_accessi
  for select to authenticated using (user_id = auth.uid() or sono_ceo());

drop policy if exists "ognuno chiede per se'" on widget_accessi;
create policy "ognuno chiede per se'" on widget_accessi
  for insert to authenticated with check (user_id = auth.uid() and stato = 'richiesto' or sono_ceo());

drop policy if exists "decide chi e' ceo" on widget_accessi;
create policy "decide chi e' ceo" on widget_accessi
  for update to authenticated using (sono_ceo()) with check (sono_ceo());

drop policy if exists "toglie chi e' ceo" on widget_accessi;
create policy "toglie chi e' ceo" on widget_accessi
  for delete to authenticated using (sono_ceo() or user_id = auth.uid());

select 'schema v22 applicato: widget a richiesta' as esito;

-- ─── schema_v23.sql ────────────────────────────────────────────

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

-- ─── schema_v24.sql ────────────────────────────────────────────

-- ODYN CRM schema v24 (12 set 2026) — le tabelle interne (outbound, runner, istruzioni) solo ai ceo
drop policy if exists "auth full access corse" on corse;
drop policy if exists "corse: i ceo" on corse;
create policy "corse: i ceo" on corse for all to authenticated using (sono_ceo()) with check (sono_ceo());
drop policy if exists "auth full access istruzioni" on istruzioni;
drop policy if exists "istruzioni: i ceo" on istruzioni;
create policy "istruzioni: i ceo" on istruzioni for all to authenticated using (sono_ceo()) with check (sono_ceo());
drop policy if exists "auth full list_members" on list_members;
drop policy if exists "list_members: i ceo" on list_members;
create policy "list_members: i ceo" on list_members for all to authenticated using (sono_ceo()) with check (sono_ceo());
drop policy if exists "auth full lists" on lists;
drop policy if exists "lists: i ceo" on lists;
create policy "lists: i ceo" on lists for all to authenticated using (sono_ceo()) with check (sono_ceo());
drop policy if exists "auth full access operazioni" on operazioni;
drop policy if exists "operazioni: i ceo" on operazioni;
create policy "operazioni: i ceo" on operazioni for all to authenticated using (sono_ceo()) with check (sono_ceo());
drop policy if exists "auth full suppressions" on suppressions;
drop policy if exists "suppressions: i ceo" on suppressions;
create policy "suppressions: i ceo" on suppressions for all to authenticated using (sono_ceo()) with check (sono_ceo());
drop policy if exists "auth full access sync_runs" on sync_runs;
drop policy if exists "sync_runs: i ceo" on sync_runs;
create policy "sync_runs: i ceo" on sync_runs for all to authenticated using (sono_ceo()) with check (sono_ceo());
drop policy if exists "auth full access tappe" on tappe;
drop policy if exists "tappe: i ceo" on tappe;
create policy "tappe: i ceo" on tappe for all to authenticated using (sono_ceo()) with check (sono_ceo());
drop policy if exists "auth full access widget_richieste" on widget_richieste;
drop policy if exists "widget_richieste: i ceo" on widget_richieste;
create policy "widget_richieste: i ceo" on widget_richieste for all to authenticated using (sono_ceo()) with check (sono_ceo());
select 'schema v24 applicato: tabelle interne ai ceo' as esito;

-- correzione: le tappe dei progetti sono di tutti, come i progetti
drop policy if exists "tappe: i ceo" on tappe;
drop policy if exists "auth full access tappe" on tappe;
create policy "auth full access tappe" on tappe for all to authenticated using (true) with check (true);
select 'tappe riaperte' as esito;

-- ─── schema_v25.sql ────────────────────────────────────────────

-- ODYN CRM schema v25 (12 set 2026) — il diario aziendale
-- Dre (9/9): Clara chiede a ognuno 1-2 volte a settimana com'e' andata,
-- in modo genuino, non ogni giorno. Le risposte le leggono solo Dre e
-- Giacomo; il lunedi' Clara fa il recap. E' la memoria dell'azienda.
create table if not exists diario (
  id        bigint generated always as identity primary key,
  user_id   uuid not null references auth.users(id) on delete cascade,
  at        timestamptz not null default now(),
  domanda   text,
  testo     text not null
);
create index if not exists idx_diario_at on diario(at desc);
alter table diario enable row level security;
drop policy if exists "diario: scrive chi lo vive" on diario;
create policy "diario: scrive chi lo vive" on diario
  for insert to authenticated with check (user_id = uid_eff());
drop policy if exists "diario: lo leggono i ceo, e ognuno il suo" on diario;
create policy "diario: lo leggono i ceo, e ognuno il suo" on diario
  for select to authenticated using (user_id = uid_eff() or sono_ceo());
select 'schema v25 applicato: il diario' as esito;

-- ─── schema_v26.sql ────────────────────────────────────────────

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

-- ─── schema_v27.sql ────────────────────────────────────────────

-- ODYN CRM schema v27 (14 set 2026) — i Documenti come cassaforte ordinata
--
-- Dre, 14/9: «la cassaforte dell'azienda, si ritrova tutto in facilita':
-- i loghi, i template di documento...». Ogni file ha una sezione (dove
-- sta) e un gruppo (lo scaffale dentro la sezione), come le cartelle di
-- Drive ma fisse: nessuno inventa cartelle nuove.
--   brand    loghi, copertine, sfondi, segni, incisioni, regole
--   modelli  i template dei documenti (contratti, condizioni, guide)
--   azienda  documenti interni (societa', procedure, formazione)
--   clienti  i file agganciati a un'azienda (prospect_id)
alter table vault_file add column if not exists sezione text not null default 'clienti';
alter table vault_file add column if not exists gruppo text;
alter table vault_file add column if not exists nota text;
alter table vault_file drop constraint if exists vault_file_sezione_check;
alter table vault_file add constraint vault_file_sezione_check
  check (sezione in ('brand', 'modelli', 'azienda', 'clienti'));
update vault_file set sezione = 'clienti' where prospect_id is not null and sezione <> 'clienti';
update vault_file set sezione = 'azienda' where prospect_id is null and sezione = 'clienti';
create index if not exists idx_vault_file_sezione on vault_file(sezione, gruppo);
create unique index if not exists idx_vault_file_path on vault_file(path);

-- le regole dei documenti per Clara: chiave «documenti» nelle istruzioni
insert into istruzioni (chiave, titolo, testo) values ('documenti', 'Le regole dei documenti', '')
  on conflict (chiave) do nothing;

select 'schema v27 applicato: sezioni dei Documenti' as esito;

-- ─── schema_v28.sql ────────────────────────────────────────────

-- ODYN CRM schema v28 (14 set 2026) — i preventivi fatti bene
--
-- Dre, 14/9: «un widget per creare preventivi in modo smooth secondo le
-- brand guidelines, collegato al resto: segnare se accettano, vedere i
-- preventivi in giro e a che cliente sono connessi».
-- Un preventivo nasce bozza, si genera il PDF (Condizioni economiche, il
-- documento formale SG), si segna inviato, poi accettato o rifiutato;
-- pagato lo scrive Stripe (stripe_sync) o Giacomo a mano.

alter table preventivi add column if not exists numero        text;          -- SG-MK-2026-003
alter table preventivi add column if not exists linea         text;          -- marketing | ai | software | istituzionale
alter table preventivi add column if not exists voci          jsonb not null default '[]'::jsonb;
alter table preventivi add column if not exists mensile       numeric;       -- la parte ricorrente, al mese
alter table preventivi add column if not exists valido_fino   date;
alter table preventivi add column if not exists accettato_il  date;
alter table preventivi add column if not exists rifiutato_il  date;
alter table preventivi add column if not exists motivo        text;          -- perche' no (o note dell'esito)
alter table preventivi add column if not exists pdf_path      text;          -- nel bucket vault
alter table preventivi add column if not exists link_pagamento text;         -- il link Stripe, incollato
alter table preventivi add column if not exists condizioni    text;          -- il testo delle condizioni, se cambiato
alter table preventivi add column if not exists aggiornato_il timestamptz not null default now();
alter table preventivi alter column inviato_il drop not null;
alter table preventivi alter column inviato_il drop default;
alter table preventivi drop constraint if exists preventivi_stato_check;
alter table preventivi add constraint preventivi_stato_check
  check (stato in ('bozza', 'inviato', 'accettato', 'rifiutato'));
alter table preventivi drop constraint if exists preventivi_linea_check;
alter table preventivi add constraint preventivi_linea_check
  check (linea is null or linea in ('marketing', 'ai', 'software', 'istituzionale'));
create unique index if not exists idx_preventivi_numero on preventivi (numero) where numero is not null;

-- i dati di fatturazione stanno sull'azienda: servono ai preventivi e a Giacomo per le fatture
alter table prospects add column if not exists fatturazione jsonb;   -- {ragione, indirizzo, piva, pec, sdi}

-- il listino interno: le voci pronte da mettere in un preventivo. Non e' un
-- listino pubblico (il documento e' intestato all'azienda, non e' un prezzario)
create table if not exists listino (
  id          bigint generated always as identity primary key,
  nome        text not null,
  descrizione text,
  prezzo      numeric not null default 0,
  ricorrenza  text not null default 'una_tantum',    -- una_tantum | mese
  linea       text not null default 'marketing',
  ordine      int not null default 0,
  attivo      boolean not null default true
);
alter table listino enable row level security;
drop policy if exists "listino: i ceo" on listino;
create policy "listino: i ceo" on listino for all to authenticated using (sono_ceo()) with check (sono_ceo());
insert into listino (nome, descrizione, prezzo, ricorrenza, linea, ordine)
select * from (values
  ('Fase pilota Google Ads, 2 mesi', 'Due mesi di lavoro reale: analisi iniziale, impostazione, gestione e ottimizzazione sui dati. Pagata in anticipo alla firma, rimborsabile fino alla fine del secondo mese.', 1500, 'una_tantum', 'marketing', 1),
  ('Lavoro continuativo Google Ads', 'Dal terzo mese: gestione operativa, ottimizzazione, report periodici e call di allineamento. Addebito ricorrente su Stripe.', 1400, 'mese', 'marketing', 2),
  ('Sito web', 'Progettazione, sviluppo e pubblicazione del sito, con il tracciamento impostato.', 800, 'una_tantum', 'software', 3),
  ('Landing page', 'Una pagina di atterraggio per le campagne, con il tracciamento impostato.', 400, 'una_tantum', 'software', 4),
  ('Automazione su misura', 'Un processo che oggi si fa a mano, automatizzato.', 0, 'una_tantum', 'ai', 5)
) as v(nome, descrizione, prezzo, ricorrenza, linea, ordine)
where not exists (select 1 from listino);

-- i tre preventivi gia' fatti a mano: numero e linea
update preventivi set numero = 'SG-MK-2026-001', linea = 'marketing' where id = 1 and numero is null;
update preventivi set numero = 'SG-SW-2026-001', linea = 'software',  voci = '[{"nome":"Sito web","quantita":1,"prezzo":802,"ricorrenza":"una_tantum"}]' where id = 2 and numero is null;
update preventivi set numero = 'SG-MK-2026-002', linea = 'marketing', voci = '[{"nome":"Fase pilota Google Ads, 2 mesi","quantita":1,"prezzo":1502,"ricorrenza":"una_tantum"}]' where id = 3 and numero is null;

select 'schema v28 applicato: preventivi, listino, fatturazione' as esito;

-- ─── schema_v29.sql ────────────────────────────────────────────

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

-- ─── schema_v30.sql ────────────────────────────────────────────

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

-- ─── schema_v31.sql ────────────────────────────────────────────

-- ODYN CRM schema v31 (15 set 2026) — la chat di Clara non e' piu' aperta a Internet
--
-- QA (backend): clara-risponde sta su --no-verify-jwt e non controllava niente:
-- chiunque conoscesse l'indirizzo poteva bruciare crediti OpenAI, scrivere come
-- Clara nella chat di chiunque e nel diario a nome di un altro. Ora il trigger
-- manda un segreto nell'intestazione, e la funzione senza quello risponde 401.

create or replace function sveglia_clara()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.tipo = 'dre' then
    perform net.http_post(
      url := 'https://tqssfcuzezlczfceqsmk.supabase.co/functions/v1/clara-risponde',
      headers := jsonb_build_object('Content-Type', 'application/json', 'x-clara-segreto', '<CLARA_SEGRETO, nei secret delle funzioni e in .env.local>'),
      body := jsonb_build_object('type', 'INSERT', 'table', 'clara_messaggi', 'record', to_jsonb(new))
    );
  end if;
  return new;
end $$;

select 'schema v31 applicato: la chat parla solo col segreto' as esito;

-- ─── schema_v32.sql ────────────────────────────────────────────

-- ODYN CRM schema v32 (15 set 2026) — i dati dello Studio, e il ricorrente in un posto solo
--
-- I dati che la controparte legge sul documento firmato (ragione sociale, P.IVA,
-- sede, IBAN, aliquota, termini). Si scrivono in Preventivi, stanno qui.
insert into istruzioni (chiave, titolo, testo) values
  ('studio', 'Dati dello Studio', '{"iva":22,"giorni":15,"preavviso":30}')
  on conflict (chiave) do nothing;

-- il canone del cliente e' quello del preventivo che ha accettato: si allinea
-- una volta sola, poi ci pensa il widget Preventivi a ogni «Ha accettato»
update prospects p set canone = q.mensile
  from preventivi q
  where q.prospect_id = p.id and q.stato = 'accettato' and q.mensile is not null
    and (p.canone is null or p.canone = 0);

select 'schema v32 applicato: dati dello Studio e canone dai preventivi' as esito;

-- ─── schema_v33.sql ────────────────────────────────────────────

-- ODYN CRM schema v33 (15 set 2026) — il diario si riconosce da una colonna, non da un'emoji
-- Regola 13 di Dre: niente emoji decorative nei testi. La domanda del diario
-- portava 📔 davanti solo perche' clara-risponde la riconoscesse.
alter table clara_messaggi add column if not exists diario boolean not null default false;
update clara_messaggi set diario = true where tipo = 'domanda' and testo like '📔%';
update clara_messaggi set testo = ltrim(replace(testo, '📔', '')) where testo like '📔%';

select 'schema v33 applicato: il diario ha la sua colonna' as esito;

-- ─── schema_v34.sql ────────────────────────────────────────────

-- v34 (15/9): la coda di Oggi non vive piu' nel browser.
-- «Da rispondere / Follow-up / Ricontatti / Rientri» erano spuntati in
-- localStorage: spuntavi dal telefono la mattina e sul Mac erano ancora da
-- fare (QA Dre, 15/9). Una verita' sola, come tutto il resto.

create table if not exists coda_fatte (
  owner uuid not null default uid_eff(),
  chiave text not null,
  giorno date not null default (now() at time zone 'Europe/Rome')::date,
  at timestamptz not null default now(),
  primary key (owner, chiave)
);

create index if not exists idx_coda_fatte_giorno on coda_fatte (owner, giorno);

alter table coda_fatte enable row level security;

drop policy if exists coda_fatte_mie on coda_fatte;
create policy coda_fatte_mie on coda_fatte
  for all to authenticated
  using (owner = uid_eff())
  with check (owner = uid_eff());

-- le spunte di ieri non servono a nessuno: si puliscono da sole
-- (la coda si ricalcola ogni giorno, le chiavi vecchie restano appese)
delete from coda_fatte where giorno < (now() at time zone 'Europe/Rome')::date - 7;

-- ─── schema_v35.sql ────────────────────────────────────────────

-- v35 (15/9): se hai una call con loro, l'azienda la vedi.
--
-- Carlo (QA del 14/9): «ho la call tecnica con Zafferano in agenda, apro la
-- scheda e mi dice che è fuori dal mio perimetro». Il perimetro parte dalla
-- call tecnica, ma la call conoscitiva la fa lui: fino a quel momento non
-- poteva nemmeno prepararsi.
--
-- Non si tocca vedo_prospect: si aggiunge una regola in piu'. In PostgreSQL
-- le policy dello stesso comando si sommano (una basta), quindi questa apre
-- senza rischiare di chiudere qualcosa che prima funzionava.

create or replace function ho_una_call(p_id uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from agenda a
    where a.prospect_id = p_id
      and (a.owner = uid_eff() or a.owner is null)
      and a.at > now() - interval '30 days'
  );
$$;

drop policy if exists "aziende: quelle con cui ho una call" on prospects;
create policy "aziende: quelle con cui ho una call" on prospects
  for select to authenticated using (ho_una_call(id));

drop policy if exists "storia: delle aziende con cui ho una call" on interactions;
create policy "storia: delle aziende con cui ho una call" on interactions
  for select to authenticated using (ho_una_call(prospect_id));

-- ─── schema_v36.sql ────────────────────────────────────────────

-- v36 (15/9): chi porta un'azienda la può mettere dentro, e la rivede.
--
-- Lorenzo lavora su LinkedIn con piu' profili: trova le aziende, ci parla, e
-- ha la sua pipeline. Fino a ieri creare un'azienda era solo dei ceo, quindi
-- il suo lavoro non entrava nel Workspace.
--
-- La regola: la metti dentro solo se ci scrivi il tuo nome in «chi segue»,
-- cosi' la rivedi (vedo_prospect guarda anche quel campo) e si sa di chi e'.
-- Non apre niente in lettura: si vede quello che si vedeva prima, piu' le
-- proprie.

drop policy if exists "aziende: crea e cancella il ceo" on prospects;
drop policy if exists "aziende: le aggiunge chi le segue" on prospects;
create policy "aziende: le aggiunge chi le segue" on prospects
  for insert to authenticated
  with check (
    sono_ceo()
    or (chi_segue is not null and nome_eff() is not null
        and chi_segue ilike '%' || split_part(nome_eff(), ' ', 1) || '%')
  );

comment on column prospects.campaign is 'Da dove arriva: campagna Smartlead, profilo LinkedIn, referral, evento';

-- ─── schema_v37.sql ────────────────────────────────────────────

-- v37 (15/9): la chat della squadra, dentro il Workspace.
--
-- Dre: «è come un WhatsApp interno: le persone si scrivono da una dashboard
-- all'altra e si passano documenti taggando il cliente, così quel documento
-- lo ritrovi sempre: sia nella sezione del cliente, con scritto chi l'ha
-- mandato, sia dentro il thread della chat».
--
-- Un messaggio può portarsi dietro due cose: un cliente (il tag) e un file
-- (che è già nei Documenti, nella cartella di quel cliente). Quindi la chat
-- non è un posto dove i file si perdono: è una strada in più per arrivarci.

create table if not exists chat (
  id bigserial primary key,
  at timestamptz not null default now(),
  da uuid not null default uid_eff(),
  -- null = a tutta la squadra (la stanza comune)
  a uuid,
  testo text,
  -- il tag: di quale cliente si sta parlando
  prospect_id uuid references prospects(id) on delete set null,
  -- il documento condiviso: sta nei Documenti, qui c'e' il riferimento
  file_id bigint references vault_file(id) on delete set null,
  letto boolean not null default false
);

create index if not exists idx_chat_giro on chat (a, da, at desc);
create index if not exists idx_chat_cliente on chat (prospect_id) where prospect_id is not null;

alter table chat enable row level security;

-- si legge quello che hai mandato tu, quello che hanno mandato a te, e la
-- stanza comune. Niente di piu': le conversazioni degli altri non si leggono.
drop policy if exists "chat: la mia" on chat;
create policy "chat: la mia" on chat
  for select to authenticated
  using (da = uid_eff() or a = uid_eff() or a is null);

drop policy if exists "chat: scrivo io" on chat;
create policy "chat: scrivo io" on chat
  for insert to authenticated
  with check (da = uid_eff());

-- «letto» lo segna chi ha ricevuto
drop policy if exists "chat: segno letto" on chat;
create policy "chat: segno letto" on chat
  for update to authenticated
  using (a = uid_eff() or (a is null and da <> uid_eff()))
  with check (true);

-- i nomi della squadra si leggono gia' (profili), serve per sapere con chi parli

-- ─── schema_v38.sql ────────────────────────────────────────────

-- v38 (15/9): gli accessi dei progetti di sito e landing.
--
-- Alex si blocca sempre sulla stessa cosa: aspetta hosting, dominio e
-- credenziali, e quella informazione oggi vive dentro le note libere, quindi
-- non si vede finche' non apri la riga. Qui NON ci vanno le credenziali:
-- solo dove stanno e a che punto siamo.
alter table progetti add column if not exists accessi_stato      text;
alter table progetti add column if not exists accessi_dove       text;
alter table progetti add column if not exists accessi_chiesti_il date;

alter table progetti drop constraint if exists progetti_accessi_stato_check;
alter table progetti add constraint progetti_accessi_stato_check
  check (accessi_stato is null or accessi_stato in ('mancano', 'chiesti', 'arrivati'));

comment on column progetti.accessi_dove is
  'Il posto, non la password: "cartella del cliente nei Documenti", "dal cliente".';

-- quello che oggi dice «aspettiamo accessi» dentro le note parte gia' segnato
update progetti set accessi_stato = 'mancano'
  where accessi_stato is null and note ilike '%access%';

-- ─── schema_v39.sql ────────────────────────────────────────────

-- COSA ABBIAMO IMPARATO (15/9/2026)
--
-- Dre: lo Studio vale quanto quello che impara, ma finora quello che si
-- impara su un progetto resta nella testa di chi l'ha fatto. Una riga sola,
-- chiesta nell'unico momento in cui uno ce l'ha in mente: quando segna il
-- progetto consegnato. Niente campo obbligatorio, niente form: si scrive o
-- si salta.
alter table progetti add column if not exists imparato text;
comment on column progetti.imparato is 'Cosa abbiamo imparato, scritto alla consegna: serve a contare i problemi che tornano, per settore.';

-- ─── schema_v40.sql ────────────────────────────────────────────

-- I FEEDBACK DELLA SQUADRA (15/9/2026)
--
-- Dre, il giorno in cui si aprono gli accessi: «lascia da qualche parte una
-- sezione feedback dove loro provano la piattaforma e scrivono cosa
-- cambiare, anche le cose minime, tipo bottoni o posizioni, o i desideri».
-- Sta dentro lo strumento e non su WhatsApp per la stessa ragione di tutto
-- il resto: su WhatsApp si perde.
--
-- Ognuno vede e scrive i suoi; chi guida lo Studio li vede tutti, perche'
-- e' chi decide cosa si cambia.
create table if not exists feedback (
  id bigserial primary key,
  user_id uuid not null default uid_eff() references auth.users(id) on delete cascade,
  at timestamptz not null default now(),
  testo text not null,
  dove text,                                   -- la sezione: oggi, pipeline, clienti...
  genere text not null default 'scomodo',      -- guasto | scomodo | desiderio
  stato text not null default 'nuovo',         -- nuovo | letto | fatto
  risposta text
);
create index if not exists feedback_user_idx on feedback (user_id, at desc);

alter table feedback enable row level security;

drop policy if exists "i miei feedback" on feedback;
create policy "i miei feedback" on feedback for all to authenticated
  using (user_id = uid_eff() or sono_ceo())
  with check (user_id = uid_eff() or sono_ceo());

-- chi guarda «come» un altro scrive a nome suo, come per tutto il resto
alter table feedback alter column user_id set default uid_eff();

-- ─── schema_v41.sql ────────────────────────────────────────────

-- QUANTO E' FRESCO QUELLO CHE VEDI (15/9/2026)
--
-- Dre: «in home metti la scritta dell'ultimo aggiornamento, così so almeno a
-- quanto è datato; l'obiettivo è portarlo a real time». La tabella delle
-- corse la leggono solo i ceo, e giustamente: dentro c'è il dettaglio di
-- ogni lavoro. Ma l'ORA dell'ultimo giro non è un segreto per nessuno, anzi:
-- e' quello che dice se ti puoi fidare di quello che stai guardando.
create or replace function ultimo_giro()
returns timestamptz
language sql
security definer
stable
set search_path = public
as $$
  select max(at) from corse where esito is distinct from 'errore';
$$;
grant execute on function ultimo_giro() to authenticated;

-- ─── schema_v42.sql ────────────────────────────────────────────

-- I DOCUMENTI CHE SI SCRIVONO DENTRO (16/9/2026)
--
-- Dre: «i preventivi voglio che siano un luogo dove vengo, vedo, e clicco un
-- + che mi porta in un posto tipo Word col template gia' li'; collego
-- l'azienda e i dati si riempiono; e un pulsante per farmi aiutare da Clara,
-- che ha i transcript di tutte le call e capisce com'e' la persona».
--
-- Il documento vive come blocchi (lo stesso formato che il motore del brand
-- sa stampare in PDF): cosi' quello che scrivi a schermo e quello che esce
-- stampato sono la stessa cosa, e Clara puo' scrivere dentro un blocco senza
-- toccare il resto.
create table if not exists documenti (
  id bigserial primary key,
  prospect_id uuid references prospects(id) on delete set null,
  modello text not null,                    -- proposta, condizioni, report, verbale
  titolo text not null default 'Senza titolo',
  doc jsonb not null,                       -- { tipo, copertina, blocchi, piede }
  stato text not null default 'bozza',      -- bozza | mandato | archiviato
  creato_il timestamptz not null default now(),
  creato_da uuid default auth.uid(),
  aggiornato_il timestamptz not null default now(),
  aggiornato_da uuid default auth.uid(),
  file text                                 -- dove sta il PDF nel vault, quando si genera
);
create index if not exists documenti_prospect_idx on documenti (prospect_id, aggiornato_il desc);

alter table documenti enable row level security;
drop policy if exists "documenti: chi vede l'azienda" on documenti;
create policy "documenti: chi vede l'azienda" on documenti for all to authenticated
  using (true) with check (true);

drop trigger if exists documenti_aggiornato on documenti;
create trigger documenti_aggiornato before update on documenti
  for each row execute function set_updated_at();

-- ─── schema_v43.sql ────────────────────────────────────────────

-- CLARA PREPARA LE CALL (16/9/2026)
--
-- Dre: «Clara deve essere come una che cerca di rendersi il piu' utile
-- possibile: se abbiamo una call, in modo proattivo fa ricerche sul cliente,
-- prepara cose che possono servire e le mette li'».
--
-- La preparazione vive sulla riga dell'agenda, non in una tabella nuova:
-- e' una proprieta' di quell'appuntamento e muore con lui.
alter table agenda add column if not exists preparazione text;
alter table agenda add column if not exists preparata_il timestamptz;
comment on column agenda.preparazione is 'Il punto della situazione che Clara scrive prima della call: chi sono, a che punto siamo, cosa chiedere.';

-- ─── schema_v44.sql ────────────────────────────────────────────

-- IL WORKSPACE VIVO (16/9/2026)
--
-- Dre: «lo voglio in realtime, tutti gli update nel workspace li voglio in
-- realtime, deve essere proprio vivo, come se arrivassero segnali e li
-- categorizza». Il primo pezzo e' questo: il database avvisa i browser
-- aperti quando una riga cambia, invece di aspettare che qualcuno ricarichi.
--
-- Solo le tabelle che si guardano mentre si lavora. Le regole di accesso
-- restano quelle di sempre: chi non puo' leggere una riga non riceve
-- nemmeno l'avviso.
alter publication supabase_realtime add table proposte;
alter publication supabase_realtime add table task;
alter publication supabase_realtime add table agenda;
alter publication supabase_realtime add table chat;
alter publication supabase_realtime add table clara_messaggi;
alter publication supabase_realtime add table prospects;
alter publication supabase_realtime add table documenti;
alter publication supabase_realtime add table feedback;
alter publication supabase_realtime add table coda_fatte;

-- ─── schema_v45.sql ────────────────────────────────────────────

-- LE AZIONI DI CLARA (16/9/2026)
--
-- Dre: «quando faccio una cosa, tipo inviare un preventivo, lei si mette in
-- automatico un promemoria di tot giorni e controlla se sono arrivati i
-- soldi; se passa una settimana e non sono arrivati me lo ricorda. Vorrei
-- piu' azioni: pensa alle cose che spesso si dimenticano».
--
-- Ogni azione e' una regola scritta qui: si accende, si spegne, si cambiano
-- i giorni. Il codice che la esegue sta in scripts/azioni.py. La regola sta
-- nel database e non nel codice per la stessa ragione di sempre: chi decide
-- deve poterla cambiare senza chiamare nessuno.
create table if not exists azioni (
  chiave text primary key,
  nome text not null,
  cosa text not null,               -- cosa fa, detto come lo direbbe una persona
  giorni int not null default 7,    -- dopo quanto guarda
  attiva boolean not null default true,
  ordine int not null default 100,
  ultima_corsa timestamptz,
  ultimo_esito text
);

alter table azioni enable row level security;
drop policy if exists "le azioni: le vedono tutti, le cambia il ceo" on azioni;
create policy "le azioni: le vedono tutti, le cambia il ceo" on azioni
  for all to authenticated using (true) with check (sono_ceo());

-- il promemoria che nasce da un'azione: si riconosce, e non si ripete
alter table proposte add column if not exists ref text;
create unique index if not exists proposte_ref_unica on proposte (ref) where ref is not null;

-- ─── schema_v46.sql ────────────────────────────────────────────

-- LE NOVITA' E IL VOTO (17/9/2026)
--
-- Dre: «quando ci sono modifiche, quando rientrano appare un banner tipo
-- quelli delle nuove feature, con le stelle e "lascia un feedback": un voto
-- onesto sull'utilita' della feature». Il voto e' un feedback come gli
-- altri (stessa tabella, stesse regole di accesso), con due colonne in piu':
-- quante stelle, e a quale novita' si riferisce (la chiave in src/lib/novita.ts).
alter table feedback add column if not exists voto int check (voto between 1 and 5);
alter table feedback add column if not exists novita text;
create index if not exists feedback_novita_idx on feedback (novita) where novita is not null;

-- ─── schema_v47.sql ────────────────────────────────────────────

-- IL PULL PRIMA DELLA CAMPAGNA (21/9/2026)
--
-- Dre: «prima si raccoglie, poi si risponde. Un giro solo: le informazioni
-- si raccolgono bene una volta, stanno da qualche parte in ordine, e quando
-- uno risponde l'analisi parte da quelle, senza rifare la ricerca da zero».
-- E: «evitare proprio di contattare quelli che non sono in target».
--
-- Tre tabelle, tutte interne (le leggono i ceo e il runner):
--   lead_lista   i lead di una lista prima che entrino in campagna, con la
--                lista di provenienza (cecchino = con nome, strascico = senza).
--                Le liste NON si mischiano: «dopo si mischiano, succede casino».
--   raccolta     una riga per dominio: cosa dice il Transparency Center (fa
--                ads), la scheda Maps (recensioni, coi testi), il sito. Solo
--                dati grezzi, nessun ragionamento: quello viene dopo.
--   piattaforme  i crediti dei servizi esterni, con la soglia sotto cui Clara
--                avvisa in chat. «Figo che mi avvisi Clara.»

create table if not exists lead_lista (
  id          bigserial primary key,
  lista       text not null,                 -- cecchino | strascico
  email       text not null,
  first_name  text,
  website     text,
  dominio     text not null,                 -- dal sito, ripulito: e' la chiave verso raccolta
  azienda     text,
  icebreaker  text,
  fa_ads      boolean,                       -- copiato da raccolta quando il pull e' fatto
  fit         text,                          -- SI | PARZIALE | NO, quando il fit e' girato
  fit_motivo  text,
  campagna_id bigint,                        -- la campagna Smartlead in cui e' finito
  caricato_il timestamptz not null default now(),
  unique (lista, email)
);
create index if not exists idx_lead_lista_dominio on lead_lista(dominio);
create index if not exists idx_lead_lista_lista on lead_lista(lista, fa_ads, fit);

create table if not exists raccolta (
  dominio          text primary key,
  azienda          text,
  fa_ads           boolean,
  annunci          int,
  giorni_ads       int,
  inserzionista    text,
  maps_trovato     boolean,
  recensioni       int,
  voto             numeric,
  tipo_maps        text,
  recensioni_testi jsonb,                    -- [{voto, testo, quando}] fino a 20
  sito_letto       boolean,
  sito_testo       text,                     -- home + servizi + prezzi, testo pulito, max 12k
  errore           text,
  crediti_usati    int not null default 0,
  raccolto_il      timestamptz
);
create index if not exists idx_raccolta_da_fare on raccolta(raccolto_il) where raccolto_il is null;

create table if not exists piattaforme (
  nome           text primary key,           -- searchapi, openai, smartlead...
  unita          text,                        -- crediti, euro
  saldo          numeric,
  totale         numeric,
  soglia         numeric,                     -- sotto questa Clara avvisa
  avvisato_il    timestamptz,                 -- per non avvisare ogni sei ore
  aggiornato_il  timestamptz,
  nota           text
);

alter table lead_lista  enable row level security;
alter table raccolta    enable row level security;
alter table piattaforme enable row level security;
drop policy if exists "lead_lista: i ceo" on lead_lista;
create policy "lead_lista: i ceo" on lead_lista for all to authenticated using (sono_ceo()) with check (sono_ceo());
drop policy if exists "raccolta: i ceo" on raccolta;
create policy "raccolta: i ceo" on raccolta for all to authenticated using (sono_ceo()) with check (sono_ceo());
drop policy if exists "piattaforme: i ceo" on piattaforme;
create policy "piattaforme: i ceo" on piattaforme for all to authenticated using (sono_ceo()) with check (sono_ceo());

insert into piattaforme (nome, unita, soglia, nota) values
  ('searchapi', 'crediti', 5000, 'Transparency Center, Maps, recensioni. Si ricarica su searchapi.io')
on conflict (nome) do nothing;

-- le due operazioni del direttore
insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ordine) values
  ('pull',    'Pull delle liste', 'Per ogni dominio delle liste in attesa: fa ads, scheda Maps con le recensioni, il sito. A lotti, finche'' non e'' finito.', 'pull.py --max 1100', 20, 35),
  ('crediti', 'Crediti delle piattaforme', 'Legge il saldo dei servizi esterni; sotto la soglia Clara avvisa in chat.', 'crediti.py', 360, 90)
on conflict (chiave) do update set cosa = excluded.cosa, comando = excluded.comando;

select 'schema v47 applicato: lead_lista, raccolta, piattaforme, operazioni pull e crediti' as esito;

-- ─── schema_v48.sql ────────────────────────────────────────────

-- v48 (21/9/2026): il cron di GitHub su questo repo non parte mai (direttore.yml
-- ha un cron ogni 20 minuti e in tre settimane non ha fatto una corsa a orologio:
-- tutte le corse sono workflow_dispatch, cioe' pg_cron e campanelli). Il pull
-- delle liste aveva lo stesso cron orario e non e' mai partito da solo.
-- Quindi anche il pull lo sveglia il database, come il direttore.

create or replace function chiama_pull()
returns void language plpgsql security definer set search_path = public as $$
declare
  tok text;
begin
  select decrypted_secret into tok from vault.decrypted_secrets where name = 'github_direttore';
  if tok is null then
    raise notice 'manca il token github_direttore nel Vault';
    return;
  end if;
  perform net.http_post(
    url := 'https://api.github.com/repos/studiogalilei/clara-dashboard/actions/workflows/pull.yml/dispatches',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || tok,
      'Accept', 'application/vnd.github+json',
      'User-Agent', 'clara-dashboard',
      'Content-Type', 'application/json'),
    body := jsonb_build_object('ref', 'main')
  );
end $$;

-- ogni ora al minuto 5: se un giro e' in corso, GitHub tiene il nuovo in coda
-- (concurrency group 'pull'); quando la raccolta e' completa il giro esce in
-- pochi secondi e non costa niente.
select cron.unschedule(jobid) from cron.job where jobname = 'pull';
select cron.schedule('pull', '5 * * * *', $$select chiama_pull()$$);

-- ─── schema_v49.sql ────────────────────────────────────────────

-- v49 (22/9/2026): L'IMPRONTA DIGITALE.
--
-- Dre: «se fanno pubblicità non è positivo di per sé: la domanda diventa se la
-- fanno bene o male, e lì si va a penetrare». Prima sapevamo solo fa_ads sì/no,
-- che non dice niente sull'angolo da usare nella mail.
--
-- Ora si misura, per ogni dominio: chi paga gli annunci (e se quel pagante
-- compare su più aziende, cioè è un rivenditore), e quali tag ha sul sito, che
-- dicono se misura quello che spende. Sono gli stessi strumenti che Carlo
-- installa ai clienti nuovi: Clarity, Analytics, Tag Manager, Google Ads.
--
-- Il limite è scritto nel dato stesso: misura='forse' quando c'è Tag Manager,
-- perché lì dentro il tag conversioni può esserci senza comparire nell'HTML
-- (misurato: solo il 13% lo mostra nel codice, il 54% ha Tag Manager).

alter table raccolta add column if not exists angolo         text;
alter table raccolta add column if not exists angolo_perche  text;
alter table raccolta add column if not exists misura         text;
alter table raccolta add column if not exists sito_letto_tag boolean;
alter table raccolta add column if not exists tag_google_ads  boolean;
alter table raccolta add column if not exists tag_analytics   boolean;
alter table raccolta add column if not exists tag_tag_manager boolean;
alter table raccolta add column if not exists tag_clarity     boolean;
alter table raccolta add column if not exists tag_meta_pixel  boolean;

-- i quattro angoli di Dre: non_fa_ads | fermo | investe | rivenditore
comment on column raccolta.angolo is
  'La situazione pubblicitaria in una parola, da cui dipende l''angolo della mail';
comment on column raccolta.misura is
  'si = tag conversioni visto | forse = c''e'' Tag Manager, puo'' stare dentro | no = nessuno dei due | non_letto';

create index if not exists idx_raccolta_da_impronta on raccolta(angolo) where angolo is null;
create index if not exists idx_raccolta_angolo on raccolta(angolo, misura);

-- ─── schema_v50.sql ────────────────────────────────────────────

-- CLARA MANDA (24/9/2026)
--
-- Dre: «fai che Clara invia i messaggi: io clicco Approva e lei invia, avendo
-- a disposizione tutto il necessario per farlo bene». Fino a oggi Clara
-- preparava e Dre copiava e mandava da Smartlead. Da oggi la bozza approvata
-- passa in stato «approvata», l'operazione `manda` (scripts/manda.py) la
-- spedisce dal thread giusto di Smartlead (stessa casella, stessa
-- conversazione), e la proposta diventa «fatta» con l'ora dell'invio.
-- «in_invio» e' il lucchetto: una bozza non parte due volte.
alter table proposte drop constraint if exists proposte_stato_check;
alter table proposte add constraint proposte_stato_check
  check (stato in ('aperta', 'approvata', 'in_invio', 'si', 'no', 'fatta'));
create index if not exists idx_proposte_approvate on proposte (at) where stato in ('approvata', 'in_invio');

insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ordine) values
  ('manda', 'Clara manda le risposte approvate', 'Le bozze che Dre ha approvato partono da Smartlead, nel thread della persona, con la firma della casella.', 'python3 scripts/manda.py', 5, 3)
on conflict (chiave) do update set cosa = excluded.cosa, comando = excluded.comando, cadenza_minuti = excluded.cadenza_minuti;

-- ─── schema_v51.sql ────────────────────────────────────────────

-- LE SETTE MIGLIORIE ACCETTATE DA DRE (24/9/2026)
-- avvisi: la notifica arriva a chi deve fare la task, non solo al ceo.
-- lezioni: una volta a settimana Clara legge le correzioni di Dre alle bozze
--          (bozza_originale vs bozza approvata) e propone tre regole.
-- arricchisci: Clara riempie sito, settore e «chi sono» da quello che sa (fit,
--          raccolta, una ricerca precisa); a Dre restano referente, ruolo, telefono.
-- clara_misure: tre numeri per sapere se Clara migliora.
alter table task add column if not exists avvisata_il timestamptz;

insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ordine, attiva) values
  ('avvisi', 'Le notifiche a chi deve fare', 'Una task nuova arriva sul telefono di chi la deve fare, con la scadenza.', 'python3 scripts/avvisi.py', 5, 4, false),
  ('lezioni', 'Le lezioni dalle correzioni', 'Ogni settimana Clara confronta le sue bozze con quelle che Dre ha mandato e propone tre regole in Posta.', 'python3 scripts/lezioni.py', 10080, 30, false),
  ('arricchisci', 'Clara riempie quello che sa', 'Sito, settore e «chi sono» dalle fonti che ha (fit, raccolta, ricerca precisa). Referente, ruolo e telefono restano a chi ha parlato con la persona.', 'python3 scripts/arricchisci.py', 60, 9, false)
on conflict (chiave) do update set cosa = excluded.cosa, comando = excluded.comando, cadenza_minuti = excluded.cadenza_minuti;

-- MISURARE CLARA (da Galileo: prima si misura, poi si migliora)
create or replace function clara_misure()
returns jsonb language sql stable security definer set search_path = public as $$
  with b as (
    select pr.id, pr.at, pr.stato, pr.azione, p.last_reply_at
    from proposte pr left join prospects p on p.id = pr.prospect_id
    where pr.tipo in ('risposta', 'umano') and pr.azione ? 'bozza' and pr.at > now() - interval '30 days'
  )
  select jsonb_build_object(
    'bozze', (select count(*) from b),
    'minuti_mediani', (select round(percentile_cont(0.5) within group (order by extract(epoch from (at - last_reply_at)) / 60))
                       from b where last_reply_at is not null and at > last_reply_at and at - last_reply_at < interval '3 days'),
    'mandate', (select count(*) from b where stato = 'fatta'),
    'senza_correzioni', (select count(*) from b where stato = 'fatta' and azione ? 'bozza_originale' and azione->>'bozza_originale' = azione->>'bozza'),
    'con_correzioni', (select count(*) from b where stato = 'fatta' and azione ? 'bozza_originale' and azione->>'bozza_originale' <> azione->>'bozza'),
    'rifiutate', (select count(*) from b where stato = 'no')
  );
$$;
grant execute on function clara_misure() to authenticated;

-- ─── schema_v52.sql ────────────────────────────────────────────

-- LA VISIBILITA' PIU' LEGGERA (24/9/2026). Alex, 17/9: «Oggi è molto lenta
-- (15-20 secondi)». Il perimetro chiamava sono_ceo() e nome_eff() UNA VOLTA
-- PER RIGA (13.000 righe, tre sottoquery ognuna). Scritte come (select ...)
-- Postgres le valuta una volta per query. Stessa regola, stesso risultato.
create or replace function vedo_prospect(p_fuori boolean, p_stage text, p_chi_segue text) returns boolean
language sql stable security definer set search_path = public as $$
  select (select sono_ceo())
      or (coalesce(p_fuori, false) and p_stage in ('tecnica', 'avvio', 'prova', 'cliente'))
      or (p_chi_segue is not null and (select nome_eff()) is not null
          and p_chi_segue ilike '%' || split_part((select nome_eff()), ' ', 1) || '%');
$$;
create or replace function ho_una_call(p_id uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from agenda a
    where a.prospect_id = p_id
      and (a.owner = (select uid_eff()) or a.owner is null)
      and a.at > now() - interval '30 days'
  );
$$;
create index if not exists idx_agenda_prospect_at on agenda (prospect_id, at desc);

-- ─── schema_v53.sql ────────────────────────────────────────────

-- IL PERIMETRO SENZA FUNZIONI PER RIGA (24/9/2026). Le policy su prospects
-- chiamavano una funzione security definer per ognuna delle 13.000 righe (non
-- si puo' inlinare): 400 ms a query, moltiplicati per le 18 query di Oggi.
-- Scritte inline, il ceo passa con un InitPlan e gli altri usano gli indici.
drop policy if exists "aziende nel perimetro" on prospects;
create policy "aziende nel perimetro" on prospects for select to authenticated using (
  (select sono_ceo())
  or (coalesce(fuori, false) and pipeline_stage in ('tecnica', 'avvio', 'prova', 'cliente'))
  or (chi_segue is not null and (select nome_eff()) is not null
      and chi_segue ilike '%' || split_part((select nome_eff()), ' ', 1) || '%')
);
-- ATTENZIONE: la policy «quelle con cui ho una call» NON si scrive inline:
-- agenda ha a sua volta una policy che guarda prospects, e Postgres va in
-- ricorsione infinita (successo il 24/9 per due minuti). Resta ho_una_call(),
-- che e' security definer e quindi non riapre le policy.
drop policy if exists "aziende: quelle con cui ho una call" on prospects;
create policy "aziende: quelle con cui ho una call" on prospects for select to authenticated using (ho_una_call(id));
drop policy if exists "aziende: scrive chi le vede" on prospects;
create policy "aziende: scrive chi le vede" on prospects for update to authenticated using (
  (select sono_ceo())
  or (coalesce(fuori, false) and pipeline_stage in ('tecnica', 'avvio', 'prova', 'cliente'))
  or (chi_segue is not null and (select nome_eff()) is not null
      and chi_segue ilike '%' || split_part((select nome_eff()), ' ', 1) || '%')
);
create index if not exists idx_prospects_fuori_stage on prospects (fuori, pipeline_stage);

-- ─── schema_v54.sql ────────────────────────────────────────────

-- IL FOLLOW-UP COME FLUSSO (24/9/2026): ogni mattina Clara mette in Posta i
-- FOLLOW UP 1 dovuti (analisi ricevuta da 5+ giorni, silenzio), massimo 10.
insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ora_preferita, ordine, attiva) values
  ('followup', 'I follow-up dopo l''analisi', 'Chi ha ricevuto l''analisi da 5 giorni e non ha più scritto: FOLLOW UP 1 in Posta, parola per parola, da approvare uno alla volta.', 'python3 scripts/followup.py', 1440, '08:30', 3, false)
on conflict (chiave) do update set cosa = excluded.cosa, comando = excluded.comando, cadenza_minuti = excluded.cadenza_minuti, ora_preferita = excluded.ora_preferita;

-- ─── schema_v55.sql ────────────────────────────────────────────

-- LA CLASSIFICAZIONE CON LE PAROLE DI DRE (25/9/2026): «positivo, negativo,
-- parziale, richiesta di rimozione, persona sbagliata, nervoso, fuori ufficio».
-- Due valori nuovi: persona_sbagliata (ci ha risposto chi non decide: si cerca
-- il referente) e nervoso (infastidito: si lascia stare, come un no).
alter table prospects drop constraint if exists prospects_classificazione_check;
alter table prospects add constraint prospects_classificazione_check
  check (classificazione in ('da_classificare','positivo','tiepido','negativo','ooo','rinvio','fuori_target','soppresso','persona_sbagliata','nervoso'));

-- ─── schema_v56.sql ────────────────────────────────────────────

-- MAI UNA BOZZA A UN CLIENTE O A CHI E' IN PIPELINE (25/9/2026, caso Zafferano).
-- Una bozza scritta il 7/9 alle 15:57 e' rimasta aperta mentre alle 17:22 Dre lo
-- spostava in Prova: nessuno la chiudeva, e sarebbe partita. Da qui in poi la
-- barriera sta nel database: una proposta «risposta» o «umano» aperta o
-- approvata NON puo' esistere per un'azienda in pipeline (fuori), cliente,
-- persa, o con «niente follow-up». Il database la rifiuta, chiunque la scriva.
create or replace function proposta_ammessa() returns trigger
language plpgsql security definer set search_path = public as $$
declare p record;
begin
  if new.tipo in ('risposta', 'umano') and new.stato in ('aperta', 'approvata', 'in_invio') and new.prospect_id is not null then
    select fuori, stage, pipeline_stage, no_followup, classificazione into p from prospects where id = new.prospect_id;
    if p.fuori or p.stage in ('cliente', 'perso') or p.pipeline_stage in ('cliente', 'perso')
       or coalesce(p.no_followup, false) or p.classificazione in ('soppresso', 'nervoso') then
      raise exception 'proposta rifiutata: l''azienda % e'' in pipeline, cliente, persa, senza follow-up o bloccata (regola del 25/9)', new.prospect_id;
    end if;
  end if;
  return new;
end $$;
drop trigger if exists trg_proposta_ammessa on proposte;
create trigger trg_proposta_ammessa before insert or update on proposte
  for each row execute function proposta_ammessa();

-- ─── schema_v57.sql ────────────────────────────────────────────

-- IL REGISTRO (25/9/2026, da Galileo: «log append-only, niente flag derivati»).
-- Dre: «come è possibile?» deve avere sempre una risposta. Ogni cambio dei campi
-- che decidono cosa Clara fa (stato, classificazione, pipeline, follow-up,
-- indirizzo, analisi) e ogni cambio di stato di una proposta finisce qui, con
-- CHI l'ha fatto: lo script (header X-Clara-Script che stanza.sb aggiunge) o
-- l'utente del workspace (auth.uid()). Solo inserimenti, mai modifiche.
create table if not exists registro (
  id        bigint generated always as identity primary key,
  at        timestamptz not null default now(),
  tabella   text not null,
  riga      text not null,
  campo     text not null,
  prima     text,
  dopo      text,
  chi       text
);
create index if not exists idx_registro_riga on registro (tabella, riga, at desc);
alter table registro enable row level security;
drop policy if exists "registro: lo leggono i ceo" on registro;
create policy "registro: lo leggono i ceo" on registro for select to authenticated using (sono_ceo());

create or replace function chi_scrive() returns text language plpgsql stable as $$
declare h text; u text;
begin
  begin
    h := current_setting('request.headers', true)::json ->> 'x-clara-script';
  exception when others then h := null;
  end;
  if h is not null and h <> '' then return 'clara:' || h; end if;
  begin
    u := auth.uid()::text;
  exception when others then u := null;
  end;
  if u is not null then return 'workspace:' || u; end if;
  return coalesce(current_setting('request.jwt.claim.role', true), current_user);
end $$;

create or replace function registra_prospects() returns trigger language plpgsql security definer set search_path = public as $$
declare c text; prima text; dopo text;
begin
  foreach c in array array['classificazione','awaiting_us','fuori','pipeline_stage','stage','no_followup','next_action','next_action_date','email','email_alt','analysis_sent','analysis_pdf','chi_segue','lost_reason'] loop
    execute format('select ($1).%I::text, ($2).%I::text', c, c) into prima, dopo using old, new;
    if prima is distinct from dopo then
      insert into registro (tabella, riga, campo, prima, dopo, chi) values ('prospects', new.id::text, c, left(prima, 300), left(dopo, 300), chi_scrive());
    end if;
  end loop;
  return new;
end $$;
drop trigger if exists trg_registra_prospects on prospects;
create trigger trg_registra_prospects after update on prospects for each row execute function registra_prospects();

create or replace function registra_proposte() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'INSERT' then
    insert into registro (tabella, riga, campo, prima, dopo, chi) values ('proposte', new.id::text, 'stato', null, new.stato || ' (' || new.tipo || ')', chi_scrive());
  elsif old.stato is distinct from new.stato then
    insert into registro (tabella, riga, campo, prima, dopo, chi) values ('proposte', new.id::text, 'stato', old.stato, new.stato, chi_scrive());
  end if;
  return new;
end $$;
drop trigger if exists trg_registra_proposte on proposte;
create trigger trg_registra_proposte after insert or update on proposte for each row execute function registra_proposte();

-- ─── schema_v58.sql ────────────────────────────────────────────

-- NESSUNA BOZZA SENZA LETTURA (25/9/2026, dopo la ripresa sbagliata: 4 mail su 10).
-- Dre: «qualsiasi cosa hai fatto per accorgertene e' quello che bisogna fare
-- sempre». Quello che ho fatto: leggere l'ultima mail loro accanto al testo
-- nostro. Da oggi una bozza «risposta» nasce SOLO con dentro la lettura:
-- la citazione dell'ultima mail loro e il verdetto di coerenza «loro/noi».
-- Il database la rifiuta altrimenti, chiunque la scriva.
-- La coda: chi va ricontattato (follow-up, ripresa, dopo le ferie) non riceve
-- piu' un testo da template: viene messo in coda, e il motore delle bozze lo
-- legge e scrive. Un motore solo.
alter table prospects add column if not exists coda text;
alter table prospects add column if not exists coda_il timestamptz;

create or replace function proposta_ammessa() returns trigger
language plpgsql security definer set search_path = public as $$
declare p record;
begin
  if new.tipo in ('risposta', 'umano') and new.stato in ('aperta', 'approvata', 'in_invio') and new.prospect_id is not null then
    select fuori, stage, pipeline_stage, no_followup, classificazione into p from prospects where id = new.prospect_id;
    if p.fuori or p.stage in ('cliente', 'perso') or p.pipeline_stage in ('cliente', 'perso')
       or coalesce(p.no_followup, false) or p.classificazione in ('soppresso', 'nervoso') then
      raise exception 'proposta rifiutata: l''azienda % e'' in pipeline, cliente, persa, senza follow-up o bloccata (regola del 25/9)', new.prospect_id;
    end if;
  end if;
  -- la lettura obbligatoria (solo alla nascita: le bozze vecchie cambiano stato senza)
  if tg_op = 'INSERT' and new.tipo = 'risposta' and new.azione ? 'bozza' then
    if coalesce(new.azione->'lettura'->>'ultima_loro', '') = '' then
      raise exception 'bozza rifiutata: manca la lettura dell''ultima mail (azione.lettura.ultima_loro). Nessuna bozza senza lettura (25/9)';
    end if;
    if coalesce(new.azione->'lettura'->>'coerenza', '') <> 'COERENTE' then
      raise exception 'bozza rifiutata: la coerenza loro/noi non e'' COERENTE (%). Nessuna bozza senza lettura (25/9)', coalesce(new.azione->'lettura'->>'coerenza', 'assente');
    end if;
  end if;
  return new;
end $$;

-- ─── schema_v59.sql ────────────────────────────────────────────

-- IL PREZZO SUGGERITO (Dre, 26/9/2026): «la fee segue la capacita' di spesa del
-- cliente e resta sotto il valore che gli portiamo. Il sistema propone, Dre decide».
-- Le modifiche concordate al dossier: si parte dalla domanda Google (volumi x CPC,
-- gia' precalcolati), il bilancio corregge; si calcola solo in pipeline; e' una
-- fascia, non un numero; tarato sui preventivi chiusi. Solo interno: mai in una mail.
create table if not exists parametri (
  chiave text primary key,
  valore jsonb not null,
  cosa text,
  aggiornato_il timestamptz default now()
);
alter table parametri enable row level security;
drop policy if exists "parametri: leggono tutti" on parametri;
create policy "parametri: leggono tutti" on parametri for select to authenticated using (true);
drop policy if exists "parametri: scrivono i ceo" on parametri;
create policy "parametri: scrivono i ceo" on parametri for all to authenticated
  using (exists (select 1 from profili where id = auth.uid() and ruolo = 'ceo'))
  with check (exists (select 1 from profili where id = auth.uid() and ruolo = 'ceo'));

insert into parametri (chiave, valore, cosa) values
  ('prezzo.base',          '1400',  'il lavoro fisso al mese (gestione, report, call): la base del canone, come nel calcolo «Quanto chiedere»'),
  ('prezzo.soglia',        '5000',  'sotto questa spesa Ads mensile il lavoro e'' sempre quello: il canone resta la base'),
  ('prezzo.quota',         '0.10',  'sopra la soglia il canone cresce di questa quota della spesa Ads gestita'),
  ('prezzo.floor',         '1200',  'il canone minimo sotto cui lo Studio non lavora'),
  ('prezzo.fascia',        '0.15',  'ampiezza della fascia intorno al punto (±15%)'),
  ('prezzo.quota_cattura', '0.03',  'IPOTESI: quota dei clic della provincia che una PMI puo'' comprare (spesa Ads sostenibile = domanda x CPC x quota)'),
  ('prezzo.conversione',   '0.02',  'IPOTESI: clic che diventano clienti, per il tetto di valore'),
  ('prezzo.tetto_quota',   '0.3333','la fee non supera un terzo del margine extra che portiamo'),
  ('prezzo.scaglioni',     '[[1000000,0.02],[3000000,0.015],[10000000,0.01],[30000000,0.008],[50000000,0.006],[null,0.005]]',
                                    'IPOTESI, budget marketing a scaglioni sul fatturato (limite superiore della fetta, % sulla fetta). Tarati sulla PMI italiana, non sul 5% del dossier'),
  ('prezzo.quota_agenzia', '0.25',  'IPOTESI: del budget marketing, la parte che va all''agenzia (il resto e'' spesa pubblicitaria)'),
  ('prezzo.margine',       '[[0,0.5],[0.03,0.7],[0.08,1.0],[0.15,1.2],[null,1.4]]',
                                    'IPOTESI: moltiplicatore per margine netto (limite superiore della fascia, moltiplicatore); in perdita = 0.5 e flag'),
  ('prezzo.cluster',       '{"A":1.1,"B":0.9}', 'IPOTESI: gia'' su Google Ads = A (budget esistente), non ancora = B (serve educazione)'),
  ('prezzo.taratura',      '{"preventivi_minimi":10,"accettati":0,"rifiutati":0}', 'dopo 10 preventivi reali si rivedono i parametri su accettati contro rifiutati')
on conflict (chiave) do nothing;

-- i numeri di bilancio li scrive Dre nella scheda quando li ha (o li porta un arricchimento futuro): enriched.bilancio
insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ordine, attiva) values
  ('prezzo', 'Il prezzo suggerito', 'Per chi e'' in pipeline: la fascia di canone dalla domanda Google della sua zona, corretta dal bilancio se c''e''. Solo interna, mai in una mail.', 'python3 scripts/prezzo.py', 60, 12, true)
on conflict (chiave) do update set cosa = excluded.cosa, comando = excluded.comando, cadenza_minuti = excluded.cadenza_minuti;

-- ─── schema_v60.sql ────────────────────────────────────────────

-- IL REPARTO (Dre, 26/9/2026): ognuno entra nel colore del suo reparto.
-- «in home sia albero bianco con fondo colore di colore reparto», e all'ingresso
-- la schermata piena col nome del reparto sotto, come fa Smartlead.
-- Direzione (Dre, Giacomo, Lorenzo) navy · Marketing (Salvatore, Carlo, Alex) rosso
-- Software (Okay e i tecnici) verde · AI blu acceso.
alter table profili add column if not exists reparto text;
alter table profili drop constraint if exists profili_reparto_check;
alter table profili add constraint profili_reparto_check
  check (reparto is null or reparto in ('direzione', 'marketing', 'software', 'ai'));

update profili set reparto = 'direzione' where nome in ('Dramane', 'Giacomo Facchin', 'Lorenzo Fornasier');
update profili set reparto = 'marketing'  where nome in ('Salvatore', 'Carlo Durigon', 'Alex');
update profili set reparto = 'software'   where nome in ('Okay Sözen');

-- il reparto viaggia con il profilo: l'app lo legge a ogni ingresso
create or replace function chi_sono() returns json language sql stable security definer set search_path = public as $$
  select json_build_object(
    'uid', uid_eff(),
    'nome', nome_eff(),
    'ruolo', coalesce((select ruolo from profili where id = uid_eff()), 'coordinamento'),
    'reparto', (select reparto from profili where id = uid_eff()),
    'concessi', coalesce((select json_agg(widget) from widget_accessi where user_id = uid_eff() and stato = 'approvato'), '[]'::json),
    'pod', coalesce((select json_agg(json_build_object('id', pr.id, 'nome', pr.nome, 'ruolo', pr.ruolo)) from pod po join profili pr on pr.id = po.membro_id where po.manager_id = uid_eff()), '[]'::json),
    'vista', (select json_build_object('id', v.come_id, 'nome', pr.nome) from vista_come v join profili pr on pr.id = v.come_id where v.ceo_id = auth.uid())
  );
$$;

-- ─── schema_v61.sql ────────────────────────────────────────────

-- LA REGOLA ZAFFERANO COLPIVA TROPPO LARGO (bug trovato il 26/9 col check).
-- Il 25/9 avevamo vietato ogni proposta «risposta» o «umano» per chi e' cliente,
-- in pipeline, perso o bloccato: giusto per le MAIL, sbagliato per i promemoria.
-- Conseguenza vera: `azioni.py` non riusciva a scrivere niente («il preventivo e'
-- fermo da 15 giorni», «la prova sta per finire», «manca il canone»), perche'
-- quei promemoria parlano proprio di clienti e di aziende in pipeline. Da mesi
-- nessuno veniva avvisato di niente, in silenzio.
--
-- La regola vera e' un'altra, ed e' quella che Dre ha detto: a un cliente non si
-- MANDA una mail di outbound. Quindi si blocca solo cio' che contiene un testo da
-- mandare (azione.bozza). Una domanda o un promemoria interno passa sempre.
create or replace function proposta_ammessa() returns trigger
language plpgsql security definer set search_path = public as $$
declare p record;
begin
  -- una proposta che porta un TESTO DA MANDARE non nasce per chi non e' contattabile
  if new.azione ? 'bozza' and new.tipo in ('risposta', 'umano')
     and new.stato in ('aperta', 'approvata', 'in_invio') and new.prospect_id is not null then
    select fuori, stage, pipeline_stage, no_followup, classificazione into p from prospects where id = new.prospect_id;
    if p.fuori or p.stage in ('cliente', 'perso') or p.pipeline_stage in ('cliente', 'perso')
       or coalesce(p.no_followup, false) or p.classificazione in ('soppresso', 'nervoso') then
      raise exception 'proposta rifiutata: l''azienda % e'' in pipeline, cliente, persa, senza follow-up o bloccata (regola del 25/9)', new.prospect_id;
    end if;
  end if;
  -- nessuna bozza senza lettura (25/9)
  if tg_op = 'INSERT' and new.tipo = 'risposta' and new.azione ? 'bozza' then
    if coalesce(new.azione->'lettura'->>'ultima_loro', '') = '' then
      raise exception 'bozza rifiutata: manca la lettura dell''ultima mail (azione.lettura.ultima_loro). Nessuna bozza senza lettura (25/9)';
    end if;
    if coalesce(new.azione->'lettura'->>'coerenza', '') <> 'COERENTE' then
      raise exception 'bozza rifiutata: la coerenza loro/noi non e'' COERENTE (%). Nessuna bozza senza lettura (25/9)', coalesce(new.azione->'lettura'->>'coerenza', 'assente');
    end if;
  end if;
  return new;
end $$;

-- ─── schema_v62.sql ────────────────────────────────────────────

-- L'ARCHIVIO DELLA PIPELINE (Dre, 29/9/2026)
--
-- «Dobbiamo impostare un sistema per archiviare i lead, perche' la pipeline non
-- puo' essere sempre piena... oppure un modo per far si' che le cose importanti
-- arrivino in alto e le meno importanti piu' in basso.»
--
-- Misurato il 29/9: 83 aziende in pipeline, 72 ferme da piu' di un mese, e il
-- lavoro vero di quel giorno erano 11 righe. Dentro le 72: 57 «no», il piu'
-- vecchio di 127 giorni, e 13 positivi fermi che nessuno guardava piu' perche'
-- erano invisibili in mezzo ai rifiuti.
--
-- Due pezzi, non uno:
--   1. l'ORDINE per urgenza, a schermo (src/lib/urgenza.ts): chi pesa di piu' sta in cima;
--   2. l'ARCHIVIO, qui: chi e' finito esce di scena.
-- L'ordine da solo lascia la lista lunga, l'archivio da solo non dice cosa fare
-- prima. Insieme: poche righe, e le prime sono quelle giuste.
--
-- ARCHIVIARE NON E' CANCELLARE. La riga resta, con tutta la sua storia, e chi
-- torna a scrivere rientra da solo: lo fa il trigger qui sotto, non una persona
-- che se lo ricorda.

alter table prospects add column if not exists archiviato_il  timestamptz;
alter table prospects add column if not exists archiviato_perche text;

create index if not exists idx_prospects_archiviato on prospects (archiviato_il)
  where archiviato_il is not null;

-- CHI RISCRIVE TORNA DA SOLO. E' il pezzo che rende l'archivio sicuro: senza
-- questo, archiviare vorrebbe dire perdere qualcuno che ci ripensa.
create or replace function risveglia_se_scrive() returns trigger
language plpgsql as $$
begin
  if new.archiviato_il is not null
     and new.last_reply_at is distinct from old.last_reply_at
     and new.last_reply_at > old.archiviato_il then
    new.archiviato_il := null;
    new.archiviato_perche := null;
  end if;
  return new;
end;
$$;

drop trigger if exists prospects_risveglio on prospects;
create trigger prospects_risveglio
  before update on prospects
  for each row execute function risveglia_se_scrive();

select 'schema v62 applicato: archivio della pipeline, con risveglio automatico' as esito;

-- ─── schema_v63.sql ────────────────────────────────────────────

-- LA PRIMA RISPOSTA AUTOMATICA (Dre, 29/9/2026)
--
-- «La prima risposta parte da sola, con l'analisi e la presentazione.»
-- scripts/prima_risposta.py approva solo le prime risposte semplici (positivo
-- o tiepido, analisi pronta, seconda testa COERENTE, Revisore OK, lun-ven 9-17,
-- max 5 per giro e 15 al giorno); l'invio resta a manda.py.
--
-- NASCE SPENTA. Si accende dalla sala di controllo insieme a «manda», la prima
-- volta guardando partire una mail insieme (regola del 28/9). Lo script non
-- approva niente se uno dei due interruttori e' spento. Ordine 2: gira prima
-- di manda (3), cosi' l'approvata parte nello stesso giro.
--
-- PARTE IN OMBRA (--ombra): decide e scrive cosa avrebbe fatto, non approva.
-- Si toglie --ombra dopo ~50 casi confrontati con quello che Dre ha mandato.

insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ora_preferita, ordine, attiva) values
  ('prima_risposta', 'La prima risposta parte da sola',
   'Approva da sola le prime risposte semplici (positivi e tiepidi con l''analisi pronta), dopo il Revisore. Manda le spedisce con analisi e presentazione. I no, i rinvii e i casi strani restano a Dre.',
   'python3 scripts/prima_risposta.py', 5, null, 2, false)
on conflict (chiave) do update set nome = excluded.nome, cosa = excluded.cosa, comando = excluded.comando,
  cadenza_minuti = excluded.cadenza_minuti, ordine = excluded.ordine;

select 'schema v63 applicato: la prima risposta automatica, spenta' as esito;

-- ─── schema_v64.sql ────────────────────────────────────────────

-- I SEGUITI AUTOMATICI (Dre, 29/9/2026: strada A)
--
-- I follow-up col template (FOLLOW UP 1, MINI FOLLOW UP, RIPRESA, RINVIO SCADUTO)
-- li scrive il codice, parola per parola (scripts/seguiti.py). Questa operazione
-- li approva da soli con la stessa porta della prima risposta: il codice riscrive
-- il testo e deve venire identico, e basta una traccia di contatto fuori da
-- Smartlead negli ultimi 60 giorni (Gmail, call, transcript, note, calendario,
-- task, «Fuori binario», presa in carico) perche' resti a Dre.
--
-- PARTE IN OMBRA (--ombra): decide e scrive cosa avrebbe fatto, non approva.

insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ora_preferita, ordine, attiva) values
  ('seguiti', 'I follow-up partono da soli',
   'Approva da soli i follow-up scritti dal codice col template di Dre, se nessuno sta già sentendo quell''azienda fuori da Smartlead. Per ora in ombra: decide e scrive, non approva.',
   'python3 scripts/prima_risposta.py --seguiti --ombra', 15, null, 2, true)
on conflict (chiave) do update set nome = excluded.nome, cosa = excluded.cosa, comando = excluded.comando,
  cadenza_minuti = excluded.cadenza_minuti, ordine = excluded.ordine;

select 'schema v64 applicato: i seguiti automatici, in ombra' as esito;

-- ─── schema_v65.sql ────────────────────────────────────────────

-- I FOLLOW-UP IN ARRIVO, GIORNO PER GIORNO (Dre, 29/9/2026)
--
-- «Per i follow-up ci deve essere una sezione apribile dove vedo in ordine,
-- giorno dopo giorno, quelli in arrivo, e un sistema in leverage per gestirli.»
--
-- Le date le calcola UNA sola regola, quella di scripts/followup.py (la stessa
-- che mette in coda): lo script le scrive qui, lo schermo le legge. Nessuna
-- seconda copia della regola nel Workspace, nessun numero diverso per la stessa
-- domanda. Una riga per azienda: il prossimo follow-up che le spetta.

create table if not exists seguiti_calendario (
  prospect_id   uuid primary key references prospects(id) on delete cascade,
  gruppo        text not null,          -- FOLLOW UP 1, MINI FOLLOW UP, RINVIO SCADUTO
  il            date not null,          -- quando tocca (nel passato = dovuto)
  perche        text,                   -- «analisi del 24/9, nessuna risposta»
  aggiornato_il timestamptz not null default now()
);

create index if not exists idx_seguiti_calendario_il on seguiti_calendario (il);

alter table seguiti_calendario enable row level security;

-- vede la riga chi vede l'azienda: la regola resta quella di prospects
drop policy if exists seguiti_calendario_leggi on seguiti_calendario;
create policy seguiti_calendario_leggi on seguiti_calendario for select to authenticated
  using (exists (select 1 from prospects p where p.id = seguiti_calendario.prospect_id));

select 'schema v65 applicato: il calendario dei follow-up' as esito;

-- il ricalcolo ogni ora (applicato il 29/9 dalla sala di controllo)
insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ora_preferita, ordine, attiva) values
  ('calendario_seguiti', 'Il calendario dei follow-up',
   'Chi riceve un follow-up nei prossimi 21 giorni e quando, con la stessa regola di followup.py. Lo legge la sezione «Follow-up in arrivo» della Posta.',
   'python3 scripts/followup.py --calendario', 60, null, 4, true)
on conflict (chiave) do nothing;

-- ─── schema_v66.sql ────────────────────────────────────────────

-- COSA VEDE OGNUNO (decisione Dre 28/9, strada A scelta il 29/9)
--
-- Prima: chi non era ceo vedeva solo le aziende col suo nome in «chi segue»
-- (11 su 13.230) piu' i clienti. Lorenzo, Carlo, Salvatore, Alex e Okay aprivano
-- il Workspace e trovavano 16-18 aziende e zero bozze.
--
-- Adesso si vede per AREA di lavoro, un campo nuovo e separato dal reparto (il
-- reparto veste l'app con il suo colore, 26/9, e non si tocca):
--   direzione  tutto;
--   vendita    la vendita: chi ha risposto e non e' ancora cliente, e le call
--              conoscitive e tecniche; piu' le bozze senza proprietario;
--   marketing  i clienti in avvio, prova e canone, e le aziende con un progetto Ads;
--   web        le aziende con un progetto sito o landing;
--   software   quello che segue (chi segue, le sue call).
-- Restano le regole di prima (chi segue, i clienti in tecnica/avvio/prova/cliente,
-- le aziende delle proprie call): le policy si sommano.
--
-- E sparisce il controllo riga per riga delle call (ho_una_call(id), 13.230 volte
-- a lettura per chi non e' ceo): l'elenco delle aziende delle mie call si calcola
-- una volta sola per lettura.

alter table profili add column if not exists area text
  check (area is null or area in ('direzione', 'vendita', 'marketing', 'web', 'software'));

update profili set area = 'direzione' where id in ('43095060-b873-4d29-825b-55522f26af55', '47f779aa-e952-468f-b6ce-5df848944092');  -- Dre, Giacomo
update profili set area = 'vendita'   where id = 'a8eff3b6-b553-4d56-90fb-3c17eac6822d';   -- Lorenzo
update profili set area = 'marketing' where id in ('4d5a857e-f0b3-43d3-8b1a-8e24c7102d8a', '880f4e94-2f2f-48da-aa28-ddac04b7d61f');  -- Carlo, Salvatore
update profili set area = 'web'       where id = 'e6276dd0-b940-48fc-a808-09b05ab3830b';   -- Alex
update profili set area = 'software'  where id = 'f5431303-0d75-4702-a108-9660b0eeb372';   -- Okay

create or replace function mia_area() returns text
language sql stable security definer set search_path = public as $$
  select area from profili where id = uid_eff();
$$;

create or replace function aziende_delle_mie_call() returns uuid[]
language sql stable security definer set search_path = public as $$
  select coalesce(array_agg(distinct a.prospect_id), '{}')
  from agenda a
  where a.prospect_id is not null
    and (a.owner = (select uid_eff()) or a.owner is null)
    and a.at > now() - interval '30 days';
$$;

drop policy if exists "aziende: quelle con cui ho una call" on prospects;
create policy "aziende: quelle con cui ho una call" on prospects for select to authenticated
  using (id = any ((select aziende_delle_mie_call())::uuid[]));

drop policy if exists "aziende della mia area" on prospects;
create policy "aziende della mia area" on prospects for select to authenticated using (
  case (select mia_area())
    when 'direzione' then true
    when 'vendita' then (not coalesce(fuori, false) and last_reply_at is not null)
                     or (coalesce(fuori, false) and pipeline_stage in ('conoscitiva', 'tecnica'))
    when 'marketing' then (coalesce(fuori, false) and pipeline_stage in ('avvio', 'prova', 'cliente'))
                     or exists (select 1 from progetti g where g.prospect_id = prospects.id and g.natura ilike '%ads%')
    when 'web' then exists (select 1 from progetti g where g.prospect_id = prospects.id
                            and (g.natura ilike '%sito%' or g.natura ilike '%landing%'))
    else false
  end
);

-- chi vede per area deve anche poter lavorare: segnare «Fatto, l'ho mandata»,
-- togliere l'attesa, scrivere una nota
drop policy if exists "aziende: scrive la mia area" on prospects;
create policy "aziende: scrive la mia area" on prospects for update to authenticated using (
  case (select mia_area())
    when 'direzione' then true
    when 'vendita' then (not coalesce(fuori, false) and last_reply_at is not null)
                     or (coalesce(fuori, false) and pipeline_stage in ('conoscitiva', 'tecnica'))
    when 'marketing' then (coalesce(fuori, false) and pipeline_stage in ('avvio', 'prova', 'cliente'))
                     or exists (select 1 from progetti g where g.prospect_id = prospects.id and g.natura ilike '%ads%')
    when 'web' then exists (select 1 from progetti g where g.prospect_id = prospects.id
                            and (g.natura ilike '%sito%' or g.natura ilike '%landing%'))
    else false
  end
);

-- le bozze delle mail: le vede e le lavora anche la vendita (le mail partono dalle
-- caselle di Lorenzo e sono firmate da lui)
drop policy if exists "proposte: le bozze alla vendita" on proposte;
create policy "proposte: le bozze alla vendita" on proposte for all to authenticated
  using (owner is null and tipo in ('risposta', 'umano') and (select mia_area()) in ('direzione', 'vendita'));

select 'schema v66 applicato: cosa vede ognuno, per area' as esito;

-- ─── schema_v67.sql ────────────────────────────────────────────

-- LA CASSAFORTE: i soldi li vedono solo Dre e Giacomo (Dre, 29/9/2026)
--
-- «Niente soldi per gli altri: solo io e Giacomo vediamo tutte le robe che
-- riguardano soldi.» Preventivi, incassi e listino erano gia' solo dei ceo. Nelle
-- tabelle che la squadra legge restavano: il canone e i dati di fatturazione sulla
-- scheda, il prezzo suggerito e i numeri del cliente (enriched: prezzo, bilancio,
-- valore), il valore dei progetti, e la formula dei prezzi nei parametri.
--
-- Non basta nasconderli dallo schermo: chi ha l'accesso li leggerebbe lo stesso.
-- Qui stanno in due tabelle che solo i ceo leggono, e un controllo nel database
-- li SPOSTA da solo: qualunque cosa scriva un canone o un valore nelle tabelle
-- normali (lo schermo, uno script, un pezzo di codice di domani), il dato finisce
-- in cassaforte e nella tabella normale resta vuoto. Chi non e' ceo non puo'
-- nemmeno scriverlo.

create table if not exists soldi_clienti (
  prospect_id   uuid primary key references prospects(id) on delete cascade deferrable initially deferred,
  canone        numeric,
  fatturazione  jsonb,
  prezzo        jsonb,          -- il prezzo suggerito (scripts/prezzo.py)
  bilancio      jsonb,          -- i numeri del cliente usati per il prezzo
  valore        jsonb,
  aggiornato_il timestamptz not null default now()
);
create table if not exists soldi_progetti (
  progetto_id   bigint primary key references progetti(id) on delete cascade deferrable initially deferred,
  valore        numeric,
  aggiornato_il timestamptz not null default now()
);

alter table soldi_clienti enable row level security;
alter table soldi_progetti enable row level security;
drop policy if exists "soldi: solo i ceo" on soldi_clienti;
create policy "soldi: solo i ceo" on soldi_clienti for all to authenticated
  using ((select sono_ceo())) with check ((select sono_ceo()));
drop policy if exists "soldi: solo i ceo" on soldi_progetti;
create policy "soldi: solo i ceo" on soldi_progetti for all to authenticated
  using ((select sono_ceo())) with check ((select sono_ceo()));

-- chi puo' mettere soldi: i ceo e gli script del sistema (chiave di servizio)
-- Si guarda CHI HA FATTO LA RICHIESTA (le sue credenziali), non l'utente del
-- database: dentro il controllo quello e' sempre il proprietario, e diceva si' a
-- tutti (trovato dalla prova del 29/9: il canone scritto da Alex entrava).
-- Senza credenziali e' una migrazione fatta a mano sul database: passa.
create or replace function puo_scrivere_soldi() returns boolean
language sql stable security definer set search_path = public as $$
  select case coalesce(nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role', '')
           when 'service_role' then true
           when '' then true
           else (select sono_ceo())
         end;
$$;

create or replace function cassaforte_prospects() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  soldi jsonb := coalesce(new.enriched, '{}'::jsonb);
begin
  if new.canone is not null or new.fatturazione is not null
     or soldi ? 'prezzo' or soldi ? 'bilancio' or soldi ? 'valore' then
    if puo_scrivere_soldi() then
      insert into soldi_clienti as s (prospect_id, canone, fatturazione, prezzo, bilancio, valore, aggiornato_il)
      values (new.id, new.canone, new.fatturazione, soldi -> 'prezzo', soldi -> 'bilancio', soldi -> 'valore', now())
      on conflict (prospect_id) do update set
        canone       = coalesce(excluded.canone, s.canone),
        fatturazione = coalesce(excluded.fatturazione, s.fatturazione),
        prezzo       = coalesce(excluded.prezzo, s.prezzo),
        bilancio     = coalesce(excluded.bilancio, s.bilancio),
        valore       = coalesce(excluded.valore, s.valore),
        aggiornato_il = now();
    end if;
    new.canone := null;
    new.fatturazione := null;
    new.enriched := case when new.enriched is null then null else new.enriched - 'prezzo' - 'bilancio' - 'valore' end;
  end if;
  return new;
end;
$$;
drop trigger if exists prospects_cassaforte on prospects;
create trigger prospects_cassaforte before insert or update on prospects
  for each row execute function cassaforte_prospects();

create or replace function cassaforte_progetti() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.valore is not null then
    if puo_scrivere_soldi() then
      insert into soldi_progetti as s (progetto_id, valore, aggiornato_il) values (new.id, new.valore, now())
      on conflict (progetto_id) do update set valore = excluded.valore, aggiornato_il = now();
    end if;
    new.valore := null;
  end if;
  return new;
end;
$$;
drop trigger if exists progetti_cassaforte on progetti;
create trigger progetti_cassaforte before insert or update on progetti
  for each row execute function cassaforte_progetti();

-- quello che c'e' gia' entra in cassaforte (le update passano dai trigger qui sopra)
update progetti set valore = valore where valore is not null;
update prospects set canone = canone where canone is not null or fatturazione is not null
   or enriched ? 'prezzo' or enriched ? 'bilancio' or enriched ? 'valore';

-- la formula dei prezzi: solo i ceo
drop policy if exists "parametri: leggono tutti" on parametri;
drop policy if exists "parametri: leggono tutti, i prezzi i ceo" on parametri;
create policy "parametri: leggono tutti, i prezzi i ceo" on parametri for select to authenticated
  using (chiave not like 'prezzo.%' or (select sono_ceo()));

select 'schema v67 applicato: la cassaforte dei soldi' as esito;

-- ─── schema_v68.sql ────────────────────────────────────────────

-- IL RISERVATO: la preparazione delle call e il prezzo li vede solo Dre (29/9/2026)
--
-- Dre: «la preparazione precall la vedo io e basta», e poi «anche il prezzo, solo io».
-- Sopra la cassaforte dei soldi (schema_v67, Dre e Giacomo) c'e' un livello in piu':
-- il riservato, solo per chi ha profili.vede_riservato (oggi Dre).
--   - le preparazioni delle call: da agenda.preparazione a una tabella loro;
--   - il prezzo suggerito e i numeri da cui nasce (bilancio, valore): da soldi_clienti
--     a riservato_clienti;
--   - la formula dei prezzi (parametri prezzo.*).
-- Come per i soldi, un controllo nel database sposta da solo quello che viene scritto
-- nel posto sbagliato, e chi non ha il permesso non puo' scriverlo.
-- Canone, fatturazione, preventivi, incassi e valore dei progetti restano a Dre e Giacomo.

alter table profili add column if not exists vede_riservato boolean not null default false;
update profili set vede_riservato = true where id = '43095060-b873-4d29-825b-55522f26af55';   -- Dre

create or replace function vedo_riservato() returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce((select vede_riservato from profili where id = uid_eff()), false);
$$;

create or replace function puo_scrivere_riservato() returns boolean
language sql stable security definer set search_path = public as $$
  select case coalesce(nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role', '')
           when 'service_role' then true
           when '' then true
           else (select vedo_riservato())
         end;
$$;

create table if not exists preparazioni (
  agenda_id    bigint primary key references agenda(id) on delete cascade deferrable initially deferred,
  prospect_id  uuid,
  testo        text not null,
  preparata_il timestamptz not null default now()
);
create table if not exists riservato_clienti (
  prospect_id   uuid primary key references prospects(id) on delete cascade deferrable initially deferred,
  prezzo        jsonb,
  bilancio      jsonb,
  valore        jsonb,
  aggiornato_il timestamptz not null default now()
);
alter table preparazioni enable row level security;
alter table riservato_clienti enable row level security;
drop policy if exists "riservato: solo Dre" on preparazioni;
create policy "riservato: solo Dre" on preparazioni for all to authenticated
  using ((select vedo_riservato())) with check ((select vedo_riservato()));
drop policy if exists "riservato: solo Dre" on riservato_clienti;
create policy "riservato: solo Dre" on riservato_clienti for all to authenticated
  using ((select vedo_riservato())) with check ((select vedo_riservato()));

-- la preparazione scritta nell'agenda va nel riservato, e dall'agenda sparisce
create or replace function riservato_agenda() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.preparazione is not null then
    if puo_scrivere_riservato() then
      insert into preparazioni as r (agenda_id, prospect_id, testo, preparata_il)
      values (new.id, new.prospect_id, new.preparazione, coalesce(new.preparata_il, now()))
      on conflict (agenda_id) do update set testo = excluded.testo, prospect_id = excluded.prospect_id,
                                            preparata_il = excluded.preparata_il;
    end if;
    new.preparazione := null;
  end if;
  return new;
end;
$$;
drop trigger if exists agenda_riservato on agenda;
create trigger agenda_riservato before insert or update on agenda
  for each row execute function riservato_agenda();

-- la cassaforte dei clienti, rifatta: canone e fatturazione a Dre e Giacomo,
-- prezzo, bilancio e valore solo a Dre
create or replace function cassaforte_prospects() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  arr jsonb := coalesce(new.enriched, '{}'::jsonb);
begin
  if new.canone is not null or new.fatturazione is not null then
    if puo_scrivere_soldi() then
      insert into soldi_clienti as s (prospect_id, canone, fatturazione, aggiornato_il)
      values (new.id, new.canone, new.fatturazione, now())
      on conflict (prospect_id) do update set
        canone = coalesce(excluded.canone, s.canone),
        fatturazione = coalesce(excluded.fatturazione, s.fatturazione),
        aggiornato_il = now();
    end if;
    new.canone := null;
    new.fatturazione := null;
  end if;
  if arr ? 'prezzo' or arr ? 'bilancio' or arr ? 'valore' then
    if puo_scrivere_riservato() then
      insert into riservato_clienti as r (prospect_id, prezzo, bilancio, valore, aggiornato_il)
      values (new.id, arr -> 'prezzo', arr -> 'bilancio', arr -> 'valore', now())
      on conflict (prospect_id) do update set
        prezzo = coalesce(excluded.prezzo, r.prezzo),
        bilancio = coalesce(excluded.bilancio, r.bilancio),
        valore = coalesce(excluded.valore, r.valore),
        aggiornato_il = now();
    end if;
    new.enriched := case when new.enriched is null then null else new.enriched - 'prezzo' - 'bilancio' - 'valore' end;
  end if;
  return new;
end;
$$;

-- quello che c'e' gia' si sposta
insert into riservato_clienti (prospect_id, prezzo, bilancio, valore)
  select prospect_id, prezzo, bilancio, valore from soldi_clienti
  where prezzo is not null or bilancio is not null or valore is not null
on conflict (prospect_id) do nothing;
update soldi_clienti set prezzo = null, bilancio = null, valore = null;
update agenda set preparazione = preparazione where preparazione is not null;

-- la formula dei prezzi: solo Dre
drop policy if exists "parametri: leggono tutti, i prezzi i ceo" on parametri;
drop policy if exists "parametri: leggono tutti, i prezzi solo Dre" on parametri;
create policy "parametri: leggono tutti, i prezzi solo Dre" on parametri for select to authenticated
  using (chiave not like 'prezzo.%' or (select vedo_riservato()));

-- «scrivono i ceo» era FOR ALL, cioe' anche lettura: Giacomo vedeva la formula
-- lo stesso (trovato dalla prova del 29/9). Si scrive con policy per scrittura sola.
drop policy if exists "parametri: scrivono i ceo" on parametri;
drop policy if exists "parametri: aggiungono i ceo" on parametri;
drop policy if exists "parametri: cambiano i ceo" on parametri;
drop policy if exists "parametri: tolgono i ceo" on parametri;
create policy "parametri: aggiungono i ceo" on parametri for insert to authenticated
  with check ((select sono_ceo()) and (chiave not like 'prezzo.%' or (select vedo_riservato())));
create policy "parametri: cambiano i ceo" on parametri for update to authenticated
  using ((select sono_ceo()) and (chiave not like 'prezzo.%' or (select vedo_riservato())));
create policy "parametri: tolgono i ceo" on parametri for delete to authenticated
  using ((select sono_ceo()) and (chiave not like 'prezzo.%' or (select vedo_riservato())));

select 'schema v68 applicato: il riservato di Dre' as esito;

-- ─── schema_v69.sql ────────────────────────────────────────────

-- IL METRO DELLE RISPOSTE (Dre, 29/9/2026: strada A del lettore unico)
--
-- Le classificazioni di Dre dicono com'e' l'azienda oggi, dopo tutta la storia, non
-- cosa dice UNA mail («ok aspetto con ansia» e' «negativo» perche' dopo l'analisi ha
-- detto no). Per misurare un lettore di mail serve un metro fatto mail per mail: qui
-- Dre etichetta una mail alla volta, senza vedere cosa ne pensa il modello (se no si
-- misura il modello contro se stesso). Poi scripts/metro.py confronta.

create table if not exists metro_risposte (
  interaction_id uuid primary key references interactions(id) on delete cascade,
  prospect_id    uuid,
  testo          text not null,                 -- solo quello che ha scritto (senza firma ne' citazione)
  proposta       jsonb,                         -- la lettura del modello: NON si mostra a Dre
  etichetta      text check (etichetta is null or etichetta in ('si', 'no', 'non_scrivere', 'fuori_ufficio', 'rinvio', 'altro')),
  etichettata_il timestamptz,
  creato_il      timestamptz not null default now()
);
alter table metro_risposte enable row level security;
drop policy if exists "metro: solo i ceo" on metro_risposte;
create policy "metro: solo i ceo" on metro_risposte for all to authenticated
  using ((select sono_ceo())) with check ((select sono_ceo()));

select 'schema v69 applicato: il metro delle risposte' as esito;

-- ─── schema_v70.sql ────────────────────────────────────────────

-- IL METRO CON I COMMENTI (Dre, 29/9/2026, mentre etichettava)
--
-- «Dammi la possibilita' di scrivere commenti»: su una mail come «chiedo scusa, e'
-- entrato un cliente e mi sono scordato» l'etichetta da sola non basta. Dietro c'era
-- una call saltata, un'azienda poco in target e la decisione di lasciar stare. Il
-- commento tiene il perche' di Dre: e' il primo pezzo delle sue regole non scritte.

alter table metro_risposte add column if not exists nota text;

select 'schema v70 applicato: i commenti nel metro' as esito;

-- ─── schema_v71.sql ────────────────────────────────────────────

-- L'ULTIMO MOVIMENTO (Dre, 30/9/2026: «mi dice fermo da sei giorni, mando avanti,
-- e c'e' ancora fermo da sei giorni»)
--
-- «Fermo da» contava i giorni dall'ultima risposta del lead nella scheda, e dall'invio
-- dell'analisi nel Radar e nei Numeri: tre orologi, e nessuno vedeva quello che fa Dre.
-- Adesso c'e' una data sola, tenuta dal database: l'ultima volta che e' successo
-- qualcosa di vero con quell'azienda. Una mail loro o nostra, un follow-up, l'analisi,
-- una call o il suo riassunto, un cambio di fase. Le note no: dentro ci sono anche
-- quelle di servizio di Clara, che non sono un passo avanti.

alter table prospects add column if not exists mosso_il timestamptz;

create or replace function mosso_da_interazione() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.prospect_id is not null and new.kind in ('email_in', 'email_out', 'followup', 'analisi', 'call', 'transcript') then
    update prospects set mosso_il = greatest(coalesce(mosso_il, new.at), new.at) where id = new.prospect_id;
  end if;
  return new;
end $$;
drop trigger if exists trg_mosso_interazione on interactions;
create trigger trg_mosso_interazione after insert on interactions
  for each row execute function mosso_da_interazione();

create or replace function mosso_da_fase() returns trigger
language plpgsql as $$
begin
  if new.stage is distinct from old.stage
     or new.pipeline_stage is distinct from old.pipeline_stage
     or new.fuori is distinct from old.fuori then
    new.mosso_il := now();
  end if;
  return new;
end $$;
drop trigger if exists trg_mosso_fase on prospects;
create trigger trg_mosso_fase before update on prospects
  for each row execute function mosso_da_fase();

-- il passato: la cosa piu' recente fra quelle che sappiamo
update prospects p set mosso_il = greatest(
  p.last_reply_at, p.analysis_sent_at, p.fuori_at,
  (select max(i.at) from interactions i where i.prospect_id = p.id
     and (i.kind in ('email_in', 'email_out', 'followup', 'analisi', 'call', 'transcript')
          or (i.kind = 'nota' and i.body ~ '^(Passa a|Entra in|Torna in|Riaperta|DIVENTA CLIENTE|Uscita dalla pipeline)'))))
where p.mosso_il is null;

select 'schema v71 applicato: l''ultimo movimento' as esito;

-- ─── schema_v72.sql ────────────────────────────────────────────

-- LA TAPPA UNICA (Dre, 30/9/2026: «bisogna ricostruire da zero, partendo dalle
-- fondamenta, first principles, non a caso»)
--
-- Per dire a che punto e' un'azienda servivano tre campi insieme: la fase delle mail
-- (stage), quella della pipeline (pipeline_stage) e «e' fuori» (fuori). Nel database
-- erano piu' di 20 combinazioni per 9 tappe, 47 aziende «in pipeline» senza fase, e
-- ogni schermata le leggeva a modo suo. Da qui in poi la tappa e' UNA, la calcola il
-- database dai campi di oggi (cosi' il motore di Clara continua a scrivere come prima)
-- e le schermate nuove leggono solo lei.
--
-- Le tappe (decise il 30/9, «Il Workspace da zero, le fondamenta»):
--   risposta, analisi, follow_up, conoscitiva, tecnica, avvio, prova, cliente, perso
--   e nuovo per chi non ha mai risposto (il mondo di Smartlead, fuori dal Workspace).
-- Scartato non e' una tappa: e' la classificazione (negativo, fuori target...).
-- Di chi e' la palla c'e' gia': awaiting_us (tocca a noi).

create or replace function tappa_di(p_stage text, p_pipeline text, p_fuori boolean, p_analisi boolean)
returns text language sql immutable as $$
  select case
    when (coalesce(p_fuori, false) and p_pipeline = 'cliente') or (not coalesce(p_fuori, false) and p_stage = 'cliente') then 'cliente'
    when (coalesce(p_fuori, false) and p_pipeline = 'perso') or (not coalesce(p_fuori, false) and p_stage = 'perso') then 'perso'
    when coalesce(p_fuori, false) then coalesce(p_pipeline, 'conoscitiva')
    when p_stage = 'call_fissata' then 'conoscitiva'
    when p_stage = 'in_follow_up' then 'follow_up'
    when p_stage = 'analisi_inviata' or coalesce(p_analisi, false) then 'analisi'
    when p_stage in ('risposto', 'rinviato') then 'risposta'
    else 'nuovo'
  end
$$;

alter table prospects add column if not exists tappa text;

create or replace function tieni_tappa() returns trigger
language plpgsql as $$
begin
  new.tappa := tappa_di(new.stage::text, new.pipeline_stage::text, new.fuori, new.analysis_sent);
  return new;
end $$;
drop trigger if exists trg_tappa on prospects;
create trigger trg_tappa before insert or update on prospects
  for each row execute function tieni_tappa();

update prospects set tappa = tappa_di(stage::text, pipeline_stage::text, fuori, analysis_sent)
where tappa is distinct from tappa_di(stage::text, pipeline_stage::text, fuori, analysis_sent);

create index if not exists idx_prospects_tappa on prospects (tappa) where tappa <> 'nuovo';

select 'schema v72 applicato: la tappa unica' as esito;

-- ─── schema_v73.sql ────────────────────────────────────────────

-- GLI ESAMI (Dre, 1/10/2026: «vorrei trainare il sistema, immagina un modello come
-- l'altro, con tutte quelle domande e commenti, così sa fare i follow-up, sa
-- riprendere, sa fare tutto esattamente come lo farei io»)
--
-- Il metro delle risposte funziona (150 mail, 97 commenti, un verdetto). Questa e'
-- la sua forma generale: un CASO per riga, di qualunque tema (seguiti, persi,
-- prezzi...), con i blocchi da mostrare, le scelte possibili, la proposta del
-- sistema NASCOSTA a Dre (se no si misura il sistema contro se stesso), la sua
-- etichetta e il suo commento. La pagina «Metro» li serve uno alla volta.

create table if not exists metro_casi (
  id             bigint generated always as identity primary key,
  tema           text not null,                  -- 'seguiti', poi 'persi', 'prezzi'...
  prospect_id    uuid,
  riferimento    text,                           -- per non proporre due volte lo stesso caso
  domanda        text not null,                  -- la domanda in testa alla carta
  mostra         jsonb not null,                 -- blocchi [{eti, testo}] che Dre vede
  scelte         jsonb not null,                 -- [[chiave, nome], ...] i bottoni
  proposta       jsonb,                          -- cosa farebbe il sistema oggi: NON si mostra
  etichetta      text,
  nota           text,
  etichettata_il timestamptz,
  creato_il      timestamptz not null default now(),
  unique (tema, riferimento)
);
alter table metro_casi enable row level security;
drop policy if exists "esami: solo i ceo" on metro_casi;
create policy "esami: solo i ceo" on metro_casi for all to authenticated
  using ((select sono_ceo())) with check ((select sono_ceo()));

select 'schema v73 applicato: gli esami' as esito;

-- ─── schema_v75.sql ────────────────────────────────────────────

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
  linkedin text,
  -- chi decide (Dre, 7/10: «decide lui?»): si | insieme | no
  decide text check (decide is null or decide in ('si', 'insieme', 'no')),
  nota text
);

-- se la tabella e' nata prima di questi campi
alter table referenti add column if not exists linkedin text;
alter table referenti add column if not exists decide text;

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

-- ─── schema_v76.sql ────────────────────────────────────────────

-- v76 (7/10): il calendario dei follow-up si tocca anche dallo schermo.
--
-- La caccia ai bug del 6/10 l'ha trovato: seguiti_calendario aveva solo la
-- regola di LETTURA (v65). «Sposta il giorno» e «Niente follow-up» dal
-- Workspace toccavano zero righe, il database rispondeva «fatto» lo stesso e
-- la riga tornava com'era al ricaricare. Nessun errore, nessun avviso.
--
-- Chi vede l'azienda (la stessa regola di prospects) puo' spostare il giorno
-- e togliere la riga. Il ricalcolo orario di followup.py resta la verita':
-- legge il giorno scelto da Dre in prospects.enriched.follow_up_il.

drop policy if exists seguiti_calendario_cambio on seguiti_calendario;
create policy seguiti_calendario_cambio on seguiti_calendario for update to authenticated
  using (exists (select 1 from prospects p where p.id = seguiti_calendario.prospect_id
                 and (sono_ceo() or vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue))))
  with check (exists (select 1 from prospects p where p.id = seguiti_calendario.prospect_id
                      and (sono_ceo() or vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue))));

drop policy if exists seguiti_calendario_tolgo on seguiti_calendario;
create policy seguiti_calendario_tolgo on seguiti_calendario for delete to authenticated
  using (exists (select 1 from prospects p where p.id = seguiti_calendario.prospect_id
                 and (sono_ceo() or vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue))));

select 'schema v76 applicato: il calendario dei follow-up si sposta dallo schermo' as esito;

-- IL GIORNO DEL FOLLOW-UP SCELTO DA DRE: una colonna sua (7/10). Dentro enriched
-- veniva cancellato da ogni copione che riscrive enriched intero; in
-- next_action_date si mischiava con la data detta dal lead (rinvio, ferie).
alter table prospects add column if not exists follow_up_il date;
comment on column prospects.follow_up_il is
  'Il giorno in cui parte il prossimo follow-up, scelto da Dre dalla schermata. Vince sulla regola (analisi+5, rinvio+1, ripresa+6). Lo legge scripts/followup.py.';

select 'schema v76: anche la colonna follow_up_il' as esito;

-- ─── schema_v77.sql ────────────────────────────────────────────

-- v77 (7/10): L'UTILIZZO DEL WORKSPACE, per persona (Dre: «metti un qualcosa che mi dica
-- l'utilizzo, cosi' monitoro l'utilizzo mio e di tutti, tipo la CodexBar; in Impostazioni,
-- solo io vedo»).
--
-- Fino a oggi il registro sapeva solo chi MODIFICA aziende e proposte: chi apre il
-- Workspace, quanto ci resta e dove, non lo sapeva nessuno. Qui: un minuto contato per
-- ogni minuto in cui la pagina e' aperta, in primo piano e la persona la sta usando
-- (mouse, tastiera, dito negli ultimi due minuti). Una riga per persona per giorno.
--
-- Conta la persona VERA (auth.uid()), non quella che un ceo sta guardando con «vedi come».
-- Lo legge solo Dre.

create table if not exists utilizzo (
  uid        uuid not null,
  giorno     date not null,
  minuti     integer not null default 0,
  azioni     integer not null default 0,          -- clic e tasti, a grandi linee: quanto lavora, non solo quanto guarda
  schermate  jsonb not null default '{}'::jsonb,  -- minuti per schermata: {"oggi": 12, "posta": 30}
  primo_at   timestamptz not null default now(),
  ultimo_at  timestamptz not null default now(),
  telefono   integer not null default 0,          -- minuti da schermo stretto
  primary key (uid, giorno)
);
alter table utilizzo enable row level security;
-- nessuna regola di lettura o scrittura diretta: si passa solo dalle due funzioni qui sotto

-- chi e' Dre: il suo id di profilo (profili, nome Dramane). Una funzione sola, cosi' se
-- cambia si cambia qui.
create or replace function e_dre() returns boolean
language sql stable security definer set search_path = public as $$
  select auth.uid() = '43095060-b873-4d29-825b-55522f26af55'::uuid
$$;

-- il minuto: si somma alla riga del giorno, in un colpo solo (niente leggi-poi-scrivi)
create or replace function segna_utilizzo(p_minuti integer, p_azioni integer, p_schermata text, p_telefono boolean)
returns void language plpgsql security definer set search_path = public as $$
declare
  oggi date := (now() at time zone 'Europe/Rome')::date;
  s text := left(coalesce(nullif(p_schermata, ''), 'altro'), 40);
  m integer := greatest(0, least(coalesce(p_minuti, 0), 5));     -- mai piu' di 5 minuti per chiamata
  a integer := greatest(0, least(coalesce(p_azioni, 0), 500));
begin
  if auth.uid() is null then return; end if;
  insert into utilizzo (uid, giorno, minuti, azioni, schermate, telefono)
    values (auth.uid(), oggi, m, a, jsonb_build_object(s, m), case when p_telefono then m else 0 end)
  on conflict (uid, giorno) do update set
    minuti    = utilizzo.minuti + excluded.minuti,
    azioni    = utilizzo.azioni + excluded.azioni,
    schermate = utilizzo.schermate || jsonb_build_object(s, coalesce((utilizzo.schermate ->> s)::integer, 0) + m),
    telefono  = utilizzo.telefono + excluded.telefono,
    ultimo_at = now();
end $$;
grant execute on function segna_utilizzo(integer, integer, text, boolean) to authenticated;

-- il riepilogo per il pannello: risponde solo a Dre, a tutti gli altri un elenco vuoto
create or replace function utilizzo_squadra(p_giorni integer default 7)
returns table (uid uuid, nome text, ruolo text, giorno date, minuti integer, azioni integer, schermate jsonb, telefono integer, ultimo_at timestamptz)
language sql stable security definer set search_path = public as $$
  select u.uid, p.nome, p.ruolo, u.giorno, u.minuti, u.azioni, u.schermate, u.telefono, u.ultimo_at
  from utilizzo u left join profili p on p.id = u.uid
  where e_dre() and u.giorno >= ((now() at time zone 'Europe/Rome')::date - greatest(1, least(p_giorni, 60)) + 1)
  order by u.giorno desc, u.minuti desc
$$;
grant execute on function utilizzo_squadra(integer) to authenticated;

select 'schema v77 applicato: l''utilizzo del Workspace, per persona, solo per Dre' as esito;

-- ─── schema_v78.sql ────────────────────────────────────────────

-- v78 (8/10): LA FASE 0 DEL SISTEMA NUOVO. Tre cose, e tre scritture che aspettavano.
--
-- Il design («Il sistema nuovo (8-10-2026)», Cervello Condiviso) parte da qui perche'
-- senza queste tre cose tutto il resto impara da dati sporchi:
--
-- 1. CHI E' CLIENTE LO DICE UNA TABELLA. Fino a oggi lo diceva `stage`, che nessuno
--    aggiorna: l'8/10 Fun Dallas Tours (cliente) stava nella lista dei si' da servire, e
--    Zafferano, ENERGY4YOU, Klavzar e SINTESIA avevano un progetto attivo e stage=risposto.
--    Da qui: `clienti`. Chi ci entra ha stage=cliente per effetto del trigger, e il cancello
--    delle proposte guarda anche qui. E' anche la base del portale clienti (Dre, 8/10:
--    «i personaggi principali del workspace sono i clienti»).
--
-- 2. IL LOCK UMANO, MURATO. I Paletti del 30/7: «serve un lock umano vero: nessun processo
--    automatico puo' toccare un campo deciso da una persona. Va risolto nello schema, non
--    nella disciplina dell'agente. E' il buco numero uno». L'8/10 rilettura.py:231
--    sovrascriveva ancora la classificazione, e 436 risposte «a mano» avevano classi
--    riscritte. Da qui: `prospects.deciso` dice quali campi ha deciso una persona, e un
--    trigger rifiuta ogni scrittura del ruolo di servizio su quei campi. Non disciplina:
--    lo schema dice no. Vale da oggi in avanti: le 436 vecchie non si bloccano al buio
--    perche' molte sono sbagliate; si ripuliscono dal Workspace, e da li' restano bloccate.
--
-- 3. IL FILO INTERO. sync_v2 registrava solo le ultime due mail nostre dopo l'ultima
--    risposta (933 risposte, 318 mail nostre nel database): la verita' su cosa e' partito
--    stava su Smartlead e basta. Da qui: `interactions.message_id` e `casella`, con un
--    indice unico, cosi' il sync puo' scrivere TUTTO il filo senza doppioni.
--
-- In fondo, le tre scritture della lista di Dre dell'8/10 (B1, B2, B3), che il guardiano
-- di Claude Code non ha lasciato fare dagli script: qui le fa il SQL editor, come gli schemi.

-- ───────────────────────────────── 1. CLIENTI ─────────────────────────────────

create table if not exists clienti (
  prospect_id uuid primary key references prospects(id) on delete cascade,
  dal         date not null default (now() at time zone 'Europe/Rome')::date,
  stato       text not null default 'attivo' check (stato in ('prova', 'attivo', 'sospeso', 'chiuso')),
  chi_segue   uuid references auth.users(id),
  note        text,
  deciso_da   uuid references auth.users(id),
  deciso_il   timestamptz not null default now()
);
comment on table clienti is 'Chi e'' cliente, deciso da una persona. E'' la fonte: stage=cliente ne e'' l''effetto, non la causa (v78, 8/10).';
alter table clienti enable row level security;

drop policy if exists "clienti: li leggono i ceo e chi li segue" on clienti;
create policy "clienti: li leggono i ceo e chi li segue" on clienti
  for select to authenticated using (sono_ceo() or chi_segue = auth.uid());
drop policy if exists "clienti: li scrivono i ceo" on clienti;
create policy "clienti: li scrivono i ceo" on clienti
  for all to authenticated using (sono_ceo()) with check (sono_ceo());

-- e' cliente adesso? (prova e attivo contano; sospeso e chiuso no)
create or replace function e_cliente(p uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from clienti where prospect_id = p and stato in ('prova', 'attivo'))
$$;

-- entrare in clienti mette stage=cliente e lo segna come deciso da una persona
create or replace function clienti_su_prospects() returns trigger
language plpgsql security definer set search_path = public as $$
declare chi uuid := coalesce(new.deciso_da, auth.uid());
begin
  if new.stato in ('prova', 'attivo') then
    update prospects
       set stage = 'cliente', awaiting_us = false,
           deciso = coalesce(deciso, '{}'::jsonb) || jsonb_build_object('stage', jsonb_build_object('da', chi, 'il', now(), 'via', 'clienti'))
     where id = new.prospect_id;
  end if;
  return new;
end $$;
drop trigger if exists trg_clienti_su_prospects on clienti;
create trigger trg_clienti_su_prospects after insert or update on clienti
  for each row execute function clienti_su_prospects();

-- ──────────────────────────────── 2. LOCK UMANO ───────────────────────────────

alter table prospects add column if not exists deciso jsonb not null default '{}'::jsonb;
comment on column prospects.deciso is 'Campi decisi da una persona: {"stage": {"da": uuid, "il": ts}, "classificazione": {...}}. Il ruolo di servizio non li tocca (v78).';

-- chi sta scrivendo e' uno script (chiave di servizio)? Una migrazione a mano (nessun
-- token) NON e' servizio: passa, come in puo_scrivere_soldi (v67).
create or replace function e_servizio() returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce(nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role', '') = 'service_role'
$$;

create or replace function lock_umano_prospects() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  c text; prima text; dopo text;
  protetti text[] := array['classificazione', 'stage', 'no_followup', 'fuori', 'pipeline_stage', 'email', 'email_alt'];
  deciso_qui boolean;
begin
  if e_servizio() then
    -- uno script non toglie un lock
    if new.deciso is distinct from old.deciso then
      raise exception 'lock umano: uno script non cambia «deciso» (regola del 30/7, murata l''8/10)';
    end if;
    foreach c in array protetti loop
      execute format('select ($1).%I::text, ($2).%I::text', c, c) into prima, dopo using old, new;
      deciso_qui := (old.deciso ? c)
                    or (c = 'classificazione' and coalesce(old.enriched ->> 'classificazione', '') = 'manual');
      if deciso_qui and prima is distinct from dopo then
        raise exception 'lock umano: «%» di % lo ha deciso una persona (% -> % rifiutato). Uno script non lo tocca: regola del 30/7, murata l''8/10',
          c, old.id, coalesce(prima, 'vuoto'), coalesce(dopo, 'vuoto');
      end if;
    end loop;
  elsif auth.uid() is not null then
    -- una persona dal Workspace: ogni campo protetto che cambia diventa deciso da lei
    foreach c in array protetti loop
      execute format('select ($1).%I::text, ($2).%I::text', c, c) into prima, dopo using old, new;
      if prima is distinct from dopo then
        new.deciso := coalesce(new.deciso, '{}'::jsonb) || jsonb_build_object(c, jsonb_build_object('da', auth.uid(), 'il', now()));
      end if;
    end loop;
  end if;
  return new;
end $$;
drop trigger if exists trg_lock_umano_prospects on prospects;
create trigger trg_lock_umano_prospects before update on prospects
  for each row execute function lock_umano_prospects();

-- il cancello delle proposte guarda anche `clienti`, non solo stage (difesa doppia)
create or replace function proposta_ammessa() returns trigger
language plpgsql security definer set search_path = public as $$
declare p record;
begin
  if new.tipo in ('risposta', 'umano') and new.stato in ('aperta', 'approvata', 'in_invio') and new.prospect_id is not null then
    select fuori, stage, pipeline_stage, no_followup, classificazione into p from prospects where id = new.prospect_id;
    if p.fuori or p.stage in ('cliente', 'perso') or p.pipeline_stage in ('cliente', 'perso')
       or coalesce(p.no_followup, false) or p.classificazione in ('soppresso', 'nervoso')
       or e_cliente(new.prospect_id) then
      raise exception 'proposta rifiutata: l''azienda % e'' cliente, in pipeline, persa, senza follow-up o bloccata (regola del 25/9, clienti dal v78)', new.prospect_id;
    end if;
  end if;
  if tg_op = 'INSERT' and new.tipo = 'risposta' and new.azione ? 'bozza' then
    if coalesce(new.azione->'lettura'->>'ultima_loro', '') = '' then
      raise exception 'bozza rifiutata: manca la lettura dell''ultima mail (azione.lettura.ultima_loro). Nessuna bozza senza lettura (25/9)';
    end if;
    if coalesce(new.azione->'lettura'->>'coerenza', '') <> 'COERENTE' then
      raise exception 'bozza rifiutata: la coerenza loro/noi non e'' COERENTE (%). Nessuna bozza senza lettura (25/9)', coalesce(new.azione->'lettura'->>'coerenza', 'assente');
    end if;
  end if;
  return new;
end $$;

-- ─────────────────────────────── 3. IL FILO INTERO ────────────────────────────

alter table interactions add column if not exists message_id text;    -- l'id del messaggio su Smartlead
alter table interactions add column if not exists casella    text;    -- da quale casella e' partita (le nostre)
create unique index if not exists uq_interactions_messaggio on interactions (prospect_id, message_id) where message_id is not null;
comment on column interactions.message_id is 'Id del messaggio su Smartlead: con l''indice unico il sync scrive tutto il filo senza doppioni (v78).';

-- ───────────────────── LE TRE SCRITTURE DELL'8/10 (B1, B2, B3) ────────────────

-- B3: i cinque clienti che il database credeva prospect
insert into clienti (prospect_id, stato, deciso_da, note)
select id, 'attivo', '43095060-b873-4d29-825b-55522f26af55'::uuid,
       'Cliente con progetto attivo o confermato da Dre; il database lo credeva prospect (domanda B3 dell''8/10)'
  from prospects
 where company in ('Zafferano Matteo Bertoli', 'ENERGY4YOU', 'SINTESIA', 'Fun Dallas Tours')
    or company like 'Paolo Klavzar%'
on conflict (prospect_id) do nothing;

-- B1: Twin System e SOLPOWER in fila (si' da 112 e 90 giorni, PDF pronto, nessuna fila li vedeva)
update prospects
   set awaiting_us = true,
       enriched = coalesce(enriched, '{}'::jsonb) || jsonb_build_object('rimesso_in_fila', jsonb_build_object(
         'quando', '2026-10-08', 'da', 'Dre (v78)',
         'perche', 'si'' senza analisi da 112/90 giorni, awaiting_us spento da un follow-up: nessuna fila lo vedeva. PDF pronto, serve la consegna. Domanda B1.'))
 where company in ('Twin System', 'SOLPOWER');

-- B2: Bank Station, il PDF di Luca e Aldo agganciato a Francesco, che l'ha chiesto
update prospects f
   set analysis_pdf = (select analysis_pdf from prospects where email in ('luca@bankstation.it', 'aldo@bankstation.it') and analysis_pdf is not null limit 1),
       awaiting_us = true,
       enriched = coalesce(f.enriched, '{}'::jsonb) || jsonb_build_object('pdf_riagganciato', jsonb_build_object(
         'quando', '2026-10-08', 'da', 'Dre (v78)',
         'perche', 'Francesco ha chiesto il reinvio; il PDF stava sui record di luca@ e aldo@. Domanda B2.'))
 where f.email = 'francesco@bankstation.it' and f.analysis_pdf is null;

-- 9/10: Cosimo Storino (Occasione Immobiliare) perso dopo la call di triage di Dre.
-- Su Smartlead e' gia' in pausa (fatto il 9/10 alle 13:40); qui lo stage e il blocco,
-- deciso da Dre, cosi' nessuno script lo rimette in fila.
update prospects
   set stage = 'perso', awaiting_us = false, no_followup = true,
       lost_reason = 'triage telefonico di Dre, 9/10',
       deciso = coalesce(deciso, '{}'::jsonb) || jsonb_build_object(
         'stage', jsonb_build_object('da', '43095060-b873-4d29-825b-55522f26af55', 'il', now(), 'via', 'triage 9/10'),
         'no_followup', jsonb_build_object('da', '43095060-b873-4d29-825b-55522f26af55', 'il', now(), 'via', 'triage 9/10'))
 where email = 'cosimo.storino@occasioneimmobiliare.com';

-- la prova, da leggere subito dopo: devono tornare 5 clienti, 2 in fila, 1 PDF, 1 perso
select 'clienti' as cosa, count(*)::text as quanti from clienti where stato = 'attivo'
union all select 'in fila (B1)', count(*)::text from prospects where company in ('Twin System', 'SOLPOWER') and awaiting_us
union all select 'pdf a francesco (B2)', count(*)::text from prospects where email = 'francesco@bankstation.it' and analysis_pdf is not null
union all select 'stage=cliente per effetto', count(*)::text from prospects where id in (select prospect_id from clienti) and stage = 'cliente'
union all select 'cosimo storino perso', count(*)::text from prospects where email = 'cosimo.storino@occasioneimmobiliare.com' and stage = 'perso';
