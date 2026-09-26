-- IL REPARTO (Dre, 26/9/2026): ognuno entra nel colore del suo reparto.
-- «in home sia albero bianco con fondo colore di colore reparto», e all'ingresso
-- la schermata piena col nome del reparto sotto, come fa Smartlead.
-- Direzione (Dre, Giacomo, Lorenzo) navy · Marketing (Salvatore, Carlo, Alex) rosso
-- Software (Okay e i tecnici) verde · AI blu acceso.
alter table profili add column if not exists reparto text;
alter table profili drop constraint if exists profili_reparto_check;
alter table profili add constraint profili_reparto_check
  check (reparto is null or reparto in ('direzione', 'marketing', 'software', 'ai'));

update profili set reparto = 'direzione' where nome in ('Dramane', 'Giacomo Facchin', 'Lorenzo Fornasier');
update profili set reparto = 'marketing'  where nome in ('Salvatore', 'Carlo Durigon', 'Alex');
update profili set reparto = 'software'   where nome in ('Okay Sözen');

-- il reparto viaggia con il profilo: l'app lo legge a ogni ingresso
create or replace function chi_sono() returns json language sql stable security definer set search_path = public as $$
  select json_build_object(
    'uid', uid_eff(),
    'nome', nome_eff(),
    'ruolo', coalesce((select ruolo from profili where id = uid_eff()), 'coordinamento'),
    'reparto', (select reparto from profili where id = uid_eff()),
    'concessi', coalesce((select json_agg(widget) from widget_accessi where user_id = uid_eff() and stato = 'approvato'), '[]'::json),
    'pod', coalesce((select json_agg(json_build_object('id', pr.id, 'nome', pr.nome, 'ruolo', pr.ruolo)) from pod po join profili pr on pr.id = po.membro_id where po.manager_id = uid_eff()), '[]'::json),
    'vista', (select json_build_object('id', v.come_id, 'nome', pr.nome) from vista_come v join profili pr on pr.id = v.come_id where v.ceo_id = auth.uid())
  );
$$;
