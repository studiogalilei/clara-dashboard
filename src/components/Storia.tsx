import { useEffect, useRef, useState } from 'react'
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

  // IL THREAD (Dre, 25/9: «la storia è vuota e blanda, non si capisce l'ordine,
  // con più eventi diventa un casino»). Si legge come una chat: giorno per
  // giorno, loro a sinistra, noi a destra in blu, call e note in mezzo come
  // righe di sistema. Dal primo all'ultimo, e si apre gia' in fondo, sull'ultimo.
  const [recentiInAlto, setRecentiInAlto] = useState(false)
  const fondo = useRef<HTMLDivElement>(null)
  useEffect(() => { if (!recentiInAlto) fondo.current?.scrollIntoView({ block: 'end' }) }, [eventi.length, recentiInAlto])
  const lista = recentiInAlto ? [...eventi].reverse() : eventi
  const giorno = (iso: string) => new Date(iso.length === 10 ? `${iso}T12:00:00` : iso).toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })

  return (
    <div className="fixed inset-0 z-[60] flex flex-col bg-fondo">
      <header className="flex items-center gap-3 border-b border-bordo bg-white px-4 py-3 lg:px-8">
        <button onClick={onChiudi} className="rounded-full px-3 py-1.5 text-sm font-semibold text-tenue hover:bg-velo">‹ Torna</button>
        <h1 className="min-w-0 truncate text-[17px] font-extrabold">{nome}</h1>
        <Micro className="ml-1 shrink-0">{eventi.length} {eventi.length === 1 ? 'evento' : 'eventi'}</Micro>
        <button onClick={() => setRecentiInAlto(!recentiInAlto)} className="ml-auto shrink-0 rounded-full border border-bordo px-3 py-1 text-[11px] font-semibold text-tenue hover:border-navy hover:text-navy">
          {recentiInAlto ? 'Dal primo all\'ultimo' : 'Più recenti in alto'}
        </button>
      </header>
      <div className="mx-auto w-full max-w-3xl flex-1 overflow-y-auto px-4 py-5 lg:px-8">
        {(prossimoPasso.cosa || prossimoPasso.quando) && (
          <Card className="mb-4 border-l-4 border-l-navy px-5 py-3">
            <Micro>Prossimo passo</Micro>
            <p className="mt-0.5 text-sm font-semibold">
              {prossimoPasso.cosa ?? 'Da decidere'}{prossimoPasso.quando ? `, ${fmtDate(prossimoPasso.quando)}` : ''}
            </p>
          </Card>
        )}
        {eventi.length === 0 && <p className="text-sm text-spento">Nessun evento ancora.</p>}
        <div className="space-y-2.5">
          {lista.map((e, i) => {
            const nuovoGiorno = i === 0 || giorno(lista[i - 1].at) !== giorno(e.at)
            return (
              <div key={e.chiave}>
                {nuovoGiorno && (
                  <p className="my-4 flex items-center gap-3 text-[11px] font-bold uppercase tracking-[0.06em] text-spento">
                    <span className="h-px flex-1 bg-bordo" />{giorno(e.at)}<span className="h-px flex-1 bg-bordo" />
                  </p>
                )}
                <Bolla tipo={e.tipo} at={e.at} testo={e.testo} />
              </div>
            )
          })}
        </div>
        <div ref={fondo} />
      </div>
    </div>
  )
}

// una bolla del thread: loro a sinistra, noi a destra, il resto in mezzo
function Bolla({ tipo, at, testo }: { tipo: string; at: string; testo: string }) {
  const [tutto, setTutto] = useState(false)
  const loro = tipo === 'email_in'
  const noi = tipo === 'email_out' || tipo === 'analisi' || tipo === 'followup'
  const call = tipo === 'call' || tipo === 'transcript'
  const eti = tipo === 'email_in' ? 'Loro' : tipo === 'email_out' ? 'Noi' : tipo === 'analisi' ? 'Noi, con l\'analisi' : tipo === 'followup' ? 'Noi, follow-up'
    : tipo === 'call' ? 'Call' : tipo === 'transcript' ? 'Call, gli appunti' : tipo === 'agenda' ? 'In calendario' : tipo === 'task' ? 'Task' : tipo === 'task_fatta' ? 'Task fatta' : 'Nota'
  const ora = at.length > 10 ? fmtOra(at) : ''
  if (!loro && !noi && !call) {
    // note, task, calendario: una riga in mezzo, senza scatola
    return (
      <p className="mx-auto max-w-[90%] text-center text-[12px] leading-snug text-tenue">
        <span className="font-semibold text-spento">{eti}{ora ? `, ${ora}` : ''}:</span> {unaRiga(testo, 160)}
      </p>
    )
  }
  const righe = testo.split('\n')
  const oggetto = (loro || noi) && righe.length > 1 && righe[0].length < 120 ? righe[0] : ''
  const corpo = oggetto ? righe.slice(1).join('\n').trim() : testo.trim()
  const lungo = corpo.length > 520 || corpo.split('\n').length > 8
  return (
    <div className={`flex ${noi ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[88%] rounded-2xl px-4 py-2.5 text-[13.5px] leading-snug ${
        noi ? 'rounded-br-md bg-blu text-white' : loro ? 'rounded-bl-md border border-bordo bg-white' : 'w-full border border-navy/30 bg-white'}`}>
        <p className={`mb-1 flex items-baseline gap-2 text-[10.5px] font-bold uppercase tracking-[0.05em] ${noi ? 'text-white/70' : loro ? 'text-green-700' : 'text-navy'}`}>
          {eti}{ora ? <span className="font-normal normal-case tracking-normal opacity-80">{ora}</span> : null}
        </p>
        {oggetto && <p className="mb-1 font-semibold">{oggetto}</p>}
        <p className={`whitespace-pre-wrap ${!tutto && lungo ? 'line-clamp-[8]' : ''}`}>{corpo}</p>
        {lungo && (
          <button onClick={() => setTutto(!tutto)} className={`mt-1 text-[11px] font-bold ${noi ? 'text-white/80' : 'text-blu'} hover:underline`}>
            {tutto ? 'chiudi' : 'leggi tutto'}
          </button>
        )}
      </div>
    </div>
  )
}
