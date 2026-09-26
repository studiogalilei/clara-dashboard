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
