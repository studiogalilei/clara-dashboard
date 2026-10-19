# Il foglio della pipeline: design

*19/10/2026. Deciso con Dre in chat. Quello che è scritto «scelta di Achille» non l'ha detto lui: va controllato.*

## Perché

Dre vuole fare azione e chiudere clienti, non costruire («robe semplici, funzionali, affidabili e actionable, poi a 50k MRR penserò ad altro»). Il sistema deve gestire tutto da solo e lasciare a Dre solo quello che serve davvero a lui.

Gli serve **un colpo d'occhio**: quanti lead ci sono e quali, in ogni fase, dall'analisi al cliente. Lo vuole in un **foglio Google sul suo account**, non nell'app, sul modello del foglio di Giacomo: colonne da sinistra a destra con un'intestazione colorata, e sotto l'elenco che scende. «Un po' di gamification.»

**L'app (SG Oggi) resta la scheda del lead:** chi è, nomi, numeri, mail, conversazione, analisi, note. Lì si sblocca quando serve intervenire.

Il foglio prende il posto dei 12 stati decisi la mattina del 19/10. Gli stati dell'app vanno allineati alle fasi qui sotto, così app e foglio dicono la stessa cosa.

## Le fasi, da sinistra a destra

| # | Fase | Chi entra | Cosa succede | Chi agisce |
|---|---|---|---|---|
| 1 | **Analisi in preparazione** | ha appena risposto con un interesse | il sistema prepara la risposta con l'analisi e la manda. Se si blocca (analisi che non nasce, dubbio, controlli che fermano), avviso nell'app e Dre sblocca | sistema, Dre se bloccato |
| 2 | **Analisi inviata** | risposta con l'analisi partita | follow-up automatici | sistema |
| 3 | **Conversazione** | ha risposto dopo l'analisi senza prenotare | il sistema prepara bozze ma NON risponde da solo: le gestisce Dre. Menu di Dre: «Da chiamare», «In attesa di risposta», «Perso» (scelta di Achille: più «Da riscrivere») | Dre |
| 4 | **Chiamata conoscitiva** | conoscitiva prenotata o fatta | promemoria il giorno prima (già attivo) | Dre fa la call |
| 5 | **Chiamata tecnica** | concordata nella conoscitiva | avviso se manca il link in calendario (vedi sotto) | Dre |
| 6 | **Chiamata di avvio** | concordata nella tecnica | come sopra | Dre |
| 7 | **Periodo di prova** | partito il progetto di prova | campi: **costo del progetto, inizio, fine** | Dre |
| 8 | **Cliente** | ha firmato | campo: **retainer mensile**. Sotto la colonna, il **MRR** (somma dei retainer) | Dre |

**Il «doppio attacco»** sta nella fase 1. Quando conviene, cioè c'è il numero e il lead vale la pena, il sistema propone nell'app: «Invio e tu lo chiami, va bene?».
- **Sì:** la mail annuncia la chiamata di Dre, e Dre chiama.
- **No:** parte la risposta solita, senza nominare la chiamata.

Il consiglio di chiamare va reso **più selettivo** di adesso. Dre: «a volte mi dice di chiamare gente normalissima».

**Fuori dal percorso** (no, non contattare, fuori ufficio, nessuna risposta, contatti sbagliati): li gestisce il sistema in automatico, come oggi. Nel foglio non stanno nelle colonne. *Scelta di Achille:* una riga di conteggi in fondo o in testa («No 441 · Non contattare 73 · Fuori ufficio 83 · Mai risposto 12.547»).

## Com'è fatto il foglio

- Un solo foglio Google, **«Pipeline Studio Galilei»**, sul Drive di Dre (studiogalilei.com), nella cartella «2 Commerciale». *Scelta di Achille:* la cartella è da confermare.
- **Scheda principale «Pipeline»:**
  - Riga 1: il titolo e la **settimana** («Settimana 43 · 19-25 ottobre»), come le settimane del foglio di Giacomo.
  - **Le righe del gioco**, sopra le colonne:
    - i numeri della settimana: risposte, analisi inviate, conoscitive, tecniche, avvii, nuovi clienti;
    - **MRR attuale**, con una barra verso **50.000 €**;
    - un segno su ogni numero rispetto alla settimana prima (▲/▼).
    - *Scelta di Achille:* niente di più, per non farne un gioco vero.
  - **Una colonna per fase**, da sinistra a destra nell'ordine sopra. Intestazione grande, colore pieno diverso per ogni fase, e il conteggio nell'intestazione («Analisi inviata · 113»).
  - **Sotto ogni intestazione, l'elenco** che scende. Per riga: azienda, ed eventualmente un dettaglio corto (per esempio la data della call o la scadenza della prova). *Scelta di Achille:* due celle per lead (nome, dettaglio), così le colonne restano strette come quelle di Giacomo.
  - **Ordine dentro ogni fase:** prima il più nuovo, appena arrivato. Nel **Periodo di prova** prima la scadenza più vicina.
  - La conversazione (fase 3) mostra accanto all'azienda il **menu di Dre** come tendina.
- **Dove scrive Dre:**
  - la tendina della Conversazione;
  - costo, inizio e fine della Prova;
  - il retainer del Cliente;
  - una cella «Nota per Achille» per lead.
  - Il resto lo scrive il sistema.
- **Vince sempre Dre.** Una cella scritta da lui non viene più riscritta dal sistema. Il sistema legge le sue scritture e le applica: stato nell'app, ricontatti, chiusure.
- **Togliere un lead** (chi si perde dopo una call): lo fa Dre. Se un lead resta fermo in una fase oltre una soglia (*scelta di Achille:* 10 giorni senza novità), il sistema legge la trascrizione dell'ultima call e fa a Dre **una domanda breve** su cosa fare. La domanda sta nella pagina «Decisioni di Dre» e nell'app.
- **Aggiornamento:** ogni 10 minuti dal cloud (corsia leggera del direttore), come le altre operazioni.

## Da dove il sistema capisce le fasi (si aggiorna da solo)

- **Fasi 1-3:** dal filo delle mail, come oggi (lettura, analisi, invii).
- **Fasi 4-6:** dal **calendario di Dre**: «Chiamata conoscitiva», «Call Tecnica», «Call di Avvio», o i nomi che usano gli eventi veri. Si controllano i titoli esistenti e si rendono regolari.
- **Dalle trascrizioni delle call in Drive:** se nella conoscitiva ci si è accordati per la tecnica in una certa data, e il giorno dopo l'invito non è in calendario, nell'app arriva **un avviso a Dre**: «manda il link della call tecnica a X». Stessa cosa dalla tecnica all'avvio.
- **Fasi 7-8:** dai campi scritti da Dre.

## Le call in Drive

- **Tutte le call** (di Dre e dei ragazzi: Giacomo, Lorenzo, e chi le fa) finiscono **in automatico** nella cartella **«Chiamate»** del Drive condiviso «Studio Galilei», l'ex «5 Riunioni».
- **Riconoscere il lead di una call,** in quest'ordine:
  1. il **sito** (il più affidabile; nelle conoscitive si chiede sito, nome e email);
  2. la **mail** dell'invitato;
  3. il **nome** solo se nome e cognome sono riconosciuti in modo sicuro.
  - Se non è sicuro, non si abbina: si chiede a Dre.
- **Da costruire:** come arrivano le trascrizioni dei ragazzi. Meet le salva nel Drive di chi organizza la call. Dre è amministratore del Workspace: si può fare con una delega a livello di dominio, oppure facendo condividere a ognuno la propria cartella di registrazioni. La strada la sceglie il costruttore, con il criterio «più semplice che regge».

## Il documento «come lavorare col sistema senza ansia»

Una pagina sola per Dre, in parole semplici:
- cosa succede da solo e in quanto tempo (una risposta, un'analisi, una bozza, un follow-up, un promemoria);
- cosa gli arriva come notifica e quando;
- cosa deve fare lui, e dove (app o foglio);
- cosa fare se qualcosa sembra fermo.

I tempi vanno **misurati** sui giri veri, non stimati.

## Obiettivi, non obiettivi, cose da non fare

- **Obiettivo:** in 5 secondi Dre vede quanti lead ci sono in ogni fase e chi sono, e il foglio si aggiorna da solo.
- **Non obiettivi:**
  - un CRM completo;
  - report e analisi;
  - modificare dal foglio i dati della scheda (nomi, numeri, mail: quelli stanno nell'app).
- **Cose da non fare:**
  - un foglio che diventa una seconda copia che si contraddice con l'app;
  - colonne in più per ogni caso;
  - una gamification rumorosa;
  - qualunque mail che parte dal foglio.

## Vincoli

- Le mail partono solo per la strada di sempre (proposta, controlli, seconda testa, postino). Mai mail a clienti o a chi è in pipeline.
- Il repository clara-dashboard è **pubblico**: nessun dato di lead nei file. Il foglio sta solo su Drive.
- **L'API di Google Sheets** è spenta nel progetto Google Cloud del sistema (686127567563). Va accesa: una volta, a mano, o dal costruttore se ha i permessi. L'accesso a Drive c'è già.
- Rientra nella regola «azione prima di costruire»: si costruisce questo e basta.

## Scelte di Achille dopo la revisione (da controllare, non confermate da Dre)

- **Spostare un lead a mano:** su ogni riga c'è una tendina «sposta in» (le fasi, e «togli»). Serve a portare un lead in Prova o in Cliente e a togliere chi si perde dopo una call.
- **Chi vince tra foglio e app:** vince l'ultima azione manuale di Dre, ovunque l'abbia fatta. Il sistema non la riscrive, nemmeno se vede un evento nuovo in calendario: lo segnala a Dre. Una fonte sola nel database; il foglio scrive lì.
- **Stati dell'app:** si fanno corrispondere alle 8 fasi, senza migrare il database (`contattabile`, `seguiti` e `manda` restano come sono).
- **Menu della Conversazione:**
  - «Da chiamare»: entra in Oggi da chiamare.
  - «In attesa di risposta»: nessuna mail automatica; dopo 5 giorni senza novità lo ricorda a Dre.
  - «Perso»: stage perso, non contattabile, esce dalle colonne ed entra nei conteggi.
  - «Da riscrivere» non c'è.
- **Ordine di costruzione:**
  1. Il foglio, le fasi dal calendario di Dre, le sue trascrizioni, gli avvisi del link mancante, il documento «senza ansia».
  2. Dopo: il doppio attacco, il consiglio di chiamare più selettivo, le call dei ragazzi.
- **Decise da Dre (19/10):**
  - il MRR conta anche i clienti attuali, che vanno messi subito nella colonna Cliente (alcuni sono in prova: li riordina Dre);
  - le conoscitive le fa Dre, le tecniche Dre con Carlo (marketing) o, rarissimamente, con Lorenzo (outbound): Dre c'è sempre, basta il suo calendario.
- Dre ha approvato il 19/10: «è una roba semplice, non complicarla, fai e basta».

## Cosa resta al costruttore

- La forma esatta delle celle, i colori e i caratteri, dentro i limiti di Sheets e coerenti con i colori dell'app.
- Come leggere le trascrizioni (formato dei documenti Meet) e come estrarre l'accordo sulla call successiva.
- La tabella del database per i campi nuovi (prova, retainer, menu della conversazione) e come tenerla allineata con il foglio.
- Il nome dell'operazione nel direttore e la sua cadenza.
