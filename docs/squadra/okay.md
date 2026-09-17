# SG Workspace, la scheda di Okay

**Come entri**
https://studiogalilei.github.io/clara/ e poi «Entra con Google», con la mail @studiogalilei.com.
La prima volta Google ti mostra una lista di permessi con delle caselle: **spuntale tutte**
(in alto c'è «Seleziona tutto»). Servono perché il Workspace lavora a nome tuo su calendario,
Drive e posta. Mettilo sulla schermata Home del telefono: si apre come un'app.

**Cos'è**
Il posto dove sta il lavoro di tutti i giorni, e sotto c'è un sistema che gira da solo:
letture del calendario, della posta e degli appunti delle call, sincronizzazioni, backup.
Tu sei quello che deve poter vedere se sta girando bene, non solo usarlo.

**Cosa vedi tu, e perché**

*Impostazioni → Widget e istruzioni*: la sala macchine. Trovi:
- **Operazioni**: tutto quello che gira da solo, con l'ultima volta che è partito, l'esito, e
  un interruttore acceso/spento. In cloud, ogni quarto d'ora, un runner fa partire quelle
  dovute.
- **Collegamenti**: Supabase, Smartlead, OpenAI, GitHub, Google Ads, Calendar, Drive, con lo
  stato di ognuno.
- **Istruzioni a Clara**: le regole che legge prima di ogni cosa, e valgono subito.

*Impostazioni → Salute dei dati*: le incoerenze fra tabelle: clienti con un canone diverso
da quello che incassa Stripe, progetti senza cliente collegato, proposte ferme da giorni.
Sono esattamente le cose che altrimenti si scoprono solo leggendo il database a mano.

*Clienti, Pipeline, Oggi, Calendario, Documenti, Condividi*: il lavoro normale, come per
tutti gli altri.

**Una cosa da sapere**
Il software lo passeremo a te: è React con Vite, il database è Supabase (Postgres con RLS,
quindi i permessi stanno nel database e non nel codice), i lavori automatici sono script
Python fatti partire da GitHub Actions. Ogni cosa che gira ha una riga nella tabella
`operazioni` e un comando dietro: non ci sono lavori nascosti da qualche parte.

**Clara**
È la tua assistente, e sta nella pallina in basso a destra. Legge il calendario, gli appunti
delle call e la posta di lavoro, tiene in ordine le schede al posto tuo, ti prepara le bozze
di risposta e ti avvisa se qualcuno è fermo da troppo. Prima di ogni call ti lascia il punto
della situazione sulla call stessa, in Oggi: chi sono, a che punto siamo, cosa chiedere. E
tiene d'occhio le cose che si dimenticano (il preventivo senza risposta, i soldi che non
arrivano, la prova che scade) e te le ricorda lei. **Non manda niente e non decide niente da
sola**: ti propone, e tu le dici sì o no dalla sua Posta. Le puoi anche scrivere come a una
persona: «ricordami giovedì di richiamare Klavzar», oppure «fammi un piano per Klavzar» e lei mette
in fila le cose da fare giorno per giorno, che con un clic diventano task. Se la pallina rimbalza,
ha qualcosa per te.

**Due regole di casa**
1. Tutto si appende all'azienda: nota, documento, task.
2. Quello che vedi è la verità di oggi, calcolata dai dati, non un'etichetta scritta a mano.
   Se dice una cosa sbagliata, è un errore del sistema: si sistema.

**Il primo giorno**
Al primo accesso parte da solo un giro guidato di due minuti che ti fa vedere dov'è cosa.
Si salta quando vuoi e si rifà da Impostazioni. Sempre in Impostazioni, sotto «Il tuo
Workspace», c'è la tua guida da scaricare: le tue sezioni, le parole che usiamo qui dentro e
un elenco di cose che puoi chiedere a Clara.

Nel menu c'è **Cosa cambieresti**: un bottone nel posto sbagliato, un giro troppo lungo, una
cosa che non funziona, o una cosa che vorresti che Clara sapesse fare per te. Anche minima.
Si legge tutto e si cambia: questo posto lo stiamo costruendo su come lavorate voi.
