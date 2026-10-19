// LA VERSIONE SNELLA (15/10/2026): i dati.
// La UI non ragiona: legge quello che scripts/schede.py prepara ogni 10 minuti (snella_schede,
// snella_numeri) e scrive solo quello che decide Dre (snella_lead, snella_note). Non tocca mai
// le tabelle del sistema vecchio, non manda mail, non scrive su Smartlead.
import { supabase } from '../lib/supabase'
import statiJson from './stati.json'

/** I 12 stati della pipeline (Dre, 19/10), nell'ordine e nei gruppi: la fonte unica e' stati.json
 *  (la leggono anche scripts/schede.py e il database, snella_stati). Nient'altro. */
export interface InfoStato { nome: string; gruppo: string; tono: string; responsabile: Responsabile; azione: string; significa: string }
export type Responsabile = 'Dramane' | 'Claude'
export const INFO_STATI = statiJson.stati as InfoStato[]
export const STATI: readonly string[] = INFO_STATI.map((s) => s.nome)
export const GRUPPI: readonly string[] = statiJson.gruppi
export type Stato = string
export const RESPONSABILI: readonly Responsabile[] = ['Dramane', 'Claude']

export interface Telefono { numero: string; tel: string; etichetta: string }
export interface Messaggio { at: string | null; chi: 'lui' | 'noi'; testo: string; citato: string }
export interface SchedaDati {
  azienda: string; nome: string; ruolo: string; email: string; sg_id: number | null; campagna: string
  telefoni: Telefono[]; attivita: string; ultima: string; ultima_il: string | null; consiglio: string
  analisi: { mandata: boolean; il: string | null; link: string; percorso: string; punto: string }
  prossima: { mossa: string; il: string | null; responsabile?: Responsabile }
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
  responsabile?: Responsabile | null
}
export interface Nota { id: number; prospect_id: string; testo: string; tipo: 'nota' | 'chiamata'; at: string; autore: string | null; autore_nome: string | null }

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

export interface Domanda { id: number; tipo: 'umano' | 'risposta'; titolo: string; perche: string | null; at: string; prospect_id: string | null; intento?: string | null }
export interface Operazione { chiave: string; ultima_corsa: string | null; ultimo_esito: string | null; attiva: boolean }

// 17/10: una scrittura e' rimasta appesa senza risposta e il bottone diceva «Salvo…» per sempre.
// Ogni lettura e scrittura ha un tempo massimo: dopo, si dice che la connessione non risponde.
const ATTESA_MS = 20_000
function entro(ms = ATTESA_MS): AbortSignal {
  const c = new AbortController()
  setTimeout(() => c.abort(), ms)
  return c.signal
}

function guasto(e: { message?: string } | null): never {
  if (/abort/i.test(e?.message ?? '')) throw new Error('La connessione non risponde. Controlla la rete e riprova.')
  // 17/10: senza rete il browser dice «Failed to fetch» / «Load failed» (l'iPhone): a parole nostre
  if (!navigator.onLine || /failed to fetch|load failed|networkerror|network request failed/i.test(e?.message ?? '')) {
    throw new Error('Sei senza connessione: riprovo da solo appena torna.')
  }
  throw new Error(e?.message || 'Il database non ha risposto')
}

const CAMPI_RIGA = 'prospect_id,azienda,persona,email,stato,ultima_risposta,frase,da_chiamare,perche_chiamare'

export async function leggiNumeri(): Promise<Numeri> {
  // 19/10: in snella_numeri ci sono anche il foglio della pipeline e le sue fasi (scripts/foglio.py):
  // qui solo i numeri di Oggi, cosi' il telefono non scarica lo stato del foglio a ogni apertura
  const { data, error } = await supabase.from('snella_numeri').select('chiave,dati,aggiornato_il')
    .in('chiave', ['oggi', 'call', 'campagne']).abortSignal(entro())
  if (error) guasto(error)
  const out: Numeri = {}
  for (const r of (data ?? []) as Array<{ chiave: keyof Numeri; dati: never; aggiornato_il: string }>) {
    out[r.chiave] = { dati: r.dati, il: r.aggiornato_il }
  }
  return out
}

export async function leggiDecisioni(): Promise<Map<string, Decisione>> {
  const { data, error } = await supabase.from('snella_lead').select('*').limit(5000).abortSignal(entro())
  if (error) guasto(error)
  return new Map(((data ?? []) as Decisione[]).map((d) => [d.prospect_id, d]))
}

/** Le righe della lista: chi ha risposto negli ultimi `giorni` giorni, piu' gli `anche` (per id). */
export async function leggiRighe(giorni = 60, anche: string[] = []): Promise<RigaLead[]> {
  const da = new Date(Date.now() - giorni * 86400e3).toISOString()
  const { data, error } = await supabase.from('snella_schede').select(CAMPI_RIGA)
    .gte('ultima_risposta', da).order('ultima_risposta', { ascending: false }).limit(2000).abortSignal(entro())
  if (error) guasto(error)
  const righe = (data ?? []) as RigaLead[]
  const mancano = anche.filter((id) => !righe.some((r) => r.prospect_id === id))
  if (mancano.length) {
    const { data: altre, error: e2 } = await supabase.from('snella_schede').select(CAMPI_RIGA).in('prospect_id', mancano).abortSignal(entro())
    if (e2) guasto(e2)
    righe.push(...((altre ?? []) as RigaLead[]))
  }
  return righe
}

export type RigaConScheda = RigaLead & { scheda: SchedaDati; filo?: Messaggio[] }

/** Chi la scheda dice di chiamare, piu' chi Dre ha detto di richiamare (per id): con la scheda e il
 *  filo (per dire cosa gli abbiamo scritto dopo la sua risposta: sono pochi, il peso non conta). */
export async function leggiPerChiamare(richiamare: string[]): Promise<RigaConScheda[]> {
  const campi = CAMPI_RIGA + ',scheda,filo'
  const { data, error } = await supabase.from('snella_schede').select(campi).eq('da_chiamare', true).limit(500).abortSignal(entro())
  if (error) guasto(error)
  const righe = (data ?? []) as unknown as RigaConScheda[]
  const mancano = richiamare.filter((id) => !righe.some((r) => r.prospect_id === id))
  if (mancano.length) {
    const { data: altre, error: e2 } = await supabase.from('snella_schede').select(campi).in('prospect_id', mancano).abortSignal(entro())
    if (e2) guasto(e2)
    righe.push(...((altre ?? []) as unknown as RigaConScheda[]))
  }
  return righe
}

export async function leggiTelefoni(ids: string[]): Promise<Map<string, SchedaDati>> {
  if (!ids.length) return new Map()
  const { data, error } = await supabase.from('snella_schede').select('prospect_id,scheda').in('prospect_id', ids).abortSignal(entro())
  if (error) guasto(error)
  return new Map(((data ?? []) as Array<{ prospect_id: string; scheda: SchedaDati }>).map((r) => [r.prospect_id, r.scheda]))
}

const CAMPI_NOTA = 'id,prospect_id,testo,tipo,at,autore,autore_nome'

export async function leggiScheda(id: string): Promise<{ scheda: Scheda | null; decisione: Decisione | null; note: Nota[]; call: Call[]; base: RigaBase | null; fase: string | null }> {
  const [s, d, n, c, f] = await Promise.all([
    supabase.from('snella_schede').select('*').eq('prospect_id', id).abortSignal(entro()).maybeSingle(),
    supabase.from('snella_lead').select('*').eq('prospect_id', id).abortSignal(entro()).maybeSingle(),
    supabase.from('snella_note').select(CAMPI_NOTA).eq('prospect_id', id).order('at', { ascending: false }).limit(200).abortSignal(entro()),
    supabase.from('snella_numeri').select('dati').eq('chiave', 'call').abortSignal(entro()).maybeSingle(),
    // la fase del foglio della pipeline (scripts/foglio.py, ogni 10 minuti): la stessa che vede Dre nel foglio
    supabase.from('snella_numeri').select(`fase:dati->>${id}`).eq('chiave', 'fasi').abortSignal(entro()).maybeSingle(),
  ])
  if (s.error) guasto(s.error)
  if (d.error) guasto(d.error)
  if (n.error) guasto(n.error)
  // le call prenotate con lui (le prepara schede.py): se manca il dato, la scheda si apre lo stesso
  const tutte = ((c.data?.dati as { call?: Call[] } | undefined)?.call ?? [])
  // 19/10: da «Tutti» si apre anche chi non ha la scheda pronta: allora la sua riga, per decidere e
  // scrivere le note lo stesso
  const base = s.data ? null : await leggiRigaTutti(id)
  return { scheda: s.data as Scheda | null, decisione: d.data as Decisione | null, note: (n.data ?? []) as Nota[],
           call: tutte.filter((x) => x.prospect_id === id), base,
           fase: ((f.data as { fase?: string | null } | null)?.fase) ?? null }
}

// ── TUTTI (19/10): il foglio con tutti i prospect, una pagina alla volta dal database ──

/** Una riga di «Tutti» (supabase/schema_v92.sql, la vista snella_tutti). */
export interface RigaTutti {
  prospect_id: string; azienda: string | null; persona: string | null; email: string | null; campagna: string | null
  stato: string; stato_tuo: boolean; gruppo: string | null; ultima_risposta: string | null; ultima_nostra: string | null; novita: string | null
  risposto: boolean; scheda_pronta: boolean; telefono: string | null; responsabile: Responsabile | null; responsabile_tuo: boolean
  mossa: string | null; mossa_il: string | null; mossa_tua: boolean; richiamare_il: string | null
}
export interface FiltriTutti { q: string; stato: string | null; campagna: string | null; mai: boolean }
export interface PaginaTutti {
  righe: RigaTutti[]
  totale?: number; stati?: Record<string, number>; campagne?: Array<{ nome: string; n: number }>
}

/** Una pagina di «Tutti», gia' filtrata e ordinata dal database (l'ultima novita' in cima).
 *  Con `conta` arrivano anche il totale e i conteggi per stato e per campagna. */
export async function leggiTutti(f: FiltriTutti, da: number, quanti: number, conta: boolean): Promise<PaginaTutti> {
  const { data, error } = await supabase.rpc('snella_tutti_pagina', {
    q: f.q, stato: f.stato, campagna: f.campagna, anche_mai: f.mai, da, quanti, conta,
  }).abortSignal(entro())
  if (error) guasto(error)
  return data as PaginaTutti
}

/** Un lead senza scheda pronta (ha risposto prima dei 60 giorni, o mai): la sua riga di «Tutti». */
export interface RigaBase extends RigaTutti { stato_sistema: string }
export async function leggiRigaTutti(id: string): Promise<RigaBase | null> {
  const { data, error } = await supabase.from('snella_tutti')
    .select('prospect_id,azienda,persona,email,campagna,stato,stato_sistema,stato_tuo,gruppo,ultima_risposta,ultima_nostra,novita,risposto,scheda_pronta,telefono,responsabile,responsabile_tuo,mossa,mossa_il,mossa_tua,richiamare_il')
    .eq('prospect_id', id).abortSignal(entro()).maybeSingle()
  if (error) guasto(error)
  return data as RigaBase | null
}

/** Scrive quello che decide Dre su un lead (solo Workspace). Torna la riga com'e' adesso. */
export async function salvaDecisione(id: string, cambia: Partial<Decisione>): Promise<Decisione> {
  const { data, error } = await supabase.from('snella_lead')
    .upsert({ prospect_id: id, ...cambia }, { onConflict: 'prospect_id' }).select('*').abortSignal(entro()).single()
  if (error) guasto(error)
  return data as Decisione
}

export async function aggiungiNota(id: string, testo: string, tipo: Nota['tipo'] = 'nota'): Promise<Nota> {
  const { data, error } = await supabase.from('snella_note').insert({ prospect_id: id, testo: testo.trim(), tipo })
    .select(CAMPI_NOTA).abortSignal(entro()).single()
  if (error) guasto(error)
  return data as Nota
}

/** Toglie una nota (il database lo lascia fare solo a chi l'ha scritta). Dice se l'ha tolta davvero. */
export async function togliNota(nota: number): Promise<void> {
  const { data, error } = await supabase.from('snella_note').delete().eq('id', nota).select('id').abortSignal(entro())
  if (error) guasto(error)
  if (!data?.length) throw new Error('la nota non si può cancellare: l\'ha scritta un\'altra persona')
}

/** Chi sono io (per sapere quali note posso cancellare). */
export async function ioSono(): Promise<string | null> {
  const { data } = await supabase.auth.getSession()
  return data.session?.user.id ?? null
}

export async function leggiDomande(): Promise<Domanda[]> {
  const { data, error } = await supabase.from('proposte').select('id,tipo,titolo,perche,at,prospect_id,intento:azione->>intento')
    .eq('stato', 'aperta').in('tipo', ['umano', 'risposta']).order('at', { ascending: false }).limit(400).abortSignal(entro())
  if (error) guasto(error)
  return (data ?? []) as Domanda[]
}

export async function leggiSistema(): Promise<Operazione[]> {
  const { data, error } = await supabase.from('operazioni').select('chiave,ultima_corsa,ultimo_esito,attiva')
    .in('chiave', ['sync_smartlead', 'schede', 'segnale']).abortSignal(entro())
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
