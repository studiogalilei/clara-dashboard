-- v122 (27/11, Dre): «posso passare anche questo sistema agli altri ragazzi: fargli fare login, connettono il loro
-- profilo, e c'e' un sistema automatizzato di LinkedIn, cosi' possono pubblicare e restare attivi anche loro».
-- Ogni post ha il suo autore e ognuno vede e scrive solo i suoi; le foto stanno nella cartella dell'autore.
-- linkedin_profilo: come scrive ognuno (chi e', di cosa parla, la sua voce), letto dalla routine che scrive.
alter table linkedin_post add column if not exists autore uuid references auth.users (id) on delete cascade default auth.uid();
-- (il 27/11 c'era solo un post di prova, assegnato a mano a Dre)
create index if not exists linkedin_post_autore on linkedin_post (autore, creato_il desc);

drop policy if exists "linkedin: solo il ceo" on linkedin_post;
drop policy if exists "linkedin: i miei post" on linkedin_post;
create policy "linkedin: i miei post" on linkedin_post for all to authenticated
  using (autore = (select auth.uid())) with check (autore = (select auth.uid()));

create table if not exists linkedin_profilo (
  utente uuid primary key references auth.users (id) on delete cascade default auth.uid(),
  nome text not null default '',
  ruolo text not null default '',   -- per esempio «CEO di Studio Galilei», «sviluppatore»
  temi text not null default '',    -- di cosa parla
  voce text not null default '',    -- come parla, parole sue, cosa non direbbe mai
  aggiornato_il timestamptz not null default now()
);
alter table linkedin_profilo enable row level security;
drop policy if exists "linkedin profilo: il mio" on linkedin_profilo;
create policy "linkedin profilo: il mio" on linkedin_profilo for all to authenticated
  using (utente = (select auth.uid())) with check (utente = (select auth.uid()));

drop policy if exists "linkedin foto: solo il ceo" on storage.objects;
drop policy if exists "linkedin foto: le mie" on storage.objects;
create policy "linkedin foto: le mie" on storage.objects for all to authenticated
  using (bucket_id = 'linkedin' and (storage.foldername(name))[1] = (select auth.uid())::text)
  with check (bucket_id = 'linkedin' and (storage.foldername(name))[1] = (select auth.uid())::text);
