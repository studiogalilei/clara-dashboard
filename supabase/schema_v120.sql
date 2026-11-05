-- v120 (5/11, Dre): «voglio la possibilità di scrivere solo in un box di note, non in più box; rimane giallo e ci
-- scrivo e basta». La nota di Dre su un lead e' UNA (l'ultima sua, tipo 'nota'); i gesti del sistema (prende in mano,
-- WhatsApp, esiti, non interessato) restano scritti per Clara ma con tipo 'gesto': non sono note sue e non si vedono nel box.
alter table snella_note drop constraint if exists snella_note_tipo_check;
alter table snella_note add constraint snella_note_tipo_check check (tipo in ('nota', 'chiamata', 'gesto'));

-- l'arretrato: le note che erano gesti del sistema diventano gesti; via il prefisso «Chiamata: » dalle note di Dre
update snella_note set tipo = 'gesto'
 where tipo = 'nota' and (
   testo like 'Dre prende in mano%' or testo like 'Dre ridà%' or testo = 'Scritto su WhatsApp' or testo = 'Chiamata: Scritto su WhatsApp'
   or testo like 'Chiamata di Dre:%' or testo like 'Dal sistema:%' or testo like 'Non interessato: l''ho sentito%' or testo like 'Dre lo riapre%'
   or testo like 'Call in calendario collegata%' or coalesce(autore_nome, '') in ('Sistema'));
update snella_note set testo = substr(testo, length('Chiamata: ') + 1) where tipo = 'nota' and testo like 'Chiamata: %' and length(btrim(substr(testo, 11))) > 0;
-- le due «Scritto su WhatsApp» sulle chiamate (Dre, 5/11: «elimina le due note scritto su WhatsApp»)
update chiamate set note = coalesce((select jsonb_agg(n) from jsonb_array_elements(note) n where n->>'testo' <> 'Scritto su WhatsApp'), '[]'::jsonb)
 where note @> '[{"testo": "Scritto su WhatsApp"}]'::jsonb;

-- i gesti scritti dal database
create or replace function clara_prendi(chi uuid, motivo text default null, lascia boolean default false) returns jsonb
language plpgsql security definer set search_path = public as $$
declare n int := 0;
begin
  if not sono_ceo() then return jsonb_build_object('ok', false, 'perche', 'solo il ceo'); end if;
  if lascia then
    update prospects set in_mano_a = null, in_mano_motivo = null, in_mano_il = null where id = chi;
    insert into snella_note (prospect_id, tipo, testo) values (chi, 'gesto', 'Dre ridà la relazione a Clara.');
    return jsonb_build_object('ok', true, 'in_mano_a', null);
  end if;
  update prospects set in_mano_a = 'Dre', in_mano_motivo = nullif(btrim(coalesce(motivo, '')), ''), in_mano_il = now() where id = chi;
  update clara_decisioni set stato = 'scartata', dre_nota = 'Me ne occupo io' || coalesce(': ' || nullif(btrim(motivo), ''), ''), dre_il = now(), errore = null
    where prospect_id = chi and stato in ('proposta', 'approvata');
  get diagnostics n = row_count;
  insert into snella_note (prospect_id, tipo, testo) values (chi, 'gesto', 'Dre prende in mano la relazione' || coalesce(': ' || nullif(btrim(motivo), ''), '') || '. Clara si ferma qui.');
  return jsonb_build_object('ok', true, 'in_mano_a', 'Dre', 'chiuse', n);
end $$;

create or replace function clara_non_interessato(chi uuid, riapri boolean default false) returns jsonb
language plpgsql security definer set search_path = public as $$
begin
  if not sono_ceo() then return jsonb_build_object('ok', false, 'perche', 'solo il ceo'); end if;
  if riapri then
    update prospects set no_followup = false, lost_reason = null where id = chi and lost_reason like 'Non interessato%';
    insert into snella_note (prospect_id, tipo, testo) values (chi, 'gesto', 'Dre lo riapre: non è più «non interessato».');
    return jsonb_build_object('ok', true, 'no_followup', false);
  end if;
  update prospects set no_followup = true, lost_reason = 'Non interessato (Dre, al telefono, ' || to_char(now() at time zone 'Europe/Rome', 'DD/MM') || ')',
    in_mano_a = coalesce(in_mano_a, 'Dre') where id = chi;
  update clara_decisioni set stato = 'scartata', dre_nota = 'Non interessato (Dre, al telefono)', dre_il = now()
    where prospect_id = chi and stato in ('proposta', 'approvata');
  insert into snella_note (prospect_id, tipo, testo) values (chi, 'gesto', 'Non interessato: l''ho sentito al telefono. Non lo contattiamo più.');
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

-- la nota di Dre (una) accanto a ogni chiamata, anche per chi e' in scheda
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
                   'lead_testo', d.lead_testo, 'chiamata_id', c.id, 'richiamare_il', c.richiamare_il, 'note', coalesce(c.note, '[]'::jsonb), 'nota', (select jsonb_build_object('id', n.id, 'testo', n.testo, 'at', n.at) from snella_note n
                              where n.prospect_id = d.prospect_id and n.tipo = 'nota' and coalesce(n.autore_nome, '') not in ('Achille', 'Clara', 'Sistema') order by n.at desc limit 1),
                   'whatsapp_il', c.whatsapp_il, 'chiamato_il', c.chiamato_il, 'origine', 'clara') order by c.richiamare_il nulls last, d.risposta_il desc)
                 from clara_decisioni d join prospects p on p.id = d.prospect_id left join chiamate c on c.decisione_id = d.id
                 where d.mossa = 'callback' and d.stato in ('proposta', 'approvata') and d.esito is null and c.esito is null and c.whatsapp_il is null
                   and p.in_mano_a is null and d.creato_il >= now() - interval '21 days'), '[]'::jsonb),
    -- le chiamate di Dre: quelle aggiunte col «+» e quelle passate su WhatsApp (restano sue, come contatti)
    'mie', coalesce((select jsonb_agg(jsonb_build_object('id', c.id, 'chiamata_id', c.id, 'prospect_id', c.prospect_id,
                   'azienda', coalesce(c.azienda, p.company), 'persona', coalesce(c.persona, p.name), 'telefono', coalesce(c.numero, p.phone),
                   'richiamare_il', c.richiamare_il, 'note', coalesce(c.note, '[]'::jsonb), 'creato_il', c.creato_il, 'origine', 'dre',
                   'nota', (select jsonb_build_object('id', n.id, 'testo', n.testo, 'at', n.at) from snella_note n
                              where n.prospect_id = c.prospect_id and n.tipo = 'nota' and coalesce(n.autore_nome, '') not in ('Achille', 'Clara', 'Sistema') order by n.at desc limit 1),
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
                   'nota', (select jsonb_build_object('id', n.id, 'testo', n.testo, 'at', n.at) from snella_note n
                              where n.prospect_id = d.prospect_id and n.tipo = 'nota' and coalesce(n.autore_nome, '') not in ('Achille', 'Clara', 'Sistema') order by n.at desc limit 1),
                   'chiamato_il', c.chiamato_il, 'origine', 'consiglio') order by d.risposta_il desc)
                 from clara_decisioni d join prospects p on p.id = d.prospect_id left join chiamate c on c.decisione_id = d.id
                 where d.consiglio->>'numero' is not null and d.consiglio->>'esito' is null and c.id is not null and c.esito is null and c.whatsapp_il is null
                   and d.stato not in ('superata', 'scartata') and p.in_mano_a is null
                   and d.creato_il >= now() - interval '21 days'), '[]'::jsonb)
  ) end;
$$;
notify pgrst, 'reload schema';

-- e nella coda, per la scheda dei consigli in Relazioni
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
      'nota', (select jsonb_build_object('id', n.id, 'testo', n.testo, 'at', n.at) from snella_note n
                 where n.prospect_id = p.id and n.tipo = 'nota' and coalesce(n.autore_nome, '') not in ('Achille', 'Clara', 'Sistema') order by n.at desc limit 1),
      'chiamata', (select jsonb_build_object('id', c.id, 'chiamato_il', c.chiamato_il, 'whatsapp_il', c.whatsapp_il, 'richiamare_il', c.richiamare_il, 'esito', c.esito)
                   from chiamate c where c.decisione_id = u.id)
    ) order by u.risposta_il desc)
    from ult u join prospects p on p.id = u.prospect_id
  ), '[]'::jsonb) end;
$$;
notify pgrst, 'reload schema';
