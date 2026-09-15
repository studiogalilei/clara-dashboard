-- v35 (15/9): se hai una call con loro, l'azienda la vedi.
--
-- Carlo (QA del 14/9): «ho la call tecnica con Zafferano in agenda, apro la
-- scheda e mi dice che è fuori dal mio perimetro». Il perimetro parte dalla
-- call tecnica, ma la call conoscitiva la fa lui: fino a quel momento non
-- poteva nemmeno prepararsi.
--
-- Non si tocca vedo_prospect: si aggiunge una regola in piu'. In PostgreSQL
-- le policy dello stesso comando si sommano (una basta), quindi questa apre
-- senza rischiare di chiudere qualcosa che prima funzionava.

create or replace function ho_una_call(p_id uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from agenda a
    where a.prospect_id = p_id
      and (a.owner = uid_eff() or a.owner is null)
      and a.at > now() - interval '30 days'
  );
$$;

drop policy if exists "aziende: quelle con cui ho una call" on prospects;
create policy "aziende: quelle con cui ho una call" on prospects
  for select to authenticated using (ho_una_call(id));

drop policy if exists "storia: delle aziende con cui ho una call" on interactions;
create policy "storia: delle aziende con cui ho una call" on interactions
  for select to authenticated using (ho_una_call(prospect_id));
