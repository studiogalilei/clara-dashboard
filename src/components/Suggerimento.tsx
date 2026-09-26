import { useEffect, useState } from 'react'

// IL SUGGERIMENTO (Dre, 26/9): «quella cosa che passi con il puntatore sopra ed
// escono le descrizioni con un breve testo: lo voglio». Un solo strato per tutta
// l'app: legge `data-tip` (o il `title`, che viene spostato li' per non far
// comparire quello grigio del browser), aspetta un attimo e mostra il testo in
// una targhetta navy vicino al puntatore. Sul telefono non c'e' il puntatore e
// non compare. Per dare un suggerimento a qualcosa basta data-tip="...".

type Stato = { testo: string; x: number; y: number; sotto: boolean } | null

export default function Suggerimento() {
  const [s, setS] = useState<Stato>(null)

  useEffect(() => {
    if (window.matchMedia('(hover: none)').matches) return
    let timer: number | undefined
    let vita: number | undefined
    let corrente: Element | null = null

    function mostra(el: Element) {
      const testo = el.getAttribute('data-tip') || ''
      if (!testo || !el.isConnected) return
      // dopo otto secondi sparisce da solo: l'hai letto, e se il puntatore resta
      // fermo non arriva nessun altro evento a spegnerlo
      window.clearTimeout(vita); vita = window.setTimeout(spegni, 8000)
      const r = el.getBoundingClientRect()
      const sotto = r.top < 56                         // troppo in alto: la targhetta va sotto
      setS({ testo, x: r.left + r.width / 2, y: sotto ? r.bottom + 8 : r.top - 8, sotto })
    }
    function sopra(e: Event) {
      const el = (e.target as Element | null)?.closest?.('[data-tip], [title]') ?? null
      if (!el || el === corrente) return
      corrente = el
      // il title del browser si sposta in data-tip: uno solo, il nostro
      const t = el.getAttribute('title')
      if (t && !el.getAttribute('data-tip')) { el.setAttribute('data-tip', t); el.removeAttribute('title') }
      window.clearTimeout(timer)
      timer = window.setTimeout(() => mostra(el), 260)
    }
    function via(e: Event) {
      const el = (e.target as Element | null)?.closest?.('[data-tip]') ?? null
      if (el && el !== corrente) return
      window.clearTimeout(timer); corrente = null; setS(null)
    }
    function spegni() { window.clearTimeout(timer); window.clearTimeout(vita); corrente = null; setS(null) }
    // se il puntatore esce dall'elemento senza che il browser lo dica, si spegne lo stesso
    function muove(e: MouseEvent) {
      if (corrente && (!corrente.isConnected || !corrente.contains(e.target as Node))) spegni()
    }
    // se l'elemento sparisce dalla pagina (cambio sezione, lista rifatta), il
    // suggerimento non resta appeso in aria
    let dove = { x: -1, y: -1 }
    document.addEventListener('mousemove', (e) => { dove = { x: e.clientX, y: e.clientY } }, { passive: true })
    const guardia = window.setInterval(() => {
      if (!corrente) return
      // sparito dalla pagina, o il puntatore non e' piu' sopra: si spegne
      if (!corrente.isConnected) { spegni(); return }
      if (dove.x >= 0) {
        const sotto = document.elementFromPoint(dove.x, dove.y)
        if (!sotto || !corrente.contains(sotto)) spegni()
      }
    }, 120)
    document.addEventListener('mousemove', muove)
    window.addEventListener('hashchange', spegni)
    window.addEventListener('popstate', spegni)
    document.addEventListener('mouseover', sopra)
    document.addEventListener('mouseout', via)
    document.addEventListener('focusin', sopra)
    document.addEventListener('focusout', via)
    document.addEventListener('mousedown', spegni)
    document.addEventListener('scroll', spegni, true)
    document.addEventListener('keydown', spegni)
    return () => {
      document.removeEventListener('mouseover', sopra); document.removeEventListener('mouseout', via)
      document.removeEventListener('focusin', sopra); document.removeEventListener('focusout', via)
      document.removeEventListener('mousedown', spegni); document.removeEventListener('scroll', spegni, true)
      document.removeEventListener('keydown', spegni); document.removeEventListener('mousemove', muove)
      window.removeEventListener('hashchange', spegni); window.removeEventListener('popstate', spegni)
      window.clearInterval(guardia)
    }
  }, [])

  if (!s) return null
  const larg = Math.min(280, window.innerWidth - 24)
  const left = Math.min(Math.max(s.x - larg / 2, 12), window.innerWidth - larg - 12)
  return (
    <div role="tooltip" style={{ left, top: s.y, width: 'max-content', maxWidth: larg, transform: s.sotto ? 'none' : 'translateY(-100%)' }}
         className="pointer-events-none fixed z-[90] rounded-[8px] bg-navy px-2.5 py-1.5 text-[12px] font-medium leading-snug text-white shadow-[var(--shadow-alta)]">
      {s.testo}
      <span style={{ left: Math.min(Math.max(s.x - left, 10), larg - 10) }}
            className={`absolute h-2 w-2 -translate-x-1/2 rotate-45 bg-navy ${s.sotto ? '-top-1' : '-bottom-1'}`} />
    </div>
  )
}
