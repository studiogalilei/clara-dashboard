// LA PORTA D'INGRESSO (15/10/2026): chi apre quale Workspace.
// - #/s/...                       la versione snella (src/snella/)
// - senza indirizzo, se sei ceo   la versione snella: e' quella che Dre usa ogni giorno
// - tutto il resto                il Workspace completo, com'era
// Il Workspace completo si carica solo quando serve: chi entra nella versione snella non
// scarica le sue 50 schermate.
import { lazy, Suspense, useEffect, useState } from 'react'
import { supabase, demo } from './lib/supabase'
import { chiSono } from './lib/accessi'
import Snella from './snella/Snella'
import { inSnella } from './snella/uso'
import Desk, { inDesk } from './desk/Desk'
import { ascoltaNotifiche } from './lib/notifiche'
import Aggiorna from './Aggiorna'

// dopo un aggiornamento il pezzo vecchio non esiste piu': si ricarica una volta sola (come in App)
const App = lazy(() => import('./App').catch((e) => {
  const ultima = Number(sessionStorage.getItem('ricaricato') ?? 0)
  if (Date.now() - ultima > 60_000) {
    sessionStorage.setItem('ricaricato', String(Date.now()))
    location.reload()
  }
  throw e
}))

type Quale = 'desk' | 'snella' | 'completo' | null

/** Si entra senza indirizzo: l'icona sul telefono, il link nudo, il ritorno dal login di Google. */
function entrataNuda(): boolean {
  const h = window.location.hash
  // 4/11: anche l'icona vecchia sul telefono (#/s/oggi) porta un ceo al Desk
  return !demo && (!h || h === '#' || h === '#/' || h.startsWith('#access_token') || /^#\/s\/oggi\/?$/.test(h)) && !/[?&]scheda=/.test(window.location.search)
}

export default function Radice() {
  // 4/11: il Desk (#/d) e' quello che Dre usa ogni giorno; la snella resta a #/s
  const [quale, setQuale] = useState<Quale>(() => inDesk(window.location.hash) ? 'desk' : entrataNuda() ? null : inSnella(window.location.hash) ? 'snella' : 'completo')

  // il tocco su una notifica con l'app gia' aperta: si va al suo indirizzo (public/push.js)
  useEffect(() => ascoltaNotifiche(), [])

  useEffect(() => {
    // un indirizzo vuoto non decide niente: e' anche il login di Google che si pulisce il token
    // dall'indirizzo (15/10, visto sul Workspace pubblicato: mandava Dre sul completo a meta' strada)
    const cambia = () => {
      if (inDesk(window.location.hash)) setQuale('desk')
      else if (entrataNuda()) setQuale(null)
      else if (inSnella(window.location.hash)) setQuale('snella')
      else setQuale('completo')
    }
    window.addEventListener('hashchange', cambia)
    window.addEventListener('popstate', cambia)
    return () => { window.removeEventListener('hashchange', cambia); window.removeEventListener('popstate', cambia) }
  }, [])

  useEffect(() => {
    if (quale !== null) return
    let vivo = true
    void (async () => {
      try {
        const { data } = await supabase.auth.getSession()
        if (data.session && (await chiSono()).ruolo === 'ceo') {
          if (!vivo) return
          window.history.replaceState(null, '', window.location.pathname + window.location.search + '#/d/coda')
          if (vivo) setQuale('desk')
          return
        }
      } catch { /* nel dubbio, il Workspace di sempre */ }
      if (vivo) setQuale(inSnella(window.location.hash) ? 'snella' : 'completo')
    })()
    return () => { vivo = false }
  }, [quale])

  return (
    <>
      <Aggiorna />
      {quale === null ? <div className="min-h-dvh bg-white" />
        : quale === 'desk' ? <Desk />
          : quale === 'snella' ? <Snella />
          : (
            <Suspense fallback={<div className="min-h-dvh bg-fondo" />}>
              <App />
            </Suspense>
          )}
    </>
  )
}
