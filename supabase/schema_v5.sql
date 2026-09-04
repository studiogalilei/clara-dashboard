-- ════════════════════════════════════════════════════════════════════
-- ODYN CRM schema v5 (3 settembre 2026): due persone dentro la Dashboard
--
-- Da qui la Dashboard non e' piu' di uno solo. Le task hanno un proprietario
-- e un mittente, i lead si possono prendere in carico o passare a qualcun
-- altro, e ognuno ha le sue preferenze.
--
-- Non cancella niente e si puo' rilanciare senza danni.
-- ════════════════════════════════════════════════════════════════════

-- 1) LE TASK non sono piu' «di Dre»: hanno un proprietario e un mittente.
--    Il nome della tabella cambia di conseguenza, se no fra sei mesi nessuno
--    capisce perche' le task di Giacomo stanno in task_dre.
alter table if exists task_dre rename to task;

alter table task add column if not exists owner uuid references auth.users(id) default null;
alter table task add column if not exists da    uuid references auth.users(id) default null;

-- una task che arriva non entra nella lista di nessuno finche' non la accetta:
-- se no la lista smette di essere sua e viene ignorata
alter table task drop constraint if exists task_stato_check;
alter table task add column if not exists stato text not null default 'accettata';
alter table task add constraint task_stato_check
  check (stato in ('proposta', 'accettata', 'rimandata', 'fatta'));

alter table task add column if not exists motivo text;      -- perche' l'ha rimandata indietro
alter table task add column if not exists colore text;      -- facoltativo, per la Week picture

create index if not exists idx_task_owner on task (owner);
create index if not exists idx_task_da on task (da) where da is not null;

-- 2) LA TERZA USCITA DALLA PIPELINE: passato a qualcun altro.
--    Non e' ne' vinto ne' perso. Oggi quei lead o restano dentro a gonfiare i
--    numeri o spariscono, e con loro il rapporto con chi li ha ricevuti.
alter table prospects add column if not exists passato_a  text;
alter table prospects add column if not exists passato_il timestamptz;

-- 3) IL PRESO IN CARICO: con due persone sulla stessa casella, o rispondono
--    in due o non risponde nessuno perche' ognuno pensa all'altro.
alter table prospects add column if not exists preso_da uuid references auth.users(id) default null;
alter table prospects add column if not exists preso_il timestamptz;

-- 4) CHI LO SEGUE: il cuore del POD di Giacomo senza costruire la gestione
--    della delivery. Un campo, e i clienti si raggruppano per persona.
alter table prospects add column if not exists chi_segue text;

create index if not exists idx_prospects_preso on prospects (preso_da) where preso_da is not null;
create index if not exists idx_prospects_passato on prospects (passato_a) where passato_a is not null;

-- 5) LE PREFERENZE di ognuno: quali widget vede, in che ordine, come si apre.
--    Stanno qui e non nel browser cosi' ti seguono sul telefono.
create table if not exists preferenze (
  owner  uuid not null references auth.users(id) on delete cascade,
  chiave text not null,
  valore jsonb not null,
  primary key (owner, chiave)
);
alter table preferenze enable row level security;
drop policy if exists "ognuno le sue preferenze" on preferenze;
create policy "ognuno le sue preferenze" on preferenze
  for all to authenticated using (owner = auth.uid()) with check (owner = auth.uid());

-- 6) LE PERSONE: chi c'e' dentro la Dashboard. Serve per mandarsi le task,
--    per sapere chi ha preso in carico un lead, e per mostrare un nome
--    invece di un codice. Il nome se lo scrive ognuno nel suo profilo.
create table if not exists profili (
  id    uuid primary key references auth.users(id) on delete cascade,
  nome  text,
  ruolo text not null default 'coordinamento'
);
alter table profili drop constraint if exists profili_ruolo_check;
alter table profili add constraint profili_ruolo_check
  check (ruolo in ('ceo', 'coordinamento'));
alter table profili enable row level security;

-- tutti vedono chi c'e' (se no non sai a chi mandare una task),
-- ma ognuno modifica solo se stesso
drop policy if exists "le persone si vedono" on profili;
create policy "le persone si vedono" on profili
  for select to authenticated using (true);
drop policy if exists "ognuno il suo profilo" on profili;
create policy "ognuno il suo profilo" on profili
  for all to authenticated using (id = auth.uid()) with check (id = auth.uid());

-- chi si iscrive entra da solo nell'elenco
create or replace function crea_profilo()
returns trigger language plpgsql security definer as $$
begin
  insert into profili (id, nome) values (new.id, split_part(new.email, '@', 1))
  on conflict (id) do nothing;
  return new;
end $$;

drop trigger if exists al_nuovo_utente on auth.users;
create trigger al_nuovo_utente after insert on auth.users
  for each row execute function crea_profilo();

-- e chi c'e' gia' ci entra adesso
insert into profili (id, nome)
  select id, split_part(email, '@', 1) from auth.users
  on conflict (id) do nothing;
