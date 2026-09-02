---
tipo: passaggio consegne
creato: 2026-09-02
per: la prossima sessione di Claude Code aperta su ~/Documents/odyn-crm
---

# Passaggio consegne — Cruscotto ODYN (la Dashboard)

> **Leggi questo per primo, poi CLAUDE.md e STATO.md nel vault.**
> Scritto il 2/9/2026 perché la sessione precedente si è rotta (connessione caduta
> + limite di utilizzo). Nessun lavoro è andato perso: è tutto su disco.

## Dove si lavora

- **Progetto**: `~/Documents/odyn-crm` (React + Vite + Tailwind v4 + Supabase)
- **Vault** (manuale, stato, playbook): `~/Documents/Obsidian/studiogalilei`
- **Demo**: `http://localhost:5173/?demo` (dati finti, DB vero non ancora attivo)
- **Apri VS Code sulla cartella odyn-crm** (File → Open Folder), poi New session.
  Una sessione, un posto: mai la stessa sessione su due finestre.

## Cos'è la Dashboard

Il CRM di Studio Galilei. I prospect scorrono:
**Prospect → Call Conoscitiva → Call Tecnica → Call di Avvio → Cliente** (o Perso).

Regola fondativa, il **pedaggio**: per avanzare di fase serve il riassunto della
call. Niente riassunto, niente avanzamento. Vale sia trascinando le carte nella
bacheca «Tutti», sia dal bottone «Porta avanti» nella scheda.

**Clara** è la segretaria AI dentro la Dashboard (logo animato che fluttua,
pannello di chat ridimensionabile). Regola non negoziabile: **Clara propone,
Dre conferma. Mai un invio, mai un evento creato in autonomia.**

## Stato al 2 settembre

**Fatto e verificato nel browser:**
- Home riordinata: card delle fasi coi numeri in alto, poi «Da fare oggi» col
  ticker + Avvisi + In settimana, poi la barra «In arrivo», in fondo gli avvisi
- Sezione «Tutti»: bacheca statica (tutte le colonne nella larghezza, niente
  scroll laterale) + vista elenco; le carte si trascinano col pedaggio
- Vault a griglia con anteprime dei documenti, stile Google Documenti
- Foto profilo: le due cifre finali dell'SG-ID sul colore della fase
  (ambra = prospect, blu che si scurisce nelle call, verde = cliente, grigio = perso)

**Da fare, in ordine:**
1. I 31 problemi dello stress test (sotto)
2. Rifare due pezzi di stress test caduti: browser dal vivo e schema del DB
3. Lucidatura UI (Dre porta immagini da Pinterest per dare personalità)
4. Sezione «Impostazioni» al posto di «Demo» in basso: impostazioni vere,
   che cambiano davvero qualcosa

## I 31 problemi trovati dallo stress test

Sei agenti in parallelo, ognuno con un verificatore avversario che ha provato a
smontare le segnalazioni. Nessuna delle giudicate è stata respinta.
**Il report completo con file e righe è nel risultato del workflow**:
`/private/tmp/claude-501/-Users-dramane-Documents-Obsidian-studiogalilei/3be24041-2cbd-410a-920e-e6114c9af600/tasks/wl0tcc1rd.output`
(campo `result.confermati`, 31 voci con `dettaglio`, `file`, `riproduzione`).

### I 6 gravi

1. **Trascinare una carta indietro su «Prospect»** scrive una fase inesistente:
   in demo la carta sparisce dalla bacheca, sul DB vero l'update viene rifiutato
   in silenzio. `Lista.tsx:22, 149, 352`
2. **Un prospect in pipeline non può mai diventare «Perso»**: nessun percorso
   esiste. Le trattative morte restano vive, gonfiano i numeri e generano avvisi.
   `Lista.tsx:27, types.ts:73-77, Scheda.tsx:734`
3. **La ricerca per SG-ID funziona solo in demo**: la query al server non guarda
   sg_id, il filtro client lavora solo su ciò che il server ha già dato.
   `Lista.tsx:72, 80-84`
4. **Clara scrive col trattino lungo** (vietato da Dre): `clara.py` lo pulisce,
   la UI no. Finisce nei titoli delle call e su Google Calendar.
   `ClaraVolante.tsx:285, 360, 374, 392`
5. **La chat di Clara carica gli 80 messaggi più VECCHI** (order ascending +
   limit): oltre le 80 righe i nuovi non compaiono mai, il badge resta a zero e
   il gancio del «sì» non trova più le domande. Nessun polling.
   `ClaraVolante.tsx:190-196`
6. **Il brief del mattino mostra le ore in UTC**: una call delle 15:00 viene
   scritta «13:00». `clara.py:243, 279`

### I 14 medi

- Il pedaggio si aggira dalle chip di stage in Scheda: due click e un prospect
  diventa cliente senza nessuna call `Scheda.tsx:765-775`
- Se il salvataggio del riassunto fallisce, il testo di Dre sparisce senza avviso
  (il modal si chiude prima della scrittura) `Lista.tsx:425-426, 164, 178, 436`
- Il numero «Prospect» della home non torna con la colonna della bacheca sul DB
  vero (filtro VIVI applicato in tre file e assente in Lista) `Pipeline.tsx:19, Lista.tsx:67`
- Conteggi calcolati su query troncate a 300/1000: sui 13k prospect mentiranno
  `Pipeline.tsx:40,45, Radar.tsx:85, Analytics.tsx:33`
- Lo stub demo non mette la data agli insert: la chat di Clara si rimescola
  `demo.ts:269-272`
- Lo stub ordina i numeri come stringhe: l'ordine delle task salta dopo un reload
  `demo.ts:276-278`
- Un «ok» qualsiasi risveglia una vecchia domanda della sentinella e prepara una
  call fuori contesto `ClaraVolante.tsx:261-263`
- Lo stato Pendente di Clara non si può annullare a parole e sequestra i messaggi
  successivi `ClaraVolante.tsx:292-353`
- Il match fuzzy dei prospect aggancia parole comuni («della», «studio») e può
  scegliere la persona sbagliata in silenzio `ClaraVolante.tsx:143-162`
- La sentinella call-fissate è rotta: `+00:00` non codificato nell'URL, e senza
  `last_reply_at` non chiede mai `clara.py:200-218`
- Cliente «vecchio stile» col badge PROSPECT ambra accanto alla faccia verde
  `Scheda.tsx:449-451`
- Plugin: «da collegare» dichiarato grigio ma disegnato rosso allarme `Plugin.tsx:23`
- Trattino lungo sparso nel copy della UI `Scheda.tsx:283, 432, 438, 681, 762`
- Con più di 80 interazioni la Scheda perde i transcript recenti e «Porta avanti»
  resta bloccato `Scheda.tsx:88-90, 242-245`

### Gli 11 piccoli

Retrocessione di un cliente con un drag senza conferma; clienti legacy segnati
«fermi» in rosso nell'elenco; date «oggi» calcolate in UTC (fra mezzanotte e le
2 il giorno è sbagliato); riordino task con una richiesta per riga senza gestione
errori; mappe colori morte in `types.ts` che contraddicono il linguaggio delle
fasi; avviso del radar che mostra la chiave grezza («in tecnica»); chat di Clara
vuota senza stato vuoto; didascalie statiche vietate in Calendario e Plugin;
parser date con casi rotti («il 31/8» → 2027, «alle 6 di mattina» → 18:00,
`task:` mai riconosciuto, mail col punto finale).

## La decisione che aspetta Dre

I due problemi più gravi dicono la stessa cosa: **il movimento all'indietro non
è mai stato progettato.** Prima di scrivere codice serve la sua scelta:

> Nella pipeline si può tornare indietro?

Proposta sul tavolo (da confermare): **sì, ma con una conferma esplicita**, e
**«Perso» raggiungibile da ogni fase**. Senza la sua risposta i fix 1 e 2 non
si fanno.

## Le regole di casa (non romperle)

- **Mai inviare niente io**: ogni invio è un click di Dre
- **Mai creare account, inserire carte o API key**. I secret stanno solo in
  `Falcon Studio/.falcon-bridge/secrets.env` e `~/.hermes/config.yaml`
- **I meeting li mette Dre.** Clara può creare un evento solo su suo comando
  esplicito, e comunque via il link di Google Calendar che clicca lui
- **Vietato il trattino lungo** nell'output di Clara: si usa «:» o «;»
- **Niente didascalie** nella UI: il testo sopravvive solo se porta un dato o
  un feedback
- **Il blocco Parked in fondo a ogni messaggio**, sempre
- **Una cosa alla volta**: una domanda per volta, una bozza per volta

## Le cose ferme che aspettano Dre

1. **Follow-up 1 settembre**: 30 bozze pronte e controllate, manca il suo click
   su Smartlead (`ODYN Cockpit/Follow-up 1 settembre 2026.md`)
2. **schema_v4.sql** da incollare su Supabase (senza, il DB vero non parte)
3. **Click su Google Calendar** per l'autorizzazione
4. **Ok ai commit git**: odyn-crm non ha NESSUN commit, il vault ne ha decine
   non salvati. È il rischio più grosso: un guasto al Mac e sparisce tutto
5. **Prova generale** sul database vero
6. **Casa di Clara**: repo privato su GitHub come backup cloud del vault e della
   memoria (proposto il 2/9, aspetta il suo vai)

## Come parlare a Dre

Italiano informale e diretto, zero fuffa. Prima la posizione netta in due righe,
poi i dettagli. Poca roba tecnica a schermo: si dice cosa cambia per lui, non
come lo fai. Quando un errore dipende da lui, glielo si dice (regola sua, 2/9).
La versione completa sta in `ODYN Cockpit/prompts/MASTER-PROMPT.md`.
