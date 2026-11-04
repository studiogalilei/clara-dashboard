-- v107 (4/11/2026 pomeriggio): le chiamate di Dre. Dre: «un quick workflow con un + per aggiungermi chiamate da fare:
-- scrivo l'azienda e se c'e' il numero me lo correla, se non c'e' la aggiungo lo stesso e la programmo con la giornata;
-- per ognuna (anche quelle che porta Clara) posso programmare quando richiamare e aggiungere note veloci».
create table if not exists chiamate (
  id            uuid primary key default gen_random_uuid(),
  prospect_id   uuid references prospects(id) on delete set null,
  decisione_id  uuid unique references clara_decisioni(id) on delete cascade,   -- quando e' un «Da chiamare» di Clara
  azienda       text,
  persona       text,
  numero        text,
  richiamare_il date,
  note          jsonb not null default '[]'::jsonb,       -- [{at, testo}]
  esito         text,
  esito_il      timestamptz,
  creato_da     text default 'Dre',
  creato_il     timestamptz not null default now()
);
create index if not exists idx_chiamate_aperte on chiamate (richiamare_il) where esito is null;
alter table chiamate enable row level security;
drop policy if exists "chiamate: i ceo" on chiamate;
create policy "chiamate: i ceo" on chiamate for all to authenticated using ((select sono_ceo())) with check ((select sono_ceo()));

-- la ricerca dice anche il telefono, e trova anche per numero
create or replace function clara_cerca(q text) returns jsonb
language sql stable security definer set search_path = public as $$
  select case when not sono_ceo() or length(btrim(coalesce(q, ''))) < 2 then '[]'::jsonb else coalesce((
    select jsonb_agg(jsonb_build_object('id', p.id, 'azienda', p.company, 'persona', p.name, 'email', p.email, 'citta', p.city,
             'telefono', p.phone, 'fase', coalesce(p.pipeline_stage, p.stage), 'classe', p.classificazione, 'ultima_risposta', p.last_reply_at,
             'analisi_mandata', p.analysis_sent) order by p.last_reply_at desc nulls last)
    from (select * from prospects
          where company ilike '%' || btrim(q) || '%' or name ilike '%' || btrim(q) || '%' or email ilike '%' || btrim(q) || '%'
             or (length(regexp_replace(q, '\D', '', 'g')) >= 5 and regexp_replace(coalesce(phone, ''), '\D', '', 'g') like '%' || regexp_replace(q, '\D', '', 'g') || '%')
          order by last_reply_at desc nulls last limit 30) p
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
notify pgrst, 'reload schema';
