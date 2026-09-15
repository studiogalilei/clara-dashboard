-- v37 (15/9): la chat della squadra, dentro il Workspace.
--
-- Dre: «è come un WhatsApp interno: le persone si scrivono da una dashboard
-- all'altra e si passano documenti taggando il cliente, così quel documento
-- lo ritrovi sempre: sia nella sezione del cliente, con scritto chi l'ha
-- mandato, sia dentro il thread della chat».
--
-- Un messaggio può portarsi dietro due cose: un cliente (il tag) e un file
-- (che è già nei Documenti, nella cartella di quel cliente). Quindi la chat
-- non è un posto dove i file si perdono: è una strada in più per arrivarci.

create table if not exists chat (
  id bigserial primary key,
  at timestamptz not null default now(),
  da uuid not null default uid_eff(),
  -- null = a tutta la squadra (la stanza comune)
  a uuid,
  testo text,
  -- il tag: di quale cliente si sta parlando
  prospect_id uuid references prospects(id) on delete set null,
  -- il documento condiviso: sta nei Documenti, qui c'e' il riferimento
  file_id bigint references vault_file(id) on delete set null,
  letto boolean not null default false
);

create index if not exists idx_chat_giro on chat (a, da, at desc);
create index if not exists idx_chat_cliente on chat (prospect_id) where prospect_id is not null;

alter table chat enable row level security;

-- si legge quello che hai mandato tu, quello che hanno mandato a te, e la
-- stanza comune. Niente di piu': le conversazioni degli altri non si leggono.
drop policy if exists "chat: la mia" on chat;
create policy "chat: la mia" on chat
  for select to authenticated
  using (da = uid_eff() or a = uid_eff() or a is null);

drop policy if exists "chat: scrivo io" on chat;
create policy "chat: scrivo io" on chat
  for insert to authenticated
  with check (da = uid_eff());

-- «letto» lo segna chi ha ricevuto
drop policy if exists "chat: segno letto" on chat;
create policy "chat: segno letto" on chat
  for update to authenticated
  using (a = uid_eff() or (a is null and da <> uid_eff()))
  with check (true);

-- i nomi della squadra si leggono gia' (profili), serve per sapere con chi parli
