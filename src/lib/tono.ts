// LA PARTE LEGGERA DEL MOTORE: tipi, controllo del tono, nomi dei file.
// Non tira dentro pdf-lib: la usano il widget Preventivi e condizioni.ts.

export type Linea = 'marketing' | 'ai' | 'software' | 'istituzionale'
export const LINEA_NOME: Record<Linea, string> = { marketing: 'Marketing', ai: 'AI', software: 'Software', istituzionale: 'Istituzionale' }
export const LINEA_SIGLA: Record<Linea, string> = { marketing: 'MK', ai: 'AI', software: 'SW', istituzionale: 'AZ' }

export type Blocco =
  | { tipo: 'kicker'; testo: string }
  | { tipo: 'h1'; testo: string }
  | { tipo: 'h2'; testo: string }
  | { tipo: 'p'; testo: string; piccolo?: boolean }
  | { tipo: 'anagrafica'; colonne: Array<{ titolo: string; righe: string[] }> }
  | { tipo: 'tabella'; colonne: Array<{ testo: string; larghezza: number; destra?: boolean }>; righe: Array<Array<{ testo: string; sotto?: string; forte?: boolean }>> }
  | { tipo: 'elenco'; voci: string[] }
  | { tipo: 'due_colonne'; sinistra: { titolo: string; voci: string[] }; destra: { titolo: string; voci: string[] } }
  | { tipo: 'riquadro'; titolo: string; voci: string[] }
  | { tipo: 'tappe'; tappe: Array<{ quando: string; titolo: string; testo: string }> }
  | { tipo: 'numeri'; voci: Array<{ valore: string; etichetta: string }> }
  | { tipo: 'spazio'; mm: number }
  | { tipo: 'pagina' }

export interface Copertina {
  linea: Linea
  occhiello: string        // il TIPO di documento: «studio di mercato», «condizioni economiche»
  titolo: string
  sottotitolo?: string
  cliente?: string
  riferimento?: string     // SG-MK-2026-003
  data?: string            // «settembre 2026»
}

export interface Documento {
  tipo: string             // in testa alle pagine: «Condizioni economiche»
  copertina?: Copertina    // solo se il documento VENDE; se consegna, carta bianca
  blocchi: Blocco[]
  piede?: string           // in fondo all'ultima pagina, a destra: «settembre 2026»
}

export interface Risorse {
  regular: ArrayBuffer | Uint8Array
  semibold: ArrayBuffer | Uint8Array
  logo: ArrayBuffer | Uint8Array               // PNG, il logo blu
  logoBianco?: ArrayBuffer | Uint8Array        // PNG, il logo bianco per le copertine
  sfondi?: Partial<Record<Linea, ArrayBuffer | Uint8Array>>   // PNG delle copertine senza testo
}

// ── il controllo del tono (tono/check_tono.py, in TypeScript) ──────────
const SEGNI: Array<[RegExp, string]> = [
  [/·/g, 'puntino centrale'], [/•/g, 'punto elenco tondo'], [/—/g, 'trattino lungo'], [/–/g, 'trattino medio'], [/!/g, 'punto esclamativo'],
]
const PAROLE = ['innovativ', "all'avanguardia", 'soluzioni concrete', 'elevare', 'approfondire', 'game changer', 'rivoluzionar',
  'straordinari', 'incredibil', 'unico nel suo genere', 'nel panorama', 'a 360', 'chiavi in mano', 'sinergi', 'valore aggiunto',
  'eccellenza', 'leader di settore', 'performante', 'implementare', 'ottimizzare']

// ── la ripulitura automatica ────────────────────────────────────────────
// I segni vietati non sono un errore di chi scrive: sono un errore di
// battitura o un incolla da Google Maps. Si correggono da soli, invece di
// bloccare il PDF con un messaggio da programmatore (QA Dre, 14/9).
export function ripulisciTono(t: string): string {
  return t
    .replace(/\s*·\s*/g, ', ')
    .replace(/\s*—\s*/g, ': ')
    .replace(/–/g, '-')
    .replace(/^\s*•\s*/gm, '')
    .replace(/\s*•\s*/g, ', ')
    .replace(/\s*!+/g, '.')
    .replace(/\.\.+/g, '.')
    .replace(/[ \t]{2,}/g, ' ')
    .trim()
}

export function controllaTono(testo: string): string[] {
  const problemi: string[] = []
  for (const [re, nome] of SEGNI) {
    const n = (testo.match(re) ?? []).length
    if (n) problemi.push(`${nome} (${n})`)
  }
  const low = testo.toLowerCase()
  for (const w of PAROLE) if (low.includes(w)) problemi.push(`parola vietata «${w}»`)
  return problemi
}

export function testoDi(doc: Documento): string {
  const pezzi: string[] = [doc.tipo]
  if (doc.copertina) pezzi.push(doc.copertina.occhiello, doc.copertina.titolo, doc.copertina.sottotitolo ?? '')
  for (const b of doc.blocchi) {
    if ('testo' in b) pezzi.push(b.testo)
    if (b.tipo === 'anagrafica') b.colonne.forEach((c) => pezzi.push(c.titolo, ...c.righe))
    if (b.tipo === 'tabella') { b.colonne.forEach((c) => pezzi.push(c.testo)); b.righe.forEach((r) => r.forEach((c) => pezzi.push(c.testo, c.sotto ?? ''))) }
    if (b.tipo === 'elenco') pezzi.push(...b.voci)
    if (b.tipo === 'due_colonne') pezzi.push(b.sinistra.titolo, ...b.sinistra.voci, b.destra.titolo, ...b.destra.voci)
    if (b.tipo === 'riquadro') pezzi.push(b.titolo, ...b.voci)
    if (b.tipo === 'tappe') b.tappe.forEach((t) => pezzi.push(t.quando, t.titolo, t.testo))
    if (b.tipo === 'numeri') b.voci.forEach((v) => pezzi.push(v.valore, v.etichetta))
  }
  return pezzi.join('\n')
}

// ── il nome del file, come vuole il brand: sg-nome-documento.pdf ─────────
export function nomeFile(...pezzi: string[]): string {
  const s = pezzi.join(' ').normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
  return `sg-${s}.pdf`
}

export const euroTesto = (n: number) => `${Math.round(n).toLocaleString('it-IT')} €`
export const meseAnno = (d = new Date()) => d.toLocaleDateString('it-IT', { month: 'long', year: 'numeric' })
