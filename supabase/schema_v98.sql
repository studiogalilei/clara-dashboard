-- schema_v98 (21/10/2026): lo «Stato» della Conversazione nel foglio della pipeline.
-- Dre, 21/10: nel blocco Conversazione la cella «La tua scelta» diventa una tendina «Stato» con nove
-- valori (ha proposto un orario, meeting accettato, ha detto no, ci fa sapere, ha fatto domande,
-- rimanda a una data, girato a un collega, vuole essere chiamato, ho risposto e aspetto).
-- «Quando il sistema lo carica mette lo stato in base a quello che ha detto, SOLO quando lo carica;
-- il resto gestisco io e modifico io»: scripts/foglio.py lo scrive una volta, all'ingresso in
-- Conversazione, dalla lettura del lettore AI; da li' la cella e' di Dre.
--
-- Qui: la colonna snella_lead.stato_conv, cosi' la scheda azienda del Workspace lo mostra («Nel foglio:
-- Ha fatto domande»). Lo scrive il foglio (chiave di servizio), non Dre nell'app: per questo NON conta
-- come un suo tocco. aggiornato_il resta «l'ultima volta che Dre ha toccato il lead nell'app» (ci
-- contano conversazioni.py, orecchio.py e foglio.py per dire «vince Dre»): una riga nata dal foglio con
-- il solo stato_conv ha aggiornato_il nullo, e un cambio del solo stato_conv non lo muove.

alter table snella_lead add column if not exists stato_conv text;
alter table snella_lead drop constraint if exists snella_lead_stato_conv_check;
alter table snella_lead add constraint snella_lead_stato_conv_check check (stato_conv is null or stato_conv in (
  'Ha proposto un orario', 'Meeting accettato', 'Ha detto no', 'Ci fa sapere', 'Ha fatto domande',
  'Rimanda a una data', 'Girato a un collega, con contatto', 'Vuole essere chiamato', 'Ho risposto, aspetto'));
comment on column snella_lead.stato_conv is 'Lo «Stato» della Conversazione nel foglio della pipeline (scripts/foglio.py): lo mette il sistema una volta quando il lead entra, poi lo cambia Dre nel foglio. Sola lettura nell''app.';

alter table snella_lead alter column aggiornato_il drop not null;
comment on column snella_lead.aggiornato_il is 'L''ultima volta che Dre ha toccato il lead nell''app (stato, mossa, chiamata). Nullo se la riga e'' nata dal foglio col solo stato_conv.';

create or replace function snella_toccata() returns trigger language plpgsql as $$
begin
  if tg_op = 'UPDATE' then
    -- cambia solo stato_conv (il foglio): non e' un tocco di Dre
    if (to_jsonb(new) - 'stato_conv' - 'aggiornato_il' - 'aggiornato_da') = (to_jsonb(old) - 'stato_conv' - 'aggiornato_il' - 'aggiornato_da') then
      new.aggiornato_il = old.aggiornato_il;
      new.aggiornato_da = old.aggiornato_da;
      return new;
    end if;
  elsif new.stato_conv is not null and new.stato is null and new.prossima_mossa is null and new.prossima_il is null
        and new.chiamata is null and new.chiamata_il is null and new.richiamare_il is null and new.responsabile is null then
    -- una riga nata dal foglio col solo stato_conv: Dre non l'ha mai toccata
    new.aggiornato_il = null;
    new.aggiornato_da = null;
    return new;
  end if;
  new.aggiornato_il = now();
  new.aggiornato_da = auth.uid();
  return new;
end $$;

select 'schema v98 applicato: lo Stato della Conversazione nel foglio' as esito;
