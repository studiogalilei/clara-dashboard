# Clara SDR v1: il piano minimo (STEP 1, 3/11/2026)

Base: `CLARA_CURRENT_STATE.md`. Sei cambi, in quest'ordine. Ognuno si può fermare e tornare
indietro da solo. Nessuno manda mail finché non arriva il passo 6 e il sì di Dre.

Legenda: **esiste** = c'è già e si riusa; **da modificare**; **nuovo**; **futuro** = non in v1.

## Il disegno in una riga

Un solo cervello (Claude via API, con tool use) legge la relazione intera e sceglie **una**
mossa con prova e responsabile. Il codice esistente fa da mani e da guardie. Il lettore C01-C55
resta come lettura di supporto, non decide più la prossima mossa.

Perché riduce la complessità: oggi la mossa nasce da cinque classificazioni in fila (lettore,
intento, cancello, Revisore, strade). Dopo nasce da una decisione, controllata da guardie fisse
che non dipendono dal modello.

## Cambio 1. L'esame, prima di tutto (nuovo, nessun rischio)

- **Cosa**: un banco di prova fatto da conversazioni vere già chiuse: le 15 prove della sezione 13
  del kit più circa 30 thread scelti per varietà (sì, sì caldo, «già seguiti», «più avanti»,
  fuori ufficio, collega, no, privacy, call già fissata, cliente).
- **Dove**: le conversazioni stanno nel bucket riservato, mai nel repository pubblico. Nel codice
  c'è solo lo script `scripts/esame_clara.py`, che fa girare il cervello sul banco e conta.
- **Misura**: errori pericolosi a parte (mail a un no, fuori ufficio letto come sì, call
  riproposta a chi l'ha già, opt-in inventato, numero in firma usato per chiamare), poi la
  qualità della mossa giudicata contro quello che avrebbe fatto Dre.
- **Rollback**: niente da tornare indietro, non scrive nulla.

## Cambio 2. Il cervello, in ombra (nuovo)

- **Cosa**: `scripts/clara_sdr.py`, un solo servizio. Identità dal file `02_` (adattato a system
  prompt), modello configurabile (`CLARA_MODELLO`, si provano Opus 5.5 e Sonnet 5.5 sul banco),
  tool use tipizzato.
- **Strumenti di lettura** (composti da funzioni esistenti):
  - `get_relationship`: `prospects`, `interactions`, `snella_lead`, `proposte`, `agenda`.
  - `inspect_campaign`: `sync_v2.sl_get` message-history e stato del lead.
  - `check_calendar`: `bozze._slot_liberi` / `due_orari`.
  - `read_asset`: `prospects.analysis_pdf` ed `enriched.analisi`.
  - `research_company`: testo del sito già raccolto e `googlefit`.
- **Uscita** (schema fisso): `lead_id`, `source_event_id`, `proposed_action` (una fra:
  `send_analysis`, `reply`, `offer_slots`, `book_meeting`, `assign_elena_callback`, `wait`,
  `close`, `escalate`), `draft`, `reason_summary`, `evidence_refs` (id del messaggio e frase
  esatta), `owner`, `due_at`.
- **Dove gira**: in `scripts/risposta.py`, dopo la lettura, dentro un try che non può rompere la
  strada veloce. Scrive solo nella tabella nuova `clara_decisioni` (sola aggiunta, si cancella con
  un `drop` senza toccare altro). È l'unica tabella nuova: serve per confrontare l'ombra con quello
  che è successo davvero.
- **Rollback**: un interruttore in `operazioni` (`clara_sdr`, spento di default).

## Cambio 3. Le guardie, fuori dal modello (da modificare)

Codice puro, provato in `test_invarianti.py`, applicato a ogni decisione prima che diventi azione:

- `stanza.contattabile` (esiste) legge **anche** la tabella `suppressions` (buco 6).
- **Niente prenotazione senza una conferma scritta** del lead: deve esserci un `evidence_ref` su
  un messaggio suo con un orario.
- **Niente richiamo senza richiesta**: `assign_elena_callback` richiede una frase del lead che
  chiede di essere chiamato. Un numero in firma non basta.
- **Privacy** (C33, opposizioni, Garante): la decisione è sempre `escalate` o `close`. Mai
  `send_analysis` o `offer_slots`.
- **Un'azione per evento**: chiave unica (`lead_id`, `source_event_id`).
- **Prezzi e contratti**: sempre `escalate`.

Rollback: le guardie possono solo bloccare. Toglierle riporta al comportamento di oggi.

## Cambio 4. La provenienza della mail (da modificare)

- Due campi in `prospects.enriched` (json, niente migrazione): `fonte_acquisizione` (lista,
  strumento, data) e `visibile_sul_sito` (URL e data della verifica, oppure assente). Restano
  separati, come chiede il kit.
- Li scrivono `strumenti/trova_email.py` e `strumenti/valida_lista.py` **da ora in poi**.
- Sui lead vecchi il valore è «non registrata». Non si ricostruisce e non si inventa niente.
- Il cervello, a «dove avete preso la mia mail?», dice la fonte vera se c'è; altrimenti passa a
  Dre. **Mai un opt-in inventato.**

## Cambio 5. Il Desk e la coda di Elena (da modificare, app)

- Nell'app snella esistente, niente pagine nuove decorative.
- **Oggi**: ogni riga mostra perché, prossima mossa, responsabile e scadenza, letti da
  `clara_decisioni` e `snella_lead`.
- **Elena**: un filtro su `snella_lead` con `responsabile='Elena'` (la colonna esiste già). Ogni
  riga ha la frase del lead che chiede il richiamo, il numero e la sua fonte, due orari veri, e i
  bottoni esito: prenotata, non risponde, richiamare, domanda, non interessato, recapito errato,
  a Dre.
- Gli esiti vanno in `snella_note` (esiste). Al giro dopo il cervello li legge.
- Futuro: profilo di Elena, notifiche sue, numeri suoi.

## Cambio 6. Dall'ombra alle mani (da modificare, solo col sì di Dre)

- Quando il banco è pulito (zero errori pericolosi) e una settimana di ombra regge il confronto,
  la decisione **diventa** la proposta in `proposte` e passa dalla strada che esiste già:
  `prima_risposta` → `manda` → invio nel thread.
- Si accende **una mossa alla volta**: prima `send_analysis` + `offer_slots` ai sì (sostituisce
  INT-01/03/23), poi `assign_elena_callback`, poi le risposte dopo l'analisi.
- Il Revisore gpt-5 e le strade restano finché la mossa corrispondente non è accesa e misurata,
  poi si spengono.
- Si aggiunge la ricevuta: dopo `manda`, una rilettura della message-history che conferma la mail
  uscita. Senza ricevuta l'azione è «non eseguita».

## Futuro (non in v1)

- Preparazione dell'analisi **prima** della campagna sulle liste di Dre (fit, Ads e PDF pronti al
  caricamento): si appoggia su `lampo.catena` e `fit_liste.py`.
- `book_meeting` che crea l'evento da solo, quando si decide su quale calendario.
- PDF Meta e LinkedIn.
- Esperimenti autonomi settimanali.

## Prove (prima di dire fatto)

`npm run controlla`, `python3 scripts/test_invarianti.py` con nuove prove per ogni guardia,
`scripts/esame_clara.py` sul banco, poi una prova di principio a fine percorso su un lead TEST non
reale (un indirizzo nostro), dal webhook alla decisione registrata.

## Cosa serve da Dre (blocchi veri)

1. **Elena e le caselle.** Oggi tutte le 12 caselle si chiamano Lorenzo. Chi firma le mail da ora,
   e da quando.
2. **Le due regole vecchie.** «Dopo l'analisi la conversazione è di Dre» (20/10) e «niente
   automatismi su orari e call fino al 21/11» (21/10): il cervello le supera, a partire dal
   cambio 6.
3. **Legale.** Una verifica del cold email B2B prima di alzare i volumi. Non blocca i cambi 1-5.
