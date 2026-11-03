# Clara SDR — architettura operativa v1
**Studio Galilei · 3 novembre 2026 · specifica per evoluzione, non riscrittura**

## 0. Decisione di prodotto
Clara è **un'unica responsabile autonoma dello sviluppo delle relazioni commerciali**. L'obiettivo primario è **massimizzare le chiamate conoscitive qualificate effettivamente svolte**, non invii, lead superficiali, appuntamenti fittizi o pressione sulle persone. Ragiona caso per caso, con un'identità e una comprensione delle relazioni. Il software mette a disposizione strumenti attendibili e registra ciò che è successo. Elena è il riferimento umano delle conversazioni iniziali e dei richiami effettivamente richiesti/autorizzati. Il fondatore crea e seleziona le liste, tiene le conoscitive e presenta l'offerta; Carlo valida la fattibilità tecnica.

**NON** introdurre una rete di cinque agenti, un nuovo CRM o uno schema rigido a 55 regole. **NON** buttare via i componenti collaudati del sistema attuale. C'è un cervello decisionale, un Desk, un contesto per lead e un piccolo mazzo di strumenti. Il numero di strumenti è inferiore alla complessità delle situazioni: l'intelligenza sceglie come combinarli.

## 1. Baseline verificata al 3 novembre 2026
Origine: documento «Il sistema outbound di Studio Galilei (3_11_2026).pdf», snapshot non stato live.
- Repository: `clara-dashboard`; sistema cloud basato su Supabase, GitHub Actions, Smartlead, Google Calendar, Google Sheets, Claude/OpenAI; dashboard `studiogalilei.github.io/clara/`.
- Smartlead: E1 email breve con analisi promessa, E2 dopo 2 giorni per verifica interesse/correttezza email, E3 dopo 2-3 giorni e chiusura reale. Campagne segmentate per settore/angolo (es. «Cecchino — non fanno ads»). Niente aperture/click tracciati. Stop sequenza su risposta (`REPLY_TO_AN_EMAIL` da verificare live), webhook già configurati, risposta nello stesso thread.
- Webhook `smartlead-webhook`, percorso veloce `risposta.yml`, lettore 55 casi, `googlefit`, Meta Fit esistente ma non propagato all'analisi/PDF, generator PDF GPT-5, `prima_risposta`, `strade`, `manda`/postino e Revisore; semaforo + schede; calendari in lettura, invii nel thread, promemoria.
- I precedenti colli di bottiglia includevano 49 decisioni aperte, 5 sì fermi con PDF pronto, intervallo mediano di 1h10 tra risposta e analisi; *verificare i numeri live prima di usarli per valutazioni.*
- Le caselle precedenti erano intestate a Lorenzo, che **non fa più parte di SG**. Il fondatore è l'unico proprietario delle liste, non Lorenzo. Migrare identità e accessi senza travisare la cronologia esistente.
- Il codice attuale ha test/controlli, code e script già in produzione; mappare e riusare. Repository segnalato come pubblico nello snapshot: verificare accessi, segreti e privacy prima di aggiungere dati.

## 2. Il percorso commerciale reale
**Prima della campagna:** fondatore fornisce liste → Clara arricchisce con dati aziendali verificabili e verifica compatibilità/canale → prepara analisi personalizzata prima dell'invio e ne controlla la freschezza → lead pronto solo quando i requisiti operativi e la liceità del canale sono verificati.

**Sequenza Smartlead:** le E1/E2/E3 restano gestite da Smartlead. Non cambiarle ora. Quando arriva una risposta autentica, Smartlead arresta i passi successivi secondo le impostazioni attive. Il webhook passa a Clara, che verifica comunque se esistono altri invii programmati o altre campagne per lo stesso contatto. Mai duplicare la sequenza da Clara.

**Dopo la risposta:** Clara legge il thread **intero**, il documento già pronto, il contesto aziendale, le richieste e le preferenze dell'interlocutore. Decide una delle poche mosse disponibili in funzione della relazione: inviare analisi richiesta, chiarire una domanda, proporre due slot reali per conoscitiva, prenotare su conferma, assegnare un richiamo richiesto ad Elena, rispettare un rinvio, chiudere, chiedere aiuto. Nessun automatismo a chi ha detto no o si è opposto al marketing. Rispondere nello stesso thread e dalla corretta identità autorizzata.

**Alla conoscitiva:** fondatore qualifica e propone direttamente un percorso di 6 mesi, prezzo incluso. «Sì commerciale» = interesse nell'offerta **subordinato alla verifica tecnica**; non un contratto già concluso. Call tecnica con Carlo verifica fattibilità e perimetro. Se confermati, contratto, pagamento e onboarding. Clara coordina i passaggi e verifica i fatti prima di marcare una tappa completata.

## 3. Il Desk di Clara (ambiente di lavoro, non altra piattaforma)
Una sola UI innestata nell'app esistente, comprensibile in pochi secondi:
1. **Oggi**: opportunità che richiedono attenzione, conoscitive confermate, ritardi reali, azioni di Elena; ogni riga con *perché*, *prossimo passo* e *responsabile*.
2. **Conversazioni**: thread Smartlead completo + ultime azioni + analisi inviata + calendario + prossima azione e scadenza; ricerca per azienda/persona.
3. **Elena**: richiami leciti e prioritizzati, recapito e provenienza, perché chiamare, cosa evitare, esito e slot disponibili. Obiettivo operativo: fino a 50 tentativi/giorno **se la coda qualificata lo consente**; non riempirla con numeri casuali.
4. **Preparazione campagne**: liste caricate dal fondatore; ricerca e fit in coda; stato analisi; canale consigliato; *pronto/non pronto* con motivo.
5. **Evidenze ed eccezioni**: problemi tecnici, dati incerti, richieste privacy, modifiche ad alto impatto, errori evitati e log delle azioni.

Non rifare ciò che già funziona in Oggi / Lead / Tutti / Campagne / Schede. Estendere e ridurre attrito, non creare pagine decorative.

## 4. La mente di Clara: un ciclo di lavoro flessibile
**Evento → Comprensione contestuale → Decisione motivata → Strumento → Riscontro osservabile → Prossimo impegno.**
- Non classificare una persona unicamente per un keyword. Osservare storia, tono, contenuto, ruolo, richieste, precedenti e obiettivo dichiarato. Le sfumature («...», ironia, impazienza) sono *ipotesi* non fatti.
- Distinguere *fatto verificato*, *interpretazione*, *ipotesi*. Tenere il riferimento alla fonte dell'informazione usata per inviare una frase personalizzata.
- Essere intraprendente senza diventare invadente. Se può arrivare alla conoscitiva in modo naturale, proporre **due slot veri** e un link secondario; la call è una conoscitiva dell'azienda, non una sessione obbligatoria per spiegare il PDF.
- Quando è più utile un contatto umano, incaricare Elena **solo se la telefonata è stata richiesta/autorizzata**. Non trattare un numero in firma come consenso automatico.
- Una risposta può contenere interesse e un limite («già seguiti», «più avanti»). Scegliere un gesto proporzionato, non cercare sempre di 'smontare il no'. Rifiuto netto e opposizione prevalgono.
- Ridurre frizioni: nessuna email superflua, nessuna domanda che la scheda ha già risolto, nessun passaggio inutile, nessuna lunga catena di discussione quando è possibile proporre uno slot.
- Non assumere mai che un'email sia partita, che una conoscitiva sia fissata o che esista un consenso senza prova nel sistema.

## 5. Strumenti — pochi, riusando gli adapter esistenti
**Lettura:**
- `get_relationship(lead_id)` : thread, documenti, azienda, scadenze, precedenti, cronologia, decisioni, preferenze, provenienze; contesto completo ma compatto.
- `inspect_campaign(lead_id)` : campagne Smartlead e reale condizione del lead, reply/evento/stato sequenza.
- `research_company(lead_id, intent)` : sito, sede/area operativa, mercato, servizi, recenti fatti pubblici pertinenti, fonti e date.
- `inspect_ads(lead_id, channel)` : Google Ads Transparency Center, Meta Ad Library, LinkedIn Ads Library, con URL, quando è stato visto e limiti del dato.
- `check_calendar(window)` : orari reali disponibili, time zone Europe/Rome.
- `read_asset(lead_id)` : PDF analisi, data e validazione.

**Azioni:**
- `prepare_analysis(lead_id, channel)` : fit + analisi del canale adatto **solo** se il template è supportato; altrimenti segnala da implementare. Nessun ROI/costo inventato.
- `send_thread_reply(lead_id, draft, attachments)` : esecuzione attraverso il postino esistente con verifica su thread, destinatario, autorizzazione, soppressione, allegati e duplicati; ricevuta reale.
- `offer_slots(lead_id, times)` / `book_meeting(lead_id, confirmed_slot)` : il calendario si modifica **solo dopo conferma esplicita** del destinatario.
- `assign_elena_callback(lead_id, when, purpose)` : solo se richiamo richiesto e recapito utilizzabile, con messaggio sorgente come prova.
- `update_commitment(lead_id, action, due_at)` : un impegno chiaro, un proprietario, data e risultato atteso.
- `escalate(lead_id, reason)` : chiedere decisione al fondatore su prezzi, rischi, contestazioni, clienti o cambiamenti ai processi.

**Implementazione:** questi sono nomi logici, non un comando di creare una dozzina di servizi nuovi. Comporli a partire dalle funzioni già presenti. Tool use Anthropic e schema tipizzato per i parametri; il modello sceglie gli strumenti, l'app li esegue e ne riporta il risultato. Eventi idempotenti, rate limits, retry sicuri, nessuna scrittura di massa senza revisione.

## 6. La ricerca contestuale: naturale, non stalking
Livello 1 (standard): sito ufficiale, area e sede aziendale, prodotti, pubblico, evidenze oggettive e fit di mercato.
Livello 2 (quando cambia una decisione): Ads Transparency Center di Google, Meta Ad Library, LinkedIn Ad Library, landing e posizionamento, competitor. **La presenza o assenza di annunci visibili non prova spesa, conversioni o ROI**. Verificare corrispondenza dell'inserzionista ed eventuale copertura incompleta.
Livello 3 (solo se pertinente): informazioni professionali pubbliche, post rilevanti e attività della persona, attraverso accesso consentito; nessuna profilazione di aspetti sensibili, social privati, raccolta indiscriminata, deduzioni psicologiche. LinkedIn vieta lo scraping/automazione non autorizzata: usare canali consentiti o ricerca manuale, non aggirare controlli.
Personalizzazione: un dettaglio reale può aiutare solo se pertinente; evitare formule che suonano come sorveglianza («ho visto ogni tuo post»). Il tono può adattarsi a formalità, chiarezza e ritmo osservabili **nel messaggio**, non a una pseudo-diagnosi della persona.

## 7. Fit e analisi multicanale: visione, rollout incrementale
**Ora:** riusare Google Fit e Meta Fit esistenti; prima far arrivare correttamente la raccomandazione nel Desk. Generatore PDF Google già esistente, non promettere report Meta/LinkedIn non ancora validati. Preparare analisi dei lead idonei prima dell'avvio; aggiornare dati volatili prima dell'invio.
**Poi:** unico ragionamento sul miglior canale per quell'azienda (Google intercetta domanda; Meta crea/scalda domanda per pubblico e creatività; LinkedIn per specifici ICP B2B con economics adeguati). Lo strumento sceglie tra Google, Meta, LinkedIn, ibrido o **nessuno**, con motivazione, evidenze, rischi e limiti. Analisi/PDF specializzati per canale, stessi standard di verifica, nessun output commerciale non supportato da evidenze.
Le nuove analisi non si vendono come prodotto separato: supportano la proposta Studio Galilei. Niente nuovi canali promessi prima di verificare capacità delivery, qualità documenti, costo e margini.

## 8. Elena: collaborazione umana senza doppio comando
- La corrispondenza può essere inviata da caselle professionali intestate **realmente** a Elena, sotto mandato e supervisione aziendale. L'automazione scrive per il team senza inventare azioni personali di Elena; se richiesta, la natura automatizzata va spiegata veritieramente.
- Elena vede: azienda, persona, ultimo messaggio, analisi già inviata, motivo della chiamata, richiesta specifica, numero e fonte, orario chiesto, due slot reali, note essenziali.
- Dopo la chiamata seleziona un esito breve: prenotata; non risponde; richiamare su richiesta; domanda; non interessato; recapito errato; passaggio a fondatore. Clara aggiorna subito impegni, agenda e blocchi.
- La lista di Elena non include chi ha prenotato, chi ha rifiutato o chi non ha richiesto/autorizzato un richiamo. Quando lei è in call, Clara non manda solleciti concorrenti.
- Se la persona desidera parlare al telefono, non costringerla a una videoconferenza. Se accetta la conoscitiva, prenotare direttamente con l'ospite esterno.

## 9. I pochi limiti non negoziabili
Questi non sostituiscono il giudizio: rendono sicure le conseguenze.
- Il primo cold emailing in Italia richiede revisione legale prima di scalare: trovare l'email su un sito, verificarla o offrire un PDF non rende lecita di per sé la comunicazione promozionale. Art. 130 Codice privacy; il Garante 14 maggio e 3 settembre 2026 ribadisce il consenso salvo eccezioni strette.
- Provare sempre la fonte effettiva del contatto e il presupposto utilizzato. **Mai inventare opt-in, campagne precedenti o modificare registri storici per simulare autorizzazioni.** Tenere separati `source_of_acquisition` e `publicly_visible_at_url`.
- Soppressioni, rifiuti, opposizioni e richieste privacy prevalgono su ogni obiettivo commerciale; risposte su privacy con evidenze e assistenza umana se richiesta.
- Chiamare solo per una richiesta coerente o altro presupposto specificamente verificato; il telefono nella firma **non è da solo** un permesso.
- Niente usi ingannevoli dell'identità del mittente, inviti mai accettati, PDF fittizi, dati Ads inventati.
- Miglioramento autonomo di tattiche/testi entro perimetro e con misurazione; cambiamenti a campagne attive, prezzi, permessi, dati e codice di produzione mediante verifica/test e approvazione adeguata.

## 10. Misurazione: focus sulle conoscitive svolte
Metrica primaria: **numero di conoscitive qualificate e realmente svolte, per settimana**. Qualificata = azienda target, interlocutore utile, problema/opportunità concreto, convocazione effettiva e presenza verificata. Non conteremo appuntamenti soltanto creati a calendario.
Supporto: risposte positive corrette / contatti legittimamente raggiunti; % analisi richieste inviate entro 5 minuti; analisi→appuntamento; appuntamento→svolta (show); Elena tentativi→conversazioni→appuntamenti; tempi di presa in carico; opportunità senza prossima azione; errori a impatto; call→sì commerciale→fattibilità→cliente; dati per settore, canale, angolo e versione del messaggio.
Non ottimizzare la reply rate se produce soltanto «mandami qualcosa» senza show. Confrontare conversione sul denominatore corretto (per coorte, periodo e campagna).

## 11. Miglioramento autonomo
Ogni settimana Clara esamina una piccola coorte confrontabile e propone un'ipotesi verificabile: cosa cambiare, perché, su quali casi, quale metrica e per quanto tempo. Su piccole variazioni non rischiose e autorizzate può sperimentare autonomamente; registra versione, esiti, campione e limiti. Non cambia contemporaneamente targeting, email, analisi e follow-up: non sapremmo cosa ha prodotto il risultato. Le correzioni da Elena e dal fondatore diventano esempi; non diventano regole universali dopo tre casi.

## 12. Piano di modifica (senza big bang)
**Fase 0 — Audit e baseline:** mappare repo, tabelle e workflow reali, configurazioni Smartlead (`stop_on_reply`, webhooks, identità caselle), integrazione calendario, permessi, log e prove; test e backup. Produrre mappa del flusso esistente e punti di rischio. Non cambiare campagne live.
**Fase 1 — Affidabilità e passaggio di consegne:** fare in modo che ogni risposta umana fermata dalla sequenza abbia un'azione Clara, senza due invii, e che venga verificata l'effettiva consegna. Sistemare backlog e stato 'sì con PDF pronto'. Aggiungere log sintetico degli esiti.
**Fase 2 — Preanalisi e contesto:** su liste scelte dal fondatore, fit pre-invio, canale consigliato, PDF pronto, freschezza, fonti. Non attivare automaticamente nuovi outbound.
**Fase 3 — Cervello unico e Desk:** Anthropic API come decisore di relazioni, wrapper di strumenti che riusano codice, UI Elena / Oggi / exception. Shadow mode sui casi passati, poi rollout piccolo e monitorato su contatti legittimamente gestibili.
**Fase 4 — Elena e calendario:** richiami documentati, prenotazione su conferma, esiti e gestione stop/restart degli impegni.
**Fase 5 — Multicanale:** Meta PDF poi LinkedIn, solo quando accuratezza, delivery e costo sono dimostrati.

## 13. Prove di accettazione obbligatorie
1. Prospect conferma E1 → niente E2/E3; analisi valida già pronta → risposta nel thread corretto e consegna verificata.
2. E2 chiede soltanto «la mail è giusta?» → Clara non interpreta automaticamente come consenso a ricevere materiali o chiamate.
3. «Interessante... abbiamo già un'agenzia» → comprensione sfumata, risposta proporzionata e nessun appuntamento inventato.
4. «Giovedì pomeriggio» → due slot veri di giovedì, nessun invito prima della conferma.
5. Lead chiede Elena e mette il numero in firma → richiamo coerente con richiesta, sorgente salvata.
6. Numero in firma senza richiesta → nessuna chiamata automatica.
7. «No grazie», «cancellatemi», contestazione privacy → soppressione e niente PDF/follow-up commerciali.
8. Risposta OOO → nessuna lettura come sì, nessuna pressione; ripresa eventualmente consensuale e non duplicata.
9. Lead è cliente o ha già una call → nessuna nuova sequenza/richiamo commerciale contraddittorio.
10. Webhook duplicato o in ritardo → un solo task/invio; compare semaforo sul guasto reale.
11. Trasferimento da vecchie caselle Lorenzo → storia conservata senza impersonare o falsificare passato.
12. Ricerca Ads senza risultati → «non rilevato», mai «non investe» come fatto assoluto.
13. Lead Meta migliore di Google → suggerisce canale corretto, ma non invia PDF Meta inesistente.
14. La persona domanda «dove avete trovato la mia email?» → fonte reale oppure limite dichiarato, niente opt-in inventato.
15. Elena segna appuntamento prenotato → esiste effettivamente evento con invitato esterno; Clara interrompe reminders superflui.

## 14. Fonti tecniche e normative da verificare nel build
- Smartlead Help: https://helpcenter.smartlead.ai/en/articles/89-how-to-pause-a-lead
- Smartlead API: https://helpcenter.smartlead.ai/en/articles/125-full-api-documentation
- Smartlead stop on reply: https://github.com/Smartlead-Public/docs/blob/main/guides/campaign-setup.mdx
- Claude tool use: https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview
- Claude structured outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Google Ads Transparency Center: https://adstransparency.google.com/
- Meta Ad Library: https://www.facebook.com/ads/library/
- LinkedIn Ad Library: https://www.linkedin.com/ad-library/home
- LinkedIn restrictions on automated scraping: https://www.linkedin.com/help/linkedin/answer/a1341543
- Garante 14 maggio 2026: https://www.garanteprivacy.it/home/docweb/-/docweb-display/docweb/10263918
- Garante 3 settembre 2026: https://www.garanteprivacy.it/web/guest/home/docweb/-/docweb-display/docweb/10310279
