-- IL METRO CON I COMMENTI (Dre, 29/9/2026, mentre etichettava)
--
-- «Dammi la possibilita' di scrivere commenti»: su una mail come «chiedo scusa, e'
-- entrato un cliente e mi sono scordato» l'etichetta da sola non basta. Dietro c'era
-- una call saltata, un'azienda poco in target e la decisione di lasciar stare. Il
-- commento tiene il perche' di Dre: e' il primo pezzo delle sue regole non scritte.

alter table metro_risposte add column if not exists nota text;

select 'schema v70 applicato: i commenti nel metro' as esito;
