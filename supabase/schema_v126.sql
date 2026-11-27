-- v126 (27/11, Dre: «Sì, costruiscilo»). Quando un'azienda delle Persone risponde, la persona tocca «Ha risposto» e il
-- sistema prepara la nota «Gestionale Operativo AI per <azienda>» (un PDF con i colori dell'azienda, scritto dalla
-- routine «LinkedIn Desk: note per chi ha risposto»). Il PDF sta nello storage «linkedin», cartella <uid>/note/.
alter table linkedin_persone add column if not exists nota_stato text
  check (nota_stato in ('richiesta', 'in_corso', 'pronta', 'errore'));
alter table linkedin_persone add column if not exists nota_chiesta_il timestamptz;
alter table linkedin_persone add column if not exists nota_file text;     -- percorso nello storage: <uid>/note/<id>.pdf
alter table linkedin_persone add column if not exists nota_errore text;   -- perche' non e' riuscita, in parole semplici
alter table linkedin_persone add column if not exists sito text;          -- il sito dell'azienda, se la persona lo sa
create index if not exists linkedin_persone_note on linkedin_persone (nota_stato) where nota_stato in ('richiesta', 'in_corso');

-- La spesa delle immagini fatte dal cloud (funzione linkedin-disegno): tetto al mese, mai crediti extra.
create table if not exists spesa_immagini (
  mese text primary key,                    -- «2026-11»
  dollari numeric not null default 0,
  immagini integer not null default 0
);
alter table spesa_immagini enable row level security;   -- nessuna regola: la legge e la scrive solo la funzione
