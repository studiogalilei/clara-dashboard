-- v115 (4/11 sera, Dre): «WhatsApp» e' un gesto in Call («l'ho passato su WhatsApp, ce l'ho li'»), non un link.
-- La chiamata resta nella lista come contatto suo, con il bottone per aprire la chat. I consigli di Clara
-- («Ti consiglio di chiamare») stanno nella stessa lista, con le note e la programmazione come le altre.
alter table chiamate add column if not exists whatsapp_il timestamptz;

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
                   'whatsapp_il', c.whatsapp_il, 'origine', 'clara') order by c.richiamare_il nulls last, d.risposta_il desc)
                 from clara_decisioni d join prospects p on p.id = d.prospect_id left join chiamate c on c.decisione_id = d.id
                 where d.mossa = 'callback' and d.stato in ('proposta', 'approvata') and d.esito is null and c.esito is null and c.whatsapp_il is null
                   and p.in_mano_a is null and d.creato_il >= now() - interval '21 days'), '[]'::jsonb),
    -- le chiamate di Dre: quelle aggiunte col «+» e quelle passate su WhatsApp (restano sue, come contatti)
    'mie', coalesce((select jsonb_agg(jsonb_build_object('id', c.id, 'chiamata_id', c.id, 'prospect_id', c.prospect_id,
                   'azienda', coalesce(c.azienda, p.company), 'persona', coalesce(c.persona, p.name), 'telefono', coalesce(c.numero, p.phone),
                   'richiamare_il', c.richiamare_il, 'note', coalesce(c.note, '[]'::jsonb), 'creato_il', c.creato_il, 'origine', 'dre',
                   'whatsapp_il', c.whatsapp_il,
                   'fase', coalesce(p.pipeline_stage, p.stage), 'analisi_mandata', p.analysis_sent, 'ultima_risposta', p.last_reply_at,
                   'lead_testo', (select u.lead_testo from clara_decisioni u where u.prospect_id = c.prospect_id order by u.risposta_il desc, u.creato_il desc limit 1),
                   'perche', (select u.perche from clara_decisioni u where u.prospect_id = c.prospect_id order by u.risposta_il desc, u.creato_il desc limit 1)
                 ) order by c.richiamare_il nulls last, coalesce(c.whatsapp_il, c.creato_il) desc)
                 from chiamate c left join prospects p on p.id = c.prospect_id
                 where (c.decisione_id is null or c.whatsapp_il is not null) and c.esito is null), '[]'::jsonb),
    -- i consigli di Clara, con la riga «chiamate» (note, giorno) se Dre l'ha gia' toccata
    'consigli', coalesce((select jsonb_agg(jsonb_build_object('id', d.id, 'prospect_id', d.prospect_id, 'azienda', p.company,
                   'persona', p.name, 'telefono', coalesce(c.numero, d.consiglio->>'numero'), 'perche', d.consiglio->>'perche', 'mossa', d.mossa,
                   'stato', d.stato, 'risposta_il', d.risposta_il, 'lead_testo', d.lead_testo, 'consiglio', d.consiglio,
                   'chiamata_id', c.id, 'richiamare_il', c.richiamare_il, 'note', coalesce(c.note, '[]'::jsonb), 'whatsapp_il', c.whatsapp_il,
                   'origine', 'consiglio') order by d.risposta_il desc)
                 from clara_decisioni d join prospects p on p.id = d.prospect_id left join chiamate c on c.decisione_id = d.id
                 where d.consiglio->>'numero' is not null and d.consiglio->>'esito' is null and c.esito is null and c.whatsapp_il is null
                   and d.stato not in ('superata', 'scartata') and p.in_mano_a is null
                   and d.creato_il >= now() - interval '21 days'), '[]'::jsonb)
  ) end;
$$;
notify pgrst, 'reload schema';
