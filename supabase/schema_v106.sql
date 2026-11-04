-- v106 (4/11/2026 pomeriggio): «Ti consiglio di chiamare». Clara manda avanti il lavoro e, quando trova un numero e una
-- telefonata di Dre sarebbe un buon touchpoint, lo segnala a parte (clara_decisioni.consiglio). Non e' un «Da chiamare»:
-- quello resta per chi ha chiesto lui di sentirci. Il Desk lo mostra in giallo nelle Relazioni e nelle Call.
alter table clara_decisioni add column if not exists consiglio jsonb;   -- {numero, perche, esito?, esito_il?}

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
      'prove', u.prove, 'richiamo', u.richiamo, 'consiglio', u.consiglio, 'segnali', u.segnali, 'giudice', u.giudice, 'stato', u.stato,
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

create or replace function clara_call() returns jsonb
language sql stable security definer set search_path = public as $$
  select case when not sono_ceo() then '{}'::jsonb else jsonb_build_object(
    'prossime', coalesce((select jsonb_agg(jsonb_build_object('at', a.at, 'tipo', a.tipo, 'titolo', a.titolo, 'link', a.link,
                   'prospect_id', a.prospect_id, 'azienda', p.company, 'persona', p.name, 'telefono', p.phone,
                   'preparazione', a.preparazione) order by a.at)
                 from agenda a left join prospects p on p.id = a.prospect_id
                 where a.at between now() - interval '2 hours' and now() + interval '14 days'), '[]'::jsonb),
    'richiami', coalesce((select jsonb_agg(jsonb_build_object('id', d.id, 'prospect_id', d.prospect_id, 'azienda', p.company,
                   'persona', p.name, 'telefono', coalesce(d.richiamo->>'numero', p.phone), 'quando', d.richiamo->>'quando',
                   'perche', coalesce(d.richiamo->>'perche', d.perche), 'risposta_il', d.risposta_il, 'esito', d.esito,
                   'lead_testo', d.lead_testo) order by d.risposta_il desc)
                 from clara_decisioni d join prospects p on p.id = d.prospect_id
                 where d.mossa = 'callback' and d.stato in ('proposta', 'approvata') and d.esito is null
                   and p.in_mano_a is null and d.creato_il >= now() - interval '21 days'), '[]'::jsonb),
    'consigli', coalesce((select jsonb_agg(jsonb_build_object('id', d.id, 'prospect_id', d.prospect_id, 'azienda', p.company,
                   'persona', p.name, 'telefono', d.consiglio->>'numero', 'perche', d.consiglio->>'perche', 'mossa', d.mossa,
                   'stato', d.stato, 'risposta_il', d.risposta_il, 'lead_testo', d.lead_testo, 'consiglio', d.consiglio) order by d.risposta_il desc)
                 from clara_decisioni d join prospects p on p.id = d.prospect_id
                 where d.consiglio->>'numero' is not null and d.consiglio->>'esito' is null
                   and d.stato not in ('superata', 'scartata') and p.in_mano_a is null
                   and d.creato_il >= now() - interval '21 days'), '[]'::jsonb)
  ) end;
$$;
notify pgrst, 'reload schema';
