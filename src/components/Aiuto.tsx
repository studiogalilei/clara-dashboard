import { useState } from 'react'
import { AIUTI } from '../lib/aiuti'

// IL «?» DI OGNI SCHERMATA (Dre, 5/10): apre il come-si-usa, che racconta il
// workflow in quattro righe. Un componente solo, i testi in lib/aiuti.ts.
export default function Aiuto({ di }: { di: keyof typeof AIUTI }) {
  const [aperto, setAperto] = useState(false)
  const guida = AIUTI[di]
  if (!guida) return null
  return (
    <span className="relative inline-flex">
      <button onClick={() => setAperto((v) => !v)} title="Come si usa" aria-label="Come si usa"
              className="flex h-6 w-6 items-center justify-center rounded-full border border-bordo text-[12px] font-bold text-tenue hover:border-blu hover:text-blu">?</button>
      {aperto && (
        <>
          <span className="fixed inset-0 z-40" onClick={() => setAperto(false)} />
          <span className="absolute left-0 top-8 z-50 block w-[320px] max-w-[85vw] rounded-2xl border border-bordo bg-white p-4 shadow-[0_12px_32px_rgba(6,23,115,0.14)]">
            <span className="block text-[14px] font-extrabold text-navy">{guida.titolo}</span>
            {guida.passi.map((p, i) => (
              <span key={i} className="mt-2 flex gap-2 text-[13px] leading-relaxed text-inchiostro">
                <span className="font-bold tabular-nums text-blu">{i + 1}</span>
                <span>{p}</span>
              </span>
            ))}
          </span>
        </>
      )}
    </span>
  )
}
