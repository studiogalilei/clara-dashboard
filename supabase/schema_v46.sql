-- LE NOVITA' E IL VOTO (17/9/2026)
--
-- Dre: «quando ci sono modifiche, quando rientrano appare un banner tipo
-- quelli delle nuove feature, con le stelle e "lascia un feedback": un voto
-- onesto sull'utilita' della feature». Il voto e' un feedback come gli
-- altri (stessa tabella, stesse regole di accesso), con due colonne in piu':
-- quante stelle, e a quale novita' si riferisce (la chiave in src/lib/novita.ts).
alter table feedback add column if not exists voto int check (voto between 1 and 5);
alter table feedback add column if not exists novita text;
create index if not exists feedback_novita_idx on feedback (novita) where novita is not null;
