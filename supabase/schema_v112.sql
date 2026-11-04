-- v112 (4/11): le call del calendario che il sistema non collega a un'azienda le collega Dre con un tocco
-- («se non riesce a collegare o non è sicuro, me lo dica e glielo collego io»). Gli eventi segnati «interna» spariscono.
create or replace function clara_call() returns jsonb
language sql stable security definer set search_path = public as $$
  select case when not sono_ceo() then '{}'::jsonb else jsonb_build_object(
    'prossime', coalesce((select jsonb_agg(jsonb_build_object('id', a.id, 'at', a.at, 'tipo', a.tipo, 'titolo', a.titolo, 'link', a.link,
                   'prospect_id', a.prospect_id, 'azienda', p.company, 'persona', p.name, 'telefono', p.phone,
                   'preparazione', a.preparazione) order by a.at)
                 from agenda a left join prospects p on p.id = a.prospect_id
                 where a.at between now() - interval '2 hours' and now() + interval '14 days'
                   and coalesce(a.tipo, '') not in ('annullata', 'interna')), '[]'::jsonb),
    -- i «Da chiamare» di Clara, con la programmazione e le note di Dre se ci sono
    'richiami', coalesce((select jsonb_agg(jsonb_build_object('id', d.id, 'prospect_id', d.prospect_id, 'azienda', p.company,
                   'persona', p.name, 'telefono', coalesce(d.richiamo->>'numero', p.phone), 'quando', d.richiamo->>'quando',
                   'perche', coalesce(d.richiamo->>'perche', d.perche), 'risposta_il', d.risposta_il, 'esito', d.esito,
                   'lead_testo', d.lead_testo, 'chiamata_id', c.id, 'richiamare_il', c.richiamare_il, 'note', coalesce(c.note, '[]'::jsonb),
                   'origine', 'clara') order by c.richiamare_il nulls last, d.risposta_il desc)
                 from clara_decisioni d join prospects p on p.id = d.prospect_id left join chiamate c on c.decisione_id = d.id
                 where d.mossa = 'callback' and d.stato in ('proposta', 'approvata') and d.esito is null and c.esito is null
                   and p.in_mano_a is null and d.creato_il >= now() - interval '21 days'), '[]'::jsonb),
    -- le chiamate aggiunte da Dre, con quello che il sistema sa del lead se e' in scheda
    'mie', coalesce((select jsonb_agg(jsonb_build_object('id', c.id, 'chiamata_id', c.id, 'prospect_id', c.prospect_id,
                   'azienda', coalesce(c.azienda, p.company), 'persona', coalesce(c.persona, p.name), 'telefono', coalesce(c.numero, p.phone),
                   'richiamare_il', c.richiamare_il, 'note', coalesce(c.note, '[]'::jsonb), 'creato_il', c.creato_il, 'origine', 'dre',
                   'fase', coalesce(p.pipeline_stage, p.stage), 'analisi_mandata', p.analysis_sent, 'ultima_risposta', p.last_reply_at,
                   'lead_testo', (select u.lead_testo from clara_decisioni u where u.prospect_id = c.prospect_id order by u.risposta_il desc, u.creato_il desc limit 1),
                   'perche', (select u.perche from clara_decisioni u where u.prospect_id = c.prospect_id order by u.risposta_il desc, u.creato_il desc limit 1)
                 ) order by c.richiamare_il nulls last, c.creato_il desc)
                 from chiamate c left join prospects p on p.id = c.prospect_id
                 where c.decisione_id is null and c.esito is null), '[]'::jsonb),
    'consigli', coalesce((select jsonb_agg(jsonb_build_object('id', d.id, 'prospect_id', d.prospect_id, 'azienda', p.company,
                   'persona', p.name, 'telefono', d.consiglio->>'numero', 'perche', d.consiglio->>'perche', 'mossa', d.mossa,
                   'stato', d.stato, 'risposta_il', d.risposta_il, 'lead_testo', d.lead_testo, 'consiglio', d.consiglio) order by d.risposta_il desc)
                 from clara_decisioni d join prospects p on p.id = d.prospect_id
                 where d.consiglio->>'numero' is not null and d.consiglio->>'esito' is null
                   and d.stato not in ('superata', 'scartata') and p.in_mano_a is null
                   and d.creato_il >= now() - interval '21 days'), '[]'::jsonb)
  ) end;
$$;

create or replace function clara_collega_call(evento bigint, chi uuid default null, lead boolean default true) returns jsonb
language plpgsql security definer set search_path = public as $$
declare t text; a timestamptz;
begin
  if not sono_ceo() then return jsonb_build_object('ok', false, 'perche', 'solo il ceo'); end if;
  if not lead then
    update agenda set tipo = 'interna' where id = evento;
    return jsonb_build_object('ok', true, 'tipo', 'interna');
  end if;
  if chi is null then return jsonb_build_object('ok', false, 'perche', 'manca l''azienda'); end if;
  select titolo, at into t, a from agenda where id = evento;
  update agenda set prospect_id = chi, tipo = case when coalesce(tipo, '') in ('', 'altro') then 'conoscitiva' else tipo end where id = evento;
  insert into snella_note (prospect_id, tipo, testo, autore_nome)
    values (chi, 'nota', 'Call in calendario collegata da Dre: ' || coalesce(t, '') || ', ' || to_char(a at time zone 'Europe/Rome', 'DD/MM HH24:MI'), 'Sistema');
  return jsonb_build_object('ok', true, 'prospect_id', chi);
end $$;
grant execute on function clara_collega_call(bigint, uuid, boolean) to authenticated;
notify pgrst, 'reload schema';
