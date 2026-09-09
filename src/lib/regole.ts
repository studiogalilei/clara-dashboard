// Le regole di casa in un posto solo (2/9).
// Prima erano copiate a mano in quattro file e i numeri divergevano:
// la home diceva 12 prospect e la bacheca ne mostrava 20.

import { supabase } from './supabase'
import { PIPELINE_LABEL, type Prospect, type PipelineStage } from './types'

// ── chi è vivo ────────────────────────────────────────────────────
// I morti dichiarati non si contano, non si ricontattano, non appaiono.
export const MORTI = ['negativo', 'fuori_target', 'soppresso']

// lo stesso filtro, nella lingua di PostgREST
export const VIVI = `classificazione.is.null,classificazione.not.in.("${MORTI.join('","')}")`

export function vivo(p: Pick<Prospect, 'classificazione'>): boolean {
  return !MORTI.includes(p.classificazione ?? '')
}

// ── dove sta uno ──────────────────────────────────────────────────
// Vale sia per chi è passato dalla pipeline sia per i record vecchio stile,
// che hanno pipeline_stage vuoto e la fase scritta in stage.
type Fase = Pick<Prospect, 'fuori' | 'stage' | 'pipeline_stage'>

export function eCliente(p: Fase): boolean {
  return (p.fuori && p.pipeline_stage === 'cliente') || (!p.fuori && p.stage === 'cliente')
}

export function ePerso(p: Fase): boolean {
  return (p.fuori && p.pipeline_stage === 'perso') || (!p.fuori && p.stage === 'perso')
}

// scartato: non era roba nostra (agenzia, concorrente, casella privacy,
// mercato che non vale). E' il morto dichiarato che NON e' un perso.
export function eScartato(p: Fase & Pick<Prospect, 'classificazione'>): boolean {
  return !vivo(p) && !ePerso(p)
}

// «quando lo risento» e' una domanda sola e ha un campo solo: next_action_date.
// Le due colonne vecchie contano finche' quella e' vuota, poi spariranno.
export function quandoRisentirlo(p: Pick<Prospect, 'next_action_date' | 'ooo_until' | 'followup_due'>): string | null {
  return p.next_action_date ?? p.ooo_until ?? p.followup_due ?? null
}

// storia finita: non si conta più il tempo che passa
export function chiuso(p: Fase & Pick<Prospect, 'classificazione'>): boolean {
  return eCliente(p) || ePerso(p) || !vivo(p)
}

// passato a qualcun altro: la terza uscita, ne' vinto ne' perso (Dre, 3/9)
export function passato(p: Fase): boolean {
  return Boolean((p as { passato_a?: string | null }).passato_a)
}

// un prospect e' chi non e' ancora in pipeline e non e' uscito da nessuna
// delle tre porte. Prima questa regola era scritta in tre punti diversi e i
// tre numeri non tornavano (revisione 4/9)
export function eProspect(p: Fase & Pick<Prospect, 'classificazione'>): boolean {
  return !p.fuori && !eCliente(p) && !ePerso(p) && vivo(p) && !passato(p)
}

// le stesse domande nella lingua di PostgREST, per quando a contare e' il
// database e non il browser. Devono dare gli stessi insiemi delle funzioni
// qui sopra: se divergono, la home e la bacheca ricominciano a litigare.
export const CLIENTI_QUERY =
  'and(fuori.eq.true,pipeline_stage.eq.cliente),and(fuori.eq.false,stage.eq.cliente)'

// il minimo che una catena di supabase-js deve saper fare per essere filtrata
// qui dentro: i generici veri non si lasciano passare in giro come valori
export interface Filtro {
  eq(c: string, v: unknown): Filtro
  neq(c: string, v: unknown): Filtro
  is(c: string, v: unknown): Filtro
  or(s: string): Filtro
}

export function soloProspect(q: Filtro): Filtro {
  return q.eq('fuori', false)
    .neq('stage', 'nuovo').neq('stage', 'perso').neq('stage', 'cliente')
    .is('passato_a', null)
    .or(VIVI)
}

// in pipeline: fra la prima call e la firma
export function inPipeline(p: Fase): boolean {
  return p.fuori && p.pipeline_stage !== 'cliente' && p.pipeline_stage !== 'perso'
}

// ── il ricorrente mensile, un numero solo ─────────────────────────
// Prima ognuna delle tre schermate lo sommava sulla propria pagina di
// risultati: la bacheca su 300 righe, Tutti su 500, i Numeri su un altro
// taglio ancora. Stessa domanda, tre cifre. Adesso si chiede al database
// una volta sola e si somma su tutti i clienti (revisione 4/9).
export async function ricorrenteMensile(): Promise<{
  mese: number; quanti: number; senza: number; problema: string | null
}> {
  const { data, error } = await supabase
    .from('prospects')
    .select('canone, fuori, stage, pipeline_stage')
    .or(CLIENTI_QUERY)
    .order('canone', { ascending: false, nullsFirst: false })
    .limit(2000)
  if (error) return { mese: 0, quanti: 0, senza: 0, problema: error.message }
  const clienti = ((data ?? []) as Array<Fase & { canone: number | null }>).filter(eCliente)
  return {
    mese: clienti.reduce((t, c) => t + (Number(c.canone) || 0), 0),
    quanti: clienti.length,
    senza: clienti.filter((c) => !c.canone).length,
    problema: null,
  }
}

// ── quanti ce n'e' in ogni fase ───────────────────────────────────
// Lo stesso nome valeva due numeri a un click di distanza: la home li
// contava sul database, la bacheca contava le 300 righe che era riuscita a
// scaricare, e lo scriveva in fondo alla pagina come una confessione. Ora la
// domanda e' una e la fa il database, per tutte e due (revisione 4/9).
export type Fascia = 'prospect' | 'conoscitiva' | 'tecnica' | 'avvio' | 'prova' | 'cliente' | 'perso' | 'scartato'


const DOMANDE: Record<Fascia, (q: Filtro) => Filtro> = {
  prospect: soloProspect,
  conoscitiva: (q) => q.eq('fuori', true).or('pipeline_stage.is.null,pipeline_stage.eq.conoscitiva'),
  tecnica: (q) => q.eq('fuori', true).eq('pipeline_stage', 'tecnica'),
  avvio: (q) => q.eq('fuori', true).eq('pipeline_stage', 'avvio'),
  prova: (q) => q.eq('fuori', true).eq('pipeline_stage', 'prova'),
  cliente: (q) => q.or(CLIENTI_QUERY),
  perso: (q) => q.or('and(fuori.eq.true,pipeline_stage.eq.perso),and(fuori.eq.false,stage.eq.perso)'),
  // i morti dichiarati che non sono persi: non era roba nostra
  // (stage.neq.perso: chi e' negativo E perso conta fra i persi, non due volte)
  scartato: (q) => q.or(`and(fuori.eq.false,stage.neq.perso,classificazione.in.("${MORTI.join('","')}"))`),
}

export const FASCE = Object.keys(DOMANDE) as Fascia[]

export async function contaFasi(): Promise<Record<Fascia, number>> {
  const esiti = await Promise.all(FASCE.map((f) =>
    DOMANDE[f](supabase.from('prospects')
      .select('*', { count: 'exact', head: true }) as unknown as Filtro) as unknown as Promise<{ count: number | null }>))
  const out = {} as Record<Fascia, number>
  FASCE.forEach((f, i) => { out[f] = esiti[i]?.count ?? 0 })
  return out
}

// ── nascere una task, da una porta sola ───────────────────────────
// Le task si creano da quattro posti (Task, la scheda di un cliente, Clara,
// e adesso il Calendario) e ognuno si ricopiava le stesse quattro righe:
// chi e' il padrone, chi l'ha mandata, che ordine ha, se e' una proposta.
// Bastava scordarsene una perche' la task finisse nella lista di un altro,
// ed e' gia' successo. Adesso la porta e' una (revisione 4/9).
export interface TaskRiga {
  id: number
  at: string
  titolo: string
  dettagli: string | null
  scadenza: string | null
  ordine: number
  colore: string | null
  fatta: boolean
  fatta_il: string | null
  owner: string | null
  da: string | null
  stato: 'proposta' | 'accettata' | 'rimandata' | 'fatta'
  motivo: string | null
}

export interface NuovaTask {
  titolo: string
  scadenza?: string | null
  prospect_id?: string | null
  // se la mandi a qualcun altro nasce «proposta»: entra nella sua lista solo
  // quando lui la accetta (Dre, 3/9)
  perChi?: string | null
  // chi ha la lista sott'occhio sa gia' dove va in cima e non la richiede
  ordine?: number
}

export async function creaTask(t: NuovaTask): Promise<{ task: TaskRiga | null; problema: string | null }> {
  const titolo = t.titolo.trim()
  if (!titolo) return { task: null, problema: 'Una task senza titolo non è una task.' }

  const { data: sess } = await supabase.auth.getSession()
  const io = sess.session?.user?.id ?? null

  let ordine = t.ordine
  if (ordine === undefined) {
    // in cima alla lista: la piu' piccola meno uno. Con -1 fisso due task
    // nate da due schermate diverse si accavallavano
    const { data: prima } = await supabase.from('task')
      .select('ordine').order('ordine', { ascending: true }).limit(1).single()
    ordine = Math.min(0, Number((prima as { ordine?: number } | null)?.ordine ?? 0)) - 1
  }

  const altrui = Boolean(t.perChi && t.perChi !== io)
  const { data, error } = await supabase.from('task').insert({
    titolo,
    scadenza: t.scadenza || null,
    prospect_id: t.prospect_id || null,
    fatta: false,
    ordine,
    owner: altrui ? t.perChi : io,
    da: io,
    stato: altrui ? 'proposta' : 'accettata',
  }).select().single()

  if (error || !data) {
    return { task: null, problema: error?.message ?? 'la task non è stata salvata' }
  }
  return { task: data as TaskRiga, problema: null }
}

// ── la coda di oggi, una sola ─────────────────────────────────────
// «Cosa devo fare oggi» era scritta tre volte: il saluto di Clara la contava
// in un modo, il Radar in un altro e la pagina Task in un terzo, con gruppi,
// filtri e tetti diversi. Due di quei numeri stanno sulla stessa schermata e
// non tornavano mai. Adesso la domanda si fa qui, una volta (revisione 4/9).
//
// Quattro ragioni per cui uno finisce nella coda, in ordine di urgenza. Chi
// ne ha piu' d'una compare una volta sola, con la prima.
export type Ragione = 'rispondi' | 'followup' | 'ricontatto' | 'rientro'

export interface VoceCoda {
  p: Prospect
  ragione: Ragione
  data: string | null      // la data che l'ha messo in coda
  fermoDa: number | null   // giorni dall'analisi, quando e' quello che conta
}

// quanti giorni di silenzio dopo l'analisi prima di considerarlo dovuto
export const GIORNI_FOLLOWUP = 5

export async function codaDiOggi(): Promise<{ voci: VoceCoda[]; problema: string | null }> {
  const today = oggi()
  const [dr, fu, ri, oo] = await Promise.all([
    supabase.from('prospects').select('*')
      .eq('awaiting_us', true).eq('fuori', false).or(VIVI)
      .order('last_reply_at', { ascending: false, nullsFirst: false }).limit(300),
    supabase.from('prospects').select('*')
      .in('stage', ['analisi_inviata', 'in_follow_up'])
      .eq('no_followup', false).eq('awaiting_us', false).eq('fuori', false).or(VIVI)
      .order('analysis_sent_at', { ascending: true, nullsFirst: false }).limit(500),
    supabase.from('prospects').select('*')
      .not('next_action_date', 'is', null).lte('next_action_date', today).or(VIVI)
      .order('next_action_date', { ascending: true }).limit(300),
    supabase.from('prospects').select('*')
      .not('ooo_until', 'is', null).lte('ooo_until', today)
      .eq('no_followup', false).eq('fuori', false).or(VIVI)
      .order('ooo_until', { ascending: true }).limit(300),
  ])
  const problema = dr.error?.message ?? fu.error?.message ?? ri.error?.message ?? oo.error?.message ?? null

  const voci: VoceCoda[] = []
  const visti = new Set<string>()
  // chi e' gia' cliente, chi e' perso e chi e' passato a un altro non ha una
  // coda: e' la stessa regola che decide tutto il resto dell'app
  const aggiungi = (p: Prospect, ragione: Ragione, data: string | null, fermoDa: number | null) => {
    if (visti.has(p.id) || eCliente(p) || ePerso(p) || passato(p)) return
    visti.add(p.id)
    voci.push({ p, ragione, data, fermoDa })
  }

  for (const p of ((dr.data as Prospect[]) ?? [])) aggiungi(p, 'rispondi', p.last_reply_at, null)

  for (const p of ((fu.data as Prospect[]) ?? [])) {
    const g = giorniDa(p.analysis_sent_at)
    // una data sua vince sul conto dei giorni: e' il motivo per cui e' qui
    if (p.followup_due) { if (p.followup_due.slice(0, 10) <= today) aggiungi(p, 'followup', p.followup_due, g) }
    else if (g !== null && g >= GIORNI_FOLLOWUP) aggiungi(p, 'followup', p.analysis_sent_at, g)
  }

  for (const p of ((ri.data as Prospect[]) ?? [])) aggiungi(p, 'ricontatto', p.next_action_date, null)
  for (const p of ((oo.data as Prospect[]) ?? [])) aggiungi(p, 'rientro', p.ooo_until, null)

  return { voci, problema }
}

export function giorniDa(iso: string | null | undefined): number | null {
  if (!iso) return null
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return null
  return Math.floor((Date.now() - t) / 86400000)
}

// ── il giorno, in ora italiana ────────────────────────────────────
// toISOString() dà il giorno UTC: fra mezzanotte e le 2 era ancora ieri.
export function giorno(d: Date | string | null | undefined = new Date()): string {
  // accetta il vuoto come tutte le sue sorelle (fmtDate, daysAgo): era
  // l'unica a spaccarsi su null, e le colonne di date nel database sono
  // quasi tutte nullable. Trovata dal primo giro di test (7/9)
  if (d == null) return ''
  const x = typeof d === 'string' ? new Date(d) : d
  if (Number.isNaN(x.getTime())) return ''
  return `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, '0')}-${String(x.getDate()).padStart(2, '0')}`
}

export function oggi(): string {
  return giorno()
}

// l'ora locale di un timestamp, hh:mm
export function ora(d: Date | string): string {
  const x = typeof d === 'string' ? new Date(d) : d
  if (Number.isNaN(x.getTime())) return ''
  return `${String(x.getHours()).padStart(2, '0')}:${String(x.getMinutes()).padStart(2, '0')}`
}

// ── il trattino lungo è bandito (Dre, 31/8) ───────────────────────
// Vale per tutto quello che scrive Clara, dal cron come dal browser.
export function pulisci(t: string): string {
  return t.replace(/\s*—\s*/g, ': ').replace(/–/g, '-')
}

// ── il pedaggio, da una porta sola ────────────────────────────────
// Prima la bacheca e la scheda facevano due domande diverse al database
// e potevano dare verdetti opposti sullo stesso prospect.
export function marcaFase(fase: PipelineStage): string {
  return `[${PIPELINE_LABEL[fase]}]`
}

export async function pedaggioPagato(prospectId: string, fase: PipelineStage): Promise<boolean> {
  const { data } = await supabase.from('interactions').select('*')
    .eq('prospect_id', prospectId).eq('kind', 'transcript')
    .order('at', { ascending: false }).limit(20)
  return ((data as Array<{ body: string | null }> | null) ?? [])
    .some((t) => (t.body ?? '').startsWith(marcaFase(fase)))
}
