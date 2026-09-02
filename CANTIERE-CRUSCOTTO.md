# CANTIERE — Cruscotto ODYN (28/8/2026)

> **Per Achille in VS Code: leggere questo file per primo, poi costruire.**
> Tutto quello che sta qui è stato deciso con Dre il 28/8. Non ridiscutere,
> non richiedere: costruire. La bozza visiva approvata come direzione è
> l'artifact «Cruscotto ODYN» (terza versione); questo file la supera dove
> dice diversamente.

## Cosa si costruisce

Il cruscotto outbound di Studio Galilei, **su questa base** (odyn-crm:
React + Vite + Tailwind + Supabase già vivo con 13k prospect e login).
Non da zero: si evolve quello che c'è.

Obiettivo di Dre, testuale: *"un luogo dove non solo gestisco tutto ma tengo
tutto ordinato, monitorato e sono in grado di aggiungere cose/fare modifiche"*.
E il ruolo di Achille dentro: *"sei praticamente lo stronzo che rende
impossibile dimenticare qualcosa o fare errori"*.

## Decisioni prese (28/8, risposte esplicite di Dre)

1. **Apertura = coda di lavoro**, non pipeline. Avvisi + da rispondere +
   call in arrivo. La pipeline è un click a lato.
2. **Calendario = agenda interpretata** stile Falcon (Oggi / Domani /
   Settimana / Preparazione / Alert), non griglia. Achille legge e serve
   pronto: cosa preparare prima delle call, avvisi su sovrapposizioni.
3. **Accesso: Dre + Giacomo, anche dal telefono.** Due login (Supabase auth
   c'è già), layout responsive vero.
4. **Transcript: lo incolla Dre a mano** da Granola. Niente automatismi.

## La pipeline (nomi di Dre, sostituiscono i vecchi pipeline_stage)

`Prospect → Chiamata Conoscitiva → Chiamata Tecnica → Chiamata di Avvio → Cliente`

- Prospect = ha risposto (lead che risponde diventa prospect).
- **Il pedaggio**: non si avanza di fase senza incollare il transcript della
  call fatta. Bottone «Passa a …» spento finché il transcript non c'è.
  Vale sempre, anche di fretta.
- Sezione **Clienti** con il modello: *Periodo di prova 1.500€ × 2 mesi*
  oppure *Stable 1.400€/mese*.
- La nomenclatura call ufficiale sta in
  `Risposte (template verbatim).md` → «NOMENCLATURA CALL» (vault).

## I due cancelli

1. **Fuori binario** (in cima alla scheda): «L'hai già sentito tu, fuori dai
   sistemi?» — due bottoni Sì/No. Finché non risponde, nessuna bozza mail.
   Esiste perché il 21/8 Achille ha proposto follow-up a gente che Dre aveva
   già sentito al telefono.
2. **Transcript** (per avanzare di fase): vedi sopra. Quando Dre lo incolla,
   Achille lo legge e riempie la scheda con quello che è emerso.

## Gli avvisi di Achille (il potere che Dre mi ha dato)

Calcolati dai dati, mostrati in cima alla coda. Esempi veri:
- rosso: N persone ferme da 30+ giorni senza risposta
- rosso: call passata e il prospect non è avanzato di fase / transcript mai incollato
- rosso: «sentiamoci a settembre» detto a luglio e mai rifissata (caso Zeni)
- giallo: in attesa senza data (caso Apiemme, era in ospedale)

## La scheda del prospect

Tre colonne su desktop (stile Capsule), impilate su telefono:
- **sx**: come si raggiunge (email, tel, sito, città, casella da usare,
  LinkedIn) + chi sono (2-3 righe). Campi ✨ se riempiti da Achille;
  le correzioni a mano NON vengono mai sovrascritte dal sync (regola che
  esiste già in Scheda.tsx / sync_v2, mantenerla).
- **centro**: cosa è successo (timeline della conversazione, con «da qui
  diventa prospect» evidenziato) + il riquadro transcript.
- **dx**: il suo mercato con **il grafico a 12 barre delle analisi**
  (G F M A M G L A S O N D, altezze %, picco evidenziato — identico a come
  lo disegna render_doc_v2.py con BARS) + ricerche/mese, CPC, mesi vivi,
  «Vale la pena? Sì/No». Servono colonne nuove a DB (market jsonb).
- sotto: appunti di Dre (l'unico campo che Achille non riempie).
- Quando uno risponde e diventa prospect: Achille in autonomia ricerca e
  filla i campi (numero se si trova, email, nome, descrizione breve di chi
  è e ruolo, azienda, social, analisi, storico conversazione).

## Design — perché le bozze sembravano «AI» e come si evita

Studiato su Google Calendar il 28/8:
- **Il software non si spiega.** Etichette di 1-2 parole, zero frasi che
  descrivono cosa fa l'interfaccia. Niente copy da presentazione.
- **Una vista alla volta.** Non una pagina lunga da scorrere: clicchi un
  nome, la scheda si apre e sostituisce la vista. Ricerca in alto sempre.
- **Tutto risponde**: hover, click, tastiera, stati attivi.
- **Colore quasi a zero** nel contenuto: bianco, bordi grigi sottili, il blu
  solo su ciò che si clicca. Rosso/giallo solo per gli avvisi. Font di sistema.
  UNICA eccezione: la barra di navigazione in alto è blu Galilei pieno, come
  Capsule (il riferimento di Dre): è il marchio, non decorazione.
- Densità da gestionale, angoli poco arrotondati, niente ombre teatrali.

## Da tenere dal vecchio odyn-crm (già nel codice)

- Vista Oggi: «Da rispondere — la palla è nostra» (awaiting_us),
  follow-up dovuti (≥5gg), ricontatti programmati, rientri ferie.
- enriched: 'auto' | 'manual' con ✨ e protezione dal sync.
- Avviso «next step non definito».
- sync_v2.py (il segugio affidabile) resta la fonte dei dati Smartlead.

## Cose tecniche note

- `.env.local` c'è già e funziona; auth Supabase attiva (Login.tsx).
- pipeline_stage e kind sono colonne testo: i nuovi valori non richiedono
  enum, ma serve una migrazione dati per i vecchi valori + schema_v4.sql
  per: prospects.fuori_binario, prospects.market (jsonb),
  interactions kind 'transcript', tabella agenda.
- **Agenda da Google Calendar**: gtasks.py usa OAuth con scope solo Tasks;
  aggiungere lo scope calendar.readonly richiede UNA riautorizzazione di
  Dre nel browser (un click). Poi uno script tipo candidature.py sincronizza
  gli eventi in una tabella `agenda` su Supabase, ogni ora via launchd.
  Finché non c'è: il pannello agenda mostra next_action_date/followup_due.
- Per vederlo: `npm run dev` (vite). MAI Bash per il server nel client
  Claude Code: usare il preview del browser integrato.

## Regole di lavoro con Dre (le solite, valgono anche lì)

- Una bozza alla volta, feedback, poi la successiva.
- Meno roba tecnica a schermo: si parla di cosa cambia per lui.
- Mai inviare mail: Achille prepara, Dre clicca.
- Blocco Parked in fondo a ogni messaggio.
- Alla prossima consegna Dre vuole **qualcosa vicinissimo alla versione
  finale, interattivo e con i suoi dati veri**.

## L'oro del vecchio ODYN (estratto il 28/8, quattro fonti lette per intero)

**Già dentro la Dashboard:**
- Coda «Oggi» ordinata per priorità fissa (da rispondere → follow-up scaduti →
  next step scaduti → rientri OOO), e dentro ogni gruppo prima i positivi.
- «Dati aggiornati alle HH:MM» da sync_runs: mai un Oggi su dati stantii.
- Correzioni a mano marcate `manual`, il sync non le tocca più.
- Avviso su chi è in fase attiva senza prossimo passo (nessuna conversazione
  muore mai).
- Badge SOPPRESSO rosso in scheda: mai ricontattare, il blocco è nei dati.
- Stati che spengono le automazioni (fuori=true, cliente, perso…).

**Da costruire nei prossimi giri (in ordine di valore):**
1. **Coda di approvazione**: ogni riga = thread + bozza già lintata + analisi
   agganciata + un click di invio (via API Smartlead, il click resta di Dre).
   È il collo di bottiglia n.1: da ore di copy-incolla a 30 secondi a lead.
2. **Segugio-scheduler**: FU1 a 5gg, FU2 a 15gg, >40gg diventa ricontatto;
   rinvii alla LORO data; OOO → riga «rientro» a rientro+3gg lavorativi.
3. **Il fossato**: ogni correzione di Dre a una bozza salvata come
   originale→corretta e riusata come esempio. Proprietà intellettuale che cresce.
4. **Semaforo salute caselle** (soglie di Ali): ≥90% ok, <80% staccare,
   bounce <2%, reply ≥3%, 20/gg. Avviso quando una casella scende.
5. **Registro soppressioni** come cancello di ogni import di liste nuove.
6. **Agenda con esito inline**: le call passate restano in vista finché
   non hanno un esito, e l'esito aggiorna la pipeline.
7. **Parcheggio deal non standard** (success-fee, equity, partnership).

## Sintesi UI del 31/8 (4 ragionamenti + sintesi) — cosa resta da costruire

**Fatto il 31/8**: stile sul riferimento Dribbble di Dre (sidebar, Plus Jakarta
Sans, carte morbide), riga dei 4 numeri con «Da fare oggi» scura (a zero dice
«Tutto in ordine» + prossima call), «Achille ha controllato tutto alle HH:MM»
anche a zero avvisi, avvisi max 3 ordinati per costo della dimenticanza,
home mobile = Oggi col radar, ricerca con «/» e ⌘K.

**Backlog (in ordine di valore):**
1. Bozza di risposta DENTRO la coda: click sulla voce → pannello con la bozza
   dal template già pronta → «Copia e apri Smartlead». 2 click totali.
2. Ogni avviso col bottone che lo risolve inline (incolla transcript /
   decidi il passo / metti la data) senza aprire la scheda.
3. Card pre-call automatica: call entro 60 minuti → card scura in cima con
   un tap sul foglio di prep (chi sono, come è arrivato, l'analisi, le domande).
4. «Riprendi da qui»: l'ultima cosa lasciata a metà, con lo stato esatto.
5. Card cliente con «Prova, giorno X di 60» / «Mensile dal …» a colpo d'occhio.
6. Scheda mobile a fisarmonica (header fisso con prossimo passo, 4 sezioni).
7. Numeri raccontati nel saluto del lunedì (delta settimana, euro ricorrente).
8. Toast «Fatto» con Annulla al posto dei popup di conferma, ovunque.

## Il principio del premio (Dre, 31/8)

Testuale: *"quelle cose che non è scontato che si facciano devono avere una
specie di reward dopo… quando carico il transcript di Granola voglio che
succeda qualcosa, magari l'AI mi dà un feedback"*.

Regola: **ogni azione che costa fatica restituisce subito qualcosa di vero**
(mai un salvataggio muto, mai lode a vuoto). Già dentro: transcript → «X parole
archiviate + ho notato: budget, ottobre…» + domanda prossima call; nuovo
cliente → banner navy con l'onore («da prospect a cliente: è l'obiettivo del
gioco»); coda svuotata → «Tutto pulito alle HH:MM»; appunti → «Salvato ✓»;
cancello → «Segnato, non te lo chiedo più». Quando ci sarà il cervello vero
dietro (Achille via API), il feedback sul transcript diventa una lettura vera.

## Sistema ID (deciso da Dre il 31/8 — CHIUDE la questione formato)

`SG-000001`: l'ID identifica il SOGGETTO, permanente, non cambia mai.
Lo STATUS (prospect → client) identifica la relazione. In schema_v4 è
`sg_id` (numerazione automatica anche sui 13k esistenti); in UI compare in
testata della scheda accanto al badge PROSPECT/CLIENTE.

## Backlog sintesi 2 (31/8)
- «Perché li perdiamo»: grafico motivi di perdita — quando lost_reason è compilato pulito.
- Colonnina agenda accanto alla bacheca — quando le call salgono a 4-5/settimana.
- Mini-mese a pallini su mobile sopra la lista.
- Link all'appunto di prep nelle card evento del calendario.

## Il pedaggio al rilascio + l'agente dentro la dashboard (Dre, 31/8)

- Il pedaggio ora si paga NEL momento del drag: rilasci la carta sulla fase
  dopo → si apre «Riassunto e prossimi passi» (transcript Granola o due righe
  scritte). Riempi → avanza. Annulli → la carta torna dov'era.
- La zona in scheda si chiama «Riassunto e prossimi passi» (non più
  "transcript"): stessa cosa, nome suo.
- IL PERCHÉ (testuale): *"questo è importante perché poi vorrei impostare un
  agente che ha anche contesto di tutte le conversazioni e che sia in questa
  sales dashboard"*. Ogni riassunto salvato è contesto che si accumula per
  l'AGENTE DENTRO LA DASHBOARD: il prossimo pezzo grosso. Achille embedded:
  legge conversazioni + riassunti call, prepara bozze, risponde a domande
  («che si è detto con Zeni?»), avvisa. Da progettare con Dre.
