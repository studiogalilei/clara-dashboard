-- v117 (5/11 notte, Dre): «se clicco Non ha risposto, Clara prosegue coi follow-up, dice che ho provato a chiamare e
-- lascia il mio numero». Il numero di Dre sta nelle regole (non nel repo pubblico): il Desk lo chiede una volta.
insert into regole (chiave, sezione, valore, perche, stato, fonte)
values ('telefono_dre', 'A', '', 'Il numero che Clara lascia nelle mail dopo una telefonata di Dre senza risposta (5/11). Lo scrive Dre dal Desk.', 'da_decidere', 'Dre, 5/11/2026')
on conflict (chiave) do nothing;
-- il link del calendario nelle regole era quello vecchio: ora e' lo stesso di bozze.CALENDARIO (4/11)
update regole set valore = 'https://calendar.app.google/PCsE9SXEpEESnMqG9', aggiornata_il = now(), aggiornata_da = 'Achille'
 where chiave = 'calendario' and valore <> 'https://calendar.app.google/PCsE9SXEpEESnMqG9';
