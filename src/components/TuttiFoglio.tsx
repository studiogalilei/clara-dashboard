import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { leggi as leggiPref, scrivi as scriviPref } from '../lib/preferenze'
import type { Prospect } from '../lib/types'
import { eCliente, ePerso, giorno } from '../lib/regole'
import { Card, Spinner, Cella, sgid, fmtDateShort } from './ui'

// TUTTI COME IL FOGLIO DI GIACOMO (Dre, 9/9): i nomi in fila, lo stato in
// un selettore (Prospect / Preventivo inviato / Cliente / Perso), chi lo
// segue, il canone, l'ultimo preventivo e le note. Il «€» sulla riga apre i
// preventivi di quell'azienda: importo, data, stato, e «pagamento arrivato»
// che spunta Giacomo a mano. Tutto appeso all'SG-ID.

export interface Preventivo {
  id: number
  prospect_id: string
  progetto_id: number | null
  titolo: string | null
  importo: number | null
  inviato_il: string
  stato: 'inviato' | 'accettato' | 'rifiutato'
  pagato_il: string | null
  pagamento_atteso_il: string | null
  note: string | null
}

type Riga = Prospect & { chi_segue?: string | null; notes?: string | null }
type StatoFoglio = 'prospect' | 'preventivo' | 'cliente' | 'perso'
type Filtro = 'clienti' | 'prospect' | 'tutti'

export const STATI_FOGLIO: Array<[StatoFoglio, string, string]> = [
  ['prospect', 'Prospect', 'bg-amber-50 text-amber-900'],
  ['preventivo', 'Preventivo inviato', 'bg-sky-100 text-sky-900'],
  ['cliente', 'Cliente', 'bg-green-100 text-green-900'],
  ['perso', 'Perso', 'bg-velo text-spento'],
]

export const STATI_PREVENTIVO: Array<[Preventivo['stato'], string, string]> = [
  ['inviato', 'inviato', 'bg-sky-100 text-sky-900'],
  ['accettato', 'accettato', 'bg-green-100 text-green-900'],
  ['rifiutato', 'rifiutato', 'bg-red-50 text-red-700'],
]

// lo stato che si vede nel foglio: una lettura sola, da regole.ts + preventivi
export function statoFoglio(p: Riga, suoi: Preventivo[]): StatoFoglio {
  if (eCliente(p)) return 'cliente'
  if (ePerso(p)) return 'perso'
  if (suoi.some((q) => q.stato === 'inviato')) return 'preventivo'
  return 'prospect'
}

export function euro(n: number | null | undefined): string {
  return n == null ? '—' : `${Number(n).toLocaleString('it-IT')} €`
}

interface Props { onOpen: (id: string) => void }

export default function TuttiFoglio({ onOpen }: Props) {
  const [righe, setRighe] = useState<Riga[] | null>(null)
  const [preventivi, setPreventivi] = useState<Preventivo[]>([])
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
    if (s === 'cliente') await scriviRiga(p, { fuori: true, fuori_at: p.fuori_at ?? new Date().toISOString(), pipeline_stage: 'cliente', awaiting_us: false, no_followup: true })
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
    filtro === 'clienti' ? s === 'cliente' : filtro === 'prospect' ? s === 'prospect' || s === 'preventivo' : true)
  const ordine: Record<StatoFoglio, number> = { cliente: 0, preventivo: 1, prospect: 2, perso: 3 }
  mostrate.sort((a, b) => ordine[a.s] - ordine[b.s] || (a.p.company || a.p.name || '').localeCompare(b.p.company || b.p.name || ''))
  const conta = (s: StatoFoglio) => conStato.filter((x) => x.s === s).length

  const rigaPreventivo = (q: Preventivo) => (
    <tr key={q.id} className="border-b border-velo last:border-0">
      <td className="border-r border-velo"><Cella valore={q.titolo ?? ''} su={(v) => scriviPreventivo(q, { titolo: v.trim() || null })} placeholder="cosa gli abbiamo proposto" /></td>
      <td className="border-r border-velo w-28"><Cella tipo="number" valore={q.importo == null ? '' : String(q.importo)} su={(v) => scriviPreventivo(q, { importo: v.trim() ? Number(v.replace(',', '.')) : null })} className="text-right tabular-nums" placeholder="€" /></td>
      <td className="border-r border-velo w-36"><Cella tipo="date" valore={q.inviato_il} su={(v) => v && scriviPreventivo(q, { inviato_il: v })} className="tabular-nums" /></td>
      <td className="border-r border-velo w-32 px-1">
        <select value={q.stato} onChange={(e) => scriviPreventivo(q, { stato: e.target.value as Preventivo['stato'] })}
          className={`w-full rounded-md border-0 px-2 py-1 text-xs font-semibold outline-none ${STATI_PREVENTIVO.find(([s]) => s === q.stato)?.[2] ?? ''}`}>
          {STATI_PREVENTIVO.map(([s, e]) => <option key={s} value={s}>{e}</option>)}
        </select>
      </td>
      <td className="border-r border-velo w-44 px-2">
        <label className="flex items-center gap-2 text-xs">
          <input type="checkbox" checked={Boolean(q.pagato_il)}
            onChange={(e) => scriviPreventivo(q, { pagato_il: e.target.checked ? oggi : null, ...(e.target.checked && q.stato === 'inviato' ? { stato: 'accettato' } : {}) })}
            className="h-4 w-4 accent-green-700" />
          {q.pagato_il ? <span className="font-semibold text-green-800">pagato il {fmtDateShort(q.pagato_il)}</span> : <span className="text-spento">pagamento arrivato</span>}
        </label>
      </td>
      <td className="border-r border-velo"><Cella valore={q.note ?? ''} su={(v) => scriviPreventivo(q, { note: v.trim() || null })} placeholder="note" /></td>
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
          {conta('cliente')} clienti · {conta('preventivo')} con preventivo · {conta('prospect')} prospect · {conta('perso')} persi
        </span>
      </div>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-velo/60 text-left text-[11px] font-bold uppercase tracking-wide text-tenue">
                <th className="min-w-[220px] border-r border-velo px-2 py-2">Azienda</th>
                <th className="min-w-[150px] border-r border-velo px-2 py-2">Stato</th>
                <th className="min-w-[110px] border-r border-velo px-2 py-2">Chi segue</th>
                <th className="min-w-[100px] border-r border-velo px-2 py-2 text-right">Canone/mese</th>
                <th className="min-w-[200px] border-r border-velo px-2 py-2">Ultimo preventivo</th>
                <th className="min-w-[220px] px-2 py-2">Note</th>
              </tr>
            </thead>
            <tbody>
              {mostrate.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-6 text-center text-sm text-spento">Nessuno qui dentro.</td></tr>
              )}
              {mostrate.map(({ p, s }) => {
                const suoi = perProspect.get(p.id) ?? []
                const ultimo = suoi[suoi.length - 1]
                const apertaQui = aperta === p.id
                return [
                  <tr key={p.id} className="border-b border-velo hover:bg-velo/30">
                    <td className="border-r border-velo">
                      <button onClick={() => onOpen(p.id)} className="w-full px-2 py-1.5 text-left text-sm font-semibold hover:underline">
                        {sgid(p.sg_id) && <span className="mr-1.5 font-mono text-[11px] font-normal text-spento">{sgid(p.sg_id)}</span>}
                        {p.company || p.name || p.email}
                      </button>
                    </td>
                    <td className="border-r border-velo px-1">
                      <select value={s} onChange={(e) => cambiaStato(p, e.target.value as StatoFoglio)}
                        className={`w-full rounded-md border-0 px-2 py-1 text-xs font-semibold outline-none ${STATI_FOGLIO.find(([x]) => x === s)?.[2] ?? ''}`}>
                        {STATI_FOGLIO.map(([x, e]) => <option key={x} value={x}>{e}</option>)}
                      </select>
                    </td>
                    <td className="border-r border-velo"><Cella valore={p.chi_segue ?? ''} su={(v) => scriviRiga(p, { chi_segue: v.trim() || null })} placeholder="chi" /></td>
                    <td className="border-r border-velo"><Cella tipo="number" valore={p.canone == null ? '' : String(p.canone)} su={(v) => scriviRiga(p, { canone: v.trim() ? Number(v.replace(',', '.')) : null })} className="text-right tabular-nums" placeholder="€" /></td>
                    <td className="border-r border-velo px-2">
                      <button onClick={() => setAperta(apertaQui ? null : p.id)} className="flex w-full items-center gap-2 py-1.5 text-left text-sm hover:text-navy">
                        <span className={`shrink-0 rounded-full border px-1.5 text-[11px] font-bold ${suoi.length ? 'border-navy text-navy' : 'border-bordo text-spento'}`}>€</span>
                        {ultimo ? (
                          <span className="truncate text-xs">
                            <span className="font-semibold tabular-nums">{euro(ultimo.importo)}</span>
                            {` · ${fmtDateShort(ultimo.inviato_il)} · ${ultimo.stato}`}
                            {ultimo.pagato_il ? <span className="text-green-800"> · pagato</span> : ''}
                            {suoi.length > 1 ? <span className="text-spento"> · {suoi.length} in tutto</span> : ''}
                          </span>
                        ) : <span className="text-xs text-spento">nessun preventivo</span>}
                      </button>
                    </td>
                    <td><Cella valore={p.notes ?? ''} su={(v) => scriviRiga(p, { notes: v.trim() || null })} placeholder="note" /></td>
                  </tr>,
                  apertaQui && (
                    <tr key={`${p.id}-prev`} className="bg-velo/30">
                      <td colSpan={6} className="px-3 py-2">
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
