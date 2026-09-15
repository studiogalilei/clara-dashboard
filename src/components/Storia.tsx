import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import type { Interaction, AgendaItem } from '../lib/types'
import { Card, Micro, Spinner, fmtDate, fmtDateShort, fmtOra } from './ui'

// LA STORIA DI UNA PERSONA, in due tagli (Dre, 7/9).
//
// Il primo e' la timeline riassuntiva dentro la scheda: le tappe che contano,
// una riga ciascuna, da capire a colpo d'occhio. Il secondo e' la storia
// intera, che si apre con un bottone: ogni mail per esteso, le call con la
// data e il transcript, le note, le task, il prossimo passo. Prima c'era un
// elenco solo, che era troppo per un colpo d'occhio e troppo poco per
// capire davvero.

// una tappa della timeline: cosa, quando, e il colore che dice il tipo
interface Tappa {
  chiave: string
  at: string
  titolo: string
  sotto?: string
  tono: 'in' | 'out' | 'call' | 'fase' | 'nota'
}

const TONO: Record<Tappa['tono'], string> = {
  in: 'bg-green-600',      // lui ha scritto
  out: 'bg-blu',           // noi abbiamo mandato
  call: 'bg-navy',         // ci siamo parlati
  fase: 'bg-amber-400',    // e' cambiato di fase
  nota: 'bg-gray-300',     // un appunto nostro
}

function unaRiga(s: string | null | undefined, max = 90): string {
  const t = (s ?? '').replace(/\s+/g, ' ').trim()
  return t.length > max ? t.slice(0, max - 1) + '…' : t
}

// le tappe da interazioni + agenda, in ordine di tempo
function tappe(timeline: Interaction[], agenda: AgendaItem[]): Tappa[] {
  const out: Tappa[] = []
  const primaRisposta = timeline.find((t) => t.kind === 'email_in')
  for (const t of timeline) {
    if (t.kind === 'postit' || t.kind === 'prep') continue
    const fase = /^\[(.+?)\]/.exec(t.body ?? '')
    if (t.kind === 'email_in') {
      out.push({ chiave: t.id, at: t.at, tono: 'in',
        titolo: t.id === primaRisposta?.id ? 'Ha risposto: diventa prospect' : 'Ha scritto',
        sotto: unaRiga(t.body) })
    } else if (t.kind === 'email_out' || t.kind === 'analisi' || t.kind === 'followup') {
      out.push({ chiave: t.id, at: t.at, tono: 'out',
        titolo: t.kind === 'analisi' ? 'Analisi inviata' : t.kind === 'followup' ? 'Follow-up' : 'Gli abbiamo scritto',
        sotto: unaRiga(t.body) })
    } else if (t.kind === 'call' || t.kind === 'transcript') {
      out.push({ chiave: t.id, at: t.at, tono: 'call',
        titolo: t.kind === 'transcript' ? 'Call fatta, col transcript' : 'Call',
        sotto: unaRiga(t.body) })
    } else if (t.kind === 'nota' && fase) {
      out.push({ chiave: t.id, at: t.at, tono: 'fase', titolo: fase[1], sotto: unaRiga((t.body ?? '').replace(/^\[.+?\]\s*/, '')) })
    } else if (t.kind === 'nota') {
      out.push({ chiave: t.id, at: t.at, tono: 'nota', titolo: 'Nota', sotto: unaRiga(t.body) })
    }
  }
  for (const a of agenda) {
    out.push({ chiave: `ag-${a.id}`, at: a.at, tono: 'call',
      titolo: a.at > new Date().toISOString() ? `Prossima: ${a.titolo}` : a.titolo,
      sotto: fmtOra(a.at) })
  }
  return out.sort((x, y) => x.at.localeCompare(y.at))
}

// le tappe che meritano il colpo d'occhio: la prima risposta, ogni cambio di
// fase, ogni call, l'analisi, e le ultime due cose successe
function riassunto(tutte: Tappa[], max = 8): Tappa[] {
  if (tutte.length <= max) return tutte
  const scelte = new Set<string>()
  const prima = tutte.find((t) => t.tono === 'in')
  if (prima) scelte.add(prima.chiave)
  for (const t of tutte) if (t.tono === 'fase' || t.tono === 'call' || t.titolo === 'Analisi inviata') scelte.add(t.chiave)
  for (const t of tutte.slice(-2)) scelte.add(t.chiave)
  let fuori = tutte.filter((t) => scelte.has(t.chiave))
  if (fuori.length > max) fuori = [fuori[0], ...fuori.slice(-(max - 1))]
  return fuori
}

export function Timeline({ timeline, agenda, onTutta }: {
  timeline: Interaction[] | null
  agenda: AgendaItem[]
  onTutta: () => void
}) {
  if (timeline === null) return <Spinner />
  const tutte = tappe(timeline, agenda)
  const poche = riassunto(tutte)
  if (tutte.length === 0) return <p className="text-sm text-spento">Nessun evento ancora.</p>
  return (
    <div>
      <ol className="relative ml-1.5 border-l-2 border-velo">
        {poche.map((t) => (
          <li key={t.chiave} className="relative pb-3 pl-4 last:pb-0">
            <span className={`absolute -left-[7px] top-1.5 h-3 w-3 rounded-full ring-4 ring-white ${TONO[t.tono]}`} />
            <p className="flex flex-wrap items-baseline gap-x-2">
              <span className="text-[11px] tabular-nums text-spento">{fmtDateShort(t.at)}</span>
              <span className="text-sm font-semibold">{t.titolo}</span>
            </p>
            {t.sotto && <p className="truncate text-xs text-tenue">{t.sotto}</p>}
          </li>
        ))}
      </ol>
      <button
        onClick={onTutta}
        className="mt-3 w-full rounded-full border border-bordo py-1.5 text-xs font-bold text-navy hover:border-navy"
      >
        Visualizza tutta la storia{tutte.length > poche.length ? `, ${tutte.length} eventi` : ''}
      </button>
    </div>
  )
}

// la storia intera: tutto, per esteso, dal primo giorno a oggi
export function StoriaCompleta({ prospectId, nome, timeline, agenda, prossimoPasso, onChiudi }: {
  prospectId: string
  nome: string
  timeline: Interaction[]
  agenda: AgendaItem[]
  prossimoPasso: { cosa: string | null; quando: string | null }
  onChiudi: () => void
}) {
  const [task, setTask] = useState<Array<{ id: number; titolo: string; fatta: boolean; scadenza: string | null }>>([])
  useEffect(() => {
    supabase.from('task').select('id,titolo,fatta,scadenza').eq('prospect_id', prospectId)
      .order('at', { ascending: true }).limit(50)
      .then(({ data }) => setTask((data as typeof task) ?? []))
  }, [prospectId])
  useEffect(() => {
    function esc(e: KeyboardEvent) { if (e.key === 'Escape') onChiudi() }
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [onChiudi])

  const eventi = [
    ...timeline.filter((t) => t.kind !== 'postit' && t.kind !== 'prep')
      .map((t) => ({ chiave: t.id, at: t.at, tipo: t.kind as string, testo: t.body ?? '' })),
    ...agenda.map((a) => ({ chiave: `ag-${a.id}`, at: a.at, tipo: 'agenda', testo: `${a.titolo}${a.tipo ? `, ${a.tipo}` : ''}` })),
    ...task.map((t) => ({ chiave: `task-${t.id}`, at: t.scadenza ?? '', tipo: t.fatta ? 'task_fatta' : 'task', testo: t.titolo })),
  ].filter((e) => e.at).sort((x, y) => x.at.localeCompare(y.at))

  const ETI: Record<string, [string, string]> = {
    email_in: ['Ha scritto', 'text-green-700'], email_out: ['Gli abbiamo scritto', 'text-blu'],
    analisi: ['Analisi inviata', 'text-blu'], followup: ['Follow-up', 'text-blu'],
    call: ['Call', 'text-navy'], transcript: ['Transcript della call', 'text-navy'],
    nota: ['Nota', 'text-tenue'], agenda: ['In calendario', 'text-navy'],
    task: ['Task', 'text-tenue'], task_fatta: ['Task fatta', 'text-spento'],
  }

  return (
    <div className="fixed inset-0 z-[60] flex flex-col bg-fondo">
      <header className="flex items-center gap-3 border-b border-bordo bg-white px-4 py-3 lg:px-8">
        <button onClick={onChiudi} className="rounded-full px-3 py-1.5 text-sm font-semibold text-tenue hover:bg-velo">‹ Torna</button>
        <h1 className="text-[17px] font-extrabold">{nome}</h1>
        <Micro className="ml-1">tutta la storia, {eventi.length} eventi</Micro>
      </header>
      <div className="mx-auto w-full max-w-3xl flex-1 space-y-3 overflow-y-auto px-4 py-5 lg:px-8">
        {(prossimoPasso.cosa || prossimoPasso.quando) && (
          <Card className="border-l-4 border-l-navy px-5 py-3">
            <Micro>Prossimo passo</Micro>
            <p className="mt-0.5 text-sm font-semibold">
              {prossimoPasso.cosa ?? 'Da decidere'}{prossimoPasso.quando ? `, ${fmtDate(prossimoPasso.quando)}` : ''}
            </p>
          </Card>
        )}
        {eventi.length === 0 && <p className="text-sm text-spento">Nessun evento ancora.</p>}
        {eventi.map((e) => {
          const [eti, colore] = ETI[e.tipo] ?? [e.tipo, 'text-tenue']
          const lungo = e.tipo === 'transcript'
          return (
            <Card key={e.chiave} className="px-5 py-3.5">
              <p className="flex items-baseline gap-2">
                <span className="text-[11px] tabular-nums text-spento">{fmtDate(e.at)}{e.tipo === 'agenda' ? `, ${fmtOra(e.at)}` : ''}</span>
                <span className={`text-xs font-bold uppercase tracking-[0.05em] ${colore}`}>{eti}</span>
              </p>
              {e.testo && (lungo
                ? <details className="mt-1.5"><summary className="cursor-pointer text-sm font-semibold text-navy">{unaRiga(e.testo, 120)}</summary><p className="mt-2 whitespace-pre-wrap text-sm text-tenue">{e.testo}</p></details>
                : <p className="mt-1 whitespace-pre-wrap text-sm">{e.testo}</p>)}
            </Card>
          )
        })}
      </div>
    </div>
  )
}
