import type { Documento, Blocco } from './tono'
import { WIDGET, haAccesso, type Chiave, type Ruolo } from './widget'

// LA GUIDA DEL TUO WORKSPACE (Dre, 16/9): «in impostazioni metti anche un
// documento scaricabile su come funziona il workspace di ognuno, e nel doc
// specifichiamo che c'e' la zona feedback e che modificheremo di
// conseguenza; e spiega anche i termini nuovi della piattaforma».
//
// Non e' un manuale: e' la scheda di quella persona. Si genera adesso, con
// i widget che ha davvero in questo momento, quindi non invecchia come
// invecchia un PDF scritto a mano.

interface Chi {
  nome: string
  ruolo: Ruolo
  ruoloVero: string
  concessi: Chiave[]
}

const NOME_RUOLO: Record<string, string> = {
  ceo: 'CEO', coordinamento: 'Coordinamento', manager: 'Marketing manager',
  specialist: 'Ad specialist', frontend: 'Frontend',
}

// cosa ci fai davvero, sezione per sezione: la riga del menu dice cosa
// mostra, questa dice cosa ci vieni a fare
const COSA: Partial<Record<Chiave, string>> = {
  pipeline: 'La tua giornata, come te l\'ha preparata Clara: chi aspetta una risposta da te, le tue task, la prossima call. Si parte da qui la mattina.',
  prospect: 'Le aziende, dalla risposta alla firma. Le carte si trascinano da una colonna all\'altra: quando ne porti avanti una Clara ti chiede com\'è andata la call, e se gli appunti li ha già te li mette lì pronti.',
  progetti: 'Chi è già cliente, con i progetti: a che punto sono, chi li segue, gli accessi che mancano. Si scrive come un foglio, cella per cella.',
  calendario: 'Call, follow-up e scadenze. Le call arrivano da Google, non si ricopiano.',
  vault: 'La cassaforte: loghi, modelli, e i file di ogni cliente nella sua cartella.',
  clara: 'Quello che Clara ha preparato per te: bozze di risposta, domande, richieste. Si risponde sì o no.',
  chat: 'Dove vi passate i documenti. Trascini il file, dici di che cliente è, e Clara lo mette anche nella cartella di quel cliente.',
  preventivi: 'I documenti: proposte, report, verbali, condizioni economiche. Il "+" apre il modello già pronto, colleghi l\'azienda e Clara riempie quello che sa. Se vuoi, lo scrive lei e tu correggi.',
  analytics: 'I numeri dell\'outbound: risposte, conversioni, andamento.',
  feedback: 'Dove scrivi cosa non va, cosa vorresti, o cosa ti piacerebbe che Clara sapesse fare per te. Si legge tutto, e si cambia.',
}

// i termini della casa: quelli che a noi sembrano ovvi e per chi entra non
// lo sono (Dre, 16/9)
const PAROLE: Array<[string, string]> = [
  ['Lead', 'Un\'azienda che abbiamo contattato e che non ha ancora fatto la call tecnica. Sta nella parte alta della Pipeline.'],
  ['Prospect', 'Dalla call tecnica in poi. Da lì la trattativa è nostra da portare a casa, e la vedono tutti quelli che lavorano sulla delivery.'],
  ['SG-ID', 'Il numero di ogni azienda, per esempio SG-141. Non cambia mai: è il modo per essere sicuri di parlare della stessa azienda.'],
  ['Pedaggio', 'Quando porti avanti una carta nella Pipeline, il software ti chiede il riassunto della call. Non è burocrazia: è quello che permette a chiunque di riprendere in mano quel cliente domani.'],
  ['Pod', 'Le persone che segui tu, se sei manager. In Oggi c\'è una riga per ognuna.'],
  ['Posta di Clara', 'La cassetta delle cose che Clara propone. Lei non manda e non decide niente da sola: propone, tu dici sì o no.'],
  ['Condividi', 'La chat dei documenti. Non serve a conversare, serve a non perdere i file: ognuno resta legato al cliente.'],
  ['Widget', 'Una sezione del menu. Quelle di base le hanno tutti; le altre si chiedono da Impostazioni e te le dà chi guida lo Studio.'],
  ['Canone', 'Quanto paga un cliente al mese. Lo propone il software leggendo Stripe o l\'ultimo preventivo: basta confermarlo.'],
]

// COSA PUOI CHIEDERLE DAVVERO (Dre, 16/9): «metti anche un elenco per
// persona con esempi di casi d'uso». Solo cose che oggi fa: se non le fa,
// non stanno qui dentro, se no la prima volta che ci provano perdiamo la
// fiducia e non torna piu'.
const CASI_TUTTI: string[] = [
  '«Chi aspetta una risposta da me?» e te li elenca, dal più fermo',
  '«Ricordami giovedì di richiamare Klavzar»: nasce la task, appesa a quella azienda',
  '«Fissa una call tecnica con Verde Urbano giovedì alle 15»: prepara l\'invito, tu confermi',
  'Dopo una call, ti mette il riassunto sulla scheda del cliente senza che tu faccia niente',
]

const CASI_RUOLO: Record<string, string[]> = {
  ceo: [
    '«Scrivimi la proposta per Bimout con quello che si sono detti in call»: la scrive dentro il documento, tu correggi',
    '«Come siamo messi questa settimana?»: chi è fermo, chi aspetta, cosa si è chiuso',
    'Ogni mattina ti lascia il punto della giornata, e la sera quello che è cambiato',
  ],
  manager: [
    '«Scrivimi il verbale della call di ieri con Apiemme»: lo compila dagli appunti della call',
    '«Chi del mio pod ha roba scaduta?»: una riga per persona, senza chiederlo a loro',
    '«Manda una task ad Alex per gli accessi di Zeni entro venerdì»',
  ],
  specialist: [
    '«Ricordami il primo del mese di rifare il budget di Klavzar»: torna ogni mese, non te lo devi ricordare',
    '«Preparami il report mensile di Serenergy»: parte dal modello e dai numeri che ci sono',
    '«Questa campagna è ferma da quanto?»',
  ],
  frontend: [
    '«Scrivi tu a Zeni che mancano gli accessi all\'hosting»: prepara la mail, tu la mandi con un clic',
    '«Segna che il sito di Tecnolegno è andato online oggi»',
    '«Cosa manca per chiudere il progetto di Bimout?»',
  ],
  coordinamento: [
    '«Ho appena parlato con questa azienda su LinkedIn»: te la aggiunge e ci appende la nota',
    '«Chi mi ha risposto e non ho ancora ripreso in mano?»',
    '«Prepara la risposta a CER Italia»: scrive la bozza, tu leggi e mandi',
  ],
}

export function guidaDi(chi: Chi): Documento {
  const concessi = new Set(chi.concessi)
  const miei = WIDGET.filter((w) => haAccesso(w, chi.ruolo, concessi))
  const non = WIDGET.filter((w) => !haAccesso(w, chi.ruolo, concessi))
  const oggi = new Date()

  const b: Blocco[] = []

  b.push({ tipo: 'h2', testo: 'Come si entra' })
  b.push({ tipo: 'p', testo: 'Si va su studiogalilei.github.io/clara e si entra con Google, con la mail dello Studio. La prima volta Google mostra una lista di permessi con delle caselle: vanno spuntate tutte. Servono perché il Workspace legge il calendario, gli appunti delle call e la posta di lavoro, e da lì tiene aggiornate le schede da solo. Sul telefono conviene metterlo nella schermata Home: si apre come un\'app.' })

  b.push({ tipo: 'h2', testo: 'Cosa ci trovi tu' })
  b.push({
    tipo: 'tabella',
    colonne: [{ testo: 'Dove', larghezza: 26 }, { testo: 'Cosa ci fai', larghezza: 74 }],
    righe: miei.map((w) => [{ testo: w.nome, forte: true }, { testo: COSA[w.chiave] ?? w.cosa }]),
  })

  if (non.length) {
    b.push({ tipo: 'h2', testo: 'Quello che non hai' })
    b.push({ tipo: 'p', testo: `Per ora non vedi ${non.map((w) => w.nome).join(', ')}. Non è una porta chiusa: si chiede da Impostazioni, nella parte dei widget, e chi guida lo Studio te lo dà con un clic. Se ti serve per lavorare, chiedilo.` })
  }

  b.push({ tipo: 'h2', testo: 'Clara' })
  b.push({ tipo: 'p', testo: 'È la tua assistente, e sta nella pallina in basso a destra. Legge il calendario, gli appunti delle call e la posta di lavoro, tiene in ordine le schede al posto tuo, ti prepara le bozze di risposta e ti avvisa se qualcuno è fermo da troppo tempo. Non manda niente e non decide niente da sola: ti propone, e tu le dici sì o no dalla sua Posta. Quando la pallina rimbalza, ha qualcosa per te.' })

  b.push({ tipo: 'h2', testo: 'Cosa puoi chiederle, per davvero' })
  b.push({ tipo: 'p', testo: 'Si scrive nella chat della pallina, come si scriverebbe a una persona. Queste le fa già oggi:' })
  b.push({ tipo: 'elenco', voci: [...(CASI_RUOLO[chi.ruoloVero] ?? CASI_RUOLO.coordinamento), ...CASI_TUTTI] })
  b.push({ tipo: 'p', piccolo: true, testo: 'Quando non è sicura non tira a indovinare: te lo chiede e aspetta. E qualunque cosa cambi una scheda passa sempre da un tuo sì.' })

  b.push({ tipo: 'h2', testo: 'Le parole che usiamo qui' })
  b.push({
    tipo: 'tabella',
    colonne: [{ testo: 'Parola', larghezza: 22 }, { testo: 'Cosa vuol dire', larghezza: 78 }],
    righe: PAROLE.map(([p, q]) => [{ testo: p, forte: true }, { testo: q }]),
  })

  b.push({ tipo: 'h2', testo: 'Due regole di casa' })
  b.push({
    tipo: 'elenco',
    voci: [
      'Tutto si appende all\'azienda: una nota, un documento, una task. Se lo appendi lì lo ritrova chiunque; se resta sul telefono, è perso.',
      'Quello che vedi è la verità di oggi, calcolata dai dati, non un\'etichetta che qualcuno deve ricordarsi di aggiornare. Se una carta dice una cosa che non ti torna, è un errore nostro: segnalalo.',
    ],
  })

  b.push({ tipo: 'h2', testo: 'Questa è una beta, e serve la tua testa' })
  b.push({ tipo: 'p', testo: 'Nel menu c\'è «Cosa cambieresti». Scrivi lì qualunque cosa: un bottone nel posto sbagliato, un giro troppo lungo, una cosa che non funziona, o una cosa che vorresti che Clara imparasse a fare per te. Anche minima, anche una virgola. Si legge tutto e si cambia: questo posto lo stiamo costruendo su come lavorate voi, non il contrario.' })
  b.push({ tipo: 'riquadro', titolo: 'A COSA SERVE', voci: [
    'Meno tempo su dove sta una cosa, più tempo sui clienti',
    'Quello che sai tu resta allo Studio anche quando non ci sei',
    'Nessuno deve più chiedere «a che punto siamo con questo cliente»',
  ] })

  return {
    tipo: 'SG Workspace',
    copertina: {
      linea: 'istituzionale',
      occhiello: 'SG Workspace, beta',
      titolo: `La guida di ${chi.nome}`,
      sottotitolo: 'Cosa vedi, cosa ci fai, e cosa ci serve da te',
      cliente: NOME_RUOLO[chi.ruoloVero] ?? undefined,
      data: oggi.toLocaleDateString('it-IT', { month: 'long', year: 'numeric' }),
    },
    blocchi: b,
    piede: oggi.toLocaleDateString('it-IT', { day: 'numeric', month: 'long', year: 'numeric' }),
  }
}
