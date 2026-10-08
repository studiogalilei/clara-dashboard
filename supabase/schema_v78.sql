-- v78 (8/10): LA FASE 0 DEL SISTEMA NUOVO. Tre cose, e tre scritture che aspettavano.
--
-- Il design («Il sistema nuovo (8-10-2026)», Cervello Condiviso) parte da qui perche'
-- senza queste tre cose tutto il resto impara da dati sporchi:
--
-- 1. CHI E' CLIENTE LO DICE UNA TABELLA. Fino a oggi lo diceva `stage`, che nessuno
--    aggiorna: l'8/10 Fun Dallas Tours (cliente) stava nella lista dei si' da servire, e
--    Zafferano, ENERGY4YOU, Klavzar e SINTESIA avevano un progetto attivo e stage=risposto.
--    Da qui: `clienti`. Chi ci entra ha stage=cliente per effetto del trigger, e il cancello
--    delle proposte guarda anche qui. E' anche la base del portale clienti (Dre, 8/10:
--    «i personaggi principali del workspace sono i clienti»).
--
-- 2. IL LOCK UMANO, MURATO. I Paletti del 30/7: «serve un lock umano vero: nessun processo
--    automatico puo' toccare un campo deciso da una persona. Va risolto nello schema, non
--    nella disciplina dell'agente. E' il buco numero uno». L'8/10 rilettura.py:231
--    sovrascriveva ancora la classificazione, e 436 risposte «a mano» avevano classi
--    riscritte. Da qui: `prospects.deciso` dice quali campi ha deciso una persona, e un
--    trigger rifiuta ogni scrittura del ruolo di servizio su quei campi. Non disciplina:
--    lo schema dice no. Vale da oggi in avanti: le 436 vecchie non si bloccano al buio
--    perche' molte sono sbagliate; si ripuliscono dal Workspace, e da li' restano bloccate.
--
-- 3. IL FILO INTERO. sync_v2 registrava solo le ultime due mail nostre dopo l'ultima
--    risposta (933 risposte, 318 mail nostre nel database): la verita' su cosa e' partito
--    stava su Smartlead e basta. Da qui: `interactions.message_id` e `casella`, con un
--    indice unico, cosi' il sync puo' scrivere TUTTO il filo senza doppioni.
--
-- In fondo, le tre scritture della lista di Dre dell'8/10 (B1, B2, B3), che il guardiano
-- di Claude Code non ha lasciato fare dagli script: qui le fa il SQL editor, come gli schemi.

-- ───────────────────────────────── 1. CLIENTI ─────────────────────────────────

create table if not exists clienti (
  prospect_id uuid primary key references prospects(id) on delete cascade,
  dal         date not null default (now() at time zone 'Europe/Rome')::date,
  stato       text not null default 'attivo' check (stato in ('prova', 'attivo', 'sospeso', 'chiuso')),
  chi_segue   uuid references auth.users(id),
  note        text,
  deciso_da   uuid references auth.users(id),
  deciso_il   timestamptz not null default now()
);
comment on table clienti is 'Chi e'' cliente, deciso da una persona. E'' la fonte: stage=cliente ne e'' l''effetto, non la causa (v78, 8/10).';
alter table clienti enable row level security;

drop policy if exists "clienti: li leggono i ceo e chi li segue" on clienti;
create policy "clienti: li leggono i ceo e chi li segue" on clienti
  for select to authenticated using (sono_ceo() or chi_segue = auth.uid());
drop policy if exists "clienti: li scrivono i ceo" on clienti;
create policy "clienti: li scrivono i ceo" on clienti
  for all to authenticated using (sono_ceo()) with check (sono_ceo());

-- e' cliente adesso? (prova e attivo contano; sospeso e chiuso no)
create or replace function e_cliente(p uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from clienti where prospect_id = p and stato in ('prova', 'attivo'))
$$;

-- entrare in clienti mette stage=cliente e lo segna come deciso da una persona
create or replace function clienti_su_prospects() returns trigger
language plpgsql security definer set search_path = public as $$
declare chi uuid := coalesce(new.deciso_da, auth.uid());
begin
  if new.stato in ('prova', 'attivo') then
    update prospects
       set stage = 'cliente', awaiting_us = false,
           deciso = coalesce(deciso, '{}'::jsonb) || jsonb_build_object('stage', jsonb_build_object('da', chi, 'il', now(), 'via', 'clienti'))
     where id = new.prospect_id;
  end if;
  return new;
end $$;
drop trigger if exists trg_clienti_su_prospects on clienti;
create trigger trg_clienti_su_prospects after insert or update on clienti
  for each row execute function clienti_su_prospects();

-- ──────────────────────────────── 2. LOCK UMANO ───────────────────────────────

alter table prospects add column if not exists deciso jsonb not null default '{}'::jsonb;
comment on column prospects.deciso is 'Campi decisi da una persona: {"stage": {"da": uuid, "il": ts}, "classificazione": {...}}. Il ruolo di servizio non li tocca (v78).';

-- chi sta scrivendo e' uno script (chiave di servizio)? Una migrazione a mano (nessun
-- token) NON e' servizio: passa, come in puo_scrivere_soldi (v67).
create or replace function e_servizio() returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce(nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role', '') = 'service_role'
$$;

create or replace function lock_umano_prospects() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  c text; prima text; dopo text;
  protetti text[] := array['classificazione', 'stage', 'no_followup', 'fuori', 'pipeline_stage', 'email', 'email_alt'];
  deciso_qui boolean;
begin
  if e_servizio() then
    -- uno script non toglie un lock
    if new.deciso is distinct from old.deciso then
      raise exception 'lock umano: uno script non cambia «deciso» (regola del 30/7, murata l''8/10)';
    end if;
    foreach c in array protetti loop
      execute format('select ($1).%I::text, ($2).%I::text', c, c) into prima, dopo using old, new;
      deciso_qui := (old.deciso ? c)
                    or (c = 'classificazione' and coalesce(old.enriched ->> 'classificazione', '') = 'manual');
      if deciso_qui and prima is distinct from dopo then
        raise exception 'lock umano: «%» di % lo ha deciso una persona (% -> % rifiutato). Uno script non lo tocca: regola del 30/7, murata l''8/10',
          c, old.id, coalesce(prima, 'vuoto'), coalesce(dopo, 'vuoto');
      end if;
    end loop;
  elsif auth.uid() is not null then
    -- una persona dal Workspace: ogni campo protetto che cambia diventa deciso da lei
    foreach c in array protetti loop
      execute format('select ($1).%I::text, ($2).%I::text', c, c) into prima, dopo using old, new;
      if prima is distinct from dopo then
        new.deciso := coalesce(new.deciso, '{}'::jsonb) || jsonb_build_object(c, jsonb_build_object('da', auth.uid(), 'il', now()));
      end if;
    end loop;
  end if;
  return new;
end $$;
drop trigger if exists trg_lock_umano_prospects on prospects;
create trigger trg_lock_umano_prospects before update on prospects
  for each row execute function lock_umano_prospects();

-- il cancello delle proposte guarda anche `clienti`, non solo stage (difesa doppia)
create or replace function proposta_ammessa() returns trigger
language plpgsql security definer set search_path = public as $$
declare p record;
begin
  if new.tipo in ('risposta', 'umano') and new.stato in ('aperta', 'approvata', 'in_invio') and new.prospect_id is not null then
    select fuori, stage, pipeline_stage, no_followup, classificazione into p from prospects where id = new.prospect_id;
    if p.fuori or p.stage in ('cliente', 'perso') or p.pipeline_stage in ('cliente', 'perso')
       or coalesce(p.no_followup, false) or p.classificazione in ('soppresso', 'nervoso')
       or e_cliente(new.prospect_id) then
      raise exception 'proposta rifiutata: l''azienda % e'' cliente, in pipeline, persa, senza follow-up o bloccata (regola del 25/9, clienti dal v78)', new.prospect_id;
    end if;
  end if;
  if tg_op = 'INSERT' and new.tipo = 'risposta' and new.azione ? 'bozza' then
    if coalesce(new.azione->'lettura'->>'ultima_loro', '') = '' then
      raise exception 'bozza rifiutata: manca la lettura dell''ultima mail (azione.lettura.ultima_loro). Nessuna bozza senza lettura (25/9)';
    end if;
    if coalesce(new.azione->'lettura'->>'coerenza', '') <> 'COERENTE' then
      raise exception 'bozza rifiutata: la coerenza loro/noi non e'' COERENTE (%). Nessuna bozza senza lettura (25/9)', coalesce(new.azione->'lettura'->>'coerenza', 'assente');
    end if;
  end if;
  return new;
end $$;

-- ─────────────────────────────── 3. IL FILO INTERO ────────────────────────────

alter table interactions add column if not exists message_id text;    -- l'id del messaggio su Smartlead
alter table interactions add column if not exists casella    text;    -- da quale casella e' partita (le nostre)
create unique index if not exists uq_interactions_messaggio on interactions (prospect_id, message_id) where message_id is not null;
comment on column interactions.message_id is 'Id del messaggio su Smartlead: con l''indice unico il sync scrive tutto il filo senza doppioni (v78).';

-- ───────────────────── LE TRE SCRITTURE DELL'8/10 (B1, B2, B3) ────────────────

-- B3: i cinque clienti che il database credeva prospect
insert into clienti (prospect_id, stato, deciso_da, note)
select id, 'attivo', '43095060-b873-4d29-825b-55522f26af55'::uuid,
       'Cliente con progetto attivo o confermato da Dre; il database lo credeva prospect (domanda B3 dell''8/10)'
  from prospects
 where company in ('Zafferano Matteo Bertoli', 'ENERGY4YOU', 'SINTESIA', 'Fun Dallas Tours')
    or company like 'Paolo Klavzar%'
on conflict (prospect_id) do nothing;

-- B1: Twin System e SOLPOWER in fila (si' da 112 e 90 giorni, PDF pronto, nessuna fila li vedeva)
update prospects
   set awaiting_us = true,
       enriched = coalesce(enriched, '{}'::jsonb) || jsonb_build_object('rimesso_in_fila', jsonb_build_object(
         'quando', '2026-10-08', 'da', 'Dre (v78)',
         'perche', 'si'' senza analisi da 112/90 giorni, awaiting_us spento da un follow-up: nessuna fila lo vedeva. PDF pronto, serve la consegna. Domanda B1.'))
 where company in ('Twin System', 'SOLPOWER');

-- B2: Bank Station, il PDF di Luca e Aldo agganciato a Francesco, che l'ha chiesto
update prospects f
   set analysis_pdf = (select analysis_pdf from prospects where email in ('luca@bankstation.it', 'aldo@bankstation.it') and analysis_pdf is not null limit 1),
       awaiting_us = true,
       enriched = coalesce(f.enriched, '{}'::jsonb) || jsonb_build_object('pdf_riagganciato', jsonb_build_object(
         'quando', '2026-10-08', 'da', 'Dre (v78)',
         'perche', 'Francesco ha chiesto il reinvio; il PDF stava sui record di luca@ e aldo@. Domanda B2.'))
 where f.email = 'francesco@bankstation.it' and f.analysis_pdf is null;

-- la prova, da leggere subito dopo: devono tornare 5 clienti, 2 in fila, 1 PDF
select 'clienti' as cosa, count(*)::text as quanti from clienti where stato = 'attivo'
union all select 'in fila (B1)', count(*)::text from prospects where company in ('Twin System', 'SOLPOWER') and awaiting_us
union all select 'pdf a francesco (B2)', count(*)::text from prospects where email = 'francesco@bankstation.it' and analysis_pdf is not null
union all select 'stage=cliente per effetto', count(*)::text from prospects where id in (select prospect_id from clienti) and stage = 'cliente';
