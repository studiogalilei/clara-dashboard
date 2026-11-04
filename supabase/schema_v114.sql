-- v114 (4/11): le note di Dre si modificano («così non ne creo di nuove, modifico sempre l'unica»).
drop policy if exists "snella note: i ceo modificano" on snella_note;
create policy "snella note: i ceo modificano" on snella_note for update to authenticated using ((select sono_ceo())) with check ((select sono_ceo()));
create or replace function clara_relazione(chi uuid) returns jsonb
language sql stable security definer set search_path = public as $$
  select case when not sono_ceo() then '{}'::jsonb else jsonb_build_object(
    'lead', (select jsonb_build_object('id', p.id, 'azienda', p.company, 'persona', p.name, 'ruolo', p.role, 'email', p.email,
               'citta', p.city, 'settore', p.sector, 'telefono', p.phone, 'sito', p.website, 'analisi_pdf', p.analysis_pdf,
               'analisi_mandata', p.analysis_sent, 'analisi_il', p.analysis_sent_at, 'fase', coalesce(p.pipeline_stage, p.stage),
               'classe', p.classificazione, 'ultima_risposta', p.last_reply_at, 'fuori', p.fuori, 'no_followup', p.no_followup,
               'fonte', p.source, 'fit', p.enriched->'google_fit'->>'verdetto', 'fit_motivo', p.enriched->'google_fit'->>'motivo',
               'cosa_fa', p.enriched->'google_fit'->>'cosa_fa', 'campagna', p.campaign,
               'in_mano_a', p.in_mano_a, 'in_mano_motivo', p.in_mano_motivo, 'in_mano_il', p.in_mano_il,
               'altre_email', coalesce(to_jsonb(p.email_alt), '[]'::jsonb))
             from prospects p where p.id = chi),
    'filo', coalesce((select jsonb_agg(jsonb_build_object('at', i.at, 'tipo', i.kind, 'testo', i.body, 'casella', i.casella) order by i.at)
             from (select * from interactions where prospect_id = chi and kind in ('email_in', 'email_out') order by at desc limit 60) i), '[]'::jsonb),
    'decisioni', coalesce((select jsonb_agg(jsonb_build_object('id', d.id, 'risposta_il', d.risposta_il, 'mossa', d.mossa, 'owner', d.owner,
                   'testo', coalesce(d.testo_finale, d.testo), 'perche', d.perche, 'stato', d.stato, 'inviata_il', d.inviata_il,
                   'esito', d.esito, 'dre_giudizio', d.dre_giudizio, 'dre_nota', d.dre_nota, 'creato_il', d.creato_il) order by d.creato_il desc)
                   from clara_decisioni d where d.prospect_id = chi), '[]'::jsonb),
    'agenda', coalesce((select jsonb_agg(jsonb_build_object('at', a.at, 'tipo', a.tipo, 'titolo', a.titolo, 'link', a.link) order by a.at desc)
               from agenda a where a.prospect_id = chi), '[]'::jsonb),
    'note', coalesce((select jsonb_agg(jsonb_build_object('id', n.id, 'at', n.at, 'tipo', n.tipo, 'testo', n.testo, 'autore', n.autore_nome) order by n.at desc)
             from (select * from snella_note where prospect_id = chi order by at desc limit 30) n), '[]'::jsonb),
    'scheda', (select to_jsonb(s) from snella_lead s where s.prospect_id = chi)
  ) end;
$$;
notify pgrst, 'reload schema';
