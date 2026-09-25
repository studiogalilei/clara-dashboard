-- IL REGISTRO (25/9/2026, da Galileo: «log append-only, niente flag derivati»).
-- Dre: «come è possibile?» deve avere sempre una risposta. Ogni cambio dei campi
-- che decidono cosa Clara fa (stato, classificazione, pipeline, follow-up,
-- indirizzo, analisi) e ogni cambio di stato di una proposta finisce qui, con
-- CHI l'ha fatto: lo script (header X-Clara-Script che stanza.sb aggiunge) o
-- l'utente del workspace (auth.uid()). Solo inserimenti, mai modifiche.
create table if not exists registro (
  id        bigint generated always as identity primary key,
  at        timestamptz not null default now(),
  tabella   text not null,
  riga      text not null,
  campo     text not null,
  prima     text,
  dopo      text,
  chi       text
);
create index if not exists idx_registro_riga on registro (tabella, riga, at desc);
alter table registro enable row level security;
drop policy if exists "registro: lo leggono i ceo" on registro;
create policy "registro: lo leggono i ceo" on registro for select to authenticated using (sono_ceo());

create or replace function chi_scrive() returns text language plpgsql stable as $$
declare h text; u text;
begin
  begin
    h := current_setting('request.headers', true)::json ->> 'x-clara-script';
  exception when others then h := null;
  end;
  if h is not null and h <> '' then return 'clara:' || h; end if;
  begin
    u := auth.uid()::text;
  exception when others then u := null;
  end;
  if u is not null then return 'workspace:' || u; end if;
  return coalesce(current_setting('request.jwt.claim.role', true), current_user);
end $$;

create or replace function registra_prospects() returns trigger language plpgsql security definer set search_path = public as $$
declare c text; prima text; dopo text;
begin
  foreach c in array array['classificazione','awaiting_us','fuori','pipeline_stage','stage','no_followup','next_action','next_action_date','email','email_alt','analysis_sent','analysis_pdf','chi_segue','lost_reason'] loop
    execute format('select ($1).%I::text, ($2).%I::text', c, c) into prima, dopo using old, new;
    if prima is distinct from dopo then
      insert into registro (tabella, riga, campo, prima, dopo, chi) values ('prospects', new.id::text, c, left(prima, 300), left(dopo, 300), chi_scrive());
    end if;
  end loop;
  return new;
end $$;
drop trigger if exists trg_registra_prospects on prospects;
create trigger trg_registra_prospects after update on prospects for each row execute function registra_prospects();

create or replace function registra_proposte() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'INSERT' then
    insert into registro (tabella, riga, campo, prima, dopo, chi) values ('proposte', new.id::text, 'stato', null, new.stato || ' (' || new.tipo || ')', chi_scrive());
  elsif old.stato is distinct from new.stato then
    insert into registro (tabella, riga, campo, prima, dopo, chi) values ('proposte', new.id::text, 'stato', old.stato, new.stato, chi_scrive());
  end if;
  return new;
end $$;
drop trigger if exists trg_registra_proposte on proposte;
create trigger trg_registra_proposte after insert or update on proposte for each row execute function registra_proposte();
