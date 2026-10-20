# Io più il sistema: design (20/10/2026)

Deciso con Dre in un brainstorming il 20/10 mattina. Segue il foglio della pipeline
(`2026-10-19-foglio-pipeline-design.md`), che resta valido: qui si dice cosa cambia attorno.

## Perché

Dre, 20/10: «delle cose non mi accorgo mai perché le vedi solo tu, le scopro dopo aver perso soldi
o quando domando a te». E: «finora l'errore è stato che ti ho fatto fare le cose sperando che le
facessi come volevo; stavo overbuildando. Il sistema sono io più il sistema». Vuole **smettere di
tornare su Claude** per sapere com'è andata o se qualcosa è rotto.

Il problema non sono i guasti in sé: è che **solo Achille li vede**, e che il confine fra cosa fa
il sistema e cosa fa Dre non era chiaro, quindi il sistema costruiva cose (bozze, avvisi,
schermate) che Dre non usa.

## Il confine

- **Fino all'analisi fa tutto il sistema**: prima mail, sì, analisi, follow-up. Nessuna
  approvazione e nessun avviso per Dre («sono easy quelli»).
- **Quando un lead risponde dopo l'analisi è «in conversazione» e passa a Dre.** Dre risponde su
  Smartlead, **senza bozze** («se è una conversazione no, faccio io»).
- Restano a Dre: rispondere alle conversazioni, chiamare, spostare i lead nel foglio, i prezzi.

## Cosa si costruisce

### 1. Il foglio è la base
Il foglio «Pipeline Studio Galilei» (esiste) resta il luogo dove Dre guarda tutti la sera.
Aggiunte:
- accanto a ogni azienda, **due link piccoli**: la **scheda** nel Workspace e la **conversazione**
  su Smartlead (il filo del lead nella Master Inbox / nella campagna);
- accanto, piccolo, **«prossimo: gio 22/10»** se il sistema ha in piano un messaggio per quel lead
  (follow-up o altro), vuoto se no.

### 2. La scheda «Clara» nel foglio
Una seconda scheda dello stesso file Google Sheets, scritta dal sistema:
- in alto un **semaforo**: verde «tutto a posto», oppure rosso con cosa si è fermato, da quando, e
  cosa sta facendo il sistema per rimettersi;
- sotto, **cosa ha fatto Clara** oggi e ieri, una riga per azione, la più recente in alto:
  analisi mandate, follow-up partiti, chi ha detto no, chi è entrato in conversazione, promemoria,
  call viste. In parole di Dre, non tecniche.
Dre l'ha scelta al posto di una pagina nelle impostazioni del Workspace («foglio»).

### 3. Una sola notifica sul telefono
**«Un lead è entrato in conversazione»** (ha risposto dopo l'analisi), col link alla scheda.
Tutte le altre notifiche di oggi si tolgono (sì da servire, prenotazioni, cose che il sistema
gestisce da solo).

### 4. Gli avvisi di guasto: rari, perché il sistema è solido
Dre: «voglio che arrivi l'avviso, ma settiamo bene le cose, non che si rompe ogni due secondi».
Un avviso parte (notifica + riga rossa nella scheda Clara) solo quando si ferma qualcosa che costa
lead o soldi:
- un sì senza analisi da più di un'ora (in orario di invio);
- l'invio fermo: crediti finiti (OpenAI, Anthropic), chiave o token scaduto, Smartlead che non
  risponde;
- un lead entrato in conversazione senza notifica partita;
- il foglio non aggiornato da più di un'ora.
Ogni avviso dice cosa sta facendo il sistema. Se un avviso suona spesso, si ripara la causa, non si
zittisce. Il resto (errori piccoli, migliorie) va al controllo del venerdì.

### 5. La scheda azienda (l'app si riduce a questa)
Le altre pagine dell'app (Oggi, Lead, Tutti, Campagne) non si toccano più. La scheda, pulita:
- chi è e come si contatta: nome, persona, **sito cliccabile**, telefono, mail, città, settore,
  campagna;
- **il prossimo messaggio di Clara**: quando e **il testo esatto**, con un pulsante per fermarlo;
- cosa ha scritto il lead e cosa gli abbiamo mandato (analisi in PDF apribile);
- lo stato in una riga; il modulo compatto, senza frasi di spiegazione («Di default…»,
  «Automatico: …», «Resta nel Workspace…»).

### 6. Pulizia (scelte di Achille, dette a Dre)
- **Niente bozze per le conversazioni**; l'arretrato della Posta (246 proposte, molte bozze di
  conversazioni) si svuota passando dal revisore.
- **Categorie automatiche su Smartlead riaccese** (spente dal 13/10 in attesa di un ok mai dato):
  sono i filtri che Dre usa in Smartlead e oggi arrivano tardi.
- **Clara intelligente** (il lettore del mattone 5 di Clara nuova) a leggere le risposte: prima in
  ombra accanto alle liste di parole, il venerdì 23 si confronta e si accende. Le liste di parole
  hanno perso 4 sì il 19/10.
- **Lettura delle mail di Dre** (l'«orecchio» Gmail, spento dal 24/9): un annullamento arrivato per
  mail (caso My Tecno, 19/10) sposta il lead e ferma il promemoria.

### 7. Il documento tecnico
Corto: questo quadro, più dove cliccare (foglio, link, scheda Clara, scheda azienda, cosa fare se
il semaforo è rosso). Aggiorna il doc «Il sistema di Studio Galilei» in Drive.

## Obiettivi, non obiettivi, cose da non fare
- Obiettivo: Dre non apre più Claude per sapere com'è andata o se qualcosa è rotto.
- Non obiettivo: nuove schermate nell'app; nuovi stati; un'altra pagina di monitoraggio.
- Da non fare: avvisi frequenti; bozze per le conversazioni; chiedere a Dre di approvare la parte
  fino all'analisi; spegnere un avviso invece di riparare la causa.

## Vincoli
- Il repository è pubblico: nel codice niente nomi o mail di lead.
- Tutto gira in cloud (GitHub Actions + Supabase); niente sul Mac.
- Le campagne Smartlead le tocca Dre: le categorie sono etichette sui lead, non modifiche alle
  campagne.

## Già deciso (dalla revisione del costruttore)
- **I follow-up partono già da soli** dal 19/10 sera (Dre: «DEVONO essere automatici»): `seguiti`
  gira senza `--ombra`; il 20/10 alle 8-9:30 ne sono partiti 38, verificati dalle routine cloud delle
  10:30 e 19:30. Il CLAUDE.md del repo va aggiornato (dice ancora «in ombra»).

## Risposte di Dre alla revisione (20/10)
- **Notifica**: chi risponde dopo l'analisi è in conversazione, punto (Dre: «se uno ha accettato
  l'analisi, noi gliela mandiamo e quella persona risponde, è in conversazione»). Ogni risposta di
  una persona dopo l'analisi fa suonare la notifica, anche un no. Le autorisposte non sono persone:
  non suonano.
- **Clara intelligente**: «accendiamola il più presto possibile, appena ci sta». Niente attesa di
  venerdì: si accende appena il rigioco sulle 1.087 risposte tiene le soglie di protezione (0 sì
  persi, 0 no letti come sì, 0 «non scrivetemi» mancati) e un giro in ombra sulle risposte vere di
  oggi non mostra errori pericolosi. Decide Achille.

## Scelte di Achille (da controllare)
- **L'arretrato della Posta si archivia, non si manda**: le bozze per conversazioni e i follow-up
  vecchi di più di 7 giorni si chiudono (stato «no», motivo scritto), passando dal poliziotto con
  prova a secco e conteggi. Nessuna mail vecchia parte in blocco.
- **Niente più proposte che aspettano Dre**: fino all'analisi il sistema manda, dopo è una
  conversazione di Dre su Smartlead. Un caso che il sistema non sa gestire (prezzo, reclamo, dubbio
  del lettore) diventa una riga gialla nella scheda Clara e, se serve una decisione, una domanda nella
  pagina «Decisioni di Dre». Mai una proposta ferma senza che nessuno la veda.
- **«Ferma questo messaggio»** ferma quel messaggio e tutti i messaggi automatici successivi a quel
  lead (il «niente follow-up» sul lead), finché il lead non riscrive. Il testo non si modifica dalla
  scheda.
- **L'orecchio Gmail** legge solo la casella di Dre e da solo fa solo una cosa: un annullamento o
  spostamento di call sposta il lead e ferma il promemoria. Il resto lo segnala nella scheda Clara.
- «Prossimo» nel foglio + testo intero nella scheda (Dre ha chiesto «app o foglio?»: risposta di
  Achille, tutte e due con compiti diversi).
- Il pulsante «ferma questo messaggio» nella scheda.
- Le soglie degli avvisi (un'ora per il sì e per il foglio).

## Cosa resta al costruttore
Come si scrive la scheda Clara (riusa la tabella `corse`, `registro`, `proposte`); dove si legge
il «prossimo messaggio» (proposte aperte/approvate e le date dei follow-up in `followup.py`);
il link al filo Smartlead (formato dell'URL della Master Inbox); come si riconosce «entrato in
conversazione» (risposta arrivata dopo `analysis_sent_at`).
