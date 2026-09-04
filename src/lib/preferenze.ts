// Le preferenze: come hai deciso di vedere la Dashboard.
//
// Stanno in due posti apposta. Nel browser perche' devono essere immediate e
// funzionare anche offline e nella demo. Sul database perche' devono seguirti
// sul telefono: e' quello che diceva schema_v5.sql, ma nessuno le scriveva
// e la tabella `preferenze` era vuota da quando esiste (revisione 4/9).
//
// L'originale e' il database. Il browser e' la copia veloce: all'avvio si
// scarica e si sovrascrive quella locale, poi ogni modifica va in tutti e due.

import { supabase } from './supabase'

// solo queste: sono scelte, non dati. Quello che sta qui dentro puo' sparire
// senza che si perda niente di vero.
export const CHIAVI = [
  'profilo-nome',
  'mio-ruolo',
  'widget-ordine',
  'widget-nascosti',
  'widget-accessi',
  'task-vista',
  'tutti-vista',
  'tutti-filtro',
  'clara-larghezza',
] as const

export type Chiave = (typeof CHIAVI)[number]

export function leggi(chiave: Chiave, difetto = ''): string {
  try { return localStorage.getItem(chiave) ?? difetto } catch { return difetto }
}

// si scrive subito nel browser e si manda al database senza aspettarlo: se la
// rete non c'e', la scelta vale lo stesso qui e riparte al prossimo salvataggio
export function scrivi(chiave: Chiave, valore: string) {
  try { localStorage.setItem(chiave, valore) } catch { /* niente */ }
  void inviaAlDatabase(chiave, valore)
}

async function inviaAlDatabase(chiave: Chiave, valore: string) {
  try {
    const { data } = await supabase.auth.getSession()
    const owner = data.session?.user?.id
    if (!owner) return
    await supabase.from('preferenze')
      .upsert({ owner, chiave, valore }, { onConflict: 'owner,chiave' })
  } catch { /* le preferenze non fanno rumore: al massimo restano locali */ }
}

// all'accesso: quello che hai scelto altrove vince su questo browser.
// Torna true se qualcosa e' cambiato, cosi' chi chiama sa che deve ridisegnare.
export async function scarica(): Promise<boolean> {
  try {
    const { data: sess } = await supabase.auth.getSession()
    const owner = sess.session?.user?.id
    if (!owner) return false
    const { data, error } = await supabase.from('preferenze')
      .select('chiave, valore').eq('owner', owner).limit(50)
    if (error || !data) return false
    let cambiato = false
    for (const r of data as Array<{ chiave: string; valore: unknown }>) {
      if (!(CHIAVI as readonly string[]).includes(r.chiave)) continue
      const v = typeof r.valore === 'string' ? r.valore : JSON.stringify(r.valore)
      try {
        if (localStorage.getItem(r.chiave) !== v) { localStorage.setItem(r.chiave, v); cambiato = true }
      } catch { /* niente */ }
    }
    return cambiato
  } catch { return false }
}
