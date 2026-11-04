
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
