# ODYN — il cruscotto di Studio Galilei

Il posto dove Dre gestisce tutto l'outbound: chi ha risposto, a che punto è,
cosa fare oggi. Achille lo tiene in ordine e avvisa quando qualcosa non torna.

**Per aprirlo**: doppio click su «Apri ODYN» sul Desktop.
(Oppure: `npm run dev` in questa cartella → http://localhost:5173)

## Com'è organizzata la cartella

| dove | cosa |
|---|---|
| `src/App.tsx` | la struttura: barra in alto con ricerca, le tre viste |
| `src/components/Oggi.tsx` | la vista d'apertura: avvisi + coda di lavoro |
| `src/components/Pipeline.tsx` | le 5 colonne: Prospect → Conoscitiva → Tecnica → Avvio → Cliente |
| `src/components/Scheda.tsx` | la scheda del singolo: cancelli, transcript, mercato |
| `src/components/Lista.tsx` | tutti i prospect, filtrabili (la ricerca in alto arriva qui) |
| `src/lib/types.ts` | le fasi, le etichette, i tipi dei dati |
| `supabase/` | gli schemi del database, in ordine (v1 → v4) |
| `scripts/sync_v2.py` | il segugio: porta dentro le risposte da Smartlead |
| `docs/archivio/` | i documenti di progettazione vecchi (luglio), solo storia |
| `CANTIERE-CRUSCOTTO.md` | il brief del redesign (28/8): decisioni e regole |
| `SETUP.md` | come si collega Supabase, una volta sola |

## Le regole incise nel software

1. **Fuori binario**: se Dre non ha detto se l'ha già sentito a voce,
   nessuna bozza mail parte.
2. **Il pedaggio**: non si avanza di fase senza il transcript della call.
3. **Le correzioni a mano non si toccano**: quello che Dre scrive, il sync
   non lo sovrascrive mai.
4. **Achille non invia niente**: prepara, Dre clicca.
