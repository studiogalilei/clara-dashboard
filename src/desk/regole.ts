// IL DESK: le regole pure (niente rete), provate in regole.test.ts.
import type { Decisione, Mossa, Stato } from './dati'
import type { Tono } from '../snella/regole'

export const MOSSE: Record<Mossa, { nome: string; bottone: string; tono: Tono; scrive: boolean; peso: number }> = {
  book_meeting: { nome: 'Conferma la call', bottone: 'Invia la conferma', tono: 'ok', scrive: true, peso: 100 },
  callback: { nome: 'Da chiamare', bottone: 'Chiamato', tono: 'ok', scrive: false, peso: 95 },
  send_analysis: { nome: 'Manda l’analisi', bottone: 'Invia l’analisi', tono: 'noi', scrive: true, peso: 90 },
  offer_slots: { nome: 'Propone due orari', bottone: 'Invia gli orari', tono: 'opp', scrive: true, peso: 85 },
  reply: { nome: 'Risponde', bottone: 'Invia la risposta', tono: 'noi', scrive: true, peso: 70 },
  escalate: { nome: 'Decidi tu', bottone: 'Fatto', tono: 'attesa', scrive: false, peso: 60 },
  wait: { nome: 'Aspetta', bottone: 'Va bene così', tono: 'neutro', scrive: false, peso: 20 },
  close: { nome: 'Chiude', bottone: 'Va bene così', tono: 'neutro', scrive: false, peso: 5 },
}

export type Gruppo = 'fare' | 'corso' | 'attesa' | 'fatte' | 'chiuse'
export const GRUPPI: Record<Gruppo, string> = { fare: 'Da fare adesso', corso: 'In partenza', attesa: 'In attesa', fatte: 'Fatte', chiuse: 'Chiuse' }

export function gruppoDi(d: Pick<Decisione, 'mossa' | 'stato'> & { entro_il?: string | null }): Gruppo {
  if (d.stato === 'approvata' || d.stato === 'in_invio') return 'corso'
  if (d.stato === 'inviata' || d.stato === 'fatta') return 'fatte'
  if (d.stato === 'scartata' || d.stato === 'superata') return 'chiuse'
  if (d.mossa === 'wait') return 'attesa'
  if (d.mossa === 'close') return 'chiuse'
  if (d.mossa === 'escalate' && d.entro_il && d.entro_il > new Date().toISOString().slice(0, 10)) return 'attesa'   // «Più avanti»
  return 'fare'
}

/** Quanto conta: la mossa, la freschezza, e chi ha gia' l'analisi (e' piu' avanti). 0-130. */
export function priorita(d: Pick<Decisione, 'mossa' | 'risposta_il' | 'analisi_mandata' | 'stato' | 'consiglio'>, adesso: Date = new Date()): number {
  let p = MOSSE[d.mossa]?.peso ?? 0
  const ore = (adesso.getTime() - new Date(d.risposta_il).getTime()) / 36e5
  if (ore < 24) p += 15
  else if (ore < 72) p += 8
  else if (ore > 24 * 7) p -= 10
  if (d.analisi_mandata && d.mossa !== 'close') p += 5
  if (d.consiglio?.numero && !d.consiglio.esito) p += 10
  if (d.stato === 'approvata' || d.stato === 'in_invio') p -= 30
  return Math.max(0, Math.min(130, Math.round(p)))
}

/** Quanto e' caldo il lead, da 1 a 10: la mossa che Clara ha scelto dice quanto interesse ha letto (una call da
 *  confermare e' un 10, un no e' un 1), l'analisi gia' mandata e un consiglio di chiamata aggiungono, il tempo
 *  passato toglie. E' un numero per orientarsi, non una misura. */
export function interesse(d: Pick<Decisione, 'mossa' | 'risposta_il' | 'analisi_mandata' | 'consiglio' | 'classe' | 'fit'>, adesso: Date = new Date()): number {
  const base: Record<Mossa, number> = { book_meeting: 10, callback: 9, offer_slots: 9, send_analysis: 7, reply: 6, escalate: 6, wait: 4, close: 1 }
  let s = base[d.mossa] ?? 4
  if (d.analisi_mandata && d.mossa !== 'close') s += 1
  if (d.consiglio?.numero) s += 1
  if (d.classe === 'positivo' && d.mossa !== 'close') s += 1
  const giorni = (adesso.getTime() - new Date(d.risposta_il).getTime()) / 864e5
  if (giorni > 14) s -= 2
  else if (giorni > 7) s -= 1
  // 4/11, Dre: «un incrocio tra il livello di interesse e quanto e' in fit, col fit deciso dal sistema»
  const fit = d.fit === 'SI' ? 10 : d.fit === 'PARZIALE' ? 6 : d.fit === 'NO' ? 2 : 5
  const voto = d.mossa === 'close' ? 1 : 0.6 * s + 0.4 * fit
  return Math.max(1, Math.min(10, Math.round(voto)))
}

export function ordina<T extends Decisione>(ds: T[], adesso: Date = new Date()): T[] {
  return [...ds].sort((a, b) => priorita(b, adesso) - priorita(a, adesso) || b.risposta_il.localeCompare(a.risposta_il))
}

export type Filtro = 'tutte' | 'inviare' | 'call' | 'consigli' | 'tue' | 'mie' | 'attesa' | 'fatte' | 'chiuse'
export const FILTRI: Array<{ f: Filtro; nome: string }> = [
  { f: 'tutte', nome: 'Da fare' }, { f: 'inviare', nome: 'Da inviare' }, { f: 'call', nome: 'Call' }, { f: 'tue', nome: 'Decidi tu' },
  { f: 'consigli', nome: 'Ti consiglio di chiamare' }, { f: 'mie', nome: 'Me ne occupo io' }, { f: 'attesa', nome: 'In attesa' }, { f: 'fatte', nome: 'Fatte' }, { f: 'chiuse', nome: 'Chiuse' },
]

export function filtra<T extends Decisione>(ds: T[], f: Filtro, q = ''): T[] {
  const testo = q.trim().toLowerCase()
  return ds.filter((d) => {
    const g = gruppoDi(d)
    if (d.in_mano_a && f !== 'mie' && f !== 'fatte' && f !== 'chiuse') return false   // una relazione di Dre non sta nella coda di Clara
    const ok = f === 'tutte' ? g === 'fare' || g === 'corso'
      : f === 'inviare' ? (g === 'fare' || g === 'corso') && MOSSE[d.mossa].scrive
        : f === 'call' ? (g === 'fare' || g === 'corso') && (d.mossa === 'callback' || d.mossa === 'book_meeting' || d.mossa === 'offer_slots')
          : f === 'tue' ? g === 'fare' && d.mossa === 'escalate'
            : f === 'mie' ? !!d.in_mano_a
            : f === 'consigli' ? !!d.consiglio?.numero && !d.consiglio.esito && g !== 'chiuse'
            : f === 'attesa' ? g === 'attesa'
              : f === 'fatte' ? g === 'fatte'
                : g === 'chiuse'
    if (!ok) return false
    if (!testo) return true
    return [d.azienda, d.persona, d.citta, d.settore, d.email].join(' ').toLowerCase().includes(testo)
  })
}

export function conta<T extends Decisione>(ds: T[]): Record<Filtro, number> {
  const out = { tutte: 0, inviare: 0, call: 0, consigli: 0, tue: 0, mie: 0, attesa: 0, fatte: 0, chiuse: 0 }
  for (const f of Object.keys(out) as Filtro[]) out[f] = filtra(ds, f).length
  return out
}

/** Lo stato in una parola, per la riga e la scheda. */
export function statoBreve(d: Pick<Decisione, 'stato' | 'mossa' | 'errore' | 'esito' | 'verificata_il'>): { testo: string; tono: Tono } {
  const s: Stato = d.stato
  if (s === 'proposta') return d.errore ? { testo: `Ferma: ${d.errore}`, tono: 'no' } : { testo: MOSSE[d.mossa].nome, tono: MOSSE[d.mossa].tono }
  if (s === 'approvata') return { testo: d.errore ? `Riprovo: ${d.errore}` : 'In partenza', tono: 'attesa' }
  if (s === 'in_invio') return { testo: 'Sta partendo', tono: 'attesa' }
  if (s === 'inviata') return { testo: d.verificata_il ? 'Inviata e verificata' : 'Inviata', tono: 'ok' }
  if (s === 'fatta') return { testo: d.esito ? `Fatto: ${d.esito}` : 'Fatto', tono: 'ok' }
  if (s === 'scartata') return { testo: 'Scartata', tono: 'neutro' }
  return { testo: 'Superata: ha riscritto', tono: 'neutro' }
}

export const ESITI_CHIAMATA: Array<{ esito: string; nome: string }> = [
  // 4/11, Dre: «Non risponde non ha senso, tutto deve essere actionable: non risponde? si richiama». Tre esiti.
  { esito: 'fissata', nome: 'Call fissata' }, { esito: 'richiamare', nome: 'Richiamare' }, { esito: 'non_interessato', nome: 'Non interessato' },
]
export const ESITI_TUA: Array<{ esito: string; nome: string }> = [
  { esito: 'risposto_io', nome: 'Ho risposto io' }, { esito: 'chiuso', nome: 'Chiudo qui' },
]

/** I motivi per cui Dre prende in mano una relazione: Clara li legge come nota. */
export const MOTIVI_IN_MANO: string[] = ['Mi ha chiamato', 'L’ho chiamato io', 'Ci ho parlato di persona', 'Me ne occupo io da qui', 'Non va più seguito']

export function nomeProprio(persona: string | null | undefined): string {
  return (persona ?? '').trim().split(/\s+/)[0] || ''
}

/** Le iniziali per il tondo dell'azienda. */
export function iniziali(azienda: string | null | undefined): string {
  const p = (azienda ?? '?').trim().split(/\s+/).filter(Boolean)
  return ((p[0]?.[0] ?? '?') + (p[1]?.[0] ?? '')).toUpperCase()
}

/** Il testo che manda, senza la riga «A: … Cc: …» e «Oggetto:» che Clara scrive quando cambia destinatario. */
export function destinatari(testo: string | null | undefined): { a: string | null; cc: string | null; oggetto: string | null; corpo: string } {
  const t = (testo ?? '').trim()
  const righe = t.split('\n')
  let a: string | null = null, cc: string | null = null, oggetto: string | null = null, i = 0
  if (/^a:/i.test(righe[0] ?? '') && righe[0].includes('@')) {
    const m = righe[0].match(/[\w.+-]+@[\w-]+(?:\.[\w-]+)+/g) ?? []
    a = m[0] ?? null; i = 1
    const inCc = [...m.slice(1)]
    if (/^cc:/i.test(righe[i] ?? '')) { inCc.push(...(righe[i].match(/[\w.+-]+@[\w-]+(?:\.[\w-]+)+/g) ?? [])); i += 1 }
    cc = inCc.join(', ') || null
  }
  if (/^oggetto:/i.test(righe[i] ?? '')) { oggetto = righe[i].replace(/^oggetto:\s*/i, '').trim(); i += 1 }
  return { a, cc, oggetto, corpo: righe.slice(i).join('\n').trim() }
}

/** Il numero di telefono dentro a un testo che puo' contenere anche nome e ruolo («335 838 3593 (Matteo…)»). */
/** Il link di WhatsApp da un numero (4/11: «dammi anche il pulsante WhatsApp, tanto succede spesso»).
 *  Cifre sole, prefisso internazionale senza «+» e senza «00»; un cellulare italiano senza prefisso prende 39. */
export function whatsappDa(numero: string | null | undefined): string | null {
  const t = telefonoDa(numero) ?? numero ?? ''
  let cifre = t.replace(/\D/g, '')
  if (cifre.startsWith('00')) cifre = cifre.slice(2)
  if (cifre.length === 10 && cifre.startsWith('3')) cifre = '39' + cifre
  if (cifre.length < 11) return null
  return `https://wa.me/${cifre}`
}
export const NOTA_WHATSAPP = 'Scritto su WhatsApp'
export const MOTIVO_WHATSAPP = 'gli ho scritto su WhatsApp'

export function telefonoDa(testo: string | null | undefined): string | null {
  const m = (testo ?? '').match(/(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3}[\s.-]?\d{3,4}(?:[\s.-]?\d{2,4})?/)
  if (!m) return null
  const n = m[0].replace(/[^\d+]/g, '')
  return n.replace(/^\+?0*/, (x) => x).length >= 9 ? m[0].trim() : null
}

/** L'agenda senza doppioni (la stessa call da due calendari) e senza gli impegni che non sono call con un lead. */
export function agendaPulita<T extends { at: string; titolo: string | null; tipo: string | null; prospect_id: string | null }>(voci: T[]): T[] {
  const viste = new Set<string>()
  return voci.filter((v) => {
    if (!v.prospect_id && (v.tipo === 'altro' || !v.tipo)) return false
    const k = `${v.at.slice(0, 16)}|${(v.titolo ?? '').trim().toLowerCase()}`
    if (viste.has(k)) return false
    viste.add(k)
    return true
  })
}
