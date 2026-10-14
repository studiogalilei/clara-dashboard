-- schema_v89 (14/10/2026): il segnale provvisorio vede le prenotazioni delle call.
-- Dre, 14/10: chi prenota la videochiamata conoscitiva dalla sua pagina di Google Calendar
-- lo vedeva solo per caso nella sua Gmail. scripts/segnale_provvisorio.py adesso guarda il suo
-- calendario (e le mail «Appuntamento prenotato») e gli manda la scheda per la call: quando
-- prenotano, la mattina della call alle 8:30, e una riga se la call si sposta o si cancella.
-- Provvisorio come la v87: si butta col sistema nuovo.

-- Una riga per segnale. `chiave` e' unica: la stessa prenotazione non suona due volte, anche
-- se la si vede sia dalla mail sia dal calendario (la chiave e' l'id dell'evento, che la mail
-- porta nel suo invito .ics). Le chiavi:
--   prenotato:<evento>            la prenotazione (con la scheda)
--   mattina:<evento>:<giorno>     la scheda della mattina della call
--   spostata:<evento>:<inizio>    un nuovo orario
--   cancellata:<evento>           annullata o rifiutata
create table if not exists prenotazioni_segnalate (
  id           bigint generated always as identity primary key,
  chiave       text not null unique,
  tipo         text not null check (tipo in ('prenotato', 'mattina', 'spostata', 'cancellata')),
  evento       text not null,                         -- l'id dell'evento nel calendario di Dre
  inizio       timestamptz,                           -- l'orario della call quando si e' segnalato
  invitato     text,                                  -- chi ha prenotato (la sua mail)
  azienda      text,                                  -- il nome nell'oggetto della mail
  prospect_id  uuid references prospects(id) on delete set null,
  quando       timestamptz not null default now(),
  come         text not null default 'segnale',       -- segnale | semina (gia' nota, nessuna mail) | assorbita | incerto
  oggetto      text                                   -- l'oggetto della mail (per i segnali «incerti»)
);
create index if not exists prenotazioni_segnalate_evento on prenotazioni_segnalate (evento);
comment on table prenotazioni_segnalate is 'Il segnale provvisorio (14/10): le prenotazioni delle call gia'' segnalate a Dre. Si butta col sistema nuovo.';
alter table prenotazioni_segnalate enable row level security;
drop policy if exists "prenotazioni segnalate: solo i ceo" on prenotazioni_segnalate;
create policy "prenotazioni segnalate: solo i ceo" on prenotazioni_segnalate for select to authenticated using ((select sono_ceo()));

notify pgrst, 'reload schema';
