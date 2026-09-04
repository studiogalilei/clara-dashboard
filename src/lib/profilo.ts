// Il profilo: chi sei dentro la Dashboard.
// Nome e iniziali stanno qui perche' compaiono in tre posti (barra in basso,
// Impostazioni, e domani accanto alle task che mandi agli altri).
// Finche' gli account non portano il nome, sta nel browser.

import type { Ruolo } from './widget'

export interface Profilo {
  nome: string
  email: string
  ruolo: Ruolo
}

export function nomeSalvato(): string {
  try { return localStorage.getItem('profilo-nome') ?? '' } catch { return '' }
}
export function salvaNome(n: string) {
  try { localStorage.setItem('profilo-nome', n.trim()) } catch { /* niente */ }
}

// le iniziali per il tondino: due lettere, nome e cognome se ci sono
export function iniziali(nome: string): string {
  const p = nome.trim().split(/\s+/).filter(Boolean)
  if (p.length === 0) return '?'
  if (p.length === 1) return p[0].slice(0, 2).toUpperCase()
  return (p[0][0] + p[p.length - 1][0]).toUpperCase()
}

// il nome da mostrare: quello scelto, altrimenti si ricava dalla mail
export function nomeDa(email: string, demo: boolean): string {
  const salvato = nomeSalvato()
  if (salvato) return salvato
  if (demo) return 'Demo'
  const prima = (email ?? '').split('@')[0]
  return prima ? prima.charAt(0).toUpperCase() + prima.slice(1) : 'Senza nome'
}
