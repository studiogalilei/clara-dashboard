# Io più il sistema: piano di costruzione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dre lavora dal foglio, riceve una sola notifica (lead in conversazione) e avvisi rari di guasto, vede cosa ha fatto Clara senza aprire Claude; il sistema riconosce i sì con l'AI e legge le sue mail.

**Architecture:** Si estende quello che c'è: `scripts/foglio.py` (il foglio e la nuova scheda «Clara»), `scripts/segnale_provvisorio.py` (notifiche), `src/snella/SchedaLead.tsx` (scheda), operazioni in `operazioni` lanciate dal direttore in cloud. Il lettore intelligente viene da `~/Documents/clara-nuova` (mattone 5) portato in Python nel vecchio.

**Tech Stack:** Python 3.9 (scripts), React + Vite + TypeScript (src/snella), Supabase REST via `stanza.sb`, Google Sheets API via `google_api.g`, Smartlead API, Anthropic Messages API via `cervello.py`.

**Spec:** `docs/superpowers/specs/2026-10-20-io-piu-il-sistema-design.md`

## Global Constraints

- Repository pubblico: nessun nome, mail o telefono di lead in file, test o commit (usare dati finti nei test).
- Tutto in cloud: ogni nuova operazione si registra in `operazioni` (chiave, comando, cadenza_minuti, attiva) e gira dal direttore; niente sul Mac.
- Le campagne Smartlead non si toccano (start, pausa, testi, mailbox); mai DELETE su Smartlead. Le categorie sono etichette sul lead.
- Ogni azione di massa passa da `scripts/polizia.py` (prova a secco, conteggi, campione).
- Prima di consegnare: `python3 scripts/test_invarianti.py`, `npm run controlla`, `npx vite build` verdi; ogni regola nuova ha la sua invariante in `scripts/test_invarianti.py`.
- Commit in italiano, in fondo «Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>».
- Testi per Dre in italiano semplice, frasi corte, niente gergo; niente trattino lungo come pausa.

## Review Focus

- Un lead che risponde due volte di fila dopo l'analisi: una notifica sola per conversazione aperta, non una per messaggio (Task 3).
- Un'autorisposta o un fuori ufficio dopo l'analisi: nessuna notifica (Task 3).
- Un avviso di guasto che resta vero per ore: una notifica alla prima volta e poi al massimo ogni 2 ore, e una «risolto» quando torna verde (Task 3).
- Un lead senza filo Smartlead (aggiunto a mano) o senza scheda: le celle link restano vuote, il foglio non cade (Task 1).
- Il lettore AI che non risponde o costa troppo: si ricade sulle liste di parole e la scheda Clara lo dice; tetto di spesa giornaliero (Task 6).

---

### Task 1: Il foglio, i due link e «prossimo»

**Files:**
- Modify: `scripts/foglio.py` (`griglia`, `forma`, `calcola`; `LAYOUT` → 5)
- Test: `scripts/test_invarianti.py`

**Interfaces:**
- Produces: `link_scheda(pid: str) -> str` (usa `segnale_provvisorio.link_snella`), `link_filo(p: dict) -> str | None` (URL della conversazione su Smartlead del lead; formato da verificare aprendolo dal vivo, None se manca campaign_id/lead_id), `prossimo_messaggio(pid: str, dati) -> tuple[datetime, str, str] | None` (quando, tipo, testo), riusato dal Task 4 via la stessa logica lato TS o un campo in `snella_*`.

- [ ] Invariante «foglio: link e prossimo»: `link_scheda('x')` finisce con `#/s/lead/x`; `link_filo({})` è None; `prossimo_messaggio` su dati finti con una proposta approvata di FOLLOW UP 1 per giovedì torna (giovedì, «follow-up», testo); senza proposte e senza follow-up in calendario torna None.
- [ ] Eseguirla e vederla cadere.
- [ ] Implementare. Nel blocco di ogni fase, accanto ad Azienda, una colonna stretta con due link `=HYPERLINK(url;"scheda")` e `=HYPERLINK(url;"filo")` (o due colonne strette, a scelta del costruttore purché resti l'effetto a celle) e una colonna «prossimo» con «gio 22/10» (vuoto se None). La fonte del «prossimo»: proposte aperte/approvate per il lead (`proposte`), poi la data del follow-up calcolata come in `scripts/followup.py`.
- [ ] Invarianti verdi; rigenerare il foglio vero (`python3 scripts/foglio.py`), rileggere via API 5 righe e aprire 2 link «filo» e 2 «scheda» per vedere che portano al lead giusto.
- [ ] Commit.

### Task 2: La scheda «Clara» nel foglio

**Files:**
- Create: `scripts/clara_foglio.py`
- Modify: `scripts/foglio.py` (`main` chiama `clara_foglio.scrivi(sid, ora)` alla fine del giro)
- Test: `scripts/test_invarianti.py`

**Interfaces:**
- Consumes: `foglio._g`, `foglio.trova_foglio`.
- Produces: `semaforo(ora) -> list[dict]` (ogni guasto aperto: `{"cosa": str, "da": datetime, "sta_facendo": str}`; lista vuota = verde), `diario(ora, giorni=2) -> list[tuple[datetime, str, str]]` (quando, azienda, cosa in parole di Dre), `scrivi(sid, ora) -> None`. `semaforo` è usato anche dal Task 3.
- Le regole del semaforo (dalla spec): sì senza analisi da più di 60 minuti nella finestra di invio (8-21); `manda`/`prima_risposta`/`seguiti` con ultime 3 corse in errore o nessuna corsa da 60 minuti nella finestra; crediti o chiave (errore 401/402/429 «quota»/«credit» nel dettaglio delle corse di `uso_modelli` o delle operazioni); foglio non aggiornato da 60 minuti; lead in conversazione senza notifica partita (dal Task 3).
- Il diario: dal `registro` e da `proposte` fatte (analisi mandata, follow-up partito, promemoria), `prospects.classificazione` cambiata a negativo (ha detto no), conversazioni aperte (Task 3), call viste (`agenda`).

- [ ] Invarianti «scheda Clara»: su dati finti, un sì arrivato 61 minuti fa alle 11 senza analisi → un guasto «sì fermo»; lo stesso alle 23 → nessuno; 3 corse `manda` in errore → guasto «invio fermo»; nessun problema → lista vuota; il diario mette la riga più recente in alto e usa frasi senza nomi tecnici («Analisi mandata», «Follow-up partito», «Ha detto no», «È entrato in conversazione»).
- [ ] Vederle cadere, implementare, vederle passare.
- [ ] La scheda «Clara» nello stesso file: riga 1 semaforo (verde «Tutto a posto · aggiornato alle HH:MM» o rosso con una riga per guasto), poi il diario di oggi e ieri. Stessa estetica del foglio (effetto a celle, font piccolo grigio per le ore).
- [ ] Giro vero, rilettura via API della scheda.
- [ ] Commit.

### Task 3: Una notifica sola, e gli avvisi rari

**Files:**
- Modify: `scripts/segnale_provvisorio.py` (le notifiche push), `scripts/sentinella.py` o il punto dove oggi nascono gli avvisi di guasto (trovarlo: il collaudo del 19/10 dice che la sentinella fallisce senza arrivare a Dre)
- Create: `scripts/avvisi.py` (operazione `avvisi`, ogni 10 minuti)
- Test: `scripts/test_invarianti.py`

**Interfaces:**
- Consumes: `clara_foglio.semaforo(ora)`, `segnale_provvisorio.notifica(titolo, testo, pid=None)`.
- Produces: `in_conversazione(pid) -> bool` (ha una risposta di persona arrivata dopo `analysis_sent_at`, non autorisposta), tabella di stato degli avvisi in `snella_numeri` chiave `avvisi` (ultimo invio per guasto).

- [ ] Invarianti: una risposta di persona dopo l'analisi → una notifica «È entrato in conversazione: <azienda>»; una seconda risposta dello stesso lead mentre la conversazione è aperta → nessuna nuova notifica; un fuori ufficio dopo l'analisi → nessuna; un «no grazie» dopo l'analisi → notifica (Dre: «risponde, è in conversazione»); prima dell'analisi → nessuna. Un guasto nuovo → una notifica; lo stesso guasto dopo 30 minuti → niente; dopo 2 ore → di nuovo; guasto risolto → «Risolto: …».
- [ ] Vederle cadere, implementare, vederle passare.
- [ ] Togliere tutte le altre notifiche push (sì da servire, prenotazioni, segnali caldi) lasciando le mail come sono; la funzione `notifica` resta, cambiano i chiamanti.
- [ ] Registrare `avvisi` in `operazioni` (10 minuti). Riparare la sentinella perché il suo esito arrivi in `semaforo`.
- [ ] Prova a secco sul giorno vero (`--prova`): quante notifiche sarebbero partite oggi; devono essere solo le conversazioni.
- [ ] Commit.

### Task 4: La scheda azienda pulita

**Files:**
- Modify: `src/snella/SchedaLead.tsx`, `src/snella/dati.ts`, eventualmente `src/snella/pezzi.tsx`
- Test: `src/snella/regole.test.ts`

**Interfaces:**
- Consumes: dai dati del lead `website`, `city`, `sector`, `campaign`, `analysis_pdf`; il prossimo messaggio (stessa regola del Task 1: proposte aperte/approvate, poi data del follow-up).
- Produces: azione «Ferma questo messaggio» che scrive `prospects.no_followup = true` e chiude (`stato = 'no'`, motivo «fermato da Dre») le proposte aperte/approvate del lead.

- [ ] Test in `regole.test.ts`: `prossimoMessaggio(lead, proposte)` torna quando + testo per una proposta approvata; null senza; `sitoCliccabile('esempio.it')` → `https://esempio.it`.
- [ ] Vederli cadere, implementare, vederli passare.
- [ ] La scheda, in quest'ordine: intestazione (azienda, persona, stato in una riga); contatti (telefono, mail, **sito cliccabile**, città, settore, campagna); «Il prossimo messaggio di Clara» (quando + testo esatto + «Ferma»); la conversazione (cosa ha scritto, cosa gli abbiamo mandato, analisi PDF); il modulo stato/prossima azione compatto, senza le frasi «Di default…», «Automatico: …», «Resta nel Workspace…».
- [ ] Aprirla col server di anteprima su telefono (390x844) e computer su 3 lead veri; controllare console senza errori.
- [ ] `npm run controlla`, `npx vite build`; commit; pubblicazione come da `pubblica.yml`.

### Task 5: Pulizia (bozze, Posta, categorie, mail di Dre)

**Files:**
- Modify: `scripts/bozze.py` (niente bozze per chi è in conversazione dopo l'analisi), `scripts/orecchio.py`
- Use: `scripts/polizia.py`, `scripts/categorie_smartlead.py`
- Test: `scripts/test_invarianti.py`

- [ ] Invariante: `bozze` non crea una proposta per un lead con risposta di persona dopo `analysis_sent_at`.
- [ ] Implementare, invarianti verdi, commit.
- [ ] Arretrato della Posta: con `polizia.py` in prova a secco, chiudere (stato `no`, motivo scritto) le bozze per conversazioni e i follow-up aperti da più di 7 giorni; conteggi e campione di 10 nel rapporto; poi l'esecuzione vera. Nessuna mail parte.
- [ ] Categorie Smartlead: leggere perché sono spente dal 13/10 (`operazioni`, `registro`), rifare il giro in prova a secco, controllare 10 etichette a campione, riaccendere `categorie`.
- [ ] Orecchio Gmail: leggere perché è spento dal 24/9; renderlo capace di una sola azione da solo: una mail nella casella di Dre che annulla o sposta una call (risposta all'invito, «annullare», «spostare», «non riesco») per un lead in `agenda` → il lead torna «Da chiamare» con una nota e il promemoria si blocca (proposta `ref=promemoria:<evento>` stato `no`). Tutto il resto si scrive nel diario di Clara. Invariante sul caso finto; giro a secco sull'ultima settimana di posta vera; accendere `orecchio`.
- [ ] Commit.

### Task 6: La Clara intelligente

**Files:**
- Read: `~/Documents/clara-nuova/supabase/functions/clara/` (lettore, pulizia, istruzioni), `~/Documents/clara-nuova/documenti/misure.md` (sezione mattone 5), `~/Documents/clara-nuova/prove/lettore_storico.ts`
- Create: `scripts/lettore.py` (il lettore portato in Python: pulizia + istruzioni + uscita strutturata), operazione `lettore`
- Modify: `scripts/sync_v2.py` (la classe la decide il lettore quando è acceso; le liste di parole restano come rete per i casi gravi), `scripts/cervello.py` se serve la strada Anthropic con uscita strutturata
- Test: `scripts/test_invarianti.py`, `scripts/misure/rigioco_lettore.py` (nuovo)

**Interfaces:**
- Produces: `leggi_risposta(testo_lead: str, filo: list[dict], lead: dict) -> dict` con almeno `{"classe": "positivo"|"negativo"|"ooo"|"rinvio"|"automatico"|"da_classificare", "caldo": bool, "non_scrivere": bool, "motivo": str}`; interruttore `operazioni.lettore` (attiva) e modalità in `snella_numeri` chiave `lettore` (`ombra` | `acceso`).

- [ ] Rigioco sulle 1.087 risposte etichettate (le etichette A3 di clara-nuova) con il modello Anthropic (Sonnet di `cervello.MODELLO_CLAUDE`; chiave `ANTHROPIC_API_KEY`), tetto di spesa 10 $: stampare le soglie di protezione (sì persi, no letti come sì, «non scrivetemi» mancati, caldi) e la precisione.
- [ ] Le soglie di protezione devono essere 0/0/0 e caldi tutti: se no, si corregge il lettore e si rifà.
- [ ] Ombra: per 1 giorno (o sulle risposte vere degli ultimi 3 giorni rigiocate) il lettore scrive cosa avrebbe deciso accanto alla classe delle liste; ogni disaccordo nel diario di Clara. Nessun errore pericoloso → `acceso` (decisione di Dre: «il più presto possibile»).
- [ ] Tetto di spesa giornaliero e ricaduta sulle liste se il modello non risponde (la scheda Clara lo dice).
- [ ] Invarianti con il modello finto: un «noi siamo interessati grazie» → positivo; «Cancellami» → negativo e non_scrivere; un'autorisposta → automatico.
- [ ] Commit; registrare `lettore` in `operazioni`.

### Task 7: Il documento e le regole del repo

**Files:**
- Modify: `scripts/strumenti/mappa_sistema.py` (il doc «Il sistema di Studio Galilei»), `CLAUDE.md` (i divieti: i follow-up partono da soli dal 19/10; la notifica unica; il foglio come base)

- [ ] Il doc diventa corto: il confine (fino all'analisi il sistema, dopo Dre), dove cliccare (foglio, link, scheda Clara, scheda azienda), cosa fare se il semaforo è rosso, il controllo del venerdì. Rigenerarlo allo stesso link e rileggerlo.
- [ ] CLAUDE.md aggiornato; commit.
