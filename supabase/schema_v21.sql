-- ODYN CRM schema v21 (11 set 2026) — da dove viene un'interazione
-- Gli appunti di Gemini entrano come interazioni «transcript»; per non
-- importarli due volte serve sapere da quale file di Drive vengono.
alter table interactions add column if not exists ref text;   -- es. gemini:<id del Google Doc>
create index if not exists idx_interactions_ref on interactions(ref);
select 'schema v21 applicato: interactions.ref' as esito;
