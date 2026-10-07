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
