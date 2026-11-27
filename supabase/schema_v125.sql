-- v125 (27/11, Dre): «al giorno da' il link di profili suggeriti in target a cui mandare la richiesta, la solita roba
-- delle 20 richieste al giorno... te lo suggerisce il coso, tu lo fai, il giorno dopo te ne da' altri; se te lo dimentichi
-- restano quelli». E: «aziende con buying intent, o in settori con segnali di utilita', tool sprawl».
-- Una riga per azienda suggerita: il segnale (perche' adesso), dove vederlo, chi cercare su LinkedIn. La persona manda la
-- richiesta a mano su LinkedIn e segna «Fatto». Il sistema non manda niente da solo.
create table if not exists linkedin_persone (
  id uuid primary key default gen_random_uuid(),
  autore uuid not null references auth.users (id) on delete cascade default auth.uid(),
  creato_il timestamptz not null default now(),
  giorno date not null default (now() at time zone 'Europe/Rome')::date,
  stato text not null default 'da_fare' check (stato in ('da_fare', 'fatto', 'saltato')),
  fatto_il timestamptz,
  azienda text not null,
  settore text,
  citta text,
  persona text,            -- nome, se si sa da una fonte pubblica (sito, annuncio)
  ruolo text,              -- chi cercare: titolare, responsabile operativo, amministrazione
  profilo text,            -- link al profilo LinkedIn, se trovato
  cerca text,              -- altrimenti la ricerca LinkedIn gia' pronta
  perche text not null,    -- il segnale in una frase: «cerca un addetto inserimento ordini»
  fonte text,              -- dove si vede il segnale (l'annuncio, la pagina del sito, la recensione)
  segnale text not null default 'annuncio' check (segnale in ('annuncio', 'sito', 'recensioni', 'cambiamento', 'caldo'))
);
create unique index if not exists linkedin_persone_una_volta on linkedin_persone (autore, lower(azienda));
create index if not exists linkedin_persone_da_fare on linkedin_persone (autore, stato, giorno);
alter table linkedin_persone enable row level security;
drop policy if exists "linkedin persone: le mie" on linkedin_persone;
create policy "linkedin persone: le mie" on linkedin_persone for all to authenticated
  using (autore = (select auth.uid())) with check (autore = (select auth.uid()));

-- chi riceve le persone del giorno (per ora chi lo accende), il mercato e la zona dove cercare
alter table linkedin_profilo add column if not exists persone boolean not null default false;
alter table linkedin_profilo add column if not exists mercato text not null default 'Aziende che noleggiano, consegnano o programmano mezzi, attrezzature e persone: noleggio, logistica leggera, trasporti, impianti, tour operator';
alter table linkedin_profilo add column if not exists zona text not null default 'Veneto, Friuli Venezia Giulia, Trentino, Lombardia est';
