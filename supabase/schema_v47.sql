-- IL PULL PRIMA DELLA CAMPAGNA (21/9/2026)
--
-- Dre: «prima si raccoglie, poi si risponde. Un giro solo: le informazioni
-- si raccolgono bene una volta, stanno da qualche parte in ordine, e quando
-- uno risponde l'analisi parte da quelle, senza rifare la ricerca da zero».
-- E: «evitare proprio di contattare quelli che non sono in target».
--
-- Tre tabelle, tutte interne (le leggono i ceo e il runner):
--   lead_lista   i lead di una lista prima che entrino in campagna, con la
--                lista di provenienza (cecchino = con nome, strascico = senza).
--                Le liste NON si mischiano: «dopo si mischiano, succede casino».
--   raccolta     una riga per dominio: cosa dice il Transparency Center (fa
--                ads), la scheda Maps (recensioni, coi testi), il sito. Solo
--                dati grezzi, nessun ragionamento: quello viene dopo.
--   piattaforme  i crediti dei servizi esterni, con la soglia sotto cui Clara
--                avvisa in chat. «Figo che mi avvisi Clara.»

create table if not exists lead_lista (
  id          bigserial primary key,
  lista       text not null,                 -- cecchino | strascico
  email       text not null,
  first_name  text,
  website     text,
  dominio     text not null,                 -- dal sito, ripulito: e' la chiave verso raccolta
  azienda     text,
  icebreaker  text,
  fa_ads      boolean,                       -- copiato da raccolta quando il pull e' fatto
  fit         text,                          -- SI | PARZIALE | NO, quando il fit e' girato
  fit_motivo  text,
  campagna_id bigint,                        -- la campagna Smartlead in cui e' finito
  caricato_il timestamptz not null default now(),
  unique (lista, email)
);
create index if not exists idx_lead_lista_dominio on lead_lista(dominio);
create index if not exists idx_lead_lista_lista on lead_lista(lista, fa_ads, fit);

create table if not exists raccolta (
  dominio          text primary key,
  azienda          text,
  fa_ads           boolean,
  annunci          int,
  giorni_ads       int,
  inserzionista    text,
  maps_trovato     boolean,
  recensioni       int,
  voto             numeric,
  tipo_maps        text,
  recensioni_testi jsonb,                    -- [{voto, testo, quando}] fino a 20
  sito_letto       boolean,
  sito_testo       text,                     -- home + servizi + prezzi, testo pulito, max 12k
  errore           text,
  crediti_usati    int not null default 0,
  raccolto_il      timestamptz
);
create index if not exists idx_raccolta_da_fare on raccolta(raccolto_il) where raccolto_il is null;

create table if not exists piattaforme (
  nome           text primary key,           -- searchapi, openai, smartlead...
  unita          text,                        -- crediti, euro
  saldo          numeric,
  totale         numeric,
  soglia         numeric,                     -- sotto questa Clara avvisa
  avvisato_il    timestamptz,                 -- per non avvisare ogni sei ore
  aggiornato_il  timestamptz,
  nota           text
);

alter table lead_lista  enable row level security;
alter table raccolta    enable row level security;
alter table piattaforme enable row level security;
drop policy if exists "lead_lista: i ceo" on lead_lista;
create policy "lead_lista: i ceo" on lead_lista for all to authenticated using (sono_ceo()) with check (sono_ceo());
drop policy if exists "raccolta: i ceo" on raccolta;
create policy "raccolta: i ceo" on raccolta for all to authenticated using (sono_ceo()) with check (sono_ceo());
drop policy if exists "piattaforme: i ceo" on piattaforme;
create policy "piattaforme: i ceo" on piattaforme for all to authenticated using (sono_ceo()) with check (sono_ceo());

insert into piattaforme (nome, unita, soglia, nota) values
  ('searchapi', 'crediti', 5000, 'Transparency Center, Maps, recensioni. Si ricarica su searchapi.io')
on conflict (nome) do nothing;

-- le due operazioni del direttore
insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ordine) values
  ('pull',    'Pull delle liste', 'Per ogni dominio delle liste in attesa: fa ads, scheda Maps con le recensioni, il sito. A lotti, finche'' non e'' finito.', 'pull.py --max 1100', 20, 35),
  ('crediti', 'Crediti delle piattaforme', 'Legge il saldo dei servizi esterni; sotto la soglia Clara avvisa in chat.', 'crediti.py', 360, 90)
on conflict (chiave) do update set cosa = excluded.cosa, comando = excluded.comando;

select 'schema v47 applicato: lead_lista, raccolta, piattaforme, operazioni pull e crediti' as esito;
