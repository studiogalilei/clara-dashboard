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
