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
