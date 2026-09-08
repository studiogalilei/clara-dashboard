-- ODYN CRM schema v12 (9 set 2026) — il contatore dei PID era rimasto indietro
--
-- Creando un cliente nuovo dal foglio di Giacomo il database ha risposto
-- «pid 1 esiste gia'»: la sequenza pid_seq era ferma a 1 perche' gli import
-- di massa scrivevano i pid a mano. Ogni inserimento nuovo (sync, stanza,
-- foglio) si rompeva. Qui la si riallinea al massimo vero.

select setval('pid_seq', coalesce((select max(pid) from prospects), 0) + 1, false);

select 'schema v12 applicato: pid_seq riallineata a ' || (select last_value from pid_seq) as esito;
