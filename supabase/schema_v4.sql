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
