import type { Documento, Blocco } from './tono'
import proposta from '../modelli/doc-proposta-tecnica.json'
import report from '../modelli/doc-report-mensile.json'
import verbale from '../modelli/doc-verbale-call.json'

// I MODELLI DENTRO L'APP (Dre, 16/9): «clicco un + e mi porta in un posto
// tipo Word col template gia' li', collego l'azienda e i dati si riempiono,
// e se non c'e' quello spazio resta fillabile e aggiungo altro».
//
// Sono gli stessi file che stampiamo in PDF (docs/modelli): quello che vedi
// a schermo e quello che esce stampato sono lo stesso oggetto. Le parti fra
// parentesi quadre sono i buchi: quelli che sappiamo li riempiamo noi, gli
// altri restano li' in chiaro, da scrivere.

export interface Modello {
  chiave: string
  nome: string
  cosa: string
  doc: () => Documento
}

const copia = (d: unknown): Documento => JSON.parse(JSON.stringify(d)) as Documento

const bianco = (): Documento => ({
  tipo: 'Documento',
  blocchi: [
    { tipo: 'h1', testo: 'Titolo del documento' },
    { tipo: 'p', testo: 'Scrivi qui.' },
  ],
})

export const MODELLI: Modello[] = [
  { chiave: 'proposta', nome: 'Proposta tecnica', cosa: 'cosa costruiamo, in che ordine, cosa serve da voi', doc: () => copia(proposta) },
  { chiave: 'report', nome: 'Report mensile', cosa: 'com\'è andato il mese, con i numeri e il prossimo passo', doc: () => copia(report) },
  { chiave: 'verbale', nome: 'Verbale di call', cosa: 'cosa si è deciso, chi fa cosa entro quando', doc: () => copia(verbale) },
  { chiave: 'bianco', nome: 'Foglio bianco', cosa: 'parti da zero, con il brand già addosso', doc: bianco },
]

export const modelloDi = (chiave: string) => MODELLI.find((m) => m.chiave === chiave)

// ── i buchi che sappiamo riempire ───────────────────────────────────────
export interface Dati {
  azienda?: string | null
  referente?: string | null
  email?: string | null
  io?: string | null            // chi sta scrivendo
  inizio?: string | null        // il periodo di prova: le date che poi
  fine?: string | null          // finiscono sulla scheda del cliente
}

function sostituzioni(d: Dati): Array<[RegExp, string]> {
  const oggi = new Date()
  const mese = oggi.toLocaleDateString('it-IT', { month: 'long', year: 'numeric' })
  const giorno = oggi.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' })
  const fuori: Array<[RegExp, string]> = [
    [/\[mese anno\]/gi, mese],
    [/\[gg\/mm\/aaaa\]/g, giorno],
  ]
  if (d.azienda) {
    fuori.push([/\[nome azienda\]/gi, d.azienda], [/\[cliente\]/gi, d.azienda])
  }
  if (d.email) fuori.push([/\[email\]/gi, d.email])
  if (d.io) fuori.push([/\[nomi lato studio\]/gi, d.io])
  if (d.referente) fuori.push([/\[referente\]/gi, d.referente])
  if (d.inizio) fuori.push([/\[data inizio\]/gi, d.inizio])
  if (d.fine) fuori.push([/\[data fine\]/gi, d.fine])
  return fuori
}

const scambia = (t: string, regole: Array<[RegExp, string]>) =>
  regole.reduce((s, [re, v]) => s.replace(re, v), t)

// riempie quello che sa, lascia il resto in chiaro
export function riempi(doc: Documento, dati: Dati): Documento {
  const regole = sostituzioni(dati)
  const testo = (t: string) => scambia(t, regole)
  const blocchi = doc.blocchi.map((b): Blocco => {
    if ('testo' in b && typeof b.testo === 'string') return { ...b, testo: testo(b.testo) } as Blocco
    if (b.tipo === 'elenco') return { ...b, voci: b.voci.map(testo) }
    if (b.tipo === 'riquadro') return { ...b, titolo: testo(b.titolo), voci: b.voci.map(testo) }
    if (b.tipo === 'anagrafica') return { ...b, colonne: b.colonne.map((c) => ({ titolo: c.titolo, righe: c.righe.map(testo) })) }
    if (b.tipo === 'tabella') return { ...b, righe: b.righe.map((r) => r.map((c) => ({ ...c, testo: testo(c.testo), sotto: c.sotto ? testo(c.sotto) : c.sotto }))) }
    if (b.tipo === 'due_colonne') return {
      ...b,
      sinistra: { titolo: testo(b.sinistra.titolo), voci: b.sinistra.voci.map(testo) },
      destra: { titolo: testo(b.destra.titolo), voci: b.destra.voci.map(testo) },
    }
    if (b.tipo === 'tappe') return { ...b, tappe: b.tappe.map((t) => ({ quando: testo(t.quando), titolo: testo(t.titolo), testo: testo(t.testo) })) }
    if (b.tipo === 'numeri') return { ...b, voci: b.voci.map((v) => ({ valore: testo(v.valore), etichetta: testo(v.etichetta) })) }
    return b
  })
  const c = doc.copertina
  const copertina = c
    ? {
        ...c,
        occhiello: testo(c.occhiello),
        titolo: testo(c.titolo),
        sottotitolo: c.sottotitolo ? testo(c.sottotitolo) : undefined,
        data: c.data ? testo(c.data) : undefined,
        cliente: dati.azienda ?? c.cliente,
      }
    : undefined
  return { ...doc, copertina, blocchi }
}

// quanti buchi restano: si dice in cima all'editor, cosi' non si manda
// fuori un documento con le parentesi quadre dentro
export function buchi(doc: Documento): number {
  return (JSON.stringify(doc).match(/\[[^\]"]{2,60}\]/g) ?? []).length
}

// il titolo che si vede nell'elenco: il primo h1, se no il tipo
export function titoloDoc(doc: Documento): string {
  const h1 = doc.blocchi.find((b) => b.tipo === 'h1') as { testo: string } | undefined
  return doc.copertina?.titolo || h1?.testo || doc.tipo || 'Senza titolo'
}
