// LA NOTA DI DRE: UNA (5/11, Dre: «voglio scrivere solo in un box, non in più box; per modificare faccio doppio tocco
// e comunque resta giallo mentre scrivo»). Un foglietto giallo sempre uguale: si legge; con due tocchi si scrive
// dentro, senza cambiare colore; si salva da solo (dopo una pausa e quando esci). Niente «Salva», niente lista.
import { useEffect, useRef, useState } from 'react'
import { quando } from '../snella/regole'

const DOPPIO_MS = 400

export function NotaUnica({ testo, at, salva, className = '' }: { testo: string; at?: string | null; salva: (testo: string) => Promise<void>; className?: string }) {
  const [valore, setValore] = useState(testo)
  const [modifico, setModifico] = useState(false)
  const [stato, setStato] = useState<'ferma' | 'scrivo' | 'salvo' | 'salvata' | 'errore'>('ferma')
  const salvato = useRef(testo)
  const timer = useRef<number | null>(null)
  const ultimoTocco = useRef(0)
  const area = useRef<HTMLTextAreaElement>(null)
  // se la nota cambia da fuori (ricarico, altro gesto) e qui non si sta scrivendo, si allinea
  useEffect(() => { if (testo !== salvato.current && !modifico) { salvato.current = testo; setValore(testo) } }, [testo, modifico])
  useEffect(() => { const a = area.current; if (a) { a.style.height = 'auto'; a.style.height = `${a.scrollHeight}px`; a.focus(); a.setSelectionRange(a.value.length, a.value.length) } }, [modifico])
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
  const esci = () => { if (timer.current) { window.clearTimeout(timer.current); timer.current = null } setModifico(false); void scrivi(valore) }
  // due tocchi ravvicinati (dito o mouse) aprono la modifica; il doppio clic del computer vale lo stesso
  const tocco = () => { const ora = Date.now(); if (ora - ultimoTocco.current < DOPPIO_MS) { ultimoTocco.current = 0; setModifico(true) } else ultimoTocco.current = ora }
  useEffect(() => () => { if (timer.current) window.clearTimeout(timer.current) }, [])
  const detto = stato === 'salvo' ? 'salvo…' : stato === 'salvata' ? 'salvata' : stato === 'errore' ? 'non salvata: riprova' : modifico ? 'scrivi, si salva da sola' : at && valore.trim() ? quando(at) : ''
  return (
    <div className={`rounded-xl border border-giallo-bordo bg-giallo-fondo px-3 py-2.5 ${className}`}>
      <p className="mb-0.5 flex items-baseline justify-between text-[11px] font-extrabold uppercase tracking-[.08em] text-giallo-testo">
        Tua nota <span className={`font-semibold normal-case tracking-normal ${stato === 'errore' ? 'text-rosso' : 'text-giallo-testo/80'}`}>{detto}</span>
      </p>
      {modifico ? (
        <textarea ref={area} value={valore} onChange={(e) => cambia(e.target.value)} onBlur={esci} rows={1} placeholder="Scrivi qui" aria-label="Tua nota"
                  className="block w-full resize-none bg-transparent text-[14.5px] font-semibold leading-snug text-inchiostro outline-none focus-visible:outline-none placeholder:font-normal placeholder:text-giallo-testo/60" />
      ) : (
        <button type="button" onPointerUp={tocco} onDoubleClick={() => setModifico(true)} aria-label="Tua nota: due tocchi per scrivere" title="Due tocchi per scrivere"
                className={`block w-full select-none whitespace-pre-wrap text-left text-[14.5px] leading-snug ${valore.trim() ? 'font-semibold text-inchiostro' : 'font-normal text-giallo-testo/60'}`}>
          {valore.trim() || 'Due tocchi per scrivere'}
        </button>
      )}
    </div>
  )
}
