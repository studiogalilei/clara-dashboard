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
