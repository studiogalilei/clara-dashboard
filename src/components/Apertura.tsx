import { useEffect, useState } from 'react'
import { REPARTI, repartoRicordato, type Reparto } from '../lib/reparto'

// LA SCHERMATA DI APERTURA (Dre, 26/9): «te lo mostra ogni volta prima di
// entrare, come Smartlead: il logo, lo sfondo diverso per persona per reparto».
// Sfondo pieno del reparto, l'albero bianco al centro, sotto il nome. Resta
// mezzo secondo e sfuma. Il reparto e' quello ricordato dall'ultima volta, cosi'
// il colore c'e' subito, prima ancora che il profilo arrivi dal database.

export default function Apertura({ reparto }: { reparto?: Reparto }) {
  const r = reparto ?? repartoRicordato()
  const { colore, scritta } = REPARTI[r]
  const [via, setVia] = useState(false)
  const [tolta, setTolta] = useState(false)

  useEffect(() => {
    const a = window.setTimeout(() => setVia(true), 900)
    const b = window.setTimeout(() => setTolta(true), 1400)
    return () => { window.clearTimeout(a); window.clearTimeout(b) }
  }, [])

  if (tolta) return null
  const base = (import.meta.env.BASE_URL || '/').replace(/\/$/, '')
  return (
    <div aria-hidden style={{ background: colore, opacity: via ? 0 : 1, ['--albero' as string]: 'min(40vh, 40vw, 340px)' }}
         className="fixed inset-0 z-[200] flex flex-col items-center justify-center transition-opacity duration-500">
      {/* LE PROPORZIONI DEL MARCHIO, misurate sui loghi veri della capsula (26/9):
          lo stacco fra albero e scritta e' il 6,8% dell'altezza dell'albero, e la
          scritta su una riga il 14,6%. L'albero prende il 40% del lato corto. */}
      <img src={`${base}/reparti/albero-bianco.svg`} alt=""
           className="w-auto" style={{ height: 'var(--albero)' }} />
      <p className="font-bold tracking-tight text-white"
         style={{ marginTop: 'calc(var(--albero) * 0.068)', fontSize: 'calc(var(--albero) * 0.146)', lineHeight: 1.1 }}>{scritta}</p>
    </div>
  )
}
