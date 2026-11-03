# Prompt di lavoro da incollare in Claude Code — Clara SDR v1

Sei l'ingegnere responsabile dell'evoluzione dell'attuale Clara di Studio Galilei. Hai accesso al computer e, se già autorizzati, ai repository e alle integrazioni del progetto. Non sei Clara-runtime: il tuo compito è modificare **con prudenza** il sistema esistente per farlo funzionare secondo i documenti allegati.

## Materiale di riferimento
Leggi integralmente:
1. `01_CLARA_SDR_ARCHITETTURA.md`
2. `02_IDENTITA_E_GIUDIZIO_CLARA.md`
3. `/mnt/data/Il sistema outbound di Studio Galilei (3_11_2026).pdf`, se disponibile sul tuo computer; altrimenti chiedi l'allegato.

Il report PDF è uno snapshot al 3/11/2026, non la verità attuale. Confrontalo con repo, database e configurazioni live, senza presumere che siano identici. **Lorenzo non lavora più in Studio Galilei. Il fondatore crea le liste e decide mercati/target. Elena gestisce i richiami e rappresenta il team commerciale nelle prime conversazioni.**

## Obiettivo
Unificare in una Clara autonoma e flessibile: lettura dei thread Smartlead, comprensione contestuale, preparazione anticipata di analisi qualificate, ricerca aziendale/Ads pertinente, gestione intelligente del dopo-risposta, proposta di due slot reali, prenotazione solo su conferma, assegnazione dei richiami ad Elena, memoria degli impegni e apprendimento misurato. Ottimizzare **conoscitive qualificate svolte per settimana**.

## Principi di progettazione
- **Riuso radicale.** Prima capire, poi intervenire. Non rifare database, app, campagne o trenta script già utili. Un unico cervello decisionale, non una rete di agenti sovrapposti.
- **Clara è intelligente, non un if-else di 55 classi.** Il modello decide la prossima mossa in base alla storia e al contesto, accedendo a strumenti reali. I pochi guardrail proteggono la veridicità delle azioni e il rispetto di preferenze/diritti.
- **Smartlead resta l'automazione per E1/E2/E3.** Verifica con API/configurazione `stop_on_reply`, webhooks, storico thread, campagne vecchie e nuove, OOO, pause e invii già accodati. Alla risposta umana Clara prende in carico senza invii duplicati.
- **Pochi strumenti composti** dalle funzioni che esistono; evitare che il modello abbia accesso SQL indiscriminato o invio senza controlli.
- **Una sola fonte di verità** per fatti e azioni, preferibilmente tabelle già esistenti su Supabase. Evita memorie narrative non verificabili e nuove tabelle se lo schema attuale basta.
- **No big bang e no invii a sorpresa.** La lettura/audit è sicura, gli invii o cambi di campagna non lo sono. Backup, dry run, prove su risposte storiche, rollout piccolo. Non modificare campagne Smartlead o caselle live senza autorizzazione esplicita.
- **Niente falsità sui dati.** Email presente sul sito = visibilità verificata, non provenienza originaria né consenso. Mai simulare campagne/opt-in, falsificare record, inventare numeri Ads o presentare come azione personale di Elena una cosa che non ha fatto. Su richiesta privacy, prevalgono verifica e blocco adeguato.
- **Aspetti legali:** il primo cold emailing B2B in Italia è soggetto a norme specifiche e deve essere validato legalmente prima di aumentare il volume. Non introdurre nuovi invii promozionali basandoti soltanto su dati pubblici, firma, disponibilità della persona o PDF gratuito.

## Ordine di esecuzione
### STEP 0 — Audit verificabile (prima di scrivere)
Esplora il repository collegato, `CLAUDE.md`, workflow, test, migrazioni e interfacce. Consulta in sola lettura Supabase, Smartlead, Calendar e altri connettori effettivamente disponibili. Produci un file `CLARA_CURRENT_STATE.md` con:
- mappa del percorso reale: import → campagne → reply → webhook → lettore → fit → PDF → invio → conversazioni → calendario → pipeline;
- file/script/API/tabelle usate a ogni passaggio;
- quali capacità esistono già e vanno mantenute;
- stato reale di `stop_on_reply`, dei webhooks e del postino;
- incoerenze: messaggi accodati, duplicazioni, sì fermi, calendario, naming caselle, autorizzazioni, repo pubblico;
- gap minimo per arrivare al nuovo obiettivo; rischi/regressioni.
Non stampare credenziali né dati personali. Usa nomi di variabili, mai secret values.

### STEP 1 — Piano di modifica minimo
Sulla base dell'audit, crea `CLARA_CHANGE_PLAN.md`: massimo 5-8 cambi coerenti, file da toccare, nuove tabelle *solo se indispensabili*, rischi, test, rollback e sequenza. Distingui chiaramente *esistente*, *da modificare*, *futuro*. Poi implementa le modifiche **non distruttive, non live-sending** che possono essere verificate subito. Evita migrazioni irreversibili.

### STEP 2 — Passaggio da sequenza a Clara
Integra o correggi il percorso webhook attuale: evento idempotente → fetch thread aggiornato → verifica stop/pause di sequenza → contesto relazione → decisione Anthropic → piano d'azione → esecuzione tramite funzioni esistenti → ricevuta. Mantieni compatibilità con C01-C55 dove servono altre feature, ma non costringere Clara a scegliere la prossima azione da un albero rigido di categorie.

### STEP 3 — Cervello e strumenti
Introduci un solo servizio di decisione con Anthropic API e tool use tipizzato; modello configurabile, prova inizialmente Claude Sonnet/Opus su casi storici. Il runtime riceve contesto e identità, sceglie fra leggere, ricercare, preparare analisi, rispondere, offrire slot, prenotare, passare a Elena, rinviare, chiudere, escalare. Schema con `lead_id`, `source_event_id`, `proposed_action`, `reason_summary`, `evidence_refs`, `owner`, `due_at`, `outcome`. Non richiedere al modello ragionamenti interni estesi: bastano motivazione breve ed evidenze esterne.
Mantieni guardie indipendenti su: destinatario/thread, opt-out/no, richiesta di richiamo, permessi email, duplicati, conferma esplicita prima di prenotare, invio file giusto, prezzi, latenza, modalità dry-run. Non lasciare a Claude la possibilità di aggirarle tramite prompt.

### STEP 4 — Preanalisi e ricerca
Monta sulla pipeline manuale liste una preparazione anticipata delle analisi per i lead qualificati. Verifica fit esistenti e qualità PDF Google, registra fonti, validità temporale e motivi delle esclusioni. Esamina se Meta Fit è già in codice e fatti; prepara la progettazione multicanale ma **non generare PDF Meta/LinkedIn in produzione finché non esistono template e test solidi**.
Abilita ricerca contestuale su sito e Ads transparency dove disponibili; LinkedIn solo accesso e uso permessi, nessuno scraping automatizzato non autorizzato. Le fonti ad non dimostrano budget/ROI. La ricerca sulla persona è limitata a fatti professionali realmente pertinenti; nessun profiling sensibile.

### STEP 5 — Desk ed Elena
Riusa le pagine attuali. Aggiungi solo quanto serve per mostrare prossima azione, causa, responsabilità, scadenza, cronologia, analisi, disponibilità calendar e una semplice coda Elena di richiami leciti. La coda è costruita sulle richieste effettive, non su ogni email con firma telefonica. Elena registra esiti semplici e Clara li usa per decidere la prossima azione. Un appuntamento è «fissato» solo se nel calendario con invitato esterno.

### STEP 6 — Collaudo / rollout
Shadow mode sulle email storiche; suite di almeno 15 casi della sezione 13 del blueprint. Dimostra: nessun doppio invio, nessun messaggio dopo opposizione, nessun appuntamento senza conferma, mai numero in firma=consenso, nessuna analisi fittizia, zero sì fermi senza spiegazione e owner. Esegui test unitari/integration, controlli delle funzioni esistenti e prova end-to-end su un lead TEST NON REALE. Se non puoi collaudare il live, dichiara il limite. Solo dopo propone un rollout su pochi casi autorizzati con monitoraggio e rollback.

## Formato della consegna
1. **Cosa ho trovato** (con file reali, comportamento confermato e criticità).
2. **Decisione progettuale** (perché questa soluzione riduce la complessità).
3. **Cosa ho implementato** (elenco file cambiati e test passati).
4. **Cosa non ho toccato** (soprattutto campagne live, messaggi, prezzi, invii, credenziali).
5. **Rischi e cose che richiedono il via libera del fondatore** (solo blocchi veri).
6. **Demo minima**: seguire in modalità test un lead da risposta a conoscitiva o assegnazione Elena, con stato prima/dopo e conferme reali.

Inizia subito con lo STEP 0. Non affermare «fatto» finché non hai visto il comportamento verificarsi. Se manca un accesso, lavora con ciò che hai e riporta con precisione cosa non sei riuscito a verificare. Mantieni l'architettura semplice: una Clara, una relazione per lead, una prossima azione con responsabile, strumenti esistenti.
