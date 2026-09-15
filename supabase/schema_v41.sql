-- QUANTO E' FRESCO QUELLO CHE VEDI (15/9/2026)
--
-- Dre: «in home metti la scritta dell'ultimo aggiornamento, così so almeno a
-- quanto è datato; l'obiettivo è portarlo a real time». La tabella delle
-- corse la leggono solo i ceo, e giustamente: dentro c'è il dettaglio di
-- ogni lavoro. Ma l'ORA dell'ultimo giro non è un segreto per nessuno, anzi:
-- e' quello che dice se ti puoi fidare di quello che stai guardando.
create or replace function ultimo_giro()
returns timestamptz
language sql
security definer
stable
set search_path = public
as $$
  select max(at) from corse where esito is distinct from 'errore';
$$;
grant execute on function ultimo_giro() to authenticated;
