// LA NOTA DI DRE: UNA (5/11, Dre: «voglio scrivere solo in un box, non in più box; non voglio che quando clicco
// diventi bianco: rimane giallo, ci scrivo e basta»). Un foglietto giallo sempre uguale: tocchi, scrivi, si salva da
// solo (dopo una pausa e quando esci). Niente «Salva», niente lista. Uguale in Call e nel Profilo.
import { useEffect, useRef, useState } from 'react'
import { quando } from '../snella/regole'

export function NotaUnica({ testo, at, salva, className = '' }: { testo: string; at?: string | null; salva: (testo: string) => Promise<void>; className?: string }) {
  const [valore, setValore] = useState(testo)
  const [stato, setStato] = useState<'ferma' | 'scrivo' | 'salvo' | 'salvata' | 'errore'>('ferma')
  const salvato = useRef(testo)
  const timer = useRef<number | null>(null)
  const area = useRef<HTMLTextAreaElement>(null)
  // se la nota cambia da fuori (ricarico, altro gesto) e qui non si sta scrivendo, si allinea
  useEffect(() => { if (testo !== salvato.current && stato !== 'scrivo') { salvato.current = testo; setValore(testo) } }, [testo, stato])
  useEffect(() => { const a = area.current; if (a) { a.style.height = 'auto'; a.style.height = `${a.scrollHeight}px` } }, [valore])
  const scrivi = async (t: string) => {
    const pulito = t.trim()
    if (pulito === salvato.current.trim()) { setStato('ferma'); return }
    setStato('salvo')
    try { await salva(pulito); salvato.current = pulito; setStato('salvata'); window.setTimeout(() => setStato((s) => s === 'salvata' ? 'ferma' : s), 1500) }
    catch { setStato('errore') }
  }
  const cambia = (t: string) => {
    setValore(t); setStato('scrivo')
    if (timer.current) window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => void scrivi(t), 1200)
  }
  const esci = () => { if (timer.current) { window.clearTimeout(timer.current); timer.current = null } void scrivi(valore) }
  useEffect(() => () => { if (timer.current) window.clearTimeout(timer.current) }, [])
  const detto = stato === 'salvo' ? 'salvo…' : stato === 'salvata' ? 'salvata' : stato === 'errore' ? 'non salvata: riprova' : at && valore.trim() ? quando(at) : ''
  return (
    <label className={`block rounded-xl border border-giallo-bordo bg-giallo-fondo px-3 py-2.5 ${className}`}>
      <span className="mb-0.5 flex items-baseline justify-between text-[11px] font-extrabold uppercase tracking-[.08em] text-giallo-testo">
        Tua nota <span className={`font-semibold normal-case tracking-normal ${stato === 'errore' ? 'text-rosso' : 'text-giallo-testo/80'}`}>{detto}</span>
      </span>
      <textarea ref={area} value={valore} onChange={(e) => cambia(e.target.value)} onBlur={esci} rows={1} placeholder="Scrivi qui" aria-label="Tua nota"
                className="block w-full resize-none bg-transparent text-[14.5px] font-semibold leading-snug text-inchiostro outline-none placeholder:font-normal placeholder:text-giallo-testo/60" />
    </label>
  )
}
