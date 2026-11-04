// LA PORTA D'INGRESSO (15/10/2026): chi apre quale Workspace.
// - #/s/...                       la versione snella (src/snella/)
// - senza indirizzo, se sei ceo   la versione snella: e' quella che Dre usa ogni giorno
// - tutto il resto                la pagina «Workspace chiuso» (4/11: il Workspace completo non c'è più)
import { useEffect, useState } from 'react'
import { supabase, demo } from './lib/supabase'
import { chiSono } from './lib/accessi'
import Snella from './snella/Snella'
import { inSnella } from './snella/uso'
import Desk, { inDesk } from './desk/Desk'
import { ascoltaNotifiche } from './lib/notifiche'
import Aggiorna from './Aggiorna'
import Chiuso from './Chiuso'

type Quale = 'desk' | 'snella' | 'chiuso' | null

/** Si entra senza indirizzo: l'icona sul telefono, il link nudo, il ritorno dal login di Google. */
function entrataNuda(): boolean {
  const h = window.location.hash
  // 4/11: anche l'icona vecchia sul telefono (#/s/oggi) porta un ceo al Desk
  return !demo && (!h || h === '#' || h === '#/' || h.startsWith('#access_token') || /^#\/s\/oggi\/?$/.test(h)) && !/[?&]scheda=/.test(window.location.search)
}

export default function Radice() {
  // 4/11: il Desk (#/d) e' quello che Dre usa ogni giorno; la snella resta a #/s
  const [quale, setQuale] = useState<Quale>(() => inDesk(window.location.hash) ? 'desk' : entrataNuda() ? null : inSnella(window.location.hash) ? 'snella' : 'chiuso')

  // il tocco su una notifica con l'app gia' aperta: si va al suo indirizzo (public/push.js)
  useEffect(() => ascoltaNotifiche(), [])

  useEffect(() => {
    // un indirizzo vuoto non decide niente: e' anche il login di Google che si pulisce il token
    // dall'indirizzo (15/10, visto sul Workspace pubblicato: mandava Dre sul completo a meta' strada)
    const cambia = () => {
      if (inDesk(window.location.hash)) setQuale('desk')
      else if (entrataNuda()) setQuale(null)
      else if (inSnella(window.location.hash)) setQuale('snella')
      else setQuale('chiuso')
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
          window.history.replaceState(null, '', window.location.pathname + window.location.search + '#/d/relazioni')
          if (vivo) setQuale('desk')
          return
        }
      } catch { /* nel dubbio, la pagina chiusa */ }
      if (vivo) setQuale(inSnella(window.location.hash) ? 'snella' : 'chiuso')
    })()
    return () => { vivo = false }
  }, [quale])

  return (
    <>
      <Aggiorna />
      {quale === null ? <div className="min-h-dvh bg-white" />
        : quale === 'desk' ? <Desk />
          : quale === 'snella' ? <Snella />
          : <Chiuso />}
    </>
  )
}
