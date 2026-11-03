// IL DESK (4/11/2026): i dati. Tutto passa dalle funzioni del database fatte per il Desk
// (schema_v104: clara_coda, clara_relazione, clara_cerca, clara_call) e dalle scritture su
// clara_decisioni, che il database lascia fare solo ai ceo. Nessuna mail parte da qui: il Desk
// approva, il postino (scripts/clara_manda.py) manda entro cinque minuti, o subito se il
// direttore risponde alla chiamata.
import { supabase } from '../lib/supabase'
export { aggiungiNota } from '../snella/dati'

export type Mossa = 'send_analysis' | 'reply' | 'offer_slots' | 'book_meeting' | 'callback' | 'wait' | 'close' | 'escalate'
export type Stato = 'proposta' | 'approvata' | 'in_invio' | 'inviata' | 'scartata' | 'superata' | 'fatta'

export interface Prova { messaggio: number; frase: string }
export interface Giudizio { pericoloso?: boolean; errore_pericoloso?: string; mossa?: string; mossa_migliore?: string; testo?: string; nota?: string; errore?: string }

export interface Decisione {
  id: string; prospect_id: string; risposta_il: string; mossa: Mossa; owner: string | null; entro_il: string | null
  testo: string | null; testo_clara: string | null; perche: string | null; prove: Prova[] | null
  richiamo: { numero?: string; quando?: string; perche?: string } | null
  segnali: string[] | null; giudice: Giudizio | null; stato: Stato; lead_testo: string | null
  approvata_il: string | null; inviata_il: string | null; verificata_il: string | null; errore: string | null
  esito: string | null; esito_il: string | null; creato_il: string; versione: string; dollari: number | null
  dre_giudizio: 'ok' | 'no' | null
  azienda: string | null; persona: string | null; ruolo: string | null; email: string; citta: string | null; settore: string | null
  telefono: string | null; sito: string | null; analisi_pdf: boolean; analisi_mandata: boolean; fase: string | null
  classe: string | null; ultima_risposta: string | null; prossima_call: string | null
}

export interface Messaggio { at: string; tipo: 'email_in' | 'email_out'; testo: string | null; casella: string | null }
export interface Relazione {
  lead: {
    id: string; azienda: string | null; persona: string | null; ruolo: string | null; email: string; citta: string | null
    settore: string | null; telefono: string | null; sito: string | null; analisi_pdf: string | null; analisi_mandata: boolean
    analisi_il: string | null; fase: string | null; classe: string | null; ultima_risposta: string | null; fuori: boolean
    no_followup: boolean; fonte: string | null; fit: string | null; fit_motivo: string | null; cosa_fa: string | null; campagna: string | null
  } | null
  filo: Messaggio[]
  decisioni: Array<{ id: string; risposta_il: string; mossa: Mossa; owner: string | null; testo: string | null; perche: string | null; stato: Stato; inviata_il: string | null; esito: string | null; dre_giudizio: string | null; dre_nota: string | null; creato_il: string }>
  agenda: Array<{ at: string; tipo: string | null; titolo: string | null; link: string | null }>
  note: Array<{ at: string; tipo: string; testo: string }>
  scheda: { stato: string | null; prossima_mossa: string | null; prossima_il: string | null; responsabile: string | null } | null
}
export interface Trovato { id: string; azienda: string | null; persona: string | null; email: string; citta: string | null; fase: string | null; classe: string | null; ultima_risposta: string | null; analisi_mandata: boolean }
export interface Call {
  prossime: Array<{ at: string; tipo: string | null; titolo: string | null; link: string | null; prospect_id: string | null; azienda: string | null; persona: string | null; telefono: string | null; preparazione: string | null }>
  richiami: Array<{ id: string; prospect_id: string; azienda: string | null; persona: string | null; telefono: string | null; quando: string | null; perche: string | null; risposta_il: string; esito: string | null; lead_testo: string | null }>
}
export interface Operazione { chiave: string; nome: string; ultima_corsa: string | null; ultimo_esito: string | null; ultimo_dettaglio: string | null; attiva: boolean }

const ATTESA_MS = 20_000
function entro(ms = ATTESA_MS): AbortSignal {
  const c = new AbortController()
  setTimeout(() => c.abort(), ms)
  return c.signal
}
function guasto(e: { message?: string } | null): never {
  if (/abort/i.test(e?.message ?? '')) throw new Error('La connessione non risponde. Controlla la rete e riprova.')
  if (!navigator.onLine || /failed to fetch|load failed|networkerror/i.test(e?.message ?? '')) throw new Error('Sei senza connessione: riprovo da solo appena torna.')
  throw new Error(e?.message || 'Il database non ha risposto')
}

export async function leggiCoda(giorni = 30): Promise<Decisione[]> {
  const { data, error } = await supabase.rpc('clara_coda', { giorni }).abortSignal(entro())
  if (error) guasto(error)
  return (data ?? []) as Decisione[]
}

export async function leggiRelazione(id: string): Promise<Relazione> {
  const { data, error } = await supabase.rpc('clara_relazione', { chi: id }).abortSignal(entro())
  if (error) guasto(error)
  return data as Relazione
}

export async function cerca(q: string): Promise<Trovato[]> {
  const { data, error } = await supabase.rpc('clara_cerca', { q }).abortSignal(entro())
  if (error) guasto(error)
  return (data ?? []) as Trovato[]
}

export async function leggiCall(): Promise<Call> {
  const { data, error } = await supabase.rpc('clara_call').abortSignal(entro())
  if (error) guasto(error)
  return (data ?? { prossime: [], richiami: [] }) as Call
}

export async function leggiOperazioni(): Promise<Operazione[]> {
  const { data, error } = await supabase.from('operazioni').select('chiave,nome,ultima_corsa,ultimo_esito,ultimo_dettaglio,attiva')
    .in('chiave', ['clara_prova', 'clara_manda', 'sync_smartlead', 'analisi']).abortSignal(entro())
  if (error) guasto(error)
  return (data ?? []) as Operazione[]
}

const ADESSO = () => new Date().toISOString()
const DRE = 'Dre (Desk)'

/** Il postino parte subito, se il direttore risponde; se no al giro dei cinque minuti. */
export async function spingiPostino(): Promise<void> {
  try { await supabase.rpc('chiama_direttore', { forza: 'clara_manda' }).abortSignal(entro(8000)) } catch { /* al giro dopo */ }
}

/** Invia: la decisione passa ad «approvata» col testo com'e' adesso. Se Dre l'ha toccato, resta scritto
 *  (testo_finale) e Clara lo impara come correzione; se e' uguale, e' un «ok» su quella mossa. */
export async function approva(d: Decisione, testo: string): Promise<void> {
  const toccato = testo.trim() !== (d.testo_clara ?? '').trim()
  const { data, error } = await supabase.from('clara_decisioni')
    .update({ stato: 'approvata', testo_finale: toccato ? testo.trim() : null, approvata_il: ADESSO(), approvata_da: DRE, errore: null,
      dre_giudizio: 'ok', dre_nota: toccato ? 'testo modificato da Dre prima dell’invio' : null, dre_il: ADESSO() })
    .eq('id', d.id).in('stato', ['proposta', 'approvata']).select('id').abortSignal(entro())
  if (error) guasto(error)
  if (!data?.length) throw new Error('Questa decisione non è più da approvare (è già partita o è superata). Ricarico.')
  void spingiPostino()
}

/** No: non si manda, e Clara sa perche'. */
export async function scarta(id: string, motivo: string): Promise<void> {
  const { error } = await supabase.from('clara_decisioni')
    .update({ stato: 'scartata', dre_giudizio: 'no', dre_nota: motivo.trim() || null, dre_il: ADESSO() })
    .eq('id', id).in('stato', ['proposta', 'approvata']).abortSignal(entro())
  if (error) guasto(error)
}

/** L'esito di una cosa fatta da Dre (una call, un richiamo, una decisione sua). */
export async function segnaEsito(id: string, esito: string, nota?: string): Promise<void> {
  const agg: Record<string, unknown> = { esito, esito_il: ADESSO(), stato: 'fatta' }
  if (nota?.trim()) agg.dre_nota = nota.trim()
  const { error } = await supabase.from('clara_decisioni').update(agg).eq('id', id).abortSignal(entro())
  if (error) guasto(error)
}

/** Il giudizio di Dre su una decisione che non manda niente (aspetta, chiude): per imparare. */
export async function giudica(id: string, ok: boolean, nota?: string): Promise<void> {
  const { error } = await supabase.from('clara_decisioni')
    .update({ dre_giudizio: ok ? 'ok' : 'no', dre_nota: nota?.trim() || null, dre_il: ADESSO() }).eq('id', id).abortSignal(entro())
  if (error) guasto(error)
}

/** Il testo cambiato senza mandare (si salva come testo_finale, la decisione resta proposta). */
export async function salvaTesto(id: string, testo: string): Promise<void> {
  const { error } = await supabase.from('clara_decisioni').update({ testo_finale: testo.trim() || null }).eq('id', id).abortSignal(entro())
  if (error) guasto(error)
}
