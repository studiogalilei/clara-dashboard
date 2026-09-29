-- IL METRO DELLE RISPOSTE (Dre, 29/9/2026: strada A del lettore unico)
--
-- Le classificazioni di Dre dicono com'e' l'azienda oggi, dopo tutta la storia, non
-- cosa dice UNA mail («ok aspetto con ansia» e' «negativo» perche' dopo l'analisi ha
-- detto no). Per misurare un lettore di mail serve un metro fatto mail per mail: qui
-- Dre etichetta una mail alla volta, senza vedere cosa ne pensa il modello (se no si
-- misura il modello contro se stesso). Poi scripts/metro.py confronta.

create table if not exists metro_risposte (
  interaction_id uuid primary key references interactions(id) on delete cascade,
  prospect_id    uuid,
  testo          text not null,                 -- solo quello che ha scritto (senza firma ne' citazione)
  proposta       jsonb,                         -- la lettura del modello: NON si mostra a Dre
  etichetta      text check (etichetta is null or etichetta in ('si', 'no', 'non_scrivere', 'fuori_ufficio', 'rinvio', 'altro')),
  etichettata_il timestamptz,
  creato_il      timestamptz not null default now()
);
alter table metro_risposte enable row level security;
drop policy if exists "metro: solo i ceo" on metro_risposte;
create policy "metro: solo i ceo" on metro_risposte for all to authenticated
  using ((select sono_ceo())) with check ((select sono_ceo()));

select 'schema v69 applicato: il metro delle risposte' as esito;
