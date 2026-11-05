
## 4/11 mattina: Clara manda da sola

Dre, appena visto il Desk: «io non ho tempo per leggere, ti ho detto che lo volevo automatizzato e
fatto bene; durante la notte dovevi solo trainarla; poi un Claude di turno che ogni giorno controlla
cosa ha fatto e come, e mi riferisce». E: «a Clara dalle un cervello intelligente, testa».

Cosa cambia, in tre mattoni:

1. **Il cervello è Fable 5.1** (`CLARA_MODELLO` default `claude-fable-5-1`, sforzo `high`). Il giudice
   resta Opus: chi controlla non è chi ha deciso. La versione di Clara ora dipende anche dal modello
   (`VERSIONE = sha1(identità + modello + sforzo)`). Costo misurato: 0,12-0,17 $ a decisione, 28 s.
   Prova sul lead che rimandava alla sede locale: con Opus v3.2 la bozza era rivolta alla sede ma
   senza cambiare destinatario (sarebbe tornata a chi aveva detto «non sono io»); è nata la regola
   «destinatario» nell'identità («A: …» / «Cc: …» in testa), e il postino e il Desk leggono la riga
   «Cc:» anche sotto. Il postino accetta un indirizzo nuovo solo se è dello stesso dominio o se lo ha
   scritto il lead nel filo; altrimenti la mail resta ferma col motivo.
2. **Autonomia** (`clara_prova.AUTONOMA`): una mail (analisi, risposta, orari, conferma) appena decisa
   viene votata dal giudice; se non è pericolosa passa ad «approvata» da sola (`approvata_da = Clara`)
   e il postino la manda (subito dalla strada veloce, entro 5 minuti dal direttore). Se il giudice la
   dice pericolosa resta ferma con «il giudice la ferma: …». `rilascia()` fa lo stesso sulle ferme
   già votate. Le call (`callback`) e i «decidi tu» (`escalate`) restano di Dre. Tetti: cervello 40 $
   al giorno, giudice 25 $.
3. **Il turno della sera** (`scripts/clara_turno.py`, dentro «La giornata» delle 19): il giudice
   rilegge ogni mail partita nelle 24 ore con quello che è successo DOPO (la mail com'è partita
   davvero e la reazione del lead) e il voto finisce in `giudice.dopo`; la mail a Dre dice cosa ha
   mandato Clara e com'è andata, le ferme, le sue (call e «decidi tu»), la spesa. La sezione
   «Aspettano te» ora ha solo le call: le risposte le fa Clara. I link puntano al Desk.

Il Desk non cambia di forma: è la finestra, non più il cancello. Invia/Modifica/No restano per le
ferme e per quando Dre vuole metterci mano.

Rilascio: postino in pausa, coda aperta ridecisa con Fable (`--giro --rifai --ore 720`), codice in
produzione, postino riacceso. Numeri sotto appena finito.

**Rilascio, 4/11 ore 9:47.** Coda aperta ridecisa con Fable 5.1 (17 lead, 7 minuti, circa 2 $): 9 mail
partite da sole dopo il voto del giudice (0 pericolose; 7 «mossa giusta», 2 «accettabile»; il testo per il
giudice è sempre «da ritoccare»: è il suo gusto, lo stile lo decide Dre), 3 escalate e 2 callback a Dre,
1 wait, 1 close. Il postino ne ha mandate 12: le altre 3 erano decisioni Opus v3.2 già votate, rilasciate
dal giro cloud prima che il rifacimento le raggiungesse (errore mio di sequenza: codice spinto prima della
fine del rifacimento; lette dopo, erano buone). Stasera il turno le rilegge tutte col dopo.

**Lo stesso giorno, da Dre davanti al Desk:** «la cosa va bene così com'è». Due richieste: dalla Coda, con
i filtri, vedere chi c'è e che conversazioni sta facendo Clara, cliccare e dirle «fermati su questa» con
il motivo (mi ha chiamato, l'ho chiamato io…) → «Me ne occupo io» (schema v105, `clara_prendi`,
`prospects.in_mano_a`; Clara non scrive più a quel lead, le mosse aperte si chiudono, il motivo resta come
nota; «Ridalla a Clara» per tornare indietro). E l'estetica: le righe divise da una linea grigia non si
vedono → ogni voce è una scheda con bordo e angoli arrotondati (Coda, Call, Relazioni, Clara).

Prossima fase, decisa da Dre: liste nuove con scraping, Google/Meta/LinkedIn fit e telefoni raccolti prima;
lui fa solo le chiamate.

## 4/11 pomeriggio: le quattro zone del Desk

Dre, davanti al Desk: «la coda attuale chiamala Relazioni; la Coda sia la coda delle cose di Clara, per avere
sempre in vista le sue attività, cosa sta facendo e cosa farà, una zona ad elenco; la pagina Clara chiamala
Analytics (lì non posso fare nulla, monitoro il lavoro di Clara che è una mia collega); il "Decidi tu" vorrei
fosse dove lei mi propone di intervenire chiamando perché c'è il numero (manda avanti il lavoro, ma mi
consiglia un touchpoint); dopo lo scraping nuovo coi numeri aziendali diventerà la norma, mentre i Da chiamare
in verde sono i certi». Colori: barra blu scuro, voce attiva bianca con testo blu, testi neri, bottoni bianco su
verde, blu minimale.

Fatto:
- **Relazioni** = la Coda di prima, identica, a `#/d/relazioni` (start_url e ingresso del Desk). In più la
  ricerca su tutte le aziende («Altre aziende», apre il filo). Il filo intero sta a `#/d/filo/<prospect>`.
- **Coda** = la coda di Clara (`src/desk/Coda.tsx`): Adesso, Ferme, Prossime (wait con la data), Passate a te,
  Fatte, Chiuse; in ordine di tempo; un tocco apre la relazione; nessun bottone.
- **Analytics** = la pagina Clara di prima.
- **«Ti consiglio di chiamare»** (`call_suggestion` nello schema e nell'identità v5e4ec43a; colonna
  `clara_decisioni.consiglio`, schema_v106; `clara_call.consigli`): in più alla mossa, Clara segnala un numero
  trovato nel filo o in scheda e il perché; un segnale fisso controlla che il numero stia davvero nel filo o in
  scheda. Giallo in Relazioni (pillola, blocco con tel: e Chiamato/Non ora) e in Call (sezione sotto «Da
  richiamare»). I «Decidi tu» veri (privacy, prezzi, partner) restano, pochi, con la proposta pronta.
- Colori come chiesto. La barra richiudibile resta.

Non visto nel browser da me: la sessione del browser di prova è scaduta e la creazione di un utente di collaudo
è stata bloccata dai permessi; tipi e test passano, il pacchetto è pubblicato. Dre lo guarda lui.

Ritocchi dello stesso pomeriggio, da Dre: al posto della priorità (0-130) uno **score d'interesse da 1 a 10**
(`regole.interesse`: la mossa scelta da Clara dà la base, call 10 e no 1; analisi mandata, consiglio di chiamata
e lead positivo aggiungono; il tempo passato toglie; è un numero per orientarsi, non una misura); i filtri a
pillola erano dispersivi → **linguette** in una riga, la scelta sottolineata; **niente forme a pillola** nel Desk
(regola CSS su `.desk`: bottoni, link e pillole con angoli a 10 px, come le voci della barra); sotto il nome,
«OUTBOUND DESK». Link unico per computer e telefono: https://studiogalilei.github.io/clara/#/d/relazioni
(sul telefono è l'app installata, che si aggiorna da sola).

**Le chiamate di Dre (4/11, dopo pranzo).** Call è la prima voce. Col «+» Dre aggiunge una chiamata: scrive
l'azienda o un numero, la ricerca (`clara_cerca`, ora anche per telefono e col numero in uscita) propone i lead in
scheda e, scelto uno, correla numero e persona; se non c'è, la aggiunge lo stesso. Giorno in cui richiamare, nota,
e finisce nella stessa lista dei «Da chiamare» di Clara. Su ogni chiamata (di Clara o sua): giorno programmato
(«Richiamare» non chiude, programma), note veloci (se il lead è in scheda vanno anche a Clara come nota), esito a
un tocco. Tabella `chiamate` (schema_v107): una riga per le sue, e una riga agganciata alla decisione per quelle
di Clara, che nasce alla prima programmazione o nota. `clara_call` torna `richiami` (Clara, con programmazione e
note), `mie` (le sue, con quello che il sistema sa del lead), `consigli`, `prossime`. Icona persone su Relazioni.
Non visto nel browser (stessa ragione di prima).

## 4/11 sera: l'analisi parte con la call dentro

Dre: «fa tanti giri prima di proporre la call… non ci devono far sapere un cazzo, noi gliela mandiamo
come regalo e il pretesto è arrivare alla call… non deve dire con il nostro fondatore… fanculo graduale».

- **send_analysis = analisi + due orari + link, in una mail sola, sempre.** Il primo orario è domani se il
  calendario vero è libero (finché si riempie: le date vicine fanno urgenza), il secondo due-tre giorni dopo
  (`bozze.due_orari`: da +2 giorni invece di +1), il link del calendario come alternativa (lo dà lo strumento
  `orari_liberi`, link nuovo `PCsE9SXEpEESnMqG9`). Niente «la legga e ci faccia sapere».
- **Prima persona.** Dramane non esiste nelle mail finché la call non è fissata: niente «fondatore», niente
  «con Dramane». Solo a prenotazione (book_meeting) e a telefonata fissata (callback) si dice che ci sarà
  anche Dramane, che ha seguito l'analisi. In call, se arriva solo lui, dice che Lorenzo ha avuto un contrattempo.
- **book_meeting ora scrive e prenota.** La decisione porta `meeting_at` (colonna `appuntamento`, v109) e una
  conferma di tre righe; il postino prima crea l'evento con Meet nel calendario di Dramane con il lead invitato
  (Google manda l'invito), poi manda la conferma. Se l'evento non si crea la mail resta ferma: non si promette un
  invito che non parte.
- **Segnali nuovi** (`clara_sdr.segnali`): analisi senza orari / senza link, «ci faccia sapere», «fondatore»,
  Dramane prima della prenotazione, conferma senza Dramane. Il giudice (`esame_clara`) conosce le regole.
- Invarianti: due blocchi nuovi in `test_invarianti.py`.

## 4/11 sera: prima il valore, poi l'incontro; le note di Dre sono ordini

Dre (screenshot di un lead): «qui Clara non ha ancora inviato l'analisi e mi consiglia di chiamarlo: sempre inviare
l'analisi e quello che porta valore, e dopo si può chiedere l'incontro. Mi deve consigliare di chiamarlo se l'abbiamo
inviata, è passato un giorno, non ha risposto né prenotato e abbiamo il numero; se non abbiamo il numero continua lei
a sentire a modo suo». E: «dai a Clara la capacità di comprendere le mie note: un unico cervello; non mi invia notifiche
su lead che ho già sentito su WhatsApp e che quindi gestisco io».

- **Consiglio di chiamata**: mai insieme a `send_analysis` né prima che l'analisi sia partita (regola in identità,
  segnale fisso, e `clara_prova` lo scarta alla fonte). Legge retroattiva: `ritira_consigli_prematuri()` a ogni giro.
- **Dopo l'analisi** (`segui_silenzio`): per ogni analisi partita da almeno un giorno feriale senza risposta né call,
  non in mano a Dre: col cellulare (regola «solo con un cellulare», `segnale_provvisorio.cellulare_di`) un consiglio
  di chiamata; senza, Clara decide il sollecito (contesto «SITUAZIONE DI OGGI: silenzio dopo l'analisi», regola 4bis:
  due orari nuovi + link, un solo sollecito), il giudice vota, la mail parte. Decisioni con `origine='silenzio'` (v111),
  `risposta_il` = quando è partita l'analisi. Finestra 10 giorni, max 10 per giro.
- **Le note di Dre** (`leggi_note_di_dre`): ogni nota firmata Dramane delle ultime 48 ore la legge il cervello
  (`snella_note.clara_letta_il`); se dice che se ne occupa lui → lead in mano a Dre, decisioni aperte scartate,
  consigli tolti. Le note entrano anche nel contesto di ogni decisione («NOTE DI DRAMANE»: ordini). Le note di
  Achille e Clara non contano; le più vecchie di due giorni si archiviano.
- Prova a secco del 4/11: 2 note («Li ho scritto su WhatsApp») → in mano a Dre; 1 consiglio prematuro da ritirare.

## 4/11 sera: via il Workspace completo

Dre: «elimina la roba del Workspace completo, non serve e non la uso mai… sia per me che per i ragazzi elimina tutto,
ho già avvisato tutti, ci faremo una piattaforma nostra con calma ma per ora pulizia». Cancellati `src/App.tsx` e
`src/components/` (53 schermate); resta `src/Login.tsx`. Chi non è ceo, e ogni indirizzo vecchio (#/pipeline, #/posta…),
trova la pagina «Il Workspace è chiuso» (`src/Chiuso.tsx`). Nel Desk e nella snella spariscono i link «Workspace
completo»; la pagina Oggi della snella manda le decisioni al Desk. Nessuna tabella toccata: gli script non dipendono
da quella interfaccia.

## 4/11 sera: comodo per il lead, comodo per Dre

Dre (una mail delle 10:47 senza link, con «mi indichi lei un giorno»): «non dobbiamo chiedere effort, rendiamo tutto
comodo; Clara deve vedere il mio calendario e le chiamate fissate e collegarle alle aziende; se non riesce o non è
sicura me lo dica e glielo collego io; così la prossima sappiamo che possiamo fare un follow-up tra 2-3 giorni».

- **Link sempre**: ogni mail con orari (analisi, orari, risposta) senza il link del calendario è un segnale; «mi indichi
  lei», «ci organizziamo» contano come chiedere sforzo (regex `ASPETTA`).
- **Follow-up dopo gli orari**: `segui_silenzio` copre anche `offer_slots`, dopo 2 giorni feriali (`ATTESA_FERIALI`);
  dopo l'analisi resta 1. Col cellulare consiglio a Dre, senza Clara sollecita (regola 4bis).
- **Collega all'azienda** (v112): `clara_call.prossime` porta l'id dell'evento; in Call ogni call senza azienda ha
  «Collega all'azienda» (ricerca + un tocco, RPC `clara_collega_call`, nota «Sistema» per Clara) e «Non è un lead»
  (tipo `interna`, sparisce). In fondo «Non so di chi sono»: gli eventi tipo «altro» senza azienda. Il sync del
  calendario non tocca un collegamento fatto a mano.

## 4/11 sera: niente vicoli ciechi («non devo aver bisogno di tornare da te»)

- **Numero**: «Senza numero» ha accanto «Aggiungi il numero» (sulla chiamata e in scheda, anche per i richiami di Clara, v113);
  una nota che è solo un numero su una chiamata senza numero diventa il numero.
- **Note modificabili** (v114): un tocco sul testo, Salva; Clara rilegge la nota corretta (`clara_letta_il` torna vuoto).
- **«No» con una nota = ordine**: Clara rifà la decisione seguendo la nota (`da_rifare`, `correzione_di_dre`, SITUAZIONE
  nel contesto); prima si segnava e basta. Provato in sandbox: «manda senza l'analisi» → reply senza allegato, due orari e link.
- **Ogni fermo dice il gesto**: i motivi del postino citano il bottone (tocca No e scrivi…, Me ne occupo io, «Invito fatto,
  manda la conferma»); un destinatario approvato da Dre non si ferma più; invariante che lo controlla.
- **Niente codici per il telefono**: via `CollegaTelefono`, «Entra con un codice», `lib/ponte.ts`; login «Outbound Desk».
- **Collaudo**: demo estesa al Desk (`?demo#/d/call`): provati a schermo numero, nota, Collega, Invito fatto, Profilo; RPC
  provate come Dre in transazioni annullate. Lezione: `tsc --noEmit -p .` non controlla niente, il build vero è `npm run build`.

## 4/11 notte: WhatsApp come gesto, il consiglio in Relazioni, il LinkedIn fit e i fit su una lista nuova

- **WhatsApp in Call è un gesto, non un link** (Dre: «se clicco vuol dire che l'ho passato e ce l'ho su WhatsApp»).
  Sta fra «Call fissata» e «Richiamare». Dopo il tocco: la chiamata resta in lista come contatto suo («Su WhatsApp»),
  compare «Apri la chat», la relazione passa a Dre (Clara si ferma), un consiglio di Clara si chiude con esito «whatsapp».
  Database: `chiamate.whatsapp_il`, `clara_call` v115 (chi è su WhatsApp sta in «mie» anche se la decisione è scartata).
- **Il consiglio di chiamata sta in Relazioni, in alto** («Ti consiglio di chiamare» con «Vai alla chiamata»): porta a
  `#/d/call/<id>`, la scheda è evidenziata e centrata fra le altre; gli esiti si danno lì. I consigli non hanno più una
  sezione a parte in Call: stanno nella stessa lista (regole.ordinaChiamate: programmate, consigli, le altre).
- **Il LinkedIn fit** (`google_fit.linkedin`, googlefit.verdetto_linkedin): B2B, ticket alto (sotto 2.000 € NO, fra
  2.000 e 5.000 PARZIALE), un compratore che si riconosce per ruolo/settore/dimensione; i segnali dal sito (pagina
  aziendale, Insight Tag). Il modello risponde a quattro domande nuove (chi_decide, pubblico_professionale,
  dimensione_clienti, ciclo_vendita). `canale` tiene conto dei tre fit. Retroattivo sui 912 fit esistenti dai campi
  salvati (681 NO, 231 PARZIALE; il motivo dice «da rifare» dove mancano le domande nuove).
- **I fit su una lista nuova, prima della campagna**: `scripts/fit_lista.py lista.csv` (CSV o XLSX, colonne
  riconosciute dai nomi di Apollo/Hunter/fogli a mano) scrive `lista_fit.csv` e `lista_fit.json` con Google, Meta,
  LinkedIn, ticket, canale, `alto_ticket` (stima alta ≥ 10.000 €). Un sito che non si legge NON va al modello:
  «non leggibile, da guardare a mano». `--senza-ricerche` evita i crediti SearchAPI; `--scrivi` salva in scheda per
  chi c'è già. La lettura del sito ora segue i redirect 308 (dominio senza www).
- **Il Profilo mostra i tre fit** (Google/Meta/LinkedIn), il canale consigliato e il ticket (clara_relazione v116).

## 5/11 notte: il consiglio con qualunque numero, retroattivo, e «Non ha risposto»

- **Consiglio di chiamata il giorno dopo l'analisi con qualunque numero** (Dre: «soprattutto i cellulari, però va
  bene anche quelli»): il cellulare prima, se no il numero migliore (firma, scheda, sito). `clara_prova.numero_da_chiamare`.
- **Retroattivo**: 72 consigli sulle analisi degli ultimi 45 giorni senza risposta, senza call e con un numero
  (`--consigli-retroattivi`): decisioni «aspetta» con il consiglio, in Relazioni e in Call. `supera_vecchie` non le
  tocca più (la prima notte ne aveva superate 62 su 72 dieci minuti dopo).
- **«Non ha risposto»** su un consiglio (Call e Relazioni): Clara prosegue coi follow-up un giorno feriale dopo la
  telefonata, anche sulle analisi vecchie; il sollecito nomina la telefonata in prima persona, lascia il numero di Dre
  e propone due orari nuovi con il link (regola 4ter di Clara, segnali se manca una delle due cose). Il numero sta in
  `regole.telefono_dre` (mai nel repo); se manca, il Desk lo chiede una volta e Clara rimanda il sollecito.
- Se poi il lead richiama Dre: «Me ne occupo io» come sempre.

## 5/11 all'una: nell'analisi un orario solo, domani, poi il calendario e il numero

- Dre: «proponiamo sempre il giorno successivo, finché non abbiamo riempito tutti gli slot del giorno successivo,
  poi si passa al prossimo; in alternativa il calendario per un altro giorno; se vuole sentirci prima al telefono,
  questo è il mio numero». Le regole del consiglio di chiamata restano.
- `bozze.un_orario` / `orario_da_proporre`: il primo buco libero da domani nel calendario vero (quando domani è
  pieno si passa da solo al giorno dopo; niente contatori, come deciso il 22/10). `due_orari` resta per il
  sistema vecchio.
- Lo strumento `orari_liberi` di Clara dà un orario, il link «per un altro giorno» e il numero di Dre
  (`regole.telefono_dre`). Identità, regola 3, 4bis e 4ter aggiornate; segnale nuovo: «manda l'analisi senza il
  numero». Il giudice sa la regola.
