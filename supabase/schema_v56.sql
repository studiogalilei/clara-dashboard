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
