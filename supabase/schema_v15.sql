-- ODYN CRM schema v15 (9 set 2026) — gli accessi del team
--
-- Creando gli utenti di Carlo, Lorenzo, Okay e Giacomo il database ha risposto
-- «Database error creating new user»: il trigger che crea il profilo
-- (crea_profilo) gira come utente di auth, che non vede lo schema public.
-- Gli si dice dove guardare, e da qui in poi ogni utente nuovo nasce col suo
-- profilo.

alter function crea_profilo() set search_path = public;

select 'schema v15 applicato: gli utenti nuovi si creano' as esito;
