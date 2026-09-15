-- ODYN CRM schema v33 (15 set 2026) — il diario si riconosce da una colonna, non da un'emoji
-- Regola 13 di Dre: niente emoji decorative nei testi. La domanda del diario
-- portava 📔 davanti solo perche' clara-risponde la riconoscesse.
alter table clara_messaggi add column if not exists diario boolean not null default false;
update clara_messaggi set diario = true where tipo = 'domanda' and testo like '📔%';
update clara_messaggi set testo = ltrim(replace(testo, '📔', '')) where testo like '📔%';

select 'schema v33 applicato: il diario ha la sua colonna' as esito;
