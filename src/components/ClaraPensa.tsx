import { useEffect, useState } from 'react'
import ClaraLogo from './ClaraLogo'

// Mentre Clara pensa si vede che pensa (Dre, 9/9): «come Claude, cosi' so
// che non e' bloccato e non sto aspettando per niente». Il logo lavora e
// cambia forma, una frase ogni due secondi, i secondi che passano.

const FRASI = [
  'Rileggo la storia…', 'Sfoglio le mail…', 'Guardo il calendario…', 'Conto i giorni…',
  'Mi gratto la testa…', 'Cerco il nome giusto…', 'Metto in fila le cose…', 'Controllo due volte…',
  'Chiedo al cervello…', 'Riordino i post-it…', 'Faccio due conti…', 'Ci sono quasi…',
  'Collego i puntini…', 'Verifico chi segue chi…', 'Tiro le somme…', 'Un attimo, ragiono…',
]

export default function ClaraPensa({ da }: { da: number }) {
  const [i, setI] = useState(() => Math.floor(Math.random() * FRASI.length))
  const [sec, setSec] = useState(0)
  useEffect(() => {
    const f = setInterval(() => setI((x) => (x + 1 + Math.floor(Math.random() * 3)) % FRASI.length), 2000)
    const s = setInterval(() => setSec(Math.round((Date.now() - da) / 1000)), 1000)
    return () => { clearInterval(f); clearInterval(s) }
  }, [da])
  return (
    <div className="flex items-center gap-2.5 px-1 py-1.5" aria-live="polite">
      <span className="text-navy"><ClaraLogo size={26} lavora /></span>
      <span key={i} className="salta-su text-sm text-tenue">{FRASI[i]}</span>
      {sec >= 3 && <span className="ml-auto text-[11px] tabular-nums text-spento">{sec}s</span>}
    </div>
  )
}
