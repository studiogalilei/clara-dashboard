# Clara oggi: com'è davvero (STEP 0, 3/11/2026 sera)

Fotografia in sola lettura per il kit Clara SDR v1 (`01_`, `02_`, `03_` in questa cartella).
Fonti: codice di questo repository (commit 3b5dddd), Smartlead via API in lettura, database
Supabase in lettura, il documento «Il sistema outbound di Studio Galilei (3_11_2026)».
Accanto a ogni fatto: **[live]** visto oggi su Smartlead/database, **[codice]** letto nel codice,
**[doc]** preso dal documento del mattino e non riverificato. Nessun dato di lead qui dentro:
il repository è pubblico.

## 1. Il percorso reale, passo per passo

| Passo | Cosa succede | Dove | Tabelle / API |
|---|---|---|---|
| Liste | File CSV fatto a mano (finora da Lorenzo), validato e caricato da Achille a mano | `scripts/strumenti/valida_lista.py`, `scripts/carica_lead.py` | `prospects`, `lead_lista`, `lists`, `suppressions` (letta qui), Smartlead `/campaigns/{id}/leads` |
| Controlli pre-invio | Mail personale, verifica, doppioni, clienti/no, icebreaker (regole + giudice dal 3/11) | `carica_lead.py` | Anthropic per il giudice |
| Fit prima della campagna | Fit di lista SI/PARZIALE/NO ogni ora; controllo Ads disponibile ma a mano | `.github/workflows/fit.yml` → `strumenti/fit_liste.py`; `carica_lead.py --controlla-ads` | `lead_lista.fit` |
| Sequenza | E1/E2/E3, ritardi 0/2/3 giorni, 1 campagna attiva | Smartlead | **[live]** |
| Risposta | Smartlead chiama il webhook, che lancia la strada veloce | `supabase/functions/smartlead-webhook/index.ts` → `.github/workflows/risposta.yml` → `scripts/risposta.py` | GitHub dispatch |
| Lettura | Lettore AI (55 casi C01-C55) + reti di parole | `scripts/lettore.py`, `scripts/lettore_regole.json`, `sync_v2.classe_col_lettore` | `prospects.enriched.lettore`, `interactions` |
| Fit del lead | Google Fit (+ Meta Ads) dopo la risposta | `scripts/googlefit.py` (`fit_nuovo.py` solo sul Mac) | `enriched.google_fit(_v2)` |
| Analisi PDF | Generata **dopo** il sì, gpt-5 + template nel bucket | `scripts/analisi_auto.py` (orchestrata da `scripts/lampo.py`) | bucket `vault/analisi/`, `prospects.analysis_pdf` |
| Bozza | Bozza scritta dal modello, cancello + coerenza | `scripts/bozze.py`, `scripts/lettura.py` | `proposte` (trigger `proposta_ammessa`) |
| Approvazione | Solo INT-01/03/23 (+08 con cc), Revisore gpt-5 deve dire «OK», 8-21, 60/giorno | `scripts/prima_risposta.py` | `proposte.stato=approvata` |
| Invio | Nel thread, con PDF e presentazione | `scripts/manda.py` → `POST /campaigns/{cid}/reply-email-thread` | `prospects`, `proposte` |
| Dopo l'analisi | Conversazione di Dre: notifica e stato nell'app; strade 2-3 opzioni | `scripts/conversazioni.py`, `scripts/strade.py` | `snella_lead`, `snella_numeri` |
| Follow-up | Template di Dre senza modello | `scripts/seguiti.py`, `scripts/followup.py` | `prospects.coda` |
| Calendario | Due orari veri dal calendario di Dre; la prenotazione la fa il lead col link | `bozze._slot_liberi`, `scripts/calendario.py`, `scripts/orecchio.py` | `agenda` |
| Pipeline | 12 stati, prossima mossa/responsabile/data, foglio ogni 10 minuti | `src/snella/`, `scripts/schede.py`, `scripts/foglio.py` | `snella_lead`, `snella_stati` |
| Regia | Direttore ogni 20 minuti (più pg_cron), interruttori in `operazioni` | `.github/workflows/direttore.yml`, `scripts/direttore.py` | `operazioni` |

## 2. Lo stato vero dei punti che il kit chiede di verificare

- **Stop on reply** [live]: `REPLY_TO_AN_EMAIL` su tutte le 19 campagne (1 attiva, 3 in pausa, 2 bozze, 10 completate, 3 archiviate). Aperture e click non tracciati. Riconoscimento fuori ufficio acceso.
- **Webhook** [live]: uno solo, sulla campagna attiva 4003942, eventi `EMAIL_REPLY`, `EMAIL_BOUNCE`, `LEAD_UNSUBSCRIBED`, verso la funzione Supabase. Le campagne in pausa e in bozza non ne hanno: se si riaccendono, le risposte entrano solo dal sync periodico.
- **Caselle** [live]: 12 caselle sulla campagna attiva, **tutte col nome mittente Lorenzo**, che non lavora più in SG. Le risposte automatiche (`manda.py`) partono da queste caselle e la firma nel codice è la sua (`bozze.py:775`, `ispettore.py:410-420`, `strumenti/crea_campagne.py`, `strumenti/firma_smartlead.py`).
- **Postino** [codice]: `manda.py` ricontrolla contattabilità e thread, prende un lucchetto, manda nel thread. **Nessuna ricevuta dopo l'invio**: la conferma arriva solo quando il sync rilegge la mail uscita.
- **Strada veloce** [live]: ultimo giro con un errore. Il passo «lampo» è andato in timeout dopo 900 secondi; gli altri passi erano ok.

## 3. Cosa esiste già e va tenuto

- La cattura delle risposte. Il 3/11 tutte le 757 risposte dal 22/9 erano nel database [live, giro del mattino].
- Il meccanismo di invio: niente doppioni e niente variabili vuote nella campagna attiva [live].
- L'invio nel thread con allegati, i cancelli di contattabilità (`stanza.contattabile` + trigger `proposta_ammessa`), il lucchetto dell'invio.
- I due orari presi dal calendario vero e la scadenza degli orari proposti (`orari.py`).
- Il lettore AI, come **lettura** (non come albero di decisione). C'è anche un banco di oltre mille risposte già classificate, utile per le prove.
- Google Fit + Meta Ads nel fit, il generatore PDF Google, l'app snella (Oggi, Lead, Tutti, Campagne, Scheda), il foglio, le 272 prove di `test_invarianti.py`.

## 4. Incoerenze e buchi trovati

1. **Le decisioni passano da troppe mani.** C01-C55 (lettore), INT-xx (bozze), regex di `sync_v2.classifica`, `cervello.classifica_risposta`, gpt-5 in `segnale_provvisorio`. Ogni passo riclassifica, e chi decide la prossima mossa è un incastro di cancelli. È la fonte degli errori «allucinanti»: non il modello, ma cinque letture che non si parlano.
2. **Due fornitori e tre client AI fatti a mano.** Lettura e strade su Claude; bozze, Revisore, PDF e coerenza su gpt-5. Nessun tool use da nessuna parte: ogni chiamata è un colpo solo con uno schema.
3. **Il dopo-analisi è un imbuto su Dre** [doc]: 49 decisioni aperte, 70 proposte aperte, 5 sì con PDF pronto fermi da 1 a 8 giorni. [live] In `snella_lead` 9 lead aperti («Da chiamare» 5, «Call fissata» 4) non hanno una prossima mossa scritta.
4. **Le call le prenota solo il lead col link.** Il sistema non crea eventi. «Call fissata» nel database non garantisce un evento vero [doc: il 24/10, 17 su 23 senza call].
5. **La provenienza della mail non è registrata.** `prospects.source` dice solo la lista (es. `lista:maps-scraper`). `trova_email.py` sa se l'indirizzo viene dal sito o da Hunter, ma non lo salva. Oggi alla domanda «dove avete preso la mia mail?» (C33) il sistema non ha una risposta documentata.
6. **Lista di soppressione** [codice]: la tabella `suppressions` si legge solo quando si valida una lista. Al momento dell'invio la guardia sono i flag sul lead (`soppresso`, `no_followup`, `fuori`). Va provato con un caso che un disiscritto da Smartlead finisca davvero in quei flag (prova 7 del kit).
7. **Il richiamo telefonico** nasce dal numero di cellulare noto (`schede.py`), non da una richiesta del lead. Va contro il kit: un numero in firma non è un permesso di chiamare.
8. **Elena non esiste nel sistema**: niente coda, niente profilo, niente casella a suo nome.
9. **Le analisi non sono pronte prima dell'invio.** Il PDF nasce dopo il sì (mediana 1h10 [doc]). Il controllo Ads arriva tardi: chi fa già Ads si scopre dopo che ha risposto.
10. **Regia sparsa.** Alcune righe di `operazioni` (googlefit, analisi, lampo, bozze, conversazioni, orecchio) esistono solo nel database, non nel repository. Cadenza scritta in tre modi diversi (5 min, 20 min, ogni ora). `npm run controlla-database` punta a un file spostato.
11. **Nessun id evento nel webhook.** I doppioni sono evitati per email (concorrenza GitHub per indirizzo), timestamp e chiavi uniche: regge, ma non è un'idempotenza per evento.
12. **Repository pubblico** [live]: `studiogalilei/clara-dashboard` è PUBLIC. Template e playbook stanno nel bucket riservato, non nel codice: va mantenuto così.

## 5. Il buco minimo verso il nuovo obiettivo

Mancano quattro cose, non trenta:
1. **Un cervello unico** dopo la risposta: legge thread + scheda + impegni e sceglie la mossa, al posto dell'incastro lettore → intento → cancello → Revisore → strade.
2. **Il registro degli impegni**: una prossima azione con responsabile, scadenza, prova e esito per ogni relazione aperta. In gran parte esiste già in `snella_lead`.
3. **La coda di Elena**, solo da richieste vere, con esiti semplici.
4. **La preparazione prima della campagna**: fit + Ads + analisi pronta + provenienza della mail.

## 6. Rischi e regressioni

- Toccare `prima_risposta`/`manda` può far partire mail. Per questo il cervello nuovo nasce **in ombra**: decide e registra, non manda.
- Le caselle a nome Lorenzo: cambiare il nome mittente sulla campagna attiva cambia l'identità a metà conversazione. È una scelta di Dre, non tecnica.
- Due regole di Dre in vigore che il kit supera: «dopo l'analisi la conversazione è di Dre» (20/10) e «niente automatismi su orari e call fino al 21/11» (21/10). Il kit le rovescia: serve il suo sì esplicito.
- Legale: il kit chiede una verifica legale del cold email B2B (art. 130 Codice privacy) prima di aumentare i volumi. Non è un blocco per le risposte a chi ha scritto, lo è per alzare gli invii.

## 7. Cosa non ho potuto verificare

- Il calendario di Elena (non esiste ancora) e i permessi delle caselle su Smartlead per un nome nuovo.
- Il comportamento di Smartlead sulle mail già in coda nel momento della risposta: la documentazione dice che una mail già accodata può partire lo stesso. Va misurato sui dati storici (giro della storia ancora in corso sulle campagne vecchie).
- I numeri del documento del mattino (49 decisioni, 70 proposte, 5 sì fermi) non sono stati ricontati stasera.
