-- ODYN CRM schema v27 (14 set 2026) — i Documenti come cassaforte ordinata
--
-- Dre, 14/9: «la cassaforte dell'azienda, si ritrova tutto in facilita':
-- i loghi, i template di documento...». Ogni file ha una sezione (dove
-- sta) e un gruppo (lo scaffale dentro la sezione), come le cartelle di
-- Drive ma fisse: nessuno inventa cartelle nuove.
--   brand    loghi, copertine, sfondi, segni, incisioni, regole
--   modelli  i template dei documenti (contratti, condizioni, guide)
--   azienda  documenti interni (societa', procedure, formazione)
--   clienti  i file agganciati a un'azienda (prospect_id)
alter table vault_file add column if not exists sezione text not null default 'clienti';
alter table vault_file add column if not exists gruppo text;
alter table vault_file add column if not exists nota text;
alter table vault_file drop constraint if exists vault_file_sezione_check;
alter table vault_file add constraint vault_file_sezione_check
  check (sezione in ('brand', 'modelli', 'azienda', 'clienti'));
update vault_file set sezione = 'clienti' where prospect_id is not null and sezione <> 'clienti';
update vault_file set sezione = 'azienda' where prospect_id is null and sezione = 'clienti';
create index if not exists idx_vault_file_sezione on vault_file(sezione, gruppo);
create unique index if not exists idx_vault_file_path on vault_file(path);

-- le regole dei documenti per Clara: chiave «documenti» nelle istruzioni
insert into istruzioni (chiave, titolo, testo) values ('documenti', 'Le regole dei documenti', '')
  on conflict (chiave) do nothing;

select 'schema v27 applicato: sezioni dei Documenti' as esito;
