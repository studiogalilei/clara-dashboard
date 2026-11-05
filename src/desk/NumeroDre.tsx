// IL NUMERO DI DRE (5/11): dopo «Non ha risposto» Clara scrive al lead «ho provato a chiamarla» e lascia il numero di
// Dre. Il numero sta nelle regole del database (non nel codice): la prima volta il Desk lo chiede qui, una volta sola.
import { useState } from 'react'
import { salvaTelefonoDre } from './dati'
import { telefonoDa } from './regole'
import { Bottone } from '../snella/pezzi'

export function NumeroDre({ fatto, annulla }: { fatto: (numero: string) => void; annulla: () => void }) {
  const [numero, setNumero] = useState('')
  const [lavoro, setLavoro] = useState(false)
  const [errore, setErrore] = useState<string | null>(null)
  const salva = async () => {
    const n = numero.trim()
    if (!telefonoDa(n)) return
    setLavoro(true); setErrore(null)
    try { await salvaTelefonoDre(n); fatto(n) } catch (e) { setErrore(e instanceof Error ? e.message : String(e)) } finally { setLavoro(false) }
  }
  return (
    <div className="space-y-2 rounded-lg border border-bordo bg-fondo/60 p-3">
      <p className="text-[13px] font-semibold text-inchiostro">Il tuo numero, una volta sola: Clara lo lascia nella mail («ho provato a chiamarla, mi trova al…»).</p>
      <div className="flex gap-2">
        <input value={numero} onChange={(e) => setNumero(e.target.value)} type="tel" autoFocus placeholder="+39 …" aria-label="Il tuo numero di telefono"
               onKeyDown={(e) => { if (e.key === 'Enter') void salva() }}
               className="min-h-10 min-w-0 flex-1 rounded-lg border border-bordo bg-white px-3 text-[14px] outline-none focus:border-navy" />
        <Bottone tipo="primo" onClick={() => void salva()} disabled={lavoro || !telefonoDa(numero)} className="px-3">Salva</Bottone>
        <Bottone tipo="piatto" onClick={annulla} disabled={lavoro}>Annulla</Bottone>
      </div>
      {errore && <p className="text-[12.5px] text-no-testo">{errore}</p>}
    </div>
  )
}
