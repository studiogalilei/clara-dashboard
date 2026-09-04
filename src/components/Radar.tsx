import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { PIPELINE_LABEL, type Prospect, type AgendaItem } from '../lib/types'
import { Dot, Card, daysAgo, fmtDateShort, fmtOra } from './ui'
import { VIVI, oggi, giorno, codaDiOggi, GIORNI_FOLLOWUP, type VoceCoda } from '../lib/regole'

// Il radar della home: la riga dei 4 numeri (la scura e' «Da fare oggi»,
// e le call di OGGI vivono li' dentro), la card «Prossima» con il primo
// evento futuro, e gli Avvisi. Regole della sintesi 31/8: mai lo stesso
// evento in due punti; zero eventi in settimana = zero interfaccia.

const FERMO_DAYS = 30


interface Avviso {
  peso: number
  tono: 'fermo' | 'attesa'
  testo: string
  id: string | null
}

interface Props {
  onOpen: (id: string) => void
  onOggi?: () => void
  onCalendario?: () => void
}

interface VoceTicker {
  testo: string
  prospect_id: string | null
}

function fraQuanto(at: string): string {
  const ms = new Date(at).getTime() - Date.now()
  const ore = Math.round(ms / 3600e3)
  if (ore < 24) return `fra ${ore} or${ore === 1 ? 'a' : 'e'}`
  const gg = Math.round(ms / 86400e3)
  if (gg === 1) return 'domani'
  return `fra ${gg} giorni`
}

export default function Radar({ onOpen, onOggi, onCalendario }: Props) {
  const [avvisi, setAvvisi] = useState<Avviso[]>([])
  const [prossimo, setProssimo] = useState<AgendaItem | null>(null)
  const [settimana, setSettimana] = useState(0)
  const [aggiornato, setAggiornato] = useState<string | null>(null)
  const [pronto, setPronto] = useState(false)
  const [callDiOggi, setCallDiOggi] = useState<VoceTicker[]>([])
  const [coda, setCoda] = useState<VoceTicker[]>([])
  const [indice, setIndice] = useState(0)
  const [fermo, setFermo] = useState(false)
  const [tuttiAvvisi, setTuttiAvvisi] = useState(false)

  useEffect(() => {
    const today = oggi()
    const adesso = new Date().toISOString()
    const fraSette = new Date(Date.now() + 7 * 86400e3).toISOString()

    supabase
      .from('sync_runs')
      .select('*')
      .order('finished_at', { ascending: false })
      .limit(1)
      .then(({ data }) => {
        const run = (data as Array<{ finished_at: string | null }> | null)?.[0]
        if (run?.finished_at) setAggiornato(run.finished_at)
      })

    // «cosa devo fare oggi» la decide regole.ts, per tutti. Prima ogni
    // schermata rifaceva le sue query con filtri e tetti diversi, e i due
    // numeri che stanno in testata e qui sotto non tornavano mai (4/9)
    codaDiOggi().then(({ voci }) => {
      const nome = (p: Prospect) => p.company || p.name || p.email
      const testo = (v: VoceCoda): string => {
        if (v.ragione === 'rispondi') return `Rispondere a ${nome(v.p)}`
        if (v.ragione === 'followup') {
          return v.p.followup_due
            ? `Follow-up a ${nome(v.p)} · previsto ${fmtDateShort(v.p.followup_due)}`
            : `Follow-up a ${nome(v.p)}${v.fermoDa !== null ? ` · tace da ${v.fermoDa} gg` : ''}`
        }
        if (v.ragione === 'ricontatto') return `${v.p.next_action ?? 'Ricontatto'} · ${nome(v.p)}`
        return `Rientrato dalle ferie: ${nome(v.p)}`
      }
      setCoda(voci.map((v) => ({ testo: testo(v), prospect_id: v.p.id })))
      setPronto(true)
    })

    Promise.all([
      supabase
        .from('agenda')
        .select('*')
        .gte('at', new Date(Date.now() - 14 * 86400e3).toISOString())
        .order('at', { ascending: true })
        .limit(50),
      supabase
        .from('prospects')
        .select('*')
        .in('stage', ['analisi_inviata', 'in_follow_up'])
        .eq('no_followup', false)
        .eq('awaiting_us', false)
        .eq('fuori', false)
        .or(VIVI)
        .order('analysis_sent_at', { ascending: true, nullsFirst: false })
        .limit(1000),
      supabase
        .from('prospects')
        .select('*')
        .eq('fuori', true)
        .in('pipeline_stage', ['conoscitiva', 'tecnica', 'avvio']),
      supabase
        .from('prospects')
        .select('*')
        .eq('fuori', false)
        .in('classificazione', ['rinvio', 'ooo'])
        .eq('no_followup', false)
        .order('last_reply_at', { ascending: false, nullsFirst: false })
        .limit(1000),
    ]).then(([ag, fu, pi, ri]) => {
      const eventi = (ag.data as AgendaItem[]) ?? []
      const futuri = eventi.filter((a) => a.at >= adesso)
      const passati = eventi.filter((a) => a.at < adesso)
      const inPipeline = (pi.data as Prospect[]) ?? []

      // oggi vive nel ticker; il primo dei giorni dopo = «Prossima»
      setProssimo(futuri.find((a) => giorno(a.at) > today) ?? null)
      setSettimana(futuri.filter((a) => a.at <= fraSette).length)

      const dovuti = ((fu.data as Prospect[]) ?? []).filter((p) => {
        if (p.followup_due) return p.followup_due.slice(0, 10) <= today
        const d = daysAgo(p.analysis_sent_at)
        return d !== null && d >= GIORNI_FOLLOWUP
      })
      // le call di oggi: quelle stanno nell'agenda, non nella coda
      setCallDiOggi(futuri.filter((a) => a.at.slice(0, 10) === today)
        .map((a) => ({ testo: `${fmtOra(a.at)} · ${a.titolo}`, prospect_id: a.prospect_id })))

      const nuovi: Avviso[] = []
      for (const a of passati) {
        if (!a.prospect_id) continue
        const p = inPipeline.find((x) => x.id === a.prospect_id)
        if (p && (!p.next_action_date || p.next_action_date < today)) {
          nuovi.push({
            peso: 1, tono: 'fermo',
            testo: `${p.company || p.name || p.email}: la call del ${fmtDateShort(a.at)} è passata e la scheda è ferma`,
            id: p.id,
          })
        }
      }
      for (const p of (ri.data as Prospect[]) ?? []) {
        if (!p.next_action_date && !p.followup_due && !p.ooo_until) {
          nuovi.push({
            peso: 2, tono: 'attesa',
            testo: `${p.company || p.name || p.email}: in attesa senza una data`,
            id: p.id,
          })
        }
      }
      const fermi = dovuti.filter((p) => (daysAgo(p.analysis_sent_at) ?? 0) >= FERMO_DAYS)
      if (fermi.length > 0) {
        nuovi.push({
          peso: 3, tono: 'fermo',
          testo: `${fermi.length} person${fermi.length === 1 ? 'a aspetta' : 'e aspettano'} una risposta da più di un mese`,
          id: null,
        })
      }
      for (const p of inPipeline) {
        const nome = p.company || p.name || p.email
        if (!p.next_action && !p.next_action_date) {
          nuovi.push({
            peso: 4, tono: 'fermo',
            testo: `${nome}: in ${p.pipeline_stage ? PIPELINE_LABEL[p.pipeline_stage] : 'pipeline'} senza un prossimo passo`,
            id: p.id,
          })
        } else if (p.next_action_date && p.next_action_date < today) {
          nuovi.push({
            peso: 5, tono: 'attesa',
            testo: `${nome}: «${p.next_action ?? 'prossimo passo'}» era per il ${fmtDateShort(p.next_action_date)}`,
            id: p.id,
          })
        }
      }

      nuovi.sort((a, b) => a.peso - b.peso)
      const visti = new Set<string>()
      setAvvisi(nuovi.filter((a) => {
        if (!a.id) return true
        if (visti.has(a.id)) return false
        visti.add(a.id)
        return true
      }))
    })
  }, [])

  // quello che scorre: prima le call di oggi, poi la coda. Due sorgenti,
  // una lista sola, e il numero in alto conta questa. Prima il Radar ne
  // calcolava un terzo, lo scriveva e non lo mostrava a nessuno (4/9)
  const ticker = [...callDiOggi, ...coda]

  useEffect(() => {
    if (ticker.length < 2 || fermo) return
    const t = setInterval(() => {
      // in secondo piano il tempo non conta: senza questo si torna alla
      // scheda e la card ha gia' fatto tre giri a vuoto
      if (document.hidden) return
      setIndice((i) => (i + 1) % ticker.length)
    }, 5000)
    return () => clearInterval(t)
  }, [ticker.length, fermo])

  const oraControllo = aggiornato ? fmtOra(aggiornato) : fmtOra(new Date().toISOString())
  const visibili = tuttiAvvisi ? avvisi : avvisi.slice(0, 3)
  const urgente = prossimo && new Date(prossimo.at).getTime() - Date.now() < 26 * 3600e3

  return (
    <div className="space-y-4">

      {/* ── cosa devi fare adesso ─────────────────────────────── */}
      <div>
        <div
          onMouseEnter={() => setFermo(true)}
          onMouseLeave={() => setFermo(false)}
          onPointerDown={() => setFermo(true)}
          onFocusCapture={() => setFermo(true)}
          className="rounded-2xl bg-navy p-3.5 text-white shadow-[0_8px_24px_rgba(6,23,115,0.25)]"
        >
          <div className="flex items-baseline justify-between">
            <p className="text-[11px] font-bold uppercase tracking-[0.05em] text-white/60">Da fare oggi</p>
            {ticker.length > 0 && (
              <div className="flex items-center gap-1.5">
                <button onClick={onOggi} className="text-[11px] font-bold tabular-nums text-white/70 hover:text-white">
                  {(indice % ticker.length) + 1}/{ticker.length}
                </button>
                {ticker.length > 1 && (
                  <button
                    onClick={() => { setFermo(true); setIndice((i) => (i + 1) % ticker.length) }}
                    aria-label="La prossima cosa da fare"
                    className="-my-1 rounded px-1 py-1 text-[11px] font-bold text-white/50 hover:text-white"
                  >
                    ›
                  </button>
                )}
              </div>
            )}
          </div>
          <div className="relative mt-1 h-12 overflow-hidden">
            {!pronto ? (
              <p className="text-lg font-extrabold">…</p>
            ) : ticker.length === 0 ? (
              <>
                <p className="text-[15px] font-extrabold">Tutto in ordine</p>
                {prossimo && (
                  <p className="truncate text-[11px] text-white/70">
                    Prossima: {prossimo.titolo} · {fmtDateShort(prossimo.at)}
                  </p>
                )}
              </>
            ) : (
              <>
                {ticker.length > 1 && (
                  <button
                    key={`fuori-${indice}`}
                    onClick={onOggi}
                    className="ticker-fuori pointer-events-none absolute inset-0 text-left"
                    aria-hidden
                  >
                    <p className="truncate text-[15px] font-extrabold leading-snug">
                      {ticker[(indice + ticker.length - 1) % ticker.length].testo}
                    </p>
                  </button>
                )}
                <button
                  key={`dentro-${indice}`}
                  onClick={() => {
                    const v = ticker[indice % ticker.length]
                    if (v.prospect_id) onOpen(v.prospect_id)
                    else onOggi?.()
                  }}
                  className="ticker-dentro absolute inset-0 text-left"
                >
                  <p className="line-clamp-2 text-[15px] font-extrabold leading-snug">
                    {ticker[indice % ticker.length].testo}
                  </p>
                </button>
              </>
            )}
          </div>
        </div>

      </div>

      {/* ── la Prossima: un solo evento, grande ───────────────── */}
      {prossimo && (
        <Card className="border-l-4 border-l-navy">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-5 py-3.5">
            <button
              onClick={() => prossimo.prospect_id ? onOpen(prossimo.prospect_id) : onCalendario?.()}
              className="flex min-w-0 flex-1 flex-wrap items-baseline gap-x-3 gap-y-0.5 text-left"
            >
              <span className={`text-[15px] font-extrabold ${urgente ? 'text-amber-700' : ''}`}>
                {fraQuanto(prossimo.at)}
              </span>
              <span className="min-w-0 truncate text-sm font-semibold">{prossimo.titolo}</span>
              <span className="text-xs text-spento">
                {fmtDateShort(prossimo.at)} · {fmtOra(prossimo.at)}
              </span>
            </button>
            {settimana > 1 && onCalendario && (
              <button onClick={onCalendario} className="shrink-0 text-xs font-semibold text-blu hover:underline">
                altri {settimana - 1} in settimana →
              </button>
            )}
          </div>
        </Card>
      )}

      {/* ── avvisi ────────────────────────────────────────────── */}
      <div id="avvisi" className="scroll-mt-4">
        {avvisi.length === 0 ? (
          <p className="flex items-center gap-2 rounded-2xl border border-green-200 bg-green-50 px-4 py-2.5 text-sm text-green-800">
            <span className="font-bold">✓</span>
            Clara ha controllato tutto alle {oraControllo}: zero problemi.
          </p>
        ) : (
          <Card>
            <header className="flex flex-wrap items-center gap-2.5 border-b border-velo px-4 py-2.5">
              <span className="text-[13px] font-bold">Avvisi</span>
              <span className="rounded-full bg-red-600 px-2 py-px text-[11px] font-bold text-white">
                {avvisi.length}
              </span>
              <span className="ml-auto text-[11px] text-spento">controllato tutto alle {oraControllo}</span>
            </header>
            {visibili.map((a, i) => {
              const vai = a.id ? () => onOpen(a.id!) : onOggi
              const dentro = (
                <>
                  <span className="mt-[7px]"><Dot tone={a.tono} /></span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-semibold">{a.testo}</span>
                  </span>
                </>
              )
              return vai ? (
                <button
                  key={i}
                  onClick={vai}
                  className="flex w-full items-start gap-3 border-b border-velo px-4 py-2.5 text-left last:border-0 hover:bg-velo/60"
                >
                  {dentro}
                </button>
              ) : (
                <div key={i} className="flex items-start gap-3 border-b border-velo px-4 py-2.5 last:border-0">
                  {dentro}
                </div>
              )
            })}
            {avvisi.length > 3 && (
              <button
                onClick={() => setTuttiAvvisi(!tuttiAvvisi)}
                className="w-full px-4 py-2 text-left text-xs font-semibold text-blu hover:bg-velo/60"
              >
                {tuttiAvvisi ? 'Mostra meno' : `Altri ${avvisi.length - 3} avvisi`}
              </button>
            )}
          </Card>
        )}
      </div>
    </div>
  )
}
