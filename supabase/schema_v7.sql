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
