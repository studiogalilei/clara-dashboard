# I modelli dei documenti

Ogni `doc-*.json` e' un `Documento` per il motore `src/lib/documento.ts` (blocchi: kicker, h1, h2, p,
numeri, anagrafica, tabella, elenco, due_colonne, riquadro, tappe, spazio, pagina). Le regole del brand
stanno nel motore: Poppins, Blu SG per la struttura, controllo del tono prima di generare.

Per rigenerare i PDF e rimetterli nei Documenti (sezione Modelli):

    npx tsx scripts/modelli.ts docs/modelli /tmp/modelli
    python3 scripts/carica_modelli.py /tmp/modelli

Il modello delle Condizioni economiche non ha JSON: nasce da `src/lib/condizioni.ts` (lo stesso codice
che usa il widget Preventivi) con i dati segnaposto.
