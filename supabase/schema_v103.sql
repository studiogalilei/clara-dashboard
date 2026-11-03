-- schema_v103 (3/11/2026, sera): CLARA IN PROVA, la sandbox sul vivo.
-- Dre, 3/11: «prima trainare, testare il sistema in sandbox finche' fa le cose bene, poi rilasciarlo».
-- Il cervello nuovo (scripts/clara_sdr.py) decide su ogni risposta che entra, accanto al sistema di
-- oggi, e qui scrive la decisione: non manda, non tocca Smartlead. Dre la corregge dal foglio (scheda
-- «Clara in prova»), il giudice indipendente la vota, e da li' si addestra l'identita'.

create table if not exists clara_decisioni (
  id            uuid primary key default gen_random_uuid(),
  prospect_id   uuid not null references prospects(id) on delete cascade,
  risposta_il   timestamptz not null,            -- la mail del lead su cui ha deciso (l'evento)
  versione      text not null,                   -- l'identita' di Clara (hash), per confrontare le versioni
  modello       text not null,
  lead_testo    text,                            -- cosa ha scritto il lead (pulito), per leggerla nel foglio
  mossa         text not null,
  owner         text,
  entro_il      date,
  testo         text,                            -- la mail che avrebbe mandato
  perche        text,
  prove         jsonb not null default '[]',     -- le frasi del lead citate
  richiamo      jsonb,
  segnali       jsonb not null default '[]',     -- le regole fisse che non tornano (metro, non cancello)
  uso           jsonb,                           -- token, strumenti usati, dollari
  contesto      text,                            -- quello che il cervello ha letto
  giudice       jsonb,                           -- il voto del giudice indipendente
  dre_giudizio  text check (dre_giudizio in ('ok', 'no')),
  dre_mossa     text,
  dre_nota      text,
  dre_il        timestamptz,
  in_prova      boolean not null default true,   -- true = sandbox, mai eseguita
  eseguita_il   timestamptz,
  creato_il     timestamptz not null default now(),
  unique (prospect_id, risposta_il, versione)
);
create index if not exists clara_decisioni_quando on clara_decisioni (creato_il desc);
alter table clara_decisioni enable row level security;
drop policy if exists "clara decisioni: i ceo leggono" on clara_decisioni;
create policy "clara decisioni: i ceo leggono" on clara_decisioni for select to authenticated using ((select sono_ceo()));

insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ordine, attiva) values
  ('clara_prova', 'Clara in prova',
   'Il cervello nuovo decide su ogni risposta entrata, accanto al sistema di oggi, senza mandare niente. Scrive la decisione in clara_decisioni e nella scheda «Clara in prova» del foglio, legge le correzioni di Dre, fa votare il giudice. Ogni 10 minuti.',
   'python3 scripts/clara_prova.py --giro', 10, 28, true)
on conflict (chiave) do nothing;
