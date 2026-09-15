# I modelli dei documenti

Ogni `doc-*.json` e' un `Documento` per il motore `src/lib/documento.ts` (blocchi: kicker, h1, h2, p,
numeri, anagrafica, tabella, elenco, due_colonne, riquadro, tappe, spazio, pagina). Le regole del brand
stanno nel motore: Poppins, Blu SG per la struttura, controllo del tono prima di generare.

Per rigenerare i PDF e rimetterli nei Documenti (sezione Modelli):

    npx tsx scripts/modelli.ts docs/modelli /tmp/modelli
    python3 scripts/carica_modelli.py /tmp/modelli

Il modello delle Condizioni economiche non ha JSON: nasce da `src/lib/condizioni.ts` (lo stesso codice
che usa il widget Preventivi) con i dati segnaposto.

## Cosa c'e' dentro

| File | Cosa e' | Copertina |
|---|---|---|
| `doc-presentazione.json` | Il documento istituzionale: chi siamo, le tre aree, il metodo | Istituzionale, rosa dei venti |
| `doc-casi-studio.json` | Tre lavori raccontati per intero, con i numeri delle dashboard | Marketing, telescopio |
| `doc-studio-di-mercato-agriverse.json` | Un esempio vero di studio di mercato, a sette mosse | Marketing, telescopio |
| `doc-guida-pagamenti.json` | Come funzionano i pagamenti, si manda prima della call di avviamento | Nessuna, e' un documento di consegna |
| `doc-report-mensile.json` | Il report che ogni ad specialist manda entro il 5 del mese (SOP M9) | Nessuna, e' un documento di consegna |
| `doc-verbale-call.json` | Il verbale che si manda il giorno dopo la chiamata | Nessuna, e' un documento di consegna |

Vendita o consegna: se il documento esce quando il cliente non ci ha ancora scelto, ha la copertina a
fondo pieno. Se esce dopo, e' carta bianca. Nel dubbio si consegna.

## I due modelli da compilare

`doc-report-mensile.json` e `doc-verbale-call.json` sono modelli veri e propri: le parti fra parentesi
quadre si sostituiscono. Non contengono numeri, nemmeno di esempio: un numero plausibile in un modello
prima o poi finisce dentro un documento vero.

## Cosa controlla lo script

Prima di generare, `scripts/modelli.ts` fa due passaggi.

1. **Il tono** (`controllaTono` in `src/lib/tono.ts`): puntino centrale, trattino lungo, punto
   esclamativo, parole gonfie. Se non passa, il PDF non esce.
2. **L'impaginazione**: le etichette maiuscole sono disegnate lettera per lettera, quindi occupano
   piu' spazio di quanto il motore misuri e se sono lunghe si accavallano fra una colonna e l'altra.
   Lo script segnala di quanti punti sbordano le etichette dei numeri, le intestazioni delle tabelle,
   i titoli delle anagrafiche e dei riquadri. Segnala anche i numeri cosi' lunghi da rimpicciolire
   tutto il blocco, e i titoli che vanno su piu' di due righe o lasciano una parola sola appesa.

Lo script esce con codice 1 se c'e' qualcosa da sistemare, ma i PDF li scrive lo stesso: si guardano
e si decide.

## Come si guardano prima di mandarli fuori

    pdftoppm -png -r 80 /tmp/modelli/sg-presentazione.pdf /tmp/pagine

Le regole scritte non bastano: una pagina puo' essere corretta e brutta lo stesso. Una pagina piena
per meno di due terzi quasi sempre vuol dire che c'e' un `pagina` di troppo nel JSON.
