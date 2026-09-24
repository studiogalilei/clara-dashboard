-- IL PERIMETRO SENZA FUNZIONI PER RIGA (24/9/2026). Le policy su prospects
-- chiamavano una funzione security definer per ognuna delle 13.000 righe (non
-- si puo' inlinare): 400 ms a query, moltiplicati per le 18 query di Oggi.
-- Scritte inline, il ceo passa con un InitPlan e gli altri usano gli indici.
drop policy if exists "aziende nel perimetro" on prospects;
create policy "aziende nel perimetro" on prospects for select to authenticated using (
  (select sono_ceo())
  or (coalesce(fuori, false) and pipeline_stage in ('tecnica', 'avvio', 'prova', 'cliente'))
  or (chi_segue is not null and (select nome_eff()) is not null
      and chi_segue ilike '%' || split_part((select nome_eff()), ' ', 1) || '%')
);
-- ATTENZIONE: la policy «quelle con cui ho una call» NON si scrive inline:
-- agenda ha a sua volta una policy che guarda prospects, e Postgres va in
-- ricorsione infinita (successo il 24/9 per due minuti). Resta ho_una_call(),
-- che e' security definer e quindi non riapre le policy.
drop policy if exists "aziende: quelle con cui ho una call" on prospects;
create policy "aziende: quelle con cui ho una call" on prospects for select to authenticated using (ho_una_call(id));
drop policy if exists "aziende: scrive chi le vede" on prospects;
create policy "aziende: scrive chi le vede" on prospects for update to authenticated using (
  (select sono_ceo())
  or (coalesce(fuori, false) and pipeline_stage in ('tecnica', 'avvio', 'prova', 'cliente'))
  or (chi_segue is not null and (select nome_eff()) is not null
      and chi_segue ilike '%' || split_part((select nome_eff()), ' ', 1) || '%')
);
create index if not exists idx_prospects_fuori_stage on prospects (fuori, pipeline_stage);
