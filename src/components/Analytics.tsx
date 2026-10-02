import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import type { Prospect, Interaction } from '../lib/types'
import { vivo, eCliente, ricorrenteMensile, ultimoMovimento } from '../lib/regole'

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
  const [attese, setAttese] = useState<Array<{ id: string; company: string | null; name: string | null; email: string; last_reply_at: string | null }> | null>(null)
  const [lane, setLane] = useState<Map<string, string>>(new Map())
  const [conoscitive, setConoscitive] = useState<Array<{ prospect_id: string | null; at: string; creato_il: string | null }> | null>(null)

  // il sommario per canale: i numeri li conta il database, non una lista
  // troncata. Oggi il sistema conosce solo l'Email (Smartlead): le altre
  // righe restano da collegare invece di essere inventate (Dre, 3/9)
  useEffect(() => { ricorrenteMensile().then(setRicorrente) }, [])

  // IL POLSO DELLE RISPOSTE (Dre, 2/10: «vorrei essere tranquillo che entro un certo
  // orario riceveranno la risposta, e guardarlo io per capire quando ci sono problemi»).
  // La promessa: nella finestra (lun-ven 9-17) una consegna semplice parte entro un'ora;
  // fuori finestra, entro le 10 del giorno lavorativo dopo. Qui si vede chi aspetta ADESSO
  // e da quanto, divisi fra corsia automatica e casi tuoi. Il rosso = promessa in ritardo.
  useEffect(() => {
    void (async () => {
      const [att, pr] = await Promise.all([
        supabase.from('prospects').select('id,company,name,email,last_reply_at').eq('awaiting_us', true).eq('fuori', false)
          .or('classificazione.is.null,classificazione.not.in.(negativo,fuori_target,soppresso,nervoso)').limit(200),
        supabase.from('proposte').select('prospect_id,stato,azione').in('stato', ['aperta', 'approvata', 'in_invio']).limit(500),
      ])
      setAttese((att.data as never) ?? [])
      const m = new Map<string, string>()
      const AUTOMATICI = ['INT-01', 'INT-02', 'INT-03', 'INT-23', 'INT-GB']
      for (const x of (pr.data ?? []) as Array<{ prospect_id: string | null; azione: { intento?: string } | null }>) {
        if (x.prospect_id) m.set(x.prospect_id, AUTOMATICI.includes(x.azione?.intento ?? '') ? 'corsia' : 'tua')
      }
      setLane(m)
    })()
  }, [])

  // le prenotazioni (Dre, 1/10): le conoscitive del calendario incrociate coi lead
  useEffect(() => {
    supabase.from('agenda').select('prospect_id,at,creato_il').eq('tipo', 'conoscitiva').eq('fonte', 'gcal').limit(1000)
      .then(({ data }) => setConoscitive((data as Array<{ prospect_id: string | null; at: string; creato_il: string | null }>) ?? []))
  }, [])

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
  // fuori_at e' la data di INGRESSO in pipeline, non quella della firma:
  // finche' non c'e' una data di conversione, la riga dice quello che sa
  const entratiNuovi30 = vivi.filter((p) => p.fuori_at && new Date(p.fuori_at).getTime() >= t30).length
  const fermi = dentro
    .filter((p) => ['analisi_inviata', 'in_follow_up'].includes(p.stage) && !p.awaiting_us)
    .map((p) => ({ p, gg: daysAgo(ultimoMovimento(p)) ?? 0 }))
    .filter((x) => x.gg >= 30)
    .sort((a, b) => b.gg - a.gg)

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

  // ── il tasso di prenotazione (Dre, 1/10: «incrociamo le prenotazioni coi lead») ──
  // Chi ha ricevuto l'analisi negli ultimi 30 giorni, e fra questi chi ha POI
  // prenotato una conoscitiva dal calendario. Le prenotazioni senza aggancio
  // all'azienda si dicono: il tasso vero puo' essere piu' alto, non si inventa.
  const pren = (() => {
    const t30 = Date.now() - 30 * 86400e3
    const prenotazioniDi = new Map<string, string[]>()
    for (const a of conoscitive ?? []) {
      if (a.prospect_id) {
        const q = prenotazioniDi.get(a.prospect_id) ?? []
        q.push(a.creato_il ?? a.at)
        prenotazioniDi.set(a.prospect_id, q)
      }
    }
    const coorte = (prospects ?? []).filter((p) => p.analysis_sent_at && new Date(p.analysis_sent_at).getTime() >= t30)
    const giorni: number[] = []
    let prenotate = 0
    for (const p of coorte) {
      const dopo = (prenotazioniDi.get(p.id) ?? []).filter((q) => q >= p.analysis_sent_at!)
      if (dopo.length) {
        prenotate += 1
        const g = (new Date(dopo.sort()[0]).getTime() - new Date(p.analysis_sent_at!).getTime()) / 86400e3
        if (g >= 0 && g < 60) giorni.push(Math.round(g))
      }
    }
    const orfane = (conoscitive ?? []).filter((a) => !a.prospect_id && new Date(a.at).getTime() >= t30).length
    giorni.sort((a, b) => a - b)
    return { analisi: coorte.length, prenotate, orfane, mediana: giorni.length ? giorni[Math.floor(giorni.length / 2)] : null }
  })()

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

  // ── QUESTO MESE CONTRO LO SCORSO (Dre, 16/9) ───────────────────────
  // «Numeri non lo guardera' nessuno finche' non risponde a una domanda».
  // La domanda di un manager e' una sola: stiamo andando meglio o peggio?
  // Quindi la prima riga e' il confronto, e il resto sta sotto.
  // il 17 del mese si confronta con i primi 17 giorni del mese scorso,
  // non con tutto il mese scorso: se no fino al 28 si perde sempre.
  // Le date si leggono in ora locale, come le vede chi guarda.
  const ora = new Date()
  const meseOra = { anno: ora.getFullYear(), mese: ora.getMonth() }
  const prima = new Date(ora.getFullYear(), ora.getMonth() - 1, 1)
  const meseScorso = { anno: prima.getFullYear(), mese: prima.getMonth() }
  const giornoOggi = ora.getDate()
  type Quale = { anno: number; mese: number }
  const nelMese = (iso: string | null | undefined, q: Quale) => {
    if (!iso) return false
    const d = new Date(iso)
    return d.getFullYear() === q.anno && d.getMonth() === q.mese && d.getDate() <= giornoOggi
  }
  const conta = (quale: Quale, filtro: (i: Interaction) => boolean) =>
    (storia ?? []).filter((i) => nelMese(i.at, quale) && filtro(i)).length
  const clientiDi = (quale: Quale) =>
    (prospects ?? []).filter((x) => eCliente(x) && nelMese(x.fuori_at, quale)).length

  const CONFRONTO: Array<[string, number, number]> = [
    ['Risposte arrivate', conta(meseOra, (i) => i.kind === 'email_in'), conta(meseScorso, (i) => i.kind === 'email_in')],
    ['Analisi mandate', conta(meseOra, (i) => i.kind === 'analisi'), conta(meseScorso, (i) => i.kind === 'analisi')],
    ['Call fatte', conta(meseOra, (i) => i.kind === 'transcript' || i.kind === 'call'), conta(meseScorso, (i) => i.kind === 'transcript' || i.kind === 'call')],
    ['Clienti nuovi', clientiDi(meseOra), clientiDi(meseScorso)],
  ]

  return (
    <div className="space-y-4 pb-36 sm:pb-8">

      {/* la prima cosa che si legge: come stiamo andando */}
      <Card>
        <header className="flex items-baseline justify-between gap-2 border-b border-velo px-4 py-3">
          <TitoloCard>Questo mese</TitoloCard>
          <Micro>fino a oggi, contro gli stessi giorni del mese scorso</Micro>
        </header>
        <div className="grid grid-cols-2 divide-x divide-velo sm:grid-cols-4">
          {CONFRONTO.map(([nome, ora, prima]) => {
            const delta = ora - prima
            return (
              <div key={nome} className="px-4 py-3">
                <p className="text-[26px] font-extrabold leading-none tabular-nums">{fmtNum(ora)}</p>
                <p className="mt-1 text-[11px] font-bold uppercase tracking-[0.06em] text-navy/70">{nome}</p>
                <p className={`mt-1 text-xs font-semibold ${delta > 0 ? 'text-green-800' : delta < 0 ? 'text-red-700' : 'text-spento'}`}>
                  {delta === 0 ? 'come il mese scorso' : `${delta > 0 ? '+' : ''}${delta} su ${fmtNum(prima)}`}
                </p>
              </div>
            )
          })}
        </div>
      </Card>

      {tagliato && (
        <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900">
          Numeri sulle prime 1.000 aziende e 2.000 interazioni: il totale vero è più alto.
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
                  <th key={h} className={`px-4 py-2 text-[11px] font-bold uppercase tracking-wide text-navy/70 ${i > 0 ? 'text-right' : ''}`}>
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
                    non passa ancora da SG Workspace
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* ── LA FOTO: quello che c'e' adesso, non quello che si e' mosso ── */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-2">
        {/* il ricorrente e i clienti li conta regole.ts, non questa lista:
            e' lo stesso numero che vedi in Tutti e in bacheca (4/9) */}
        <Foto etichetta="Ricorrente / mese" valore={ricorrente ? `${fmtNum(ricorrente.mese)} €` : '…'}
          confronto={entratiNuovi30 > 0 ? `+${entratiNuovi30} entrati in pipeline nel mese` : ''} />
        <Foto etichetta="Clienti" valore={ricorrente ? fmtNum(ricorrente.quanti) : '…'}
          confronto={entratiNuovi30 > 0 ? `+${entratiNuovi30} entrati in pipeline nel mese` : ''} />
      </div>

      {/* ── 1, il battito ──────────────────────────────────── */}
      <Card className="p-5">
        <TitoloCard>Il polso delle risposte, adesso</TitoloCard>
        {(() => {
          const ora = new Date()
          const inFinestra = ora.getDay() >= 1 && ora.getDay() <= 5 && ora.getHours() >= 9 && ora.getHours() < 17
          const righe = (attese ?? []).map((p) => {
            const min = p.last_reply_at ? Math.round((Date.now() - new Date(p.last_reply_at).getTime()) / 60000) : null
            const corsia = lane.get(p.id) ?? 'lavorazione'
            const tardi = corsia === 'corsia' && inFinestra && (min ?? 0) > 60
            return { nome: p.company || p.name || p.email, min, corsia, tardi }
          })
          const inCorsia = righe.filter((r) => r.corsia === 'corsia').length
          const tue = righe.filter((r) => r.corsia === 'tua').length
          const rosse = righe.filter((r) => r.tardi)
          return (
            <>
              <p className="text-sm font-semibold">
                {righe.length} in attesa adesso: {inCorsia} in corsia automatica, {tue} da te, {righe.length - inCorsia - tue} in lavorazione
                {rosse.length > 0
                  ? <span className="ml-2 rounded-full bg-red-600 px-2.5 py-0.5 text-xs font-bold text-white tabular-nums">{rosse.length} oltre l'ora</span>
                  : <span className="ml-2 rounded-full bg-green-600 px-2.5 py-0.5 text-xs font-bold text-white">promessa tenuta</span>}
              </p>
              <p className="mt-1.5 text-[13px] text-tenue">
                La promessa: lun-ven 9-17 la consegna semplice parte entro un'ora; fuori orario, entro le 10 del giorno dopo. I casi da te non hanno orologio: sono conversazioni.
              </p>
              {rosse.length > 0 && (
                <ul className="mt-2 space-y-0.5 text-[13px]">
                  {rosse.slice(0, 5).map((r) => (
                    <li key={r.nome as string} className="font-semibold text-red-700">{r.nome}: in corsia da {Math.round((r.min ?? 0) / 60)}h {(r.min ?? 0) % 60}m</li>
                  ))}
                </ul>
              )}
            </>
          )
        })()}
      </Card>

      <Card className="p-5">
        <TitoloCard>Prenotazioni, ultimi 30 giorni</TitoloCard>
        <p className="text-sm font-semibold">
          {pren.analisi} analisi mandate, {pren.prenotate} {pren.prenotate === 1 ? 'ha prenotato' : 'hanno prenotato'} la conoscitiva
          <span className="ml-2 rounded-full bg-navy px-2.5 py-0.5 text-xs font-bold text-white tabular-nums">
            {pren.analisi ? Math.round((pren.prenotate / pren.analisi) * 100) : 0}%
          </span>
        </p>
        <p className="mt-1.5 text-[13px] text-tenue">
          {pren.mediana != null && <>Dall'analisi alla prenotazione: {pren.mediana === 0 ? 'stesso giorno' : `${pren.mediana} giorni`} (mediana). </>}
          {pren.orfane > 0 && <span className="text-amber-700">{pren.orfane} conoscitive non agganciate a un'azienda: il tasso vero può essere più alto.</span>}
        </p>
      </Card>

      <Card className="p-5">
        <TitoloCard>Battito, ultime {SETTIMANE} settimane</TitoloCard>
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

      {/* ── 2, il funnel coi tassi ─────────────────────────── */}
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

      {/* ── 3, la velocita' e i fermi ───────────────────────── */}
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

      {/* ── 4, le campagne a confronto ─────────────────────── */}
      {campagne.length > 0 && (
        <Card className="p-5">
          <TitoloCard>Campagne</TitoloCard>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] font-bold uppercase tracking-wide text-navy/70">
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
      <p className="text-[11px] font-bold uppercase tracking-[0.05em] text-navy/70">{etichetta}</p>
      <p className={`mt-0.5 text-xl font-extrabold ${allarme ? 'text-red-700' : ''}`}>{valore}</p>
      {confronto && <p className="mt-0.5 text-[11px] text-tenue">{confronto}</p>}
    </div>
  )
}
