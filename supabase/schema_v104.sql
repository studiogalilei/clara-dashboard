-- schema_v104 (4/11/2026, notte): IL DESK. Dre, 3/11 sera: «buttiamo al cesso l'intero sistema fatto
-- finora e mi crei una nuova dashboard per interagire al posto di questo... questo sistema chiude tutti
-- i buchi e lascia spazio solo alle call». Clara decide e scrive su ogni risposta (clara_decisioni),
-- Dre nel Desk fa Invia / Modifica / No e segna gli esiti delle call; il postino nuovo (clara_manda.py)
-- manda solo quello che lui ha approvato. Il vecchio automatismo delle risposte si spegne.

-- ── la decisione ha una vita: proposta -> approvata -> in_invio -> inviata; oppure scartata/superata ──
alter table clara_decisioni
  add column if not exists stato         text not null default 'proposta'
    check (stato in ('proposta', 'approvata', 'in_invio', 'inviata', 'scartata', 'superata', 'fatta')),
  add column if not exists testo_finale  text,            -- il testo come l'ha lasciato Dre (se l'ha toccato)
  add column if not exists approvata_il  timestamptz,
  add column if not exists approvata_da  text,
  add column if not exists inviata_il    timestamptz,
  add column if not exists invio         jsonb,           -- campagna, lead, risposta di Smartlead
  add column if not exists verificata_il timestamptz,     -- la ricevuta: riletta nel filo vero
  add column if not exists errore        text,
  add column if not exists esito         text,            -- esito di una call o di un richiamo, scelto da Dre
  add column if not exists esito_il      timestamptz;
create index if not exists clara_decisioni_stato on clara_decisioni (stato, creato_il desc);
create index if not exists clara_decisioni_lead on clara_decisioni (prospect_id, risposta_il desc);

drop policy if exists "clara decisioni: i ceo scrivono" on clara_decisioni;
create policy "clara decisioni: i ceo scrivono" on clara_decisioni
  for update to authenticated using ((select sono_ceo())) with check ((select sono_ceo()));

-- ── la coda del Desk: l'ultima decisione per ogni relazione, con la scheda ─────────────────────
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
      'lead_testo', u.lead_testo, 'approvata_il', u.approvata_il, 'inviata_il', u.inviata_il, 'verificata_il', u.verificata_il,
      'errore', u.errore, 'esito', u.esito, 'esito_il', u.esito_il, 'creato_il', u.creato_il, 'versione', u.versione,
      'dollari', (u.uso->>'dollari')::numeric, 'dre_giudizio', u.dre_giudizio,
      'azienda', p.company, 'persona', p.name, 'ruolo', p.role, 'email', p.email, 'citta', p.city, 'settore', p.sector,
      'telefono', p.phone, 'sito', p.website, 'analisi_pdf', p.analysis_pdf is not null, 'analisi_mandata', p.analysis_sent,
      'fase', coalesce(p.pipeline_stage, p.stage), 'classe', p.classificazione, 'ultima_risposta', p.last_reply_at,
      'prossima_call', (select min(a.at) from agenda a where a.prospect_id = p.id and a.at > now())
    ) order by u.risposta_il desc)
    from ult u join prospects p on p.id = u.prospect_id
  ), '[]'::jsonb) end;
$$;

-- ── una relazione intera: scheda, filo (CRM), decisioni, agenda, note ─────────────────────────
create or replace function clara_relazione(chi uuid) returns jsonb
language sql stable security definer set search_path = public as $$
  select case when not sono_ceo() then '{}'::jsonb else jsonb_build_object(
    'lead', (select jsonb_build_object('id', p.id, 'azienda', p.company, 'persona', p.name, 'ruolo', p.role, 'email', p.email,
               'citta', p.city, 'settore', p.sector, 'telefono', p.phone, 'sito', p.website, 'analisi_pdf', p.analysis_pdf,
               'analisi_mandata', p.analysis_sent, 'analisi_il', p.analysis_sent_at, 'fase', coalesce(p.pipeline_stage, p.stage),
               'classe', p.classificazione, 'ultima_risposta', p.last_reply_at, 'fuori', p.fuori, 'no_followup', p.no_followup,
               'fonte', p.source, 'fit', p.enriched->'google_fit'->>'verdetto', 'fit_motivo', p.enriched->'google_fit'->>'motivo',
               'cosa_fa', p.enriched->'google_fit'->>'cosa_fa', 'campagna', p.campaign)
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

-- ── cercare un'azienda ──────────────────────────────────────────────────────────────────────────
create or replace function clara_cerca(q text) returns jsonb
language sql stable security definer set search_path = public as $$
  select case when not sono_ceo() or length(btrim(coalesce(q, ''))) < 2 then '[]'::jsonb else coalesce((
    select jsonb_agg(jsonb_build_object('id', p.id, 'azienda', p.company, 'persona', p.name, 'email', p.email, 'citta', p.city,
             'fase', coalesce(p.pipeline_stage, p.stage), 'classe', p.classificazione, 'ultima_risposta', p.last_reply_at,
             'analisi_mandata', p.analysis_sent) order by p.last_reply_at desc nulls last)
    from (select * from prospects
          where company ilike '%' || btrim(q) || '%' or name ilike '%' || btrim(q) || '%' or email ilike '%' || btrim(q) || '%'
          order by last_reply_at desc nulls last limit 30) p
  ), '[]'::jsonb) end;
$$;

-- ── le call: prossime conoscitive e richiami ────────────────────────────────────────────────────
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
                   and d.creato_il >= now() - interval '21 days'), '[]'::jsonb)
  ) end;
$$;

-- ── le operazioni: il postino nuovo acceso, il vecchio automatismo delle risposte spento ─────────
insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ordine, attiva) values
  ('clara_manda', 'Clara manda quello che Dre approva',
   'Il postino del Desk: prende le decisioni approvate da Dre in clara_decisioni e le manda nel thread di Smartlead, con analisi e presentazione quando servono. Rilegge il filo e segna la ricevuta. Ogni 5 minuti e su richiesta dal Desk.',
   'python3 scripts/clara_manda.py', 5, 29, true)
on conflict (chiave) do nothing;

-- 4/11: da oggi ogni mail parte da un'approvazione di Dre nel Desk. Il lampo si ferma all'analisi
-- (scripts/lampo.py guarda «bozze»); prima_risposta e il postino vecchio non girano piu'.
update operazioni set attiva = false where chiave in ('prima_risposta', 'seguiti', 'bozze', 'strade', 'followup', 'manda');
