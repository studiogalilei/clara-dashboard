-- v38 (15/9): gli accessi dei progetti di sito e landing.
--
-- Alex si blocca sempre sulla stessa cosa: aspetta hosting, dominio e
-- credenziali, e quella informazione oggi vive dentro le note libere, quindi
-- non si vede finche' non apri la riga. Qui NON ci vanno le credenziali:
-- solo dove stanno e a che punto siamo.
alter table progetti add column if not exists accessi_stato      text;
alter table progetti add column if not exists accessi_dove       text;
alter table progetti add column if not exists accessi_chiesti_il date;

alter table progetti drop constraint if exists progetti_accessi_stato_check;
alter table progetti add constraint progetti_accessi_stato_check
  check (accessi_stato is null or accessi_stato in ('mancano', 'chiesti', 'arrivati'));

comment on column progetti.accessi_dove is
  'Il posto, non la password: "cartella del cliente nei Documenti", "dal cliente".';

-- quello che oggi dice «aspettiamo accessi» dentro le note parte gia' segnato
update progetti set accessi_stato = 'mancano'
  where accessi_stato is null and note ilike '%access%';
