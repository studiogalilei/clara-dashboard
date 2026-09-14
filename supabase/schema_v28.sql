-- ODYN CRM schema v28 (14 set 2026) — i preventivi fatti bene
--
-- Dre, 14/9: «un widget per creare preventivi in modo smooth secondo le
-- brand guidelines, collegato al resto: segnare se accettano, vedere i
-- preventivi in giro e a che cliente sono connessi».
-- Un preventivo nasce bozza, si genera il PDF (Condizioni economiche, il
-- documento formale SG), si segna inviato, poi accettato o rifiutato;
-- pagato lo scrive Stripe (stripe_sync) o Giacomo a mano.

alter table preventivi add column if not exists numero        text;          -- SG-MK-2026-003
alter table preventivi add column if not exists linea         text;          -- marketing | ai | software | istituzionale
alter table preventivi add column if not exists voci          jsonb not null default '[]'::jsonb;
alter table preventivi add column if not exists mensile       numeric;       -- la parte ricorrente, al mese
alter table preventivi add column if not exists valido_fino   date;
alter table preventivi add column if not exists accettato_il  date;
alter table preventivi add column if not exists rifiutato_il  date;
alter table preventivi add column if not exists motivo        text;          -- perche' no (o note dell'esito)
alter table preventivi add column if not exists pdf_path      text;          -- nel bucket vault
alter table preventivi add column if not exists link_pagamento text;         -- il link Stripe, incollato
alter table preventivi add column if not exists condizioni    text;          -- il testo delle condizioni, se cambiato
alter table preventivi add column if not exists aggiornato_il timestamptz not null default now();
alter table preventivi alter column inviato_il drop not null;
alter table preventivi alter column inviato_il drop default;
alter table preventivi drop constraint if exists preventivi_stato_check;
alter table preventivi add constraint preventivi_stato_check
  check (stato in ('bozza', 'inviato', 'accettato', 'rifiutato'));
alter table preventivi drop constraint if exists preventivi_linea_check;
alter table preventivi add constraint preventivi_linea_check
  check (linea is null or linea in ('marketing', 'ai', 'software', 'istituzionale'));
create unique index if not exists idx_preventivi_numero on preventivi (numero) where numero is not null;

-- i dati di fatturazione stanno sull'azienda: servono ai preventivi e a Giacomo per le fatture
alter table prospects add column if not exists fatturazione jsonb;   -- {ragione, indirizzo, piva, pec, sdi}

-- il listino interno: le voci pronte da mettere in un preventivo. Non e' un
-- listino pubblico (il documento e' intestato all'azienda, non e' un prezzario)
create table if not exists listino (
  id          bigint generated always as identity primary key,
  nome        text not null,
  descrizione text,
  prezzo      numeric not null default 0,
  ricorrenza  text not null default 'una_tantum',    -- una_tantum | mese
  linea       text not null default 'marketing',
  ordine      int not null default 0,
  attivo      boolean not null default true
);
alter table listino enable row level security;
drop policy if exists "listino: i ceo" on listino;
create policy "listino: i ceo" on listino for all to authenticated using (sono_ceo()) with check (sono_ceo());
insert into listino (nome, descrizione, prezzo, ricorrenza, linea, ordine)
select * from (values
  ('Fase pilota Google Ads, 2 mesi', 'Due mesi di lavoro reale: analisi iniziale, impostazione, gestione e ottimizzazione sui dati. Pagata in anticipo alla firma, rimborsabile fino alla fine del secondo mese.', 1500, 'una_tantum', 'marketing', 1),
  ('Lavoro continuativo Google Ads', 'Dal terzo mese: gestione operativa, ottimizzazione, report periodici e call di allineamento. Addebito ricorrente su Stripe.', 1400, 'mese', 'marketing', 2),
  ('Sito web', 'Progettazione, sviluppo e pubblicazione del sito, con il tracciamento impostato.', 800, 'una_tantum', 'software', 3),
  ('Landing page', 'Una pagina di atterraggio per le campagne, con il tracciamento impostato.', 400, 'una_tantum', 'software', 4),
  ('Automazione su misura', 'Un processo che oggi si fa a mano, automatizzato.', 0, 'una_tantum', 'ai', 5)
) as v(nome, descrizione, prezzo, ricorrenza, linea, ordine)
where not exists (select 1 from listino);

-- i tre preventivi gia' fatti a mano: numero e linea
update preventivi set numero = 'SG-MK-2026-001', linea = 'marketing' where id = 1 and numero is null;
update preventivi set numero = 'SG-SW-2026-001', linea = 'software',  voci = '[{"nome":"Sito web","quantita":1,"prezzo":802,"ricorrenza":"una_tantum"}]' where id = 2 and numero is null;
update preventivi set numero = 'SG-MK-2026-002', linea = 'marketing', voci = '[{"nome":"Fase pilota Google Ads, 2 mesi","quantita":1,"prezzo":1502,"ricorrenza":"una_tantum"}]' where id = 3 and numero is null;

select 'schema v28 applicato: preventivi, listino, fatturazione' as esito;
