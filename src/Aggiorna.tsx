// LA VERSIONE NUOVA PRENDE IL POSTO DELLA VECCHIA (21/10/2026 sera).
// Dre: «la cosa delle due alternative non c'e' in app sul telefono». C'era: la pubblicazione era
// passata, ma l'app sul telefono resta aperta per giorni e il service worker controlla se c'e' una
// versione nuova solo quando la pagina si carica. Qui si controlla ogni cinque minuti e ogni volta
// che l'app torna davanti; il service worker nuovo prende il posto del vecchio subito (vite.config.ts:
// skipWaiting, clientsClaim).
// Quando la versione nuova e' attiva la pagina si ricarica da sola SOLO se l'app e' ferma (nessun
// campo di testo col fuoco): mentre Dre scrive una nota compare una riga «Nuova versione: tocca per
// aggiornare», e la ricarica avviene quando la tocca o quando l'app torna davanti ferma.
// Sta nella porta d'ingresso (Radice.tsx): vale per la versione snella e per il Workspace completo.
import { useEffect, useState } from 'react'
import { useRegisterSW } from 'virtual:pwa-register/react'
import { appFerma } from './snella/regole'

export const OGNI_MINUTI = 5

function fermaAdesso(): boolean {
  const a = document.activeElement as HTMLElement | null
  return appFerma(a?.tagName, Boolean(a?.isContentEditable))
}

export default function Aggiorna() {
  const [nuova, setNuova] = useState(false)

  useRegisterSW({
    onNeedReload() {
      if (fermaAdesso()) window.location.reload()
      else setNuova(true)
    },
    onRegisteredSW(_url, r) {
      if (!r) return
      const controlla = () => {
        if (document.visibilityState === 'visible' && navigator.onLine && fermaAdesso()) void r.update().catch(() => undefined)
      }
      window.setInterval(controlla, OGNI_MINUTI * 60 * 1000)
      document.addEventListener('visibilitychange', controlla)
    },
  })

  // la versione nuova aspetta: appena l'app torna davanti ed e' ferma, si ricarica
  useEffect(() => {
    if (!nuova) return
    const torna = () => { if (document.visibilityState === 'visible' && fermaAdesso()) window.location.reload() }
    document.addEventListener('visibilitychange', torna)
    return () => document.removeEventListener('visibilitychange', torna)
  }, [nuova])

  if (!nuova) return null
  return (
    <button
      type="button"
      onClick={() => window.location.reload()}
      className="fixed inset-x-0 top-0 z-50 w-full bg-inchiostro px-4 pb-2 pt-[calc(env(safe-area-inset-top)+8px)] text-center text-sm font-medium text-white"
    >
      Nuova versione: tocca per aggiornare
    </button>
  )
}
