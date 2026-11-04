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

## Aggiornamento del 3/11 sera: niente paletti, si addestra in sandbox

Dre: «prima trainare, testare il sistema in sandbox, proprio il reale sistema che poi andrà a
lavorare, finché non arriva al livello che fa le cose bene, e rilasciarlo». Quindi:
- il cambio 3 (le guardie) **non esiste più come cancello**: le regole fisse restano in
  `clara_sdr.segnali()` come metro dell'esame, si contano e non fermano;
- i cambi 1 e 2 sono fatti e accesi: `scripts/esame_clara.py` (banco storico, uscita fuori dal
  repository) e `scripts/clara_prova.py` (sandbox sul vivo: decide su ogni risposta che entra, salva in
  `clara_decisioni`, scheda «Clara in prova» nel foglio con le colonne gialle di Dre, voto del giudice;
  `schema_v103.sql`, operazione `clara_prova` ogni 10 minuti più la strada veloce);
- il rilascio (cambio 6) arriva quando il banco è pulito e le decisioni di qualche giorno reggono
  le correzioni di Dre; le telefonate per ora le fa lui, le 12 caselle si rinominano al rilascio.

Primo esame (3/11, 35 conversazioni vere, giudice indipendente): identità v1 → 2 errori pericolosi,
25 mosse giuste, 10 accettabili; identità v2 (regola delle correzioni, via la frase sul cambio di
mittente) → 0 pericolosi, 30 giuste, 5 accettabili, 12 testi da ritoccare. Costo del cervello: circa
1,1 $ per 35 decisioni.
Identità v3 (notte del 4/11: firma come la casella, niente orari a chi vuole prima leggere, attese con
una data, l'analisi «mandata alle» nel contesto): 0 pericolosi, 28 giuste, 7 accettabili, 8 testi
buoni e 13 da ritoccare (il revisore vede il mittente coerente e non lo segnala più). Le 7 accettabili
sono quasi tutte «ha risposto due righe a un no secco»: corretto in v3.1 (a un no secco non si
risponde). Sul vivo (prima notte, 46 decisioni votate): 38 giuste, 8 accettabili, 0 pericolose.

## Il Desk (notte del 3-4/11)

Dre, 3/11 sera: «buttiamo al cesso l'intero sistema fatto finora e mi crei una nuova dashboard per
interagire al posto di questo... lascia spazio solo alle call... non overcomplicarlo». Fatto così:

- **Una decisione ha una vita** (`schema_v104.sql`): proposta → approvata → in_invio → inviata, oppure
  scartata (Dre ha detto no), superata (il lead ha riscritto), fatta (esito di una call o di una cosa
  sua). Tutto in `clara_decisioni`.
- **Clara decide su ogni risposta** (`clara_prova.py`, strada veloce + ogni 10 minuti; la prima notte
  anche su tutto l'arretrato dei 30 giorni) e il filo che legge unisce Smartlead e le mail del CRM
  fuori thread.
- **Il postino nuovo** (`clara_manda.py`, ogni 5 minuti e su chiamata dal Desk) manda SOLO le
  approvate: riusa i pezzi di `manda.py` (thread, HTML, link freschi, a chi rispondere), lucchetto
  approvata→in_invio, allegati (analisi + presentazione alla prima volta), «A:/Cc:» quando il lead ha
  indicato un collega, ricevuta rilettura del filo, lucchetti appesi sciolti dopo 30 minuti.
- **Il vecchio automatismo è spento**: prima_risposta, seguiti, bozze, strade, followup, manda
  (`operazioni.attiva=false`); il lampo si ferma all'analisi (`lampo.bozze_accese`). Restano sync,
  campanello, lettore (solo lettura), fit e PDF.
- **Il Desk** (`src/desk/`, `#/d/...`, i ceo entrano qui da `Radice.tsx`; PWA «SG Desk»): Coda
  (priorità, filtri, scheda con «ha scritto», «Clara», la mail; Invia / Modifica / No; esiti per
  richiami e «Decidi tu»; «va bene così» su aspetta/chiude), Call (da richiamare con tel: e esiti,
  agenda 14 giorni), Relazioni (ricerca, scheda, filo a bolle, decisioni, note), Clara (numeri 7 giorni,
  salute delle operazioni, come impara). Regole pure in `src/desk/regole.ts` con le prove.
- **Come impara**: Invia senza ritocchi = ok; testo cambiato = testo_finale + nota; No = motivo; esiti.
  Il giro delle correzioni rilegge `dre_*`, ritocca l'identità, rigioca l'esame.

Non fatto, di proposito: nuove tabelle oltre a clara_decisioni, agenti multipli, regole-cancello,
pagine decorative. Aperto: le notifiche sul telefono puntano ancora alla versione snella.

## Decisioni di Dre (archivio della discussione del 3/11)

- **Elena è una collega vera e il volto dell'outbound.** Le mail partono a nome suo, da caselle
  configurate per lei. Le comunicazioni non le attribuiscono cose che non ha fatto. Il numero di
  Elena può stare in firma. Se il lead non ha un numero, glielo si chiede.
- **Clara gestisce tutto in autonomia**, Elena interviene per le chiamate. Le regole del 20/10 («dopo
  l'analisi la conversazione è di Dre») e del 21/10 («niente automatismi fino al 21/11») sono
  superate, a partire dal cambio 6.
- **Le liste le fa Dre**, Lorenzo è uscito.
- **Nella conoscitiva Dre propone subito il percorso di 6 mesi con il prezzo.** Poi c'è la tecnica
  con Carlo.
- **Privacy**: solo la fonte vera, nessun opt-in inventato, nessuna prova costruita dopo.

## Ancora aperto

1. **Le caselle di Elena** (operativo): o caselle nuove a suo nome, che vanno scaldate per qualche
   settimana, o rinominare il mittente delle 12 di oggi. Ma l'indirizzo resta quello di Lorenzo, e
   si nota. Si decide prima del cambio 6. Il nome mittente su Smartlead lo cambia Dre.
2. **Legale**: una verifica con un professionista del cold email B2B prima di alzare i volumi.
   Non blocca i cambi 1-5.
