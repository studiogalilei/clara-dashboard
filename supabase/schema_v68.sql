-- IL RISERVATO: la preparazione delle call e il prezzo li vede solo Dre (29/9/2026)
--
-- Dre: «la preparazione precall la vedo io e basta», e poi «anche il prezzo, solo io».
-- Sopra la cassaforte dei soldi (schema_v67, Dre e Giacomo) c'e' un livello in piu':
-- il riservato, solo per chi ha profili.vede_riservato (oggi Dre).
--   - le preparazioni delle call: da agenda.preparazione a una tabella loro;
--   - il prezzo suggerito e i numeri da cui nasce (bilancio, valore): da soldi_clienti
--     a riservato_clienti;
--   - la formula dei prezzi (parametri prezzo.*).
-- Come per i soldi, un controllo nel database sposta da solo quello che viene scritto
-- nel posto sbagliato, e chi non ha il permesso non puo' scriverlo.
-- Canone, fatturazione, preventivi, incassi e valore dei progetti restano a Dre e Giacomo.

alter table profili add column if not exists vede_riservato boolean not null default false;
update profili set vede_riservato = true where id = '43095060-b873-4d29-825b-55522f26af55';   -- Dre

create or replace function vedo_riservato() returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce((select vede_riservato from profili where id = uid_eff()), false);
$$;

create or replace function puo_scrivere_riservato() returns boolean
language sql stable security definer set search_path = public as $$
  select case coalesce(nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role', '')
           when 'service_role' then true
           when '' then true
           else (select vedo_riservato())
         end;
$$;

create table if not exists preparazioni (
  agenda_id    bigint primary key references agenda(id) on delete cascade deferrable initially deferred,
  prospect_id  uuid,
  testo        text not null,
  preparata_il timestamptz not null default now()
);
create table if not exists riservato_clienti (
  prospect_id   uuid primary key references prospects(id) on delete cascade deferrable initially deferred,
  prezzo        jsonb,
  bilancio      jsonb,
  valore        jsonb,
  aggiornato_il timestamptz not null default now()
);
alter table preparazioni enable row level security;
alter table riservato_clienti enable row level security;
drop policy if exists "riservato: solo Dre" on preparazioni;
create policy "riservato: solo Dre" on preparazioni for all to authenticated
  using ((select vedo_riservato())) with check ((select vedo_riservato()));
drop policy if exists "riservato: solo Dre" on riservato_clienti;
create policy "riservato: solo Dre" on riservato_clienti for all to authenticated
  using ((select vedo_riservato())) with check ((select vedo_riservato()));

-- la preparazione scritta nell'agenda va nel riservato, e dall'agenda sparisce
create or replace function riservato_agenda() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.preparazione is not null then
    if puo_scrivere_riservato() then
      insert into preparazioni as r (agenda_id, prospect_id, testo, preparata_il)
      values (new.id, new.prospect_id, new.preparazione, coalesce(new.preparata_il, now()))
      on conflict (agenda_id) do update set testo = excluded.testo, prospect_id = excluded.prospect_id,
                                            preparata_il = excluded.preparata_il;
    end if;
    new.preparazione := null;
  end if;
  return new;
end;
$$;
drop trigger if exists agenda_riservato on agenda;
create trigger agenda_riservato before insert or update on agenda
  for each row execute function riservato_agenda();

-- la cassaforte dei clienti, rifatta: canone e fatturazione a Dre e Giacomo,
-- prezzo, bilancio e valore solo a Dre
create or replace function cassaforte_prospects() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  arr jsonb := coalesce(new.enriched, '{}'::jsonb);
begin
  if new.canone is not null or new.fatturazione is not null then
    if puo_scrivere_soldi() then
      insert into soldi_clienti as s (prospect_id, canone, fatturazione, aggiornato_il)
      values (new.id, new.canone, new.fatturazione, now())
      on conflict (prospect_id) do update set
        canone = coalesce(excluded.canone, s.canone),
        fatturazione = coalesce(excluded.fatturazione, s.fatturazione),
        aggiornato_il = now();
    end if;
    new.canone := null;
    new.fatturazione := null;
  end if;
  if arr ? 'prezzo' or arr ? 'bilancio' or arr ? 'valore' then
    if puo_scrivere_riservato() then
      insert into riservato_clienti as r (prospect_id, prezzo, bilancio, valore, aggiornato_il)
      values (new.id, arr -> 'prezzo', arr -> 'bilancio', arr -> 'valore', now())
      on conflict (prospect_id) do update set
        prezzo = coalesce(excluded.prezzo, r.prezzo),
        bilancio = coalesce(excluded.bilancio, r.bilancio),
        valore = coalesce(excluded.valore, r.valore),
        aggiornato_il = now();
    end if;
    new.enriched := case when new.enriched is null then null else new.enriched - 'prezzo' - 'bilancio' - 'valore' end;
  end if;
  return new;
end;
$$;

-- quello che c'e' gia' si sposta
insert into riservato_clienti (prospect_id, prezzo, bilancio, valore)
  select prospect_id, prezzo, bilancio, valore from soldi_clienti
  where prezzo is not null or bilancio is not null or valore is not null
on conflict (prospect_id) do nothing;
update soldi_clienti set prezzo = null, bilancio = null, valore = null;
update agenda set preparazione = preparazione where preparazione is not null;

-- la formula dei prezzi: solo Dre
drop policy if exists "parametri: leggono tutti, i prezzi i ceo" on parametri;
drop policy if exists "parametri: leggono tutti, i prezzi solo Dre" on parametri;
create policy "parametri: leggono tutti, i prezzi solo Dre" on parametri for select to authenticated
  using (chiave not like 'prezzo.%' or (select vedo_riservato()));

-- «scrivono i ceo» era FOR ALL, cioe' anche lettura: Giacomo vedeva la formula
-- lo stesso (trovato dalla prova del 29/9). Si scrive con policy per scrittura sola.
drop policy if exists "parametri: scrivono i ceo" on parametri;
drop policy if exists "parametri: aggiungono i ceo" on parametri;
drop policy if exists "parametri: cambiano i ceo" on parametri;
drop policy if exists "parametri: tolgono i ceo" on parametri;
create policy "parametri: aggiungono i ceo" on parametri for insert to authenticated
  with check ((select sono_ceo()) and (chiave not like 'prezzo.%' or (select vedo_riservato())));
create policy "parametri: cambiano i ceo" on parametri for update to authenticated
  using ((select sono_ceo()) and (chiave not like 'prezzo.%' or (select vedo_riservato())));
create policy "parametri: tolgono i ceo" on parametri for delete to authenticated
  using ((select sono_ceo()) and (chiave not like 'prezzo.%' or (select vedo_riservato())));

select 'schema v68 applicato: il riservato di Dre' as esito;
