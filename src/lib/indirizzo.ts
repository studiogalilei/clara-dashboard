// GLI INDIRIZZI (Dre, 26/9): «i nomi, gli index, come arrivo alle info».
// Ogni cosa che guardi ha un indirizzo suo nella barra del browser: lo copi, lo
// mandi a Carlo, lui apre esattamente quello che vedevi tu. E il tasto indietro
// del browser fa quello che ci si aspetta.
//
//   /clara/#/pipeline                una sezione
//   /clara/#/azienda/<id>            una scheda
//   /clara/#/azienda/<id>/lavoro     una scheda, tab Lavoro
//
// Restano buoni i vecchi link ?scheda=<id> che Clara ha messo in calendario.

import type { Chiave } from './widget'

export interface Dove { tab: Chiave; id: string | null; sezione: string | null }

// il nome nella barra: corto, in italiano, uguale a quello che si legge nel menu
export const NOME_TAB: Record<string, Chiave> = {
  oggi: 'pipeline', pipeline: 'prospect', clienti: 'progetti', calendario: 'calendario',
  preventivi: 'preventivi', posta: 'clara', documenti: 'vault', chat: 'chat',
  numeri: 'analytics', impostazioni: 'impostazioni', widget: 'plugin', feedback: 'feedback',
  aziende: 'prospect', task: 'oggi', tutti: 'tutti',
}
const VERSO_URL = Object.fromEntries(Object.entries(NOME_TAB).map(([n, t]) => [t, n])) as Record<Chiave, string>
// dove due nomi puntano alla stessa tab, vince quello giusto
VERSO_URL.pipeline = 'oggi'; VERSO_URL.prospect = 'pipeline'; VERSO_URL.progetti = 'clienti'
VERSO_URL.clara = 'posta'; VERSO_URL.vault = 'documenti'; VERSO_URL.analytics = 'numeri'; VERSO_URL.plugin = 'widget'

export function leggiIndirizzo(): Dove | null {
  const h = window.location.hash.replace(/^#\/?/, '')
  if (h) {
    const [uno, due, tre] = h.split('/')
    if (uno === 'azienda' && due) return { tab: 'prospect', id: due, sezione: tre ?? null }
    const t = NOME_TAB[uno]
    if (t) return { tab: t, id: null, sezione: due ?? null }
  }
  // i vecchi link di Clara in calendario: ?scheda=<id>
  const vecchio = new URLSearchParams(window.location.search).get('scheda')
  if (vecchio) return { tab: 'prospect', id: vecchio, sezione: null }
  return null
}

export function scriviIndirizzo(d: Dove, sostituisci = false) {
  const pezzi = d.id ? ['azienda', d.id, d.sezione] : [VERSO_URL[d.tab] ?? d.tab, d.sezione]
  const h = '#/' + pezzi.filter(Boolean).join('/')
  if (h === window.location.hash) return
  const url = window.location.pathname + window.location.search.replace(/[?&]scheda=[^&]*/, '').replace(/^&/, '?') + h
  if (sostituisci) window.history.replaceState(null, '', url)
  else window.history.pushState(null, '', url)
}

/** Il link da mandare a qualcuno: sempre assoluto. */
export function linkDi(d: Dove): string {
  const pezzi = d.id ? ['azienda', d.id, d.sezione] : [VERSO_URL[d.tab] ?? d.tab, d.sezione]
  return `${window.location.origin}${window.location.pathname}#/${pezzi.filter(Boolean).join('/')}`
}
