import { useEffect, useRef, useState } from 'react'
import ClaraLogo from './ClaraLogo'
import {
  STAGE_LABEL, CLS_LABEL, PIPELINE_LABEL,
  type Stage, type Classificazione, type PipelineStage, type Market, type Prospect,
} from '../lib/types'

// L'ETICHETTA DI STATO (rifatta 16/9). Dre: «le pillole pastello sanno di
// roba generata dall'AI, voglio un feel piu' meccanico, serio».
// Quindi: niente fondo colorato e niente pillola tonda. Un rettangolo con
// il bordo sottile, il testo in maiuscoletto come su una targhetta, e il
// colore ridotto a un punto: il colore dice lo stato, il testo lo nomina,
// e la forma resta sempre la stessa in tutta l'app.
function Eti({ testo, tono }: { testo: string; tono?: 'verde' | 'ambra' | 'rosso' }) {
  const punto =
    tono === 'verde' ? 'bg-green-600'
    : tono === 'ambra' ? 'bg-amber-500'
    : tono === 'rosso' ? 'bg-red-600'
    : 'bg-spento'
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-[4px] border border-bordo bg-white px-2 py-[3px] text-[10.5px] font-bold uppercase tracking-[0.06em] text-tenue">
      <span className={`h-[5px] w-[5px] shrink-0 rounded-[1px] ${punto}`} />
      {testo}
    </span>
  )
}

export function StageBadge({ stage }: { stage: Stage }) {
  const tono = stage === 'cliente' ? 'verde' : stage === 'perso' ? 'rosso' : undefined
  return <Eti testo={STAGE_LABEL[stage] ?? stage} tono={tono} />
}

export function ClsBadge({ cls }: { cls: Classificazione }) {
  const tono = cls === 'positivo' ? 'verde' : cls === 'negativo' ? 'rosso' : cls === 'tiepido' || cls === 'rinvio' ? 'ambra' : undefined
  return <Eti testo={CLS_LABEL[cls] ?? cls} tono={tono} />
}

export function PipelineBadge({ stage }: { stage: PipelineStage }) {
  const tono = stage === 'cliente' ? 'verde' : stage === 'perso' ? 'rosso' : undefined
  return <Eti testo={PIPELINE_LABEL[stage] ?? stage} tono={tono} />
}

export { Eti }

// Pallino di stato: verde = ok, ambra = in attesa, rosso = fermo/problema,
// grigio = mai acceso (che non è un guasto)
export function Dot({ tone }: { tone: 'ok' | 'attesa' | 'fermo' | 'spento' }) {
  const c = tone === 'ok' ? 'bg-green-600' : tone === 'attesa' ? 'bg-amber-500'
    : tone === 'spento' ? 'bg-gray-300' : 'bg-red-600'
  return <span className={`inline-block h-[7px] w-[7px] shrink-0 rounded-full ${c}`} />
}

export function Avatar({ nome, azienda }: { nome: string | null; azienda: string | null }) {
  return (
    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-navy text-sm font-bold text-white">
      {initials(nome, azienda)}
    </div>
  )
}

// Il colore della fase, unico in tutta l'app: ambra = prospect (come il
// badge PROSPECT), poi il blu si scurisce man mano che avanza nelle call,
// verde = cliente, grigio = perso. Il colore dice dov'e', senza leggere.
export type FacciaP = Pick<Prospect, 'sg_id' | 'name' | 'company' | 'fuori' | 'stage' | 'pipeline_stage'>

export function tonoFase(p: Pick<FacciaP, 'fuori' | 'stage' | 'pipeline_stage'>): string {
  const perso = (p.fuori && p.pipeline_stage === 'perso') || (!p.fuori && p.stage === 'perso')
  const cliente = (p.fuori && p.pipeline_stage === 'cliente') || (!p.fuori && p.stage === 'cliente')
  if (perso) return 'bg-gray-200 text-gray-500'
  if (cliente) return 'bg-green-600 text-white'
  if (p.fuori) {
    if (p.pipeline_stage === 'tecnica') return 'bg-blu text-white'
    if (p.pipeline_stage === 'avvio') return 'bg-blu text-white'
    if (p.pipeline_stage === 'prova') return 'bg-teal-600 text-white'
    return 'bg-[#6b85e0] text-white'
  }
  return 'bg-amber-400 text-amber-950'
}

// La «foto profilo» di un lead: le due cifre finali del suo SG-ID sul
// colore della fase. Chi non ha ancora l'ID (mai risposto) tiene le iniziali.
export function Faccia({ p, size = 36 }: { p: FacciaP; size?: number }) {
  const cifre = p.sg_id != null ? String(p.sg_id % 100).padStart(2, '0') : null
  return (
    <span
      title={sgid(p.sg_id, p) ?? undefined}
      className={`flex shrink-0 items-center justify-center rounded-full font-bold tabular-nums ${
        cifre ? tonoFase(p) : 'bg-velo text-navy'
      }`}
      style={{ width: size, height: size, fontSize: Math.round(size * 0.37) }}
    >
      {cifre ?? initials(p.name, p.company)}
    </span>
  )
}

// Il grafico a 12 barre delle analisi (G F M A M G L A S O N D, picco pieno).
// Stessa logica del renderer dei PDF (render_doc_v2.py).
const MESI = ['G', 'F', 'M', 'A', 'M', 'G', 'L', 'A', 'S', 'O', 'N', 'D']

export function SeasonChart({ bars }: { bars: Market['bars'] }) {
  return (
    <div>
      <div className="flex h-14 items-end gap-[3px]">
        {bars.map(([v, hi], i) => (
          <div
            key={i}
            className={`flex-1 rounded-t-[2px] ${hi ? 'bg-navy' : 'bg-blu/25'}`}
            style={{ height: `${Math.max(v, 3)}%` }}
            title={`${MESI[i]}: ${v}%`}
          />
        ))}
      </div>
      <div className="mt-1 flex gap-[3px]">
        {MESI.map((m, i) => (
          <span key={i} className="flex-1 text-center text-[9px] text-spento">{m}</span>
        ))}
      </div>
    </div>
  )
}

export function fmtDate(d: string | null | undefined): string {
  if (!d) return '—'
  const date = new Date(d)
  if (isNaN(date.getTime())) return '—'
  return date.toLocaleDateString('it-IT', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function fmtDateShort(d: string | null | undefined): string {
  if (!d) return '—'
  const date = new Date(d)
  if (isNaN(date.getTime())) return '—'
  return date.toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })
}

export function fmtOra(d: string | null | undefined): string {
  if (!d) return ''
  const date = new Date(d)
  if (isNaN(date.getTime())) return ''
  return date.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
}

// separatore delle migliaia fatto a mano: il toLocaleString del browser
// headless puo' non avere l'italiano e mostrare 6270 invece di 6.270
export function fmtNum(n: number): string {
  return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

// L'ID permanente: SG-1481. Non cambia mai, per nessun motivo: ne' se il
// prospect diventa cliente, ne' se cambia nome o referente (Giacomo, 9/9:
// «l'ID non deve codificare informazioni che possono cambiare»). Lo stato lo
// dice l'etichetta di fase accanto. Il secondo parametro resta per le vecchie
// chiamate e non fa niente.
export function sgid(n: number | null | undefined, _p?: FacciaP | null): string | null {
  if (n == null) return null
  return 'SG-' + String(n)
}

export function giorni(n: number): string {
  return `${n} ${n === 1 ? 'giorno' : 'giorni'}`
}

export function daysAgo(d: string | null | undefined): number | null {
  if (!d) return null
  const t = new Date(d).getTime()
  if (isNaN(t)) return null
  return Math.floor((Date.now() - t) / 86400000)
}

export function initials(name: string | null, company: string | null): string {
  const s = (company || name || '?').trim()
  const parts = s.split(/\s+/)
  return ((parts[0]?.[0] ??'') + (parts[1]?.[0] ?? '')).toUpperCase() || '?'
}

// QUANDO CARICA (Dre, 16/9): Clara che lavora. Non il marchio che gira,
// che «e' orrendo da vedere»: la costellazione ha gia' il suo movimento,
// quello vero, che dice che sta succedendo qualcosa.
export function Spinner() {
  return (
    <div className="flex items-center justify-center py-12 text-navy">
      <ClaraLogo size={40} lavora />
    </div>
  )
}

// SCORRERE COL POLLICE (Dre, 16/9): «sul telefono quello che faranno
// principalmente sara' aggiungere task e fare check delle robe da fare,
// tutto deve essere actionable e a portata di mano». Quindi la riga si
// trascina: verso destra e' fatta, verso sinistra si sposta a domani.
// Sul computer non succede niente: reagisce solo al dito.
export function Scorri({ onDestra, onSinistra, destra = 'Fatta', sinistra = 'Domani', children }: {
  onDestra?: () => void
  onSinistra?: () => void
  destra?: string
  sinistra?: string
  children: React.ReactNode
}) {
  const [dx, setDx] = useState(0)
  const [tiro, setTiro] = useState(false)
  const partenza = useRef(0)
  // il dito e' piu' veloce di React: se il primo touchmove arriva prima che
  // lo stato si aggiorni, la riga non si muove. Quindi il «sto trascinando»
  // vive in un ref, e lo stato serve solo a togliere l'animazione
  const giu = useRef(false)
  const SOGLIA = 88

  return (
    <div className="relative overflow-hidden">
      {/* quello che succede se molli adesso: si vede mentre trascini */}
      {dx !== 0 && (
        <div className={`absolute inset-0 flex items-center px-4 text-[11px] font-bold uppercase tracking-[0.06em] text-white ${
          dx > 0 ? 'justify-start bg-green-600' : 'justify-end bg-amber-500'
        }`}>
          {dx > 0 ? destra : sinistra}
        </div>
      )}
      <div
        onTouchStart={(e) => { partenza.current = e.touches[0].clientX; giu.current = true; setTiro(true) }}
        onTouchMove={(e) => {
          if (!giu.current) return
          const d = e.touches[0].clientX - partenza.current
          if ((d > 0 && !onDestra) || (d < 0 && !onSinistra)) return
          setDx(Math.max(-140, Math.min(140, d)))
        }}
        onTouchEnd={() => {
          giu.current = false
          setTiro(false)
          if (dx > SOGLIA && onDestra) onDestra()
          else if (dx < -SOGLIA && onSinistra) onSinistra()
          setDx(0)
        }}
        style={{ transform: `translateX(${dx}px)` }}
        className={`relative bg-white ${tiro ? '' : 'transition-transform duration-200 ease-out'}`}
      >
        {children}
      </div>
    </div>
  )
}

// L'unica micro-etichetta maiuscola dell'app: stesso corpo, stesso tracking,
// stesso colore ovunque (In arrivo, colonne, titoli delle card)
export function Micro({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <span className={`shrink-0 text-[11px] font-bold uppercase tracking-[0.05em] text-spento ${className}`}>
      {children}
    </span>
  )
}

export function Empty({ text }: { text: string }) {
  return <div className="px-4 py-5 text-sm text-spento">{text}</div>
}

// Il contenitore standard: card bianca, bordo netto, angoli appena smussati
export function Card({ children, className = '', id }: { children: React.ReactNode; className?: string; id?: string }) {
  return (
    <div id={id} className={`overflow-hidden rounded-2xl border border-bordo bg-white ${className}`}>
      {children}
    </div>
  )
}

export function TitoloCard({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="mb-2.5 text-[11px] font-bold uppercase tracking-[0.05em] text-spento">
      {children}
    </h3>
  )
}

// Etichetta secca per i campi riempiti in automatico (niente emoji)
export function Auto() {
  return <span className="text-[10px] font-semibold uppercase text-spento" title="riempito in automatico">auto</span>
}

// Zona che accoglie i file trascinati: avvolge qualunque area e quando
// un file le passa sopra si illumina; al rilascio chiama onFile.
// Ignora i drag interni (le carte della bacheca): reagisce SOLO ai file.
export function ZonaFile({ onFile, messaggio = 'Lascia qui il file', className = '', children }: {
  onFile: (f: File) => void
  messaggio?: string
  className?: string
  children: React.ReactNode
}) {
  const [sopra, setSopra] = useState(false)
  const conta = useRef(0)
  const eFile = (e: React.DragEvent) => [...(e.dataTransfer?.types ?? [])].includes('Files')

  return (
    <div
      className="relative flex min-h-0 flex-1 flex-col"
      onDragEnter={(e) => {
        if (!eFile(e)) return
        conta.current += 1
        setSopra(true)
      }}
      onDragLeave={(e) => {
        if (!eFile(e)) return
        conta.current -= 1
        if (conta.current <= 0) { conta.current = 0; setSopra(false) }
      }}
      onDragOver={(e) => { if (eFile(e)) e.preventDefault() }}
      onDrop={(e) => {
        if (!eFile(e)) return
        e.preventDefault()
        conta.current = 0
        setSopra(false)
        const f = e.dataTransfer.files?.[0]
        if (f) onFile(f)
      }}
    >
      <div className={className}>{children}</div>
      {sopra && (
        <div className="pointer-events-none absolute inset-0 z-30 flex items-center justify-center rounded-2xl border-2 border-dashed border-navy bg-navy/5">
          <span className="rounded-full bg-blu px-4 py-2 text-sm font-bold text-white shadow-lg">
            {messaggio}
          </span>
        </div>
      )}
    </div>
  )
}

// una cella di foglio: si scrive dentro, si salva quando esci (blur o Invio).
// E' la cella del foglio di Giacomo: Progetti, Tutti, i preventivi.
export function Cella({ valore, tipo = 'text', su, className = '', placeholder }: {
  valore: string; tipo?: 'text' | 'date' | 'number'; su: (v: string) => void; className?: string; placeholder?: string
}) {
  const [v, setV] = useState(valore)
  const [attiva, setAttiva] = useState(false)      // vuota e non toccata: mostra «—», non «dd/mm/yyyy»
  const ultimo = useRef(valore)
  useEffect(() => { setV(valore); ultimo.current = valore }, [valore])
  function chiudi() { setAttiva(false); if (v !== ultimo.current) { ultimo.current = v; su(v) } }
  if (!v && !attiva) {
    return (
      <button
        type="button"
        onClick={() => setAttiva(true)}
        title={placeholder}
        className={`flex h-12 w-full items-center px-3 text-sm text-spento hover:text-tenue ${className.includes('text-right') ? 'justify-end' : ''}`}
      >
        —
      </button>
    )
  }
  return (
    <input
      type={tipo}
      value={v}
      autoFocus={attiva}
      onChange={(e) => setV(e.target.value)}
      onBlur={chiudi}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === 'Escape') (e.target as HTMLInputElement).blur() }}
      className={`h-12 w-full min-w-0 bg-transparent px-3 text-sm outline-none focus:bg-blu/5 ${className}`}
    />
  )
}
