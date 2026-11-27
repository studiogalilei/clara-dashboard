-- v124 (27/11, Dre): «un calendario tipo Google Calendar, da sinistra a destra... sopra la foto profilo con il nome, la
-- camera e l'audio che si trascrive in live, poi Ottimizza e migliora lo storytelling, poi il pulsante Schedule e
-- scegli il giorno e l'ora». Il post nuovo nasce senza giorno (si ottimizza), poi si programma: giorno e ora li sceglie
-- la persona. Se quel giorno c'era un post automatico non ancora uscito, lascia il posto.
create or replace function linkedin_programma(post uuid, quando timestamptz) returns jsonb
language plpgsql security invoker set search_path = public as $$
declare io uuid := auth.uid(); p linkedin_post;
begin
  select * into p from linkedin_post where id = post and autore = io;
  if not found then return jsonb_build_object('ok', false, 'perche', 'post non trovato'); end if;
  if quando < now() then return jsonb_build_object('ok', false, 'perche', 'quell''ora è già passata'); end if;
  if exists (select 1 from linkedin_post where autore = io and id <> post and uscita_il is not null
               and linkedin_giorno(uscita_il) = linkedin_giorno(quando) and stato not in ('scartato', 'errore')
               and (origine = 'mio' or stato = 'pubblicato')) then
    return jsonb_build_object('ok', false, 'perche', 'quel giorno c''è già un tuo post');
  end if;
  update linkedin_post set stato = 'scartato'
   where autore = io and id <> post and origine = 'auto' and stato not in ('scartato', 'errore', 'pubblicato')
     and uscita_il is not null and linkedin_giorno(uscita_il) = linkedin_giorno(quando);
  update linkedin_post set uscita_il = quando, stato = 'programmato',
         testo = coalesce(nullif(btrim(testo), ''), versioni -> coalesce(scelta, 0) ->> 'testo', nullif(btrim(dettato), ''))
   where id = post;
  return jsonb_build_object('ok', true, 'uscita_il', quando);
end $$;
grant execute on function linkedin_programma(uuid, timestamptz) to authenticated;
