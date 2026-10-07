-- v77 (7/10): L'UTILIZZO DEL WORKSPACE, per persona (Dre: «metti un qualcosa che mi dica
-- l'utilizzo, cosi' monitoro l'utilizzo mio e di tutti, tipo la CodexBar; in Impostazioni,
-- solo io vedo»).
--
-- Fino a oggi il registro sapeva solo chi MODIFICA aziende e proposte: chi apre il
-- Workspace, quanto ci resta e dove, non lo sapeva nessuno. Qui: un minuto contato per
-- ogni minuto in cui la pagina e' aperta, in primo piano e la persona la sta usando
-- (mouse, tastiera, dito negli ultimi due minuti). Una riga per persona per giorno.
--
-- Conta la persona VERA (auth.uid()), non quella che un ceo sta guardando con «vedi come».
-- Lo legge solo Dre.

create table if not exists utilizzo (
  uid        uuid not null,
  giorno     date not null,
  minuti     integer not null default 0,
  azioni     integer not null default 0,          -- clic e tasti, a grandi linee: quanto lavora, non solo quanto guarda
  schermate  jsonb not null default '{}'::jsonb,  -- minuti per schermata: {"oggi": 12, "posta": 30}
  primo_at   timestamptz not null default now(),
  ultimo_at  timestamptz not null default now(),
  telefono   integer not null default 0,          -- minuti da schermo stretto
  primary key (uid, giorno)
);
alter table utilizzo enable row level security;
-- nessuna regola di lettura o scrittura diretta: si passa solo dalle due funzioni qui sotto

-- chi e' Dre: il suo id di profilo (profili, nome Dramane). Una funzione sola, cosi' se
-- cambia si cambia qui.
create or replace function e_dre() returns boolean
language sql stable security definer set search_path = public as $$
  select auth.uid() = '43095060-b873-4d29-825b-55522f26af55'::uuid
$$;

-- il minuto: si somma alla riga del giorno, in un colpo solo (niente leggi-poi-scrivi)
create or replace function segna_utilizzo(p_minuti integer, p_azioni integer, p_schermata text, p_telefono boolean)
returns void language plpgsql security definer set search_path = public as $$
declare
  oggi date := (now() at time zone 'Europe/Rome')::date;
  s text := left(coalesce(nullif(p_schermata, ''), 'altro'), 40);
  m integer := greatest(0, least(coalesce(p_minuti, 0), 5));     -- mai piu' di 5 minuti per chiamata
  a integer := greatest(0, least(coalesce(p_azioni, 0), 500));
begin
  if auth.uid() is null then return; end if;
  insert into utilizzo (uid, giorno, minuti, azioni, schermate, telefono)
    values (auth.uid(), oggi, m, a, jsonb_build_object(s, m), case when p_telefono then m else 0 end)
  on conflict (uid, giorno) do update set
    minuti    = utilizzo.minuti + excluded.minuti,
    azioni    = utilizzo.azioni + excluded.azioni,
    schermate = utilizzo.schermate || jsonb_build_object(s, coalesce((utilizzo.schermate ->> s)::integer, 0) + m),
    telefono  = utilizzo.telefono + excluded.telefono,
    ultimo_at = now();
end $$;
grant execute on function segna_utilizzo(integer, integer, text, boolean) to authenticated;

-- il riepilogo per il pannello: risponde solo a Dre, a tutti gli altri un elenco vuoto
create or replace function utilizzo_squadra(p_giorni integer default 7)
returns table (uid uuid, nome text, ruolo text, giorno date, minuti integer, azioni integer, schermate jsonb, telefono integer, ultimo_at timestamptz)
language sql stable security definer set search_path = public as $$
  select u.uid, p.nome, p.ruolo, u.giorno, u.minuti, u.azioni, u.schermate, u.telefono, u.ultimo_at
  from utilizzo u left join profili p on p.id = u.uid
  where e_dre() and u.giorno >= ((now() at time zone 'Europe/Rome')::date - greatest(1, least(p_giorni, 60)) + 1)
  order by u.giorno desc, u.minuti desc
$$;
grant execute on function utilizzo_squadra(integer) to authenticated;

select 'schema v77 applicato: l''utilizzo del Workspace, per persona, solo per Dre' as esito;
