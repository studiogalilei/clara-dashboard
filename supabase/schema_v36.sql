-- v36 (15/9): chi porta un'azienda la può mettere dentro, e la rivede.
--
-- Lorenzo lavora su LinkedIn con piu' profili: trova le aziende, ci parla, e
-- ha la sua pipeline. Fino a ieri creare un'azienda era solo dei ceo, quindi
-- il suo lavoro non entrava nel Workspace.
--
-- La regola: la metti dentro solo se ci scrivi il tuo nome in «chi segue»,
-- cosi' la rivedi (vedo_prospect guarda anche quel campo) e si sa di chi e'.
-- Non apre niente in lettura: si vede quello che si vedeva prima, piu' le
-- proprie.

drop policy if exists "aziende: crea e cancella il ceo" on prospects;
drop policy if exists "aziende: le aggiunge chi le segue" on prospects;
create policy "aziende: le aggiunge chi le segue" on prospects
  for insert to authenticated
  with check (
    sono_ceo()
    or (chi_segue is not null and nome_eff() is not null
        and chi_segue ilike '%' || split_part(nome_eff(), ' ', 1) || '%')
  );

comment on column prospects.campaign is 'Da dove arriva: campagna Smartlead, profilo LinkedIn, referral, evento';
