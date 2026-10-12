-- v79 (12/10/2026): il budget Ads suggerito e il prezzo che non lo gonfia.
-- Dre, 12/10: «dice di spendere 15k in Ads, non e' realistico, di solito facciamo 20/30 al
-- giorno». La spesa veniva da domanda di tutta la provincia × CPC × 3% (prezzo.quota_cattura).
-- Da oggi il budget e' la regola di Carlo (scripts/mercato.py: 6 clic al giorno × CPC, fra
-- 10 e 25 €/giorno in prova, 30 in retainer), il canone e' il listino, e il tetto di valore si
-- stima con l'imbuto prudente. I parametri che non servono piu' si tolgono: una regola in un
-- posto solo, e niente numeri morti in Impostazioni.
insert into parametri (chiave, valore, cosa) values
  ('budget.clic_giorno',    '6',    'clic al giorno che bastano per capire se converte (~180 al mese): il budget di prova li compra, non di piu'''),
  ('budget.ctr',            '0.07', 'quota delle ricerche che cliccano un annuncio ben posizionato: fa il tetto fisico dei clic disponibili'),
  ('budget.pavimento',      '10',   'euro al giorno sotto cui non si raccolgono dati leggibili'),
  ('budget.tetto_prova',    '25',   'euro al giorno massimi in prova: sopra si aspetta che i numeri lo giustifichino (Carlo, 31/7)'),
  ('budget.tetto_retainer', '30',   'euro al giorno massimi in retainer senza una decisione del cliente in call (Dre: «di solito 20/30»)')
on conflict (chiave) do update set valore = excluded.valore, cosa = excluded.cosa, aggiornato_il = now();

update parametri set valore = '0.006', aggiornato_il = now(),
  cosa = 'IPOTESI prudente: clic che diventano clienti (contatto 3% × chiusura 20%), per il tetto di valore stimato dal fit'
  where chiave = 'prezzo.conversione';
update parametri set cosa = 'il canone se il listino non si legge: la fonte e'' la tabella listino (Impostazioni › Lo Studio)'
  where chiave = 'prezzo.base';

delete from parametri where chiave in ('prezzo.quota_cattura', 'prezzo.quota', 'prezzo.soglia', 'prezzo.floor', 'prezzo.fascia', 'prezzo.cluster');
