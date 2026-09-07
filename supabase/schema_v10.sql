-- ODYN CRM schema v10 (7 set 2026) — l'orologio di riserva
--
-- Il direttore gira su GitHub ogni 15 minuti. Ma il cron di GitHub, il 7/9,
-- non e' partito da solo per ore: e' noto che ritarda, e per un sistema che
-- deve durare anni un orologio solo non basta. Questo e' il secondo orologio:
-- pg_cron, dentro Supabase, che ogni 15 minuti chiede a GitHub di far
-- partire il direttore (workflow_dispatch). Se GitHub parte da solo, il
-- direttore trova gia' tutto fatto e non fa niente: i due orologi non si
-- pestano i piedi (il workflow ha «concurrency: direttore»).
--
-- SERVE UN TOKEN: un «fine-grained personal access token» di GitHub, creato
-- da Dre, con permesso Actions: Read and write SOLO sul repo
-- studiogalilei/clara-dashboard. Si mette nel Vault di Supabase, mai qui.
--
-- ISTRUZIONI:
--   1) sostituire IL_TOKEN qui sotto col token (una volta sola), incollare, Run
--   2) poi cancellare il token dalla riga: resta nel Vault, cifrato

create extension if not exists pg_cron;
create extension if not exists pg_net;

-- il token nel Vault (cifrato). Se esiste gia', lo aggiorna.
do $$
declare v_id uuid;
begin
  select id into v_id from vault.secrets where name = 'github_direttore';
  if v_id is null then
    perform vault.create_secret('IL_TOKEN', 'github_direttore', 'token GitHub per far partire il direttore');
  else
    perform vault.update_secret(v_id, 'IL_TOKEN');
  end if;
end $$;

-- la funzione che bussa a GitHub
create or replace function chiama_direttore(forza text default '')
returns void language plpgsql security definer as $$
declare
  tok text;
begin
  select decrypted_secret into tok from vault.decrypted_secrets where name = 'github_direttore';
  if tok is null then
    raise notice 'manca il token github_direttore nel Vault';
    return;
  end if;
  perform net.http_post(
    url := 'https://api.github.com/repos/studiogalilei/clara-dashboard/actions/workflows/direttore.yml/dispatches',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || tok,
      'Accept', 'application/vnd.github+json',
      'User-Agent', 'clara-dashboard',
      'Content-Type', 'application/json'),
    body := jsonb_build_object('ref', 'main', 'inputs', jsonb_build_object('forza', forza))
  );
end $$;

-- ogni 15 minuti: il direttore. Ogni notte alle 01:10 UTC: il backup.
select cron.unschedule(jobid) from cron.job where jobname in ('direttore', 'backup');
select cron.schedule('direttore', '*/15 * * * *', $$select chiama_direttore()$$);
select cron.schedule('backup', '10 1 * * *', $$
  select net.http_post(
    url := 'https://api.github.com/repos/studiogalilei/clara-dashboard/actions/workflows/backup.yml/dispatches',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || (select decrypted_secret from vault.decrypted_secrets where name = 'github_direttore'),
      'Accept', 'application/vnd.github+json', 'User-Agent', 'clara-dashboard', 'Content-Type', 'application/json'),
    body := '{"ref":"main"}'::jsonb)
$$);

select 'schema v10 applicato: due orologi' as esito;
