import { useRef, useState } from 'react'
import {
  STAGE_LABEL, CLS_LABEL, PIPELINE_LABEL,
  type Stage, type Classificazione, type PipelineStage, type Market, type Prospect,
} from '../lib/types'

// Etichette sobrie: bordo, quadrate, niente colori accesi.
// Il colore vero lo portano solo i pallini di stato.
function Eti({ testo, tono }: { testo: string; tono?: 'verde' | 'ambra' | 'rosso' }) {
  const c =
    tono === 'verde' ? 'bg-green-50 text-green-800 border-transparent'
    : tono === 'ambra' ? 'bg-amber-50 text-amber-800 border-transparent'
    : tono === 'rosso' ? 'bg-red-50 text-red-700 border-transparent'
    : 'bg-velo text-tenue border-bordo'
  return (
    <span className={`inline-block whitespace-nowrap rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${c}`}>
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
type FacciaP = Pick<Prospect, 'sg_id' | 'name' | 'company' | 'fuori' | 'stage' | 'pipeline_stage'>

export function tonoFase(p: Pick<FacciaP, 'fuori' | 'stage' | 'pipeline_stage'>): string {
  const perso = (p.fuori && p.pipeline_stage === 'perso') || (!p.fuori && p.stage === 'perso')
  const cliente = (p.fuori && p.pipeline_stage === 'cliente') || (!p.fuori && p.stage === 'cliente')
  if (perso) return 'bg-gray-200 text-gray-500'
  if (cliente) return 'bg-green-600 text-white'
  if (p.fuori) {
    if (p.pipeline_stage === 'tecnica') return 'bg-blu text-white'
    if (p.pipeline_stage === 'avvio') return 'bg-navy text-white'
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

export function Spinner() {
  return <div className="py-10 text-center text-sm text-spento">Caricamento…</div>
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
    <div id={id} className={`overflow-hidden rounded-2xl border border-bordo bg-white shadow-[0_1px_2px_rgba(16,24,40,0.03),0_4px_16px_rgba(16,24,40,0.04)] ${className}`}>
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
          <span className="rounded-full bg-navy px-4 py-2 text-sm font-bold text-white shadow-lg">
            {messaggio}
          </span>
        </div>
      )}
    </div>
  )
}
