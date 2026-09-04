import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import type { Prospect, Interaction } from '../lib/types'
import { vivo, eCliente, ricorrenteMensile } from '../lib/regole'

// giusto i pezzi di catena che servono qui
interface Filtro {
  eq(c: string, v: unknown): Filtro
  neq(c: string, v: unknown): Filtro
  not(c: string, o: string, v: unknown): Filtro
  or(s: string): Filtro
}
import { Card, TitoloCard, fmtNum, daysAgo, giorni, Micro } from './ui'

// Analytics: la FOTO in alto (i numeri col confronto), sotto il PERCHE'
// in 4 blocchi. Ogni grafico ha sopra una frase-verdetto in italiano.
// Regole scritte qui perche' restino: periodi fissi (8 settimane, 30 giorni),
// niente selettori, niente metriche di volume email (stanno su Smartlead),
// niente torte, mai piu' di 4 blocchi.

interface Props {
  onOpen: (id: string) => void
}

const SETTIMANE = 8

function inizioSettimana(offset: number): Date {
  const d = new Date()
  const lun = new Date(d.getFullYear(), d.getMonth(), d.getDate() - ((d.getDay() + 6) % 7) - offset * 7)
  return lun
}

export default function Analytics({ onOpen }: Props) {
  const [canale, setCanale] = useState<Record<string, number> | null>(null)
  const [prospects, setProspects] = useState<Prospect[] | null>(null)
  const [ricorrente, setRicorrente] = useState<{ mese: number; quanti: number } | null>(null)
  const [storia, setStoria] = useState<Interaction[] | null>(null)

  // il sommario per canale: i numeri li conta il database, non una lista
  // troncata. Oggi il sistema conosce solo l'Email (Smartlead): le altre
  // righe restano da collegare invece di essere inventate (Dre, 3/9)
  useEffect(() => { ricorrenteMensile().then(setRicorrente) }, [])

  useEffect(() => {
    const conta = (domanda: (f: Filtro) => Filtro) =>
      domanda(supabase.from('prospects')
        .select('*', { count: 'exact', head: true }) as unknown as Filtro) as unknown as Promise<{ count: number | null }>
    Promise.all([
      conta((f) => f),   // lead = tutti i contattati, se no il tasso supera il 100%
      conta((f) => f.not('first_reply_at', 'is', null)),
      conta((f) => f.or('fuori.eq.true,stage.eq.call_fissata')),
      conta((f) => f.eq('fuori', true).not('pipeline_stage', 'is', null)),
    ]).then(([lead, risposte, fissate, fatte]) => {
      setCanale({
        lead: lead.count ?? 0,
        risposte: risposte.count ?? 0,
        fissate: fissate.count ?? 0,
        fatte: fatte.count ?? 0,
      })
    })
  }, [])

  useEffect(() => {
    supabase
      .from('prospects')
      .select('*')
      .neq('stage', 'nuovo')
      .order('last_reply_at', { ascending: false, nullsFirst: false })
      .limit(1000)
      .then(({ data }) => setProspects((data as Prospect[]) ?? []))

    supabase
      .from('interactions')
      .select('*')
      .gte('at', inizioSettimana(SETTIMANE - 1).toISOString())
      .order('at', { ascending: false })
      .limit(2000)
      .then(({ data }) => setStoria((data as Interaction[]) ?? []))
  }, [])

  if (prospects === null || storia === null) return null

  // se le liste arrivano piene, i conti sotto sono su un pezzo del totale:
  // meglio dirlo che dare per buoni numeri piu' bassi del vero
  const tagliato = prospects.length >= 1000 || storia.length >= 2000
  const vivi = prospects.filter(vivo)
  const dentro = vivi.filter((p) => !p.fuori)
  const clienti = vivi.filter(eCliente)   // stessa regola di Tutti e della bacheca

  // ── la FOTO: numeri col confronto sui 30 giorni ───────────────
  const t30 = Date.now() - 30 * 86400e3
  const t60 = Date.now() - 60 * 86400e3
  const nel = (kind: Interaction['kind'], da: number, a: number) =>
    storia.filter((i) => i.kind === kind && new Date(i.at).getTime() >= da && new Date(i.at).getTime() < a).length
  const risposte30 = nel('email_in', t30, Date.now())
  const rispostePrec = nel('email_in', t60, t30)
  const call30 = nel('transcript', t30, Date.now()) + nel('call', t30, Date.now())
  const callPrec = nel('transcript', t60, t30) + nel('call', t60, t30)
  // fuori_at e' la data di INGRESSO in pipeline, non quella della firma:
  // finche' non c'e' una data di conversione, la riga dice quello che sa
  const entratiNuovi30 = vivi.filter((p) => p.fuori_at && new Date(p.fuori_at).getTime() >= t30).length
  const fermi = dentro
    .filter((p) => ['analisi_inviata', 'in_follow_up'].includes(p.stage) && !p.awaiting_us)
    .map((p) => ({ p, gg: daysAgo(p.analysis_sent_at) ?? 0 }))
    .filter((x) => x.gg >= 30)
    .sort((a, b) => b.gg - a.gg)

  const delta = (ora: number, prima: number) =>
    ora === prima ? '=' : ora > prima ? `+${ora - prima}` : `${ora - prima}`

  // ── blocco 1: il battito (8 settimane) ────────────────────────
  const battito = ['email_in', 'analisi', 'transcript'].map((kind) => {
    const serie = Array.from({ length: SETTIMANE }, (_, i) => {
      const da = inizioSettimana(SETTIMANE - 1 - i).getTime()
      const a = da + 7 * 86400e3
      return storia.filter((x) => x.kind === kind && new Date(x.at).getTime() >= da && new Date(x.at).getTime() < a).length
    })
    return { kind, serie, media: serie.reduce((s, n) => s + n, 0) / SETTIMANE }
  })
  const [risposteW, analisiW, callW] = battito
  const ultimaW = risposteW.serie[SETTIMANE - 1]
  const verdettoBattito =
    ultimaW > risposteW.media ? `Questa settimana ${ultimaW} risposte, sopra la media delle ultime ${SETTIMANE}.`
    : ultimaW === 0 ? 'Questa settimana ancora zero risposte: le campagne sono il rubinetto.'
    : `Questa settimana ${ultimaW} rispost${ultimaW === 1 ? 'a' : 'e'}, sotto la media delle ultime ${SETTIMANE} settimane.`

  // ── blocco 2: il funnel coi tassi ─────────────────────────────
  const conAnalisi = vivi.filter((p) => p.analysis_sent).length
  const inCall = vivi.filter((p) => p.fuori).length
  const passi: Array<[string, number, number]> = [
    ['Hanno risposto', vivi.length, 100],
    ['Analisi ricevuta', conAnalisi, vivi.length ? Math.round((conAnalisi / vivi.length) * 100) : 0],
    ['Arrivano in call', inCall, conAnalisi ? Math.round((inCall / conAnalisi) * 100) : 0],
    ['Diventano clienti', clienti.length, inCall ? Math.round((clienti.length / inCall) * 100) : 0],
  ]
  const peggiore = passi.slice(1).reduce((min, x) => (x[2] < min[2] ? x : min), passi[1])
  const maxFunnel = Math.max(vivi.length, 1)

  // ── blocco 3: la velocita' ────────────────────────────────────
  const medie: Array<[string, number | null]> = (() => {
    const diffMedia = (coppie: Array<[string | null, string | null]>) => {
      const gg = coppie
        .filter(([a, b]) => a && b)
        .map(([a, b]) => (new Date(b!).getTime() - new Date(a!).getTime()) / 86400e3)
        .filter((n) => n >= 0 && n < 120)
      return gg.length ? Math.round(gg.reduce((s, n) => s + n, 0) / gg.length) : null
    }
    return [
      ['dalla risposta all\'analisi', diffMedia(vivi.map((p) => [p.first_reply_at ?? p.last_reply_at, p.analysis_sent_at]))],
      ['dall\'analisi alla call', diffMedia(vivi.filter((p) => p.fuori).map((p) => [p.analysis_sent_at, p.fuori_at]))],
    ]
  })()

  // ── blocco 4: le campagne ─────────────────────────────────────
  const campagne = [...new Set(vivi.map((p) => p.campaign).filter(Boolean))].map((c) => {
    const del = vivi.filter((p) => p.campaign === c)
    return {
      nome: c as string,
      risposte: del.length,
      analisi: del.filter((p) => p.analysis_sent).length,
      call: del.filter((p) => p.fuori).length,
      clienti: del.filter(eCliente).length,
    }
  }).sort((a, b) => b.call - a.call)

  return (
    <div className="space-y-4 pb-24 sm:pb-8">

      {tagliato && (
        <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900">
          Numeri sui primi 1.000 prospect e 2.000 interazioni: il totale vero è più alto.
        </p>
      )}

      {/* ── PER CANALE: il sommario che Giacomo riempiva a mano ── */}
      <Card>
        <header className="flex items-baseline justify-between gap-2 border-b border-velo px-4 py-3">
          <TitoloCard>Per canale</TitoloCard>
          <Micro>da quando esiste il database</Micro>
        </header>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm">
            <thead>
              <tr className="border-b border-velo text-left">
                {['Canale', 'Lead', 'Risposte', '% reply', 'Call fissate', 'Call fatte'].map((h, i) => (
                  <th key={h} className={`px-4 py-2 text-[11px] font-bold uppercase tracking-wide text-spento ${i > 0 ? 'text-right' : ''}`}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-velo">
                <td className="px-4 py-2.5 font-semibold">Email</td>
                <td className="px-4 py-2.5 text-right tabular-nums">{canale ? fmtNum(canale.lead) : '…'}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">{canale ? fmtNum(canale.risposte) : '…'}</td>
                <td className="px-4 py-2.5 text-right font-bold tabular-nums">
                  {canale && canale.lead > 0 ? `${((canale.risposte / canale.lead) * 100).toFixed(1)}%` : '…'}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums">{canale ? fmtNum(canale.fissate) : '…'}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">{canale ? fmtNum(canale.fatte) : '…'}</td>
              </tr>
              {['LinkedIn', 'Instagram', 'Referral', 'Altro'].map((c) => (
                <tr key={c} className="border-b border-velo last:border-0">
                  <td className="px-4 py-2.5 font-semibold text-spento">{c}</td>
                  <td colSpan={5} className="px-4 py-2.5 text-right text-xs text-spento">
                    non passa ancora dalla Dashboard
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* ── LA FOTO ─────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {/* il ricorrente e i clienti li conta regole.ts, non questa lista:
            e' lo stesso numero che vedi in Tutti e in bacheca (4/9) */}
        <Foto etichetta="Ricorrente / mese" valore={ricorrente ? `${fmtNum(ricorrente.mese)} €` : '…'}
          confronto={entratiNuovi30 > 0 ? `+${entratiNuovi30} entrati in pipeline nel mese` : ''} />
        <Foto etichetta="Clienti" valore={ricorrente ? fmtNum(ricorrente.quanti) : '…'}
          confronto={entratiNuovi30 > 0 ? `+${entratiNuovi30} entrati in pipeline nel mese` : ''} />
        <Foto etichetta="Risposte 30 giorni" valore={fmtNum(risposte30)}
          confronto={`${delta(risposte30, rispostePrec)} sul mese prima`} />
        <Foto etichetta="Call 30 giorni" valore={fmtNum(call30)}
          confronto={`${delta(call30, callPrec)} sul mese prima`} />
      </div>

      {/* ── 1 · il battito ──────────────────────────────────── */}
      <Card className="p-5">
        <TitoloCard>Battito · ultime {SETTIMANE} settimane</TitoloCard>
        <p className="mb-4 text-sm font-semibold">{verdettoBattito}</p>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
          {[
            ['Risposte', risposteW], ['Analisi inviate', analisiW], ['Call fatte', callW],
          ].map(([nome, b]) => {
            const box = b as typeof risposteW
            const max = Math.max(...box.serie, 1)
            return (
              <div key={nome as string}>
                <p className="mb-1.5 text-xs font-semibold text-tenue">{nome as string}</p>
                <div className="relative flex h-16 items-end gap-1">
                  <div
                    className="absolute inset-x-0 border-t border-dashed border-spento/50"
                    style={{ bottom: `${(box.media / max) * 100}%` }}
                    title={`media: ${box.media.toFixed(1)}`}
                  />
                  {box.serie.map((n, i) => (
                    <div
                      key={i}
                      className={`flex-1 rounded-t ${i === SETTIMANE - 1 ? 'bg-navy' : 'bg-navy/30'}`}
                      style={{ height: `${Math.max((n / max) * 100, n > 0 ? 6 : 2)}%` }}
                      title={`${n}`}
                    />
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </Card>

      {/* ── 2 · il funnel coi tassi ─────────────────────────── */}
      <Card className="p-5">
        <TitoloCard>Funnel</TitoloCard>
        <p className="mb-4 text-sm font-semibold">
          Il passaggio più duro: «{peggiore[0]}» ({peggiore[2]}%): qui si perde di più.
        </p>
        <div className="space-y-2.5">
          {passi.map(([nome, n, tasso], i) => (
            <div key={nome} className="flex items-center gap-3" title={`${nome}: ${n}`}>
              <span className="w-32 shrink-0 text-xs font-semibold text-tenue">{nome}</span>
              <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-velo">
                <div
                  className={`h-full rounded-full ${nome === peggiore[0] ? 'bg-amber-500' : 'bg-navy'}`}
                  style={{ width: `${Math.max((n / maxFunnel) * 100, n > 0 ? 3 : 0)}%` }}
                />
              </div>
              <span className="w-8 shrink-0 text-right text-sm font-bold">{n}</span>
              <span className="w-12 shrink-0 text-right text-[11px] text-spento">
                {i === 0 ? '' : `${tasso}%`}
              </span>
            </div>
          ))}
        </div>
      </Card>

      {/* ── 3 · la velocita' e i fermi ───────────────────────── */}
      <Card className="p-5">
        <TitoloCard>Velocità</TitoloCard>
        <div className="mb-4 grid grid-cols-2 gap-3">
          {medie.map(([nome, gg]) => (
            <div key={nome}>
              <p className="text-xl font-extrabold">{gg === null ? '—' : giorni(gg)}</p>
              <p className="text-xs text-tenue">in media, {nome}</p>
            </div>
          ))}
        </div>
        {fermi.length > 0 && (
          <>
            <p className="mb-2 text-sm font-semibold">Fermi da più tempo</p>
            <div className="divide-y divide-velo">
              {fermi.slice(0, 5).map(({ p, gg }) => (
                <button
                  key={p.id}
                  onClick={() => onOpen(p.id)}
                  className="flex w-full items-center justify-between gap-3 py-2 text-left hover:bg-velo/40"
                >
                  <span className="truncate text-sm font-semibold">{p.company || p.name || p.email}</span>
                  <span className="shrink-0 text-xs font-bold text-red-700">fermo da {giorni(gg)}</span>
                </button>
              ))}
            </div>
          </>
        )}
      </Card>

      {/* ── 4 · le campagne a confronto ─────────────────────── */}
      {campagne.length > 0 && (
        <Card className="p-5">
          <TitoloCard>Campagne</TitoloCard>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] font-bold uppercase tracking-wide text-spento">
                  <th className="pb-2 pr-3">Campagna</th>
                  <th className="pb-2 pr-3 text-right">Risposte</th>
                  <th className="pb-2 pr-3 text-right">Analisi</th>
                  <th className="pb-2 pr-3 text-right">Call</th>
                  <th className="pb-2 text-right">Clienti</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-velo">
                {campagne.map((c) => (
                  <tr key={c.nome}>
                    <td className="py-2 pr-3 font-semibold">{c.nome}</td>
                    <td className="py-2 pr-3 text-right">{c.risposte}</td>
                    <td className="py-2 pr-3 text-right">{c.analisi}</td>
                    <td className="py-2 pr-3 text-right font-bold">{c.call}</td>
                    <td className="py-2 text-right font-bold text-green-700">{c.clienti}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}

function Foto({ etichetta, valore, confronto, allarme }: {
  etichetta: string
  valore: string
  confronto: string
  allarme?: boolean
}) {
  return (
    <div className="rounded-2xl border border-bordo bg-white p-4 shadow-[0_1px_2px_rgba(16,24,40,0.03),0_4px_16px_rgba(16,24,40,0.04)]">
      <p className="text-[11px] font-bold uppercase tracking-[0.05em] text-spento">{etichetta}</p>
      <p className={`mt-0.5 text-xl font-extrabold ${allarme ? 'text-red-700' : ''}`}>{valore}</p>
      {confronto && <p className="mt-0.5 text-[11px] text-tenue">{confronto}</p>}
    </div>
  )
}
