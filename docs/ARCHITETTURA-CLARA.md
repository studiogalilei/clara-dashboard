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
  "costa": false,
  "chi": "tutti"
}
```

- `famiglia`: `skill` o `agente`
- `quando`: `ogni mattina`, `al bisogno`, `su tuo ordine`
- `livello`: `guarda`, `prepara`, `propone`, `esegue` (la scala del 31/8)
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

## Cosa NON si costruisce adesso

- Clara che si scrive skill da sola
- il bottone «lancia adesso»
- i tetti di spesa (non servono finché nessun agente parte da solo)
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
