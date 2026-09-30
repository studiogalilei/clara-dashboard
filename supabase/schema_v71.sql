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
