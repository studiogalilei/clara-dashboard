-- COSA VEDE OGNUNO (decisione Dre 28/9, strada A scelta il 29/9)
--
-- Prima: chi non era ceo vedeva solo le aziende col suo nome in «chi segue»
-- (11 su 13.230) piu' i clienti. Lorenzo, Carlo, Salvatore, Alex e Okay aprivano
-- il Workspace e trovavano 16-18 aziende e zero bozze.
--
-- Adesso si vede per AREA di lavoro, un campo nuovo e separato dal reparto (il
-- reparto veste l'app con il suo colore, 26/9, e non si tocca):
--   direzione  tutto;
--   vendita    la vendita: chi ha risposto e non e' ancora cliente, e le call
--              conoscitive e tecniche; piu' le bozze senza proprietario;
--   marketing  i clienti in avvio, prova e canone, e le aziende con un progetto Ads;
--   web        le aziende con un progetto sito o landing;
--   software   quello che segue (chi segue, le sue call).
-- Restano le regole di prima (chi segue, i clienti in tecnica/avvio/prova/cliente,
-- le aziende delle proprie call): le policy si sommano.
--
-- E sparisce il controllo riga per riga delle call (ho_una_call(id), 13.230 volte
-- a lettura per chi non e' ceo): l'elenco delle aziende delle mie call si calcola
-- una volta sola per lettura.

alter table profili add column if not exists area text
  check (area is null or area in ('direzione', 'vendita', 'marketing', 'web', 'software'));

update profili set area = 'direzione' where id in ('43095060-b873-4d29-825b-55522f26af55', '47f779aa-e952-468f-b6ce-5df848944092');  -- Dre, Giacomo
update profili set area = 'vendita'   where id = 'a8eff3b6-b553-4d56-90fb-3c17eac6822d';   -- Lorenzo
update profili set area = 'marketing' where id in ('4d5a857e-f0b3-43d3-8b1a-8e24c7102d8a', '880f4e94-2f2f-48da-aa28-ddac04b7d61f');  -- Carlo, Salvatore
update profili set area = 'web'       where id = 'e6276dd0-b940-48fc-a808-09b05ab3830b';   -- Alex
update profili set area = 'software'  where id = 'f5431303-0d75-4702-a108-9660b0eeb372';   -- Okay

create or replace function mia_area() returns text
language sql stable security definer set search_path = public as $$
  select area from profili where id = uid_eff();
$$;

create or replace function aziende_delle_mie_call() returns uuid[]
language sql stable security definer set search_path = public as $$
  select coalesce(array_agg(distinct a.prospect_id), '{}')
  from agenda a
  where a.prospect_id is not null
    and (a.owner = (select uid_eff()) or a.owner is null)
    and a.at > now() - interval '30 days';
$$;

drop policy if exists "aziende: quelle con cui ho una call" on prospects;
create policy "aziende: quelle con cui ho una call" on prospects for select to authenticated
  using (id = any ((select aziende_delle_mie_call())::uuid[]));

drop policy if exists "aziende della mia area" on prospects;
create policy "aziende della mia area" on prospects for select to authenticated using (
  case (select mia_area())
    when 'direzione' then true
    when 'vendita' then (not coalesce(fuori, false) and last_reply_at is not null)
                     or (coalesce(fuori, false) and pipeline_stage in ('conoscitiva', 'tecnica'))
    when 'marketing' then (coalesce(fuori, false) and pipeline_stage in ('avvio', 'prova', 'cliente'))
                     or exists (select 1 from progetti g where g.prospect_id = prospects.id and g.natura ilike '%ads%')
    when 'web' then exists (select 1 from progetti g where g.prospect_id = prospects.id
                            and (g.natura ilike '%sito%' or g.natura ilike '%landing%'))
    else false
  end
);

-- chi vede per area deve anche poter lavorare: segnare «Fatto, l'ho mandata»,
-- togliere l'attesa, scrivere una nota
drop policy if exists "aziende: scrive la mia area" on prospects;
create policy "aziende: scrive la mia area" on prospects for update to authenticated using (
  case (select mia_area())
    when 'direzione' then true
    when 'vendita' then (not coalesce(fuori, false) and last_reply_at is not null)
                     or (coalesce(fuori, false) and pipeline_stage in ('conoscitiva', 'tecnica'))
    when 'marketing' then (coalesce(fuori, false) and pipeline_stage in ('avvio', 'prova', 'cliente'))
                     or exists (select 1 from progetti g where g.prospect_id = prospects.id and g.natura ilike '%ads%')
    when 'web' then exists (select 1 from progetti g where g.prospect_id = prospects.id
                            and (g.natura ilike '%sito%' or g.natura ilike '%landing%'))
    else false
  end
);

-- le bozze delle mail: le vede e le lavora anche la vendita (le mail partono dalle
-- caselle di Lorenzo e sono firmate da lui)
drop policy if exists "proposte: le bozze alla vendita" on proposte;
create policy "proposte: le bozze alla vendita" on proposte for all to authenticated
  using (owner is null and tipo in ('risposta', 'umano') and (select mia_area()) in ('direzione', 'vendita'));

select 'schema v66 applicato: cosa vede ognuno, per area' as esito;
