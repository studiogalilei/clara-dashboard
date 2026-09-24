-- LA VISIBILITA' PIU' LEGGERA (24/9/2026). Alex, 17/9: «Oggi è molto lenta
-- (15-20 secondi)». Il perimetro chiamava sono_ceo() e nome_eff() UNA VOLTA
-- PER RIGA (13.000 righe, tre sottoquery ognuna). Scritte come (select ...)
-- Postgres le valuta una volta per query. Stessa regola, stesso risultato.
create or replace function vedo_prospect(p_fuori boolean, p_stage text, p_chi_segue text) returns boolean
language sql stable security definer set search_path = public as $$
  select (select sono_ceo())
      or (coalesce(p_fuori, false) and p_stage in ('tecnica', 'avvio', 'prova', 'cliente'))
      or (p_chi_segue is not null and (select nome_eff()) is not null
          and p_chi_segue ilike '%' || split_part((select nome_eff()), ' ', 1) || '%');
$$;
create or replace function ho_una_call(p_id uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from agenda a
    where a.prospect_id = p_id
      and (a.owner = (select uid_eff()) or a.owner is null)
      and a.at > now() - interval '30 days'
  );
$$;
create index if not exists idx_agenda_prospect_at on agenda (prospect_id, at desc);
