-- v118 (5/11, Dre): i consigli nuovi stanno in Relazioni; al primo gesto (numero toccato, WhatsApp, richiamo) passano in Call.
-- chiamate.chiamato_il = Dre ha toccato il numero; clara_coda porta la riga «chiamate» e il PDF dell'analisi.
alter table chiamate add column if not exists chiamato_il timestamptz;

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
      'in_mano_a', p.in_mano_a, 'in_mano_motivo', p.in_mano_motivo, 'in_mano_il', p.in_mano_il,
      'fit', p.enriched->'google_fit'->>'verdetto', 'analisi_url', p.analysis_pdf,
      'chiamata', (select jsonb_build_object('id', c.id, 'chiamato_il', c.chiamato_il, 'whatsapp_il', c.whatsapp_il, 'richiamare_il', c.richiamare_il, 'esito', c.esito)
                   from chiamate c where c.decisione_id = u.id)
    ) order by u.risposta_il desc)
    from ult u join prospects p on p.id = u.prospect_id
  ), '[]'::jsonb) end;
$$;
notify pgrst, 'reload schema';

create or replace function clara_call() returns jsonb
language sql stable security definer set search_path = public as $$
  select case when not sono_ceo() then '{}'::jsonb else jsonb_build_object(
    'prossime', coalesce((select jsonb_agg(jsonb_build_object('id', a.id, 'at', a.at, 'tipo', a.tipo, 'titolo', a.titolo, 'link', a.link,
                   'prospect_id', a.prospect_id, 'azienda', p.company, 'persona', p.name, 'telefono', p.phone,
                   'preparazione', a.preparazione) order by a.at)
                 from agenda a left join prospects p on p.id = a.prospect_id
                 where a.at between now() - interval '2 hours' and now() + interval '14 days'
                   and coalesce(a.tipo, '') not in ('annullata', 'interna')), '[]'::jsonb),
    -- i «Da chiamare» di Clara, con la programmazione e le note di Dre se ci sono; chi e' passato su WhatsApp sta in «mie»
    'richiami', coalesce((select jsonb_agg(jsonb_build_object('id', d.id, 'prospect_id', d.prospect_id, 'azienda', p.company,
                   'persona', p.name, 'telefono', coalesce(c.numero, d.richiamo->>'numero', p.phone), 'quando', d.richiamo->>'quando',
                   'perche', coalesce(d.richiamo->>'perche', d.perche), 'risposta_il', d.risposta_il, 'esito', d.esito,
                   'lead_testo', d.lead_testo, 'chiamata_id', c.id, 'richiamare_il', c.richiamare_il, 'note', coalesce(c.note, '[]'::jsonb),
                   'whatsapp_il', c.whatsapp_il, 'chiamato_il', c.chiamato_il, 'origine', 'clara') order by c.richiamare_il nulls last, d.risposta_il desc)
                 from clara_decisioni d join prospects p on p.id = d.prospect_id left join chiamate c on c.decisione_id = d.id
                 where d.mossa = 'callback' and d.stato in ('proposta', 'approvata') and d.esito is null and c.esito is null and c.whatsapp_il is null
                   and p.in_mano_a is null and d.creato_il >= now() - interval '21 days'), '[]'::jsonb),
    -- le chiamate di Dre: quelle aggiunte col «+» e quelle passate su WhatsApp (restano sue, come contatti)
    'mie', coalesce((select jsonb_agg(jsonb_build_object('id', c.id, 'chiamata_id', c.id, 'prospect_id', c.prospect_id,
                   'azienda', coalesce(c.azienda, p.company), 'persona', coalesce(c.persona, p.name), 'telefono', coalesce(c.numero, p.phone),
                   'richiamare_il', c.richiamare_il, 'note', coalesce(c.note, '[]'::jsonb), 'creato_il', c.creato_il, 'origine', 'dre',
                   'whatsapp_il', c.whatsapp_il, 'chiamato_il', c.chiamato_il,
                   'fase', coalesce(p.pipeline_stage, p.stage), 'analisi_mandata', p.analysis_sent, 'ultima_risposta', p.last_reply_at,
                   'lead_testo', (select u.lead_testo from clara_decisioni u where u.prospect_id = c.prospect_id order by u.risposta_il desc, u.creato_il desc limit 1),
                   'perche', (select u.perche from clara_decisioni u where u.prospect_id = c.prospect_id order by u.risposta_il desc, u.creato_il desc limit 1)
                 ) order by c.richiamare_il nulls last, coalesce(c.whatsapp_il, c.creato_il) desc)
                 from chiamate c left join prospects p on p.id = c.prospect_id
                 where (c.decisione_id is null or c.whatsapp_il is not null) and c.esito is null), '[]'::jsonb),
    -- i consigli di Clara su cui Dre ha gia' mosso qualcosa (5/11: i nuovi stanno in Relazioni, in Call arrivano al primo gesto)
    'consigli', coalesce((select jsonb_agg(jsonb_build_object('id', d.id, 'prospect_id', d.prospect_id, 'azienda', p.company,
                   'persona', p.name, 'telefono', coalesce(c.numero, d.consiglio->>'numero'), 'perche', d.consiglio->>'perche', 'mossa', d.mossa,
                   'stato', d.stato, 'risposta_il', d.risposta_il, 'lead_testo', d.lead_testo, 'consiglio', d.consiglio,
                   'chiamata_id', c.id, 'richiamare_il', c.richiamare_il, 'note', coalesce(c.note, '[]'::jsonb), 'whatsapp_il', c.whatsapp_il,
                   'chiamato_il', c.chiamato_il, 'origine', 'consiglio') order by d.risposta_il desc)
                 from clara_decisioni d join prospects p on p.id = d.prospect_id left join chiamate c on c.decisione_id = d.id
                 where d.consiglio->>'numero' is not null and d.consiglio->>'esito' is null and c.id is not null and c.esito is null and c.whatsapp_il is null
                   and d.stato not in ('superata', 'scartata') and p.in_mano_a is null
                   and d.creato_il >= now() - interval '21 days'), '[]'::jsonb)
  ) end;
$$;
notify pgrst, 'reload schema';
