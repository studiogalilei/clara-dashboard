# ODYN WORKSPACE — Documento completo di contesto e ingegnerizzazione
*(9 luglio 2026 — preparato da Claude Code per la sessione di design con Dre. Autoportante: contiene tutto il contesto necessario. Nessun segreto incluso.)*

---

## PARTE 0 — Chi legge e a cosa serve
Sei Claude e stai aiutando **Dre (Dramane)**, fondatore di **Studio Galilei**, a **ingegnerizzare il software finale del suo workspace**. Dre: italiano informale, diretto, NON tecnico, odia la fuffa. Lavorate da pari ("entrambi CEO"): lui brainstorma disordinato, tu organizzi e fai domande una alla volta, proponi opzioni con una raccomandazione, traduci tutto terra-terra. Mai ignorare un problema: dillo e proponi soluzioni. L'obiettivo di Dre: un sistema così solido che lui si limiti ad APPROVARE.

**Output atteso da questa sessione**: la specifica ingegnerizzata del nuovo software (architettura, moduli, priorità), da dare "ai ragazzi" (il team di sviluppo — Studio Galilei ha collaboratori esterni, inclusi profili in Pakistan/India usati per setup campagne e infrastruttura email).

---

## PARTE 1 — Il business e la visione

**Studio Galilei** = agenzia marketing AI-first. Visione dichiarata: **"l'Anthropic italiano"** — un software centrale e un "modello AI" chiamato **ODYN** (verso il mercato si vende come modello; tecnicamente è un'infrastruttura connessa di agenti + workflow + playbook). Il business: connettere Talenti ad Aziende. Partner esterni invece di dipendenti (futuro PRT-ID + matching). Obiettivo: monopolio Italia, "le agenzie si uniscono o affogano" (costo delivery AI-first imbattibile + white-label ai competitor che mollano).

**Le 6 macchine** (ordine di costruzione): 1) fondamenta dati (anagrafe/soppressioni/validazione/CRM — IN CORSO, è questo progetto) → 2) sales system → 3) hire system → 4) creative engine → 5) delivery system → 6) consolidamento.

**3 settori main**: Turismo & Hospitality · Salute & Benessere · Casa. Porta aperta agli altri.

**Flusso commerciale oggi (funziona, genera call ogni settimana):**
1. Campagne cold email su **Smartlead** (mittente "Lorenzo Fornasier", ~68 caselle su ~10 domini, throttle ~20 mail/giorno/casella)
2. Il lead risponde → si classifica → ai positivi si manda **l'analisi Google Ads gratuita** ("il dono", angle "gigante buono": generoso, zero pressione) — PDF brandizzato col LORO logo/colori, con dati veri verificati (SERP live, recensioni Maps, audit sito)
3. Silenzio dopo l'analisi → follow-up (FU1 a 5 giorni, FU2 a 15)
4. Call → lead maturo si **"porta FUORI"** da Smartlead → pipeline agenzia (call fatta → proposta → pilota → cliente). Dopo OGNI call si definisce il next step. Offerta: formula soddisfatti-o-rimborsati sul pilota; outbound a percentuale SOLO se internazionale+high-ticket+non-competitor.

---

## PARTE 2 — Il principio fondativo del software

> **Nessuna conversazione muore mai.** Ogni lead ha sempre, visibile: uno STATO, una PROSSIMA AZIONE, una DATA. Tutto il software esiste per garantire questo.

Secondo principio: **il software prepara, l'umano invia**. Claude/l'agente non manda MAI nulla da solo: prepara bozze, analisi, code di approvazione; Dre clicca.

---

## PARTE 3 — FALCON STUDIO: la logica completa dell'antenato
*(App locale che ha girato per mesi, ritirata il 3/7/2026. Archivio: `Falcon Studio/ARCHIVIO-2026-07-03/` — falcon_bridge.py ~5.246 righe + index.html ~2.600 righe. Questa è la logica da cui ripartire.)*

### 3.1 Architettura
- **Backend**: 1 file Python 3, zero framework (stdlib: ThreadingHTTPServer), server su `127.0.0.1:8765`, CORS solo loopback. Persistenza: file JSON/JSONL (niente DB). LaunchAgent macOS per l'autostart.
- **Frontend**: 1 file HTML, SPA vanilla JS stile "Obsidian-like", REST + SSE per lo streaming chat.
- **Motori AI switchabili**: `local` (Ollama qwen3:8b, gratis, grunt work) / `codex` (Hermes/Codex flat, gratis) / `frontier` (Claude/GPT a pagamento). Il lavoro pesante di scrittura andava a codex, la classificazione al locale.

### 3.2 La UI: il funnel come tab
Sidebar: Home, Analisi (vista operativa), Impostazioni, Attività/Agenti. La vista operativa aveva un **funnel bar** coi conteggi e queste tab:

| Tab | Contenuto | Azioni |
|---|---|---|
| **Nuove** | Lead che hanno appena risposto e aspettano noi (separati "veri" / "forse-no") — card con thread, bozza AI, analisi allegata | "Inviata l'analisi", invia risposta via Smartlead, copia/correggi bozza |
| **Inviate/Follow-up** | Analisi mandata, silenzio ≥3 giorni lavorativi → follow-up dovuti | Copia follow-up, avanza stato |
| **Appuntamenti** | Call estratte automaticamente dai thread (parsing date, anche relative: "giovedì alle 9:30") | Vedi agenda |
| **Trattativa** | Trattative aperte | — |
| **Chiuse** | Vinti/persi con ricerca e filtri | Cerca, filtra |
| **Smartlead** | Campagne live, toggle "gestita sì/no" | Scope delle campagne |

Ogni lead → **drawer**: dati, thread completo, analisi collegata, chat con l'agente. Più un **agent drawer** (bolla) con la coda "da approvare".

### 3.3 La macchina a stati del lead
`risposto → analisi_inviata / in_attesa → appuntamento → trattativa → chiuso/firmato/cliente | perso/non_firmato` + `ignorato`. Concetti chiave:
- **`ball` = you/them**: di chi è la palla. La vista principale è sempre "dove la palla è NOSTRA". (L'idea singola più preziosa di Falcon.)
- **PARKED_STAGES**: stati che bloccano le automazioni (niente bozze automatiche a chi è parcheggiato).
- Categoria Smartlead "Meeting Request" → auto-stage `appuntamento`.

### 3.4 Il loop dell'agente (il motore autonomo)
Thread in background (`agent_cycle` + scheduler + supervisor + queue worker):
1. Scarica le risposte dalle campagne gestite
2. Classifica ogni risposta a 2 livelli: (a) rifiuto/interesse/altro; (b) **8 scenari**: `interessato, chi_sei, quanto_costa, gia_agenzia, non_e_il_momento, solo_mail, non_interessati, rimuovetemi`
3. Accoda lavori: **draft** (bozza risposta), **analysis** (genera analisi se: ha risposto + ha sito + analisi non esiste; max 20/giro), **followup** (per chi è in scadenza silenzio)
4. Il worker esegue; il supervisor sblocca i job impantanati (timeout 6 min draft / 20 min analisi); tutto idempotente (`seen_reply_at`), coda persistita, **audit log append-only di ogni azione**
5. Tutto finisce in coda di approvazione umana. Mai invio automatico.

### 3.5 La pipeline analisi (il prodotto)
`dominio → scraping multi-pagina del sito → keyword scout (Google autocomplete) → verifica su Google Ads Transparency (Tipo A: fa già ads / Tipo B: domanda esiste ma nessuno fa ads) → dossier dati veri ("Cacciatore", LLM locale) → scrittura ("Analista", con skill/linee guida in Markdown) → revisione automatica ("Critico", max 2 giri) → logo + palette del prospect (fetch_client_logo, extract_brand_colors, pick_palette con guardie di leggibilità) → render PDF (WeasyPrint) → PDF brandizzato in Obsidian`.
Evoluzione post-Falcon (già viva nel Cockpit): **lint_analisi.py** = gate murato nel renderer (boccia trattini da AI, sezioni mancanti, dossier assente, dati non citati); struttura "Canossa" a 8 sezioni + "Prima di iniziare" col testo verbatim di Dre; regole di scrittura precise (frasi lunghe naturali, sezioni a inizio pagina, pagine piene).

### 3.6 Il "fossato": lo stile che impara
Ogni correzione di Dre a una bozza → salvata in `draft_corpus.jsonl` → riusata come esempio nelle bozze successive (retrieve_examples, learn_from_thread, collect_dre_corpus). Il software impara lo stile del capo. **È proprietà intellettuale cumulativa: più si usa, più è suo.**

### 3.7 Playbook nelle note (config senza deploy)
Le risposte non erano hardcodate: il backend leggeva un **file Markdown in Obsidian** (`## scenario · Nome`, `> quando:`, `> firma:`). Dre modifica la nota → il software cambia comportamento. Evoluzione post-Falcon: template verbatim + **lint_risposta.py** (boccia registro tu/lei misto, aperture secche, promesse vietate, trattini).

### 3.8 Integrazioni e servizi
Smartlead API (risposte, thread, invio con allegati via presigned upload su Cloudflare R2), Ollama locale, Hermes/Codex, SearchAPI + Apify (enrichment), Supabase (predisposto). Costanti: FOLLOWUP_DAYS=3 (poi diventato 5), MAX_ANALISI_PER_GIRO=20.

### 3.9 Perché Falcon è stato ritirato (le lezioni)
Monolite fragile, stato sparso in file locali invisibili a Dre, blocco TCC macOS su ~/Documents per il launchd, e soprattutto: **il tracking si fidava di endpoint Smartlead che sotto-restituiscono in silenzio** → lead persi scoperti a mano. Da qui la rifondazione.

---

## PARTE 4 — LO STATO ATTUALE (ODYN CRM v3, live oggi)

**Stack**: `~/Documents/odyn-crm` — Vite + React 19 + TS + Tailwind 4 + supabase-js, PWA (Dre la usa da telefono). Supabase = **unica fonte di verità** (~13.150 prospect con PID permanenti).

**Schema (v1+v2+v3):**
- `prospects`: anagrafica completa + `stage` (nuovo→risposto→analisi_inviata→in_follow_up→call_fissata→cliente|perso|rinviato) + **v3**: `awaiting_us` (bool: l'ultimo messaggio è del lead = tocca a noi — il campo anti-buchi), `classificazione` (da_classificare|positivo|tiepido|negativo|ooo|rinvio|fuori_target|soppresso), `followup_due`, `ooo_until`, **`fuori`** (portato fuori da Smartlead) + `fuori_at` + `pipeline_stage` (call_fatta|proposta_inviata|pilota|cliente|perso_fuori), `enriched` (jsonb campo→'auto'|'manual': le correzioni manuali vincono per sempre), `pid`/`cid`
- `interactions`: timeline per lead (email_in/out, analisi, call, nota), dedup
- `suppressions`: registro NON-CONTATTARE globale (gdpr/rimozione/lamentela/deceduto/non_target) — sacro
- `lists` + `list_members`: liste L-NNN col cancello di validazione (dedup→soppressioni→PID→report)
- `sync_runs`: log di ogni sync con riconciliazione e anomalie — **mai più buchi silenziosi**
- vista `v_oggi`: tutto ciò che chiede attenzione, con priorità (1=da rispondere, 2=follow-up scaduto, 3=next step scaduto, 4=rientro da OOO)

**Sync v2 (il segugio affidabile, `scripts/sync_v2.py`)**: per ogni campagna scarica l'**export CSV completo** (unica fonte con reply_count vero — l'endpoint /leads non lo espone, /statistics sotto-restituisce), riconcilia i conteggi (se non tornano: anomalia registrata e allarme), legge i thread di chi ha risposto, calcola awaiting_us + classificazione euristica (regex IT + categoria Smartlead come suggerimento) + date OOO, upsert su Supabase. Rispetta: stage bloccati, fuori=true, campi 'manual', followup_due non regredisce. **Nessuno si scarta**: OOO/autoreply/cambi email entrano con stato e data.

**UI attuale (3 tab)**: Oggi (🔴 Da rispondere / follow-up dovuti / ricontatti / rientri OOO) · Pipeline (i "fuori" per stadio, warning se manca il next step) · Prospect (lista+ricerca) · Scheda lead (bottone "Porta fuori →", chip classificazione correggibili, timeline, 15 campi).

**Fuori dal CRM ma parte del sistema**: pipeline analisi nel Cockpit Obsidian (dossier.py con SearchAPI, brand_assets.py, lint_analisi, render WeasyPrint), lint_risposta, template verbatim, registro decisioni. Bozze oggi in file temporanei (`/tmp/mail/*.txt`) — FRAGILE, da portare nel CRM.

---

## PARTE 5 — COSA COSTRUIRE (la roadmap proposta, da ingegnerizzare)

1. **Bozze nel CRM**: risposta+analisi attaccate al lead (tabella `drafts`?), stati bozza (proposta→approvata→inviata), bottone copia. Elimina i file temporanei.
2. **Il loop agente ricostruito sopra Supabase**: classificazione automatica → coda di approvazione visibile nella UI (l'"agent drawer" di Falcon, ma nel CRM). Claude gira via cron/scheduled task, scrive su Supabase, Dre approva dal telefono.
3. **Daily brief automatico**: sync schedulato + brief mattutino (già prototipato con scheduled task).
4. **Il fossato in Supabase**: tabella `rewrites` (bozza originale → correzione di Dre), riusata per ogni bozza nuova.
5. **Vista Appuntamenti + estrazione call dai thread** (Falcon lo faceva: parsing date relative).
6. **Portale cliente** (più avanti): vista cliente della stessa anagrafe via Client ID — lavori in corso, timeline, proposte.
7. **Multi-canale**: stessa macchina a stati per LinkedIn (LinkedIn Cockpit) e campagna USA.

## PARTE 6 — Vincoli NON negoziabili
1. Il software prepara, **l'umano invia**. Sempre.
2. Ogni lead: stato + prossima azione + data. Anche OOO e autoreply (il rumore di oggi è il lead di settembre).
3. Conteggi riconciliati o allarme. Mai buchi silenziosi.
4. Correzioni manuali > automazione, per sempre (flag manual).
5. Soppressioni irrevocabili e globali (GDPR/rimozioni/deceduti).
6. Un solo cervello: Supabase = stato; Obsidian = conoscenza (playbook/analisi/decisioni); niente stato in file volatili.
7. Semplicità per un non-tecnico: la mattina UNA schermata dice cosa fare. Dre approva, non amministra.
8. Segreti solo in .env locali / config fuori repo. Mai in chat, codice, git.
9. Gate qualità murati nel codice (lint analisi + lint risposte): le regole non si affidano alla memoria.

## PARTE 7 — Domande aperte da ingegnerizzare in questa sessione
1. **Dove gira l'agente?** Oggi: Claude Code sul Mac di Dre (manuale/schedulato). Opzioni: cron sul Mac / cloud (Vercel functions? un worker?) / Claude scheduled tasks. Vincolo: deve leggere Smartlead e scrivere Supabase; le chiavi stanno sul Mac.
2. **Coda di approvazione**: dentro la PWA (tab "Da approvare") o via canale (Telegram/notifiche push PWA)? Dre vive da telefono.
3. **Bozze**: schema tabella, ciclo di vita, come si collega al thread Smartlead (reply via API con un click dalla UI? Falcon lo faceva con R2 per gli allegati — l'invio resta però SEMPRE un click di Dre).
4. **Multi-utente**: oggi 1 utente (Dre). I "ragazzi" avranno accesso? Ruoli? (Il portale cliente arriverà dopo, ma lo schema deve prevederlo: RLS per ruolo.)
5. **Deploy**: oggi localhost. Vercel per la PWA? (Account già esistente.) Il sync resta sul Mac (chiavi) o si sposta?
6. **Il fossato**: come strutturare il corpus (embedding? semplice retrieval per scenario?) — Falcon usava retrieval semplice per scenario, funzionava.
7. Cosa del vecchio Falcon NON rifare (motori AI multipli in-process? chat SSE integrata? piattaforma agenti mock?) — proposta: tenere il workspace focalizzato sul funnel, l'AI vive fuori (Claude) e parla col DB.

---
*Riferimenti su disco: archivio Falcon in `Falcon Studio/ARCHIVIO-2026-07-03/` (falcon_bridge.py, index.html, analista/), dati storici in `Falcon Studio/.falcon-bridge/` (MAI aprire secrets.env), sistema attuale in `~/Documents/odyn-crm` (+ CONTEXT.md), pipeline analisi in Obsidian `ODYN Cockpit/`. Blueprint sintetico per il team: `00 - Cervello Condiviso/ODYN Workspace — La logica del software (da Falcon al nuovo).md`.*
