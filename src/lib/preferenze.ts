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
  'tutti-modo',
  'progetti-ordine',
  'clienti-modo',
  'clara-larghezza',
  'clara-aperta',
  'menu-larghezza',
  'obsidian-vault',
  'oggi-clara',
  'calendario-pod',
  'calendario-vista',
  'chat-con',
  'clara-chat',
  'menu-essenziale', // 23/9: il menu corto di Dre (Pipeline, Clienti, Calendario, Posta, Preventivi)      // 23/9: la chat di Clara, spenta finche' non sa leggere il CRM prima di rispondere
  'chat-visto',
  'giro-fatto',
  'task-apertura',       // «Come si apre» in Impostazioni: il difetto
  'pipeline-apertura',   // delle viste di sessione, e questo resta
  'novita-viste',        // le novita' gia' viste (e votate): non tornano
] as const

export type Chiave = (typeof CHIAVI)[number]

// DI SESSIONE, NON PER SEMPRE (Dre, 15/9): «se clicco Bacheca resta cosi'
// anche passando in altre tab, ma torna al difetto se chiudo l'app e
// rientro». Come sto guardando una cosa adesso e' un gesto dentro una
// sessione di lavoro, non una preferenza: se resta per sempre, un giorno
// riapri il Workspace e non ti ricordi piu' perche' vedi quella roba li'.
// Queste vivono in sessionStorage e basta: si spengono con la finestra.
const DI_SESSIONE: readonly string[] = [
  'task-vista', 'tutti-vista', 'tutti-filtro', 'tutti-modo',
  'progetti-ordine', 'clienti-modo', 'oggi-clara', 'calendario-pod', 'calendario-vista',
]
const sessione = (c: string) => DI_SESSIONE.includes(c)

export function leggi(chiave: Chiave, difetto = ''): string {
  try {
    if (sessione(chiave)) return sessionStorage.getItem(chiave) ?? difetto
    return localStorage.getItem(chiave) ?? difetto
  } catch { return difetto }
}

// si scrive subito nel browser e si manda al database senza aspettarlo: se la
// rete non c'e', la scelta vale lo stesso qui e riparte al prossimo salvataggio
export function scrivi(chiave: Chiave, valore: string) {
  if (sessione(chiave)) {
    try { sessionStorage.setItem(chiave, valore) } catch { /* niente */ }
    return
  }
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
      if (sessione(r.chiave)) continue      // le viste non arrivano dal database
      const v = typeof r.valore === 'string' ? r.valore : JSON.stringify(r.valore)
      try {
        if (localStorage.getItem(r.chiave) !== v) { localStorage.setItem(r.chiave, v); cambiato = true }
      } catch { /* niente */ }
    }
    return cambiato
  } catch { return false }
}
