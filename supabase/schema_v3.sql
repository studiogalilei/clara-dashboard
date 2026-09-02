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
