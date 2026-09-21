-- v48 (21/9/2026): il cron di GitHub su questo repo non parte mai (direttore.yml
-- ha un cron ogni 20 minuti e in tre settimane non ha fatto una corsa a orologio:
-- tutte le corse sono workflow_dispatch, cioe' pg_cron e campanelli). Il pull
-- delle liste aveva lo stesso cron orario e non e' mai partito da solo.
-- Quindi anche il pull lo sveglia il database, come il direttore.

create or replace function chiama_pull()
returns void language plpgsql security definer set search_path = public as $$
declare
  tok text;
begin
  select decrypted_secret into tok from vault.decrypted_secrets where name = 'github_direttore';
  if tok is null then
    raise notice 'manca il token github_direttore nel Vault';
    return;
  end if;
  perform net.http_post(
    url := 'https://api.github.com/repos/studiogalilei/clara-dashboard/actions/workflows/pull.yml/dispatches',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || tok,
      'Accept', 'application/vnd.github+json',
      'User-Agent', 'clara-dashboard',
      'Content-Type', 'application/json'),
    body := jsonb_build_object('ref', 'main')
  );
end $$;

-- ogni ora al minuto 5: se un giro e' in corso, GitHub tiene il nuovo in coda
-- (concurrency group 'pull'); quando la raccolta e' completa il giro esce in
-- pochi secondi e non costa niente.
select cron.unschedule(jobid) from cron.job where jobname = 'pull';
select cron.schedule('pull', '5 * * * *', $$select chiama_pull()$$);
