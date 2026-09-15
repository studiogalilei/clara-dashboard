import { useEffect, useMemo, useState } from 'react'
import { supabase } from '../lib/supabase'
import type { Prospect, AgendaItem } from '../lib/types'
import { Card, Micro, Empty, fmtDateShort, fmtOra } from './ui'
import { giorno, creaTask } from '../lib/regole'
import { leggi as leggiPref, scrivi as scriviPref } from '../lib/preferenze'
import CercaAzienda, { nomeAzienda, type Azienda } from './CercaAzienda'

// Il calendario: griglia mensile con le chip dei prospect nelle celle
// (desktop) e lista raggruppata sul telefono. Quattro colori fissi:
// call = blu Galilei, follow-up armato = ambra, scadenza/altro = rosso,
// scadenza di un account = verde.
// I meeting restano in sola lettura: li mette Dre su Google Calendar.
//
// L'unica cosa che si scrive da qui e' una task, e sta apposta in fondo al
// pannello del giorno e non nella barra in alto (Dre, 4/9): il calendario
// non e' il posto delle task, ma se sei qui e ti viene in mente una cosa per
// giovedi', doverla andare a scrivere altrove significa perderla.

type Tipo = 'call' | 'followup' | 'task' | 'altro' | 'account'

// LE SCADENZE DI SALVATORE (15/9). Rifare il budget di un account e il
// rinnovo o la revisione di una campagna sono meta' del mese di un ad
// specialist e non stavano scritte da nessuna parte. Vivono nella tabella
// agenda come tutti gli altri impegni, con un tipo loro: cosi' entrano nella
// griglia che c'e' gia' e il manager le vede nella vista del pod, senza una
// tabella nuova da tenere allineata.
type Scadenza = 'budget' | 'rinnovo'
const SCADENZE: Array<[Scadenza, string]> = [['budget', 'Budget'], ['rinnovo', 'Rinnovo']]
const DETTAGLIO: Record<Scadenza, string> = { budget: 'budget da rifare', rinnovo: 'rinnovo campagna' }
const sottoDi = (t: string | null | undefined): Scadenza | undefined =>
  t === 'budget' || t === 'rinnovo' ? t : undefined

interface Voce {
  at: string
  titolo: string
  tipo: Tipo
  prospect_id: string | null
  chi?: string          // del pod: il nome della persona
  id?: number           // solo le righe di agenda: serve per toglierle
  sotto?: Scadenza      // budget o rinnovo, per la riga del giorno
}

interface Props {
  onOpen: (id: string) => void
  // IL POD (Carlo, 14/9): il manager vede anche calendario, task e scadenze
  // dei progetti delle persone del suo pod, con il nome davanti
  pod?: Array<{ id: string; nome: string | null }>
}

const MESI = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
  'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']
const GIORNI_LUNGHI = ['lunedì', 'martedì', 'mercoledì', 'giovedì', 'venerdì', 'sabato', 'domenica']

const COLORE: Record<Tipo, string> = {
  call: 'bg-blu text-white',
  followup: 'bg-amber-100 text-amber-900',
  task: 'bg-velo text-tenue',
  altro: 'bg-red-100 text-red-900',
  account: 'bg-green-100 text-green-900',
}
const PALLINO: Record<Tipo, string> = {
  call: 'bg-navy', followup: 'bg-amber-500', task: 'bg-spento', altro: 'bg-red-500',
  account: 'bg-green-600',
}

const chiave = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

function tipoAgenda(t: string | null): Tipo {
  if (sottoDi(t)) return 'account'
  if (t && ['conoscitiva', 'tecnica', 'avvio', 'call'].includes(t)) return 'call'
  if (t && ['invio', 'followup'].includes(t)) return 'followup'
  return 'altro'
}

// il pezzo corto per la chip nella cella: si toglie solo il prefisso
// «Call tecnica StudioGalilei - Azienda», non il trattino di «follow-up»,
// che tagliava «Invio follow-up, 30 mail pronte» in «up, 30 mail p…»
// (QA browser, 15/9)
function corto(titolo: string): string {
  const pezzi = titolo.split(' - ')
  const dopo = (pezzi.length > 1 ? pezzi[pezzi.length - 1] : titolo).trim()
  return dopo.length > 18 ? dopo.slice(0, 17) + '…' : dopo
}

export default function Calendario({ onOpen, pod = [] }: Props) {
  const [conPod, setConPod] = useState(() => leggiPref('calendario-pod', 'si') === 'si')
  const [io, setIo] = useState<string | null>(null)
  const oggi = new Date()
  const [voci, setVoci] = useState<Voce[] | null>(null)
  const [anno, setAnno] = useState(oggi.getFullYear())
  const [mese, setMese] = useState(oggi.getMonth())
  const [scelto, setScelto] = useState(chiave(oggi))
  const [scrivoTask, setScrivoTask] = useState(false)
  const [titoloTask, setTitoloTask] = useState('')
  const [salvo, setSalvo] = useState(false)
  const [esito, setEsito] = useState<string | null>(null)
  const [giro, setGiro] = useState(0)     // si alza quando salvi: rilegge l'agenda

  // la scadenza appena salvata deve comparire subito nella griglia, se no
  // sembra che il salvataggio non abbia fatto niente
  function salvata(messaggio: string) {
    setEsito(messaggio)
    setGiro((g) => g + 1)
    setTimeout(() => setEsito(null), 3000)
  }

  async function togliScadenza(v: Voce) {
    if (v.id == null) return
    const { error } = await supabase.from('agenda').delete().eq('id', v.id)
    if (error) { setEsito('Non si è tolta: ' + error.message); return }
    setVoci((l) => (l ?? []).filter((x) => x.id !== v.id))
  }

  async function aggiungiTask() {
    const titolo = titoloTask.trim()
    if (!titolo) { setScrivoTask(false); return }
    setSalvo(true)
    const { problema } = await creaTask({ titolo, scadenza: scelto })
    setSalvo(false)
    if (problema) { setEsito('Non si è salvata: ' + problema); return }
    setEsito(`«${titolo}» è in Task per il ${fmtDateShort(scelto)}`)
    setTitoloTask('')
    setScrivoTask(false)
    setTimeout(() => setEsito(null), 3000)
  }

  useEffect(() => {
    void supabase.auth.getSession().then(({ data }) => setIo(data.session?.user?.id ?? null))
  }, [])

  useEffect(() => {
    Promise.all([
      supabase
        .from('agenda')
        .select('*')
        .gte('at', new Date(Date.now() - 90 * 86400e3).toISOString())
        .order('at', { ascending: true })
        .limit(300),
      supabase
        .from('prospects')
        .select('*')
        .eq('fuori', true)
        .not('next_action_date', 'is', null)
        .order('next_action_date', { ascending: true })
        .limit(200),
      supabase
        .from('prospects')
        .select('*')
        .eq('fuori', false)
        .eq('no_followup', false)
        .not('followup_due', 'is', null)
        .order('followup_due', { ascending: true })
        .limit(200),
      // i miei (owner = io) e quelli del pod, se sono manager
      supabase.from('agenda').select('*').not('owner', 'is', null)
        .gte('at', new Date(Date.now() - 7 * 86400e3).toISOString()).order('at', { ascending: true }).limit(400),
      pod.length ? supabase.from('task').select('id,titolo,scadenza,owner,fatta').in('owner', pod.map((p) => p.id))
        .eq('fatta', false).not('scadenza', 'is', null).limit(300) : Promise.resolve({ data: [] }),
      pod.length ? supabase.from('progetti').select('id,nome,scadenza,chi_segue,stato,prospect_id').not('scadenza', 'is', null).neq('stato', 'consegnato').limit(300) : Promise.resolve({ data: [] }),
    ]).then(([ag, pa, fu, agPod, taskPod, progPod]) => {
      const nome = (id: string | null) => pod.find((p) => p.id === id)?.nome?.split(' ')[0] ?? ''
      const out: Voce[] = ((ag.data as Array<AgendaItem & { owner?: string | null }>) ?? []).filter((a) => !a.owner).map((a) => ({
        at: a.at, titolo: a.titolo, tipo: tipoAgenda(a.tipo), prospect_id: a.prospect_id,
        id: a.id, sotto: sottoDi(a.tipo),
      }))
      for (const a of (agPod.data as Array<AgendaItem & { owner: string }>) ?? []) {
        // i miei senza etichetta, quelli del pod col nome davanti
        out.push({
          at: a.at, titolo: a.titolo, tipo: tipoAgenda(a.tipo), prospect_id: a.prospect_id,
          chi: a.owner === io ? undefined : nome(a.owner), id: a.id, sotto: sottoDi(a.tipo),
        })
      }
      for (const t of (taskPod.data as Array<{ titolo: string; scadenza: string; owner: string }>) ?? []) {
        out.push({ at: t.scadenza + 'T09:00:00', titolo: t.titolo, tipo: 'task', prospect_id: null, chi: t.owner === io ? undefined : nome(t.owner) })
      }
      const miei = new Set(pod.map((p) => (p.nome ?? '').split(' ')[0].toLowerCase()).filter(Boolean))
      for (const g of (progPod.data as Array<{ nome: string; scadenza: string; chi_segue: string | null; prospect_id: string | null }>) ?? []) {
        const chi = (g.chi_segue ?? '').trim()
        if (!chi || !miei.has(chi.split(' ')[0].toLowerCase())) continue
        out.push({ at: g.scadenza + 'T09:00:00', titolo: `Scadenza: ${g.nome}`, tipo: 'altro', prospect_id: g.prospect_id, chi })
      }
      const conEvento = new Set(
        out.filter((v) => v.prospect_id).map((v) => `${v.prospect_id}|${giorno(v.at)}`)
      )
      for (const p of (pa.data as Prospect[]) ?? []) {
        if (conEvento.has(`${p.id}|${p.next_action_date}`)) continue
        out.push({
          at: p.next_action_date! + 'T09:00:00',
          titolo: `${p.next_action ?? 'Prossimo passo'}, ${p.company || p.name || p.email}`,
          tipo: 'altro',
          prospect_id: p.id,
        })
      }
      for (const p of (fu.data as Prospect[]) ?? []) {
        out.push({
          at: p.followup_due!.slice(0, 10) + 'T09:00:00',
          titolo: `Follow-up, ${p.company || p.name || p.email}`,
          tipo: 'followup',
          prospect_id: p.id,
        })
      }
      out.sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime())
      setVoci(out)
    })
  }, [pod, io, giro])

  const visibili = useMemo(() => (voci ?? []).filter((v) => conPod || !v.chi), [voci, conPod])
  const perGiorno = useMemo(() => {
    const m = new Map<string, Voce[]>()
    for (const v of visibili) {
      const g = giorno(v.at)
      m.set(g, [...(m.get(g) ?? []), v])
    }
    return m
  }, [visibili])

  if (voci === null) return null

  const primo = new Date(anno, mese, 1)
  const slittamento = (primo.getDay() + 6) % 7
  const nelMese = new Date(anno, mese + 1, 0).getDate()
  const celle: Array<Date | null> = [
    ...Array.from({ length: slittamento }, () => null),
    ...Array.from({ length: nelMese }, (_, i) => new Date(anno, mese, i + 1)),
  ]
  while (celle.length % 7 !== 0) celle.push(null)

  const oggiChiave = chiave(oggi)
  const delGiorno = perGiorno.get(scelto) ?? []
  const titoloGiorno = new Date(scelto + 'T12:00:00').toLocaleDateString('it-IT', {
    weekday: 'long', day: 'numeric', month: 'long',
  })

  // «Prossimi 7 giorni: N call, M follow-up»
  const adesso = new Date().toISOString()
  const fraSette = new Date(Date.now() + 7 * 86400e3).toISOString()
  const prossimi = visibili.filter((v) => v.at >= adesso && v.at <= fraSette)
  const nCall = prossimi.filter((v) => v.tipo === 'call').length
  const nFu = prossimi.filter((v) => v.tipo === 'followup').length
  const nScad = prossimi.filter((v) => v.tipo === 'account').length

  function cambiaMese(delta: number) {
    const d = new Date(anno, mese + delta, 1)
    setAnno(d.getFullYear())
    setMese(d.getMonth())
  }

  // la lista raggruppata (telefono)
  const domani = giorno(new Date(Date.now() + 86400e3))
  const settimanaFine = fraSette.slice(0, 10)
  const futureVoci = visibili.filter((v) => v.at >= adesso)
  const gruppi: Array<[string, Voce[]]> = [
    ['Oggi', futureVoci.filter((v) => giorno(v.at) === oggiChiave)],
    ['Domani', futureVoci.filter((v) => giorno(v.at) === domani)],
    ['Questa settimana', futureVoci.filter((v) => giorno(v.at) > domani && giorno(v.at) <= settimanaFine)],
    ['Più avanti', futureVoci.filter((v) => giorno(v.at) > settimanaFine)],
  ]

  const rigaVoce = (v: Voce, i: number) => {
    const dentro = (
      <>
        <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${PALLINO[v.tipo]}`} />
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-semibold">{v.chi ? <span className="mr-1.5 rounded-md bg-velo px-1.5 py-0.5 text-[11px] font-bold text-navy">{v.chi}</span> : null}{v.titolo}</span>
          <span className="block text-xs text-tenue">
            {fmtDateShort(v.at)}, {fmtOra(v.at)}
            {v.tipo === 'followup' ? ', follow-up' : v.tipo === 'task' ? ', task' : v.tipo === 'altro' ? ', scadenza' : ''}
          </span>
        </span>
      </>
    )
    return v.prospect_id ? (
      <button
        key={i}
        onClick={() => onOpen(v.prospect_id!)}
        className="flex w-full items-start gap-3 border-b border-velo px-4 py-3 text-left last:border-0 hover:bg-velo/60"
      >
        {dentro}
      </button>
    ) : (
      <div key={i} className="flex items-start gap-3 border-b border-velo px-4 py-3 last:border-0">
        {dentro}
      </div>
    )
  }

  return (
    <div className="pb-24 sm:pb-8">

      {/* telefono: la lista raggruppata */}
      <div className="space-y-5 lg:hidden">
        <Card className="px-4 py-2.5">
          {scrivoTask ? (
            <div className="flex items-center gap-2">
              <input
                autoFocus
                value={titoloTask}
                onChange={(e) => setTitoloTask(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') aggiungiTask()
                  if (e.key === 'Escape') { setScrivoTask(false); setTitoloTask('') }
                }}
                placeholder="Cosa c'è da fare oggi?"
                className="min-w-0 flex-1 rounded-lg border border-bordo px-2.5 py-1.5 text-sm outline-none focus:border-blu"
              />
              <button onClick={aggiungiTask} disabled={!titoloTask.trim() || salvo}
                      className="shrink-0 rounded-full bg-blu px-3 py-1.5 text-xs font-bold text-white disabled:opacity-30">
                {salvo ? 'Salvo…' : 'Metti in Task'}
              </button>
            </div>
          ) : (
            <button onClick={() => setScrivoTask(true)} className="text-sm font-semibold text-blu">
              + Aggiungi una task per oggi
            </button>
          )}
          {esito && <p className="mt-1.5 text-xs font-semibold text-green-700">{esito}</p>}
        </Card>
        {futureVoci.length === 0 && <Card><Empty text="Niente in programma" /></Card>}
        {gruppi.map(([nome, lista]) =>
          lista.length === 0 ? null : (
            <section key={nome}>
              <div className="mb-2 flex items-baseline gap-2">
                <Micro>{nome}</Micro>
                <span className="text-xs text-spento">{lista.length}</span>
              </div>
              <Card>{lista.map(rigaVoce)}</Card>
            </section>
          )
        )}
      </div>

      {/* desktop: griglia + giorno, a tutta larghezza (Dre, 3/9): un mese
          dentro un contenitore stretto si legge, non si scansiona */}
      <div className="hidden gap-4 lg:grid lg:grid-cols-[minmax(0,9fr)_minmax(0,3fr)]">
        <Card className="p-5">
          <div className="mb-3 flex items-baseline justify-between">
            <div className="flex items-baseline gap-2.5">
              <h2 className="text-[15px] font-extrabold">{MESI[mese]} {anno}</h2>
              <span className="text-xs text-spento">
                {(() => {
                  const meseStr = `${anno}-${String(mese + 1).padStart(2, '0')}`
                  const delMese = voci.filter((v) => v.at.startsWith(meseStr))
                  const c = delMese.filter((v) => v.tipo === 'call').length
                  const f = delMese.filter((v) => v.tipo === 'followup').length
                  const s = delMese.filter((v) => v.tipo === 'account').length
                  if (delMese.length === 0) return 'mese libero'
                  return `${c} call, ${f} follow-up` + (s > 0 ? `, ${s === 1 ? '1 scadenza' : `${s} scadenze`}` : '')
                })()}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <button onClick={() => cambiaMese(-1)} aria-label="Mese precedente"
                className="flex h-8 w-8 items-center justify-center rounded-full text-tenue hover:bg-velo">‹</button>
              <button
                onClick={() => { setAnno(oggi.getFullYear()); setMese(oggi.getMonth()); setScelto(oggiChiave) }}
                className="rounded-full border border-bordo px-3 py-1 text-xs font-semibold text-tenue hover:border-spento">
                Oggi
              </button>
              <button onClick={() => cambiaMese(1)} aria-label="Mese successivo"
                className="flex h-8 w-8 items-center justify-center rounded-full text-tenue hover:bg-velo">›</button>
            </div>
          </div>

          <div className="mb-3 flex flex-wrap items-center gap-2">
            {(nCall > 0 || nFu > 0 || nScad > 0) && (
              <button
                onClick={() => { setAnno(oggi.getFullYear()); setMese(oggi.getMonth()); setScelto(oggiChiave) }}
                className="flex-1 rounded-xl bg-velo px-3 py-2 text-left text-xs font-semibold text-tenue hover:bg-velo/70"
              >
                Prossimi 7 giorni: {nCall} call, {nFu} follow-up{nScad > 0 ? `, ${nScad === 1 ? '1 scadenza' : `${nScad} scadenze`}` : ''}
              </button>
            )}
            {pod.length > 0 && (
              <button onClick={() => setConPod((v) => { scriviPref('calendario-pod', v ? 'no' : 'si'); return !v })}
                      className={`shrink-0 rounded-full border px-3 py-1.5 text-[11px] font-bold ${conPod ? 'border-navy bg-navy text-white' : 'border-bordo bg-white text-tenue'}`}>
                Pod{conPod ? '' : ': nascosto'}
              </button>
            )}
          </div>
          {pod.length > 0 && conPod && !(voci ?? []).some((v) => v.chi) && (
            <p className="mb-3 rounded-xl bg-velo px-3 py-2 text-xs text-spento">
              {pod.map((p) => p.nome?.split(' ')[0]).filter(Boolean).join(' e ')} non hanno ancora collegato Google: i loro impegni arrivano da lì.
            </p>
          )}

          <div className="mb-1 grid grid-cols-7 border-b border-velo">
            {GIORNI_LUNGHI.map((g, i) => (
              <span key={i} className={`px-2 py-1.5 text-[11px] font-bold uppercase tracking-wide ${i >= 5 ? 'text-bordo' : 'text-tenue'}`}>
                {g}
              </span>
            ))}
          </div>
          <div className="grid grid-cols-7 gap-1">
            {celle.map((d, i) => {
              if (!d) return <span key={i} />
              const k = chiave(d)
              const eventi = perGiorno.get(k) ?? []
              const eOggi = k === oggiChiave
              const eScelto = k === scelto
              const weekend = i % 7 >= 5
              return (
                <button
                  key={i}
                  onClick={() => setScelto(k)}
                  className={`flex min-h-[118px] flex-col gap-1 rounded-lg border p-2 text-left transition-colors ${
                    eScelto ? 'border-navy bg-navy/5'
                    : 'border-transparent hover:border-bordo'
                  } ${weekend ? 'bg-velo/40' : ''}`}
                >
                  <span className={`self-start text-sm font-bold ${
                    eOggi ? 'flex h-6 w-6 items-center justify-center rounded-full bg-blu text-white' : 'text-tenue'
                  }`}>
                    {d.getDate()}
                  </span>
                  {eventi.slice(0, 4).map((v, j) => (
                    <span key={j} className={`truncate rounded px-1.5 py-0.5 text-[11px] font-semibold leading-tight ${COLORE[v.tipo]}`}>
                      {corto(v.titolo)}
                    </span>
                  ))}
                  {eventi.length > 4 && (
                    <span className="text-[11px] font-semibold text-spento">+{eventi.length - 4}</span>
                  )}
                </button>
              )
            })}
          </div>
        </Card>

        <div key={scelto} className="salta-su">
          <p className="mb-2 flex items-baseline gap-2 text-sm font-bold capitalize">
            {titoloGiorno}
            {delGiorno.length > 0 && (
              <span className="text-xs font-semibold normal-case text-spento">
                {delGiorno.length} in programma
              </span>
            )}
          </p>
          <Card>
            {delGiorno.length === 0
              ? <Empty text="Niente in programma" />
              : delGiorno.map(rigaVoce)}

            {/* la porta discreta: una riga sotto quello che c'e' gia' */}
            <div className="border-t border-velo px-4 py-2.5">
              {scrivoTask ? (
                <div className="flex items-center gap-2">
                  <input
                    autoFocus
                    value={titoloTask}
                    onChange={(e) => setTitoloTask(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') aggiungiTask()
                      if (e.key === 'Escape') { setScrivoTask(false); setTitoloTask('') }
                    }}
                    placeholder="Cosa c'è da fare?"
                    className="min-w-0 flex-1 rounded-lg border border-bordo px-2.5 py-1.5 text-sm outline-none focus:border-blu"
                  />
                  <button
                    onClick={aggiungiTask}
                    disabled={!titoloTask.trim() || salvo}
                    className="shrink-0 rounded-full bg-blu px-3 py-1.5 text-xs font-bold text-white disabled:opacity-30"
                  >
                    {salvo ? 'Salvo…' : 'Metti in Task'}
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setScrivoTask(true)}
                  className="text-xs font-semibold text-spento hover:text-navy"
                >
                  + una task per questo giorno
                </button>
              )}
              {esito && <p className="mt-1.5 text-xs font-semibold text-green-700">{esito}</p>}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
