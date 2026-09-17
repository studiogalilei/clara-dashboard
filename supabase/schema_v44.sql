-- IL WORKSPACE VIVO (16/9/2026)
--
-- Dre: «lo voglio in realtime, tutti gli update nel workspace li voglio in
-- realtime, deve essere proprio vivo, come se arrivassero segnali e li
-- categorizza». Il primo pezzo e' questo: il database avvisa i browser
-- aperti quando una riga cambia, invece di aspettare che qualcuno ricarichi.
--
-- Solo le tabelle che si guardano mentre si lavora. Le regole di accesso
-- restano quelle di sempre: chi non puo' leggere una riga non riceve
-- nemmeno l'avviso.
alter publication supabase_realtime add table proposte;
alter publication supabase_realtime add table task;
alter publication supabase_realtime add table agenda;
alter publication supabase_realtime add table chat;
alter publication supabase_realtime add table clara_messaggi;
alter publication supabase_realtime add table prospects;
alter publication supabase_realtime add table documenti;
alter publication supabase_realtime add table feedback;
alter publication supabase_realtime add table coda_fatte;
