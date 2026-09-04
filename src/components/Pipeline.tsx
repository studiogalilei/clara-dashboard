import { useEffect, useState } from 'react'
import { contaFasi, type Fascia } from '../lib/regole'
import Radar from './Radar'
import { Micro, Spinner, fmtNum } from './ui'

// La home (ordine di Dre, 1/9): le fasi coi numeri in alto, poi il radar
// (da fare oggi, avvisi, in settimana, la Prossima, la lista avvisi).
// La bacheca vera, con le carte e il pedaggio, vive nella sezione «Tutti».
// I numeri li conta il database (2/9): prima si contavano le prime 300
// righe scaricate, e sui 13k veri il conto si fermava lì.

interface Props {
  onOpen: (id: string) => void
  onOggi?: () => void
  onCalendario?: () => void
  onTutti?: () => void
}

// [nome, colore-fase (lo stesso delle facce), quale fascia]. I numeri li
// conta regole.ts: sono gli stessi che vedi sulle colonne della bacheca,
// e prima erano due conti diversi a un click di distanza (revisione 4/9)
const FASI: Array<[string, string, Fascia]> = [
  ['Prospect', 'bg-amber-400', 'prospect'],
  ['Call Conoscitiva', 'bg-[#6b85e0]', 'conoscitiva'],
  ['Call Tecnica', 'bg-blu', 'tecnica'],
  ['Call di Avvio', 'bg-navy', 'avvio'],
]

export default function Pipeline({ onOpen, onOggi, onCalendario, onTutti }: Props) {
  const [numeri, setNumeri] = useState<Record<Fascia, number> | null>(null)

  useEffect(() => { contaFasi().then(setNumeri) }, [])

  if (numeri === null) return <Spinner />

  return (
    <div className="space-y-4 pb-24 sm:pb-8">

      {/* ── le fasi, coi numeri ───────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {FASI.map(([nome, colore, fascia]) => (
          <button
            key={nome}
            onClick={onTutti}
            className="rounded-2xl border border-bordo bg-white p-4 text-left shadow-[0_1px_2px_rgba(16,24,40,0.03),0_4px_16px_rgba(16,24,40,0.04)] transition-transform hover:-translate-y-px"
          >
            <span className="flex items-center gap-1.5">
              <span className={`inline-block h-[7px] w-[7px] shrink-0 rounded-full ${colore}`} />
              <Micro>{nome}</Micro>
            </span>
            <p className="mt-1 text-[26px] font-extrabold leading-none tabular-nums">
              {fmtNum(numeri[fascia] ?? 0)}
            </p>
          </button>
        ))}
      </div>

      <Radar onOpen={onOpen} onOggi={onOggi} onCalendario={onCalendario} />
    </div>
  )
}
