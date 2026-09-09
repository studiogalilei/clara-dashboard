---
name: design-dashboard
description: Come si disegna una schermata della Clara Dashboard di Studio Galilei. Da leggere PRIMA di creare o rifare qualunque componente, pagina o widget della dashboard (src/components), e da rifinire a ogni bocciatura di Dre (sezione «Rifinitura»).
---

# Design della Clara Dashboard

Idea presa dal metodo di Chad (video del 9/9): non prompt migliori, ma una
skill che si rifinisce a ogni feedback. Ogni «fa cagare» di Dre diventa una
riga nella sezione Rifinitura, con problema → causa → regola. Le schermate
nuove nascono gia' con tutte le regole dentro.

## Chi la usa

Dre (CEO, non tecnico, la usa dal Mac e dal telefono), Giacomo (coordina,
vive nel suo excel: vuole tabelle dense e contesto completo in ogni cella),
Carlo (delivery, vuole vedere solo il suo), Lorenzo (outbound LinkedIn),
Okay, Alex. Ognuno apre la sua pagina e deve capire in tre secondi cosa
fare adesso.

## Il brand (STUDIOGALILEI_BRAND_DIRECTIVES_v2)

- Colori: nero `#000000`, navy `#1C2E6E` (in tailwind `navy`), blu `#2979C4`
  (`blu`), avorio `#FAF8F4`. Niente gradienti, niente ombre pesanti, niente
  grigi neutri: i «grigi» sono `velo`, `bordo`, `tenue`, `spento` del tema.
- Font: Plus Jakarta Sans. Titoli in extrabold, corpo 14px, etichette 11px
  uppercase con tracking.
- Logo di Clara (`ClaraLogo`) in alto nel menu; l'albero di Studio Galilei
  accanto al nome dell'utente in basso.
- Carte morbide (`Card`): bordo `bordo`, raggio xl, fondo bianco. Una carta =
  un oggetto. Non tutto e' una carta: liste dense dentro una carta sola.

## Le regole di Dre (imparate sul campo)

1. **Titoli puliti.** «Progetti», non «I suoi progetti». Niente possessivi,
   niente frasi come titolo. (4/9)
2. **Niente didascalie.** Nessun testo che spiega la schermata all'utente.
   Se serve spiegare, la schermata e' sbagliata. (regola anti-didascalie)
3. **Numeri solo se decidono qualcosa.** Le file di numeri in cima alla home
   erano «numeri inutili»: via. Un numero sta in alto solo se cambia cosa fai
   oggi. (7/9)
4. **La giornata, per davvero.** La home dice cosa aspetta te: bozze da
   approvare, domande di Clara, call di oggi, task in scadenza. Ogni riga
   porta dove si agisce. (7/9)
5. **Una verita', piu' viste.** Bacheca, elenco, foglio: stessi dati da
   `src/lib/regole.ts`. Mai tre numeri diversi per la stessa domanda.
6. **Clara propone, Dre dispone.** Ogni cosa che Clara vuole fare e' una
   proposta con si'/no; niente scritture silenziose. Le proposte stanno nella
   posta (bustina), non in mezzo alla pagina.
7. **Il foglio, non il form.** Dove Giacomo usa un excel, la schermata e' una
   tabella con celle scrivibili e selettori colorati (Trial giallo, Retainer
   verde, onboarding azzurro), non un modulo con i campi in colonna. (8/9)
8. **Ogni cosa appesa all'SG-ID.** Progetti, call, task, preventivi: tutti
   con il cliente davanti, «SG-1481 · Dän Ink». L'ID non cambia mai. (9/9)
9. **Silenzioso di lato.** Quello che arriva dagli altri (task in arrivo,
   mandate) sta in una colonna stretta a destra, non in mezzo alla lista: le
   persone devono restare sulle proprie task. Vuoto = una riga. (9/9)
10. **Niente oltre 30 giorni** in vista, se non sbiadito o richiudibile
    (regola di Giacomo).
11. **Mobile prima o poi, sempre.** Ogni schermata deve reggere a 390px:
    colonne che vanno sotto, tabelle che scorrono dentro il loro contenitore,
    bottone «+» in basso. Il menu passa in alto sul telefono.
12. **Resizable.** Menu e pannello di Clara si allargano col divisorio, come
    Claude. Nessun `max-w` fisso che spreca lo schermo (7/9).
13. **Testi: italiano informale, secchi.** «Accetta», «Rimanda», «+ Riga».
    Niente «Clicca qui per…», niente emoji decorative, niente trattino lungo.


## Apple e Google, assorbiti (9/9)

Dre: «Google semplifica le cose, Apple fa diventare bello il fatto di
lavorare». Letti dal vivo Apple HIG (layout, tipografia, colore, liste e
tabelle, sidebar, toolbar, scrittura, macOS, iOS) e Material 3 (layout,
breakpoint, tipografia, ruoli colore, stati, motion). Il testo integrale sta
in `riferimenti/`. Quello che vale per noi, in regole:

**Da Apple: chiarezza, deferenza, profondita'.**
- Raggruppa con lo spazio prima che con le linee. Spazio vuoto, sfondi
  leggeri, separatori sottili: mai tutte e tre le cose insieme. Contenuto e
  controlli devono restare distinti.
- L'informazione essenziale ha spazio; il secondario va altrove (dettaglio,
  scheda, disclosure), non nella stessa riga. Ordine di lettura: alto e
  sinistra sono i posti importanti.
- Allinea tutto: l'allineamento e' la gerarchia che non si vede.
- Disclosure progressiva: se non ci sta tutto, mostra che c'e' altro
  (freccina, riga che continua), non tutto piu' piccolo.
- Controlli con aria intorno e in gruppi logici; mai due controlli estranei
  vicini. Sul Mac niente di critico in fondo alla finestra.
- Tipografia: un typeface (Plus Jakarta), pesi Regular/Medium/Semibold/Bold,
  mai Light. Default 13-14px, minimo 11px, e i titoli fanno la gerarchia con
  peso e colore prima che con la dimensione.
- Colore: lo stesso colore vuol dire sempre la stessa cosa. Il navy e' solo
  «interattivo o attivo»: non si usa per decorare testo non cliccabile. Il
  colore non e' mai l'unico segnale (etichetta o forma accanto).
- Tabelle: testo corto nelle righe, intestazioni con nomi (niente frasi),
  sul Mac colonne ridimensionabili e ordinabili cliccando l'intestazione,
  righe alternate solo se la tabella e' larga. Selezione persistente quando
  la riga apre qualcosa.
- Sidebar: massimo due livelli, etichette secche, icone di un colore solo
  (l'accento), nascondibile. Niente di critico in fondo.
- Scrittura: verbi sui bottoni («Manda», non «Fatto!»), niente possessivi
  («Progetti», non «I tuoi progetti»), niente «noi», errori vicino al campo e
  che dicono cosa fare («Scegli una data» non «Data non valida»), stati vuoti
  con il passo successivo e un bottone, niente «oops».
- iPhone: default 17px, tocco 44px, niente bottoni a tutta larghezza
  incollati ai bordi, la barra di stato resta.

**Da Google: struttura, ruoli, breakpoint.**
- Layout a pannelli: uno sul telefono (< 600), due dal desktop (840-1199),
  tre solo sopra i 1600. Per noi: telefono = un pannello e menu in basso;
  desktop = menu + contenuto (+ pannello di Clara). Le tabelle dense non si
  dividono mai in due pannelli sul medio.
- Passando da uno schermo all'altro ci si chiede: cosa si rivela, come si
  divide, cosa si ridimensiona, cosa si sposta, cosa si scambia. Mai
  «la stessa cosa piu' grande».
- Testo fra 40 e 60 caratteri per riga; numeri tabulari ovunque si
  allineano; interlinea 1.2 sui titoli, 1.5 sul corpo.
- Ruoli di colore, non colori: `primary` (navy) per l'azione che conta,
  `secondary` per chip e selezioni, `tertiary` per badge e avvisi piccoli,
  `error`, `surface` e `outline`. Ogni colore ha il suo «on» (testo sopra)
  con contrasto 4.5:1 (3:1 per testo grande). Contenitori tonali (verde
  chiaro / testo verde scuro) per gli stati: e' il pattern delle pillole.
- Stati, sempre e uguali ovunque: enabled, disabled, hover, focused, pressed,
  dragged; due indicatori visivi per stato (colore + qualcos'altro).
- Motion: «standard», niente rimbalzi. 120-250 ms, ease-out in entrata,
  ease-in in uscita; il movimento spiega da dove viene una cosa.
- Tipo in cinque ruoli: display (mai qui), headline (titolo pagina 26px),
  title (carte, 15-16px semibold), body (14px), label (11-12px per chip,
  bottoni, intestazioni di tabella).

**Le tre frasi da tenere a mente**
1. Ogni schermata risponde a una domanda sola, e la risposta sta in alto a
   sinistra.
2. Lo spazio bianco e' un materiale: si compra togliendo, non aggiungendo.
3. Se serve una didascalia per capire un controllo, il controllo e' sbagliato.


## L'intervista a Dre (9/9): le sue risposte, che valgono come specifica

- Sensazione al mattino: **calma e controllo** (Apple Notes/Calendar/Reminders
  e' il riferimento del «bello»). Non cabina di regia, non to-do.
- Densita' tabelle: **ariosa**, righe 48-52px, poche colonne, molto bianco.
- Colore: **bianco e nero, dettagli in blu SG**. Il blu sta su: bottone
  principale (uno per pagina), titoli e intestazioni. Gli stati con pillole
  tonali (verde cliente, azzurro preventivo, ambra prospect, grigio perso).
  Due blu del brand: navy `#1C2E6E` per titoli e testo importante, blu
  `#2979C4` per bottoni e link. Niente altro colore.
- Superfici: carte bianche su fondo chiarissimo, bordi sottili, nessuna
  ombra. Angoli **arrotondati Apple** (12-16px carte, 10px bottoni, pillole).
- Testo **piu' grande**: corpo 15px, righe 48px, titolo pagina 28px.
- Menu: a sinistra, testo e icone, come ora. **Cinque voci**: Oggi · Aziende ·
  Progetti · Calendario · Clara. Aziende = Pipeline + Tutti + Preventivi
  (tab). Task dentro Oggi. Numeri e Widget e istruzioni finiscono sotto
  Impostazioni.
- Orientamento: **briciole e ‹ Torna** sempre in alto; meno pagine.
- Home (Oggi): **sopra le cose che aspettano me**, sotto le mie task; a
  destra In arrivo e Mandate.
- Celle: **click e scrivi, salva da solo** (Sheets).
- Apertura azienda: **pannello a lato** che scivola da destra; in alto **chi
  e' e come contattarlo**, poi la storia.
- Fasi: **bacheca a colonne, trascinando** (col pedaggio del transcript).
- Clara: **pannello a destra sempre aperto, 320px, apre sulla posta**; la
  chat sotto, si espande quando scrivi.
- Telefono: approvare bozze e proposte, vedere la giornata, scrivere task
  e note. **Barra in basso con 5 icone**.
- Fastidi di oggi: «brutto da vedere» e «non capisco dove sono».

## Come si costruisce una schermata nuova

1. Dire in una riga chi la apre e cosa deve decidere in tre secondi.
2. Scegliere la forma: lista (cose da fare), foglio (Giacomo), bacheca
   (fasi), timeline (tempo). Una sola.
3. Componenti esistenti prima: `Card`, `TitoloCard`, `Micro`, `Spinner`,
   `Cella` (foglio), `SceltaCliente`, `Timeline`.
4. Stato vuoto = una riga secca, mai una spiegazione.
5. Provarla in demo (`?demo`) a 1200px e a 390px prima di mostrarla.

## Rifinitura (si aggiorna a ogni bocciatura)

Formato: data · cosa ha detto Dre · problema · causa · regola.

- 7/9 · «quei numeri sono inutili» · la home apriva con quattro tessere
  numeriche · avevo copiato il pattern «dashboard = KPI in alto» · regola 3.
- 7/9 · «non 'I suoi progetti' ma 'Progetti'» · titoli con possessivo ·
  linguaggio da assistente che parla all'utente · regola 1.
- 7/9 · «lo schermo fa cagare, la chat di Clara con le proposte in mezzo» ·
  proposte mischiate ai messaggi · due cose diverse nello stesso flusso ·
  bustina separata, regola 6.
- 7/9 · «la sezione calendario si vede male» · griglia larga quanto lo
  schermo che finiva sotto il menu · `w-screen` con margine negativo ·
  regola 12, niente trucchi di larghezza.
- 9/9 · «falla meno invasiva, le persone devono essere focus sulle proprie
  task» · le task in arrivo stavano sopra la lista · avevo dato priorita'
  visiva a cio' che arriva · regola 9.
- 9/9 · «fa tanto cagare la UI/UX» · tutto uguale, due file di pillole,
  celle piene di segnaposto, select nativi, bordi verticali da Excel ·
  avevo costruito «un form che sembra un foglio» senza gerarchia · titolo
  grande + tab sotto, filtri con i conteggi, vuoto = trattino, pillole
  colorate custom, solo righe orizzontali, piede coi tre numeri.
- 9/9 · «c'e' ancora confusione, e il codice e' brutto da vedere» · SG-ID in
  monospazio davanti a ogni nome · avevo mostrato un identificatore tecnico
  come contenuto · la «foto» con le due cifre sul colore di fase, l'ID
  intero solo al passaggio del mouse e nella scheda; meno filtri, una
  colonna preventivo sola.
