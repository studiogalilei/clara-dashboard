import { useEffect, useMemo, useState } from 'react'
import { supabase } from '../lib/supabase'
import type { Prospect, AgendaItem } from '../lib/types'
import { Card, Micro, Empty, fmtDateShort, fmtOra } from './ui'
import { giorno } from '../lib/regole'

// Il calendario: griglia mensile con le chip dei prospect nelle celle
// (desktop) e lista raggruppata sul telefono. Tre colori fissi:
// call = blu Galilei, follow-up armato = ambra, scadenza/altro = rosso.
// Sola lettura: i meeting li mette Dre su Google Calendar, regola fissa.

type Tipo = 'call' | 'followup' | 'altro'

interface Voce {
  at: string
  titolo: string
  tipo: Tipo
  prospect_id: string | null
}

interface Props {
  onOpen: (id: string) => void
}

const MESI = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
  'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']
const GIORNI = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']

const COLORE: Record<Tipo, string> = {
  call: 'bg-navy text-white',
  followup: 'bg-amber-100 text-amber-900',
  altro: 'bg-red-100 text-red-900',
}
const PALLINO: Record<Tipo, string> = {
  call: 'bg-navy', followup: 'bg-amber-500', altro: 'bg-red-500',
}

const chiave = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

function tipoAgenda(t: string | null): Tipo {
  if (t && ['conoscitiva', 'tecnica', 'avvio', 'call'].includes(t)) return 'call'
  if (t && ['invio', 'followup'].includes(t)) return 'followup'
  return 'altro'
}

// il pezzo corto per la chip nella cella
function corto(titolo: string): string {
  const dopo = titolo.split('·').pop()?.trim() ?? titolo
  return dopo.length > 14 ? dopo.slice(0, 13) + '…' : dopo
}

export default function Calendario({ onOpen }: Props) {
  const oggi = new Date()
  const [voci, setVoci] = useState<Voce[] | null>(null)
  const [anno, setAnno] = useState(oggi.getFullYear())
  const [mese, setMese] = useState(oggi.getMonth())
  const [scelto, setScelto] = useState(chiave(oggi))

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
        .limit(200),
      supabase
        .from('prospects')
        .select('*')
        .eq('fuori', false)
        .eq('no_followup', false)
        .not('followup_due', 'is', null)
        .limit(200),
    ]).then(([ag, pa, fu]) => {
      const out: Voce[] = ((ag.data as AgendaItem[]) ?? []).map((a) => ({
        at: a.at, titolo: a.titolo, tipo: tipoAgenda(a.tipo), prospect_id: a.prospect_id,
      }))
      const conEvento = new Set(
        out.filter((v) => v.prospect_id).map((v) => `${v.prospect_id}|${giorno(v.at)}`)
      )
      for (const p of (pa.data as Prospect[]) ?? []) {
        if (conEvento.has(`${p.id}|${p.next_action_date}`)) continue
        out.push({
          at: p.next_action_date! + 'T09:00:00',
          titolo: `${p.next_action ?? 'Prossimo passo'} · ${p.company || p.name || p.email}`,
          tipo: 'altro',
          prospect_id: p.id,
        })
      }
      for (const p of (fu.data as Prospect[]) ?? []) {
        out.push({
          at: p.followup_due!.slice(0, 10) + 'T09:00:00',
          titolo: `Follow-up · ${p.company || p.name || p.email}`,
          tipo: 'followup',
          prospect_id: p.id,
        })
      }
      out.sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime())
      setVoci(out)
    })
  }, [])

  const perGiorno = useMemo(() => {
    const m = new Map<string, Voce[]>()
    for (const v of voci ?? []) {
      const g = giorno(v.at)
      m.set(g, [...(m.get(g) ?? []), v])
    }
    return m
  }, [voci])

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

  // «Prossimi 7 giorni: N call · M follow-up»
  const adesso = new Date().toISOString()
  const fraSette = new Date(Date.now() + 7 * 86400e3).toISOString()
  const prossimi = voci.filter((v) => v.at >= adesso && v.at <= fraSette)
  const nCall = prossimi.filter((v) => v.tipo === 'call').length
  const nFu = prossimi.filter((v) => v.tipo === 'followup').length

  function cambiaMese(delta: number) {
    const d = new Date(anno, mese + delta, 1)
    setAnno(d.getFullYear())
    setMese(d.getMonth())
  }

  // la lista raggruppata (telefono)
  const domani = giorno(new Date(Date.now() + 86400e3))
  const settimanaFine = fraSette.slice(0, 10)
  const futureVoci = voci.filter((v) => v.at >= adesso)
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
          <span className="block text-sm font-semibold">{v.titolo}</span>
          <span className="block text-xs text-tenue">
            {fmtDateShort(v.at)} · {fmtOra(v.at)}
            {v.tipo === 'followup' ? ' · follow-up' : v.tipo === 'altro' ? ' · scadenza' : ''}
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

      {/* desktop: griglia + giorno */}
      <div className="hidden gap-4 lg:grid lg:grid-cols-[minmax(0,8fr)_minmax(0,4fr)]">
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
                  return delMese.length === 0 ? 'mese libero' : `${c} call · ${f} follow-up`
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

          {(nCall > 0 || nFu > 0) && (
            <button
              onClick={() => { setAnno(oggi.getFullYear()); setMese(oggi.getMonth()); setScelto(oggiChiave) }}
              className="mb-3 w-full rounded-xl bg-velo px-3 py-2 text-left text-xs font-semibold text-tenue hover:bg-velo/70"
            >
              Prossimi 7 giorni: {nCall} call · {nFu} follow-up
            </button>
          )}

          <div className="mb-1 grid grid-cols-7">
            {GIORNI.map((g, i) => (
              <span key={i} className={`py-1 text-center text-[11px] font-bold uppercase ${i >= 5 ? 'text-bordo' : 'text-spento'}`}>
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
                  className={`flex min-h-[64px] flex-col gap-1 rounded-lg border p-1.5 text-left transition-colors ${
                    eScelto ? 'border-navy bg-navy/5'
                    : 'border-transparent hover:border-bordo'
                  } ${weekend ? 'opacity-60' : ''}`}
                >
                  <span className={`self-start text-xs font-bold ${
                    eOggi ? 'flex h-5 w-5 items-center justify-center rounded-full bg-navy text-white' : 'text-tenue'
                  }`}>
                    {d.getDate()}
                  </span>
                  {eventi.slice(0, 2).map((v, j) => (
                    <span key={j} className={`truncate rounded px-1 py-px text-[10px] font-semibold leading-tight ${COLORE[v.tipo]}`}>
                      {corto(v.titolo)}
                    </span>
                  ))}
                  {eventi.length > 2 && (
                    <span className="text-[10px] font-semibold text-spento">+{eventi.length - 2}</span>
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
          </Card>
        </div>
      </div>
    </div>
  )
}
