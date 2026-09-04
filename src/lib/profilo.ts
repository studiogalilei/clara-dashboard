// Il profilo: chi sei dentro la Dashboard.
// Nome e iniziali stanno qui perche' compaiono in tre posti (barra in basso,
// Impostazioni, e accanto alle task che mandi agli altri).

import { supabase } from './supabase'
import { leggi as leggiPref, scrivi as scriviPref } from './preferenze'
import type { Ruolo } from './widget'

export interface Profilo {
  nome: string
  email: string
  ruolo: Ruolo
}

export function nomeSalvato(): string {
  return leggiPref('profilo-nome')
}

// il nome va anche in `profili`, perche' non serve solo a te: e' quello che
// l'altra persona legge accanto a una task che le hai mandato. Prima restava
// nel tuo browser e gli altri vedevano il prefisso della mail (revisione 4/9)
export function salvaNome(n: string) {
  const nome = n.trim()
  scriviPref('profilo-nome', nome)
  void (async () => {
    try {
      const { data } = await supabase.auth.getSession()
      const id = data.session?.user?.id
      if (!id) return
      await supabase.from('profili').upsert({ id, nome }, { onConflict: 'id' })
    } catch { /* resta il nome locale */ }
  })()
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
