// LE NOTE DI DRE (4/11: «fai che si vedano un po' di più, sono cose che ho scritto io»; «dammi la possibilità di
// modificarle, così non ne creo di nuove, modifico sempre l'unica»): un foglietto giallo, «Tua nota», la data piccola,
// e un tocco sul testo per correggerlo. Uguale nelle call e nel Profilo.
import { useState } from 'react'
import { quando } from '../snella/regole'
import { Bottone } from '../snella/pezzi'

export function Note({ note, className = '', modifica }: { note: Array<{ at: string; testo: string }>; className?: string; modifica?: (indice: number, testo: string) => Promise<void> }) {
  const [aperta, setAperta] = useState<number | null>(null)
  const [testo, setTesto] = useState('')
  const [lavoro, setLavoro] = useState(false)
  if (note.length === 0) return null
  const salva = async (i: number) => {
    if (!modifica || !testo.trim()) return
    setLavoro(true)
    try { await modifica(i, testo.trim()); setAperta(null) } finally { setLavoro(false) }
  }
  return (
    <ul className={`space-y-2 ${className}`}>
      {note.map((n, i) => (
        <li key={i} className="rounded-xl border border-giallo-bordo bg-giallo-fondo px-3 py-2.5">
          <p className="mb-0.5 text-[11px] font-extrabold uppercase tracking-[.08em] text-giallo-testo">Tua nota <span className="font-semibold normal-case tracking-normal text-giallo-testo/80">{quando(n.at)}</span></p>
          {aperta === i ? (
            <div>
              <textarea value={testo} onChange={(e) => setTesto(e.target.value)} autoFocus rows={3} aria-label="Modifica la nota"
                        className="w-full rounded-lg border border-giallo-bordo bg-white px-3 py-2 text-[14.5px] leading-snug outline-none focus:border-navy" />
              <div className="mt-1.5 flex gap-2">
                <Bottone tipo="primo" onClick={() => void salva(i)} disabled={lavoro || !testo.trim()} className="text-[13px]">Salva</Bottone>
                <Bottone tipo="piatto" onClick={() => setAperta(null)} disabled={lavoro} className="text-[13px]">Annulla</Bottone>
              </div>
            </div>
          ) : modifica ? (
            <button type="button" onClick={() => { setAperta(i); setTesto(n.testo) }} title="Tocca per modificare" className="block w-full text-left text-[14.5px] font-semibold leading-snug text-inchiostro hover:underline decoration-giallo-bordo underline-offset-4">{n.testo}</button>
          ) : (
            <p className="text-[14.5px] font-semibold leading-snug text-inchiostro">{n.testo}</p>
          )}
        </li>
      ))}
    </ul>
  )
}
