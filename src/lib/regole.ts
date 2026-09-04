// Le regole di casa in un posto solo (2/9).
// Prima erano copiate a mano in quattro file e i numeri divergevano:
// la home diceva 12 prospect e la bacheca ne mostrava 20.

import type { Prospect } from './types'

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

// la stessa domanda nella lingua di PostgREST, per i conteggi sul database
export const PROSPECT_QUERY = {
  fuori: false,
  esclusi: "stage.not.in.(\"perso\",\"cliente\",\"nuovo\")",
}

// in pipeline: fra la prima call e la firma
export function inPipeline(p: Fase): boolean {
  return p.fuori && p.pipeline_stage !== 'cliente' && p.pipeline_stage !== 'perso'
}

// ── il giorno, in ora italiana ────────────────────────────────────
// toISOString() dà il giorno UTC: fra mezzanotte e le 2 era ancora ieri.
export function giorno(d: Date | string = new Date()): string {
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
import { supabase } from './supabase'
import { PIPELINE_LABEL, type PipelineStage } from './types'

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
