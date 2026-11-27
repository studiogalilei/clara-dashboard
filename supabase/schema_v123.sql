-- v123 (27/11, Dre): «il default deve essere che ci sono i post automatici e un calendario... un post al giorno...
-- al massimo posso cambiare l'ora... posso modificare il post e cambiare le immagini... clicco un bottone e schedulo un
-- altro post». Ogni post ha il suo giorno e la sua ora (uscita_il) e un'origine: «auto» li prepara il sistema per
-- riempire i giorni vuoti, «mio» nasce da un audio o da un testo della persona e prende il posto dell'automatico del suo giorno.
alter table linkedin_post add column if not exists origine text not null default 'mio' check (origine in ('auto', 'mio'));

-- un giorno, un post: per ogni persona al massimo un post vivo (non scartato, non in errore) per giorno di uscita
create or replace function linkedin_giorno(t timestamptz) returns date language sql immutable as $$
  select (t at time zone 'Europe/Rome')::date $$;
drop index if exists linkedin_un_post_al_giorno;
create unique index linkedin_un_post_al_giorno on linkedin_post (autore, linkedin_giorno(uscita_il))
  where uscita_il is not null and stato not in ('scartato', 'errore');

-- l'ora di uscita di ognuno (si cambia dal calendario, vale per i giorni nuovi) e se vuole i post automatici
alter table linkedin_profilo add column if not exists ora text not null default '08:30' check (ora ~ '^[0-2][0-9]:[0-5][0-9]$');
alter table linkedin_profilo add column if not exists automatici boolean not null default true;

-- «Programma un post»: il post nuovo va nel primo giorno libero da oggi in poi; un giorno con un post automatico
-- non ancora uscito conta come libero (quello automatico lascia il posto). Oggi vale solo se l'ora non e' passata.
create or replace function linkedin_nuovo(dettato text, foto text default null) returns jsonb
language plpgsql security invoker set search_path = public as $$
declare
  io uuid := auth.uid();
  ora text := coalesce((select p.ora from linkedin_profilo p where p.utente = io), '08:30');
  g date := (now() at time zone 'Europe/Rome')::date;
  quando timestamptz;
  occupato linkedin_post;
  nuovo uuid;
begin
  if io is null then return jsonb_build_object('ok', false, 'perche', 'non sei dentro'); end if;
  for i in 0..60 loop
    quando := ((g + i)::text || ' ' || ora)::timestamp at time zone 'Europe/Rome';
    continue when quando < now() + interval '15 minutes';
    select * into occupato from linkedin_post
      where autore = io and uscita_il is not null and linkedin_giorno(uscita_il) = g + i and stato not in ('scartato', 'errore');
    if not found then exit; end if;
    if occupato.origine = 'auto' and occupato.stato <> 'pubblicato' then
      update linkedin_post set stato = 'scartato' where id = occupato.id;
      exit;
    end if;
  end loop;
  insert into linkedin_post (autore, dettato, foto, stato, origine, uscita_il)
    values (io, btrim(coalesce(dettato, '')), foto, 'da_scrivere', 'mio', quando) returning id into nuovo;
  return jsonb_build_object('ok', true, 'id', nuovo, 'uscita_il', quando);
end $$;
grant execute on function linkedin_nuovo(text, text) to authenticated;
