import { euroTesto, type Documento, type Blocco } from './tono'

// LE CONDIZIONI ECONOMICHE: il documento formale dello Studio, puro (senza
// database): lo usano il widget Preventivi e lo script dei modelli.

export type Ricorrenza = 'una_tantum' | 'mese'
export interface Voce {
  nome: string
  descrizione?: string
  quantita: number
  prezzo: number
  ricorrenza: Ricorrenza
}
export interface Fatturazione { ragione?: string; indirizzo?: string; piva?: string; pec?: string; sdi?: string }

// I DATI DELLO STUDIO (15/9): un documento da firmare ha due parti, non una.
// Si scrivono una volta in Impostazioni e stanno in istruzioni, chiave «studio».
export interface DatiStudio {
  ragione?: string
  indirizzo?: string
  piva?: string
  pec?: string
  iban?: string
  iva?: number          // aliquota, in percentuale
  giorni?: number       // termini di pagamento
  preavviso?: number    // giorni di preavviso per fermare il ricorrente
  foro?: string
  firmatario?: string   // chi firma per lo Studio
}
export const STUDIO_VUOTO: DatiStudio = { iva: 22, giorni: 15, preavviso: 30 }

export function mancaStudio(d: DatiStudio): string[] {
  const buchi: string[] = []
  if (!d.ragione?.trim()) buchi.push('la ragione sociale dello Studio')
  if (!d.piva?.trim()) buchi.push('la partita IVA dello Studio')
  if (!d.indirizzo?.trim()) buchi.push('la sede dello Studio')
  return buchi
}
export const unaTantum = (voci: Voce[]) => voci.filter((v) => v.ricorrenza === 'una_tantum').reduce((t, v) => t + v.quantita * v.prezzo, 0)
export const alMese = (voci: Voce[]) => voci.filter((v) => v.ricorrenza === 'mese').reduce((t, v) => t + v.quantita * v.prezzo, 0)
export const ePilota = (v: Voce) => /pilota|prova/i.test(v.nome)
const dataLunga = (iso: string) => new Date(iso + 'T12:00:00').toLocaleDateString('it-IT', { day: 'numeric', month: 'long', year: 'numeric' })

// IL DOCUMENTO: «Condizioni economiche», il testo ufficiale dello Studio
// (sg-condizioni-modello): non si modifica il testo, si cambiano i dati.
// cosa manca per mandarlo al cliente: il documento e' intestato, non un listino
export function cosaManca(f: Fatturazione): string[] {
  const buchi: string[] = []
  if (!f.ragione?.trim()) buchi.push('la ragione sociale')
  if (!f.piva?.trim()) buchi.push('la partita IVA')
  if (!f.indirizzo?.trim()) buchi.push('l\'indirizzo')
  return buchi
}

// cosa e' incluso e cosa sta a parte, per linea: un preventivo per un sito non
// puo' dire che il sito e' escluso (QA Giacomo, 14/9)
const INCLUSO: Record<string, { incluso: string[]; parte: string[] }> = {
  marketing: {
    incluso: ['Analisi iniziale e impostazione del sistema', 'Gestione operativa e lavoro sui dati', 'Report periodici con metodo di calcolo dichiarato', 'Call di allineamento regolari', 'Un referente che risponde del progetto'],
    parte: ['Budget pubblicitario, che resta sui vostri account', 'Licenze di strumenti terzi, se ne servono', 'Produzione video e fotografica sul posto', 'Sviluppo software su misura, che ha un suo preventivo'],
  },
  software: {
    incluso: ['Analisi di quello che vi serve e progettazione', 'Sviluppo, prove e pubblicazione', 'Tracciamento impostato e verificato', 'Un referente che risponde del progetto', 'Il codice e i contenuti restano vostri'],
    parte: ['Dominio e hosting, intestati a voi', 'Licenze di temi, moduli o strumenti terzi', 'Produzione di testi, foto e video', 'Gestione delle campagne, che ha un suo preventivo'],
  },
  ai: {
    incluso: ['Mappatura del processo che si automatizza', 'Costruzione, prove e messa in funzione', 'Istruzioni scritte per chi lo usa ogni giorno', 'Un referente che risponde del progetto'],
    parte: ['Licenze e consumi degli strumenti terzi, intestati a voi', 'I dati e gli accessi, che restano vostri', 'Sviluppo software su misura, che ha un suo preventivo'],
  },
}

export function documentoDi(q: { voci: Voce[]; valido_fino: string | null; numero: string | null }, azienda: string, f: Fatturazione, linea: string = 'marketing', studio: DatiStudio = STUDIO_VUOTO): Documento {
  const pilota = q.voci.find(ePilota)
  const mensili = q.voci.filter((v) => v.ricorrenza === 'mese')
  const unaTantumTot = unaTantum(q.voci)
  const meseTot = alMese(q.voci)
  const oggi = new Date()
  const b: Blocco[] = []
  b.push({ tipo: 'kicker', testo: 'Condizioni economiche' })
  b.push({ tipo: 'h1', testo: azienda })
  b.push({ tipo: 'anagrafica', colonne: [
    { titolo: 'Intestatario', righe: [f.ragione || azienda, ...(f.indirizzo ? [f.indirizzo] : []), ...(f.piva ? [`Partita IVA ${f.piva}`] : []), ...(f.pec ? [`PEC ${f.pec}`] : []), ...(f.sdi ? [`Codice SDI ${f.sdi}`] : [])] },
    { titolo: 'Fornitore', righe: [studio.ragione || 'Studio Galilei', ...(studio.indirizzo ? [studio.indirizzo] : []), ...(studio.piva ? [`Partita IVA ${studio.piva}`] : []), ...(studio.pec ? [`PEC ${studio.pec}`] : [])] },
    { titolo: 'Riferimento', righe: [q.numero ?? '', oggi.toLocaleDateString('it-IT', { day: 'numeric', month: 'long', year: 'numeric' })] },
  ] })

  if (pilota && mensili.length) {
    b.push({ tipo: 'h2', testo: 'Come si struttura il rapporto' })
    b.push({ tipo: 'p', testo: 'Non si parte con un contratto annuale. Si comincia con due mesi di lavoro reale, poi si decide insieme se ha senso continuare.' })
    b.push({ tipo: 'p', testo: 'Questa formula la proponiamo a chi ha in mente un percorso di lungo periodo: serve a costruire fiducia all\'inizio, non a coprire due mesi di lavoro e basta.' })
    b.push({ tipo: 'tappe', tappe: [
      { quando: 'Mesi 1 e 2', titolo: 'Fase pilota', testo: 'Due mesi per conoscerci davvero: come lavoriamo, come vi trovate con noi e se ci sono le basi per costruire qualcosa di lungo periodo. Il lavoro parte subito, ma la decisione resta aperta.' },
      { quando: 'Fine mese 2', titolo: 'La scelta è vostra', testo: 'Se il percorso convince si passa al lavoro continuativo. Altrimenti potete semplicemente non proseguire.' },
      { quando: 'Dal mese 3', titolo: 'Lavoro continuativo', testo: 'Canone mensile con pagamenti ricorrenti su Stripe, e il lavoro prosegue finché ha senso per entrambi.' },
    ] })
  }

  b.push({ tipo: 'h2', testo: mensili.length ? 'I momenti economici' : 'Cosa proponiamo' })
  const righe = q.voci.map((v) => {
    const tot = v.quantita * v.prezzo
    const come = v.ricorrenza === 'mese'
      ? 'Addebito ricorrente su Stripe, ogni mese. La durata si concorda insieme in base alla strategia scelta.'
      : ePilota(v) ? 'In anticipo alla firma, in un\'unica soluzione. Resta interamente rimborsabile fino alla fine del secondo mese.'
      : 'Alla firma, in un\'unica soluzione, con il link di pagamento che vi mandiamo.'
    return [
      { testo: v.nome, sotto: [v.descrizione, v.quantita > 1 ? `${v.quantita} unità` : ''].filter(Boolean).join(', ') || undefined, forte: true },
      { testo: euroTesto(tot), sotto: v.ricorrenza === 'mese' ? 'al mese' : 'in totale' },
      { testo: come },
    ]
  })
  b.push({ tipo: 'tabella', colonne: [{ testo: 'Voce', larghezza: 34 }, { testo: 'Importo', larghezza: 20, destra: true }, { testo: 'Come si paga', larghezza: 46 }], righe })
  const totali: string[] = []
  if (unaTantumTot) totali.push(`${euroTesto(unaTantumTot)} alla firma`)
  if (meseTot) totali.push(`${euroTesto(meseTot)} al mese dal ${pilota ? 'terzo mese' : 'primo mese'}`)
  const iva = studio.iva ?? 22
  const conIva = (n: number) => euroTesto(n * (1 + iva / 100))
  if (totali.length) b.push({ tipo: 'p', testo: `In tutto: ${totali.join(', ')}, IVA esclusa.` })
  if (unaTantumTot || meseTot) {
    const righeIva: Array<Array<{ testo: string; sotto?: string; forte?: boolean }>> = []
    if (unaTantumTot) righeIva.push([{ testo: 'Alla firma', forte: true }, { testo: euroTesto(unaTantumTot) }, { testo: euroTesto(unaTantumTot * iva / 100) }, { testo: conIva(unaTantumTot), forte: true }])
    if (meseTot) righeIva.push([{ testo: 'Ogni mese', forte: true }, { testo: euroTesto(meseTot) }, { testo: euroTesto(meseTot * iva / 100) }, { testo: conIva(meseTot), forte: true }])
    b.push({ tipo: 'tabella', colonne: [
      { testo: 'Quando', larghezza: 28 }, { testo: 'Imponibile', larghezza: 24, destra: true },
      { testo: `IVA ${iva}%`, larghezza: 24, destra: true }, { testo: 'Totale', larghezza: 24, destra: true },
    ], righe: righeIva })
  }
  b.push({ tipo: 'p', piccolo: true, testo: `Il pagamento avviene entro ${studio.giorni ?? 15} giorni dalla fattura${studio.iban ? `, con bonifico su ${studio.iban}` : ''}, oppure con il link di pagamento che vi mandiamo. Il budget pubblicitario, quando previsto, è a parte: si definisce insieme e resta sui vostri account.` })
  if (q.valido_fino) b.push({ tipo: 'p', piccolo: true, testo: `Queste condizioni valgono fino al ${dataLunga(q.valido_fino)}.` })

  b.push({ tipo: 'pagina' })
  if (pilota) {
    b.push({ tipo: 'kicker', testo: 'Garanzia' })
    b.push({ tipo: 'h2', testo: 'Il rischio del primo passo resta nostro' })
    b.push({ tipo: 'p', testo: `Quello che ferma la maggior parte delle aziende non è il budget: è l'esperienza precedente con fornitori spariti dopo la firma. Per questo i ${euroTesto(pilota.quantita * pilota.prezzo)} del pilota restano rimborsabili fino alla fine del secondo mese.` })
    b.push({ tipo: 'riquadro', titolo: 'Due cose distinte', voci: [
      'Alla fine dei due mesi guardiamo insieme com\'è andata',
      'Proseguire o no è una vostra scelta, e non richiede motivazioni',
      'Il rimborso è un\'altra cosa: se il lavoro non vi ha convinto, lo chiedete per iscritto entro 15 giorni dalla fine del secondo mese e ve lo restituiamo per intero entro 15 giorni dalla richiesta',
      'Il budget pubblicitario speso sulle piattaforme non rientra nel rimborso: è denaro andato a Google o a Meta, non a noi',
      'Quello che abbiamo costruito resta vostro in ogni caso',
    ] })
    b.push({ tipo: 'p', piccolo: true, testo: 'La garanzia esiste perché nessuno debba fidarsi sulla parola. Nella pratica chi si ferma lo fa quasi sempre per ragioni che con il lavoro svolto non c\'entrano, e in quel caso il rimborso non si pone.' })
  }
  b.push({ tipo: 'h2', testo: 'Cosa è incluso e cosa no' })
  const liste = INCLUSO[linea] ?? INCLUSO.marketing
  b.push({ tipo: 'due_colonne',
    sinistra: { titolo: 'Incluso', voci: liste.incluso },
    destra: { titolo: 'A parte', voci: liste.parte } })
  b.push({ tipo: 'h2', testo: 'Come si parte' })
  b.push({ tipo: 'p', testo: pilota
    ? 'Alla firma si salda la quota del pilota e si fissa la call di avviamento: quindici minuti in cui ci raccontate come lavorate oggi e si imposta tutto quello che serve per partire.'
    : 'Alla firma si salda la quota indicata e si fissa la call di avviamento: quindici minuti in cui ci raccontate come lavorate oggi e si imposta tutto quello che serve per partire.' })

  b.push({ tipo: 'h2', testo: 'Le regole del rapporto' })
  const regole: string[] = []
  if (meseTot) regole.push(`Il lavoro continuativo non ha una durata minima: si ferma quando volete, con ${studio.preavviso ?? 30} giorni di preavviso scritto, e l'addebito successivo non parte`)
  regole.push(linea === 'software'
    ? 'Il codice, i contenuti e il dominio sono vostri dalla consegna. Le licenze di strumenti terzi restano intestate a voi'
    : 'Gli account pubblicitari, i dati e quello che costruiamo restano vostri, anche se il rapporto finisce')
  regole.push('Per lavorare entriamo negli strumenti che ci indicate: trattiamo i dati solo per il progetto, come responsabili del trattamento, e li restituiamo o cancelliamo quando finisce')
  regole.push(`Quello che non è scritto qui si concorda per iscritto${studio.foro ? `. Per ogni controversia è competente il foro di ${studio.foro}` : ''}`)
  b.push({ tipo: 'elenco', voci: regole })

  b.push({ tipo: 'h2', testo: 'Firma per accettazione' })
  b.push({ tipo: 'p', testo: 'Si accetta firmando qui sotto e rimandando il documento, oppure rispondendo per iscritto «accetto» alla mail con cui lo avete ricevuto. Il pagamento della prima quota vale come accettazione.' })
  b.push({ tipo: 'anagrafica', colonne: [
    { titolo: 'Per il cliente', righe: [f.ragione || azienda, '', 'Luogo e data', '', 'Nome, ruolo e firma'] },
    { titolo: 'Per lo Studio', righe: [studio.ragione || 'Studio Galilei', '', 'Luogo e data', '', studio.firmatario || 'Nome, ruolo e firma'] },
  ] })
  return { tipo: 'Condizioni economiche', blocchi: b, piede: oggi.toLocaleDateString('it-IT', { day: 'numeric', month: 'long', year: 'numeric' }) }
}

