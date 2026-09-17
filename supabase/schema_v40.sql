-- I FEEDBACK DELLA SQUADRA (15/9/2026)
--
-- Dre, il giorno in cui si aprono gli accessi: «lascia da qualche parte una
-- sezione feedback dove loro provano la piattaforma e scrivono cosa
-- cambiare, anche le cose minime, tipo bottoni o posizioni, o i desideri».
-- Sta dentro lo strumento e non su WhatsApp per la stessa ragione di tutto
-- il resto: su WhatsApp si perde.
--
-- Ognuno vede e scrive i suoi; chi guida lo Studio li vede tutti, perche'
-- e' chi decide cosa si cambia.
create table if not exists feedback (
  id bigserial primary key,
  user_id uuid not null default uid_eff() references auth.users(id) on delete cascade,
  at timestamptz not null default now(),
  testo text not null,
  dove text,                                   -- la sezione: oggi, pipeline, clienti...
  genere text not null default 'scomodo',      -- guasto | scomodo | desiderio
  stato text not null default 'nuovo',         -- nuovo | letto | fatto
  risposta text
);
create index if not exists feedback_user_idx on feedback (user_id, at desc);

alter table feedback enable row level security;

drop policy if exists "i miei feedback" on feedback;
create policy "i miei feedback" on feedback for all to authenticated
  using (user_id = uid_eff() or sono_ceo())
  with check (user_id = uid_eff() or sono_ceo());

-- chi guarda «come» un altro scrive a nome suo, come per tutto il resto
alter table feedback alter column user_id set default uid_eff();
