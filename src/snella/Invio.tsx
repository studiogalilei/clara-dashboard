// LA BARRA DELL'INVIO (22/10/2026). Dre: quando premo «Manda» voglio vedere che parte, come nella schermata
// di prenotazione: «Attendi qualche secondo», una barra, poi «Inviata». La mail la spedisce scripts/manda.py in
// cloud, nei giri del direttore (misurato: di solito 3-10 minuti), non l'app: la barra legge lo stato vero dal
// database ogni pochi secondi, e dice che si puo' chiudere l'app. Niente timer finto: «Inviata» solo a «fatta».
import { useEffect, useRef, useState } from 'react'
import { leggiInvio } from './dati'
import { statoInvio, type PropostaInvio, type StatoInvio } from './regole'
import { Icona } from './pezzi'

export interface Invio { proposta: number; prospect: string; approvata: Date; azienda: string }

const OGNI_MS = 5000

export function BarraInvio({ invio, chiudi, finita: alla_fine }: { invio: Invio; chiudi: () => void; finita?: () => void }) {
  const [p, setP] = useState<PropostaInvio | null>(null)
  const [analisiPronta, setAnalisiPronta] = useState(true)
  const [ora, setOra] = useState(() => new Date())
  const [rete, setRete] = useState(false)
  const finita = useRef(false)

  useEffect(() => {
    let vivo = true
    async function guarda() {
      if (finita.current || document.visibilityState !== 'visible') return
      try {
        const r = await leggiInvio(invio.proposta, invio.prospect)
        if (!vivo) return
        setP(r.proposta); setAnalisiPronta(r.analisiPronta); setRete(false)
        if (r.proposta && ['fatta', 'no', 'aperta'].includes(r.proposta.stato)) {
          finita.current = true
          alla_fine?.()                     // la scheda sotto si rilegge: niente piu' «Parte a minuti» quando e' gia' finita
        }
      } catch {
        if (vivo) setRete(true)
      }
    }
    void guarda()
    const t = window.setInterval(() => { setOra(new Date()); void guarda() }, OGNI_MS)
    const vis = () => { if (document.visibilityState === 'visible') { setOra(new Date()); void guarda() } }
    document.addEventListener('visibilitychange', vis)
    return () => { vivo = false; window.clearInterval(t); document.removeEventListener('visibilitychange', vis) }
  }, [invio.proposta, invio.prospect, alla_fine])

  const s: StatoInvio = statoInvio(p, { approvata: invio.approvata, ora, aspettaAnalisi: !analisiPronta })
  // «Inviata» resta qualche secondo e poi se ne va da sola; un errore resta finche' Dre non lo chiude
  useEffect(() => {
    if (s.fase !== 'inviata') return
    const t = window.setTimeout(chiudi, 8000)
    return () => window.clearTimeout(t)
  }, [s.fase, chiudi])

  const colore = s.fase === 'inviata' ? 'bg-ok-segno' : s.fase === 'ferma' ? 'bg-no-segno' : s.fase === 'notte' || s.fase === 'analisi' ? 'bg-attesa-segno' : 'bg-blu'
  const testo = s.fase === 'inviata' ? 'text-ok-testo' : s.fase === 'ferma' ? 'text-no-testo' : 'text-inchiostro'
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-[calc(76px+env(safe-area-inset-bottom))] z-40 flex justify-center px-4 lg:bottom-6">
      <section aria-label={`Invio a ${invio.azienda}`} role="status" aria-live="polite"
               className="pointer-events-auto w-full max-w-md overflow-hidden rounded-2xl border border-bordo bg-white shadow-lg">
        <div className="flex items-start gap-3 px-4 pt-3">
          <span className={`mt-0.5 shrink-0 ${testo}`}>
            <Icona nome={s.fase === 'inviata' ? 'ok' : s.fase === 'ferma' ? 'divieto' : 'campagna'} className="h-5 w-5" />
          </span>
          <div className="min-w-0 flex-1">
            <p className={`text-[16px] font-bold leading-snug ${testo}`}>{s.titolo}</p>
            <p className="mt-0.5 text-[14px] leading-snug text-tenue">
              {s.fase === 'inviata' ? `${invio.azienda}. ${s.frase}` : s.frase}
              {rete && ' Non riesco a leggere lo stato adesso: riprovo da solo.'}
            </p>
          </div>
          <button onClick={chiudi} aria-label="Chiudi"
                  className="-mr-2 -mt-1 inline-flex min-h-11 min-w-11 shrink-0 items-center justify-center rounded-full text-tenue transition-colors duration-150 hover:bg-velo focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blu">
            <Icona nome="chiudi" className="h-4 w-4" />
          </button>
        </div>
        <div className="mx-4 mb-3 mt-2.5 h-1.5 overflow-hidden rounded-full bg-velo" role="progressbar" aria-label="Avanzamento dell'invio"
             aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(s.progresso * 100)}>
          <div className={`h-full rounded-full ${colore} transition-[width] duration-700 ease-out motion-reduce:transition-none`}
               style={{ width: `${Math.max(s.fase === 'ferma' ? 100 : 4, Math.round(s.progresso * 100))}%` }} />
        </div>
      </section>
    </div>
  )
}
