-- GLI ESAMI (Dre, 1/10/2026: «vorrei trainare il sistema, immagina un modello come
-- l'altro, con tutte quelle domande e commenti, così sa fare i follow-up, sa
-- riprendere, sa fare tutto esattamente come lo farei io»)
--
-- Il metro delle risposte funziona (150 mail, 97 commenti, un verdetto). Questa e'
-- la sua forma generale: un CASO per riga, di qualunque tema (seguiti, persi,
-- prezzi...), con i blocchi da mostrare, le scelte possibili, la proposta del
-- sistema NASCOSTA a Dre (se no si misura il sistema contro se stesso), la sua
-- etichetta e il suo commento. La pagina «Metro» li serve uno alla volta.

create table if not exists metro_casi (
  id             bigint generated always as identity primary key,
  tema           text not null,                  -- 'seguiti', poi 'persi', 'prezzi'...
  prospect_id    uuid,
  riferimento    text,                           -- per non proporre due volte lo stesso caso
  domanda        text not null,                  -- la domanda in testa alla carta
  mostra         jsonb not null,                 -- blocchi [{eti, testo}] che Dre vede
  scelte         jsonb not null,                 -- [[chiave, nome], ...] i bottoni
  proposta       jsonb,                          -- cosa farebbe il sistema oggi: NON si mostra
  etichetta      text,
  nota           text,
  etichettata_il timestamptz,
  creato_il      timestamptz not null default now(),
  unique (tema, riferimento)
);
alter table metro_casi enable row level security;
drop policy if exists "esami: solo i ceo" on metro_casi;
create policy "esami: solo i ceo" on metro_casi for all to authenticated
  using ((select sono_ceo())) with check ((select sono_ceo()));

select 'schema v73 applicato: gli esami' as esito;
