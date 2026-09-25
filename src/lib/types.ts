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
// 9/9, Dre: fra avvio e cliente c'e' il periodo di prova (due mesi, con le date):
// quasi tutti i clienti cominciano da li'. Poi si ridiscute e si passa al retainer.
export type PipelineStage = 'conoscitiva' | 'tecnica' | 'avvio' | 'prova' | 'cliente' | 'perso'

export const PIPELINE_STAGES: PipelineStage[] = [
  'conoscitiva',
  'tecnica',
  'avvio',
  'prova',
  'cliente',
  'perso',
]

export const PIPELINE_LABEL: Record<PipelineStage, string> = {
  conoscitiva: 'Conoscitiva',
  tecnica: 'Tecnica',
  avvio: 'Avvio',
  prova: 'Prova',
  cliente: 'Cliente',
  perso: 'Perso',
}

export const PIPELINE_HINT: Record<PipelineStage, string> = {
  conoscitiva: 'Prima call: chi sono, cosa vogliono',
  tecnica: 'Con Carlo: il come',
  avvio: 'Hanno detto sì',
  prova: 'Due mesi di prova, poi si ridiscute',
  cliente: 'Retainer',
  perso: 'Non se ne fa niente',
}

// La fase successiva, per il bottone «Passa a …» (pedaggio: serve il transcript)
export const PIPELINE_NEXT: Partial<Record<PipelineStage, PipelineStage>> = {
  conoscitiva: 'tecnica',
  tecnica: 'avvio',
  avvio: 'prova',
  prova: 'cliente',
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
  | 'persona_sbagliata'
  | 'nervoso'

export const CLASSIFICAZIONI: Classificazione[] = [
  'da_classificare',
  'positivo',
  'tiepido',
  'negativo',
  'ooo',
  'rinvio',
  'fuori_target',
  'soppresso',
  'persona_sbagliata',
  'nervoso',
]

// Le stesse parole della bacheca (Caldi, Tiepidi, Rinviati, Da capire): un
// nome solo per ogni cosa, nel menu, nella scheda e nella bocca di Clara
// (glossario, 24/9). Le chiavi nel database non cambiano.
// Le parole di Dre (25/9): positivo, negativo, parziale, richiesta di
// rimozione, persona sbagliata, nervoso, fuori ufficio. Piu' rinviato, fuori
// target e «da capire». Le chiavi nel database non cambiano.
export const CLS_LABEL: Record<Classificazione, string> = {
  da_classificare: 'Da capire',
  positivo: 'Positivo',
  tiepido: 'Parziale',
  negativo: 'Negativo',
  ooo: 'Fuori ufficio',
  rinvio: 'Rinviato',
  fuori_target: 'Fuori target',
  soppresso: 'Richiesta di rimozione',
  persona_sbagliata: 'Persona sbagliata',
  nervoso: 'Nervoso',
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
  prova_inizio: string | null
  prova_fine: string | null
  // pipeline agenzia
  fuori: boolean
  fuori_at: string | null
  pipeline_stage: PipelineStage | null
  // v4 — il cruscotto
  fuori_binario: 'si' | 'no' | null   // null = mai chiesto a Dre: mail ferme
  market: Market | null
  contratto: 'prova' | 'stable' | null
  canone: number | null
  // chi la segue: si scrive a mano nel Foglio, e ci si scrive da solo chi
  // aggiunge un'azienda. E' anche una delle chiavi del perimetro
  chi_segue: string | null
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
  // quello che Clara prepara prima della call (schema_v43)
  preparazione?: string | null
  preparata_il?: string | null
}
