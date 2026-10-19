-- schema_v92 (19/10/2026): i 12 stati della pipeline e «Tutti», il foglio della versione snella.
--
-- I 12 STATI. Dre, 19/10 (decisione definitiva): la pipeline outbound ha dodici stati in quattro
-- gruppi, nient'altro. Un contatto = uno stato; ogni stato ha un responsabile (Dramane o Claude) e
-- una prossima azione di default; le date stanno nel campo data, non in stati nuovi (chi e' «Da
-- ricontattare» a gennaio resta li' con la data). La fonte unica e' src/snella/stati.json: qui ne
-- sta la copia (snella_stati) e scripts/test_invarianti.py controlla che coincidano.
--   snella_stati       i 12 stati: ordine, gruppo, colore, responsabile e azione di default
--   snella_lead        lo stato scelto da Dre punta a snella_stati (niente altri nomi); nuova
--                      colonna «responsabile». La prossima azione resta in prossima_mossa (il testo)
--                      e prossima_il (la data): stesse colonne, nome nuovo solo a schermo.
--                      Le righe che c'erano passano ai nomi nuovi (stati.json, dai_vecchi).
--
-- TUTTI. Dre, 19/10: «io non ho un luogo dove vedere tutti quanti». Lead mostra solo chi ha
-- risposto negli ultimi 60 giorni; lui voleva un foglio con tutti i prospect e gli stati, «un luogo
-- ordinato con visibilita' totale dove lavoriamo entrambi». Deciso: niente foglio a parte (una
-- seconda copia che si stacca), la vista sta nell'app e legge le stesse righe di Lead e della scheda.
--   snella_tutti        una riga per prospect (tutti, ~13.500): lo stato, l'ultima risposta, la
--                       nostra ultima mail, responsabile, prossima azione e data, il telefono.
--                       Lo stato, in ordine: quello scelto da Dre (snella_lead) > quello della
--                       scheda pronta (scripts/schede.py stato_di) > lo stesso calcolo fatto qui
--                       sulle colonne di prospects (snella_stato_calcolato: chi ha risposto piu' di
--                       60 giorni fa, o mai, non ha la scheda pronta).
--   snella_tutti_pagina una pagina gia' filtrata e ordinata (ricerca, stato, campagna) e i conteggi:
--                       il telefono non scarica 13.500 righe, ne chiede 80 alla volta.
--
-- Chi la vede: come le altre tabelle snella, solo i ceo (sono_ceo). La vista e la funzione girano
-- coi permessi di chi legge (security_invoker): valgono le RLS di prospects e delle snella_*.
-- Non scrive su Smartlead.

-- ── i 12 stati ─────────────────────────────────────────────────────────

create table if not exists snella_stati (
  nome          text primary key,
  ordine        int not null unique,
  gruppo        text not null check (gruppo in ('Da gestire oggi', 'Opportunità', 'In attesa', 'Chiusi')),
  tono          text not null,
  responsabile  text not null check (responsabile in ('Dramane', 'Claude')),
  azione        text not null check (length(btrim(azione)) > 0),
  significa     text not null
);
comment on table snella_stati is 'I 12 stati della pipeline outbound (Dre, 19/10). Copia di src/snella/stati.json: si cambia li'' e qui insieme (la prova lo controlla).';

insert into snella_stati (nome, ordine, gruppo, tono, responsabile, azione, significa) values
  ('Da chiamare',       1,  'Da gestire oggi', 'ok',     'Dramane', 'Chiamare', 'Ha chiesto una chiamata o lasciato il numero'),
  ('Da rispondere',     2,  'Da gestire oggi', 'attesa', 'Claude',  'Rispondere con l''analisi', 'Ha risposto, fatto una domanda o chiesto informazioni'),
  ('Analisi inviata',   3,  'Da gestire oggi', 'noi',    'Claude',  'Fare follow-up', 'Ha ricevuto l''analisi, aspettiamo'),
  ('Call fissata',      4,  'Opportunità',     'opp',    'Dramane', 'Fare la call', 'Appuntamento in calendario'),
  ('Proposta inviata',  5,  'Opportunità',     'opp',    'Dramane', 'Seguire la proposta', 'Call fatta, proposta mandata'),
  ('Cliente acquisito', 6,  'Opportunità',     'ok',     'Dramane', 'Fermare le campagne e fare l''onboarding', 'Ha firmato'),
  ('Da ricontattare',   7,  'In attesa',       'giallo', 'Claude',  'Riprendere alla data', 'Ha chiesto di sentirsi più avanti'),
  ('Assente',           8,  'In attesa',       'neutro', 'Claude',  'Riprendere al rientro', 'Fuori ufficio'),
  ('Nessuna risposta',  9,  'In attesa',       'neutro', 'Claude',  'Continuare la sequenza', 'Non ha mai risposto'),
  ('Non interessato',   10, 'Chiusi',          'no',     'Claude',  'Fermare la sequenza', 'Ha rifiutato (anche casella morta, persona sbagliata senza alternativa, fuori target: il motivo nella prossima azione)'),
  ('Perso',             11, 'Chiusi',          'no',     'Claude',  'Fermare la sequenza', 'Opportunità chiusa senza vendita'),
  ('Non contattare',    12, 'Chiusi',          'stop',   'Claude',  'Nessun messaggio, mai più', 'Ha chiesto di non ricevere messaggi: blocco permanente')
on conflict (nome) do update set ordine = excluded.ordine + 100, gruppo = excluded.gruppo, tono = excluded.tono,
  responsabile = excluded.responsabile, azione = excluded.azione, significa = excluded.significa;
update snella_stati set ordine = ordine - 100 where ordine > 100;   -- l'ordine e' unico: si sposta in due passi

alter table snella_stati enable row level security;
drop policy if exists "snella stati: i ceo leggono" on snella_stati;
create policy "snella stati: i ceo leggono" on snella_stati for select to authenticated using ((select sono_ceo()));

-- il nome nuovo di uno stato vecchio (stati.json, dai_vecchi); null se non c'e' un nome solo
-- («Nel Workspace» dipende dalla pipeline: si ricalcola)
create or replace function snella_nome_nuovo(vecchio text) returns text
language sql immutable parallel safe as $$
  select case vecchio
    when 'No grazie' then 'Non interessato'
    when 'Non scrivere più' then 'Non contattare'
    when 'Fuori ufficio' then 'Assente'
    when 'Conoscitiva' then 'Call fissata'
    when 'Analisi mandata' then 'Analisi inviata'
    when 'Vuole sentirti' then 'Da chiamare'
    when 'Follow-up' then 'Analisi inviata'
    when 'Da riprendere' then 'Da ricontattare'
    when 'In conversazione' then 'Da rispondere'
    when 'Fuori target' then 'Non interessato'
    when 'Casella morta' then 'Non interessato'
    when 'In campagna' then 'Nessuna risposta'
  end
$$;

-- snella_lead: lo stato di Dre e' uno dei 12, e il responsabile
alter table snella_lead drop constraint if exists snella_lead_stato_check;
update snella_lead set stato = snella_nome_nuovo(stato)
  where stato is not null and stato not in (select nome from snella_stati) and snella_nome_nuovo(stato) is not null;
update snella_lead set stato = null where stato is not null and stato not in (select nome from snella_stati);
alter table snella_lead drop constraint if exists snella_lead_stato_fkey;
alter table snella_lead add constraint snella_lead_stato_fkey foreign key (stato) references snella_stati (nome) on update cascade;
alter table snella_lead add column if not exists responsabile text
  check (responsabile is null or responsabile in ('Dramane', 'Claude'));
comment on column snella_lead.prossima_mossa is 'La prossima azione scritta da Dre (a schermo «Prossima azione»). Vuota: vale quella di default dello stato.';
comment on column snella_lead.prossima_il is 'La data della prossima azione.';
comment on column snella_lead.responsabile is 'Chi la fa: Dramane o Claude. Vuoto: vale quello di default dello stato (snella_stati).';

-- ── Tutti ──────────────────────────────────────────────────────────────

drop view if exists snella_tutti;   -- si rifa' sotto (le funzioni che usa cambiano forma)

-- la ricerca senza accenti e maiuscole (l'estensione unaccent qui non c'e')
create or replace function snella_norm(t text) returns text
language sql immutable parallel safe as $$
  select translate(lower(coalesce(t, '')), 'àáâãäåèéêëìíîïòóôõöùúûüçñ''’', 'aaaaaaeeeeiiiiooooouuuucn  ')
$$;

-- lo stato dalle colonne di prospects, per chi non ha la scheda pronta: lo stesso ordine di
-- scripts/schede.py stato_di, senza le cose che solo la scheda sa (il testo della sua ultima mail,
-- l'intento, l'agenda: per chi ha risposto negli ultimi 60 giorni vale la scheda).
create or replace function snella_stato_calcolato(p prospects) returns text
language sql stable parallel safe as $$
  select case
    when p.classificazione in ('soppresso', 'nervoso') then 'Non contattare'
    when p.stage = 'cliente' or p.pipeline_stage in ('cliente', 'prova', 'avvio') then 'Cliente acquisito'
    when p.pipeline_stage = 'perso' then 'Perso'
    when p.pipeline_stage in ('conoscitiva', 'tecnica') or (p.stage = 'call_fissata' and p.last_reply_at is not null) then 'Call fissata'
    when p.last_reply_at is null then 'Nessuna risposta'
    when p.classificazione in ('negativo', 'fuori_target') then 'Non interessato'
    when p.stage = 'perso' then 'Perso'
    when p.classificazione = 'ooo' then 'Assente'
    when p.classificazione = 'rinvio' then 'Da ricontattare'
    when p.classificazione = 'positivo' then 'Analisi inviata'
    else 'Da rispondere'
  end
$$;

-- la prossima azione di default di uno stato e la sua data (schede.prossima_mossa, senza l'agenda)
drop function if exists snella_mossa(text, prospects);
create or replace function snella_mossa(stato text, p prospects) returns table (mossa text, il date)
language sql stable parallel safe as $$
  select
    case when stato = 'Non interessato' and p.classificazione = 'fuori_target' then st.azione || ': fuori target'
         else st.azione end,
    case stato
      when 'Analisi inviata' then p.followup_due
      when 'Da ricontattare' then coalesce(p.next_action_date, p.followup_due)
      when 'Assente' then p.ooo_until
    end
  from snella_stati st where st.nome = stato
$$;

-- la nostra ultima mail per lead. Passa da una funzione coi permessi del proprietario perche' la
-- RLS di interactions (una sottoquery su prospects per ogni riga) costava 1,5 secondi su 2.500
-- mail: qui il filtro e' uno solo, sono_ceo(), e prospects resta filtrata dalla sua RLS nella vista.
create or replace function snella_ultime_nostre() returns table (prospect_id uuid, at timestamptz)
language sql stable security definer set search_path = public as $$
  select i.prospect_id, max(i.at) from interactions i
  where i.kind = 'email_out' and (select sono_ceo())
  group by i.prospect_id
$$;
revoke all on function snella_ultime_nostre() from public, anon;
grant execute on function snella_ultime_nostre() to authenticated;

create view snella_tutti with (security_invoker = on) as
with nostre as (
  select * from snella_ultime_nostre()
), righe as (
  select
    p.id as prospect_id,
    nullif(btrim(coalesce(nullif(btrim(p.company), ''), nullif(btrim(p.name), ''))), '') as azienda,
    coalesce(nullif(btrim(s.persona), ''), nullif(btrim(p.name), '')) as persona,
    p.email,
    p.campaign as campagna,
    p, s, l,
    -- lo stato del sistema: la scheda (coi nomi nuovi; una scheda non ancora rifatta col nome vecchio
    -- si traduce), se no il calcolo sulle colonne
    case when s.stato in (select nome from snella_stati) then s.stato
         else coalesce(snella_nome_nuovo(s.stato), snella_stato_calcolato(p)) end as stato_sistema,
    s.stato in (select nome from snella_stati) as scheda_nuova,
    coalesce(s.ultima_risposta, p.last_reply_at) as ultima_risposta,
    n.at as ultima_nostra,
    (p.last_reply_at is not null or s.ultima_risposta is not null) as risposto,
    s.prospect_id is not null as scheda_pronta,
    coalesce(nullif(s.scheda -> 'telefoni' -> 0 ->> 'numero', ''), nullif(btrim(p.phone), '')) as telefono
  from prospects p
  left join snella_schede s on s.prospect_id = p.id
  left join snella_lead l on l.prospect_id = p.id
  left join nostre n on n.prospect_id = p.id
  where (select sono_ceo())
), con_stato as (
  select r.*, coalesce((r.l).stato, r.stato_sistema) as stato from righe r
)
select
  r.prospect_id, r.azienda, r.persona, r.email, r.campagna,
  r.stato, r.stato_sistema, (r.l).stato is not null as stato_tuo,
  st.gruppo, st.ordine,
  r.ultima_risposta, r.ultima_nostra,
  greatest(r.ultima_risposta, r.ultima_nostra) as novita,
  r.risposto, r.scheda_pronta, r.telefono,
  coalesce((r.l).responsabile, st.responsabile) as responsabile,
  (r.l).responsabile is not null as responsabile_tuo,
  -- la prossima azione: quella scritta da Dre; se no quella della scheda (se lo stato e' ancora
  -- quello della scheda, rifatta coi nomi nuovi), se no quella di default dello stato
  case when nullif(btrim((r.l).prossima_mossa), '') is not null then (r.l).prossima_mossa
       when r.scheda_nuova and r.stato = r.stato_sistema and nullif((r.s).scheda -> 'prossima' ->> 'mossa', '') is not null
         then (r.s).scheda -> 'prossima' ->> 'mossa'
       else (select m.mossa from snella_mossa(r.stato, r.p) m) end as mossa,
  coalesce((r.l).prossima_il,
    case when nullif(btrim((r.l).prossima_mossa), '') is not null then null
         when r.scheda_nuova and r.stato = r.stato_sistema then nullif((r.s).scheda -> 'prossima' ->> 'il', '')::date
         else (select m.il from snella_mossa(r.stato, r.p) m) end) as mossa_il,
  nullif(btrim((r.l).prossima_mossa), '') is not null as mossa_tua,
  case when (r.l).chiamata = 'richiamare' then (r.l).richiamare_il end as richiamare_il,
  (r.l).chiamata as chiamata,
  snella_norm(concat_ws(' ', (r.p).company, (r.p).name, r.persona, (r.p).email)) as cerca
from con_stato r
left join snella_stati st on st.nome = r.stato;

comment on view snella_tutti is 'La versione snella (19/10): «Tutti», una riga per prospect con uno dei 12 stati, responsabile e prossima azione. Solo i ceo. Si butta con Clara nuova.';
revoke all on snella_tutti from anon;
grant select on snella_tutti to authenticated;

-- una pagina e i conteggi, in una chiamata sola (il telefono fa un viaggio, non quattro).
--   q          la ricerca (azienda, persona, mail), parole separate, tutte devono esserci
--   stato      uno stato o null; campagna una campagna, '' per «senza campagna», null tutte
--   anche_mai  true: anche chi non ha mai risposto
--   conta      false sulle pagine dopo la prima: i conteggi non servono
-- I conteggi per stato ignorano il filtro di stato (cosi' i pallini dicono quanti ce ne sono in
-- ciascuno), quelli per campagna ignorano il filtro di campagna.
create or replace function snella_tutti_pagina(q text default '', stato text default null, campagna text default null,
  anche_mai boolean default false, da int default 0, quanti int default 60, conta boolean default true)
returns jsonb
language plpgsql stable security invoker set search_path = public as $$
declare
  w text[] := array_remove(regexp_split_to_array(btrim(snella_norm(q)), '\s+'), '');
  ids uuid[];
  conti jsonb;
  righe jsonb;
begin
  -- prima solo le colonne che servono a filtrare, contare e ordinare (la pagina e i conteggi);
  -- poi la prossima azione e il telefono, le parti care, per le sole righe della pagina (in due
  -- passi perche' il pianificatore, in uno, li calcolava per tutte le 13.500)
  with base as (
    select t.prospect_id, t.azienda, t.campagna, t.stato, t.novita from snella_tutti t
    where (anche_mai or t.risposto)
      and (cardinality(w) = 0 or not exists (select 1 from unnest(w) x where position(x in t.cerca) = 0))
  ), scelte as (
    select * from base b
    where (snella_tutti_pagina.stato is null or b.stato = snella_tutti_pagina.stato)
      and (snella_tutti_pagina.campagna is null or coalesce(b.campagna, '') = snella_tutti_pagina.campagna)
  )
  select
    (select array_agg(x.prospect_id order by x.novita desc nulls last, x.azienda nulls last, x.prospect_id) from (
       select * from scelte order by novita desc nulls last, azienda nulls last, prospect_id
       offset greatest(da, 0) limit least(greatest(quanti, 1), 200)) x),
    case when conta then jsonb_build_object(
      'totale', (select count(*) from scelte),
      'stati', (select coalesce(jsonb_object_agg(k, n), '{}'::jsonb) from (
                 select b.stato as k, count(*) as n from base b
                 where snella_tutti_pagina.campagna is null or coalesce(b.campagna, '') = snella_tutti_pagina.campagna
                 group by b.stato) x),
      'campagne', (select coalesce(jsonb_agg(jsonb_build_object('nome', k, 'n', n) order by n desc, k), '[]'::jsonb) from (
                 select coalesce(b.campagna, '') as k, count(*) as n from base b
                 where snella_tutti_pagina.stato is null or b.stato = snella_tutti_pagina.stato
                 group by 1) x)) end
  into ids, conti;

  select coalesce(jsonb_agg(to_jsonb(r) order by array_position(ids, r.prospect_id)), '[]'::jsonb) into righe from (
    select t.prospect_id, t.azienda, t.persona, t.email, t.campagna, t.stato, t.stato_tuo, t.gruppo, t.ultima_risposta,
           t.ultima_nostra, t.novita, t.risposto, t.scheda_pronta, t.telefono, t.responsabile, t.responsabile_tuo,
           t.mossa, t.mossa_il, t.mossa_tua, t.richiamare_il
    from snella_tutti t where t.prospect_id = any(coalesce(ids, '{}'::uuid[]))) r;

  return jsonb_build_object('righe', righe) || coalesce(conti, '{}'::jsonb);
end $$;

comment on function snella_tutti_pagina is 'La versione snella (19/10): una pagina di «Tutti» (ricerca, stato, campagna) e i conteggi. Solo lettura, solo i ceo.';
revoke all on function snella_tutti_pagina(text, text, text, boolean, int, int, boolean) from public, anon;
grant execute on function snella_tutti_pagina(text, text, text, boolean, int, int, boolean) to authenticated;

notify pgrst, 'reload schema';
