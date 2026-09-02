# ODYN CRM — Contesto completo per progettazione
*(aggiornato 7 luglio 2026, sera — scritto da Claude Code per la sessione di design su Claude Desktop)*

## 0. Chi legge questo documento
Sei Claude, e stai aiutando **Dre (Dramane)**, fondatore di **Studio Galilei**, a progettare il suo CRM. Dre: italiano informale, diretto, NON tecnico, odia la fuffa. Siete soci alla pari ("entrambi CEO"): lui brainstorma idee disorganizzate, tu le riorganizzi e fai domande per strutturarle. Mai ignorare un problema: dillo e proponi soluzioni. Meglio prevenire che curare. Lui vuole arrivare a fidarsi ciecamente del sistema e limitarsi ad APPROVARE.

## 1. Il business (in breve)
- **Studio Galilei** = agenzia marketing AI-first. Visione: "l'Anthropic italiano" — un software centrale + un "modello AI" chiamato **ODYN** (in realtà un'infrastruttura di agenti e workflow), partner esterni invece di dipendenti, obiettivo monopolio Italia.
- **Flusso commerciale attuale (cold outreach)**: campagne email su **Smartlead** (mittente: caselle "Lorenzo Fornasier" su ~10 domini) → il lead risponde → gli si manda un'**analisi Google Ads gratuita** brandizzata (il "dono", angle "gigante buono": generoso, zero pressione) → call → proposta con formula soddisfatti-o-rimborsati.
- **3 settori main decisi**: Turismo & Hospitality, Salute & Benessere, Casa.
- Regola d'oro assoluta: **Claude non invia MAI nulla** — prepara, Dre clicca. Niente account, niente carte, niente API key in chat.

## 2. IL MODELLO OPERATIVO (deciso da Dre, 7 luglio — è la legge)
> **Smartlead serve SOLO per il primo contatto. L'obiettivo è portare i lead FUORI.**
1. Smartlead aggancia il lead (primo contatto, risposta, invio analisi, follow-up).
2. Quando il lead è maturo (call fatta), Dre lo **"porta fuori"** da Smartlead → da lì vive SOLO nel CRM, nella **pipeline agenzia**.
3. Dopo OGNI call, Dre delinea **sempre il next step** (regola personale sua).
4. **Supabase = unica fonte di verità.** Tutto si segna lì. Obsidian resta per conoscenza/playbook/analisi, NON per il tracking lead.
5. Claude = **motore automatico in sinergia**: sync, classificazione, preparazione bozze/analisi; Dre approva e agisce.

## 3. Lo stato del sistema — COSA ESISTE GIÀ (costruito, funzionante)

### 3.1 Stack
- **App**: `~/Documents/odyn-crm` — Vite + React 19 + TypeScript + Tailwind 4 + supabase-js, **PWA** (Dre la usa anche da telefono). Nessun router: tab con state in App.tsx. Dev: `npm run dev`.
- **DB**: Supabase (progetto `ncqkaaeokdubrnielzxn`), ~13.150 prospect importati, con **PID** (Prospect ID permanente P-NNNNN), registro **soppressioni** (GDPR/rimozioni/deceduti — mai più contattare), **liste** (L-NNN) con cancello di validazione.
- **Script Python** (in `scripts/`, girano sul Mac, service key in `.env.local` MAI committata): `sync_v2.py` (nuovo, vedi sotto), `import_all.py`, `valida_lista.py`.
- Chiave Smartlead in `~/.hermes/config.yaml`. API Smartlead: base `https://server.smartlead.ai/api/v1`, serve User-Agent, dà 401 transitori sotto raffica (retry).

### 3.2 Schema DB (v1+v2+v3 applicati)
**prospects**: email(unique), name, role, phone, linkedin, company, website, sector, city, socials(jsonb), owner_name, campaign, campaign_id, lead_id, stage, first/last_reply_at, analysis_sent(+at,+pdf), next_action, next_action_date, no_followup, deal_value, lost_reason, notes, enriched(jsonb: campo→'auto'|'manual'), pid, cid, source.
**v3 (nuove, 7/7)**:
- `awaiting_us` bool → l'ultimo messaggio del thread è del LEAD = tocca a noi rispondere (IL campo anti-buchi)
- `classificazione` → da_classificare | positivo | tiepido | negativo | ooo | rinvio | fuori_target | soppresso (il sync la propone; se Dre la corregge, `enriched.classificazione='manual'` e il sync non la tocca più)
- `followup_due` date, `ooo_until` date
- `fuori` bool + `fuori_at` + `pipeline_stage` (call_fatta | proposta_inviata | pilota | cliente | perso_fuori)
**interactions**: prospect_id, at, kind(email_in|email_out|analisi|followup|call|nota), body — timeline per lead, dedup su (prospect_id,at,kind).
**suppressions**, **lists**, **list_members**: anagrafe soppressioni e liste.
**sync_runs** (v3): log di ogni sync — leads_scanned, replies_found, reconciliation_ok, anomalies. Se i conti non tornano resta scritto.
**v_oggi** (vista): tutto ciò che chiede attenzione oggi, con priorità (1=da rispondere, 2=follow-up scaduto, 3=next step scaduto, 4=rientro da OOO).

### 3.3 Stage Smartlead (conversazione) vs Pipeline agenzia
- **Stage conversazione**: nuovo → risposto → analisi_inviata → in_follow_up → call_fissata → (cliente | perso | rinviato). Bloccati per il sync: cliente, call_fissata, perso, rinviato.
- **Pipeline agenzia** (solo se fuori=true): call_fatta → proposta_inviata → pilota → cliente | perso_fuori.

### 3.4 UI attuale (3 tab, mobile-first, max-w-2xl)
1. **Oggi**: 🔴 Da rispondere (awaiting_us, esclusi negativi/fuori_target/soppressi) · Follow-up dovuti (silenzio ≥5gg da analisi) · Ricontatti programmati · Rientri da ferie (ooo_until scaduta).
2. **Pipeline**: i "fuori", a sezioni per pipeline_stage, con contatore e **⚠️ warning sui lead senza next step**.
3. **Prospect**: lista globale con filtri e ricerca.
4. **Scheda** (modal): bottone **"Porta fuori →"** (setta fuori+call_fatta+nota in timeline), chip classificazione correggibili, chip stage/pipeline, 15 campi editabili (modifica manuale = 'manual' in enriched, il sync la rispetta), timeline, note.

### 3.5 Sync v2 (`scripts/sync_v2.py`) — il "segugio" affidabile
- **Perché esiste**: il vecchio giro usava l'endpoint `/statistics` di Smartlead che è paginato/rate-limitato e **sotto-restituisce senza errore** → risposte di lead reali perse in silenzio (il 7/7 le ha trovate Dre a mano: caso grave, mai più).
- **Come funziona**: per ogni campagna non archiviata (esclusa "The Best Campaign in the World" che si IGNORA sempre) scorre TUTTI i lead via `/campaigns/{id}/leads` paginato → **riconcilia** scaricati vs total dichiarato (se non tornano: anomalia scritta e exit code 2) → per chi ha risposto legge il thread `/message-history` → calcola awaiting_us, classificazione euristica (regex IT: positivo/negativo/ooo/rinvio/cambio-indirizzo), data rientro OOO, followup_due (5gg dopo analisi) → upsert su Supabase + interactions. **Nessuno viene scartato**: anche OOO e autoreply entrano con stato e data. Non tocca: stage bloccati, fuori=true, campi 'manual'. `--dry-run` disponibile. Ogni corsa loggata in sync_runs.
- **Stato**: scritto e pronto, **MAI ancora girato in produzione** (schema appena applicato; il primo run completo è il prossimo passo, con verifica che i 5 lead persi — marco.genova@digital-instruments.com, it@evolvomobility.com, massimo@madaprojects.it, ottaviano@lamedicinaestetica.tech, f.gianisi@gianisi.com — compaiano in Da rispondere).

## 4. Il resto dell'ecosistema (fuori dal CRM ma collegato)
- **Pipeline analisi "Canossa"** (in Obsidian `ODYN Cockpit/`): ricerca → dossier con DATI VERI (script dossier.py: SERP live + Maps via SearchAPI + audit sito) → brand assets (logo+palette prospect) → scrittura 8 sezioni → **lint_analisi.py** (gate che boccia: trattini lunghi, sezioni mancanti, dossier assente, dati non citati) → render PDF brandizzato. Le risposte ai lead usano template verbatim + **lint_risposta.py** (boccia tu/lei misto, aperture secche, promesse).
- **Regole outbound**: l'analisi-dono va a tutti i prospect validi; l'offerta OUTBOUND si propone solo se internazionale + high-ticket + non competitor. Skip: agenzie marketing/competitor; ONLUS → angolo Google Ad Grants.
- **Caselle**: solo "Lorenzo"; soglie deliverability: <80% reputazione staccare 5-7gg, riattaccare ≥90%, bounce <2%, 20 mail/gg/casella, mai link/PDF in prima mail. Salute in calo il 6/7 (7 rosse staccate).
- **Follow-up**: 5 giorni di silenzio dopo l'analisi → FOLLOW UP 1; rinvii con data propria rispettati (es. SAD Brescia→ottobre, EXSSA→mai più sollecitare, ricontatta lei).

## 5. COSA MANCA / DA PROGETTARE (il lavoro di questa sessione di design)
Priorità dichiarate da Dre:
1. **Migliorare la UI** ("poi miglioriamo la UI" — detto esplicitamente). Oggi è funzionale ma spartana. Idee sul tavolo: smart defaults ovunque (70-90% degli utenti non cambia i default), vista mattutina come "daily brief", niente stati a zero (goal gradient), dashboard con numeri pipeline.
2. **Il "software di gestione tutto suo"**: evolvere il CRM nel centro operativo dell'agenzia — sezione clienti veri, valore pipeline, e più avanti il **portale cliente** (ogni cliente vede i suoi lavori in corso/timeline — vista cliente della stessa anagrafe via Client ID).
3. **Automazioni in sinergia**: sync schedulato (mattina presto) + daily brief automatico; bozze risposte/analisi attaccate al lead nel CRM (oggi vivono in /tmp e in Obsidian, fragile); registro decisioni a fine sessione.
4. **Nodi aperti**: deploy (oggi solo localhost; Vercel? Dre ha già account), auth (oggi email+password singolo utente), come mostrare le bozze preparate da Claude dentro la Scheda, notifiche (PWA push? Telegram?), LinkedIn Cockpit gemello (prospect estate, stessa logica segugio).

## 6. Vincoli non negoziabili (qualunque design deve rispettarli)
1. Claude prepara, **Dre invia/clicca**. Sempre.
2. **Nessun lead si scarta**: ogni contatto ha sempre stato + prossima azione + data. Anche OOO e autoreply.
3. I conteggi si **riconciliano**: se i numeri non tornano, il sistema lo dice forte, non fa finta di niente.
4. Le correzioni manuali di Dre **vincono** sull'automazione, per sempre.
5. Soppressioni = sacre (GDPR, rimozioni, deceduti): mai più contattare, tutto il sistema lo sa.
6. Semplicità per un non-tecnico: Dre apre l'app la mattina e in UNA schermata sa cosa fare oggi. Lui approva, non amministra.
7. Niente segreti in chat/codice/git: chiavi solo in `.env.local` (mac) e `~/.hermes/config.yaml`.

## 7. Riferimenti rapidi
- Repo: `~/Documents/odyn-crm` (src/components: App, Oggi, Pipeline, Lista, Scheda, Login, ui; src/lib: types.ts, supabase.ts; supabase/: schema.sql, schema_v2.sql, schema_v3.sql; scripts/: sync_v2.py, import_all.py, valida_lista.py)
- Obsidian: `~/Documents/Obsidian/studiogalilei` → `Sistema Operativo Studio Galilei/ODYN Cockpit/` (playbook, scripts analisi, data), `00 - Cervello Condiviso/` (visione, linee guida analisi).
- Supabase dashboard: progetto `ncqkaaeokdubrnielzxn`.

*Fine contesto. Progetta insieme a Dre: fai domande una alla volta, proponi opzioni concrete con raccomandazione, e traduci tutto terra-terra.*
