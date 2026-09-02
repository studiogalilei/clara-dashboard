---
tipo: documento di progetto
titolo: Agenti e Skills, l'architettura di Clara
deciso: 2026-09-02 con Dre
stato: approvato, da costruire
---

# Agenti e Skills

Come è fatta Clara dentro, e la regola per cui aggiungerle roba non la rompe. Ogni scelta qui sotto è stata decisa da Dre il 2/9/2026.

## Il principio

**Clara è una sola.** Non ci sono altri personaggi: «analisi», «risposte»,
«segugio» non sono colleghi con una faccia, sono cose che lei sa fare.
Una porta sola, una voce sola.

Quello che sa fare si divide in due famiglie:

- **Skill**: lo sa fare da sola. Regole precise, risultato sempre uguale,
  costa zero. Gira da sola, quasi sempre nel giro delle 8.
- **Agente**: serve una testa che ragiona caso per caso, e costa.
  **Non parte mai da solo.** Prepara la richiesta, la mette in coda, aspetta
  che Dre dica vai.

E sotto ci sono i **collegamenti**, le spine verso il mondo (Supabase,
Smartlead, Porkbun, Google Ads, Google Tasks, Google Calendar, Granola,
Zapmail). Una capacità senza la sua spina non si accende.

## La scheda

**Una capacità = un file.** Vive in `skills/<chiave>.json` nel progetto e
dichiara chi è:

```json
{
  "chiave": "brief-mattino",
  "nome": "Brief del mattino",
  "cosa": "Legge la giornata e te la scrive alle 8",
  "famiglia": "skill",
  "dipende": ["supabase"],
  "quando": "ogni mattina",
  "livello": "prepara",
  "testa": null,
  "costa": false,
  "chi": "tutti"
}
```

- `famiglia`: `skill` o `agente`
- `quando`: `ogni mattina`, `al bisogno`, `su tuo ordine`
- `livello`: `guarda`, `prepara`, `propone`, `esegue` (la scala del 31/8)
- `testa`: `null` se non le serve un modello, altrimenti `leggera`,
  `normale` o `pesante`
- `costa`: se girando spende soldi
- `chi`: `tutti` oggi; domani `ceo` e sparisce dalla lista di chi non deve vederla

Aggiungere una capacità vuol dire scrivere quel file. Compare da sola nella
sezione, senza toccare niente altro. Se una si rompe, le altre continuano.

**Perché JSON e non codice**: la scheda la leggono in due, la Dashboard
(TypeScript) e il motore del mattino (Python). Un formato che parlano
entrambi evita di scrivere la stessa lista due volte, che è il modo
sicuro per farle divergere.

## Le manopole

Il **livello sta nella scheda ed è fisso**. Non è una manopola in mano a
Dre: è una proprietà della capacità, decisa quando la si scrive, e sensata
di suo. La guardia sulle caselle guarda. Le bozze preparano. Fissare una
call esegue solo su ordine esplicito.

In mano a Dre c'è **l'interruttore**: acceso o spento. Nient'altro.

Motivo (2/9): tredici manopole a quattro posizioni sono tredici decisioni
prese una volta e mai più riguardate, e una schermata che dichiara un
livello che nessuno ha mai scelto davvero mente. La manopola si aggiunge il
giorno che Dre vuole cambiare un livello sul serio.

## Dove vive lo stato

La scheda è la dichiarazione e non cambia. Quello che cambia sta in una
tabella sola, `clara_skills`, letta sia dalla Dashboard sia dal motore
delle 8:

| campo | cosa tiene |
|---|---|
| `chiave` | il nome tecnico della capacità, uguale a quello nel file |
| `acceso` | l'interruttore di Dre |
| `ultimo_giro` | quando ha girato l'ultima volta |
| `ultimo_esito` | cosa ha fatto, in una riga |
| `owner` | chi possiede la riga (vuoto = dell'azienda) |

La riga nasce da sola alla prima accensione: una capacità nuova non ha
bisogno che qualcuno tocchi il database.

Spegni qui, e domattina il motore obbedisce. Un posto solo, nessuna copia.

## La coda degli agenti

Quando una skill capisce che serve una testa (un'analisi da fare, una
risposta da scrivere, un foglio di prep prima di una call) **non chiama
nessuno**. Scrive un messaggio nella Inbox di Clara con dentro tre cose:
cosa servirebbe, perché adesso, e che costerebbe.

Dre apre e dice vai. Il lavoro parte da lì, con Claude, dentro una sessione.

Niente parte a sua insaputa. Niente costa a sua insaputa.

## La testa: chi ragiona, e come si cambia

Gli agenti non chiamano Claude. Chiamano **la testa**, e chi sia la testa lo
dice un file di configurazione (Dre, 2/9).

Un punto solo nel codice, con tre funzioni: fai una domanda, dammi una
risposta strutturata, dimmi quanto è costata. Sotto ci sta quello che si
vuole: oggi Claude, domani un modello sul Mac, dopodomani un altro
fornitore. Nessun agente si accorge del cambio.

Il confine parla il **dialetto OpenAI**, che non è una scelta di campo ma la
presa universale: ci si attaccano i modelli locali (Ollama, LM Studio), i
proxy aperti tipo LiteLLM, e con un adattatore sottile anche Anthropic.

**Perché adesso e non dopo**: se gli agenti scrivono dritti sul fornitore,
cambiarlo vuol dire toccarli tutti uno per uno. Con il confine è una riga di
configurazione. Costa mezza giornata oggi e non scade mai.

**Cosa NON promette**: l'indipendenza dalla qualità. Un'analisi Canossa
oggi la scrive un modello forte, e un modello locale non ci arriva. La
libertà che si compra qui è quella di cambiare senza rifare, che è una cosa
diversa e più utile.

**I dati sono già liberi**: Supabase è Postgres. Il giorno che lo si vuole
su un server proprio è un salvataggio e un ripristino, non un progetto.

## Da dove viene questo disegno

Le scelte qui sopra non sono nate a mente. Il 2/9 abbiamo studiato come è
fatta dentro Claude Code, che è il sistema agentico più esaminato in giro
(il suo codice e le sue istruzioni sono pubblici e analizzati a fondo).
Quattro cose da lì valgono anche qui, e sono già dentro questo documento:

1. **Il cuore è piccolo.** Il ciclo dell'agente vero sta in poche decine di
   righe: chiedi, esegui, rimetti il risultato nella lista, ripeti. Tutto il
   resto sta intorno e si stacca.
2. **Lo stato è una lista di messaggi.** Nessuno stato nascosto: così una
   sessione si salva, si rigioca per capire cosa è andato storto, e si
   comprime quando è lunga.
3. **Le capacità si dichiarano, non si programmano dentro.** Nome,
   descrizione, schema, permesso: la scheda della skill è esattamente
   questo.
4. **Un permesso negato non è un errore.** Il sistema non si pianta,
   risponde «no» e chi ha chiesto cambia strada.

Quello che di là c'è e qui **non serve**: le squadre di agenti che si
coordinano, la compattazione del contesto a più livelli, il caricamento
dinamico degli strumenti. Sono risposte a conversazioni lunghissime e a
centinaia di strumenti. Clara ne ha tredici e i suoi lavori durano un
minuto. Copiarle adesso sarebbe peso.

## Il magazzino: chi tiene cosa

**La regola, in una riga: se serve interrogarlo va su Supabase; se serve
leggerlo e vale anche senza il software, va in Obsidian.**

| | Supabase | Obsidian |
|---|---|---|
| cosa | i fatti che cambiano e che qualcuno cerca | quello che si scrive e si legge a mano |
| esempi | prospect, interazioni, agenda, task, messaggi di Clara, stato delle skill | regole di casa, stato dei cantieri, playbook, prompt, analisi finite |
| perché | ha le password e i permessi, si apre dal telefono | è versionato con git, sopravvive al software |

**Un originale solo, e la copia va in una direzione sola.** I documenti
nascono e vivono in Obsidian. Quando uno è finito, la Dashboard ne pubblica
una copia di sola lettura su Supabase, così si vede dal telefono e la
vedrà chi entrerà in azienda. **Mai il contrario**: da Supabase non si
torna indietro a scrivere in Obsidian.

Chi scrive dove, per non pestarsi i piedi:

- **Clara scrive solo su Supabase.** Il motore del mattino non tocca mai
  i file di Obsidian: sono sotto git e sotto sincronizzazione di Obsidian,
  e due mani sullo stesso file fanno conflitti.
- **In Obsidian scrive Claude dentro una sessione**, dove Dre vede cosa
  succede.

**Nomi**: c'erano due cose diverse chiamate «Vault». La sezione della
Dashboard diventa **Documenti**. «Il Vault» resta Obsidian, uno solo.

## Il bridge verso Obsidian

Obsidian si apre da un link (`obsidian://open?vault=studiogalilei&file=...`)
e il link può puntare alla nota esatta.

Il bridge **non va nelle Impostazioni**, dove diventerebbe un segnalibro.
Va dove serve: sulla scheda del prospect, «apri il dossier in Obsidian».
Un bottone che porta al punto vale dieci volte un bottone che apre l'app.
Funziona sul Mac, non dal telefono, ed è giusto così: è una comodità da
scrivania.

## I permessi, e la porta lasciata aperta

Dare Clara ad altri è **un'opzione senza data**, non un piano (Dre, 2/9).
Quindi oggi non si costruisce niente per il multi-utente. Si mettono solo
le due cose che dopo costerebbero care:

1. **`owner` sui dati.** L'identità vera di chi possiede la riga, non un
   nome scritto a mano. Oggi è vuoto ovunque e vuol dire «dell'azienda»:
   nessuna schermata cambia. È il gancio a cui domani si attaccano le
   regole di Supabase. **L'abitudine che vale più del campo: ogni tabella
   nuova nasce con `owner`.**
2. **`chi` nella scheda.** Oggi `tutti`. Domani `ceo`, e la capacità
   sparisce dalla lista di chi non deve vederla.

Nota: il campo `owner_name` che esiste già sui prospect è vuoto su tutte le
righe controllate e non si riusa: è un nome scritto a mano, e i permessi
non si appoggiano su un nome.

## Con cosa nasce la sezione

Nove skill esistono già nel codice, fra il motore del mattino
(`scripts/clara.py`) e il pannello di Clara: vanno solo dichiarate.
I quattro agenti nascono **spenti**, con scritto cosa manca per accenderli.
Meglio una sezione vera con quattro caselle spente che una sezione piena a
metà finta.

**Skill** (gratis, girano alle 8)

| capacità | livello | dipende da |
|---|---|---|
| Brief del mattino | prepara | Supabase |
| Saluto in testata | prepara | Supabase |
| Sentinella call fissate | propone | Supabase, Smartlead |
| Guardia caselle Smartlead | guarda | Smartlead |
| Guardia domini Porkbun | guarda | Porkbun |
| Scadenze e fermi | propone | Supabase |
| Prove in scadenza | propone | Supabase |
| Task dettate a parole | esegue | Supabase |
| Call fissate a parole | esegue | Supabase, Google Calendar |

**Agenti** (costano, non partono da soli, nascono spenti)

| capacità | livello | manca |
|---|---|---|
| Analisi Google Ads | prepara | niente, si accende quando Dre vuole |
| Risposte ai lead | prepara | niente, si accende quando Dre vuole |
| Foglio di prep prima delle call | prepara | Google Calendar |
| Bozze di follow-up alla scadenza | prepara | niente, si accende quando Dre vuole |

Le due capacità marcate `esegue` sono le sole che creano qualcosa, una
task o una proposta di evento, e solo su ordine esplicito di Dre: la
proposta resta da confermare e l'ultimo click è suo (regola del 12/8,
mai cambiata).

## La velocità, e perché non dipende dal modello

Dre (2/9) vuole Clara veloce. La cosa da capire prima di ottimizzare
qualunque cosa: **la qualità del modello non è la velocità del prodotto.**

Dove si aspetta davvero, oggi:

| cosa fa Dre | cosa aspetta | c'è un modello? |
|---|---|---|
| apre la Dashboard | il database | no |
| apre una scheda | il database | no |
| legge il brief | niente, è già scritto dalle 8 | no |
| detta una call a Clara | un parser scritto a mano | no |
| chiede un'analisi | il lavoro vero | sì, ed è un minuto |

**In quattro casi su cinque il modello non è nella stanza**, e non per
fortuna: è la conseguenza di due scelte di questo documento, cioè le skill
deterministiche e gli agenti che non partono da soli.

**La regola**: mai un modello sulla strada di qualcosa che Dre sta
aspettando. Una schermata che aspetta un modello per disegnarsi è un errore
di progetto, non un problema di velocità.

Dove invece il modello c'è davvero, tre cose, e nessuna riguarda il modello:

1. **Scrivere mentre pensa.** Una risposta che parte dopo mezzo secondo e
   finisce in otto sembra più veloce di una che appare intera dopo tre.
2. **Rispondere dai dati quando si può.** «Quanti sono in tecnica» è una
   domanda al database. Prima si smista, poi semmai si pensa.
3. **Non ricominciare da capo.** La parte fissa delle istruzioni resta fissa
   e nello stesso ordine, così il fornitore la tiene in cache e non la
   rifà pagare. Rimescolarla a ogni richiesta significa pagare pieno ogni
   volta.

## Perché un cambio di modello non si deve notare

Il confine fa **cambiare** modello. Non basta a cambiarlo **senza
accorgersene**: quella è un'altra cosa e si compra così.

**La qualità sta nel contesto.** La voce di Clara non nasce dal modello,
nasce da CLARA.md, dai template verbatim, dalle correzioni imparate da Dre,
dai playbook. Per la gran parte dei lavori (classificare, riassumere,
estrarre, scrivere partendo da un template) un modello medio con un
contesto eccellente batte un modello fortissimo a digiuno. Quella parte si
cambia e non si vede.

**Il resto si nota, e la risposta è non dare a tutti la stessa testa.** Il
campo `testa` nella scheda dice quanto pesa il ragionamento che serve. La
sentinella e le classificazioni girano sulla leggera, dove i modelli si
somigliano. L'analisi Canossa gira sulla pesante. Si cambia la leggera senza
che si veda niente, e si paga il grosso solo dove conta.

## Il banco di prova

Dieci casi veri presi dal lavoro di questi mesi, con scritto cosa deve
venirne fuori: questo thread va classificato così, su questo prospect il
verdetto è questo, a questa mail si risponde con quel template. Stanno in
`prove/` nel progetto, uno per file.

A cosa serve, in concreto: si cambia modello, si rilanciano, e in due minuti
si sa se si è perso qualcosa. Senza, il cambio di modello lo si fa a occhio.

**Ed è anche il motivo per cui il sistema migliora nel tempo**: ogni volta
che Clara sbaglia, quel caso entra nella cartella e non si ripete più. Il
sistema migliora perché ricorda i suoi errori, non perché qualcuno si
ricorda di migliorarlo.

Nasce piccolo, dieci casi (Dre, 2/9), insieme al primo agente.

## I documenti che Clara produce

Domanda di Dre (2/9): darle la capacità di fare documenti è overbuilding?
Risposta: **in generale sì, su un documento preciso no.**

Un editor generico per documenti è un prodotto, non una funzione, e nasce
per un bisogno che nessuno ha ancora nominato. Ma il motore c'è già: 132
analisi impaginate col logo e i colori del prospect e il grafico delle 12
barre dentro (`render_an.py` più `brand_assets.py`). Il documento numero due
costa una frazione del numero uno.

**Il primo e per ora unico: il dossier di preparazione pre-call** (scelto da
Dre il 2/9). Chi sono, come sono arrivati con la frase verbatim e la data,
cosa dice l'analisi che hanno già in mano, le dieci domande dal generico al
preciso, cosa serve validare per la tecnica con Carlo. Il formato è già
scritto nelle regole di casa e non si reinventa.

È l'agente «Foglio di prep prima delle call» già in elenco: non è una
capacità in più, cambia solo che il risultato è un documento impaginato
invece di testo dentro la scheda. Parte a mano dal bottone «Chiedila a
Clara» che c'è già, e da sola quando arriva Google Calendar.

**I disegni: no.** Immagini generate per un'agenzia di marketing sono la
cosa che sembra utile e non lo è, l'output raramente sopravvive al contatto
con un brand vero, servono un altro fornitore e un'altra voce di spesa, e
non c'è modo di misurarne la qualità. I grafici dentro i documenti, che sono
la parte che paga, ci sono già.

**Il prossimo documento entra solo quando Dre lo avrà fatto a mano più di
due volte in un mese.** Candidati già sul tavolo e volutamente non
costruiti: la proposta dopo la call tecnica (serve la testa di Carlo) e il
report mensile ai clienti (con i clienti di oggi è un documento al mese, il
fastidio non c'è ancora).

## Le regole per aggiungere una capacità

Un filtro solo per decidere se una regola vale la pena di essere scritta
oggi: **cambia una decisione che stiamo prendendo adesso?** Se sì si scrive.
Se no è astrologia: sarà sbagliata quando ci arriveremo, e nel frattempo
qualcuno costruirà roba per rispettarla.

Queste tredici passano il filtro.

1. **Una capacità, una scheda.** Il file dichiara chi è. Aggiungerne una non
   tocca nient'altro, e nessuno deve modificare una lista centrale.

2. **Nasce spenta.** L'interruttore lo accende Dre, mai il codice. Una
   capacità che si accende da sola il giorno che la scrivi è una capacità
   che gira prima che qualcuno l'abbia guardata.

3. **Il livello sta nella scheda.** Non è una manopola in mano a nessuno: è
   una proprietà, decisa quando la capacità si scrive e sensata di suo.

4. **Nessuna capacità ne chiama un'altra.** Se una si accorge che serve
   altro, mette la richiesta in coda. Le capacità non si parlano fra loro,
   parlano tutte con la coda. Questa è la regola che tiene aperta la porta
   alle squadre di agenti **senza costruirle adesso**: il giorno che
   servisse un coordinatore, lui legge la coda e nient'altro cambia.

5. **Chi si accorge non esegue.** La skill che vede il bisogno prepara la
   richiesta e si ferma. Il lavoro lo fa chi ha il potere di farlo, dopo un
   via. Il confine viene dalla struttura, non da un controllo scritto a mano
   che qualcuno prima o poi dimentica.

6. **Un no non è un errore.** Permesso che non basta o collegamento spento:
   si risponde no, si scrive il perché nell'esito, il giro continua. Niente
   si pianta, e chi ha chiesto cambia strada.

7. **Se cade, cade da sola.** Una capacità che si rompe non ferma le altre e
   lascia scritto cosa è successo. Il giro del mattino deve arrivare in
   fondo anche con un pezzo rotto.

8. **Dichiara cosa costa.** Se spende, si vede prima di spendere, non nel
   conto a fine mese.

9. **La testa sta sempre dietro il confine.** Nessuna capacità nomina un
   fornitore di modelli dentro di sé.

10. **Mai un modello sulla strada di un'attesa.** Se qualcosa che Dre sta
    guardando deve aspettare un modello per esistere, il disegno è
    sbagliato: si risponde dai dati e si pensa dopo.

11. **Ogni capacità dichiara che testa le serve.** `leggera`, `normale`,
    `pesante`, o nessuna. Così si cambia modello dove non si vede e si paga
    il grosso solo dove conta.

12. **Ogni agente nuovo porta almeno un caso di prova.** Se non c'è un
    esempio con scritto cosa deve venirne fuori, non c'è modo di sapere se
    il prossimo cambio di modello lo ha peggiorato.

13. **Ogni documento nasce bozza, col nome di Clara sopra.** Un documento
    che sembra finito ma è sbagliato fa più danni di un documento che non
    esiste.

**E la riga di fondo: niente regole su macchine che non abbiamo.** Come si
coordinano gli agenti fra loro, come si comprime una conversazione lunga,
come si caricano gli strumenti al volo: quando servirà lo si scoprirà
guardando il problema vero, non immaginandolo oggi.

## Cosa NON si costruisce adesso

- Clara che si scrive skill da sola
- il bottone «lancia adesso»
- i tetti di spesa (non servono finché nessun agente parte da solo)
- le squadre di agenti che si coordinano fra loro, la compattazione del
  contesto a più livelli, il caricamento dinamico degli strumenti
- la separazione multi-azienda, i cataloghi di skill per persona, il
  pannello dei ruoli, il pacchetto da consegnare fuori

Il bottone «lancia adesso» e i tetti di spesa si aggiungono quando
servono, senza rifare niente: la scheda è già fatta per reggerli. Clara che
si scrive skill da sola è lontana e va guardata bene prima. L'ultimo punto
è un'altra azienda, non una funzione da aggiungere.

## Cosa cambia nel database

Un pezzo solo da incollare, insieme a `schema_v4.sql` che non è ancora
passato:

- tabella `clara_skills` (chiave, acceso, ultimo_giro, ultimo_esito, owner)
- colonna `owner` su `prospects` e su tutte le tabelle nuove

## La regola per non ingolfarsi

**Un collegamento nuovo entra solo quando toglie un fastidio che Dre ha
avuto davvero quella settimana.** Non perché sarebbe bello averlo.
