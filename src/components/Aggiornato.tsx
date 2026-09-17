import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'

// QUANTO E' FRESCO QUELLO CHE VEDI (Dre, 15/9): «metti la scritta
// dell'ultimo aggiornamento, così so almeno a quanto è datato. L'obiettivo
// è portarlo a real time».
//
// Sta sotto il saluto, in verde, piccola: chi entra la legge senza cercarla
// e chi non gliene importa non la nota. Il verde vuol dire fresco; se il
// giro si ferma diventa ambra e poi rossa, perche' a quel punto non e' piu'
// un dettaglio: e' il motivo per cui una carta dice una cosa vecchia.
//
// Si aggiorna da sola: il testo si ricalcola ogni mezzo minuto e la domanda
// al database si rifa' ogni due. Non e' ancora il tempo reale, ma e' la
// stessa riga che diventera' tempo reale quando ci arriveremo.

const MIN = 60000

function frase(quando: Date): { testo: string; tono: string } {
  const min = Math.floor((Date.now() - quando.getTime()) / MIN)
  const ora = quando.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
  if (min < 2) return { testo: 'Clara ha appena controllato tutto', tono: 'text-green-700' }
  if (min < 60) return { testo: `Clara ha controllato tutto ${min} minuti fa`, tono: 'text-green-700' }
  const ore = Math.floor(min / 60)
  // fino a 3 ore e' normale (e' lo stesso confine del Radar), poi e' fermo
  if (ore < 3) return { testo: `Clara ha controllato tutto ${ore === 1 ? "un'ora" : `${ore} ore`} fa, alle ${ora}`, tono: 'text-green-700' }
  if (ore < 6) return { testo: `L'ultimo controllo è di ${ore} ore fa, alle ${ora}: Clara è ferma`, tono: 'text-amber-700' }
  if (ore < 24) return { testo: `L'ultimo controllo è di stamattina, alle ${ora}`, tono: 'text-amber-700' }
  const giorni = Math.floor(ore / 24)
  return { testo: `Il controllo è fermo da ${giorni} ${giorni === 1 ? 'giorno' : 'giorni'}: quello che vedi è vecchio`, tono: 'text-red-700' }
}

export default function Aggiornato() {
  const [quando, setQuando] = useState<Date | null>(null)
  const [, ridisegna] = useState(0)

  useEffect(() => {
    let vivo = true
    const chiedi = async () => {
      const { data } = await supabase.rpc('ultimo_giro')
      if (vivo && data) setQuando(new Date(data as string))
    }
    void chiedi()
    const q = setInterval(() => void chiedi(), 2 * MIN)
    const t = setInterval(() => ridisegna((n) => n + 1), MIN / 2)
    return () => { vivo = false; clearInterval(q); clearInterval(t) }
  }, [])

  if (!quando) return null
  const { testo, tono } = frase(quando)
  return (
    <p className={`mt-1.5 flex items-center gap-1.5 text-[12px] font-semibold ${tono}`}>
      <span className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-current" />
      {testo}
    </p>
  )
}
