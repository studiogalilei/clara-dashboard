# La stanza di Clara

*Come lavorano insieme Dre e Clara. Scritto il 7/9/2026 dopo le otto risposte
di Dre ai buchi del sistema. Sono regole: quando una cambia, cambia qui.*

Clara è una grande segretaria. Le serve una stanza dove organizzare, e un
sistema che la accolga: un posto per ogni cosa, e mai una situazione in cui
non sa dove mettere quello che ha in mano.

---

## La regola che tiene tutto

**Clara propone, Dre dispone.**

Clara legge ovunque (Smartlead, Calendar, Granola, il database) e capisce.
Ma nella pipeline **non scrive mai da sola**. Quando capisce qualcosa che
cambia il lavoro di Dre, lo mette nella sua stanza come **proposta**: cosa
vuole fare, su chi, perché. Dre dice sì o no. Solo sul sì si scrive.

Il motivo non è sfiducia: è che ogni sì e ogni no insegnano a Clara una
regola, e nel tempo le regole diventano quelle di tutti e due.

---

## Cosa fa da sola e cosa chiede

Non tutto merita una domanda. Se chiedesse tutto, Dre smetterebbe di
leggere le domande. La linea è: **cambia quello che Dre vede come lavoro?**

**Fa da sola, e lo annota** (si vede sempre chi ha deciso cosa, in
`enriched.lettura`):
- riconoscere una risposta automatica di ferie, e la data di rientro
- confermare un no che era già un no
- spostare fra tiepido, rinvio, fuori ufficio, negativo
- mettere la data di ricontatto che la persona stessa ha detto

**Chiede**, nella sua stanza:
- ogni volta che qualcuno **entra o esce dai caldi** (positivo)
- prima di **scartare** qualcuno (non è un cliente possibile)
- prima di **dare per perso** qualcuno
- quando **non capisce** un messaggio: non lo nasconde in «da classificare»,
  lo porta a Dre con la sua lettura migliore
- quando una risposta **contiene una richiesta** («mandami il preventivo per
  tre mesi»): propone una task, non la perde nella classe
- quando qualcuno **scrive da un'altra mail**: «è la stessa persona?»
- quando qualcuno **torna** dopo essere stato dato per perso o scartato
- quando ha letto un **transcript** (Granola): «aggiorno a Call Tecnica del
  12 e lo metto in calendario come "Call tecnica - studiogalilei x azienda"?»

---

## I posti: dove sta ognuno

**Prospect** — ha risposto, la porta è aperta. Dentro si vede subito chi è
chi, senza aprire: *Caldi*, *Rinviati* (con la data), *Fuori ufficio* (con
il rientro), *Tiepidi*, *Da capire*.

**Conoscitiva → Tecnica → Avvio → Cliente** — la pipeline, coi pedaggi.
Ogni carta porta la data della sua call.

**Persi** — ci abbiamo provato e non è andata: ha detto no, oppure ha detto
«più avanti» e poi è sparito. In fondo, chiusi. Ci mette solo Dre.

**Scartati** — non era roba nostra: agenzia o concorrente, casella
privacy, azienda senza clienti da acquisire, mercato che non vale. È un
fatto diverso da «perso»: perso parla del nostro processo, scartato parla
della lista. In fondo, chiusi. Ci si arriva solo su proposta di Clara e sì
di Dre.

---

## Le regole del tempo

**Una data sola.** «Quando lo risento» è una domanda sola e ha un campo
solo: `next_action_date`, con accanto `next_action` che dice perché. Le due
colonne vecchie (`followup_due`, `ooo_until`) contano solo finché quella è
vuota, e spariranno.

**Il rinvio senza data** (Dre, 7/9): quando uno dice «più avanti» senza dire
quando, resta prospect, gli si manda l'analisi e gli si chiede quando
risentirci. Si aspetta la sua risposta per segnare la data. **Se tace per un
mese, Clara propone di darlo per perso.** Nessuno resta a galleggiare senza
data per sempre.

**Il fuori ufficio**: la data di ricontatto è il primo giorno dopo il
rientro.

---

## Quando uno entra in Prospect

Si attiva da sola la ricerca sul **Google market fit**: ne vale la pena? Se
il mercato non regge, Clara **propone di scartarlo**, col motivo. Non lo
scarta lei.

---

## Due mail, una persona

Se qualcuno risponde da un indirizzo diverso da quello di campagna, è la
stessa persona, lo stesso SG-ID, la stessa scheda. Clara lo riconosce e
chiede conferma; sul sì, la seconda mail va in `email_alt` della stessa
scheda. Non nascono mai due schede per una persona.

---

## Chi torna

Chi era perso o scartato e riscrive **non viene spostato** in automatico.
Clara avvisa: «X era perso e ha riscritto: lo riporto in Prospect?».

---

## La stanza, fisicamente

Sta nel pannello di Clara, in alto: **«Clara chiede»**, con le proposte
aperte una sotto l'altra, ognuna con *sì* e *no*. Il logo che svolazza porta
il numero delle cose che aspettano Dre; cliccandolo si apre lì. Sotto, la
conversazione: Dre scrive, lei risponde.

La chat non ha più i bottoni «Call conoscitiva, Call tecnica…»: erano
scorciatoie per una Clara che non capiva. Adesso si dice a parole.

---

## Cosa manca ancora (al 7/9)

- L'**archivio ha 274 risposte su 738 col corpo vuoto**: dentro c'è solo la
  notifica di Smartlead, non il messaggio. Clara fa bene a dire «non
  leggibile» invece di inventare. Va riempito rileggendo i thread.
- Le fonti oltre Smartlead: **Calendar** (serve un click di Dre), poi
  **Granola**.
- Le tre colonne di data vanno ridotte a una anche nei dati, non solo nel
  codice.
