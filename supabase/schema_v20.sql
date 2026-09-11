-- ODYN CRM schema v20 (11 set 2026) — il login con Google e la chiave per agire a nome tuo
--
-- Dre: accessi come Google. Si entra nel Workspace con l'account
-- @studiogalilei.com (provider Google in Supabase Auth, progetto Cloud
-- «SG Workspace»). Al primo accesso Google consegna anche un refresh token
-- con i permessi su Drive, Chat e Calendar: lo teniamo qui, uno per
-- persona, cosi' Clara puo' leggere il Drive e scrivere in SG Chat a nome
-- di chi ha dato il permesso. Lo scrive solo il proprietario; lo legge
-- solo il runner (service role): nessuna policy di lettura per gli utenti.

create table if not exists google_token (
  user_id        uuid primary key references auth.users(id) on delete cascade,
  email          text,
  refresh_token  text not null,
  scopes         text,
  aggiornato_il  timestamptz not null default now()
);
alter table google_token enable row level security;
drop policy if exists "ognuno scrive il suo token google" on google_token;
create policy "ognuno scrive il suo token google" on google_token
  for insert to authenticated with check (user_id = auth.uid());
drop policy if exists "ognuno aggiorna il suo token google" on google_token;
create policy "ognuno aggiorna il suo token google" on google_token
  for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
-- e vede solo se ce l'ha (non il valore: la select espone solo le colonne che il client chiede, ma per prudenza si legge via funzione)
create or replace function ho_il_token_google() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from google_token where user_id = auth.uid());
$$;

select 'schema v20 applicato: login con Google' as esito;

-- aggiunta (11/9 sera): l'upsert (on conflict do update) deve poter leggere la propria riga
drop policy if exists "ognuno vede il suo token google" on google_token;
create policy "ognuno vede il suo token google" on google_token
  for select to authenticated using (user_id = auth.uid());
