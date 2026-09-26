import { useEffect, useMemo, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'
import { menuDi, type Chiave, type Ruolo } from '../lib/widget'
import { recenti } from '../lib/recenti'
import { Spinner } from './ui'

// LA PALETTE DEI COMANDI (Dre, 26/9: «il feel di un software professionale, la
// navigabilita', come arrivo alle info»). Un campo solo, ⌘K da qualunque punto:
// cerchi un'azienda e ci entri, scrivi il nome di una sezione e ci vai, scrivi
// un'azione e la fai. Prima ancora di scrivere, ti mostra dove sei stato.
// Si guida con le frecce e Invio, si chiude con Esc.

export interface Comando {
  id: string
  titolo: string
  sotto?: string
  gruppo: 'Vai a' | 'Visti di recente' | 'Aziende' | 'Azioni'
  fai: () => void
}

export default function Comandi({ aperto, chiudi, ruolo, concessi, vaiA, apriScheda, azioni }: {
  aperto: boolean
  chiudi: () => void
  ruolo: Ruolo
  concessi: ReadonlySet<Chiave>
  vaiA: (t: Chiave) => void
  apriScheda: (id: string) => void
  azioni: Comando[]
}) {
  const [q, setQ] = useState('')
  const [scelto, setScelto] = useState(0)
  const [trovate, setTrovate] = useState<Array<{ id: string; company: string | null; name: string | null; email: string | null; city: string | null }>>([])
  const [cerco, setCerco] = useState(false)
  const campo = useRef<HTMLInputElement>(null)

  useEffect(() => { if (aperto) { setQ(''); setScelto(0); setTrovate([]); setTimeout(() => campo.current?.focus(), 20) } }, [aperto])
  // finche' la palette e' aperta, l'Esc e' suo: la scheda sotto non si chiude
  useEffect(() => {
    if (!aperto) return
    document.body.dataset.sopra = 'comandi'
    return () => { delete document.body.dataset.sopra }
  }, [aperto])

  // le aziende: si cercano nel database, non solo fra quelle già caricate
  useEffect(() => {
    if (!aperto || q.trim().length < 2) { setTrovate([]); return }
    let vivo = true
    setCerco(true)
    const t = setTimeout(() => {
      const s = q.trim().replace(/[%,]/g, ' ')
      void supabase.from('prospects').select('id,company,name,email,city')
        .or(`company.ilike.%${s}%,name.ilike.%${s}%,email.ilike.%${s}%`).limit(8)
        .then(({ data }) => { if (vivo) { setTrovate(data ?? []); setCerco(false) } })
    }, 180)
    return () => { vivo = false; clearTimeout(t) }
  }, [q, aperto])

  const lista = useMemo<Comando[]>(() => {
    const testo = q.trim().toLowerCase()
    const sezioni: Comando[] = [...menuDi(ruolo, 'menu', concessi), ...menuDi(ruolo, 'sistema', concessi)]
      .map((w) => ({ id: `vai:${w.chiave}`, titolo: w.nome, sotto: w.cosa, gruppo: 'Vai a' as const, fai: () => vaiA(w.chiave) }))
    const viste: Comando[] = testo ? [] : recenti().slice(0, 5)
      .map((r) => ({ id: `rec:${r.id}`, titolo: r.nome, gruppo: 'Visti di recente' as const, fai: () => apriScheda(r.id) }))
    const az: Comando[] = azioni
    const aziende: Comando[] = trovate.map((p) => ({
      id: `az:${p.id}`,
      titolo: p.company || p.name || p.email || 'senza nome',
      sotto: [p.name, p.city, p.email].filter(Boolean).join(' · '),
      gruppo: 'Aziende' as const,
      fai: () => apriScheda(p.id),
    }))
    const filtra = (c: Comando[]) => testo ? c.filter((x) => (x.titolo + ' ' + (x.sotto ?? '')).toLowerCase().includes(testo)) : c
    return [...viste, ...aziende, ...filtra(sezioni), ...filtra(az)]
  }, [q, ruolo, concessi, trovate, azioni, vaiA, apriScheda])

  useEffect(() => { setScelto((s) => Math.min(s, Math.max(0, lista.length - 1))) }, [lista.length])

  if (!aperto) return null
  const gruppi = lista.reduce<Record<string, Comando[]>>((m, c) => { (m[c.gruppo] ||= []).push(c); return m }, {})
  let indice = -1

  return (
    <div className="fixed inset-0 z-[120] flex items-start justify-center px-4 pt-[12vh]" onMouseDown={chiudi}>
      <div className="absolute inset-0 bg-inchiostro/25" />
      <div onMouseDown={(e) => e.stopPropagation()} role="dialog" aria-label="Comandi"
           className="carta carta-alta relative w-full max-w-[620px] overflow-hidden">
        <div className="flex items-center gap-2 border-b border-velo px-4 py-3">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="h-[18px] w-[18px] shrink-0 text-spento"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
          <input
            ref={campo} value={q} onChange={(e) => { setQ(e.target.value); setScelto(0) }}
            placeholder="Cerca un'azienda, una sezione, un'azione…"
            className="min-w-0 flex-1 bg-transparent text-[15px] outline-none placeholder:text-spento"
            onKeyDown={(e) => {
              if (e.key === 'ArrowDown') { e.preventDefault(); setScelto((s) => Math.min(s + 1, lista.length - 1)) }
              if (e.key === 'ArrowUp') { e.preventDefault(); setScelto((s) => Math.max(s - 1, 0)) }
              if (e.key === 'Enter') { e.preventDefault(); const c = lista[scelto]; if (c) { c.fai(); chiudi() } }
              if (e.key === 'Escape') { e.preventDefault(); chiudi() }
            }}
          />
          {cerco && <Spinner />}
          <kbd className="shrink-0 rounded border border-bordo px-1.5 py-0.5 text-[10px] font-semibold text-spento">esc</kbd>
        </div>
        <div className="max-h-[52vh] overflow-y-auto py-1">
          {lista.length === 0 && <p className="px-4 py-6 text-center text-sm text-spento">Niente con «{q}». Prova con il nome dell'azienda o della sezione.</p>}
          {Object.entries(gruppi).map(([nome, voci]) => (
            <div key={nome}>
              <p className="px-4 pb-1 pt-2 text-[10px] font-bold uppercase tracking-[0.06em] text-spento">{nome}</p>
              {voci.map((c) => {
                indice += 1
                const mio = indice
                return (
                  <button
                    key={c.id}
                    onMouseEnter={() => setScelto(mio)}
                    onClick={() => { c.fai(); chiudi() }}
                    className={`flex w-full items-baseline gap-2 px-4 py-2 text-left ${scelto === mio ? 'bg-velo' : ''}`}
                  >
                    <span className="shrink-0 text-[14px] font-semibold text-inchiostro">{c.titolo}</span>
                    {c.sotto && <span className="min-w-0 flex-1 truncate text-[12px] text-tenue">{c.sotto}</span>}
                  </button>
                )
              })}
            </div>
          ))}
        </div>
        <div className="flex items-center gap-3 border-t border-velo px-4 py-1.5 text-[11px] text-spento">
          <span>↑↓ per scegliere</span><span>Invio per aprire</span><span className="ml-auto">⌘K da qualunque pagina</span>
        </div>
      </div>
    </div>
  )
}
