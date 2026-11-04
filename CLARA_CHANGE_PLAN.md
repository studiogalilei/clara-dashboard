
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
