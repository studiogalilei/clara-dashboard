-- v111 (4/11): da dove nasce una decisione di Clara. 'risposta' = una mail del lead (risposta_il e' la sua mail);
-- 'silenzio' = nessuna risposta dopo l'analisi (risposta_il e' il momento in cui l'analisi e' partita).
alter table clara_decisioni add column if not exists origine text not null default 'risposta';
create index if not exists idx_clara_decisioni_origine on clara_decisioni (prospect_id, origine);
-- le note di Dre le legge Clara (un cervello solo): quando una nota dice che se ne occupa lui, la relazione passa a lui
alter table snella_note add column if not exists clara_letta_il timestamptz;
notify pgrst, 'reload schema';
