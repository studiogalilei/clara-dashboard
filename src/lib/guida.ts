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
  pipeline: 'La tua giornata: chi aspetta una risposta da te, le tue task, la prossima call. Si parte da qui la mattina.',
  prospect: 'Le aziende, dalla risposta alla firma. Le carte si trascinano da una colonna all\'altra: portandole avanti ti chiede il riassunto della call, e se gli appunti esistono già te li propone.',
  progetti: 'Chi è già cliente, con i progetti: a che punto sono, chi li segue, gli accessi che mancano. Si scrive come un foglio, cella per cella.',
  calendario: 'Call, follow-up e scadenze. Le call arrivano da Google, non si ricopiano.',
  vault: 'La cassaforte: loghi, modelli, e i file di ogni cliente nella sua cartella.',
  clara: 'Quello che Clara ha preparato per te: bozze di risposta, domande, richieste. Si risponde sì o no.',
  chat: 'Dove ci passiamo i documenti. Trascini il file, dici di che cliente è, e resta trovabile per sempre.',
  preventivi: 'I documenti: proposte, report, verbali, condizioni economiche. Il "+" apre il modello già pronto e l\'azienda si collega con un clic.',
  analytics: 'I numeri dell\'outbound: risposte, conversioni, andamento.',
  feedback: 'Dove scrivi cosa non va o cosa vorresti. Si legge tutto, e le cose scomode si cambiano.',
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
  b.push({ tipo: 'p', testo: 'È la pallina in basso a destra. Legge il calendario, gli appunti delle call e la posta di lavoro, tiene aggiornate le schede, prepara le bozze di risposta e segnala chi è fermo da troppo tempo. Non manda niente e non decide niente da sola: propone, e tu rispondi dalla sua Posta. Quando la pallina rimbalza, ha qualcosa per te.' })

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
  b.push({ tipo: 'p', testo: 'Nel menu c\'è «Cosa cambieresti». Scrivi lì qualunque cosa: un bottone nel posto sbagliato, un giro troppo lungo, una cosa che non funziona, o una che non c\'è e ti farebbe comodo. Anche minima, anche una virgola. Si legge tutto e si cambia: lo strumento serve a farvi lavorare meglio, non il contrario.' })
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
