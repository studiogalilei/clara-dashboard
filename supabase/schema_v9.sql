-- ODYN CRM schema v9 (7 set 2026) — la sala di controllo
--
-- Dre, 7/9: «non voglio che i processi siano legati al Mac, voglio in cloud,
-- che non si perda nulla, un sync autonomo, e scegliere la cadenza da li'».
--
-- Tre tabelle:
--   operazioni   cosa gira, ogni quanto, com'e' andata l'ultima volta.
--                La cadenza la cambia Dre dalla Dashboard; il direttore in
--                cloud (scripts/direttore.py, ogni 15 minuti) legge qui e fa
--                partire quello che e' dovuto. Nessun orologio da riscrivere.
--   corse        il registro: ogni esecuzione lascia una riga, anche se fallisce
--   istruzioni   le regole scritte da Dre che il cervello legge prima di tutto:
--                come classificare, come parlare in chat, cosa mettere nel brief
--   widget_richieste  i widget chiesti da Dre, con il loro stato
--
-- ISTRUZIONI: incollare nell'editor SQL di Supabase e premere Run.

create table if not exists operazioni (
  chiave           text primary key,
  nome             text not null,
  cosa             text,
  comando          text,                       -- lo script che gira; null = gira altrove (backup)
  cadenza_minuti   int  not null default 60,
  ora_preferita    text,                       -- per le giornaliere: "08:00" (ora di Roma)
  attiva           boolean not null default true,
  richiesta_ora    boolean not null default false,   -- «fai ora» dalla Dashboard
  ultima_corsa     timestamptz,
  ultimo_esito     text,                       -- ok | errore
  ultimo_dettaglio text,
  ultima_durata_ms int,
  ordine           int not null default 0
);
alter table operazioni enable row level security;
drop policy if exists "auth full access operazioni" on operazioni;
create policy "auth full access operazioni" on operazioni
  for all to authenticated using (true) with check (true);

create table if not exists corse (
  id         bigint generated always as identity primary key,
  operazione text not null references operazioni(chiave) on delete cascade,
  at         timestamptz not null default now(),
  esito      text not null,                    -- ok | errore
  dettaglio  text,
  righe      int,
  durata_ms  int
);
create index if not exists idx_corse_op on corse (operazione, at desc);
alter table corse enable row level security;
drop policy if exists "auth full access corse" on corse;
create policy "auth full access corse" on corse
  for all to authenticated using (true) with check (true);

create table if not exists istruzioni (
  chiave     text primary key,                 -- lettura | chat | brief
  titolo     text not null,
  testo      text not null default '',
  aggiornata timestamptz not null default now()
);
alter table istruzioni enable row level security;
drop policy if exists "auth full access istruzioni" on istruzioni;
create policy "auth full access istruzioni" on istruzioni
  for all to authenticated using (true) with check (true);

create table if not exists widget_richieste (
  id       bigint generated always as identity primary key,
  at       timestamptz not null default now(),
  nome     text not null,
  cosa     text not null,                      -- cosa deve mostrare o tenere d'occhio
  per_chi  text,                               -- ceo | coordinamento | tutti
  fonte    text,                               -- da dove prende i dati
  cadenza  text,                               -- ogni quanto guarda
  tipo     text not null default 'monitoraggio',  -- monitoraggio | interfaccia
  stato    text not null default 'richiesto',  -- richiesto | in_costruzione | attivo | scartato
  note     text
);
alter table widget_richieste enable row level security;
drop policy if exists "auth full access widget_richieste" on widget_richieste;
create policy "auth full access widget_richieste" on widget_richieste
  for all to authenticated using (true) with check (true);

-- le operazioni di partenza: si possono cambiare dalla Dashboard
insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ora_preferita, ordine) values
  ('sync_smartlead', 'Sincronizza Smartlead', 'Legge tutte le risposte e le mette nella Dashboard. Era fermo un mese, ad agosto.', 'python3 scripts/sync_v2.py', 60, null, 1),
  ('rilettura',      'Clara rilegge le risposte', 'Corregge il sicuro da sola, il resto lo chiede nella sua stanza.', 'python3 scripts/rilettura.py', 1440, '06:30', 2),
  ('brief',          'Il punto del mattino', 'Il saluto in testata e il brief nella chat di Clara.', 'python3 scripts/clara.py', 1440, '08:00', 3),
  ('backup',         'Backup notturno', 'Una copia cifrata di tutto, fuori da Supabase, tenuta 30 giorni.', null, 1440, '03:00', 4),
  ('calendar',       'Legge Google Calendar', 'Le call con data, invitati e link. Arriva con l''utenza tecnica di Workspace.', null, 60, null, 5),
  ('granola',        'Legge Granola', 'I transcript delle call. Arriva con la chiave API di Granola.', null, 120, null, 6)
on conflict (chiave) do nothing;
update operazioni set attiva = false where chiave in ('calendar', 'granola') and ultima_corsa is null;

insert into istruzioni (chiave, titolo, testo) values
  ('lettura', 'Come classificare le risposte', ''),
  ('chat',    'Come parlare con me in chat', ''),
  ('brief',   'Cosa mettere nel punto del mattino', '')
on conflict (chiave) do nothing;

select 'schema v9 applicato' as esito;
