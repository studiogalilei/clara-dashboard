// LA VERSIONE SNELLA: le poche regole della UI, pure e provate (regole.test.ts).
// Il grosso lo decide scripts/schede.py; qui solo come si combinano le schede con quello che
// ha deciso Dre (chiamato, richiamare il...) e come si scrivono date e numeri.
import { INFO_STATI, type Call, type Decisione, type Domanda, type InfoStato, type RigaLead, type Telefono } from './dati'
import statiJson from './stati.json'

export const ROMA = 'Europe/Rome'
export const GIORNI_DA_CHIAMARE = 21          // oltre, chi voleva sentirti si guarda dalla lista Lead
// chi Dre ha messo in un'opportunita' (la call c'e' gia', o e' cliente) o fra i chiusi non si chiama
const FERMI: string[] = INFO_STATI.filter((s) => s.gruppo === 'Opportunità' || s.gruppo === 'Chiusi').map((s) => s.nome)
const DAI_VECCHI: Record<string, string> = statiJson.dai_vecchi

/** Il nome di uno stato fra i 12 di Dre (19/10): una scheda non ancora rifatta puo' avere ancora
 *  un nome vecchio («No grazie», «Vuole sentirti»...): si traduce, mai si mostra. */
export function nomeStato(s: string | null | undefined): string | null {
  if (!s) return null
  if (INFO_STATI.some((x) => x.nome === s)) return s
  return DAI_VECCHI[s] ?? null
}

/** LE 8 FASI del foglio della pipeline (19/10), da sinistra a destra (stati.json, «fasi»). */
export const FASI: ReadonlyArray<{ nome: string; colore: string; fondo: string; testo: string; chi: string }> = statiJson.fasi
const FASE_DI_STATO: Record<string, string | null> = statiJson.fase_di_stato
const FUORI_PERCORSO: Record<string, string> = statiJson.fuori_percorso

/** La fase di un lead, come la dice il foglio: quella calcolata da scripts/foglio.py (che guarda
 *  anche l'analisi, il calendario e le scelte di Dre) se c'e', se no quella di partenza dello stato.
 *  Fuori dal percorso torna l'etichetta del conteggio («No», «Fuori ufficio»...) e `dentro` falso. */
export function faseDi(stato: string | null | undefined, dalFoglio?: string | null): { nome: string; dentro: boolean } | null {
  if (dalFoglio) return { nome: dalFoglio, dentro: FASI.some((f) => f.nome === dalFoglio) }
  const s = nomeStato(stato)
  if (!s) return null
  const f = FASE_DI_STATO[s]
  if (f) return { nome: f, dentro: true }
  return FUORI_PERCORSO[s] ? { nome: FUORI_PERCORSO[s], dentro: false } : null
}

/** Quello che sa lo stato: gruppo, colore, responsabile e prossima azione di default. */
export function infoStato(s: string): InfoStato | null {
  return INFO_STATI.find((x) => x.nome === s) ?? null
}

/** Il giorno a Roma, AAAA-MM-GG. */
export function giornoRoma(d: Date = new Date()): string {
  const p = new Intl.DateTimeFormat('en-CA', { timeZone: ROMA, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(d)
  const v = (t: string) => p.find((x) => x.type === t)?.value ?? ''
  return `${v('year')}-${v('month')}-${v('day')}`
}

export function piuGiorni(giorno: string, n: number): string {
  const [a, m, g] = giorno.split('-').map(Number)
  const d = new Date(Date.UTC(a, m - 1, g + n, 12))
  return d.toISOString().slice(0, 10)
}

export function statoDi(r: Pick<RigaLead, 'stato'>, d?: Decisione | null): string {
  return nomeStato(d?.stato) || nomeStato(r.stato) || 'Da rispondere'
}

/** I toni del Workspace (src/index.css, 17/10 e 19/10): il colore dice il significato, mai da solo.
 *  ok verde, no rosso, attesa ambra, noi blu, loro arancio, neutro grigio; dal 19/10 opp viola (le
 *  opportunita'), giallo (da ricontattare) e stop (Non contattare: piu' scuro del rosso). */
export type Tono = 'ok' | 'no' | 'attesa' | 'noi' | 'loro' | 'neutro' | 'opp' | 'giallo' | 'stop'
const TONI: readonly Tono[] = ['ok', 'no', 'attesa', 'noi', 'loro', 'neutro', 'opp', 'giallo', 'stop']

/** Il colore di uno stato, da stati.json. Uno stato che non c'e' resta grigio, non inventa un colore. */
export function tonoStato(stato: string): Tono {
  const t = infoStato(stato)?.tono as Tono | undefined
  return t && TONI.includes(t) ? t : 'neutro'
}

/** IL CELLULARE di un lead (Dre, 20/10 sera: «Da chiamare SOLO se c'e' il numero, e se e' personale, un
 *  cellulare, non uno d'ufficio»): un numero che inizia per 3 lasciato da lui (la firma) o scritto nella sua
 *  scheda, mai il centralino del sito. La stessa regola di scripts/segnale_provvisorio.cellulare_fra; una
 *  scheda vecchia senza tipo e fonte si legge dall'etichetta («cellulare, dalla firma»). */
export function cellulareDi(s: { telefoni?: Telefono[] } | null | undefined): Telefono | null {
  for (const t of s?.telefoni ?? []) {
    if (t.tipo ? (t.tipo === 'cellulare' && (t.fonte === 'firma' || t.fonte === 'scheda')) : /^cellulare, dalla (firma|scheda)/.test(t.etichetta)) return t
  }
  return null
}

export type Motivo = 'richiamare' | 'chiamare'
export interface DaChiamare<R extends RigaLead = RigaLead> { riga: R; decisione: Decisione | null; motivo: Motivo; nonRisponde: boolean }

/** Chi chiamare adesso: chi lo vuole (la scheda) E ha lasciato un cellulare (20/10 sera: senza, non si
 *  chiama, gli si scrive), piu' chi va richiamato oggi (un gesto di Dre: resta com'e'). Chi e' stato
 *  chiamato dopo la sua ultima risposta esce; chi va richiamato torna il giorno scelto. */
export function listaDaChiamare<R extends RigaLead & { scheda?: { telefoni?: Telefono[] } }>(righe: R[], decisioni: Map<string, Decisione>, ora: Date = new Date()): Array<DaChiamare<R>> {
  const oggi = giornoRoma(ora)
  const limite = ora.getTime() - GIORNI_DA_CHIAMARE * 86400e3
  const out: Array<DaChiamare<R>> = []
  for (const r of righe) {
    const d = decisioni.get(r.prospect_id) ?? null
    if (d?.stato && FERMI.includes(d.stato)) continue
    const ultima = r.ultima_risposta ? new Date(r.ultima_risposta).getTime() : 0
    const chiamataIl = d?.chiamata_il ? new Date(d.chiamata_il).getTime() : 0
    if (d?.chiamata === 'richiamare' && d.richiamare_il) {
      // una risposta nuova dopo il «richiamare» lo riporta su, se la scheda dice di chiamare
      const nuova = r.da_chiamare && ultima > chiamataIl && cellulareDi(r.scheda)
      if (d.richiamare_il <= oggi) { out.push({ riga: r, decisione: d, motivo: 'richiamare', nonRisponde: false }); continue }
      if (!nuova) continue
    }
    if (!r.da_chiamare || ultima < limite || !cellulareDi(r.scheda)) continue
    if (d?.chiamata === 'chiamato' && chiamataIl >= ultima) continue
    out.push({ riga: r, decisione: d, motivo: 'chiamare', nonRisponde: d?.chiamata === 'non_risponde' && chiamataIl >= ultima })
  }
  const peso = (x: DaChiamare<R>) => (x.motivo === 'richiamare' ? 0 : 1) + (x.nonRisponde ? 2 : 0)
  return out.sort((a, b) => peso(a) - peso(b)
    || (a.riga.ultima_risposta ?? '').localeCompare(b.riga.ultima_risposta ?? ''))
}

/** Chi aspetta una telefonata da piu' di un giorno senza che sia successo niente. */
export function chiamateInRitardo(lista: DaChiamare[], ora: Date = new Date()): DaChiamare[] {
  return lista.filter((x) => x.motivo === 'chiamare' && !x.nonRisponde && x.riga.ultima_risposta
    && ora.getTime() - new Date(x.riga.ultima_risposta).getTime() > 86400e3)
}

export function contaStati(righe: RigaLead[], decisioni: Map<string, Decisione>): Map<string, number> {
  const m = new Map<string, number>()
  for (const r of righe) {
    const s = statoDi(r, decisioni.get(r.prospect_id))
    m.set(s, (m.get(s) ?? 0) + 1)
  }
  return m
}

/** Cerca per azienda, persona o mail, senza accenti e maiuscole. */
export function cerca(righe: RigaLead[], q: string): RigaLead[] {
  const n = (s: string | null | undefined) => (s ?? '').normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase()
  const parole = n(q).split(/\s+/).filter(Boolean)
  if (!parole.length) return righe
  return righe.filter((r) => {
    const t = `${n(r.azienda)} ${n(r.persona)} ${n(r.email)}`
    return parole.every((p) => t.includes(p))
  })
}

// ── le date, dette come le dice una persona ─────────────────────────────

const fmt = (o: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat('it-IT', { timeZone: ROMA, ...o })
const ORA = fmt({ hour: '2-digit', minute: '2-digit' })
const GIORNO = fmt({ weekday: 'short', day: 'numeric', month: 'short' })
const GIORNO_LUNGO = fmt({ weekday: 'long', day: 'numeric', month: 'long' })

export function ora(iso: string | null | undefined): string {
  return iso ? ORA.format(new Date(iso)) : ''
}

/** «oggi alle 10:31», «ieri alle 18:02», «lun 12 ott» */
export function quando(iso: string | null | undefined, adesso: Date = new Date()): string {
  if (!iso) return ''
  const d = new Date(iso)
  const g = giornoRoma(d)
  const oggi = giornoRoma(adesso)
  if (g === oggi) return `oggi alle ${ORA.format(d)}`
  if (g === piuGiorni(oggi, -1)) return `ieri alle ${ORA.format(d)}`
  return GIORNO.format(d)
}

/** Il nome del giorno per i gruppi: «Oggi», «Domani», «lunedì 19 ottobre». */
export function nomeGiorno(giorno: string, adesso: Date = new Date()): string {
  const oggi = giornoRoma(adesso)
  if (giorno === oggi) return 'Oggi'
  if (giorno === piuGiorni(oggi, 1)) return 'Domani'
  const [a, m, g] = giorno.split('-').map(Number)
  const s = GIORNO_LUNGO.format(new Date(Date.UTC(a, m - 1, g, 12)))
  return s.charAt(0).toUpperCase() + s.slice(1)
}

/** Una data AAAA-MM-GG detta corta: «20 ott». */
export function dataCorta(giorno: string | null | undefined): string {
  if (!giorno) return ''
  const [a, m, g] = giorno.slice(0, 10).split('-').map(Number)
  return fmt({ day: 'numeric', month: 'short' }).format(new Date(Date.UTC(a, m - 1, g, 12)))
}

/** «da 40 minuti», «da 3 ore», «da 5 giorni» */
export function daQuanto(iso: string | null | undefined, adesso: Date = new Date()): string {
  if (!iso) return ''
  const min = Math.max(0, Math.round((adesso.getTime() - new Date(iso).getTime()) / 60000))
  return `da ${durata(min)}`
}

export function durata(min: number): string {
  if (min < 60) return `${min} ${min === 1 ? 'minuto' : 'minuti'}`
  const h = Math.round(min / 60)
  if (h < 24) return `${h} ${h === 1 ? 'ora' : 'ore'}`
  const g = Math.round(h / 24)
  return `${g} ${g === 1 ? 'giorno' : 'giorni'}`
}

export function perGiorno(call: Call[]): Array<{ giorno: string; call: Call[] }> {
  const m = new Map<string, Call[]>()
  for (const c of [...call].sort((a, b) => a.at.localeCompare(b.at))) {
    const g = giornoRoma(new Date(c.at))
    m.set(g, [...(m.get(g) ?? []), c])
  }
  return [...m.entries()].map(([giorno, cc]) => ({ giorno, call: cc }))
}

/** Le domande della Posta, una riga per azienda (la piu' recente), con quante sono. */
export function perAzienda(domande: Domanda[]): Array<{ ultima: Domanda; quante: number }> {
  const m = new Map<string, { ultima: Domanda; quante: number }>()
  for (const d of domande) {
    const k = d.prospect_id ?? `t:${d.titolo}`
    const x = m.get(k)
    if (!x) m.set(k, { ultima: d, quante: 1 })
    else { x.quante += 1; if (d.at > x.ultima.at) x.ultima = d }
  }
  return [...m.values()].sort((a, b) => b.ultima.at.localeCompare(a.ultima.at))
}

/** Il tasso di risposta in percento, una cifra decimale; null se non si puo' dire. */
export function tasso(risposte: number | null | undefined, scritte: number | null | undefined): string | null {
  if (risposte == null || !scritte) return null
  const v = (risposte / scritte) * 100
  return `${v.toLocaleString('it-IT', { maximumFractionDigits: 1, minimumFractionDigits: v < 10 ? 1 : 0 })}%`
}

export function numero(n: number | null | undefined): string | null {
  return n == null ? null : String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

/** Il titolo di una domanda della Posta senza i prefissi tecnici («Bozza per X, INT-08»,
 *  «Follow up 1: X, FOLLOW UP 1»): resta il nome dell'azienda. */
export function titoloDomanda(t: string): string {
  return t.replace(/,?\s*INT-\d+\b/g, '').replace(/,?\s*(MINI\s+)?FOLLOW UP\s*\d*\s*$/i, '')
    .replace(/^Da guardare tu:\s*/i, '').replace(/^Bozza per\s+/i, '').replace(/^(mini\s+)?follow up\s*\d*:\s*/i, '').trim()
}

/** Una domanda della Posta che e' un follow-up (o una ripresa): non e' una persona che aspetta. */
export function eSeguito(d: Pick<Domanda, 'titolo' | 'intento'>): boolean {
  return /FOLLOW UP|RIPRESA/i.test(`${d.intento ?? ''} ${d.titolo}`)
}

/** Il perche' di una domanda detto senza le parole interne del sistema («si':», «la seconda testa
 *  dice INCOERENTE», «CANCELLO: ...», «INT-08»). Vuoto se non resta niente. */
export function spiegaDomanda(perche: string | null | undefined): string {
  let t = (perche ?? '').replace(/\s+/g, ' ')
  t = t.replace(/^\s*s[iì]['’]?\s*:\s*/i, '')
  t = t.replace(/,?\s*CANCELLO:.*$/i, '')
  t = t.replace(/la seconda testa dice INCOERENTE:\s*/i, 'il controllo ha fermato la bozza: ')
  t = t.replace(/\(?\bINT-\d+\b\)?/g, '').replace(/\s+([,.;:])/g, '$1').replace(/\s{2,}/g, ' ').trim()
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : ''
}

/** La prima riga che dice qualcosa di una nostra mail (senza «Buongiorno Mario,»). */
export function primaRiga(testo: string, max = 140): string {
  const r = testo.split('\n').map((x) => x.trim())
    .find((x) => x && !/^(buongiorno|buonasera|salve|gentile|gentili|ciao|egregi[oa]|alla cortese)\b/i.test(x)) ?? ''
  return r.length > max ? `${r.slice(0, max - 1).trimEnd()}…` : r
}

// ── la scheda pulita (20/10): il prossimo messaggio di Clara e il sito ──

/** Quello che serve di un lead per dire il suo prossimo messaggio (la riga di prospects). */
export interface LeadPerProssimo {
  analysis_sent_at: string | null; last_reply_at: string | null; no_followup: boolean | null; fuori: boolean | null
  stage: string | null; classificazione: string | null; coda: string | null; awaiting_us: boolean | null
}
/** Una proposta del lead (tabella proposte): `bozza` e `template` vengono da `azione`; `titolo`, `perche`,
 *  `motivo_controllo` (azione.lettura.coerenza_motivo) e `ombra` (azione.ombra) dicono perche' e' ferma. */
export interface PropostaLead {
  id: number; tipo: string; stato: string; at: string; bozza: string | null; template: string | null; risposta: string | null
  titolo?: string | null; perche?: string | null; motivo_controllo?: string | null; ombra?: string | null
}
export interface Prossimo {
  quando: string; giorno: string | null; tipo: string
  /** il testo esatto che partira'; null se Clara lo scrive il giorno stesso, dopo aver riletto il filo */
  testo: string | null
  /** la proposta da cui viene il testo (per non mostrarla due volte nella scheda) */
  proposta: number | null
  /** le proposte da chiudere se Dre lo ferma */
  da_chiudere: number[]
}

const NOMI_GRUPPO: Record<string, string> = {
  'FOLLOW UP 1': 'Primo follow-up', 'FOLLOW UP SU MISURA': 'Follow-up su misura', 'MINI FOLLOW UP': 'Mini follow-up', RIPRESA: 'Ripresa',
  'RINVIO SCADUTO': 'Ripresa dopo il rinvio', 'RICONTATTO OOO': 'Ricontatto dopo le ferie',
}
// come scripts/followup.py: chi non e' piu' un lead non riceve follow-up da nessuna strada
const FERMI_FOLLOWUP = ['negativo', 'soppresso', 'nervoso', 'fuori_target', 'persona_sbagliata']
const STADI_FERMI = ['cliente', 'perso', 'call_fissata', 'rinviato']
const CLASSI_FOLLOWUP = ['positivo', 'tiepido', 'da_classificare']
export const GIORNI_FOLLOWUP = 5

/** IL PROSSIMO MESSAGGIO DI CLARA a questo lead, nell'ordine:
 *  1. una mail gia' scritta (proposta aperta o approvata col testo): quella, parola per parola;
 *  2. il calendario dei follow-up (seguiti_calendario, lo scrive scripts/followup.py): il giorno;
 *  3. la stessa regola di followup.py rifatta qui (analisi + 5 giorni di silenzio, mai prima di oggi).
 *  `nostre`: quando sono partite le nostre mail (il filo), per sapere se un follow-up c'e' gia' stato. */
export function prossimoMessaggio(lead: LeadPerProssimo, proposte: PropostaLead[], calendario: { gruppo: string; il: string } | null,
  nostre: string[], ora: Date = new Date()): Prossimo | null {
  const aperte = proposte.filter((p) => (p.stato === 'aperta' || p.stato === 'approvata') && (p.tipo === 'risposta' || p.tipo === 'umano'))
  const da_chiudere = aperte.map((p) => p.id)
  const scritte = aperte.filter((p) => p.bozza?.trim())
    .sort((a, b) => Number(b.stato === 'approvata') - Number(a.stato === 'approvata') || b.at.localeCompare(a.at))
  const p = scritte[0]
  if (p) {
    return { quando: p.stato === 'approvata' ? 'Parte a minuti' : 'Scritto, non ancora partito', giorno: null,
             tipo: NOMI_GRUPPO[p.template ?? ''] ?? 'Risposta', testo: p.bozza!.trim(), proposta: p.id, da_chiudere }
  }
  if (lead.no_followup || lead.fuori) return null
  const oggi = giornoRoma(ora)
  const nel = (il: string, gruppo: string): Prossimo => {
    const giorno = il < oggi ? oggi : il
    return { quando: nomeGiorno(giorno, ora), giorno, tipo: NOMI_GRUPPO[gruppo] ?? 'Primo follow-up', testo: null, proposta: null, da_chiudere }
  }
  if (calendario) return nel(calendario.il.slice(0, 10), calendario.gruppo)
  // 3. followup.py, main(): analisi mandata, silenzio, nessun follow-up avuto
  const a = lead.analysis_sent_at
  if (!a || lead.coda || lead.awaiting_us) return null
  if (FERMI_FOLLOWUP.includes(lead.classificazione ?? '') || !CLASSI_FOLLOWUP.includes(lead.classificazione ?? 'da_classificare')) return null
  if (STADI_FERMI.includes(lead.stage ?? '')) return null
  if (lead.last_reply_at && lead.last_reply_at > a) return null
  const avuto = proposte.some((x) => /^FOLLOW UP (1|SU MISURA)$/.test(x.template ?? '') && (x.stato !== 'no' || (x.risposta ?? '').startsWith('NO:')))
  if (avuto) return null
  const inviata = a.slice(0, 10)
  if (nostre.some((at) => at > piuGiorni(inviata, 1))) return null
  return nel(piuGiorni(inviata, GIORNI_FOLLOWUP), 'FOLLOW UP 1')
}

/** Il sito com'e' scritto nel database, reso un link che si apre: «esempio.it» → «https://esempio.it».
 *  Quello che non sembra un sito (spazi, niente punto) torna null. */
export function sitoCliccabile(s: string | null | undefined): string | null {
  const t = (s ?? '').trim()
  if (!t || /\s/.test(t)) return null
  if (/^https?:\/\//i.test(t)) return t
  return /^[\w-]+(\.[\w-]+)+/.test(t) ? `https://${t.replace(/^\/+/, '')}` : null
}

/** Il sito detto corto, per leggerlo: senza https, www e la barra finale. */
export function sitoBreve(url: string): string {
  return url.replace(/^https?:\/\//i, '').replace(/^www\./i, '').replace(/\/$/, '')
}

/** Le nostre mail partite dopo la sua ultima risposta (cosa abbiamo gia' fatto). */
export function scrittoDopo(filo: Array<{ at: string | null; chi: 'lui' | 'noi'; testo: string }> | undefined,
  ultima: string | null | undefined): { at: string; testo: string } | null {
  if (!filo?.length || !ultima) return null
  const da = new Date(ultima).getTime()
  const dopo = filo.filter((m) => m.chi === 'noi' && m.at && new Date(m.at).getTime() > da && m.testo.trim())
  const u = dopo[dopo.length - 1]
  return u?.at ? { at: u.at, testo: u.testo } : null
}

// ── risolvere da soli un lead fermo (20/10 sera, Dre: «lo vedevo, ma non potevo agire») ──

/** Il messaggio che aspetta una decisione di Dre: la proposta aperta piu' recente (risposta o umano)
 *  che ha gia' il testo. Le approvate stanno partendo e non si decidono piu'. */
export interface InAttesa { id: number; testo: string; motivo: string; tipo: string }
export function messaggioInAttesa(proposte: PropostaLead[]): InAttesa | null {
  const p = proposte.filter((x) => x.stato === 'aperta' && (x.tipo === 'risposta' || x.tipo === 'umano') && x.bozza?.trim())
    .sort((a, b) => b.at.localeCompare(a.at))[0]
  if (!p) return null
  return { id: p.id, testo: p.bozza!.trim(), motivo: motivoFermo(p), tipo: NOMI_GRUPPO[p.template ?? ''] ?? 'Risposta' }
}

/** Perche' il messaggio e' fermo, in parole normali: il perche' della Posta senza le parole interne,
 *  se no il motivo del controllo (coerenza), se no l'ombra, se no quello che dice il titolo. */
export function motivoFermo(p: Pick<PropostaLead, 'titolo' | 'perche' | 'motivo_controllo' | 'ombra'>): string {
  const perche = spiegaDomanda(p.perche)
  if (perche) return perche
  const controllo = (p.motivo_controllo ?? '').replace(/\s+/g, ' ').trim()
  if (controllo) return `Il controllo ha fermato la bozza: ${controllo}`
  const ombra = (p.ombra ?? '').replace(/\s+/g, ' ').trim()
  if (ombra) return ombra.charAt(0).toUpperCase() + ombra.slice(1)
  return /^Da guardare tu/i.test(p.titolo ?? '') ? 'Clara non era sicura: la guardi tu.' : 'Aspetta un tuo sì.'
}

export const DA_APP = 'Dre (app)'
/** Le note che restano sul lead dopo un gesto dalla scheda (snella_note): la traccia di cosa ha deciso Dre. */
export const NOTE_APP = { mandato: "Dall'app: mandato", non_mandato: "Dall'app: non mandato", chiuso: "Dall'app: chiuso, non interessato" } as const

/** L'analisi va in allegato? Se c'e' il PDF, non e' ancora stata mandata e la bozza non la porta gia'
 *  (il postino manda.py la allega alla prima risposta; qui lo si scrive, cosi' e' detto). A chi l'ha gia'
 *  ricevuta non si rimanda. */
export function allegaAnalisi(azione: { bozza?: unknown; allega?: unknown }, lead: { analysis_pdf: string | null; analysis_sent_at: string | null }): boolean {
  if (azione.allega === true) return true
  if (!lead.analysis_pdf || lead.analysis_sent_at) return false
  return !String(azione.bozza ?? '').includes(lead.analysis_pdf)
}

/** «MANDA»: com'e' `azione` dopo il si' di Dre dalla scheda. manda.py vuole `approvata_da`; il resto
 *  della bozza non si tocca (il testo non si modifica dalla scheda). */
export function azioneApprovata(azione: Record<string, unknown>, lead: { analysis_pdf: string | null; analysis_sent_at: string | null },
  ora: Date = new Date()): Record<string, unknown> {
  const out: Record<string, unknown> = { ...azione, approvata_da: DA_APP, approvata_il: ora.toISOString() }
  if (allegaAnalisi(azione, lead)) out.allega = true
  return out
}

/** «NON MANDARE»: la proposta si chiude col motivo, come un no di Dre dalla Posta. */
export function scritturaNonMandare(ora: Date = new Date()): { stato: 'no'; risposta: string; risposta_il: string } {
  return { stato: 'no', risposta: "NO: Dre dall'app", risposta_il: ora.toISOString() }
}

/** «CHIUDI: NON INTERESSATO»: il lead e' un no deciso da una persona (il database lo segna in
 *  `deciso` da solo), niente follow-up, lo stato di Dre «Non interessato», le mail aperte chiuse. */
export function scrittureChiusura(ora: Date = new Date()): {
  lead: { classificazione: 'negativo'; no_followup: true; coda: null }
  decisione: { stato: 'Non interessato' }
  proposte: { stato: 'no'; risposta: string; risposta_il: string }
} {
  return {
    lead: { classificazione: 'negativo', no_followup: true, coda: null },
    decisione: { stato: 'Non interessato' },
    proposte: { stato: 'no', risposta: "NO: Dre dall'app, lead chiuso", risposta_il: ora.toISOString() },
  }
}
