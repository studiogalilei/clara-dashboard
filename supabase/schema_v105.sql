-- v105 (4/11/2026): «Me ne occupo io». Dre, dalla Coda, prende in mano una relazione e Clara si ferma su quella:
-- niente piu' decisioni ne' mail per quel lead finche' non gliela ridà. Il motivo (mi ha chiamato, l'ho chiamato io,
-- ci ho parlato) resta scritto e Clara lo legge come nota.
alter table prospects
  add column if not exists in_mano_a text,            -- 'Dre' quando la relazione e' sua; null = Clara
  add column if not exists in_mano_motivo text,
  add column if not exists in_mano_il timestamptz;

create or replace function clara_prendi(chi uuid, motivo text default null, lascia boolean default false) returns jsonb
language plpgsql security definer set search_path = public as $$
declare n int := 0;
begin
  if not sono_ceo() then return jsonb_build_object('ok', false, 'perche', 'solo il ceo'); end if;
  if lascia then
    update prospects set in_mano_a = null, in_mano_motivo = null, in_mano_il = null where id = chi;
    insert into snella_note (prospect_id, tipo, testo) values (chi, 'nota', 'Dre ridà la relazione a Clara.');
    return jsonb_build_object('ok', true, 'in_mano_a', null);
  end if;
  update prospects set in_mano_a = 'Dre', in_mano_motivo = nullif(btrim(coalesce(motivo, '')), ''), in_mano_il = now() where id = chi;
  update clara_decisioni set stato = 'scartata', dre_nota = 'Me ne occupo io' || coalesce(': ' || nullif(btrim(motivo), ''), ''), dre_il = now(), errore = null
    where prospect_id = chi and stato in ('proposta', 'approvata');
  get diagnostics n = row_count;
  insert into snella_note (prospect_id, tipo, testo) values (chi, 'nota', 'Dre prende in mano la relazione' || coalesce(': ' || nullif(btrim(motivo), ''), '') || '. Clara si ferma qui.');
  return jsonb_build_object('ok', true, 'in_mano_a', 'Dre', 'chiuse', n);
end $$;
grant execute on function clara_prendi(uuid, text, boolean) to authenticated;

-- la coda e la relazione dicono di chi e' la relazione
create or replace function clara_coda(giorni int default 30) returns jsonb
language sql stable security definer set search_path = public as $$
  select case when not sono_ceo() then '[]'::jsonb else coalesce((
    with ult as (
      select distinct on (d.prospect_id) d.*
      from clara_decisioni d
      where d.creato_il >= now() - make_interval(days => giorni)
      order by d.prospect_id, d.risposta_il desc, d.creato_il desc
    )
    select jsonb_agg(jsonb_build_object(
      'id', u.id, 'prospect_id', u.prospect_id, 'risposta_il', u.risposta_il, 'mossa', u.mossa, 'owner', u.owner,
      'entro_il', u.entro_il, 'testo', coalesce(u.testo_finale, u.testo), 'testo_clara', u.testo, 'perche', u.perche,
      'prove', u.prove, 'richiamo', u.richiamo, 'segnali', u.segnali, 'giudice', u.giudice, 'stato', u.stato,
      'lead_testo', u.lead_testo, 'approvata_il', u.approvata_il, 'approvata_da', u.approvata_da, 'inviata_il', u.inviata_il, 'verificata_il', u.verificata_il,
      'errore', u.errore, 'esito', u.esito, 'esito_il', u.esito_il, 'creato_il', u.creato_il, 'versione', u.versione,
      'dollari', (u.uso->>'dollari')::numeric, 'dre_giudizio', u.dre_giudizio,
      'azienda', p.company, 'persona', p.name, 'ruolo', p.role, 'email', p.email, 'citta', p.city, 'settore', p.sector,
      'telefono', p.phone, 'sito', p.website, 'analisi_pdf', p.analysis_pdf is not null, 'analisi_mandata', p.analysis_sent,
      'fase', coalesce(p.pipeline_stage, p.stage), 'classe', p.classificazione, 'ultima_risposta', p.last_reply_at,
      'prossima_call', (select min(a.at) from agenda a where a.prospect_id = p.id and a.at > now()),
      'in_mano_a', p.in_mano_a, 'in_mano_motivo', p.in_mano_motivo, 'in_mano_il', p.in_mano_il
    ) order by u.risposta_il desc)
    from ult u join prospects p on p.id = u.prospect_id
  ), '[]'::jsonb) end;
$$;

create or replace function clara_relazione(chi uuid) returns jsonb
language sql stable security definer set search_path = public as $$
  select case when not sono_ceo() then '{}'::jsonb else jsonb_build_object(
    'lead', (select jsonb_build_object('id', p.id, 'azienda', p.company, 'persona', p.name, 'ruolo', p.role, 'email', p.email,
               'citta', p.city, 'settore', p.sector, 'telefono', p.phone, 'sito', p.website, 'analisi_pdf', p.analysis_pdf,
               'analisi_mandata', p.analysis_sent, 'analisi_il', p.analysis_sent_at, 'fase', coalesce(p.pipeline_stage, p.stage),
               'classe', p.classificazione, 'ultima_risposta', p.last_reply_at, 'fuori', p.fuori, 'no_followup', p.no_followup,
               'fonte', p.source, 'fit', p.enriched->'google_fit'->>'verdetto', 'fit_motivo', p.enriched->'google_fit'->>'motivo',
               'cosa_fa', p.enriched->'google_fit'->>'cosa_fa', 'campagna', p.campaign,
               'in_mano_a', p.in_mano_a, 'in_mano_motivo', p.in_mano_motivo, 'in_mano_il', p.in_mano_il)
             from prospects p where p.id = chi),
    'filo', coalesce((select jsonb_agg(jsonb_build_object('at', i.at, 'tipo', i.kind, 'testo', i.body, 'casella', i.casella) order by i.at)
             from (select * from interactions where prospect_id = chi and kind in ('email_in', 'email_out') order by at desc limit 60) i), '[]'::jsonb),
    'decisioni', coalesce((select jsonb_agg(jsonb_build_object('id', d.id, 'risposta_il', d.risposta_il, 'mossa', d.mossa, 'owner', d.owner,
                   'testo', coalesce(d.testo_finale, d.testo), 'perche', d.perche, 'stato', d.stato, 'inviata_il', d.inviata_il,
                   'esito', d.esito, 'dre_giudizio', d.dre_giudizio, 'dre_nota', d.dre_nota, 'creato_il', d.creato_il) order by d.creato_il desc)
                   from clara_decisioni d where d.prospect_id = chi), '[]'::jsonb),
    'agenda', coalesce((select jsonb_agg(jsonb_build_object('at', a.at, 'tipo', a.tipo, 'titolo', a.titolo, 'link', a.link) order by a.at desc)
               from agenda a where a.prospect_id = chi), '[]'::jsonb),
    'note', coalesce((select jsonb_agg(jsonb_build_object('at', n.at, 'tipo', n.tipo, 'testo', n.testo) order by n.at desc)
             from (select * from snella_note where prospect_id = chi order by at desc limit 30) n), '[]'::jsonb),
    'scheda', (select to_jsonb(s) from snella_lead s where s.prospect_id = chi)
  ) end;
$$;
notify pgrst, 'reload schema';
