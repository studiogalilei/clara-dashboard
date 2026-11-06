-- v121 (6/11, Achille di turno). Il caso: alle 15:30-15:54 Dre ha segnato dall'app quattro lead «Non interessato:
-- l'ho sentito al telefono». Le mail si sono fermate (no_followup), ma nel foglio e nell'app restavano «Da chiamare» e
-- «Da rispondere», e una decisione «Da guardare tu» restava aperta in Posta.
-- La fonte, due pezzi:
--   1. il gesto (clara_non_interessato, v120) scriveva su prospects ma non sullo stato che il foglio legge
--      (snella_lead.stato vince su tutto, e c'era ancora quello vecchio);
--   2. le bozze di chi esce dai lead le chiudeva solo manda.py (pulizia), e manda e' spenta dal 3/11: chi esce dai lead
--      da allora lasciava la sua bozza aperta (il caso Zafferano del 25/9, di nuovo possibile).
-- Ovunque: il punto 2 vale per qualunque modo in cui un'azienda smette di essere un lead (gesto, sync, foglio, a mano),
-- quindi sta nel database, con la stessa condizione di proposta_ammessa (una regola in un posto solo).

-- la condizione di stanza.contattabile (quella che usava manda.pulizia), in una funzione sola: quella di proposta_ammessa
-- piu' «in mano a Dre» (4/11, «Me ne occupo io»: Clara si ferma). proposta_ammessa resta com'e' (rifiuta, non chiude).
create or replace function prospect_fuori_dai_lead(p prospects) returns boolean
language sql stable security definer set search_path = public as $$
  -- coalesce sul tutto: con stage o classificazione vuoti l'«in» dice null, e «not null» non e' vero (il trigger non scattava)
  select coalesce(coalesce(p.fuori, false) or p.stage in ('cliente', 'perso') or p.pipeline_stage in ('cliente', 'perso')
      or coalesce(p.no_followup, false) or p.classificazione in ('soppresso', 'nervoso') or e_cliente(p.id)
      or nullif(btrim(coalesce(p.in_mano_a, '')), '') is not null, false)
$$;

-- quando un'azienda esce dai lead, le sue bozze aperte si chiudono da sole (prima: solo manda.pulizia)
create or replace function chiudi_bozze_fuori_dai_lead() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if prospect_fuori_dai_lead(new) and not prospect_fuori_dai_lead(old) then
    update proposte set stato = 'no', risposta_il = now(),
           risposta = 'chiusa da sola: l''azienda non è più un lead (pipeline, cliente, persa o senza follow-up)'
     where prospect_id = new.id and tipo in ('risposta', 'umano') and stato in ('aperta', 'approvata');
  end if;
  return new;
end $$;
drop trigger if exists chiudi_bozze_fuori_dai_lead on prospects;
create trigger chiudi_bozze_fuori_dai_lead after update of fuori, stage, pipeline_stage, no_followup, classificazione, in_mano_a
  on prospects for each row execute function chiudi_bozze_fuori_dai_lead();

-- il gesto «Non interessato» porta anche lo stato del foglio (scelto da Dre: snella_lead); «riapri» lo ridà al sistema
create or replace function clara_non_interessato(chi uuid, riapri boolean default false) returns jsonb
language plpgsql security definer set search_path = public as $$
begin
  if not sono_ceo() then return jsonb_build_object('ok', false, 'perche', 'solo il ceo'); end if;
  if riapri then
    update prospects set no_followup = false, lost_reason = null where id = chi and lost_reason like 'Non interessato%';
    update snella_lead set stato = null, prossima_mossa = null, prossima_il = null
     where prospect_id = chi and stato = 'Non interessato' and prossima_mossa like 'Fermare la sequenza: sentito al telefono%';
    insert into snella_note (prospect_id, tipo, testo) values (chi, 'gesto', 'Dre lo riapre: non è più «non interessato».');
    return jsonb_build_object('ok', true, 'no_followup', false);
  end if;
  update prospects set no_followup = true, lost_reason = 'Non interessato (Dre, al telefono, ' || to_char(now() at time zone 'Europe/Rome', 'DD/MM') || ')',
    in_mano_a = coalesce(in_mano_a, 'Dre') where id = chi;
  insert into snella_lead (prospect_id, stato, prossima_mossa, prossima_il, chiamata, richiamare_il)
  values (chi, 'Non interessato', 'Fermare la sequenza: sentito al telefono, non interessato', null, null, null)
  on conflict (prospect_id) do update set stato = excluded.stato, prossima_mossa = excluded.prossima_mossa,
    prossima_il = null, chiamata = null, richiamare_il = null;
  update clara_decisioni set stato = 'scartata', dre_nota = 'Non interessato (Dre, al telefono)', dre_il = now()
    where prospect_id = chi and stato in ('proposta', 'approvata');
  insert into snella_note (prospect_id, tipo, testo) values (chi, 'gesto', 'Non interessato: l''ho sentito al telefono. Non lo contattiamo più.');
  return jsonb_build_object('ok', true, 'no_followup', true);
end $$;
grant execute on function clara_non_interessato(uuid, boolean) to authenticated;

-- lo stato calcolato dice lo stesso (per chi non ha la riga in snella_lead), come schede.stato_di
create or replace function snella_stato_calcolato(p prospects) returns text
language sql stable parallel safe as $$
  select case
    when p.classificazione in ('soppresso', 'nervoso') then 'Non contattare'
    when p.stage = 'cliente' or p.pipeline_stage in ('cliente', 'prova', 'avvio') then 'Cliente acquisito'
    when coalesce(p.no_followup, false) and p.lost_reason like 'Non interessato%' then 'Non interessato'
    when p.pipeline_stage = 'perso' then 'Perso'
    when p.pipeline_stage in ('conoscitiva', 'tecnica') or (p.stage = 'call_fissata' and p.last_reply_at is not null) then 'Call fissata'
    when p.last_reply_at is null then 'Nessuna risposta'
    when p.classificazione in ('negativo', 'fuori_target') then 'Non interessato'
    when p.stage = 'perso' then 'Perso'
    when p.classificazione = 'ooo' then 'Assente'
    when p.classificazione = 'rinvio' then 'Da ricontattare'
    when p.classificazione = 'positivo' then 'Analisi inviata'
    else 'Da rispondere'
  end
$$;

-- l'arretrato (le leggi sono retroattive): i «non interessato» gia' segnati prendono lo stato, e le bozze aperte di chi
-- non e' piu' un lead si chiudono
insert into snella_lead (prospect_id, stato, prossima_mossa)
select id, 'Non interessato', 'Fermare la sequenza: sentito al telefono, non interessato'
  from prospects where no_followup and lost_reason like 'Non interessato (Dre, al telefono%'
on conflict (prospect_id) do update set stato = excluded.stato, prossima_mossa = excluded.prossima_mossa,
  prossima_il = null, chiamata = null, richiamare_il = null
  where snella_lead.stato is distinct from 'Non interessato';
update proposte x set stato = 'no', risposta_il = now(),
       risposta = 'chiusa da sola: l''azienda non è più un lead (pipeline, cliente, persa o senza follow-up)'
  from prospects p
 where p.id = x.prospect_id and x.tipo in ('risposta', 'umano') and x.stato in ('aperta', 'approvata')
   and prospect_fuori_dai_lead(p);
