-- LA CASSAFORTE: i soldi li vedono solo Dre e Giacomo (Dre, 29/9/2026)
--
-- «Niente soldi per gli altri: solo io e Giacomo vediamo tutte le robe che
-- riguardano soldi.» Preventivi, incassi e listino erano gia' solo dei ceo. Nelle
-- tabelle che la squadra legge restavano: il canone e i dati di fatturazione sulla
-- scheda, il prezzo suggerito e i numeri del cliente (enriched: prezzo, bilancio,
-- valore), il valore dei progetti, e la formula dei prezzi nei parametri.
--
-- Non basta nasconderli dallo schermo: chi ha l'accesso li leggerebbe lo stesso.
-- Qui stanno in due tabelle che solo i ceo leggono, e un controllo nel database
-- li SPOSTA da solo: qualunque cosa scriva un canone o un valore nelle tabelle
-- normali (lo schermo, uno script, un pezzo di codice di domani), il dato finisce
-- in cassaforte e nella tabella normale resta vuoto. Chi non e' ceo non puo'
-- nemmeno scriverlo.

create table if not exists soldi_clienti (
  prospect_id   uuid primary key references prospects(id) on delete cascade deferrable initially deferred,
  canone        numeric,
  fatturazione  jsonb,
  prezzo        jsonb,          -- il prezzo suggerito (scripts/prezzo.py)
  bilancio      jsonb,          -- i numeri del cliente usati per il prezzo
  valore        jsonb,
  aggiornato_il timestamptz not null default now()
);
create table if not exists soldi_progetti (
  progetto_id   bigint primary key references progetti(id) on delete cascade deferrable initially deferred,
  valore        numeric,
  aggiornato_il timestamptz not null default now()
);

alter table soldi_clienti enable row level security;
alter table soldi_progetti enable row level security;
drop policy if exists "soldi: solo i ceo" on soldi_clienti;
create policy "soldi: solo i ceo" on soldi_clienti for all to authenticated
  using ((select sono_ceo())) with check ((select sono_ceo()));
drop policy if exists "soldi: solo i ceo" on soldi_progetti;
create policy "soldi: solo i ceo" on soldi_progetti for all to authenticated
  using ((select sono_ceo())) with check ((select sono_ceo()));

-- chi puo' mettere soldi: i ceo e gli script del sistema (chiave di servizio)
-- Si guarda CHI HA FATTO LA RICHIESTA (le sue credenziali), non l'utente del
-- database: dentro il controllo quello e' sempre il proprietario, e diceva si' a
-- tutti (trovato dalla prova del 29/9: il canone scritto da Alex entrava).
-- Senza credenziali e' una migrazione fatta a mano sul database: passa.
create or replace function puo_scrivere_soldi() returns boolean
language sql stable security definer set search_path = public as $$
  select case coalesce(nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role', '')
           when 'service_role' then true
           when '' then true
           else (select sono_ceo())
         end;
$$;

create or replace function cassaforte_prospects() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  soldi jsonb := coalesce(new.enriched, '{}'::jsonb);
begin
  if new.canone is not null or new.fatturazione is not null
     or soldi ? 'prezzo' or soldi ? 'bilancio' or soldi ? 'valore' then
    if puo_scrivere_soldi() then
      insert into soldi_clienti as s (prospect_id, canone, fatturazione, prezzo, bilancio, valore, aggiornato_il)
      values (new.id, new.canone, new.fatturazione, soldi -> 'prezzo', soldi -> 'bilancio', soldi -> 'valore', now())
      on conflict (prospect_id) do update set
        canone       = coalesce(excluded.canone, s.canone),
        fatturazione = coalesce(excluded.fatturazione, s.fatturazione),
        prezzo       = coalesce(excluded.prezzo, s.prezzo),
        bilancio     = coalesce(excluded.bilancio, s.bilancio),
        valore       = coalesce(excluded.valore, s.valore),
        aggiornato_il = now();
    end if;
    new.canone := null;
    new.fatturazione := null;
    new.enriched := case when new.enriched is null then null else new.enriched - 'prezzo' - 'bilancio' - 'valore' end;
  end if;
  return new;
end;
$$;
drop trigger if exists prospects_cassaforte on prospects;
create trigger prospects_cassaforte before insert or update on prospects
  for each row execute function cassaforte_prospects();

create or replace function cassaforte_progetti() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.valore is not null then
    if puo_scrivere_soldi() then
      insert into soldi_progetti as s (progetto_id, valore, aggiornato_il) values (new.id, new.valore, now())
      on conflict (progetto_id) do update set valore = excluded.valore, aggiornato_il = now();
    end if;
    new.valore := null;
  end if;
  return new;
end;
$$;
drop trigger if exists progetti_cassaforte on progetti;
create trigger progetti_cassaforte before insert or update on progetti
  for each row execute function cassaforte_progetti();

-- quello che c'e' gia' entra in cassaforte (le update passano dai trigger qui sopra)
update progetti set valore = valore where valore is not null;
update prospects set canone = canone where canone is not null or fatturazione is not null
   or enriched ? 'prezzo' or enriched ? 'bilancio' or enriched ? 'valore';

-- la formula dei prezzi: solo i ceo
drop policy if exists "parametri: leggono tutti" on parametri;
drop policy if exists "parametri: leggono tutti, i prezzi i ceo" on parametri;
create policy "parametri: leggono tutti, i prezzi i ceo" on parametri for select to authenticated
  using (chiave not like 'prezzo.%' or (select sono_ceo()));

select 'schema v67 applicato: la cassaforte dei soldi' as esito;
