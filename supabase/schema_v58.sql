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
