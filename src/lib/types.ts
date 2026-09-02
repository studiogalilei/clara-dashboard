export type Stage =
  | 'nuovo'
  | 'risposto'
  | 'analisi_inviata'
  | 'in_follow_up'
  | 'call_fissata'
  | 'cliente'
  | 'perso'
  | 'rinviato'

export const STAGES: Stage[] = [
  'nuovo',
  'risposto',
  'analisi_inviata',
  'in_follow_up',
  'call_fissata',
  'cliente',
  'perso',
  'rinviato',
]

export const STAGE_LABEL: Record<Stage, string> = {
  nuovo: 'Nuovo',
  risposto: 'Risposto',
  analisi_inviata: 'Analisi inviata',
  in_follow_up: 'In follow-up',
  call_fissata: 'Call fissata',
  cliente: 'Cliente',
  perso: 'Perso',
  rinviato: 'Rinviato',
}

// Le fasi della pipeline agenzia — i nomi di Dre (28/8).
// prospect NON e' un pipeline_stage: e' chi ha risposto e non e' ancora fuori.
export type PipelineStage = 'conoscitiva' | 'tecnica' | 'avvio' | 'cliente' | 'perso'

export const PIPELINE_STAGES: PipelineStage[] = [
  'conoscitiva',
  'tecnica',
  'avvio',
  'cliente',
  'perso',
]

export const PIPELINE_LABEL: Record<PipelineStage, string> = {
  conoscitiva: 'Conoscitiva',
  tecnica: 'Tecnica',
  avvio: 'Avvio',
  cliente: 'Cliente',
  perso: 'Perso',
}

export const PIPELINE_HINT: Record<PipelineStage, string> = {
  conoscitiva: 'Prima call: chi sono, cosa vogliono',
  tecnica: 'Con Carlo: il come',
  avvio: 'Hanno detto sì',
  cliente: 'Pagano',
  perso: 'Non se ne fa niente',
}

// La fase successiva, per il bottone «Passa a …» (pedaggio: serve il transcript)
export const PIPELINE_NEXT: Partial<Record<PipelineStage, PipelineStage>> = {
  conoscitiva: 'tecnica',
  tecnica: 'avvio',
  avvio: 'cliente',
}

export type Classificazione =
  | 'da_classificare'
  | 'positivo'
  | 'tiepido'
  | 'negativo'
  | 'ooo'
  | 'rinvio'
  | 'fuori_target'
  | 'soppresso'

export const CLASSIFICAZIONI: Classificazione[] = [
  'da_classificare',
  'positivo',
  'tiepido',
  'negativo',
  'ooo',
  'rinvio',
  'fuori_target',
  'soppresso',
]

export const CLS_LABEL: Record<Classificazione, string> = {
  da_classificare: 'Da classificare',
  positivo: 'Positivo',
  tiepido: 'Tiepido',
  negativo: 'Negativo',
  ooo: 'Fuori ufficio',
  rinvio: 'Rinvio',
  fuori_target: 'Fuori target',
  soppresso: 'Soppresso',
}

// Il mercato del prospect, dalla base precalcolata (333 combinazioni settore x provincia)
export interface Market {
  ricerche: number          // ricerche al mese nella zona
  cpc: number               // costo per clic di cima pagina, in euro
  mesi_vivi: number         // per quanti mesi l'anno la domanda e' viva (0-12)
  bars: Array<[number, 0 | 1]>  // 12 barre: [altezza in % del massimo, e' il picco]
  fit: 'si' | 'no'
  zona: string              // es. "provincia di Padova"
  misurato_il: string       // ISO date
}

export interface Prospect {
  id: string
  sg_id: number | null   // SG-000001: l'identita' permanente, non cambia mai
  email: string
  name: string | null
  role: string | null
  phone: string | null
  linkedin: string | null
  company: string | null
  website: string | null
  sector: string | null
  city: string | null
  descrizione: string | null   // chi sono, 2-3 righe (riempita in automatico)
  socials: Record<string, string>
  owner_name: string | null
  campaign: string | null
  stage: Stage
  first_reply_at: string | null
  last_reply_at: string | null
  analysis_sent: boolean
  analysis_sent_at: string | null
  analysis_pdf: string | null
  next_action: string | null
  next_action_date: string | null
  no_followup: boolean
  deal_value: number | null
  lost_reason: string | null
  notes: string | null
  enriched: Record<string, 'auto' | 'manual'>
  updated_at: string
  // conversazione
  awaiting_us: boolean
  classificazione: Classificazione | null
  followup_due: string | null
  ooo_until: string | null
  // pipeline agenzia
  fuori: boolean
  fuori_at: string | null
  pipeline_stage: PipelineStage | null
  // v4 — il cruscotto
  fuori_binario: 'si' | 'no' | null   // null = mai chiesto a Dre: mail ferme
  market: Market | null
  contratto: 'prova' | 'stable' | null
  canone: number | null
}

export interface Interaction {
  id: string
  prospect_id: string
  at: string
  kind: 'email_in' | 'email_out' | 'analisi' | 'followup' | 'call' | 'nota' | 'transcript' | 'postit' | 'prep'
  body: string | null
}

export const KIND_LABEL: Record<Interaction['kind'], string> = {
  email_in: 'Risposta del lead',
  email_out: 'Email inviata',
  analisi: 'Analisi inviata',
  followup: 'Follow-up',
  call: 'Call',
  nota: 'Nota',
  transcript: 'Transcript call',
  postit: 'Post-it',
  prep: 'Prep call',
}

export interface AgendaItem {
  id: number
  at: string
  titolo: string
  tipo: string | null
  prospect_id: string | null
  link?: string | null
  fonte: string
}
