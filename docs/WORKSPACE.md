# SG Workspace, documentazione tecnica

Scritta il 17 settembre 2026 leggendo il codice e il database vivo, non a memoria.
Dove una cosa non è stata verificata c'è scritto. Aggiornare questo file quando
cambia l'architettura: le rifiniture di una schermata non c'entrano, un nuovo pezzo
di infrastruttura sì.

## 1. Cos'è

SG Workspace è il posto di lavoro di Studio Galilei: le aziende dalla prima risposta
alla firma, i clienti con i progetti, il calendario, i preventivi e i documenti, la
squadra. Dentro c'è Clara, l'assistente: legge posta, calendario e appunti delle call,
tiene aggiornate le schede, prepara bozze e promemoria. Regola fondativa, incisa in
tutto il sistema: **Clara propone, una persona decide**. Nessun invio e nessuna
modifica alla pipeline parte senza un sì dato dalla Posta di Clara.

- App pubblica: https://studiogalilei.github.io/clara/ (solo i file compilati, repo
  pubblico `studiogalilei/clara`)
- Codice: repo privato `studiogalilei/clara-dashboard`, cartella locale
  `~/Documents/odyn-crm` (il nome della cartella è storico)
- Database e cloud: progetto Supabase `tqssfcuzezlczfceqsmk`
- Lavori in cloud: GitHub Actions sul repo del codice
- Progetto Google Cloud: `sg-workspace-508320` (OAuth e Pub/Sub)

## 2. L'architettura in una pagina

```
 browser (React, PWA)
   |  supabase-js: PostgREST + Auth + Storage + Realtime + functions.invoke
   v
 Supabase ─ Postgres (34 tabelle, RLS ovunque)
         ─ Auth (Google OAuth, dominio studiogalilei.com; password di riserva)
         ─ Storage: bucket privato `vault`
         ─ Realtime: publication su 9 tabelle
         ─ Edge Functions (Deno): clara-risponde, documento, piano, piva,
                                  smartlead-webhook, squadra, sveglia
         ─ pg_cron + pg_net: rete di sicurezza oraria, trigger che sveglia Clara
   ^
   |  REST con service key (scripts/stanza.py)
 il direttore (GitHub Actions, Python 3.12, `scripts/direttore.py`)
   fa partire le 25 operazioni alla loro cadenza; parte
   - a orologio ogni 20 minuti (cron del workflow)
   - subito quando bussa Smartlead (webhook), Gmail (Pub/Sub) o pg_cron (ogni ora)
   parla con: Gmail, Google Calendar, Google Drive, Smartlead, Stripe, OpenAI,
   SearchAPI, Web Push
```

Tre principi che spiegano quasi tutto il codice:

1. **Una porta sola verso i dati.** Il browser legge e scrive con le regole di
   accesso del database (RLS). Gli script in cloud usano la service key ma scrivono
   solo attraverso `scripts/stanza.py`. Non esistono API nostre in mezzo.
2. **Clara propone.** Tutto quello che Clara vuole fare diventa una riga in
   `proposte` (la Posta di Clara). La persona dice sì o no nell'app; solo il sì
   esegue l'azione.
3. **Il database è la verità di oggi.** Gli stati non sono etichette da aggiornare
   a mano: si calcolano da date e righe (`src/lib/stato.ts`, `src/lib/regole.ts`).

## 3. Il frontend

### Stack

| Cosa | Versione | Note |
|---|---|---|
| React | 19 | funzioni e hook, niente redux |
| Vite | 8 | `base` da `BASE_PATH` (in produzione `/clara/`) |
| Tailwind | 4 | classi utility, token colore in `src/index.css` |
| TypeScript | 6 | `npx tsc --noEmit -p tsconfig.app.json` |
| supabase-js | 2 | un solo client in `src/lib/supabase.ts` |
| pdf-lib, pdfjs-dist | | PDF generati (documenti) e PDF compilati sopra l'originale |
| vite-plugin-pwa | 1 | manifest «SG Workspace», service worker `autoUpdate` |
| vitest, oxlint | | 35 test, lint |

Comandi: `npm run dev` (http://localhost:5173), `npm run controlla` (tsc + oxlint +
vitest), `npm run build`, `npm run controlla-database` (confronta le colonne usate
dal codice con quelle vere).

### Avvio e accesso

- `index.html` mostra il logo di Clara che ruota finché React non disegna. Ha le
  etichette Open Graph (`public/anteprima.png`) per l'anteprima del link.
- `src/lib/supabase.ts`: se la URL contiene `demo` l'app usa `src/lib/demo.ts`, un
  finto client con dati inventati e senza login (http://localhost:5173/?demo).
- Login (`src/components/Login.tsx`): «Entra con Google» con `hd=studiogalilei.com`
  e i permessi in `src/lib/google.ts` (Drive, Calendar, Gmail lettura e invio, Chat).
  Resta la password come riserva. Al login il refresh token di Google finisce in
  `google_token` (una riga per persona): è quello che gli script usano per agire a
  nome di quella persona. Il permesso in più `cloud-platform` lo dà solo chi guida lo
  Studio, da Impostazioni, e serve all'orecchio di Gmail (vedi 7).
- Al primo accesso parte il giro guidato (`Giro.tsx`): Clara si presenta e dice cosa
  sa fare per il ruolo di chi guarda. La preferenza `giro-fatto` lo spegne.

### Sezioni, widget, ruoli

Ogni sezione è un widget dichiarato in `src/lib/widget.ts` (chiave, nome, zona,
ruoli, base). Aggiungere una riga lì lo fa comparire nel menu e nelle Impostazioni.

| Chiave | Nome nel menu | Chi ce l'ha |
|---|---|---|
| pipeline | Oggi | tutti (base) |
| prospect | Pipeline | tutti (base) |
| progetti | Clienti | a richiesta |
| calendario | Calendario | tutti (base) |
| preventivi | Preventivi | ceo |
| vault | Documenti | tutti (base) |
| clara | Posta di Clara | tutti (base) |
| chat | Condividi | tutti (base) |
| feedback | Cosa cambieresti | tutti (base) |
| analytics | Numeri | a richiesta |
| plugin, impostazioni | sala di controllo, Impostazioni | dentro Impostazioni |

I ruoli nell'app sono due (`ceo`, `coordinamento`); in `profili.ruolo` ci sono anche
`manager`, `specialist`, `frontend`, che l'app tratta come coordinamento e usa per le
schede e il giro. Un widget «a richiesta» si chiede da Impostazioni e lo concede un
ceo (`widget_accessi`, `src/lib/accessi.ts`). Un ceo può «vedere come» un'altra
persona: la riga in `vista_come` fa sì che tutte le regole del database valgano per
quella persona (`uid_eff()`).

### Preferenze

`src/lib/preferenze.ts`: chiavi fisse (`CHIAVI`). Quelle di sessione (vista task,
vista pipeline, filtri) stanno in sessionStorage e tornano al difetto chiudendo
l'app; le altre stanno in localStorage e nella tabella `preferenze`, quindi seguono la
persona su ogni dispositivo. «Come si apre» in Impostazioni scrive i difetti
(`task-apertura`, `pipeline-apertura`).

### Tempo reale nel browser

`src/lib/vivo.ts`, hook `useVivo(tabelle, cb)`: un canale Realtime per tabella,
condiviso fra le schermate; quando una riga cambia, la schermata rilegge (con mezzo
secondo di attesa per non rileggere venti volte). Lo usano App (i numeri sul menu),
Oggi, Clara, Condividi. In demo non esiste.

### Documenti e PDF

`src/lib/tono.ts` definisce il `Documento` a blocchi (copertina, h1, p, elenco,
tabella, numeri, tappe...). `src/lib/documento.ts` lo stampa in PDF con pdf-lib e
Poppins, con le regole di tono dello Studio (`ripulisciTono`, `controllaTono`: niente
trattino lungo, niente puntino centrale, parole vietate). Lo stesso motore fa i
preventivi, i documenti dell'Editor, le schede della squadra e i modelli. I modelli
dell'Editor sono in `src/modelli/*.json`. `CompilaPdf.tsx` invece scrive sopra un PDF
esistente (il contratto di prova) senza rifarlo.

### Componenti principali

| File | Cosa fa |
|---|---|
| `App.tsx` | ossatura: menu, testata, sezioni, riposo, giro, novità, battito realtime |
| `Oggi.tsx`, `Radar.tsx`, `Aggiornato.tsx` | la giornata: chi aspetta te, task, prossima call, freschezza dei dati |
| `Aziende.tsx`, `Lista.tsx`, `TuttiFoglio.tsx` | pipeline a bacheca (trascinamento con pedaggio) e a foglio |
| `Scheda.tsx`, `Storia.tsx` | la scheda dell'azienda: fasi, call, appunti, documenti, task, piano |
| `Clienti.tsx`, `Progetti.tsx`, `NuovoProgetto.tsx` | i clienti e il foglio dei progetti |
| `Calendario.tsx` | specchio di Google Calendar più scadenze e prove |
| `Preventivi.tsx`, `Prezzo.tsx`, `Editor.tsx` | preventivi, calcolo del prezzo, editor a blocchi con «Scrivilo con me» |
| `Vault.tsx`, `CompilaPdf.tsx`, `Firma.tsx` | cassaforte, compila sopra il PDF, firma e timbro |
| `Chat.tsx` | Condividi: documenti passati fra persone, legati al cliente |
| `ClaraVolante.tsx`, `ClaraPensa.tsx`, `ClaraLogo.tsx` | la pallina, la chat, la Posta, i comandi a parole |
| `Piano.tsx` | dagli appunti alle task giorno per giorno |
| `Feedback.tsx`, `Novita.tsx` | feedback della squadra, cantiere del ceo, striscia delle novità con le stelle |
| `Impostazioni.tsx`, `Squadra.tsx`, `Plugin.tsx` | profilo, widget, collegamenti, squadra, listino, sala di controllo, azioni di Clara |
| `Analytics.tsx` | Numeri: mese contro mese, settimane, settori |
| `Login.tsx`, `Rete.tsx`, `Giro.tsx`, `CercaAzienda.tsx`, `NuovaAzienda.tsx`, `ui.tsx` | porta, rete di sicurezza sugli errori, giro guidato, ricerca, inserimento a mano, pezzi comuni |

## 4. Il database

### Le tabelle (34, tutte con RLS)

**Le aziende e la loro storia**

| Tabella | Cosa | Righe oggi |
|---|---|---|
| `prospects` | l'anagrafe: un'azienda per riga, da Smartlead o a mano. `stage` (outbound: nuovo, risposto, analisi_inviata, in_follow_up, call_fissata, cliente, perso, rinviato), `pipeline_stage` (vendita: conoscitiva, tecnica, avvio, prova, cliente, perso), `classificazione`, `sector` (dal Foglio Settori), `chi_segue`, `canone`, `contratto`, `prova_inizio/fine`, `sg_id` (numero progressivo, trigger `trg_sg_id` alla prima risposta), `enriched` (json: google fit, lettura) | 13.193 |
| `interactions` | la storia: `kind` fra email_in, email_out, analisi, call, transcript, nota, postit; `ref` per non duplicare (gmail:id, gemini:id, gdoc:id) | 413 |
| `agenda` | le call e gli eventi (da Google Calendar): `tipo` conoscitiva, tecnica, avvio, altro; `preparazione` scritta da Clara | 101 |
| `suppressions`, `lists`, `list_members`, `sync_runs` | il registro di chi non si contatta, le liste importate, le corse del sync Smartlead | |

**Il lavoro**

| Tabella | Cosa |
|---|---|
| `task` | le task: `owner`, `da`, `stato` (proposta quando la manda un altro, poi accettata), `scadenza`, `prospect_id` |
| `progetti`, `tappe` | i progetti per cliente (natura, stato, chi segue, accessi, «cosa abbiamo imparato»), le tappe |
| `preventivi`, `listino`, `incassi` | preventivi con voci e stato (inviato, accettato, rifiutato, pagato), listino prezzi, incassi da Stripe |
| `documenti` | i documenti dell'Editor (json a blocchi), con il PDF archiviato in `file` |
| `vault_file` | l'indice dei file nel bucket `vault`: sezione (brand, modelli, clienti), prospect, nota |
| `chat` | Condividi: messaggi e file fra persone |
| `coda_fatte` | le voci della coda di Oggi spuntate, per persona e giorno |

**Clara**

| Tabella | Cosa |
|---|---|
| `proposte` | la Posta di Clara: `tipo` (risposta, classifica, scarta, data, avanza, richiesta, nuovo, umano), `azione` (json con cosa eseguire al sì), `stato`, `owner`, `ref` (indice unico parziale: la stessa domanda non nasce due volte) |
| `clara_messaggi` | la chat con Clara: `tipo` (dre, clara, brief, promemoria, domanda, controllo, saluto), `diario` |
| `diario` | le risposte alle domande del diario |
| `azioni` | le otto azioni di Clara: giorni e accesa/spenta, si cambiano dalla sala di controllo |
| `istruzioni` | testi che vincono su tutto nei prompt (per chiave), più l'id del calendario SG Scadenze |
| `operazioni`, `corse` | le operazioni del direttore e le loro corse |
| `clara_skills` | vuota, resto dell'architettura a skill del 2/9 |

**Le persone**

| Tabella | Cosa |
|---|---|
| `profili` | id (= auth.users), nome, ruolo, firma; creato dal trigger `crea_profilo` |
| `google_token` | refresh token e scope di Google per persona |
| `pod` | manager e membri del pod |
| `widget_accessi`, `widget_richieste` | i widget a richiesta e le richieste di nuovi widget |
| `vista_come` | il ceo che sta guardando come un'altra persona |
| `preferenze` | le preferenze permanenti, per persona |
| `feedback` | feedback della squadra: genere, stato, risposta, e per le novità `voto` e `novita` |
| `candidature` | il modulo pubblico di candidatura (l'unica tabella scrivibile da anonimo, solo insert) |

C'è anche la vista `v_oggi` (la coda di oggi in SQL, precedente alla coda calcolata in `regole.ts`).

### La sicurezza

- `uid_eff()`: chi sei davvero, o la persona che stai «vedendo come». Tutte le
  regole passano da qui.
- `sono_ceo()`: il ruolo in `profili` è ceo.
- `vedo_prospect(fuori, stage, chi_segue)`: il perimetro sulle aziende. Un ceo vede
  tutto; gli altri vedono i clienti (dalla fase tecnica in poi) e le aziende che
  seguono (`chi_segue` contiene il loro nome). `ho_una_call(id)` aggiunge le aziende
  con cui hanno una call negli ultimi 30 giorni.
- `nel_mio_pod(persona)`: un manager vede le task e le cose del suo pod.
- Le regole per tabella sono elencate in `supabase/schema_completo.sql` e nei
  `schema_v*.sql`. In sintesi: ognuno le proprie (task, proposte, preferenze,
  feedback, clara_messaggi); i ceo tutto; preventivi, incassi, listino, operazioni,
  istruzioni, liste solo i ceo; le persone si vedono a vicenda.
- Funzioni di servizio chiamate dall'app (`rpc`): `chi_sono` (uid, nome, ruolo, pod,
  widget concessi, vista), `ho_il_token_google`, `ultimo_giro` (l'ultima corsa
  riuscita, per la riga verde in Oggi).
- Trigger: `trg_prospects_updated` (updated_at), `trg_sg_id` (assegna il numero SG),
  `clara_messaggi_sveglia` (a ogni messaggio di una persona chiama la funzione
  `clara-risponde` con pg_net), `progetti_chi_segue_sync`.

### Storage

Un bucket privato, `vault`. Cartelle: `brand/` (98 file, la Clara Capsule),
`modelli/` (i PDF modello, fra cui il contratto di prova), `clienti/<prospect_id>/`
(i file di ogni cliente, compresi i PDF scaricati dall'Editor e i PDF compilati),
`azienda/`. L'indice è `vault_file`; le regole di lettura seguono quelle delle aziende.

### Realtime

Publication `supabase_realtime` su: proposte, task, agenda, chat, clara_messaggi,
prospects, documenti, feedback, coda_fatte (schema_v44).

### Le migrazioni

`supabase/schema_v2.sql` ... `schema_v46.sql`, una per cambiamento, con il perché in
testa. `schema_completo.sql` è il cumulato (rigenerato con `scripts/schema-completo.sh`).
Si applicano dall'SQL editor di Supabase o con la Management API. Non c'è `supabase
db push`: il repo non ha `supabase/config.toml`.

### Estensioni e cron

`pg_cron`, `pg_net`, `pgcrypto`, `supabase_vault`, `uuid-ossp`. Un solo lavoro cron:
`direttore`, ogni ora al minuto 37, chiama `chiama_direttore()` che fa partire il
workflow su GitHub con un token conservato nel Vault di Supabase (`github_direttore`).
È la rete di sicurezza se GitHub non fa partire il cron suo.

## 5. Le Edge Functions

| Funzione | Cosa fa | Chi può chiamarla |
|---|---|---|
| `clara-risponde` | risponde in chat: legge la conversazione, la persona, le istruzioni, chiama OpenAI, scrive in `clara_messaggi`; se la risposta contiene una riga `PROPOSTA` crea una proposta; salva le risposte al diario | il trigger del database, con l'header segreto `x-clara-segreto` (deploy `--no-verify-jwt`) |
| `documento` | riscrive un documento dell'Editor con il contesto dell'azienda (scheda, call, mail, progetti, preventivi) | l'utente loggato (JWT) |
| `piano` | dagli appunti di una call (o idee sparse) a 3-8 passi datati | l'utente loggato |
| `piva` | ragione sociale e indirizzo da partita IVA via VIES | l'utente loggato |
| `squadra` | elenco, ruolo, blocca, sblocca, scollega Google: usa la service key dopo aver verificato che chi chiama è ceo | l'utente loggato, ceo |
| `smartlead-webhook` | Smartlead bussa a ogni risposta: fa partire il direttore con la catena sync, googlefit, bozze | Smartlead, con `?chiave=` (deploy `--no-verify-jwt`) |
| `sveglia` | Pub/Sub bussa quando arriva una mail: fa partire il direttore con posta e calendar; se c'è già un direttore in coda non ne accoda un altro | Pub/Sub, con `?chiave=` (deploy `--no-verify-jwt`) |

Deploy: `npx supabase functions deploy <nome> --project-ref tqssfcuzezlczfceqsmk`
(con `--no-verify-jwt` per le tre a segreto). Il comando esatto sta in testa a ogni
funzione. Segreti in Supabase: `OPENAI_API_KEY`, `MODELLO_OPENAI`, `CLARA_SEGRETO`,
`GITHUB_DIRETTORE_TOKEN`, `WEBHOOK_SEGRETO`, più quelli di piattaforma.

## 6. Il direttore e le operazioni

`scripts/direttore.py` gira su GitHub Actions (`.github/workflows/direttore.yml`):
legge la tabella `operazioni`, fa partire quelle dovute (in ordine, una alla volta,
timeout 40 minuti ciascuna), scrive esito e durata in `operazioni` e una riga in
`corse`. Concorrenza: mai due direttori insieme (concurrency group). Parte:

- a orologio, ogni 20 minuti;
- `workflow_dispatch` con `forza=<chiavi>` da Smartlead, da Gmail (sveglia), dal
  cron di Supabase, o a mano (`gh workflow run direttore.yml -f forza=posta`).

Le operazioni oggi in produzione (cadenza in minuti; le giornaliere hanno un'ora):

| Chiave | Comando | Cadenza | Cosa fa |
|---|---|---|---|
| posta | `posta.py` | 15 | legge le caselle Gmail di chi è entrato con Google, attacca le mail alle aziende (email esatta, poi dominio; se solo l'oggetto combacia chiede), aggiorna gli stati |
| calendar | `calendario.py && tracciato.py` | 15 | specchia Google Calendar in `agenda` e propone gli avanzamenti di fase coerenti con le call fatte |
| sync_smartlead | `sync_v2.py` | 15 | porta dentro risposte e thread da Smartlead, riconcilia, scrive `sync_runs` |
| googlefit | `googlefit.py` | 15 | per le aziende in arrivo: settore, provincia, zona (Foglio Zone), verdetto |
| bozze | `bozze.py` | 15 | scrive le bozze di risposta secondo il playbook `docs/clara-sg-outbound.md`, con cancello di qualità; le mette in Posta |
| appunti | `appunti.py` | 30 | prende gli Appunti di Gemini dal Drive, li attacca alla call e all'azienda |
| transcript | `transcript.py` | 30 | da ogni riassunto di call una proposta di avanzamento |
| preparo | `preparo.py` | 30 | il punto pre-call per le call delle prossime 30 ore |
| azioni | `azioni.py` | 60 | le otto azioni di Clara (preventivo fermo, non pagato, call senza riassunto, cliente senza canone, prova che finisce, accessi fermi, imparato mancante, cliente muto) |
| stripe | `stripe_sync.py` | 60 | incassi da Stripe (sola lettura) e preventivi pagati |
| silenzi | `silenzi.py` | 120 | dopo 10 giorni di silenzio post analisi, nei Persi |
| calendario_sg | `calendario_sg.py` | 180 | le scadenze del Workspace nel calendario Google «SG Scadenze» |
| scadenze | `scadenze.py` | 240 | avviso 14 giorni prima della fine di una prova |
| sync_completo | `sync_v2.py --completo` | giornaliera 05:00 | il sync intero |
| rilettura | `rilettura.py` | 06:30 | seconda lettura delle risposte: corregge il sicuro, propone il resto |
| brief | `clara.py` | 08:00 | il brief del mattino in chat |
| diario_recap, diario | `diario.py` | 08:20, 09:40 | il recap del lunedì e le domande del diario (martedì e giovedì) |
| scadenze, silenzi | | 07:30, 07:40 | ora preferita quando la cadenza lo permette |
| recap_pomeriggio, recap_sera | `recap.py` | 13:00, 18:00 | il punto in chat |
| webhooks | `webhook_smartlead.py` | 04:50 | registra il campanello su ogni campagna Smartlead |
| posta_ordine | `posta_ordine.py` | giornaliera | chiude le proposte vecchie a basso rischio |
| orecchio | `orecchio.py` | giornaliera | rinnova l'ascolto push di Gmail (scade dopo 7 giorni) |
| backup | (workflow `backup.yml`) | 03:00 | esporta tutte le tabelle, cifra, salva come artifact per 30 giorni |
| granola | `granola.py` | spenta | superata da appunti (Gemini) |

Aggiungere un'operazione: uno script in `scripts/` che usa `stanza.sb` e stampa
poche righe; una riga in `operazioni` (chiave, nome, cosa, comando, cadenza, ordine).
Da quel momento la sala di controllo la mostra e il direttore la fa girare.

Costi: ogni corsa del direttore dura da uno a due minuti di runner GitHub; con
l'orologio a 20 minuti sono circa 72 corse al giorno più i campanelli.

## 7. Clara

- **Il cervello**: `scripts/cervello.py`, una porta sola verso il modello. In cloud
  `FORNITORE=openai`, modello `gpt-5` (dal workflow); in locale il difetto è
  `gpt-5-mini`, con Claude come alternativa. Le funzioni cloud usano OpenAI
  direttamente. Le istruzioni in `istruzioni` vincono su tutto.
- **La Posta** (`proposte`): ogni cosa che Clara vuole fare. L'app la mostra nella
  pallina e in Posta di Clara; al sì esegue `azione` (una task, un avanzamento, una
  mail da mandare, una classificazione). `posta_ordine.py` chiude quelle vecchie.
- **La chat** (`clara_messaggi`): il brief del mattino, i recap, le domande del diario,
  i promemoria; la risposta in tempo reale arriva da `clara-risponde` via trigger.
  Nel browser, `ClaraVolante.tsx` riconosce anche comandi a parole senza modello:
  «ricordami di...», «fissa una call...», «fammi un piano per...».
- **Le azioni** (`azioni.py`): promemoria con `ref`, quindi mai doppi.
- **La preparazione delle call** (`preparo.py`): scritta sulla riga di `agenda`, si
  legge in Oggi e sulla scheda.
- **I documenti**: `documento` riscrive un documento dell'Editor con quello che
  Clara sa dell'azienda; `piano` trasforma appunti in task.
- **Il tono**: le stesse regole ovunque, nel PDF (`src/lib/documento.ts`), nella chat
  (`stanza.di_clara`, `regole.pulisci`) e nei prompt delle funzioni: niente trattino
  lungo, niente puntino centrale, niente punto esclamativo, niente parole vuote.

## 8. Integrazioni e segreti

| Servizio | Come | Dove stanno le chiavi (nomi) |
|---|---|---|
| Google (Gmail, Calendar, Drive, Docs) | OAuth per persona, refresh token in `google_token`, scambio in `scripts/google_api.py` | `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` (GitHub, .env.local) |
| Gmail push | topic Pub/Sub `sg-posta` e iscrizione `sg-posta-sveglia` nel progetto Cloud, `users.watch` per casella | `GOOGLE_CLOUD_PROJECT`, `WEBHOOK_SEGRETO` |
| Smartlead | API v1 (sync) e webhook per campagna | `SMARTLEAD_API_KEY` (GitHub) |
| Stripe | API in sola lettura | `STRIPE_SECRET_KEY` (GitHub, .env.local). `STRIPE_ADMIN_KEY` resta solo sul Mac, mai in cloud |
| OpenAI | chat completions | `OPENAI_API_KEY`, `MODELLO_OPENAI` (GitHub e Supabase) |
| SearchAPI | recensioni Maps in googlefit | `SEARCHAPI_KEY` |
| Web Push | VAPID; iscrizioni nelle preferenze (`push-iscrizioni`); `scripts/avvisa.py` | `VITE_VAPID_PUBLIC`, `VAPID_PRIVATE` |
| Calendario ICS | l'ICS segreto del calendario di Dre come seconda fonte | `CALENDARIO_ICS` |
| GitHub | token per far partire il direttore | `GITHUB_DIRETTORE_TOKEN` (Supabase), `github_direttore` (Vault di Postgres), `PAGES_DEPLOY_KEY` (GitHub) |
| Supabase | service key per gli script, anon key per il browser, access token per Management API e deploy | `SUPABASE_SERVICE_KEY`, `VITE_SUPABASE_ANON_KEY`, `SUPABASE_ACCESS_TOKEN` |

Regole: le chiavi non passano mai in chat né nei commit; `.env.local` è fuori dal
repo; in cloud stanno nei secret di GitHub e di Supabase. Le chiavi Google Ads in
`.env.local` sono di un lavoro precedente e non le usa niente nel repo.

## 9. Come si lavora e come si pubblica

- Sviluppo: `npm run dev`, demo con `?demo`. Prima di ogni push:
  `npm run controlla` e `npm run build` devono passare.
- CI (`controlla.yml`): a ogni push e pull request, tsc + oxlint + vitest + build.
- Pubblicazione (`pubblica.yml`): a ogni push su `main` che tocca `src/`, `public/`,
  `index.html` o la configurazione, compila con `BASE_PATH=/clara/` e copia `dist/`
  nel repo pubblico `studiogalilei/clara` (GitHub Pages). L'app si aggiorna da sola
  per tutti: il service worker è in `autoUpdate`.
- Backup (`backup.yml`): ogni notte alle 01:00 UTC. Lo script di ripristino non
  esiste ancora.
- Funzioni: deploy a mano con la CLI (vedi 5). Migrazioni: a mano (vedi 4).
- Script una tantum ancora nel repo, non operativi: `import_all.py`,
  `migra_soppressioni.py`, `carica_brand.py`, `carica_modelli.py`,
  `esporta_thread.py`, `confronto-modelli.py`, `sync_smartlead.py` (sostituito da
  `sync_v2.py`), `clara_ascolta.py` e `installa-ascoltatore.sh` (sostituiti da
  `clara-risponde`), `granola.py` (spento).

## 10. Cose da sapere

- **Calendar in push non si può.** Google chiede un dominio verificato per il
  ricevitore delle notifiche di Calendar; il nostro sta su Supabase. Gli inviti
  arrivano per mail, quindi il push di Gmail copre quasi tutto; il resto aspetta il
  giro dei 20 minuti.
- **Le due fasi.** `stage` è l'outbound (Smartlead), `pipeline_stage` è la vendita
  (dalla conoscitiva alla firma). `fuori=true` vuol dire fuori dall'outbound, dentro
  la pipeline.
- **Il pedaggio.** Non si avanza di fase senza il riassunto della call: la bacheca e
  la scheda lo chiedono (`regole.pedaggioPagato`, marca `[Fase]` in testa al testo).
- **Il vocabolario dei settori** è il Foglio Settori (`data/foglio_settori.csv`,
  141 voci); `scripts/settori_json.py` lo copia in `src/lib/settori.json`.
- **Il contratto di prova** in `modelli/` è ancora la versione a 1.500: si corregge
  con «Correggi» in Documenti o si carica il nuovo.
- **Documenti vecchi nel repo**: `README.md` rimanda qui; `LEGGIMI-PRIMA.md`,
  `SETUP.md`, `CANTIERE-CRUSCOTTO.md`, `docs/ARCHITETTURA-CLARA.md`,
  `docs/clara-sg-system-prompt.md` sono storia (settembre, prima dell'infrastruttura
  in cloud). Restano attuali `docs/LA-STANZA-DI-CLARA.md` (le regole di Clara) e
  `docs/clara-sg-outbound.md` (il playbook che usa `bozze.py`).
- **La sala di controllo** (Impostazioni, Lo Studio, Strumenti) è il posto dove si
  vede se tutto gira: ultima corsa ed esito di ogni operazione, le azioni di Clara,
  le istruzioni.

## 11. Glossario

| Parola | Vuol dire |
|---|---|
| Posta di Clara | le proposte in attesa di un sì o un no |
| pedaggio | il riassunto della call che serve per avanzare di fase |
| perimetro | le aziende che una persona può vedere (regole RLS) |
| direttore | il lavoro in cloud che fa girare le operazioni |
| campanello | un webhook che fa partire il direttore subito |
| orecchio | l'ascolto push di Gmail |
| sala di controllo | la schermata delle operazioni (Plugin.tsx) |
| cantiere | la parte del ceo in «Cosa cambieresti»: feedback, stelle, diario |
| vedi come | il ceo che guarda l'app con gli occhi di un'altra persona |
| pod | un manager e le persone che segue |
| SG-id | il numero progressivo di un'azienda dalla prima risposta |
