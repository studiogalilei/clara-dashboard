// LA VERSIONE SNELLA (15/10/2026): i dati.
// La UI non ragiona: legge quello che scripts/schede.py prepara ogni 10 minuti (snella_schede,
// snella_numeri) e scrive solo quello che decide Dre (snella_lead, snella_note). Non tocca mai
// le tabelle del sistema vecchio, non manda mail, non scrive su Smartlead.
import { supabase } from '../lib/supabase'

export const STATI = [
  'In conversazione', 'Vuole sentirti', 'Analisi mandata', 'Conoscitiva', 'Follow-up',
  'Da riprendere', 'No grazie', 'Non scrivere più', 'Fuori ufficio',
] as const
export type Stato = (typeof STATI)[number]

export interface Telefono { numero: string; tel: string; etichetta: string }
export interface Messaggio { at: string | null; chi: 'lui' | 'noi'; testo: string; citato: string }
export interface SchedaDati {
  azienda: string; nome: string; ruolo: string; email: string; sg_id: number | null; campagna: string
  telefoni: Telefono[]; attivita: string; ultima: string; ultima_il: string | null; consiglio: string
  analisi: { mandata: boolean; il: string | null; link: string; percorso: string; punto: string }
  prossima: { mossa: string; il: string | null }
  aspetta_noi: boolean
}
export interface RigaLead {
  prospect_id: string; azienda: string | null; persona: string | null; email: string | null
  stato: string | null; ultima_risposta: string | null; frase: string | null
  da_chiamare: boolean; perche_chiamare: string | null
}
export interface Scheda extends RigaLead { scheda: SchedaDati; filo: Messaggio[]; aggiornata_il: string }
export interface Decisione {
  prospect_id: string; stato: Stato | null; prossima_mossa: string | null; prossima_il: string | null
  chiamata: 'chiamato' | 'non_risponde' | 'richiamare' | null; chiamata_il: string | null
  richiamare_il: string | null; tentativi: number; aggiornato_il?: string
}
export interface Nota { id: number; prospect_id: string; testo: string; tipo: 'nota' | 'chiamata'; at: string; autore_nome: string | null }

export interface NumeriOggi {
  risposte: number; messaggi: number; si: number; media_minuti: number | null
  serviti: Array<{ prospect_id: string; azienda: string; at: string; minuti: number }>
  in_attesa: Array<{ prospect_id: string; azienda: string; at: string; minuti: number }>
  aspettano: number; aspetta_da_piu: { prospect_id: string; azienda: string; da: string } | null
  ritardo: boolean; ritardi: string[]
}
export interface Call { at: string; titolo: string; tipo: string; prospect_id: string | null; azienda: string; meet: string; di_dre: boolean; di_chi: string }
export interface Finestra { mandate: number | null; aziende: number | null; risposte: number | null; risposte_lette: number; si: number; no: number; call: number }
export interface Campagna { id: number; nome: string; creata: string; finestre: Record<'7' | '30', Finestra> }
export interface NumeriCampagne { campagne: Campagna[]; totale: Record<'7' | '30', Finestra>; errore: string | null }
export interface Numeri { oggi?: { dati: NumeriOggi; il: string }; call?: { dati: { call: Call[] }; il: string }; campagne?: { dati: NumeriCampagne; il: string } }

export interface Domanda { id: number; tipo: 'umano' | 'risposta'; titolo: string; perche: string | null; at: string; prospect_id: string | null }
export interface Operazione { chiave: string; ultima_corsa: string | null; ultimo_esito: string | null; attiva: boolean }

function guasto(e: { message?: string } | null): never {
  throw new Error(e?.message || 'Il database non ha risposto')
}

const CAMPI_RIGA = 'prospect_id,azienda,persona,email,stato,ultima_risposta,frase,da_chiamare,perche_chiamare'

export async function leggiNumeri(): Promise<Numeri> {
  const { data, error } = await supabase.from('snella_numeri').select('chiave,dati,aggiornato_il')
  if (error) guasto(error)
  const out: Numeri = {}
  for (const r of (data ?? []) as Array<{ chiave: keyof Numeri; dati: never; aggiornato_il: string }>) {
    out[r.chiave] = { dati: r.dati, il: r.aggiornato_il }
  }
  return out
}

export async function leggiDecisioni(): Promise<Map<string, Decisione>> {
  const { data, error } = await supabase.from('snella_lead').select('*').limit(5000)
  if (error) guasto(error)
  return new Map(((data ?? []) as Decisione[]).map((d) => [d.prospect_id, d]))
}

/** Le righe della lista: chi ha risposto negli ultimi `giorni` giorni, piu' gli `anche` (per id). */
export async function leggiRighe(giorni = 60, anche: string[] = []): Promise<RigaLead[]> {
  const da = new Date(Date.now() - giorni * 86400e3).toISOString()
  const { data, error } = await supabase.from('snella_schede').select(CAMPI_RIGA)
    .gte('ultima_risposta', da).order('ultima_risposta', { ascending: false }).limit(2000)
  if (error) guasto(error)
  const righe = (data ?? []) as RigaLead[]
  const mancano = anche.filter((id) => !righe.some((r) => r.prospect_id === id))
  if (mancano.length) {
    const { data: altre, error: e2 } = await supabase.from('snella_schede').select(CAMPI_RIGA).in('prospect_id', mancano)
    if (e2) guasto(e2)
    righe.push(...((altre ?? []) as RigaLead[]))
  }
  return righe
}

export type RigaConScheda = RigaLead & { scheda: SchedaDati }

/** Chi la scheda dice di chiamare, piu' chi Dre ha detto di richiamare (per id): con la scheda. */
export async function leggiPerChiamare(richiamare: string[]): Promise<RigaConScheda[]> {
  const campi = CAMPI_RIGA + ',scheda'
  const { data, error } = await supabase.from('snella_schede').select(campi).eq('da_chiamare', true).limit(500)
  if (error) guasto(error)
  const righe = (data ?? []) as unknown as RigaConScheda[]
  const mancano = richiamare.filter((id) => !righe.some((r) => r.prospect_id === id))
  if (mancano.length) {
    const { data: altre, error: e2 } = await supabase.from('snella_schede').select(campi).in('prospect_id', mancano)
    if (e2) guasto(e2)
    righe.push(...((altre ?? []) as unknown as RigaConScheda[]))
  }
  return righe
}

export async function leggiTelefoni(ids: string[]): Promise<Map<string, SchedaDati>> {
  if (!ids.length) return new Map()
  const { data, error } = await supabase.from('snella_schede').select('prospect_id,scheda').in('prospect_id', ids)
  if (error) guasto(error)
  return new Map(((data ?? []) as Array<{ prospect_id: string; scheda: SchedaDati }>).map((r) => [r.prospect_id, r.scheda]))
}

export async function leggiScheda(id: string): Promise<{ scheda: Scheda | null; decisione: Decisione | null; note: Nota[] }> {
  const [s, d, n] = await Promise.all([
    supabase.from('snella_schede').select('*').eq('prospect_id', id).maybeSingle(),
    supabase.from('snella_lead').select('*').eq('prospect_id', id).maybeSingle(),
    supabase.from('snella_note').select('id,prospect_id,testo,tipo,at,autore_nome').eq('prospect_id', id).order('at', { ascending: false }).limit(200),
  ])
  if (s.error) guasto(s.error)
  if (d.error) guasto(d.error)
  if (n.error) guasto(n.error)
  return { scheda: s.data as Scheda | null, decisione: d.data as Decisione | null, note: (n.data ?? []) as Nota[] }
}

/** Scrive quello che decide Dre su un lead (solo Workspace). Torna la riga com'e' adesso. */
export async function salvaDecisione(id: string, cambia: Partial<Decisione>): Promise<Decisione> {
  const { data, error } = await supabase.from('snella_lead')
    .upsert({ prospect_id: id, ...cambia }, { onConflict: 'prospect_id' }).select('*').single()
  if (error) guasto(error)
  return data as Decisione
}

export async function aggiungiNota(id: string, testo: string, tipo: Nota['tipo'] = 'nota'): Promise<Nota> {
  const { data, error } = await supabase.from('snella_note').insert({ prospect_id: id, testo: testo.trim(), tipo })
    .select('id,prospect_id,testo,tipo,at,autore_nome').single()
  if (error) guasto(error)
  return data as Nota
}

export async function togliNota(nota: number): Promise<void> {
  const { error } = await supabase.from('snella_note').delete().eq('id', nota)
  if (error) guasto(error)
}

export async function leggiDomande(): Promise<Domanda[]> {
  const { data, error } = await supabase.from('proposte').select('id,tipo,titolo,perche,at,prospect_id')
    .eq('stato', 'aperta').in('tipo', ['umano', 'risposta']).order('at', { ascending: false }).limit(400)
  if (error) guasto(error)
  return (data ?? []) as Domanda[]
}

export async function leggiSistema(): Promise<Operazione[]> {
  const { data, error } = await supabase.from('operazioni').select('chiave,ultima_corsa,ultimo_esito,attiva')
    .in('chiave', ['sync_smartlead', 'schede', 'segnale'])
  if (error) guasto(error)
  return (data ?? []) as Operazione[]
}

/** Il link firmato al PDF dell'analisi (il bucket e' privato e i link scadono): uno nuovo ogni volta. */
export async function linkAnalisi(a: SchedaDati['analisi']): Promise<string | null> {
  if (a.percorso) {
    const { data } = await supabase.storage.from('vault').createSignedUrl(a.percorso, 3600)
    if (data?.signedUrl) return data.signedUrl
  }
  return a.link || null
}
