-- v119 (5/11, Dre): «Non interessato» al telefono = smettiamo di contattarlo (niente campagne, niente follow-up), ma
-- resta ritrovabile: la lista dei non interessati sta in Analytics, in basso, con «Riapri» se cambia idea.
create or replace function clara_non_interessato(chi uuid, riapri boolean default false) returns jsonb
language plpgsql security definer set search_path = public as $$
begin
  if not sono_ceo() then return jsonb_build_object('ok', false, 'perche', 'solo il ceo'); end if;
  if riapri then
    update prospects set no_followup = false, lost_reason = null where id = chi and lost_reason like 'Non interessato%';
    insert into snella_note (prospect_id, tipo, testo) values (chi, 'nota', 'Dre lo riapre: non è più «non interessato».');
    return jsonb_build_object('ok', true, 'no_followup', false);
  end if;
  update prospects set no_followup = true, lost_reason = 'Non interessato (Dre, al telefono, ' || to_char(now() at time zone 'Europe/Rome', 'DD/MM') || ')',
    in_mano_a = coalesce(in_mano_a, 'Dre') where id = chi;
  update clara_decisioni set stato = 'scartata', dre_nota = 'Non interessato (Dre, al telefono)', dre_il = now()
    where prospect_id = chi and stato in ('proposta', 'approvata');
  insert into snella_note (prospect_id, tipo, testo) values (chi, 'nota', 'Non interessato: l''ho sentito al telefono. Non lo contattiamo più.');
  return jsonb_build_object('ok', true, 'no_followup', true);
end $$;
grant execute on function clara_non_interessato(uuid, boolean) to authenticated;

create or replace function clara_non_interessati() returns jsonb
language sql stable security definer set search_path = public as $$
  select case when not sono_ceo() then '[]'::jsonb else coalesce((
    select jsonb_agg(jsonb_build_object('id', p.id, 'azienda', p.company, 'persona', p.name, 'email', p.email, 'citta', p.city,
             'telefono', p.phone, 'quando', p.lost_reason, 'analisi_mandata', p.analysis_sent, 'ultima_risposta', p.last_reply_at)
           order by p.updated_at desc nulls last)
    from prospects p where p.no_followup and p.lost_reason like 'Non interessato%'
  ), '[]'::jsonb) end;
$$;
grant execute on function clara_non_interessati() to authenticated;
notify pgrst, 'reload schema';
