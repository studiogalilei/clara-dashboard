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
La pallina in basso a destra. Prepara bozze, segnala anomalie, tiene in ordine le schede.
**Non manda niente e non decide niente da sola**: propone, e la persona decide.

**Due regole di casa**
1. Tutto si appende all'azienda: nota, documento, task.
2. Quello che vedi è la verità di oggi, calcolata dai dati, non un'etichetta scritta a mano.
   Se dice una cosa sbagliata, è un errore del sistema: si sistema.

**Questa è una beta, e serve la tua testa**
Nel menu c'è **Cosa cambieresti**. Da te servono soprattutto due tipi di segnalazione: le cose
rotte (con cosa stavi facendo quando è successo) e le cose che un sistemista vorrebbe vedere
e non ci sono: un allarme quando una sincronizzazione fallisce, un posto dove leggere i log,
qualunque cosa. Scrivila lì, anche minima.
