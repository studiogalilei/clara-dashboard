-- v74 (6/10/2026): la sentinella la sveglia il database, come il direttore e il pull.
-- Il cron di GitHub della sentinella («ogni 15 minuti») parte ogni 5-9 ore: il 5/10
-- alle 1:55, 7:48, 16:27 e 22:48 UTC. Se il direttore si inceppa, chi lo rianima
-- arriverebbe ore dopo. Stesso token del direttore (github_direttore nel Vault),
-- sfasata di due minuti per non partire insieme a lui.

create or replace function chiama_sentinella()
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
    url := 'https://api.github.com/repos/studiogalilei/clara-dashboard/actions/workflows/sentinella.yml/dispatches',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || tok,
      'Accept', 'application/vnd.github+json',
      'User-Agent', 'clara-dashboard',
      'Content-Type', 'application/json'),
    body := jsonb_build_object('ref', 'main')
  );
end $$;

-- ogni 15 minuti, ai minuti 2, 17, 32 e 47. Se un giro e' ancora in corso GitHub
-- tiene il nuovo in coda (concurrency group 'sentinella').
select cron.unschedule(jobid) from cron.job where jobname = 'sentinella';
select cron.schedule('sentinella', '2-59/15 * * * *', $$select chiama_sentinella()$$);
