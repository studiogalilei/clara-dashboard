-- v81 (12/10/2026): il senso lo decide l'AI.
--
-- Il 12/10 il postino ha fermato due «sì» veri come «ha detto no»: una lista di parole trovava
-- «cancellare il messaggio» nell'informativa privacy e «Buongiorno, grazie» come «no, grazie», e
-- la regola «basta che UNO dei due dica no» la faceva vincere sull'AI, che aveva capito. Dre:
-- «questo deve essere interpretato». Da qui (scripts/senso.py, scripts/lettura.py):
--   - il senso di una risposta lo decide l'AI sul testo suo; la lista solo come rete per i gravi;
--   - una lettura per messaggio, salvata qui: tutti gli altri la rileggono gratis;
--   - se la lista e l'AI discordano si rilegge, e il dubbio va a Dre in tre righe (proposta «senso»),
--     con i bottoni del Metro: la sua scelta scrive la lettura e diventa un'etichetta del Metro.
--
-- 1. uso_modelli: il contatore dei token nel database. Il file ~/.odyn-uso-cervello.json muore col
--    runner del direttore, e il costo di un giorno non si poteva dire.
-- 2. letture: la lettura di ogni risposta (una per prospect, testo suo e versione del lettore).
-- 3. decidi_lettura(id, scelta): il bottone di Dre sul dubbio.
-- 4. l'interruttore senso_v2 (spento) e il confronto di ogni mattina, senso_ombra (acceso).

-- ─────────────────────────────── 1. IL CONTATORE ──────────────────────────────
create table if not exists uso_modelli (
  id         bigint generated always as identity primary key,
  il         timestamptz not null default now(),
  script     text,                         -- chi ha chiamato (sys.argv[0])
  scopo      text,                         -- lettura | seconda | bozza | coerenza | altro
  modello    text,
  token_in   int not null default 0,
  token_out  int not null default 0
);
create index if not exists idx_uso_modelli_il on uso_modelli (il desc);
comment on table uso_modelli is 'Ogni chiamata a un modello, coi token: il costo si misura invece di temerlo (v81, 12/10).';
alter table uso_modelli enable row level security;
drop policy if exists "uso modelli: solo i ceo" on uso_modelli;
create policy "uso modelli: solo i ceo" on uso_modelli for select to authenticated using ((select sono_ceo()));

-- ─────────────────────────────── 2. LE LETTURE ────────────────────────────────
create table if not exists letture (
  id             bigserial primary key,
  prospect_id    uuid not null references prospects(id) on delete cascade,
  interaction_id uuid references interactions(id) on delete set null,   -- null: messaggio solo su Smartlead
  impronta       text not null,                    -- sha256 del testo suo normalizzato
  versione       text not null,                    -- cervello.VERSIONE: domande + prompt + schema + modello
  testo_suo      text not null,
  risposte       jsonb,                            -- probabilita' e campi della prima lettura
  seconda        jsonb,                            -- {campo, p, dove, perche}
  rete           jsonb not null default '[]',      -- frasi della lista grave trovate nel testo suo
  decisione      jsonb,                            -- uscita di senso.giudica
  stato          text not null check (stato in ('letta', 'seconda', 'dubbio_a_dre', 'senza_ai', 'senza_regole', 'deciso_dre')),
  fonte          text not null check (fonte in ('ai', 'ai+seconda', 'ai+rete', 'dre', 'nessuna')),
  decisione_dre  text check (decisione_dre in ('si', 'no', 'non_scrivere', 'fuori_ufficio', 'rinvio', 'altro')),
  deciso_il      timestamptz,
  tentativi      int not null default 0,
  proposta_id    bigint,
  modello        text,
  letta_il       timestamptz not null default now(),
  unique (prospect_id, impronta, versione)
);
create index if not exists idx_letture_prospect on letture (prospect_id, letta_il desc);
create index if not exists idx_letture_stato on letture (stato) where stato in ('senza_ai', 'senza_regole', 'dubbio_a_dre');
comment on table letture is 'La lettura del senso di ogni risposta: una per messaggio, chi decide e perche'' (v81, 12/10).';

-- la stessa protezione della storia (interactions): chi vede l'azienda vede le sue letture
alter table letture enable row level security;
drop policy if exists "letture nel perimetro" on letture;
create policy "letture nel perimetro" on letture
  for all to authenticated
  using (exists (select 1 from prospects p where p.id = prospect_id and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue)))
  with check (exists (select 1 from prospects p where p.id = prospect_id and vedo_prospect(p.fuori, p.pipeline_stage, p.chi_segue)));
drop policy if exists "letture: delle aziende con cui ho una call" on letture;
create policy "letture: delle aziende con cui ho una call" on letture
  for select to authenticated using (ho_una_call(prospect_id));

-- ─────────────────────────────── 3. IL BOTTONE DI DRE ─────────────────────────
-- La scelta (le stesse del Metro) scrive la lettura, chiude la domanda in Posta e, se il
-- messaggio e' nel CRM, entra nel Metro come etichetta: i dubbi diventano esempi.
create or replace function decidi_lettura(p_id bigint, p_scelta text) returns void
language plpgsql security definer set search_path = public as $$
declare l record;
begin
  if not (select sono_ceo()) then
    raise exception 'decidi_lettura: la decide un ceo';
  end if;
  if p_scelta not in ('si', 'no', 'non_scrivere', 'fuori_ufficio', 'rinvio', 'altro') then
    raise exception 'decidi_lettura: scelta sconosciuta (%)', p_scelta;
  end if;
  update letture
     set decisione_dre = p_scelta, stato = 'deciso_dre', fonte = 'dre', deciso_il = now()
   where id = p_id
  returning * into l;
  if not found then
    raise exception 'decidi_lettura: la lettura % non c''e''', p_id;
  end if;
  update proposte
     set stato = 'fatta', risposta = 'deciso da Dre: ' || p_scelta, risposta_il = now()
   where stato = 'aperta' and (id = l.proposta_id or ref = 'senso:' || p_id::text
                               -- 12/10 sera: la domanda e' del messaggio (prospect + impronta), non della riga
                               or ref = 'senso:' || l.prospect_id::text || ':' || left(l.impronta, 16));
  if l.interaction_id is not null then
    insert into metro_risposte (interaction_id, prospect_id, testo, proposta, etichetta, etichettata_il)
    values (l.interaction_id, l.prospect_id, left(l.testo_suo, 1500), l.risposte, p_scelta, now())
    on conflict (interaction_id) do update set etichetta = excluded.etichetta, etichettata_il = now();
  end if;
end $$;
revoke all on function decidi_lettura(bigint, text) from public;
grant execute on function decidi_lettura(bigint, text) to authenticated;

-- ─────────────────────────────── 4. L'INTERRUTTORE ────────────────────────────
-- senso_v2 spento: il vecchio decide, il nuovo gira in ombra (sette giorni). Lo accende Dre,
-- dopo l'ok alle soglie nuove del Manuale (sezione F) e la misura. Senza comando: e' solo un
-- interruttore, il direttore non lo fa partire mai.
insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, attiva, ordine)
values ('senso_v2', 'Il senso lo decide l''AI',
        'Acceso: il senso delle risposte lo decide l''AI sul testo suo, la lista di parole solo per i gravi, i dubbi a Dre. Spento: il vecchio, col nuovo in ombra.',
        null, 1440, false, 90)
on conflict (chiave) do nothing;
-- il confronto di ogni mattina: vecchio e nuovo, i disaccordi nel Metro, i no chiusi da sola
insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ora_preferita, attiva, ordine)
values ('senso_ombra', 'Il senso: il confronto del mattino',
        'Confronta la lettura vecchia e la nuova sulle risposte di ieri: i disaccordi vanno nel Metro, e una riga dice quanti no ho chiuso da sola.',
        'python3 scripts/senso_ombra.py', 1440, '07:30', true, 91)
on conflict (chiave) do nothing;

select 'schema v81 applicato: le letture, il contatore dei modelli, il bottone di Dre, l''interruttore senso_v2' as esito;
