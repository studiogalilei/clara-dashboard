import { supabase } from './supabase'

// L'UTILIZZO (Dre, 7/10: «monitoro l'utilizzo mio e di tutti»). Ogni minuto in cui la
// pagina e' in primo piano e la persona l'ha toccata negli ultimi due minuti, si conta un
// minuto per lei e per la schermata (funzione segna_utilizzo, schema_v77). Chi lascia la
// scheda aperta e va a pranzo non accumula niente. Invisibile per chi usa il Workspace:
// se la funzione non c'e' ancora nel database, tace.

const ATTIVO_MS = 2 * 60_000
let ultimoGesto = Date.now()
let azioni = 0
let avviato = false

export function avviaUtilizzo(schermata: () => string, demo: boolean): () => void {
  if (avviato || demo) return () => {}
  avviato = true
  const gesto = () => { ultimoGesto = Date.now(); azioni += 1 }
  const eventi: Array<keyof WindowEventMap> = ['pointerdown', 'keydown', 'wheel', 'touchstart']
  eventi.forEach((e) => window.addEventListener(e, gesto, { passive: true }))
  let spenta = false                       // la funzione manca (prima della v77): non si riprova a ogni minuto
  const t = window.setInterval(() => {
    if (spenta || document.visibilityState !== 'visible' || Date.now() - ultimoGesto > ATTIVO_MS) return
    const fatte = azioni
    azioni = 0
    void supabase.rpc('segna_utilizzo', {
      p_minuti: 1, p_azioni: fatte, p_schermata: schermata(), p_telefono: window.innerWidth < 640,
    }).then(({ error }) => { if (error && /segna_utilizzo|function/i.test(error.message)) spenta = true })
  }, 60_000)
  return () => {
    window.clearInterval(t)
    eventi.forEach((e) => window.removeEventListener(e, gesto))
    avviato = false
  }
}
