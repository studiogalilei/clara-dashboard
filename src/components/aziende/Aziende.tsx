import { useCallback, useEffect, useMemo, useState } from 'react'
import { supabase } from '../../lib/supabase'
import type { PipelineStage, Prospect } from '../../lib/types'
import { giorno, pedaggioPagato, ultimoMovimento, vivo } from '../../lib/regole'
import { azzeraCanone } from '../../lib/soldi'
import { IN_TRATTATIVA, NOME_TAPPA, PRIMA_DELLA_CALL, inBacheca, mossa, tappaDi, toccaANoi, type Tappa } from '../../lib/percorso'
import { daysAgo, fmtDateShort, giorni, Spinner } from '../ui'
import Pannello from './Pannello'

// AZIENDE, LA BACHECA NUOVA (Dre, 30/9: «a me serve mandare avanti i lead e
// aggiungere le cose»). Rifatta da zero sulle fondamenta del 30/9: ogni azienda ha
// una tappa e una palla (lib/percorso.ts). Cinque colonne, ogni carta dice UNA cosa
// (la piu' importante), e cliccando si apre il pannello da cui si fa tutto.

type Colonna = 'lead' | Tappa
const COLONNE: Array<[Colonna, string]> = [
  ['lead', 'Lead'], ['conoscitiva', 'Conoscitiva'], ['tecnica', 'Tecnica'], ['avvio', 'Avvio'], ['prova', 'Prova'],
]
type Vista = 'cammino' | 'clienti' | 'persi' | 'scartati'

export type Esegui = (p: Prospect, verso: Tappa | 'lead', opz?: { motivo?: string }) => Promise<boolean>

const nomeDi = (p: Prospect) => p.company || p.name || p.email

/** La riga della carta: una cosa sola, la piu' importante. */
function riga(p: Prospect, bozze: number): { testo: string; tono: 'nostra' | 'ok' | 'ferma' | 'spento' } {
  const oggi = giorno()
  if (bozze > 0) return { testo: 'Bozza pronta in Posta', tono: 'nostra' }
  if (p.awaiting_us) return { testo: `Ha scritto${p.last_reply_at ? ` il ${fmtDateShort(p.last_reply_at)}` : ''}: tocca a te`, tono: 'nostra' }
  if (p.next_action_date) {
    const scaduta = p.next_action_date < oggi
    return { testo: `${p.next_action || 'Prossimo passo'} ${p.next_action_date === oggi ? 'oggi' : `il ${fmtDateShort(p.next_action_date)}`}`, tono: scaduta ? 'nostra' : 'ok' }
  }
  const fermo = daysAgo(ultimoMovimento(p))
  if (IN_TRATTATIVA.includes(tappaDi(p))) return { testo: 'Nessun prossimo passo', tono: 'ferma' }
  if (fermo !== null && fermo >= 1) return { testo: `Aspettiamo loro, da ${giorni(fermo)}`, tono: 'spento' }
  return { testo: 'Aspettiamo loro', tono: 'spento' }
}

const PUNTO: Record<string, string> = { nostra: 'bg-red-600', ok: 'bg-green-600', ferma: 'bg-amber-500', spento: 'bg-bordo' }

export default function Aziende({ onScheda }: { onScheda: (id: string) => void }) {
  const [righe, setRighe] = useState<Prospect[] | null>(null)
  const [bozze, setBozze] = useState<Map<string, number>>(new Map())
  const [sel, setSel] = useState<string | null>(null)
  const [vista, setVista] = useState<Vista>('cammino')
  const [mie, setMie] = useState(false)
  const [cerca, setCerca] = useState('')
  const [avviso, setAvviso] = useState<string | null>(null)
  const [conferma, setConferma] = useState<{ p: Prospect; verso: Tappa | 'lead' } | null>(null)
  const [sopra, setSopra] = useState<Colonna | null>(null)

  const carica = useCallback(async () => {
    const [pr, bz] = await Promise.all([
      supabase.from('prospects').select('*').neq('tappa', 'nuovo').limit(1000),
      supabase.from('proposte').select('prospect_id').eq('stato', 'aperta').eq('tipo', 'risposta').limit(1000),
    ])
    setRighe(((pr.data as Prospect[]) ?? []).filter((p) => tappaDi(p) !== 'nuovo'))
    const m = new Map<string, number>()
    for (const r of (bz.data as Array<{ prospect_id: string | null }>) ?? []) if (r.prospect_id) m.set(r.prospect_id, (m.get(r.prospect_id) ?? 0) + 1)
    setBozze(m)
  }, [])
  useEffect(() => { void carica() }, [carica])

  useEffect(() => {
    if (!avviso) return
    const t = setTimeout(() => setAvviso(null), 4500)
    return () => clearTimeout(t)
  }, [avviso])

  // muovere un'azienda: la regola e' una sola (lib/percorso.ts), da qui e dal pannello
  const esegui: Esegui = useCallback(async (p, verso, opz = {}) => {
    const da = tappaDi(p)
    const riassunto = ['conoscitiva', 'tecnica', 'avvio'].includes(da) ? await pedaggioPagato(p.id, da as PipelineStage) : true
    const m = mossa(p, verso, { ...opz, riassunto })
    if ('no' in m) { setAvviso(m.no); return false }
    const { data, error } = await supabase.from('prospects').update(m.patch).eq('id', p.id).select().single()
    if (error || !data) { setAvviso(`${nomeDi(p)}: non sono riuscito a salvare, resta dov'era`); return false }
    await supabase.from('interactions').insert({ prospect_id: p.id, at: new Date().toISOString(), kind: 'nota', body: m.nota })
    if (da === 'cliente' && verso !== 'cliente') void azzeraCanone(p.id)      // il canone sta in cassaforte (29/9)
    setRighe((rs) => (rs ?? []).map((x) => (x.id === p.id ? (data as Prospect) : x)))
    setAvviso(`${nomeDi(p)}: ${m.nota.replace(/\.$/, '')}`)
    return true
  }, [])

  // indietro si puo', ma non per sbaglio (Dre, 2/9)
  const verso = useCallback(async (p: Prospect, dove: Colonna) => {
    const da = tappaDi(p)
    const target: Tappa | 'lead' = dove === 'lead' ? 'lead' : dove
    const indietro = target === 'lead' ? !PRIMA_DELLA_CALL.includes(da) : IN_TRATTATIVA.indexOf(target) < IN_TRATTATIVA.indexOf(da)
    if (dove === 'lead' && PRIMA_DELLA_CALL.includes(da)) return
    if (indietro) { setConferma({ p, verso: target }); return }
    await esegui(p, target)
  }, [esegui])

  const tutte = useMemo(() => {
    const q = cerca.trim().toLowerCase()
    return (righe ?? []).filter((p) => !q || `${p.company ?? ''} ${p.name ?? ''} ${p.email}`.toLowerCase().includes(q))
  }, [righe, cerca])

  const insiemi = useMemo(() => ({
    cammino: tutte.filter((p) => inBacheca(p)),
    clienti: tutte.filter((p) => tappaDi(p) === 'cliente'),
    persi: tutte.filter((p) => tappaDi(p) === 'perso'),
    scartati: tutte.filter((p) => !vivo(p) && tappaDi(p) !== 'perso' && tappaDi(p) !== 'cliente'),
  }), [tutte])

  const nostre = insiemi.cammino.filter((p) => toccaANoi(p, bozze.has(p.id))).length
  const ordina = (l: Prospect[]) => [...l].sort((a, b) => {
    const na = toccaANoi(a, bozze.has(a.id)) ? 0 : 1, nb = toccaANoi(b, bozze.has(b.id)) ? 0 : 1
    if (na !== nb) return na - nb
    return (ultimoMovimento(b) ?? '').localeCompare(ultimoMovimento(a) ?? '')
  })

  if (!righe) return <Spinner />
  const aperta = righe.find((p) => p.id === sel) ?? null
  const visibili = mie ? insiemi.cammino.filter((p) => toccaANoi(p, bozze.has(p.id))) : insiemi.cammino

  const carta = (p: Prospect, conTappa: boolean) => {
    const r = riga(p, bozze.get(p.id) ?? 0)
    return (
      <button key={p.id} draggable onDragStart={(e) => e.dataTransfer.setData('text/plain', p.id)} onClick={() => setSel(p.id)}
              className={`w-full rounded-xl border bg-white px-3 py-2.5 text-left transition-colors hover:border-blu ${sel === p.id ? 'border-blu' : 'border-bordo'}`}>
        <span className="flex items-center gap-2">
          <span className="min-w-0 flex-1 truncate text-[14px] font-bold text-inchiostro">{nomeDi(p)}</span>
          {conTappa && <span className="shrink-0 text-[10.5px] font-semibold uppercase tracking-[0.05em] text-spento">{NOME_TAPPA[tappaDi(p)]}</span>}
        </span>
        <span className="mt-1 flex items-start gap-1.5 text-[12.5px] leading-snug text-tenue">
          <span className={`mt-[5px] h-1.5 w-1.5 shrink-0 rounded-full ${PUNTO[r.tono]}`} />
          <span className={`line-clamp-2 ${r.tono === 'nostra' ? 'font-semibold text-red-700' : ''}`}>{r.testo}</span>
        </span>
      </button>
    )
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {([['cammino', 'In cammino', insiemi.cammino.length], ['clienti', 'Clienti', insiemi.clienti.length], ['persi', 'Persi', insiemi.persi.length], ['scartati', 'Scartati', insiemi.scartati.length]] as Array<[Vista, string, number]>).map(([k, n, c]) => (
          <button key={k} onClick={() => setVista(k)}
                  className={`rounded-full px-3 py-1.5 text-[13px] font-semibold ${vista === k ? 'bg-navy text-white' : 'text-tenue hover:text-navy'}`}>
            {n} <span className="tabular-nums opacity-70">{c}</span>
          </button>
        ))}
        <span className="mx-1 hidden h-5 w-px bg-bordo sm:block" />
        {vista === 'cammino' && (
          <button onClick={() => setMie((m) => !m)}
                  className={`rounded-full border px-3 py-1.5 text-[13px] font-semibold ${mie ? 'border-red-600 bg-red-50 text-red-700' : 'border-bordo text-tenue hover:border-navy hover:text-navy'}`}>
            Tocca a te <span className="tabular-nums">{nostre}</span>
          </button>
        )}
        <input value={cerca} onChange={(e) => setCerca(e.target.value)} placeholder="Cerca un'azienda"
               className="ml-auto w-full rounded-full border border-bordo bg-white px-4 py-1.5 text-sm outline-none focus:border-blu sm:w-56" />
      </div>

      {vista === 'cammino' ? (
        <div className="-mx-4 flex snap-x gap-3 overflow-x-auto px-4 pb-4 lg:mx-0 lg:grid lg:grid-cols-5 lg:overflow-visible lg:px-0">
          {COLONNE.map(([k, nome]) => {
            const dentro = ordina(visibili.filter((p) => (k === 'lead' ? PRIMA_DELLA_CALL.includes(tappaDi(p)) : tappaDi(p) === k)))
            return (
              <section key={k} onDragOver={(e) => { e.preventDefault(); setSopra(k) }} onDragLeave={() => setSopra(null)}
                       onDrop={(e) => { e.preventDefault(); setSopra(null); const p = righe.find((x) => x.id === e.dataTransfer.getData('text/plain')); if (p) void verso(p, k) }}
                       className={`w-[82vw] shrink-0 snap-start rounded-2xl p-2 sm:w-72 lg:w-auto ${sopra === k ? 'bg-blu/10' : 'bg-velo/60'}`}>
                <h2 className="flex items-center justify-between px-1.5 pb-2 pt-1 text-[11px] font-bold uppercase tracking-[0.06em] text-navy">
                  {nome}<span className="tabular-nums text-tenue">{dentro.length}</span>
                </h2>
                {dentro.length === 0 ? <p className="px-1.5 py-2 text-xs text-spento">Nessuno</p> : k !== 'lead' ? (
                  <div className="space-y-2">{dentro.map((p) => carta(p, false))}</div>
                ) : PRIMA_DELLA_CALL.map((g) => {
                  const del = dentro.filter((p) => tappaDi(p) === g)
                  return del.length === 0 ? null : (
                    <div key={g} className="mb-3">
                      <p className="px-1.5 pb-1.5 text-[10.5px] font-semibold uppercase tracking-[0.05em] text-spento">{NOME_TAPPA[g]} {del.length}</p>
                      <div className="space-y-2">{del.map((p) => carta(p, false))}</div>
                    </div>
                  )
                })}
              </section>
            )
          })}
        </div>
      ) : (
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {insiemi[vista].length === 0 ? <p className="text-sm text-spento">Nessuno</p> : ordina(insiemi[vista]).map((p) => carta(p, true))}
        </div>
      )}

      {aperta && (
        <Pannello key={aperta.id} p={aperta} bozze={bozze.get(aperta.id) ?? 0} onChiudi={() => setSel(null)}
                  onEsegui={esegui} onIndietro={(v) => setConferma({ p: aperta, verso: v })}
                  onCambiato={(x) => setRighe((rs) => (rs ?? []).map((y) => (y.id === x.id ? x : y)))}
                  onScheda={() => { setSel(null); onScheda(aperta.id) }} />
      )}

      {conferma && (
        <div className="fixed inset-0 z-[90] flex items-end justify-center bg-black/20 p-4 sm:items-center" onClick={() => setConferma(null)}>
          <div className="w-full max-w-sm rounded-2xl bg-white p-5" onClick={(e) => e.stopPropagation()}>
            <p className="text-[15px] font-bold text-inchiostro">
              {nomeDi(conferma.p)} torna {conferma.verso === 'lead' ? 'fra i lead' : `in ${NOME_TAPPA[conferma.verso]}`}?
            </p>
            <p className="mt-1 text-sm text-tenue">Resta scritto nella storia.</p>
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setConferma(null)} className="rounded-full px-4 py-2 text-sm font-semibold text-tenue hover:text-navy">Annulla</button>
              <button onClick={() => { const c = conferma; setConferma(null); void esegui(c.p, c.verso) }}
                      className="rounded-full bg-blu px-4 py-2 text-sm font-bold text-white">Torna indietro</button>
            </div>
          </div>
        </div>
      )}

      {avviso && (
        <div className="fixed bottom-24 left-1/2 z-[95] -translate-x-1/2 rounded-full bg-navy px-4 py-2 text-sm font-semibold text-white shadow-[0_6px_20px_rgba(16,24,40,0.2)] lg:bottom-8">
          {avviso}
        </div>
      )}
    </div>
  )
}
