import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { leggi as leggiPref, scrivi as scriviPref } from '../lib/preferenze'
import type { Prospect } from '../lib/types'
import { eCliente, ePerso, giorno } from '../lib/regole'
import { Card, Spinner, Cella, sgid, fmtDateShort, Faccia } from './ui'

// TUTTI COME IL FOGLIO DI GIACOMO (Dre, 9/9): i nomi in fila, lo stato in
// un selettore (Prospect / Preventivo inviato / Cliente / Perso), chi lo
// segue, il canone, l'ultimo preventivo e le note. Il «€» sulla riga apre i
// preventivi di quell'azienda: importo, data, stato, e «pagamento arrivato»
// che spunta Giacomo a mano. Tutto appeso all'SG-ID.

export type { Preventivo } from '../lib/preventivo'
import type { Preventivo } from '../lib/preventivo'

type Riga = Prospect & { chi_segue?: string | null; notes?: string | null }
type StatoFoglio = 'prospect' | 'preventivo' | 'prova' | 'cliente' | 'perso'
type Filtro = 'clienti' | 'prospect' | 'tutti'

export const STATI_FOGLIO: Array<[StatoFoglio, string, string]> = [
  ['prospect', 'Prospect', 'bg-amber-50 text-amber-900'],
  ['preventivo', 'Preventivo inviato', 'bg-sky-100 text-sky-900'],
  ['prova', 'In prova', 'bg-teal-100 text-teal-900'],
  ['cliente', 'Cliente', 'bg-green-100 text-green-900'],
  ['perso', 'Perso', 'bg-velo text-spento'],
]

export { STATI as STATI_PREVENTIVO } from '../lib/preventivo'
import { STATI as STATI_PREVENTIVO } from '../lib/preventivo'

// lo stato che si vede nel foglio: una lettura sola, da regole.ts + preventivi
export function statoFoglio(p: Riga, suoi: Preventivo[]): StatoFoglio {
  if (eCliente(p)) return 'cliente'
  if (ePerso(p)) return 'perso'
  if (p.fuori && p.pipeline_stage === 'prova') return 'prova'
  if (suoi.some((q) => q.stato === 'inviato')) return 'preventivo'
  return 'prospect'
}

export function euro(n: number | null | undefined): string {
  return n == null ? '—' : `${Number(n).toLocaleString('it-IT')} €`
}

interface Props { onOpen: (id: string) => void }

// IL BLOCCO PAGAMENTI (Dre, 10/9): sulla riga del cliente come paga, quanto al
// mese, prossimo addebito; in cima il mese. Viene da `incassi` (Stripe, letto
// da Clara ogni ora). Chi non e' ceo non riceve le righe: il blocco sparisce.
export interface Incasso {
  id: string
  genere: 'addebito' | 'fattura' | 'abbonamento'
  importo: number
  valuta: string
  stato: string | null
  quando: string | null
  ricorrenza: string | null
  metodo: string | null
  prossimo_il: string | null
  fine_il: string | null
  cliente_nome: string | null
  prospect_id: string | null
}
const METODO: Record<string, string> = { sepa: 'SEPA', carta: 'carta', bonifico: 'bonifico', altro: 'altro' }
const ATTIVO = new Set(['active', 'trialing', 'past_due', 'unpaid'])
export function mensile(i: Incasso) { return i.ricorrenza === 'year' ? i.importo / 12 : i.importo }

export default function TuttiFoglio({ onOpen }: Props) {
  const [righe, setRighe] = useState<Riga[] | null>(null)
  const [preventivi, setPreventivi] = useState<Preventivo[]>([])
  const [incassi, setIncassi] = useState<Incasso[] | null>(null)
  const [filtro, setFiltro] = useState<Filtro>(() => (leggiPref('tutti-filtro') as Filtro) || 'tutti')
  const [aperta, setAperta] = useState<string | null>(null)     // la riga con i preventivi aperti
  const [problema, setProblema] = useState<string | null>(null)
  const oggi = giorno()

  useEffect(() => {
    supabase.from('prospects').select('*').neq('stage', 'nuovo')
      .order('last_reply_at', { ascending: false, nullsFirst: false }).limit(500)
      .then(({ data }) => setRighe((data as Riga[]) ?? []))
    supabase.from('preventivi').select('*').order('inviato_il', { ascending: true }).limit(2000)
      .then(({ data, error }) => {
        if (error) setProblema('I preventivi non si leggono: ' + error.message)
        setPreventivi((data as Preventivo[]) ?? [])
      })
    supabase.from('incassi').select('id,genere,importo,valuta,stato,quando,ricorrenza,metodo,prossimo_il,fine_il,cliente_nome,prospect_id')
      .order('quando', { ascending: false }).limit(1000)
      .then(({ data, error }) => { if (!error && data && data.length) setIncassi(data as Incasso[]) })
  }, [])

  async function scriviRiga(p: Riga, patch: Partial<Riga>) {
    const { data, error } = await supabase.from('prospects').update(patch).eq('id', p.id).select().single()
    if (error || !data) { setProblema(`«${p.company || p.name}» non si è salvato: ${error?.message ?? ''}`); return }
    setProblema(null)
    setRighe((r) => r!.map((x) => (x.id === p.id ? (data as Riga) : x)))
  }

  async function nuovoPreventivo(p: Riga) {
    const { data, error } = await supabase.from('preventivi')
      .insert({ prospect_id: p.id, inviato_il: oggi, stato: 'inviato' }).select().single()
    if (error || !data) { setProblema('Il preventivo non si è creato: ' + (error?.message ?? '')); return null }
    setPreventivi((q) => [...q, data as Preventivo])
    setAperta(p.id)
    return data as Preventivo
  }

  async function scriviPreventivo(q: Preventivo, patch: Partial<Preventivo>) {
    const { data, error } = await supabase.from('preventivi').update(patch).eq('id', q.id).select().single()
    if (error || !data) { setProblema('Il preventivo non si è salvato: ' + (error?.message ?? '')); return }
    setProblema(null)
    setPreventivi((l) => l.map((x) => (x.id === q.id ? (data as Preventivo) : x)))
  }

  async function togliPreventivo(q: Preventivo) {
    if (!confirm('Tolgo questo preventivo?')) return
    const { error } = await supabase.from('preventivi').delete().eq('id', q.id)
    if (error) { setProblema('Non si è tolto: ' + error.message); return }
    setPreventivi((l) => l.filter((x) => x.id !== q.id))
  }

  // il selettore di stato: cambia la fase vera, non un'etichetta a parte
  async function cambiaStato(p: Riga, s: StatoFoglio) {
    if (s === 'cliente') await scriviRiga(p, { fuori: true, fuori_at: p.fuori_at ?? new Date().toISOString(), pipeline_stage: 'cliente', contratto: 'stable', awaiting_us: false, no_followup: true })
    else if (s === 'prova') {
      const d = new Date(); const inizio = d.toISOString().slice(0, 10); d.setMonth(d.getMonth() + 2)
      await scriviRiga(p, { fuori: true, fuori_at: p.fuori_at ?? new Date().toISOString(), pipeline_stage: 'prova', contratto: 'prova',
        prova_inizio: p.prova_inizio ?? inizio, prova_fine: p.prova_fine ?? d.toISOString().slice(0, 10), awaiting_us: false, no_followup: true })
    }
    else if (s === 'perso') await scriviRiga(p, p.fuori ? { pipeline_stage: 'perso', awaiting_us: false, no_followup: true } : { stage: 'perso', awaiting_us: false, no_followup: true })
    else if (s === 'preventivo') {
      // preventivo inviato = call tecnica fatta: entra in pipeline in Tecnica e nasce il preventivo
      if (!p.fuori || p.pipeline_stage === 'cliente' || p.pipeline_stage === 'perso') {
        await scriviRiga(p, { fuori: true, fuori_at: p.fuori_at ?? new Date().toISOString(), pipeline_stage: 'tecnica' })
      }
      if (!preventivi.some((q) => q.prospect_id === p.id && q.stato === 'inviato')) await nuovoPreventivo(p)
      else setAperta(p.id)
    } else {
      // torna prospect: in pipeline, in Conoscitiva
      await scriviRiga(p, { fuori: true, fuori_at: p.fuori_at ?? new Date().toISOString(), pipeline_stage: 'conoscitiva' })
    }
  }

  if (righe === null) return <Spinner />

  const perProspect = new Map<string, Preventivo[]>()
  for (const q of preventivi) perProspect.set(q.prospect_id, [...(perProspect.get(q.prospect_id) ?? []), q])
  const conStato = righe.map((p) => ({ p, s: statoFoglio(p, perProspect.get(p.id) ?? []) }))
  const mostrate = conStato.filter(({ s }) =>
    filtro === 'clienti' ? s === 'cliente' || s === 'prova' : filtro === 'prospect' ? s === 'prospect' || s === 'preventivo' : true)
  const ordine: Record<StatoFoglio, number> = { cliente: 0, prova: 1, preventivo: 2, prospect: 3, perso: 4 }
  mostrate.sort((a, b) => ordine[a.s] - ordine[b.s] || (a.p.company || a.p.name || '').localeCompare(b.p.company || b.p.name || ''))
  const conta = (s: StatoFoglio) => conStato.filter((x) => x.s === s).length

  // il mese, dai pagamenti
  const perIncasso = new Map<string, Incasso[]>()
  for (const i of incassi ?? []) if (i.prospect_id) perIncasso.set(i.prospect_id, [...(perIncasso.get(i.prospect_id) ?? []), i])
  const mese = oggi.slice(0, 7)
  const abbonamentiAttivi = (incassi ?? []).filter((i) => i.genere === 'abbonamento' && ATTIVO.has(i.stato ?? ''))
  const attesoMese = abbonamentiAttivi.reduce((t, i) => t + mensile(i), 0)
  const entratoMese = (incassi ?? []).filter((i) => i.genere === 'addebito' && i.stato === 'succeeded' && (i.quando ?? '').startsWith(mese)).reduce((t, i) => t + i.importo, 0)
  const inRitardo = abbonamentiAttivi.filter((i) => i.stato === 'past_due' || i.stato === 'unpaid')
  const pagamentoDi = (id: string) => {
    const suoi = perIncasso.get(id) ?? []
    const abb = suoi.find((i) => i.genere === 'abbonamento' && ATTIVO.has(i.stato ?? '')) ?? suoi.find((i) => i.genere === 'abbonamento')
    const ultimo = suoi.find((i) => i.genere === 'addebito' && i.stato === 'succeeded')
    return { abb, ultimo }
  }

  const rigaPreventivo = (q: Preventivo) => (
    <tr key={q.id} className="border-b border-velo last:border-0">
      <td className=""><Cella valore={q.titolo ?? ''} su={(v) => scriviPreventivo(q, { titolo: v.trim() || null })} placeholder="cosa gli abbiamo proposto" /></td>
      <td className="w-28"><Cella tipo="number" valore={q.importo == null ? '' : String(q.importo)} su={(v) => scriviPreventivo(q, { importo: v.trim() ? Number(v.replace(',', '.')) : null })} className="text-right tabular-nums" placeholder="€" /></td>
      <td className="w-36"><Cella tipo="date" valore={q.inviato_il ?? ''} su={(v) => v && scriviPreventivo(q, { inviato_il: v })} className="tabular-nums" /></td>
      <td className="w-32 px-1">
        <select value={q.stato} onChange={(e) => scriviPreventivo(q, { stato: e.target.value as Preventivo['stato'] })}
          className={`w-full rounded-md border-0 px-2 py-1 text-xs font-semibold outline-none ${STATI_PREVENTIVO.find(([s]) => s === q.stato)?.[2] ?? ''}`}>
          {STATI_PREVENTIVO.map(([s, e]) => <option key={s} value={s}>{e}</option>)}
        </select>
      </td>
      <td className="w-44 px-3">
        <label className="flex items-center gap-2 text-xs">
          <input type="checkbox" checked={Boolean(q.pagato_il)}
            onChange={(e) => scriviPreventivo(q, { pagato_il: e.target.checked ? oggi : null, ...(e.target.checked && q.stato === 'inviato' ? { stato: 'accettato' } : {}) })}
            className="h-4 w-4 accent-green-700" />
          {q.pagato_il ? <span className="font-semibold text-green-800">pagato il {fmtDateShort(q.pagato_il)}</span> : <span className="text-spento">pagamento arrivato</span>}
        </label>
      </td>
      <td className=""><Cella valore={q.note ?? ''} su={(v) => scriviPreventivo(q, { note: v.trim() || null })} placeholder="note" /></td>
      <td className="w-8 text-center"><button onClick={() => togliPreventivo(q)} aria-label="Togli" className="rounded px-1.5 text-spento hover:bg-red-50 hover:text-red-700">×</button></td>
    </tr>
  )

  return (
    <div className="space-y-3 pb-24 sm:pb-8">
      {problema && (
        <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <span className="flex-1">{problema}</span>
          <button onClick={() => setProblema(null)} className="text-xs font-bold text-red-600">chiudi</button>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex overflow-hidden rounded-full border border-bordo bg-white">
          {(['tutti', 'clienti', 'prospect'] as Filtro[]).map((f) => (
            <button key={f} onClick={() => { setFiltro(f); scriviPref('tutti-filtro', f) }}
              className={`px-4 py-1.5 text-xs font-bold transition-colors ${filtro === f ? 'bg-blu text-white' : 'text-tenue hover:bg-velo'}`}>
              {f === 'tutti' ? 'Tutti' : f === 'clienti' ? 'Clienti' : 'Prospect'}
            </button>
          ))}
        </div>
        <span className="text-xs text-tenue">
          {conta('cliente')} clienti, {conta('prova')} in prova, {conta('preventivo')} con preventivo, {conta('prospect')} prospect, {conta('perso')} persi
        </span>
      </div>

      {incassi && (
        <div className="flex flex-wrap gap-2">
          {[
            ['Atteso questo mese', attesoMese, `${abbonamentiAttivi.length} abbonament${abbonamentiAttivi.length === 1 ? 'o' : 'i'} attiv${abbonamentiAttivi.length === 1 ? 'o' : 'i'}`, ''],
            ['Entrato', entratoMese, 'pagamenti riusciti su Stripe', 'text-green-800'],
            ['In ritardo', inRitardo.reduce((t, i) => t + mensile(i), 0), inRitardo.length ? inRitardo.map((i) => i.cliente_nome).filter(Boolean).join(', ') : 'nessuno', inRitardo.length ? 'text-red-700' : ''],
          ].map(([n, v, sotto, tono]) => (
            <div key={n as string} className="min-w-[150px] flex-1 rounded-xl border border-bordo bg-white px-4 py-3">
              <p className="text-[11px] font-bold uppercase tracking-wide text-tenue">{n as string}</p>
              <p className={`text-xl font-extrabold tabular-nums ${tono as string}`}>{Math.round(v as number).toLocaleString('it-IT')} €</p>
              <p className="truncate text-[11px] text-spento">{sotto as string}</p>
            </div>
          ))}
        </div>
      )}

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-velo/60 text-left text-[11px] font-bold uppercase tracking-wide text-tenue">
                <th className="min-w-[220px] px-3 py-2.5">Azienda</th>
                <th className="min-w-[150px] px-3 py-2.5">Stato</th>
                <th className="min-w-[110px] px-3 py-2.5">Chi segue</th>
                <th className="min-w-[100px] px-3 py-2.5 text-right">Canone/mese</th>
                {incassi && <th className="min-w-[210px] px-3 py-2.5">Pagamenti</th>}
                <th className="min-w-[200px] px-3 py-2.5">Ultimo preventivo</th>
                <th className="min-w-[220px] px-2 py-2">Note</th>
              </tr>
            </thead>
            <tbody>
              {mostrate.length === 0 && (
                <tr><td colSpan={incassi ? 7 : 6} className="px-4 py-6 text-center text-sm text-spento">Nessuno qui dentro.</td></tr>
              )}
              {mostrate.map(({ p, s }) => {
                const suoi = perProspect.get(p.id) ?? []
                const ultimo = suoi[suoi.length - 1]
                const apertaQui = aperta === p.id
                return [
                  <tr key={p.id} className="h-12 border-b border-velo hover:bg-velo/30">
                    <td className="">
                      <button onClick={() => onOpen(p.id)} title={sgid(p.sg_id) ?? undefined}
                              className="flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm font-semibold hover:text-navy">
                        <Faccia p={p} size={28} />
                        <span className="truncate">{p.company || p.name || p.email}</span>
                      </button>
                    </td>
                    <td className="px-1">
                      <select value={s} onChange={(e) => cambiaStato(p, e.target.value as StatoFoglio)}
                        className={`w-full rounded-md border-0 px-2 py-1 text-xs font-semibold outline-none ${STATI_FOGLIO.find(([x]) => x === s)?.[2] ?? ''}`}>
                        {STATI_FOGLIO.map(([x, e]) => <option key={x} value={x}>{e}</option>)}
                      </select>
                    </td>
                    <td className=""><Cella valore={p.chi_segue ?? ''} su={(v) => scriviRiga(p, { chi_segue: v.trim() || null })} placeholder="chi" /></td>
                    <td className=""><Cella tipo="number" valore={p.canone == null ? '' : String(p.canone)} su={(v) => scriviRiga(p, { canone: v.trim() ? Number(v.replace(',', '.')) : null })} className="text-right tabular-nums" placeholder="€" /></td>
                    {incassi && (() => {
                      const { abb, ultimo } = pagamentoDi(p.id)
                      if (!abb && !ultimo) return <td className="px-3 text-xs text-spento">{s === 'cliente' || s === 'prova' ? 'non su Stripe' : ''}</td>
                      const vivo = abb && ATTIVO.has(abb.stato ?? '')
                      const male = abb && (abb.stato === 'past_due' || abb.stato === 'unpaid')
                      return (
                        <td className="px-3 py-1 text-xs">
                          {abb && (
                            <p className={`font-semibold ${male ? 'text-red-700' : vivo ? '' : 'text-spento'}`}>
                              {Math.round(mensile(abb)).toLocaleString('it-IT')} € al mese{abb.metodo ? `, ${METODO[abb.metodo] ?? abb.metodo}` : ''}
                              {male ? ', in ritardo' : vivo ? '' : abb.fine_il ? `, finito il ${fmtDateShort(abb.fine_il.slice(0, 10))}` : ', non attivo'}
                            </p>
                          )}
                          <p className="text-spento">
                            {vivo && abb?.prossimo_il ? `prossimo ${fmtDateShort(abb.prossimo_il.slice(0, 10))}` : ''}
                            {vivo && abb?.prossimo_il && ultimo ? ', ' : ''}
                            {ultimo ? `ultimo pagato ${fmtDateShort((ultimo.quando ?? '').slice(0, 10))}` : ''}
                          </p>
                        </td>
                      )
                    })()}
                    <td className="px-3">
                      <button onClick={() => setAperta(apertaQui ? null : p.id)} className="flex w-full items-center gap-2 py-1.5 text-left text-sm hover:text-navy">
                        <span className={`shrink-0 rounded-full border px-1.5 text-[11px] font-bold ${suoi.length ? 'border-navy text-navy' : 'border-bordo text-spento'}`}>€</span>
                        {ultimo ? (
                          <span className="truncate text-xs">
                            <span className="font-semibold tabular-nums">{euro(ultimo.importo)}</span>
                            {`, ${fmtDateShort(ultimo.inviato_il)}, ${ultimo.stato}`}
                            {ultimo.pagato_il ? <span className="text-green-800">, pagato</span> : ''}
                            {suoi.length > 1 ? <span className="text-spento">, {suoi.length} in tutto</span> : ''}
                          </span>
                        ) : <span className="text-xs text-spento">nessun preventivo</span>}
                      </button>
                    </td>
                    <td><Cella valore={p.notes ?? ''} su={(v) => scriviRiga(p, { notes: v.trim() || null })} placeholder="note" /></td>
                  </tr>,
                  apertaQui && (
                    <tr key={`${p.id}-prev`} className="bg-velo/30">
                      <td colSpan={incassi ? 7 : 6} className="px-3 py-2">
                        <div className="flex items-center justify-between gap-2 pb-1.5">
                          <p className="text-[11px] font-bold uppercase tracking-wide text-tenue">Preventivi di {p.company || p.name}</p>
                          <button onClick={() => nuovoPreventivo(p)} className="rounded-full bg-blu px-3 py-1 text-[11px] font-bold text-white hover:bg-blu-scuro">+ Preventivo</button>
                        </div>
                        {suoi.length === 0 ? (
                          <p className="py-2 text-xs text-spento">Nessun preventivo ancora.</p>
                        ) : (
                          <div className="overflow-x-auto rounded-lg border border-velo bg-white">
                            <table className="w-full border-collapse">
                              <thead>
                                <tr className="text-left text-[10px] font-bold uppercase tracking-wide text-spento">
                                  <th className="border-r border-velo px-2 py-1">Cosa</th><th className="border-r border-velo px-2 py-1 text-right">Importo</th>
                                  <th className="border-r border-velo px-2 py-1">Inviato</th><th className="border-r border-velo px-2 py-1">Stato</th>
                                  <th className="border-r border-velo px-2 py-1">Pagamento</th><th className="px-2 py-1">Note</th><th></th>
                                </tr>
                              </thead>
                              <tbody>{suoi.map(rigaPreventivo)}</tbody>
                            </table>
                          </div>
                        )}
                      </td>
                    </tr>
                  ),
                ]
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
