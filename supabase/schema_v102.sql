-- schema_v102 (23/10/2026, turno delle 11): l'ispettore parte dal direttore.
-- L'orologio di GitHub saltava gli orari di ispettore.yml (cron «41 5-19»): dal 22/10 sera nessuna
-- corsa per oltre dieci ore. Il direttore gira ogni 5 minuti chiamato da Supabase e non perde giri:
-- da adesso l'ispettore e' una sua operazione, ogni ora, nella corsia pesante. La finestra di prima
-- (8-22 di Roma) la tiene ispettore.py; ispettore.yml resta solo per le partenze a mano.

insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ordine, attiva) values
  ('ispettore', 'L''ispettore',
   'Rilegge quello che e'' uscito davvero da Smartlead (sequenze, risposte a mano, caselle, rimbalzi) e lo confronta col Workspace. Guarda e dice, non tocca. Ogni ora dalle 8 alle 22; dalle 18 la pagella, il lunedi'' i consigli.',
   'python3 scripts/ispettore.py', 60, 27, true)
on conflict (chiave) do nothing;
