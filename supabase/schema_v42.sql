-- I DOCUMENTI CHE SI SCRIVONO DENTRO (16/9/2026)
--
-- Dre: «i preventivi voglio che siano un luogo dove vengo, vedo, e clicco un
-- + che mi porta in un posto tipo Word col template gia' li'; collego
-- l'azienda e i dati si riempiono; e un pulsante per farmi aiutare da Clara,
-- che ha i transcript di tutte le call e capisce com'e' la persona».
--
-- Il documento vive come blocchi (lo stesso formato che il motore del brand
-- sa stampare in PDF): cosi' quello che scrivi a schermo e quello che esce
-- stampato sono la stessa cosa, e Clara puo' scrivere dentro un blocco senza
-- toccare il resto.
create table if not exists documenti (
  id bigserial primary key,
  prospect_id uuid references prospects(id) on delete set null,
  modello text not null,                    -- proposta, condizioni, report, verbale
  titolo text not null default 'Senza titolo',
  doc jsonb not null,                       -- { tipo, copertina, blocchi, piede }
  stato text not null default 'bozza',      -- bozza | mandato | archiviato
  creato_il timestamptz not null default now(),
  creato_da uuid default auth.uid(),
  aggiornato_il timestamptz not null default now(),
  aggiornato_da uuid default auth.uid(),
  file text                                 -- dove sta il PDF nel vault, quando si genera
);
create index if not exists documenti_prospect_idx on documenti (prospect_id, aggiornato_il desc);

alter table documenti enable row level security;
drop policy if exists "documenti: chi vede l'azienda" on documenti;
create policy "documenti: chi vede l'azienda" on documenti for all to authenticated
  using (true) with check (true);

drop trigger if exists documenti_aggiornato on documenti;
create trigger documenti_aggiornato before update on documenti
  for each row execute function set_updated_at();
