-- schema_v90 (15/10/2026): la versione snella del Workspace.
-- Dre, 15/10: il Workspace e' pesante e confuso per quello che fa ogni giorno con le campagne
-- outbound: vedere chi chiamare, segnarsi le note, sapere come vanno le campagne. Fino a «Clara
-- nuova» (dicembre) c'e' una shell snella con tre schermate (Oggi, Lead, Campagne) che si apre
-- per prima per i ceo. Provvisoria: si butta col sistema nuovo (tabelle, riga in `operazioni`,
-- scripts/schede.py, src/snella/).
--
-- Quattro tabelle, solo i ceo le vedono:
--   snella_schede   una scheda pronta per lead attivo, scritta da scripts/schede.py ogni 10 minuti
--                   (telefoni in gerarchia con la fonte, cosa fa, ultima frase, analisi, stato
--                   calcolato, prossima mossa suggerita, il filo delle mail gia' diviso). La UI la
--                   legge e basta.
--   snella_lead     quello che decide Dre su un lead: lo stato e la prossima mossa (solo nel
--                   Workspace: non va su Smartlead), e l'esito della chiamata (chiamato, non
--                   risponde, richiamare il...). Una riga per lead.
--   snella_note     le note di Dre, con la data: lo storico non si riscrive.
--   snella_numeri   i numeri gia' fatti: la riga di stato di Oggi, le call prenotate, le campagne.

create table if not exists snella_schede (
  prospect_id      uuid primary key references prospects(id) on delete cascade,
  azienda          text,
  persona          text,
  email            text,
  stato            text,                    -- il nome della categoria di Dre (calcolato)
  ultima_risposta  timestamptz,             -- l'ultima mail sua
  frase            text,                    -- la sua frase (dalla lettura del segnale, o l'ultima frase)
  da_chiamare      boolean not null default false,
  perche_chiamare  text,                    -- «Segnalato caldo», «Vuole sentirti», «Ha lasciato il numero»
  scheda           jsonb not null default '{}'::jsonb,
  filo             jsonb not null default '[]'::jsonb,
  impronta         text,                    -- quando cambia, la scheda si rifa'
  aggiornata_il    timestamptz not null default now()
);
create index if not exists snella_schede_ultima on snella_schede (ultima_risposta desc);
create index if not exists snella_schede_chiamare on snella_schede (da_chiamare) where da_chiamare;

create table if not exists snella_lead (
  prospect_id      uuid primary key references prospects(id) on delete cascade,
  stato            text check (stato is null or stato in ('In conversazione', 'Vuole sentirti', 'Analisi mandata',
                     'Conoscitiva', 'Follow-up', 'Da riprendere', 'No grazie', 'Non scrivere più', 'Fuori ufficio')),
  prossima_mossa   text,
  prossima_il      date,
  chiamata         text check (chiamata is null or chiamata in ('chiamato', 'non_risponde', 'richiamare')),
  chiamata_il      timestamptz,
  richiamare_il    date,
  tentativi        int not null default 0,  -- quante volte non ha risposto
  aggiornato_il    timestamptz not null default now(),
  aggiornato_da    uuid default auth.uid()
);

create table if not exists snella_note (
  id           bigint generated always as identity primary key,
  prospect_id  uuid not null references prospects(id) on delete cascade,
  testo        text not null check (length(btrim(testo)) between 1 and 4000),
  tipo         text not null default 'nota' check (tipo in ('nota', 'chiamata')),
  at           timestamptz not null default now(),
  autore       uuid default auth.uid(),
  autore_nome  text default nome_eff()
);
create index if not exists snella_note_lead on snella_note (prospect_id, at desc);

create table if not exists snella_numeri (
  chiave         text primary key,          -- oggi | call | campagne
  dati           jsonb not null default '{}'::jsonb,
  aggiornato_il  timestamptz not null default now()
);

comment on table snella_schede is 'La versione snella (15/10): una scheda pronta per lead attivo, da scripts/schede.py. Si butta con Clara nuova.';
comment on table snella_lead is 'La versione snella (15/10): stato, prossima mossa e chiamata decisi da Dre. Solo Workspace, mai Smartlead.';
comment on table snella_note is 'La versione snella (15/10): le note di Dre sui lead, con la data.';
comment on table snella_numeri is 'La versione snella (15/10): i numeri gia'' fatti da scripts/schede.py (oggi, call, campagne).';

-- l'ora dell'ultima modifica la mette il database, non il telefono
create or replace function snella_toccata() returns trigger language plpgsql as $$
begin
  new.aggiornato_il = now();
  new.aggiornato_da = auth.uid();
  return new;
end $$;
drop trigger if exists snella_lead_toccata on snella_lead;
create trigger snella_lead_toccata before insert or update on snella_lead
  for each row execute function snella_toccata();

-- RLS: solo i ceo. Lo script scrive con la chiave di servizio.
alter table snella_schede enable row level security;
alter table snella_lead   enable row level security;
alter table snella_note   enable row level security;
alter table snella_numeri enable row level security;

drop policy if exists "snella schede: i ceo leggono" on snella_schede;
create policy "snella schede: i ceo leggono" on snella_schede for select to authenticated using ((select sono_ceo()));
drop policy if exists "snella numeri: i ceo leggono" on snella_numeri;
create policy "snella numeri: i ceo leggono" on snella_numeri for select to authenticated using ((select sono_ceo()));

drop policy if exists "snella lead: i ceo leggono" on snella_lead;
create policy "snella lead: i ceo leggono" on snella_lead for select to authenticated using ((select sono_ceo()));
drop policy if exists "snella lead: i ceo scrivono" on snella_lead;
create policy "snella lead: i ceo scrivono" on snella_lead for insert to authenticated with check ((select sono_ceo()));
drop policy if exists "snella lead: i ceo cambiano" on snella_lead;
create policy "snella lead: i ceo cambiano" on snella_lead for update to authenticated using ((select sono_ceo())) with check ((select sono_ceo()));

drop policy if exists "snella note: i ceo leggono" on snella_note;
create policy "snella note: i ceo leggono" on snella_note for select to authenticated using ((select sono_ceo()));
drop policy if exists "snella note: i ceo scrivono" on snella_note;
create policy "snella note: i ceo scrivono" on snella_note for insert to authenticated with check ((select sono_ceo()));
drop policy if exists "snella note: chi l'ha scritta la toglie" on snella_note;
create policy "snella note: chi l'ha scritta la toglie" on snella_note for delete to authenticated using ((select sono_ceo()) and autore = auth.uid());

-- il giro: ogni 10 minuti, nella corsia leggera del direttore (dura pochi secondi: rifa' solo
-- le schede cambiate). Nasce accesa: legge e scrive solo le sue tabelle.
insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ora_preferita, ordine, attiva) values
  ('schede', 'Le schede della versione snella',
   'Prepara per ogni lead attivo la scheda pronta (telefoni, cosa fa, ultima frase, analisi, stato), le call prenotate e i numeri delle campagne. Solo lettura, scrive solo nelle tabelle snella_*.',
   'python3 scripts/schede.py', 10, null, 22, true)
on conflict (chiave) do nothing;

notify pgrst, 'reload schema';
