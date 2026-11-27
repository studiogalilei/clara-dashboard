-- v121 (27/11, Dre): il LinkedIn Desk. «Un sistema sul telefono dove in modo veloce posso registrare un audio, mettere
-- una foto e trasforma la roba in un post». Una riga per post: Dre mette il materiale (testo dettato, foto), il
-- sistema scrive due versioni con due framework diversi (una routine di Claude Code, sull'abbonamento di Dre), Dre ne
-- sceglie una, la corregge, la programma. Solo il ceo legge e scrive. I testi stanno qui, mai nel repository.
create table if not exists linkedin_post (
  id uuid primary key default gen_random_uuid(),
  creato_il timestamptz not null default now(),
  aggiornato_il timestamptz not null default now(),
  -- da_scrivere: aspetta la routine; in_scrittura: la routine ci lavora; bozza: le versioni sono pronte;
  -- programmato: ha un'uscita; pubblicato; scartato; errore (la routine dice perche' in «errore»)
  stato text not null default 'da_scrivere'
    check (stato in ('da_scrivere', 'in_scrittura', 'bozza', 'programmato', 'pubblicato', 'scartato', 'errore')),
  -- quello che mette Dre: il testo dettato o scritto, il percorso della foto nello storage
  dettato text not null default '',
  foto text,
  -- una richiesta di riscrittura su una versione gia' fatta: «piu_corto», «piu_ironico», «cambia_framework»
  richiesta text check (richiesta in ('piu_corto', 'piu_ironico', 'cambia_framework')),
  -- le versioni scritte: [{framework, caso, testo, giudice: {passa, note}}]
  versioni jsonb not null default '[]'::jsonb,
  scelta int,
  testo text,
  uscita_il timestamptz,
  pubblicato_il timestamptz,
  linkedin_urn text,
  errore text
);

create index if not exists linkedin_post_stato on linkedin_post (stato, creato_il desc);

alter table linkedin_post enable row level security;
drop policy if exists "linkedin: solo il ceo" on linkedin_post;
create policy "linkedin: solo il ceo" on linkedin_post for all to authenticated
  using ((select sono_ceo())) with check ((select sono_ceo()));

create or replace function linkedin_toccato() returns trigger language plpgsql as $$
begin new.aggiornato_il := now(); return new; end $$;
drop trigger if exists linkedin_toccato on linkedin_post;
create trigger linkedin_toccato before update on linkedin_post for each row execute function linkedin_toccato();

-- l'app vede arrivare le versioni senza ricaricare
do $$ begin
  alter publication supabase_realtime add table linkedin_post;
exception when duplicate_object then null; end $$;

-- le foto: cartella privata, solo il ceo
insert into storage.buckets (id, name, public) values ('linkedin', 'linkedin', false) on conflict (id) do nothing;
drop policy if exists "linkedin foto: solo il ceo" on storage.objects;
create policy "linkedin foto: solo il ceo" on storage.objects for all to authenticated
  using (bucket_id = 'linkedin' and (select sono_ceo())) with check (bucket_id = 'linkedin' and (select sono_ceo()));
