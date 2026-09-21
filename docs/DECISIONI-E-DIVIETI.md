# Le decisioni e i divieti

*Scritto il 21 settembre 2026, leggendo i 46 schemi del database, il codice e
STATO.md. Il compagno di `WORKSPACE.md`: quello dice **com'è fatto** il sistema,
questo dice **perché è fatto così** e **cosa non si tocca**.*

> **A chi legge.** Se sei un'AI e stai per mettere mano al Workspace, questo è il
> file da leggere per primo. Il sistema è **vivo e usato da sei persone**: Dre,
> Giacomo, Carlo, Lorenzo, Salvatore, Alex. Non è un progetto su cui sperimentare.
> Quasi tutto quello che sembra strano qui dentro è strano per una ragione, e la
> ragione è scritta sotto con la data e le parole di chi l'ha decisa.

---

## I cinque principi che spiegano tutto il resto

Prima delle singole decisioni, le cinque regole da cui discendono. Se una modifica
ne viola una, è sbagliata anche se funziona.

**1. Clara propone, una persona decide.**
Niente parte da solo. Ogni cosa che Clara vuole fare diventa una riga in `proposte`
e aspetta un sì. Vale per le mail, per gli avanzamenti di fase, per le
classificazioni. È la regola fondativa: viene dalla regola d'oro dell'outbound
(«mai inviare io»), e vale anche adesso che il sistema è grande.

**2. La regola sta nel database, non nell'interfaccia.**
Ripetuto testualmente in cinque schemi diversi (v17, v22, v23, v45). Chi può vedere
i soldi, chi vede quali aziende, ogni quanto gira un lavoro: tutto in Postgres con
le RLS, o in tabelle che si modificano dall'app. **Nascondere un bottone non è
sicurezza.** Se metti un controllo solo nel frontend, hai lasciato la porta aperta.

**3. Una verità sola.**
Il bug che è tornato più volte: la stessa domanda contava tre numeri diversi in tre
schermate. Da lì `src/lib/regole.ts`, dove «cliente», «prospect», il ricorrente e la
coda di oggi sono definiti **una volta sola**. Il 15/9 sono stati cancellati tre file
(`Tutti`, `Pipeline`, `TuttiElenco`) *solo* perché avevano una loro copia delle
regole. Se stai per scrivere una seconda definizione di qualcosa, fermati.

**4. Se si perde, non esiste.**
Il feedback sta nello strumento e non su WhatsApp, il diario sta nel database e non
nella testa, quello che si impara si chiede quando uno ce l'ha in mente. Motivazione
testuale di Dre (v40): *«su WhatsApp si perde»*.

**5. Chi decide deve poter cambiare senza chiamare nessuno.**
Le cadenze delle operazioni, le azioni di Clara, le istruzioni: sono righe di
database modificabili dall'app, non costanti nel codice. Se stai per mettere un
numero che Dre vorrà cambiare, mettilo in una tabella.

---

## I divieti

Le cose che non vanno toccate, e cosa succede se le tocchi.

### Non si tocca `vedo_prospect()`

È la funzione che decide chi vede quali aziende. Il 15/9 serviva aprire il
perimetro a chi ha una call in agenda, e la scelta fu esplicita (v35):

> *«Non si tocca vedo_prospect: si aggiunge una regola in più. In PostgreSQL le
> policy dello stesso comando si sommano (una basta), quindi questa apre senza
> rischiare di chiudere qualcosa che prima funzionava.»*

**Il modo giusto di allargare un perimetro è una policy nuova accanto, mai una
modifica a quella che c'è.** Toccare la funzione centrale rischia di far sparire
aziende dalla vista di chi ci sta lavorando, e non te ne accorgi finché non ti
chiama qualcuno.

### Le chiavi dei widget non si rinominano

`src/lib/widget.ts:53`: *«Le chiavi non si toccano: ci sono appese le preferenze
salvate.»* Rinominare `prospect` o `progetti` significa che ognuno si ritrova il
menu che aveva configurato. Nota: i nomi visibili sono già stati cambiati senza
toccare le chiavi. `prospect` si chiama «Pipeline», `progetti` si chiama «Clienti».

### Il warmup delle caselle non si spegne mai

Regola fissa di Dre dal 12/8, ripetuta in `scripts/clara.py`. Vale su tutte le
caselle, anche quelle ferme, anche a campagne in pausa. Spegnerlo significa
ricominciare il riscaldamento da capo.

### Nel sync di Smartlead: mai toccare i bloccati e i "fuori"

`sync_v2.py:329`. Un'azienda portata fuori dall'outbound vive nella pipeline: se il
sync le riscrive la fase, il lavoro commerciale fatto a mano sparisce. Stessa cosa
per chi si è disiscritto (`no_followup`): non lo si ricontatta più, e il sync non
deve riaprirlo.

### Il prospect scelto a mano non si sovrascrive

`calendario.py:353`. Quando qualcuno aggancia una call all'azienda giusta a mano,
l'automatismo non ci ripassa sopra. Vale come principio generale: **una scelta umana
esplicita batte sempre una deduzione della macchina.**

### Le credenziali dei clienti non entrano nel database

v38, sugli accessi dei progetti: si scrive **dove stanno** e **a che punto siamo**,
mai la password. *«Il posto, non la password»*.

### `STRIPE_ADMIN_KEY` resta solo sul Mac

Mai nei secret in cloud. In cloud gira solo la chiave in sola lettura
(`STRIPE_SECRET_KEY`), che legge gli incassi e non può muovere un euro.

### Non si aggiunge un secondo posto dove vive uno stato

La coda di Oggi stava in `localStorage`: spuntavi dal telefono la mattina e sul Mac
erano ancora da fare (v34). Ogni stato che conta vive nel database. Il browser tiene
solo preferenze di comodità.

---

## Le decisioni, e perché

### Sull'infrastruttura

**Niente Vercel, si sta su GitHub Pages** (9/9). Dre: *«se si perde sono casini»*.
Il Vercel dello Studio era bloccato dal recupero account con la 2FA persa, e la
scelta è stata togliersi la dipendenza invece di risolverla. L'app pubblica è il
repo `studiogalilei/clara` con i soli file compilati; il codice sta nel repo privato
`clara-dashboard`.

**Due orologi, non uno** (v10, v16). Il 7/9 il cron di GitHub non è partito da solo
per ore. Da lì: GitHub Actions ogni 20 minuti **più** pg_cron dentro Supabase ogni
ora, sfasato di mezz'ora. Se partono insieme non si pestano (`concurrency: direttore`)
e il secondo trova il lavoro già fatto. Motivazione: *«per un sistema che deve durare
anni un orologio solo non basta»*.

**Niente più processi legati al Mac** (7/9). Dre: *«non voglio che i processi siano
legati al Mac, voglio in cloud, che non si perda nulla»*. L'ascoltatore della chat
sul Mac è stato spento il 10/9 e sostituito da una Edge Function. Se vedi uno script
che gira in locale, probabilmente è residuo.

**Il token del direttore non è un PAT** (10/9). La pagina di GitHub non generava il
fine-grained token e Dre non aveva la password: si è usato il token della CLI `gh`.
**Se un giorno si rifà `gh auth login`, il token va rimesso in due posti**: nei
secret di Supabase (`GITHUB_DIRETTORE_TOKEN`) e nel Vault di Postgres
(`github_direttore`). Se il direttore smette di partire dal cron di riserva, guarda
prima qui.

### Su chi vede cosa

**Il perimetro parte dalla call tecnica** (11/9). Dre: *«Carlo entra dalla call
tecnica in poi, prima non vede i prospect»*. Prima di quel momento le aziende sono
lavoro commerciale, non ancora delivery.

**Ma chi ha una call con loro li vede lo stesso** (15/9, v35). Carlo in QA: *«ho la
call tecnica con Zafferano in agenda, apro la scheda e mi dice che è fuori dal mio
perimetro»*. La conoscitiva la fa lui, e senza vedere l'azienda non poteva nemmeno
prepararsi. Finestra: le call degli ultimi 30 giorni e quelle future.

**Chi porta un'azienda la può creare** (15/9, v36). Lorenzo lavora su LinkedIn e
trovava aziende che non potevano entrare nel Workspace. La regola: la crei solo se
scrivi il tuo nome in «chi segue», così la rivedi e si sa di chi è. Non apre niente
in lettura a nessun altro.

**I soldi solo ai ceo** (v17). Preventivi e incassi li vedono Dre e Giacomo. Nel
database, non nell'interfaccia.

**«Vedi come»** (12/9). Dre: *«voglio vedere cosa vedono gli altri»*. Un ceo si mette
nei panni di una persona e **tutte** le regole valgono per quella persona, non è
un'imitazione. Dettaglio importante: la riga in `vista_come` la scrive e la toglie
solo il ceo vero (`auth.uid()`, non `uid_eff()`), **così non può chiudersi fuori**.
Se tocchi quella policy, uno può restare bloccato nei panni di un altro.

**L'agenda senza azienda e senza proprietario è la vita privata di Dre** (v29). Solo
ceo. Sembra un dettaglio, non lo è: il calendario personale finisce nella stessa
tabella di quello di lavoro.

### Sulla pipeline e la vendita

**Si diventa prospect solo dopo l'analisi** (9/9). Il pedaggio è l'invio: chi ha
risposto ma non ha ancora ricevuto l'analisi è «in arrivo». Prima questa regola era
scritta in tre punti e i tre numeri non tornavano.

**Non si avanza di fase senza il riassunto della call.** Il pedaggio. Vale sulla
bacheca e sulla scheda.

**Fra avvio e cliente c'è la prova** (9/9, v14). Dre: *«la pipeline da prospect non
passa subito a cliente: passa prima al periodo di prova, due mesi, con inizio e fine.
Quando finisce mi riaccordo con loro (alzo il prezzo) e si passa al retainer. Il 97%
dei clienti comincia dal trial.»* Clara avvisa 14 giorni prima della fine.

**Il follow-up è a 6 giorni, non 5** (9/9). Alzato da Dre. **Se lo vedi a 6 e pensi
sia un bug, non lo è.**

**Dopo 10 giorni di silenzio post-analisi si esce dai prospect** (9/9). Va nei Persi
col motivo. Al primo giro ne uscirono 38 vecchi di giugno.

**Due fasi diverse, non una.** `stage` è l'outbound (Smartlead), `pipeline_stage` è
la vendita. `fuori=true` vuol dire fuori dall'outbound, dentro la pipeline. Confonderle
è il modo più rapido per fare danni al sync.

**Retainer e progetto sono cose diverse** (v6). Il ricorrente mensile e il lavoro
singolo con una scadenza. *«Il ricorrente da solo era metà della verità.»*

### Su Clara

**Clara non ha un account Google** (11/9). Dre ha detto no a `clara@studiogalilei.com`.
Clara agisce **a nome della persona che ha dato il permesso**, col refresh token in
`google_token`. Conseguenza pratica: se una persona non ha fatto «Collega Google»,
Clara non vede la sua posta e il suo Drive. Non è un bug.

**Il diario si riconosce da una colonna, non da un'emoji** (v33). Prima la domanda
del diario aveva 📔 davanti solo perché il codice la riconoscesse. Regola 13 di Dre:
niente emoji decorative. **Il fatto che una cosa sia comoda da programmare non
giustifica una violazione dello stile.**

**Le regole di tono valgono ovunque**: nel PDF, nella chat, nei prompt. Niente
trattino lungo, niente puntino centrale, niente punto esclamativo, niente parole
vuote. Il `·` è stato tolto da 23 file e 74 titoli in un colpo solo il 9/9 perché Dre
lo odia.

**Il diario si chiede 1-2 volte a settimana, non ogni giorno** (v25). *«In modo
genuino.»* Martedì e giovedì, recap il lunedì.

**Le azioni di Clara hanno un `ref`**, quindi non fa mai due promemoria per la stessa
cosa.

### Su cosa si è deciso di NON fare

Queste servono a non riaprire cantieri già chiusi.

**La Control Room di Carlo non si fa nel Workspace** (9/9). La dashboard per le
Google Ads la stanno costruendo a parte; a gennaio entra come widget.

**Osservatorio e LinkedIn: fuori per ora** (12/9). Si riprendono con le informazioni
di Lorenzo e Carlo.

**Le tre porte di Clara (Chat, Chiede, Propone): bocciate** (9/9). Clara è una sola:
la pallina per la chat, la Posta per le proposte.

**Google Calendar in push non si può.** Google chiede un dominio verificato per il
ricevitore; il nostro sta su Supabase. Il push di Gmail copre quasi tutto perché gli
inviti arrivano per mail. **Non è una cosa da sistemare, è un limite di Google.**

**Granola è spento**, sostituito dagli Appunti di Gemini: le call sono quasi tutte su
Meet e gli appunti sono già nel piano Workspace, senza costi in più.

---

## Dove il sistema è fragile

Le cose vere da sapere prima di toccare.

**Le migrazioni si applicano a mano.** 46 schemi, nessuna automazione. Se scrivi un
`schema_v47.sql` e non lo incolli su Supabase, il codice parla di colonne che non
esistono. C'è `npm run controlla-database` che confronta le colonne usate dal codice
con quelle vere: **lanciarlo dopo ogni modifica allo schema.**

**Le Edge Functions si deployano a mano** con la CLI. Non c'è CI che le pubblichi.

**Lo script di ripristino del backup non esiste.** Il backup gira ogni notte e cifra
tutto, ma nessuno ha mai provato a riportarlo indietro. **È il rischio più grosso
del sistema oggi**, e vale la pena chiuderlo prima di aggiungere funzioni.

**Il contratto di prova nei modelli è ancora la versione a 1.500€.**

**Il campanello di Smartlead va ri-registrato ogni giorno** (operazione `webhooks`,
04:50). Se smette, le risposte arrivano comunque col giro dei 20 minuti, più lente.

**L'ascolto push di Gmail scade dopo 7 giorni** e lo rinnova l'operazione `orecchio`.
Se quella fallisce per una settimana, Clara smette di svegliarsi sulla posta senza
dire niente.

**Documenti vecchi che non descrivono più il sistema**: `LEGGIMI-PRIMA.md`,
`SETUP.md`, `CANTIERE-CRUSCOTTO.md`, `docs/ARCHITETTURA-CLARA.md`,
`docs/clara-sg-system-prompt.md`. Restano attuali `docs/LA-STANZA-DI-CLARA.md` e
`docs/clara-sg-outbound.md` (il playbook che usa `bozze.py`).

---

## Gli errori già fatti, per non rifarli

Dal registro degli errori in `STATO.md`, quelli che valgono per chi scrive codice qui:

- **Le didascalie.** Riempire l'interfaccia di testi esplicativi dopo che era già
  stato deciso che il software non si spiega. *Un testo accanto a un elemento
  sopravvive solo se porta un **dato** (numero, data, delta) o un **feedback**
  (Salvato, toast). Se serve una spiegazione, si rende l'elemento più intuitivo.*
- **Il metodo prima del lavoro lungo.** Costruire un filtro su un segnale che era già
  stato misurato come non predittivo. *Prima di un lavoro lungo: il metodo risponde
  alla domanda vera?*
- **Le modifiche in blocco.** Una conversione su più file ruppe uno script, e se ne è
  accorto solo provandolo. *Dopo una modifica in blocco si lancia un controllo
  statico su ogni nome importato, non solo sulla sintassi.*
- **Il limite del piano gratuito si legge prima**, non dopo aver detto cosa si può
  fare.

---

## Cosa fare prima di toccare qualcosa

1. Leggi `docs/WORKSPACE.md` (com'è fatto) e questo file (perché).
2. Cerca il perché nello schema: `grep -l "<argomento>" supabase/schema_v*.sql`. I
   commenti in testa hanno data e parole di Dre.
3. Se è un perimetro: **aggiungi una policy, non modificarne una.**
4. Se è una regola di business: sta in `src/lib/regole.ts` e **una volta sola**.
5. Se è un numero che Dre vorrà cambiare: mettilo in una tabella, non nel codice.
6. Prima del push: `npm run controlla` e `npm run build`. Se hai toccato lo schema,
   anche `npm run controlla-database`.
7. Lo schema nuovo **va incollato su Supabase a mano**, o il codice parla di colonne
   che non esistono.

---

*Aggiornare questo file quando si prende una decisione, non quando si scrive il
codice che la applica. Una decisione non scritta è una decisione che si ridiscute
fra tre giorni.*
