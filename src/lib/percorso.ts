import type { PipelineStage, Prospect, Stage } from './types'
import { giorno, vivo } from './regole'

// IL PERCORSO (Dre, 30/9: «bisogna ricostruire da zero, partendo dalle fondamenta,
// first principles, non a caso»). Ogni azienda ha due cose sole: la TAPPA e di chi
// e' la PALLA. La tappa la tiene il database (schema_v72, colonna tappa, calcolata
// dai campi di oggi); qui ci sono i nomi, l'ordine e le regole per muoversi, una
// volta sola per tutte le schermate nuove. Le decisioni stanno nel vault: «Il
// Workspace da zero, le fondamenta (30-9-2026)».

export type Tappa = 'nuovo' | 'risposta' | 'analisi' | 'follow_up' | 'conoscitiva' | 'tecnica' | 'avvio' | 'prova' | 'cliente' | 'perso'

export const NOME_TAPPA: Record<Tappa, string> = {
  nuovo: 'Nuovo', risposta: 'Risposta', analisi: 'Analisi', follow_up: 'Follow-up',
  conoscitiva: 'Conoscitiva', tecnica: 'Tecnica', avvio: 'Avvio', prova: 'Prova', cliente: 'Cliente', perso: 'Perso',
}

// il cammino, in ordine: prima della call le muove Clara (analisi, follow-up), dalla
// Conoscitiva in poi le muove chi fa le call
export const CAMMINO: Tappa[] = ['risposta', 'analisi', 'follow_up', 'conoscitiva', 'tecnica', 'avvio', 'prova', 'cliente']
export const PRIMA_DELLA_CALL: Tappa[] = ['risposta', 'analisi', 'follow_up']
export const IN_TRATTATIVA: Tappa[] = ['conoscitiva', 'tecnica', 'avvio', 'prova']
const DELLE_CALL: Tappa[] = ['conoscitiva', 'tecnica', 'avvio']

type Campi = Pick<Prospect, 'stage' | 'pipeline_stage' | 'fuori' | 'analysis_sent'> & { tappa?: string | null }

/** La tappa: quella del database, o la stessa regola di tappa_di() (schema_v72) dove la colonna non c'e' ancora. */
export function tappaDi(p: Campi): Tappa {
  if (p.tappa) return p.tappa as Tappa
  const fuori = Boolean(p.fuori)
  if ((fuori && p.pipeline_stage === 'cliente') || (!fuori && p.stage === 'cliente')) return 'cliente'
  if ((fuori && p.pipeline_stage === 'perso') || (!fuori && p.stage === 'perso')) return 'perso'
  if (fuori) return (p.pipeline_stage ?? 'conoscitiva') as Tappa
  if (p.stage === 'call_fissata') return 'conoscitiva'
  if (p.stage === 'in_follow_up') return 'follow_up'
  if (p.stage === 'analisi_inviata' || p.analysis_sent) return 'analisi'
  if (p.stage === 'risposto' || p.stage === 'rinviato') return 'risposta'
  return 'nuovo'
}

/** Dove porta «Avanza»: prima della call si entra dalla Conoscitiva, poi una tappa alla volta. */
export function prossima(t: Tappa): Tappa | null {
  if (PRIMA_DELLA_CALL.includes(t)) return 'conoscitiva'
  const i = CAMMINO.indexOf(t)
  return i >= 0 && i < CAMMINO.length - 1 ? CAMMINO[i + 1] : null
}

/** Un passo indietro, solo dentro la trattativa: prima della call le tappe le muove Clara. */
export function precedente(t: Tappa): Tappa | 'lead' | null {
  if (t === 'conoscitiva') return 'lead'
  const i = CAMMINO.indexOf(t)
  return i > 3 ? CAMMINO[i - 1] : null
}

/** La palla: tocca a noi se ha scritto lui per ultimo, o se c'e' una cosa nostra scaduta. */
export function toccaANoi(p: Pick<Prospect, 'awaiting_us' | 'next_action_date'>, bozzaPronta = false): boolean {
  return Boolean(p.awaiting_us) || bozzaPronta || Boolean(p.next_action_date && p.next_action_date <= giorno())
}

export function inBacheca(p: Campi & Pick<Prospect, 'classificazione'>): boolean {
  const t = tappaDi(p)
  return t !== 'nuovo' && t !== 'perso' && t !== 'cliente' && vivo(p)
}

export type Mossa = { patch: Partial<Prospect>; nota: string } | { no: string }

const fraDueMesi = () => { const d = new Date(); d.setMonth(d.getMonth() + 2); return giorno(d) }

/**
 * Cosa scrivere per portare un'azienda in un'altra tappa. Le regole sono quelle
 * della bacheca di sempre (2/9, 9/9, 14/9), con una sola differenza decisa il 30/9:
 * il riassunto della call non blocca piu', l'avanzamento lo ricorda nella nota.
 */
export function mossa(p: Campi & Pick<Prospect, 'prova_inizio'>, verso: Tappa | 'lead', opz: { motivo?: string; riassunto?: boolean } = {}): Mossa {
  const da = tappaDi(p)
  const pulisci = { next_action: null, next_action_date: null }
  if (verso === 'perso') {
    const motivo = (opz.motivo ?? '').trim()
    if (!motivo) return { no: 'Scrivi il motivo: resta nella storia e torna utile per i prossimi simili.' }
    const patch: Partial<Prospect> = p.fuori
      ? { pipeline_stage: 'perso' as PipelineStage, lost_reason: motivo, ...pulisci }
      : { stage: 'perso' as Stage, lost_reason: motivo, ...pulisci }
    return { patch, nota: `Segnato come perso: ${motivo}` }
  }
  if (verso === 'lead') {
    if (!p.fuori) return { no: 'È già fra i lead.' }
    return { patch: { fuori: false, fuori_at: null, pipeline_stage: null, ...pulisci }, nota: 'Uscita dalla pipeline: torna fra i lead.' }
  }
  if (da === 'perso') {
    // riaprire: si torna nella trattativa dalla tappa scelta
    if (!IN_TRATTATIVA.includes(verso)) return { no: 'Si riapre dentro la trattativa: dalla Conoscitiva in poi.' }
    return { patch: { fuori: true, pipeline_stage: verso as PipelineStage, lost_reason: null, ...pulisci }, nota: `Riaperta: torna in ${NOME_TAPPA[verso]}` }
  }
  if (PRIMA_DELLA_CALL.includes(verso)) return { no: 'Prima della call le tappe le muove Clara: quando parte l\'analisi o il follow-up.' }
  if (PRIMA_DELLA_CALL.includes(da)) {
    if (verso !== 'conoscitiva') return { no: 'Si entra dalla Conoscitiva, la prima call.' }
    return { patch: { fuori: true, fuori_at: new Date().toISOString(), pipeline_stage: 'conoscitiva', awaiting_us: false }, nota: 'Entra in Conoscitiva.' }
  }
  const salto = CAMMINO.indexOf(verso) - CAMMINO.indexOf(da)
  if (salto === 0) return { no: `È già in ${NOME_TAPPA[verso]}.` }
  if (salto > 1) return { no: 'Una tappa alla volta: le call si fanno in ordine.' }
  const patch: Partial<Prospect> = { pipeline_stage: verso as PipelineStage, ...pulisci }
  if (verso === 'prova' && !p.prova_inizio) Object.assign(patch, { prova_inizio: giorno(), prova_fine: fraDueMesi(), contratto: 'prova' })
  if (verso === 'cliente') Object.assign(patch, { contratto: 'stable' })
  if (da === 'cliente') Object.assign(patch, { contratto: null })
  if (salto < 0) return { patch, nota: `Torna in ${NOME_TAPPA[verso]}` }
  const senza = DELLE_CALL.includes(da) && !opz.riassunto ? ` (senza riassunto della ${NOME_TAPPA[da]})` : ''
  return { patch, nota: verso === 'cliente' ? 'DIVENTA CLIENTE.' : `Passa a ${NOME_TAPPA[verso]}${senza}` }
}
