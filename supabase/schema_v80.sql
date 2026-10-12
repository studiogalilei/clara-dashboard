-- v80 (12/10/2026): il Manuale di Clara entra nel database.
--
-- 1. LA TABELLA `regole`. Dre, 12/10: «scrivi tutti i documenti come li vuoi tu, poi io correggo»;
--    la sera stessa: «letto, applica questo intanto». Il documento 01 del manuale («Le regole»)
--    diventa una riga per regola: un valore, un posto. La carica scripts/regole_dal_manuale.py dal
--    vault; quando Dre corregge il documento si ricarica. Il codice la legge un pezzo alla volta
--    (prima le costanti che oggi vivono in 7 file con 9 valori diversi).
--    stato: bozza = scritta da Achille; da_confermare = due versioni, scelta di Achille;
--    da_decidere = manca una decisione di Dre («?»); approvata = Dre l'ha confermata.
--    I prezzi e il budget (sezione B) li legge solo chi vede il riservato, come i parametri prezzo.*.
--
-- 2. UNA SUA MAIL NUOVA SVUOTA LA CODA (manuale, documento 02). Prima la coda dei follow-up restava
--    anche dopo una risposta: chi scriveva «sì, sentiamoci» mentre era in coda poteva ricevere un
--    FOLLOW UP 1 («volevo sapere se ha avuto occasione di leggerla»). Il trigger toglie la coda
--    appena arriva una sua risposta piu' nuova dell'ingresso in coda; la risposta la prepara il
--    giro normale, col gesto giusto.

create table if not exists regole (
  chiave         text primary key,
  sezione        text not null,
  valore         text not null,
  perche         text,
  stato          text not null default 'bozza' check (stato in ('bozza', 'da_confermare', 'da_decidere', 'approvata')),
  fonte          text not null default 'Manuale di Clara, 01 · Le regole',
  aggiornata_il  timestamptz not null default now(),
  aggiornata_da  text
);
comment on table regole is 'Il documento 01 del Manuale di Clara, una riga per regola: un valore, un posto (v80, 12/10).';

alter table regole enable row level security;
drop policy if exists "regole: leggono tutti, i prezzi solo Dre" on regole;
create policy "regole: leggono tutti, i prezzi solo Dre" on regole for select to authenticated
  using (sezione not like 'B%' or (select vedo_riservato()));
drop policy if exists "regole: cambiano i ceo" on regole;
create policy "regole: cambiano i ceo" on regole for update to authenticated
  using ((select sono_ceo()) and (sezione not like 'B%' or (select vedo_riservato())));

create or replace function svuota_coda_se_scrive() returns trigger
language plpgsql as $$
begin
  if new.coda is not null
     and new.last_reply_at is distinct from old.last_reply_at
     and new.last_reply_at > coalesce(new.coda_il, '-infinity'::timestamptz) then
    new.coda := null;
    new.coda_il := null;
  end if;
  return new;
end;
$$;

drop trigger if exists prospects_svuota_coda on prospects;
create trigger prospects_svuota_coda
  before update on prospects
  for each row execute function svuota_coda_se_scrive();

select 'schema v80 applicato: le regole del manuale, e una risposta svuota la coda' as esito;
