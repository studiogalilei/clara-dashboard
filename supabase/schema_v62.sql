-- L'ARCHIVIO DELLA PIPELINE (Dre, 29/9/2026)
--
-- «Dobbiamo impostare un sistema per archiviare i lead, perche' la pipeline non
-- puo' essere sempre piena... oppure un modo per far si' che le cose importanti
-- arrivino in alto e le meno importanti piu' in basso.»
--
-- Misurato il 29/9: 83 aziende in pipeline, 72 ferme da piu' di un mese, e il
-- lavoro vero di quel giorno erano 11 righe. Dentro le 72: 57 «no», il piu'
-- vecchio di 127 giorni, e 13 positivi fermi che nessuno guardava piu' perche'
-- erano invisibili in mezzo ai rifiuti.
--
-- Due pezzi, non uno:
--   1. l'ORDINE per urgenza, a schermo (src/lib/urgenza.ts): chi pesa di piu' sta in cima;
--   2. l'ARCHIVIO, qui: chi e' finito esce di scena.
-- L'ordine da solo lascia la lista lunga, l'archivio da solo non dice cosa fare
-- prima. Insieme: poche righe, e le prime sono quelle giuste.
--
-- ARCHIVIARE NON E' CANCELLARE. La riga resta, con tutta la sua storia, e chi
-- torna a scrivere rientra da solo: lo fa il trigger qui sotto, non una persona
-- che se lo ricorda.

alter table prospects add column if not exists archiviato_il  timestamptz;
alter table prospects add column if not exists archiviato_perche text;

create index if not exists idx_prospects_archiviato on prospects (archiviato_il)
  where archiviato_il is not null;

-- CHI RISCRIVE TORNA DA SOLO. E' il pezzo che rende l'archivio sicuro: senza
-- questo, archiviare vorrebbe dire perdere qualcuno che ci ripensa.
create or replace function risveglia_se_scrive() returns trigger
language plpgsql as $$
begin
  if new.archiviato_il is not null
     and new.last_reply_at is distinct from old.last_reply_at
     and new.last_reply_at > old.archiviato_il then
    new.archiviato_il := null;
    new.archiviato_perche := null;
  end if;
  return new;
end;
$$;

drop trigger if exists prospects_risveglio on prospects;
create trigger prospects_risveglio
  before update on prospects
  for each row execute function risveglia_se_scrive();

select 'schema v62 applicato: archivio della pipeline, con risveglio automatico' as esito;
