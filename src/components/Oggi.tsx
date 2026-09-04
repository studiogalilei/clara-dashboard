import { Fragment, useCallback, useEffect, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'
import { leggi as leggiPref, scrivi as scriviPref } from '../lib/preferenze'
import type { Classificazione } from '../lib/types'
import Radar from './Radar'
import { Card, Spinner, giorni, fmtDateShort, sgid } from './ui'
import { oggi, giorno, codaDiOggi, creaTask, type VoceCoda } from '../lib/regole'

// La sezione Task, ricalcata su Google Tasks (Dre, 31/8): cerchietti,
// «Aggiungi un'attività», note sotto il titolo, trascina per riordinare,
// Completate in fondo. La coda generata dai dati non fa dieci task
// fotocopia: UN titolo («Rispondere ai lead») e i nomi come sottopunti.

// Le due viste (Dre, 3/9). «On go» e' la scatola pulita dall'alto in basso,
// quella del telefono, dove butti dentro una cosa in tre secondi. «Week
// picture» e' la settimana intera davanti, senza scorrere. Stesse task
// sotto: cambia solo come le guardi.
type Vista = 'ongo' | 'big'

function leggiVista(): Vista {
  return (leggiPref('task-vista') as Vista) || 'ongo'
}

const GIORNI_IT = ['lunedì', 'martedì', 'mercoledì', 'giovedì', 'venerdì', 'sabato', 'domenica']

// I colori sono facoltativi (Dre, 3/9): di default una task e' bianca come
// tutto il resto. Chi vuole marcarne qualcuna se la colora, ma tinte tenui:
// il foglio di Giacomo piace perche' e' pulito, non perche' e' colorato.
const COLORI: Array<[string, string, string]> = [
  // [chiave, tinta della riga, pallino nel selettore]
  ['giallo', 'bg-amber-50', 'bg-amber-300'],
  ['verde',  'bg-green-50', 'bg-green-400'],
  ['blu',    'bg-blue-50',  'bg-blue-400'],
  ['viola',  'bg-violet-50', 'bg-violet-400'],
  ['rosa',   'bg-pink-50',  'bg-pink-300'],
  ['grigio', 'bg-gray-100', 'bg-gray-400'],
]
// la tinta della riga: bianca se nessuno l'ha voluta colorata
const tinta = (c: string | null) => COLORI.find(([k]) => k === c)?.[1] ?? ''

// il lunedi' della settimana di una data
function lunediDi(d: Date): Date {
  const x = new Date(d)
  x.setDate(x.getDate() - ((x.getDay() + 6) % 7))
  x.setHours(0, 0, 0, 0)
  return x
}

const RANGO: Partial<Record<Classificazione, number>> = {
  positivo: 0, da_classificare: 1, tiepido: 2, rinvio: 3, ooo: 4,
}

interface TaskDre {
  id: number
  at: string
  titolo: string
  dettagli: string | null
  scadenza: string | null
  ordine: number
  colore: string | null
  fatta: boolean
  fatta_il: string | null
  owner: string | null       // di chi e'
  da: string | null          // chi l'ha mandata
  stato: 'proposta' | 'accettata' | 'rimandata' | 'fatta'
  motivo: string | null
}

interface Persona { id: string; nome: string | null }

interface Sotto {
  chiave: string
  nome: string
  nota: string
  prospect_id: string
  sg: string | null
}

interface Gruppo {
  chiave: string
  titolo: string
  sotto: Sotto[]
}

interface Props {
  onOpen: (id: string) => void
}

const OGGI_CHIAVE = () => `task-fatte-${oggi()}`
function leggiFatte(): Set<string> {
  try { return new Set(JSON.parse(localStorage.getItem(OGGI_CHIAVE()) ?? '[]')) } catch { return new Set() }
}
function salvaFatte(f: Set<string>) {
  try { localStorage.setItem(OGGI_CHIAVE(), JSON.stringify([...f])) } catch { /* niente */ }
}

function Cerchio({ fatta, mezzo, onClick }: { fatta: boolean; mezzo?: boolean; onClick: () => void }) {
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onClick() }}
      aria-label={fatta ? 'Segna da fare' : 'Completa'}
      className="group/c mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center"
    >
      {fatta ? (
        <svg viewBox="0 0 24 24" className="h-[22px] w-[22px] text-blu">
          <path fill="currentColor" d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z" />
        </svg>
      ) : (
        <span className={`flex h-[18px] w-[18px] items-center justify-center rounded-full border-2 transition-colors ${
          mezzo ? 'border-blu' : 'border-spento group-hover/c:border-tenue'
        }`}>
          <svg viewBox="0 0 24 24" className="h-3 w-3 text-tenue opacity-0 transition-opacity group-hover/c:opacity-100">
            <path fill="currentColor" d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z" />
          </svg>
        </span>
      )}
    </button>
  )
}

export default function Oggi({ onOpen }: Props) {
  const [attivita, setAttivita] = useState<TaskDre[] | null>(null)
  const [gruppi, setGruppi] = useState<Gruppo[] | null>(null)
  const [fatteCoda, setFatteCoda] = useState<Set<string>>(leggiFatte)
  const [spuntando, setSpuntando] = useState<string | null>(null)
  const [aggiungo, setAggiungo] = useState(false)
  const [nuovo, setNuovo] = useState('')
  const [nuovaData, setNuovaData] = useState('')
  const [apertaTask, setApertaTask] = useState<number | null>(null)
  const [completateAperte, setCompletateAperte] = useState(false)
  const [trascino, setTrascino] = useState<number | null>(null)
  const [sopraDi, setSopraDi] = useState<number | null>(null)
  const nuovoRef = useRef<HTMLInputElement>(null)
  const [problema, setProblema] = useState('')
  const [vista, setVista] = useState<Vista>(leggiVista)
  const [settimana, setSettimana] = useState(0)          // 0 = questa
  const [aggiungoIn, setAggiungoIn] = useState<string | null>(null)
  const [nuovoIn, setNuovoIn] = useState('')
  const [sopraGiorno, setSopraGiorno] = useState<string | null>(null)
  // le task hanno un proprietario e un mittente (Dre, 3/9)
  const [io, setIo] = useState<string | null>(null)
  const [persone, setPersone] = useState<Persona[]>([])
  const [perChi, setPerChi] = useState<string>('')      // '' = per me
  const [mandate, setMandate] = useState<TaskDre[]>([])
  const [tavolozza, setTavolozza] = useState<number | null>(null)

  const [stretto, setStretto] = useState(false)
  useEffect(() => {
    try {
      const m = window.matchMedia('(max-width: 640px)')
      setStretto(m.matches)
      const su = (e: MediaQueryListEvent) => setStretto(e.matches)
      m.addEventListener('change', su)
      return () => m.removeEventListener('change', su)
    } catch { /* niente */ }
  }, [])
  const vistaVera: Vista = stretto ? 'ongo' : vista

  function cambiaVista(v: Vista) {
    setVista(v)
    scriviPref('task-vista', v)
  }

  const caricaTask = useCallback(() => {
    // le mie: quelle mie e quelle vecchie senza proprietario. Chiedere «di
    // chi sono» al database e non al browser: se no, con due persone, le 200
    // righe se le prendeva chi ne aveva scritte di piu' (revisione 4/9)
    const mie = io ? `owner.is.null,owner.eq.${io}` : 'owner.is.null'
    supabase.from('task').select('*').or(mie)
      .order('ordine', { ascending: true }).limit(200)
      .then(({ data }) => setAttivita((data as TaskDre[]) ?? []))
    // quelle che ho mandato io a un altro: e' una lista sua, non mia,
    // ma voglio sapere se l'ha presa
    if (io) {
      supabase.from('task').select('*').eq('da', io).neq('owner', io)
        .order('ordine', { ascending: true }).limit(100)
        .then(({ data }) => setMandate((data as TaskDre[]) ?? []))
    } else setMandate([])
  }, [io])

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setIo(data.session?.user?.id ?? null))
    supabase.from('profili').select('id,nome').order('nome', { ascending: true }).limit(20)
      .then(({ data }) => setPersone((data as Persona[]) ?? []))
  }, [])

  const nomeDi = (id: string | null) =>
    persone.find((p) => p.id === id)?.nome ?? 'qualcuno'

  // una task che arriva non entra nella lista finche' non la accetti
  async function rispondiAllaProposta(t: TaskDre, accetto: boolean, motivo?: string) {
    await supabase.from('task')
      .update(accetto ? { stato: 'accettata' } : { stato: 'rimandata', motivo: motivo ?? null })
      .eq('id', t.id).select().single()
    caricaTask()
  }

  useEffect(() => {
    caricaTask()

    // la coda la definisce regole.ts, per tutti: qui si decide solo come
    // si chiamano i gruppi e cosa c'e' scritto sotto ogni nome
    codaDiOggi().then(({ voci }) => {
      const caldo = (a: VoceCoda, b: VoceCoda) =>
        (RANGO[a.p.classificazione ?? 'da_classificare'] ?? 5) - (RANGO[b.p.classificazione ?? 'da_classificare'] ?? 5)
      const nota = (v: VoceCoda): string => {
        if (v.ragione === 'rispondi') return `ha scritto lui il ${fmtDateShort(v.data)}`
        if (v.ragione === 'followup') return v.fermoDa !== null ? `silenzio da ${giorni(v.fermoDa)}` : `dovuto dal ${fmtDateShort(v.data)}`
        if (v.ragione === 'ricontatto') return v.p.next_action ?? 'la data è arrivata'
        return `rientrato il ${fmtDateShort(v.data)}`
      }
      const sotto = (v: VoceCoda): Sotto => ({
        chiave: `coda-${v.p.id}`, nome: v.p.company || v.p.name || v.p.email,
        nota: nota(v), prospect_id: v.p.id, sg: sgid(v.p.sg_id),
      })
      const gruppo = (r: VoceCoda['ragione'], titolo: string, ordina?: (a: VoceCoda, b: VoceCoda) => number) => {
        const sue = voci.filter((v) => v.ragione === r)
        if (ordina) sue.sort(ordina)
        return sue.length ? [{ chiave: r, titolo, sotto: sue.map(sotto) }] : []
      }
      setGruppi([
        ...gruppo('rispondi', 'Rispondere ai lead', caldo),
        ...gruppo('followup', 'Mandare i follow-up', (a, b) => (b.fermoDa ?? 0) - (a.fermoDa ?? 0)),
        ...gruppo('ricontatto', 'Ricontatti in scadenza'),
        ...gruppo('rientro', 'Rientrati dalle ferie'),
      ])
    })
  }, [caricaTask])

  if (attivita === null || gruppi === null) return <Spinner />

  const proposte = attivita.filter((t) => t.stato === 'proposta' && !t.fatta)
  const mieDaFare = attivita.filter((t) => !t.fatta && t.stato !== 'proposta')
  const gruppiVivi = gruppi
    .map((g) => ({ ...g, sotto: g.sotto.filter((s) => !fatteCoda.has(s.chiave)) }))
    .filter((g) => g.sotto.length > 0)
  const completate: Array<{ chiave: string; titolo: string; taskId: number | null }> = [
    ...attivita.filter((t) => t.fatta).map((t) => ({ chiave: `dre-${t.id}`, titolo: t.titolo, taskId: t.id })),
    ...gruppi.flatMap((g) => g.sotto.filter((s) => fatteCoda.has(s.chiave))
      .map((s) => ({ chiave: s.chiave, titolo: s.nome, taskId: null }))),
  ]

  function spuntaCoda(chiavi: string[]) {
    setSpuntando(chiavi[0])
    setTimeout(() => {
      setSpuntando(null)
      const nuove = new Set(fatteCoda)
      chiavi.forEach((c) => nuove.add(c))
      setFatteCoda(nuove)
      salvaFatte(nuove)
    }, 380)
  }

  async function spuntaMia(t: TaskDre) {
    setSpuntando(`dre-${t.id}`)
    setTimeout(async () => {
      setSpuntando(null)
      const { data } = await supabase.from('task')
        .update({ fatta: true, fatta_il: new Date().toISOString() })
        .eq('id', t.id).select().single()
      if (data) setAttivita((a) => a!.map((x) => (x.id === t.id ? (data as TaskDre) : x)))
    }, 380)
  }

  async function ripristina(c: { chiave: string; taskId: number | null }) {
    if (c.taskId !== null) {
      const { data } = await supabase.from('task')
        .update({ fatta: false, fatta_il: null }).eq('id', c.taskId).select().single()
      if (data) setAttivita((a) => a!.map((x) => (x.id === c.taskId ? (data as TaskDre) : x)))
    } else {
      const nuove = new Set(fatteCoda)
      nuove.delete(c.chiave)
      setFatteCoda(nuove)
      salvaFatte(nuove)
    }
  }

  // se il database rifiuta, lo schermo non deve mostrare il valore nuovo:
  // prima restava scritto e nessuno se ne accorgeva (revisione 4/9)
  async function aggiorna(id: number, patch: Partial<TaskDre>) {
    const { data } = await supabase.from('task').update(patch).eq('id', id).select().single()
    if (!data) {
      setProblema('Non sono riuscito a salvare: rimetto quello che c\'è nel database.')
      caricaTask()
      return
    }
    setAttivita((a) => a!.map((t) => (t.id === id ? (data as TaskDre) : t)))
  }

  async function aggiungi() {
    const titolo = nuovo.trim()
    if (!titolo) { setAggiungo(false); return }
    const altrui = Boolean(perChi && perChi !== io)
    const { task, problema: guaio } = await creaTask({
      titolo,
      scadenza: nuovaData || null,
      perChi,
      ordine: Math.min(0, ...attivita!.map((t) => t.ordine)) - 1,
    })
    if (guaio) { setProblema('La task non è stata salvata: ' + guaio); return }
    if (task && !altrui) setAttivita((a) => [task as TaskDre, ...(a ?? [])])
    if (task && altrui) setMandate((m) => [task as TaskDre, ...m])
    setNuovo('')
    setNuovaData('')
    setPerChi('')
    nuovoRef.current?.focus()
  }

  // trascina per riordinare (le mie attivita')
  async function lascia(su: TaskDre) {
    const daId = trascino
    setTrascino(null)
    setSopraDi(null)
    if (daId === null || daId === su.id) return
    const vive = mieDaFare.slice()
    const da = vive.findIndex((t) => t.id === daId)
    const a = vive.findIndex((t) => t.id === su.id)
    if (da < 0 || a < 0) return
    const [mossa] = vive.splice(da, 1)
    // dopo la rimozione gli indici a valle scalano di uno: senza questa
    // correzione la task finiva una riga piu' giu' di dove diceva la linea
    vive.splice(da < a ? a - 1 : a, 0, mossa)
    // si riscrive l'ordine 0..n
    setAttivita((att) => {
      const mappa = new Map(vive.map((t, i) => [t.id, i]))
      return att!.map((t) => (mappa.has(t.id) ? { ...t, ordine: mappa.get(t.id)! } : t))
        .sort((x, y) => x.ordine - y.ordine)
    })
    // si riscrivono solo le righe che cambiano davvero, e si controlla:
    // prima l'ordine a schermo poteva non essere quello sul database
    const cambiate = vive.map((t, i) => ({ id: t.id, i })).filter(({ id, i }) => {
      const prima = attivita!.find((t) => t.id === id)
      return prima?.ordine !== i
    })
    const esiti = await Promise.all(cambiate.map(({ id, i }) =>
      supabase.from('task').update({ ordine: i }).eq('id', id).select().single()))
    if (esiti.some((e) => !e.data)) {
      setProblema('Il nuovo ordine non è stato salvato: rimetto quello del database.')
      caricaTask()
    }
  }

  // ── WEEK PICTURE: la settimana davanti, senza scorrere ───────────
  async function spostaA(id: number, quando: string | null) {
    setSopraGiorno(null)
    await aggiorna(id, { scadenza: quando })
  }

  async function aggiungiIn(quando: string | null) {
    const t = nuovoIn.trim()
    if (!t) { setAggiungoIn(null); return }
    const min = Math.min(0, ...(attivita ?? []).map((x) => x.ordine))
    const { data } = await supabase.from('task')
      .insert({ titolo: t, scadenza: quando, fatta: false, ordine: min - 1, owner: io, da: io })
      .select().single()
    if (data) setAttivita((a) => [data as TaskDre, ...(a ?? [])])
    setNuovoIn('')
    setAggiungoIn(null)
  }

  function bigPicture() {
    const inizio = lunediDi(new Date())
    inizio.setDate(inizio.getDate() + settimana * 7)
    const giorni = Array.from({ length: 7 }, (_, i) => {
      const d = new Date(inizio); d.setDate(d.getDate() + i)
      return { iso: giorno(d), nome: GIORNI_IT[i], numero: d.getDate() }
    })
    const vive = (attivita ?? []).filter((t) => !t.fatta)
    // niente colonne appese ai lati: il blocco comincia lunedi' e finisce
    // domenica (Dre, 3/9). Le task senza data vivono in On go.
    const colonne = giorni.map((g) => ({
      chiave: g.iso, titolo: g.nome, sotto: String(g.numero), iso: g.iso as string | null,
      task: vive.filter((t) => t.scadenza === g.iso), oggi: g.iso === oggi(),
    }))

    const RIGHE = Math.max(14, ...colonne.map((c) => c.task.length + 2))
    const righe = Array.from({ length: RIGHE }, (_, i) => i)

    return (
      // a tutta larghezza: una settimana dentro un contenitore stretto
      // costringe a scorrere, che e' esattamente quello che non si vuole
      <div className="-mx-4 lg:-mx-8">
        <div className="overflow-x-auto rounded-lg border border-bordo bg-white">
          <div className="grid min-w-[1000px]"
               style={{ gridTemplateColumns: 'repeat(7, minmax(140px,1fr))' }}>

            {/* la testata: i giorni, grossi, come nel foglio */}
            {colonne.map((c) => (
              <div
                key={`t-${c.chiave}`}
                className={`border-b border-bordo px-2.5 py-1.5 last:border-r-0 [&:not(:last-child)]:border-r ${
                  c.oggi ? 'bg-navy text-white' : 'bg-navy/10 text-navy'
                }`}
              >
                <span className="block truncate text-lg font-extrabold uppercase leading-tight tracking-tight">
                  {c.titolo}
                </span>
                <span className={`text-[11px] font-semibold ${c.oggi ? 'text-white/70' : 'text-navy/60'}`}>
                  {c.sotto}
                </span>
              </div>
            ))}

            {/* il reticolo: le celle ci sono anche quando sono vuote */}
            {righe.map((r) => (
              <Fragment key={`r-${r}`}>
                {colonne.map((c) => {
                  const t = c.task[r]
                  const chiaveCella = `${c.chiave}-${r}`
                  return (
                    <div
                      key={chiaveCella}
                      draggable={Boolean(t)}
                      onDragStart={(e) => { if (t) e.dataTransfer.setData('text/plain', String(t.id)) }}
                      onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; setSopraGiorno(c.chiave) }}
                      onDragLeave={() => setSopraGiorno(null)}
                      onDrop={(e) => {
                        e.preventDefault()
                        const id = Number(e.dataTransfer.getData('text/plain'))
                        if (id) spostaA(id, c.iso)
                      }}
                      className={`group relative flex min-h-[30px] min-w-0 items-start gap-1.5 border-b border-r border-bordo/70 px-1.5 py-1 ${
                        t ? 'cursor-grab active:cursor-grabbing' : ''
                      } ${tinta(t?.colore ?? null)} ${
                        sopraGiorno === c.chiave && !t ? 'bg-navy/5' : ''
                      }`}
                    >
                      {t ? (
                        <>
                          <Cerchio fatta={false} onClick={() => spuntaMia(t)} />
                          <span className="min-w-0 flex-1 truncate pt-0.5 text-[13px] leading-tight" title={t.titolo}>
                            {t.titolo}
                          </span>
                          <button
                            onClick={(e) => { e.stopPropagation(); setTavolozza(tavolozza === t.id ? null : t.id) }}
                            aria-label="Colore"
                            className={`mt-1 h-3 w-3 shrink-0 rounded-full border border-bordo transition-opacity ${
                              t.colore ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                            } ${COLORI.find(([k]) => k === t.colore)?.[2] ?? 'bg-white'}`}
                          />
                          {tavolozza === t.id && (
                            <div className="salta-su absolute right-1 top-6 z-20 flex gap-1 rounded-xl border border-bordo bg-white p-1.5 shadow-[0_8px_24px_rgba(16,24,40,0.16)]">
                              <button
                                onClick={() => { aggiorna(t.id, { colore: null }); setTavolozza(null) }}
                                aria-label="Nessun colore"
                                className="h-4 w-4 rounded-full border border-bordo bg-white"
                              />
                              {COLORI.map(([k, , pallino]) => (
                                <button key={k} onClick={() => { aggiorna(t.id, { colore: k }); setTavolozza(null) }}
                                  aria-label={k} className={`h-4 w-4 rounded-full ${pallino}`} />
                              ))}
                            </div>
                          )}
                        </>
                      ) : aggiungoIn === chiaveCella ? (
                        <input
                          autoFocus
                          value={nuovoIn}
                          onChange={(e) => setNuovoIn(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') aggiungiIn(c.iso)
                            if (e.key === 'Escape') { setAggiungoIn(null); setNuovoIn('') }
                          }}
                          onBlur={() => aggiungiIn(c.iso)}
                          className="w-full bg-transparent text-[13px] outline-none"
                        />
                      ) : (
                        <button
                          onClick={() => { setAggiungoIn(chiaveCella); setNuovoIn('') }}
                          aria-label="Scrivi qui"
                          className="absolute inset-0 hover:bg-velo/60"
                        />
                      )}
                    </div>
                  )
                })}
              </Fragment>
            ))}
          </div>
        </div>
      </div>
    )
  }

  const chipData = (scadenza: string | null) => scadenza && (
    <span className={`mt-1 inline-block rounded-full border px-2 py-px text-[11px] ${
      scadenza <= oggi()
        ? 'border-transparent bg-blu/10 font-semibold text-blu'
        : 'border-bordo text-tenue'
    }`}>
      {scadenza === oggi() ? 'Oggi' : fmtDateShort(scadenza)}
    </span>
  )

  return (
    <div className="space-y-4 pb-28 sm:pb-8">
      <div className="lg:hidden">
        <Radar onOpen={onOpen} />
      </div>

      {problema && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm font-semibold text-red-800">
          {problema}
        </p>
      )}

      {/* le due viste: stesse task, due modi di guardarle */}
      <div className="hidden items-center gap-2 sm:flex">
        <div className="flex overflow-hidden rounded-full border border-bordo bg-white">
          {(['ongo', 'big'] as const).map((v) => (
            <button
              key={v}
              onClick={() => cambiaVista(v)}
              className={`px-4 py-1.5 text-xs font-bold transition-colors ${
                vista === v ? 'bg-navy text-white' : 'text-tenue hover:bg-velo'
              }`}
            >
              {v === 'ongo' ? 'On go' : 'Week picture'}
            </button>
          ))}
        </div>
        {vistaVera === 'big' && (
          <div className="ml-auto flex items-center gap-1">
            <button onClick={() => setSettimana(settimana - 1)} aria-label="Settimana prima"
              className="rounded-full border border-bordo bg-white px-2.5 py-1 text-sm text-tenue hover:border-navy">‹</button>
            <button onClick={() => setSettimana(0)} disabled={settimana === 0}
              className="rounded-full border border-bordo bg-white px-3 py-1 text-xs font-semibold text-navy hover:border-navy disabled:border-transparent disabled:bg-transparent disabled:text-spento">
              {settimana === 0 ? 'questa settimana' : 'torna a oggi'}
            </button>
            <button onClick={() => setSettimana(settimana + 1)} aria-label="Settimana dopo"
              className="rounded-full border border-bordo bg-white px-2.5 py-1 text-sm text-tenue hover:border-navy">›</button>
          </div>
        )}
      </div>

      {/* quello che ti hanno mandato: sta sopra, e non entra nella tua coda
          finche' non lo accetti (Dre, 3/9) */}
      {proposte.length > 0 && (
        <Card className="border-blu/30">
          <header className="border-b border-velo bg-blu/5 px-4 py-2.5">
            <p className="text-sm font-bold text-navy">
              {proposte.length === 1 ? 'Una task per te' : `${proposte.length} task per te`}
            </p>
          </header>
          {proposte.map((t) => (
            <div key={t.id} className="flex flex-wrap items-center gap-3 border-b border-velo px-4 py-3 last:border-0">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold">{t.titolo}</p>
                <p className="text-xs text-tenue">
                  da {nomeDi(t.da)}
                  {t.scadenza ? ` · per il ${fmtDateShort(t.scadenza)}` : ''}
                </p>
              </div>
              <div className="flex shrink-0 gap-2">
                <button
                  onClick={() => {
                    const m = window.prompt('Perché la rimandi indietro?')
                    if (m !== null) rispondiAllaProposta(t, false, m)
                  }}
                  className="rounded-full border border-bordo px-3 py-1.5 text-xs font-semibold text-tenue hover:border-spento"
                >
                  Rimanda indietro
                </button>
                <button
                  onClick={() => rispondiAllaProposta(t, true)}
                  className="rounded-full bg-navy px-4 py-1.5 text-xs font-bold text-white hover:bg-navy-scuro"
                >
                  Accetta
                </button>
              </div>
            </div>
          ))}
        </Card>
      )}

      {/* quelle che hai mandato tu: per sapere a che punto sono senza chiedere */}
      {mandate.length > 0 && vistaVera === 'ongo' && (
        <Card>
          <header className="flex items-baseline justify-between gap-2 border-b border-velo px-4 py-2.5">
            <p className="text-sm font-bold">Mandate da te</p>
            <span className="text-xs text-spento">{mandate.length}</span>
          </header>
          {mandate.map((t) => (
            <div key={t.id} className="flex items-center gap-3 border-b border-velo px-4 py-2.5 last:border-0">
              <div className="min-w-0 flex-1">
                <p className={`text-sm ${t.fatta ? 'text-spento line-through' : 'font-semibold'}`}>{t.titolo}</p>
                <p className="text-xs text-tenue">
                  a {nomeDi(t.owner)}
                  {t.stato === 'rimandata' && t.motivo ? ` · rimandata indietro: ${t.motivo}` : ''}
                </p>
              </div>
              <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                t.fatta ? 'bg-green-50 text-green-800'
                : t.stato === 'proposta' ? 'bg-amber-50 text-amber-800'
                : t.stato === 'rimandata' ? 'bg-red-50 text-red-700'
                : 'bg-velo text-tenue'
              }`}>
                {t.fatta ? 'fatta' : t.stato === 'proposta' ? 'da accettare' : t.stato === 'rimandata' ? 'rimandata' : 'in corso'}
              </span>
            </div>
          ))}
        </Card>
      )}

      {vistaVera === 'big' ? bigPicture() : (
      <Card className="p-3">
        {aggiungo ? (
          <div className="flex items-start gap-3 rounded-lg px-2 py-2">
            <span className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center">
              <span className="h-[18px] w-[18px] rounded-full border-2 border-bordo" />
            </span>
            <div className="flex-1">
              <input
                ref={nuovoRef}
                autoFocus
                value={nuovo}
                onChange={(e) => setNuovo(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') aggiungi()
                  if (e.key === 'Escape') { setAggiungo(false); setNuovo('') }
                }}
                onBlur={() => { if (nuovo.trim()) aggiungi(); else setAggiungo(false) }}
                placeholder="Titolo"
                className="w-full bg-transparent text-sm outline-none placeholder:text-spento"
              />
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                <input
                  type="date"
                  value={nuovaData}
                  onChange={(e) => setNuovaData(e.target.value)}
                  className="rounded-full border border-bordo px-2 py-px text-[11px] text-tenue outline-none focus:border-blu"
                />
                {persone.filter((x) => x.id !== io).length > 0 && (
                  <select
                    value={perChi}
                    onChange={(e) => setPerChi(e.target.value)}
                    className="rounded-full border border-bordo bg-white px-2 py-px text-[11px] text-tenue outline-none focus:border-blu"
                  >
                    <option value="">per me</option>
                    {persone.filter((x) => x.id !== io).map((x) => (
                      <option key={x.id} value={x.id}>per {x.nome ?? 'lui'}</option>
                    ))}
                  </select>
                )}
              </div>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setAggiungo(true)}
            className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left hover:bg-velo/50"
          >
            <span className="flex h-6 w-6 shrink-0 items-center justify-center text-blu">
              <svg viewBox="0 0 24 24" className="h-5 w-5"><path fill="currentColor" d="M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6z" /></svg>
            </span>
            <span className="text-sm font-semibold text-blu">Aggiungi un'attività</span>
          </button>
        )}

        {/* le mie attivita': trascinabili, con le note sotto */}
        {mieDaFare.map((t) => (
          <div
            key={t.id}
            draggable
            onDragStart={() => setTrascino(t.id)}
            onDragEnd={() => { setTrascino(null); setSopraDi(null) }}
            onDragOver={(e) => { e.preventDefault(); setSopraDi(t.id) }}
            onDrop={(e) => { e.preventDefault(); lascia(t) }}
            className={`group rounded-lg transition-all ${
              trascino === t.id ? 'opacity-40' : ''
            } ${sopraDi === t.id && trascino !== t.id ? 'border-t-2 border-blu' : 'border-t-2 border-transparent'}`}
          >
            <div className={`flex items-start gap-3 px-2 py-2 hover:bg-velo/50 ${spuntando === `dre-${t.id}` ? 'opacity-40' : ''}`}>
              <span className="mt-1.5 hidden h-4 w-2.5 shrink-0 cursor-grab flex-col justify-between opacity-0 transition-opacity group-hover:opacity-100 sm:flex" aria-hidden>
                {[0, 1, 2].map((i) => (
                  <span key={i} className="flex justify-between">
                    <span className="h-[3px] w-[3px] rounded-full bg-spento" />
                    <span className="h-[3px] w-[3px] rounded-full bg-spento" />
                  </span>
                ))}
              </span>
              <Cerchio fatta={spuntando === `dre-${t.id}`} onClick={() => spuntaMia(t)} />
              <button onClick={() => setApertaTask(apertaTask === t.id ? null : t.id)} className="min-w-0 flex-1 text-left">
                <p className={`text-sm ${spuntando === `dre-${t.id}` ? 'text-spento line-through' : 'font-medium'}`}>
                  {t.titolo}
                </p>
                {t.dettagli && apertaTask !== t.id && (
                  <p className="truncate text-xs text-tenue">{t.dettagli}</p>
                )}
                {apertaTask !== t.id && chipData(t.scadenza)}
              </button>
            </div>
            {apertaTask === t.id && (
              <div className="salta-su space-y-2 px-2 pb-3 pl-[4.25rem] sm:pl-[4.9rem]">
                <input
                  value={t.titolo}
                  onChange={(e) => setAttivita((a) => a!.map((x) => (x.id === t.id ? { ...x, titolo: e.target.value } : x)))}
                  onBlur={(e) => aggiorna(t.id, { titolo: e.target.value })}
                  className="w-full rounded-lg border border-bordo px-2.5 py-1.5 text-sm outline-none focus:border-blu"
                />
                <textarea
                  rows={2}
                  value={t.dettagli ?? ''}
                  onChange={(e) => setAttivita((a) => a!.map((x) => (x.id === t.id ? { ...x, dettagli: e.target.value } : x)))}
                  onBlur={(e) => aggiorna(t.id, { dettagli: e.target.value || null })}
                  placeholder="Aggiungi dettagli"
                  className="w-full resize-none rounded-lg border border-bordo px-2.5 py-1.5 text-sm outline-none placeholder:text-spento focus:border-blu"
                />
                <input
                  type="date"
                  value={t.scadenza ?? ''}
                  onChange={(e) => aggiorna(t.id, { scadenza: e.target.value || null })}
                  className="rounded-full border border-bordo px-2.5 py-1 text-xs text-tenue outline-none focus:border-blu"
                />
              </div>
            )}
          </div>
        ))}

        {/* la coda dai dati: un titolo, i nomi come sottopunti */}
        {gruppiVivi.map((g) => (
          <div key={g.chiave} className="mt-1">
            <div className="flex items-start gap-3 rounded-lg px-2 py-2 hover:bg-velo/50">
              <Cerchio
                fatta={false}
                mezzo
                onClick={() => spuntaCoda(g.sotto.map((s) => s.chiave))}
              />
              <p className="flex-1 text-sm font-semibold">{g.titolo}</p>
              <span className="text-xs text-spento">{g.sotto.length}</span>
            </div>
            <div className="ml-[1.35rem] border-l border-velo pl-1">
              {g.sotto.map((s) => (
                <div
                  key={s.chiave}
                  className={`flex items-start gap-3 rounded-lg px-2 py-1.5 hover:bg-velo/50 ${
                    spuntando === s.chiave ? 'opacity-40' : ''
                  }`}
                >
                  <Cerchio fatta={spuntando === s.chiave} onClick={() => spuntaCoda([s.chiave])} />
                  <button onClick={() => onOpen(s.prospect_id)} className="min-w-0 flex-1 text-left">
                    <p className={`text-sm ${spuntando === s.chiave ? 'text-spento line-through' : ''}`}>
                      {s.nome}
                      {s.sg && <span className="ml-1.5 text-[10px] font-semibold text-blu/70">{s.sg}</span>}
                    </p>
                    <p className="truncate text-xs text-tenue">{s.nota}</p>
                  </button>
                </div>
              ))}
            </div>
          </div>
        ))}

        {mieDaFare.length === 0 && gruppiVivi.length === 0 && !aggiungo && (
          <p className="px-2 py-6 text-center text-sm text-spento">Tutte le attività completate</p>
        )}
      </Card>
      )}

      {completate.length > 0 && (
        <Card className="p-3">
          <button
            onClick={() => setCompletateAperte(!completateAperte)}
            className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left hover:bg-velo/50"
          >
            <svg viewBox="0 0 24 24" className={`h-4 w-4 text-tenue transition-transform ${completateAperte ? 'rotate-90' : ''}`}>
              <path fill="currentColor" d="M9 6l6 6-6 6z" />
            </svg>
            <span className="text-sm font-semibold">Completate ({completate.length})</span>
          </button>
          {completateAperte && completate.map((c) => (
            <div key={c.chiave} className="flex items-start gap-3 rounded-lg px-2 py-1.5 hover:bg-velo/50">
              <Cerchio fatta onClick={() => ripristina(c)} />
              <p className="flex-1 text-sm text-spento line-through">{c.titolo}</p>
            </div>
          ))}
        </Card>
      )}

      <button
        onClick={() => { setAggiungo(true); setTimeout(() => nuovoRef.current?.focus(), 50) }}
        aria-label="Aggiungi un'attività"
        className="fixed bottom-20 left-1/2 z-30 flex -translate-x-1/2 items-center justify-center rounded-2xl bg-white p-3 text-blu shadow-[0_6px_20px_rgba(16,24,40,0.25)] sm:hidden"
      >
        <svg viewBox="0 0 24 24" className="h-7 w-7"><path fill="currentColor" d="M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6z" /></svg>
      </button>
    </div>
  )
}
