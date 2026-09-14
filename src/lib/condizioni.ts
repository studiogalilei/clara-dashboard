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
export const unaTantum = (voci: Voce[]) => voci.filter((v) => v.ricorrenza === 'una_tantum').reduce((t, v) => t + v.quantita * v.prezzo, 0)
export const alMese = (voci: Voce[]) => voci.filter((v) => v.ricorrenza === 'mese').reduce((t, v) => t + v.quantita * v.prezzo, 0)
export const ePilota = (v: Voce) => /pilota|prova/i.test(v.nome)
const dataLunga = (iso: string) => new Date(iso + 'T12:00:00').toLocaleDateString('it-IT', { day: 'numeric', month: 'long', year: 'numeric' })

// IL DOCUMENTO: «Condizioni economiche», il testo ufficiale dello Studio
// (sg-condizioni-modello): non si modifica il testo, si cambiano i dati.
export function documentoDi(q: { voci: Voce[]; valido_fino: string | null; numero: string | null }, azienda: string, f: Fatturazione): Documento {
  const pilota = q.voci.find(ePilota)
  const mensili = q.voci.filter((v) => v.ricorrenza === 'mese')
  const unaTantumTot = unaTantum(q.voci)
  const meseTot = alMese(q.voci)
  const oggi = new Date()
  const b: Blocco[] = []
  b.push({ tipo: 'kicker', testo: 'Condizioni economiche' })
  b.push({ tipo: 'h1', testo: azienda })
  b.push({ tipo: 'anagrafica', colonne: [
    { titolo: 'Intestatario', righe: [f.ragione || azienda, ...(f.indirizzo ? [f.indirizzo] : [])] },
    { titolo: 'Partita IVA', righe: [f.piva || '[da verificare]', ...(f.pec ? [`PEC ${f.pec}`] : []), ...(f.sdi ? [`SDI ${f.sdi}`] : [])] },
    { titolo: 'Riferimento', righe: [q.numero ?? '', oggi.toLocaleDateString('it-IT', { month: 'long', year: 'numeric' })] },
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
  const validita = q.valido_fino ? ` Queste condizioni valgono fino al ${dataLunga(q.valido_fino)}.` : ''
  if (totali.length) b.push({ tipo: 'p', testo: `In tutto: ${totali.join(', ')}. Importi IVA esclusa.${validita}` })
  b.push({ tipo: 'p', piccolo: true, testo: 'Gli importi indicati sono quelli che troverete in fattura, senza aggiunte. Il budget pubblicitario, quando previsto, è a parte: si definisce insieme e si tara sulla strategia scelta, restando sui vostri account.' })

  b.push({ tipo: 'pagina' })
  if (pilota) {
    b.push({ tipo: 'kicker', testo: 'Garanzia' })
    b.push({ tipo: 'h2', testo: 'Il rischio del primo passo resta nostro' })
    b.push({ tipo: 'p', testo: `Quello che ferma la maggior parte delle aziende non è il budget: è l'esperienza precedente con fornitori spariti dopo la firma. Per questo i ${euroTesto(pilota.quantita * pilota.prezzo)} del pilota restano rimborsabili fino alla fine del secondo mese.` })
    b.push({ tipo: 'riquadro', titolo: 'Due cose distinte', voci: [
      'Alla fine dei due mesi guardiamo insieme com\'è andata',
      'Proseguire o no è una vostra scelta, e non richiede motivazioni',
      'Il rimborso è un\'altra cosa: se il lavoro non vi ha convinto o vi sentite fortemente insoddisfatti, lo chiedete e ve lo restituiamo per intero',
      'Quello che abbiamo costruito resta vostro in ogni caso',
    ] })
    b.push({ tipo: 'p', piccolo: true, testo: 'La garanzia esiste perché nessuno debba fidarsi sulla parola. Nella pratica chi si ferma lo fa quasi sempre per ragioni che con il lavoro svolto non c\'entrano, e in quel caso il rimborso non si pone.' })
  }
  b.push({ tipo: 'h2', testo: 'Cosa è incluso e cosa no' })
  b.push({ tipo: 'due_colonne',
    sinistra: { titolo: 'Incluso', voci: ['Analisi iniziale e impostazione del sistema', 'Gestione operativa e lavoro sui dati', 'Report periodici con metodo di calcolo dichiarato', 'Call di allineamento regolari', 'Un referente che risponde del progetto'] },
    destra: { titolo: 'A parte', voci: ['Budget pubblicitario, che resta sui vostri account', 'Licenze di strumenti terzi, se ne servono', 'Produzione video e fotografica sul posto', 'Sviluppo software su misura, che ha un suo preventivo'] } })
  b.push({ tipo: 'h2', testo: 'Come si parte' })
  b.push({ tipo: 'p', testo: pilota
    ? 'Alla firma si salda la quota del pilota e si fissa la call di avviamento: quindici minuti in cui ci raccontate come lavorate oggi e si imposta tutto quello che serve per partire.'
    : 'Alla firma si salda la quota indicata e si fissa la call di avviamento: quindici minuti in cui ci raccontate come lavorate oggi e si imposta tutto quello che serve per partire.' })
  return { tipo: 'Condizioni economiche', blocchi: b, piede: oggi.toLocaleDateString('it-IT', { month: 'long', year: 'numeric' }) }
}

