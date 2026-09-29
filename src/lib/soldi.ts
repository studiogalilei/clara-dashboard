import { useEffect, useState } from 'react'
import { supabase } from './supabase'

// LA CASSAFORTE (Dre, 29/9: «niente soldi per gli altri, solo io e Giacomo»).
// Canone, fatturazione, prezzo suggerito, numeri del cliente e valore dei progetti
// stanno in soldi_clienti e soldi_progetti, che il database fa leggere solo ai ceo
// (schema_v67). Qui si leggono e si rimettono al loro posto sulle righe, in
// memoria: a chi non e' ceo il database risponde vuoto, quindi non si vede niente.

export interface Soldi {
  canone: number | null
  fatturazione: unknown
  prezzo: unknown
  bilancio: unknown
  valore: unknown
}

let clienti: Promise<Map<string, Soldi>> | null = null
let progetti: Promise<Map<number, number>> | null = null

export function soldiClienti(forza = false): Promise<Map<string, Soldi>> {
  if (!clienti || forza) {
    clienti = (async () => {
      const m = new Map<string, Soldi>()
      // canone e fatturazione: Dre e Giacomo. Prezzo, bilancio e valore: solo Dre (il riservato, schema_v68)
      const [soldi, ris] = await Promise.all([
        supabase.from('soldi_clienti').select('prospect_id,canone,fatturazione').limit(1000),
        supabase.from('riservato_clienti').select('prospect_id,prezzo,bilancio,valore').limit(1000),
      ])
      const vuoto = { canone: null, fatturazione: null, prezzo: null, bilancio: null, valore: null }
      for (const r of (soldi.data ?? []) as Array<{ prospect_id: string; canone: number | null; fatturazione: unknown }>) {
        m.set(r.prospect_id, { ...vuoto, canone: r.canone, fatturazione: r.fatturazione })
      }
      for (const r of (ris.data ?? []) as Array<{ prospect_id: string; prezzo: unknown; bilancio: unknown; valore: unknown }>) {
        m.set(r.prospect_id, { ...(m.get(r.prospect_id) ?? vuoto), prezzo: r.prezzo, bilancio: r.bilancio, valore: r.valore })
      }
      return m
    })()
  }
  return clienti
}

export function soldiProgetti(forza = false): Promise<Map<number, number>> {
  if (!progetti || forza) {
    progetti = (async () => {
      const m = new Map<number, number>()
      const { data } = await supabase.from('soldi_progetti').select('progetto_id,valore').limit(1000)
      for (const r of (data ?? []) as Array<{ progetto_id: number; valore: number | null }>) {
        if (r.valore != null) m.set(Number(r.progetto_id), Number(r.valore))
      }
      return m
    })()
  }
  return progetti
}

/** La riga dell'azienda con i suoi soldi rimessi al loro posto (solo per chi li puo' vedere). */
export function conSoldi<T extends { id: string; canone?: number | null; enriched?: unknown }>(p: T, m: Map<string, Soldi>): T {
  const s = m.get(p.id)
  if (!s) return p
  const arr = { ...((p.enriched as Record<string, unknown> | null) ?? {}) }
  if (s.prezzo != null) arr.prezzo = s.prezzo
  if (s.bilancio != null) arr.bilancio = s.bilancio
  if (s.valore != null) arr.valore = s.valore
  return { ...p, canone: p.canone ?? s.canone, enriched: arr }
}

/** Il valore del progetto dalla cassaforte. */
export function conValore<T extends { id: number; valore?: number | null }>(g: T, m: Map<number, number>): T {
  return m.has(Number(g.id)) ? { ...g, valore: m.get(Number(g.id)) ?? null } : g
}

export function useSoldiClienti(): Map<string, Soldi> {
  const [m, setM] = useState<Map<string, Soldi>>(new Map())
  useEffect(() => { let vivo = true; void soldiClienti().then((x) => { if (vivo) setM(x) }); return () => { vivo = false } }, [])
  return m
}

export function useSoldiProgetti(): Map<number, number> {
  const [m, setM] = useState<Map<number, number>>(new Map())
  useEffect(() => { let vivo = true; void soldiProgetti().then((x) => { if (vivo) setM(x) }); return () => { vivo = false } }, [])
  return m
}

/** Azzera il canone (un cliente che torna indietro): nella tabella normale non si puo', e' in cassaforte. */
export async function azzeraCanone(prospectId: string) {
  await supabase.from('soldi_clienti').update({ canone: null }).eq('prospect_id', prospectId)
  void soldiClienti(true)
}

/** Azzera il valore di un progetto: in cassaforte, come il canone. */
export async function azzeraValore(progettoId: number) {
  await supabase.from('soldi_progetti').update({ valore: null }).eq('progetto_id', progettoId)
  void soldiProgetti(true)
}
