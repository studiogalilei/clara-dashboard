-- IL PREZZO SUGGERITO (Dre, 26/9/2026): «la fee segue la capacita' di spesa del
-- cliente e resta sotto il valore che gli portiamo. Il sistema propone, Dre decide».
-- Le modifiche concordate al dossier: si parte dalla domanda Google (volumi x CPC,
-- gia' precalcolati), il bilancio corregge; si calcola solo in pipeline; e' una
-- fascia, non un numero; tarato sui preventivi chiusi. Solo interno: mai in una mail.
create table if not exists parametri (
  chiave text primary key,
  valore jsonb not null,
  cosa text,
  aggiornato_il timestamptz default now()
);
alter table parametri enable row level security;
drop policy if exists "parametri: leggono tutti" on parametri;
create policy "parametri: leggono tutti" on parametri for select to authenticated using (true);
drop policy if exists "parametri: scrivono i ceo" on parametri;
create policy "parametri: scrivono i ceo" on parametri for all to authenticated
  using (exists (select 1 from profili where id = auth.uid() and ruolo = 'ceo'))
  with check (exists (select 1 from profili where id = auth.uid() and ruolo = 'ceo'));

insert into parametri (chiave, valore, cosa) values
  ('prezzo.base',          '1400',  'il lavoro fisso al mese (gestione, report, call): la base del canone, come nel calcolo «Quanto chiedere»'),
  ('prezzo.soglia',        '5000',  'sotto questa spesa Ads mensile il lavoro e'' sempre quello: il canone resta la base'),
  ('prezzo.quota',         '0.10',  'sopra la soglia il canone cresce di questa quota della spesa Ads gestita'),
  ('prezzo.floor',         '1200',  'il canone minimo sotto cui lo Studio non lavora'),
  ('prezzo.fascia',        '0.15',  'ampiezza della fascia intorno al punto (±15%)'),
  ('prezzo.quota_cattura', '0.03',  'IPOTESI: quota dei clic della provincia che una PMI puo'' comprare (spesa Ads sostenibile = domanda x CPC x quota)'),
  ('prezzo.conversione',   '0.02',  'IPOTESI: clic che diventano clienti, per il tetto di valore'),
  ('prezzo.tetto_quota',   '0.3333','la fee non supera un terzo del margine extra che portiamo'),
  ('prezzo.scaglioni',     '[[1000000,0.02],[3000000,0.015],[10000000,0.01],[30000000,0.008],[50000000,0.006],[null,0.005]]',
                                    'IPOTESI, budget marketing a scaglioni sul fatturato (limite superiore della fetta, % sulla fetta). Tarati sulla PMI italiana, non sul 5% del dossier'),
  ('prezzo.quota_agenzia', '0.25',  'IPOTESI: del budget marketing, la parte che va all''agenzia (il resto e'' spesa pubblicitaria)'),
  ('prezzo.margine',       '[[0,0.5],[0.03,0.7],[0.08,1.0],[0.15,1.2],[null,1.4]]',
                                    'IPOTESI: moltiplicatore per margine netto (limite superiore della fascia, moltiplicatore); in perdita = 0.5 e flag'),
  ('prezzo.cluster',       '{"A":1.1,"B":0.9}', 'IPOTESI: gia'' su Google Ads = A (budget esistente), non ancora = B (serve educazione)'),
  ('prezzo.taratura',      '{"preventivi_minimi":10,"accettati":0,"rifiutati":0}', 'dopo 10 preventivi reali si rivedono i parametri su accettati contro rifiutati')
on conflict (chiave) do nothing;

-- i numeri di bilancio li scrive Dre nella scheda quando li ha (o li porta un arricchimento futuro): enriched.bilancio
insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ordine, attiva) values
  ('prezzo', 'Il prezzo suggerito', 'Per chi e'' in pipeline: la fascia di canone dalla domanda Google della sua zona, corretta dal bilancio se c''e''. Solo interna, mai in una mail.', 'python3 scripts/prezzo.py', 60, 12, true)
on conflict (chiave) do update set cosa = excluded.cosa, comando = excluded.comando, cadenza_minuti = excluded.cadenza_minuti;
