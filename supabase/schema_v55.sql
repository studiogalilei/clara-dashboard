-- LA CLASSIFICAZIONE CON LE PAROLE DI DRE (25/9/2026): «positivo, negativo,
-- parziale, richiesta di rimozione, persona sbagliata, nervoso, fuori ufficio».
-- Due valori nuovi: persona_sbagliata (ci ha risposto chi non decide: si cerca
-- il referente) e nervoso (infastidito: si lascia stare, come un no).
alter table prospects drop constraint if exists prospects_classificazione_check;
alter table prospects add constraint prospects_classificazione_check
  check (classificazione in ('da_classificare','positivo','tiepido','negativo','ooo','rinvio','fuori_target','soppresso','persona_sbagliata','nervoso'));
