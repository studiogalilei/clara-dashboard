import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { Card, Spinner, Micro, sgid, fmtDateShort, Faccia, type FacciaP } from './ui'
import { STATI_PREVENTIVO, euro, type Preventivo } from './TuttiFoglio'

// GLI INCASSI DA STRIPE (10/9): Clara li legge ogni ora (scripts/stripe_sync.py)
// e li mette in `incassi`. Li vedono solo Dre e Giacomo: la regola e' nel
// database (ruolo ceo), qui si mostra quello che arriva.
interface Incasso {
  id: string
  genere: 'addebito' | 'fattura' | 'abbonamento'
  importo: number
  valuta: string
  stato: string | null
  quando: string | null
  ricorrenza: string | null
  cliente_nome: string | null
  cliente_email: string | null
  descrizione: string | null
  prospect_id: string | null
  preventivo_id: number | null
}
const GENERE: Record<Incasso['genere'], string> = { addebito: 'Pagamento', fattura: 'Fattura', abbonamento: 'Abbonamento' }
function tonoStato(s: string | null) {
  if (s === 'succeeded' || s === 'paid' || s === 'active' || s === 'trialing') return 'bg-green-100 text-green-900'
  if (s === 'failed' || s === 'canceled' || s === 'incomplete_expired' || s === 'unpaid') return 'bg-red-50 text-red-700'
  return 'bg-velo text-tenue'
}
function statoIt(s: string | null) {
  return ({ succeeded: 'riuscito', paid: 'pagata', open: 'aperta', active: 'attivo', trialing: 'in prova', canceled: 'cancellato',
    failed: 'fallito', incomplete: 'incompleto', incomplete_expired: 'scaduto', past_due: 'in ritardo', unpaid: 'non pagato' } as Record<string, string>)[s ?? ''] ?? (s ?? '')
}

// TUTTI I PREVENTIVI (Dre, 9/9): una lista sola, dal primo all'ultimo, con
// i totali in alto. Ogni riga porta alla scheda dell'azienda. Si scrive
// dentro dal foglio (il «€» sulla riga), qui si guarda.

interface Props { onOpen: (id: string) => void }
type Nome = FacciaP & { email: string }

export default function Preventivi({ onOpen }: Props) {
  const [righe, setRighe] = useState<Preventivo[] | null>(null)
  const [nomi, setNomi] = useState<Record<string, Nome>>({})
  const [incassi, setIncassi] = useState<Incasso[] | null>(null)   // null = non li vedo (non sono ceo)

  useEffect(() => {
    supabase.from('incassi').select('*').order('quando', { ascending: false }).limit(500)
      .then(({ data, error }) => { if (!error && data && data.length) setIncassi(data as Incasso[]) })
  }, [])

  useEffect(() => {
    supabase.from('preventivi').select('*').order('inviato_il', { ascending: true }).order('id', { ascending: true }).limit(2000)
      .then(async ({ data }) => {
        const l = (data as Preventivo[]) ?? []
        setRighe(l)
        const ids = [...new Set(l.map((q) => q.prospect_id))]
        if (ids.length === 0) return
        const { data: p } = await supabase.from('prospects').select('id,company,name,email,sg_id,fuori,stage,pipeline_stage').in('id', ids)
        const m: Record<string, Nome> = {}
        for (const x of (p as Array<Nome & { id: string }>) ?? []) m[x.id] = x
        setNomi(m)
      })
  }, [])

  if (righe === null) return <Spinner />

  const somma = (l: Preventivo[]) => l.reduce((t, q) => t + (Number(q.importo) || 0), 0)
  const accettati = righe.filter((q) => q.stato === 'accettato')
  const incassati = righe.filter((q) => q.pagato_il)
  const daIncassare = accettati.filter((q) => !q.pagato_il)
  const aperti = righe.filter((q) => q.stato === 'inviato')
  const anno = new Date().getFullYear()
  const incassatiStripe = (incassi ?? []).filter((i) => (i.genere === 'addebito' && i.stato === 'succeeded') && (i.quando ?? '').startsWith(String(anno)))
  const abbonamenti = (incassi ?? []).filter((i) => i.genere === 'abbonamento' && (i.stato === 'active' || i.stato === 'trialing'))
  const mensile = abbonamenti.reduce((t, i) => t + (i.ricorrenza === 'year' ? i.importo / 12 : i.importo), 0)

  const tessera = (n: string, v: number, quanti: number, tono = '') => (
    <div className="min-w-[140px] flex-1 rounded-xl border border-bordo bg-white px-4 py-3">
      <Micro>{n}</Micro>
      <p className={`text-xl font-extrabold tabular-nums ${tono}`}>{v.toLocaleString('it-IT')} €</p>
      <p className="text-[11px] text-spento">{quanti} preventiv{quanti === 1 ? 'o' : 'i'}</p>
    </div>
  )

  return (
    <div className="space-y-3 pb-24 sm:pb-8">
      <div className="flex flex-wrap gap-2">
        {tessera('Inviati, in attesa', somma(aperti), aperti.length)}
        {tessera('Accettati', somma(accettati), accettati.length)}
        {tessera('Incassati', somma(incassati), incassati.length, 'text-green-800')}
        {tessera('Da incassare', somma(daIncassare), daIncassare.length, daIncassare.length ? 'text-amber-800' : '')}
      </div>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-velo/60 text-left text-[11px] font-bold uppercase tracking-wide text-tenue">
                <th className="w-10 px-2 py-2">#</th>
                <th className="min-w-[110px] px-2 py-2">Inviato</th>
                <th className="min-w-[220px] px-2 py-2">Azienda</th>
                <th className="min-w-[200px] px-2 py-2">Cosa</th>
                <th className="min-w-[100px] px-2 py-2 text-right">Importo</th>
                <th className="min-w-[100px] px-2 py-2">Stato</th>
                <th className="min-w-[130px] px-2 py-2">Pagamento</th>
                <th className="min-w-[160px] px-2 py-2">Note</th>
              </tr>
            </thead>
            <tbody>
              {righe.length === 0 && (
                <tr><td colSpan={8} className="px-4 py-6 text-center text-sm text-spento">Nessun preventivo ancora. Si crea dal foglio, col «€» sulla riga.</td></tr>
              )}
              {righe.map((q, i) => {
                const n = nomi[q.prospect_id]
                const tono = STATI_PREVENTIVO.find(([s]) => s === q.stato)?.[2] ?? ''
                return (
                  <tr key={q.id} className="border-b border-velo last:border-0 hover:bg-velo/30">
                    <td className="px-2 py-2 font-mono text-[11px] text-spento">{i + 1}</td>
                    <td className="px-2 py-2 text-sm tabular-nums">{fmtDateShort(q.inviato_il)}</td>
                    <td className="px-2 py-2">
                      <button onClick={() => onOpen(q.prospect_id)} title={n ? (sgid(n.sg_id) ?? undefined) : undefined}
                              className="flex items-center gap-2.5 text-left text-sm font-semibold hover:text-navy">
                        {n && <Faccia p={n} size={28} />}
                        <span className="truncate">{n ? (n.company || n.name || n.email) : '…'}</span>
                      </button>
                    </td>
                    <td className="px-2 py-2 text-sm">{q.titolo || <span className="text-spento">—</span>}</td>
                    <td className="px-2 py-2 text-right text-sm font-semibold tabular-nums">{euro(q.importo)}</td>
                    <td className="px-2 py-2"><span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${tono}`}>{q.stato}</span></td>
                    <td className="px-2 py-2 text-xs">
                      {q.pagato_il ? <span className="font-semibold text-green-800">pagato il {fmtDateShort(q.pagato_il)}</span>
                        : q.stato === 'accettato' ? <span className="font-semibold text-amber-800">da incassare</span>
                        : <span className="text-spento">—</span>}
                    </td>
                    <td className="px-2 py-2 text-xs text-tenue">{q.note}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Card>

      {incassi && (
        <>
          <div className="flex flex-wrap items-end justify-between gap-2 pt-2">
            <div>
              <h2 className="text-base font-extrabold text-navy">Incassi su Stripe</h2>
              <p className="text-xs text-spento">Clara li legge ogni ora. Li vedete solo tu e Giacomo.</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {tessera(`Incassato nel ${anno}`, somma(incassatiStripe.map((i) => ({ importo: i.importo } as Preventivo))), incassatiStripe.length, 'text-green-800')}
            <div className="min-w-[140px] flex-1 rounded-xl border border-bordo bg-white px-4 py-3">
              <Micro>Abbonamenti attivi</Micro>
              <p className="text-xl font-extrabold tabular-nums">{Math.round(mensile).toLocaleString('it-IT')} € <span className="text-sm font-semibold text-tenue">al mese</span></p>
              <p className="text-[11px] text-spento">{abbonamenti.length} attiv{abbonamenti.length === 1 ? 'o' : 'i'}</p>
            </div>
          </div>
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="bg-velo/60 text-left text-[11px] font-bold uppercase tracking-wide text-tenue">
                    <th className="min-w-[110px] px-2 py-2">Quando</th>
                    <th className="min-w-[110px] px-2 py-2">Cosa</th>
                    <th className="min-w-[220px] px-2 py-2">Cliente</th>
                    <th className="min-w-[200px] px-2 py-2">Descrizione</th>
                    <th className="min-w-[100px] px-2 py-2 text-right">Importo</th>
                    <th className="min-w-[100px] px-2 py-2">Stato</th>
                    <th className="min-w-[160px] px-2 py-2">Azienda</th>
                  </tr>
                </thead>
                <tbody>
                  {incassi.map((i) => {
                    const n = i.prospect_id ? nomi[i.prospect_id] : undefined
                    return (
                      <tr key={i.id} className="border-b border-velo last:border-0 hover:bg-velo/30">
                        <td className="px-2 py-2 text-sm tabular-nums">{fmtDateShort(i.quando ? i.quando.slice(0, 10) : null)}</td>
                        <td className="px-2 py-2 text-sm">{GENERE[i.genere]}{i.ricorrenza ? <span className="text-spento"> / {i.ricorrenza === 'year' ? 'anno' : 'mese'}</span> : null}</td>
                        <td className="px-2 py-2">
                          <p className="text-sm font-semibold">{i.cliente_nome || <span className="text-spento">senza nome</span>}</p>
                          {i.cliente_email && <p className="text-[11px] text-spento">{i.cliente_email}</p>}
                        </td>
                        <td className="px-2 py-2 text-sm text-tenue">{i.descrizione || <span className="text-spento">—</span>}</td>
                        <td className="px-2 py-2 text-right text-sm font-semibold tabular-nums">{i.importo.toLocaleString('it-IT', { minimumFractionDigits: 0, maximumFractionDigits: 2 })} {i.valuta.toUpperCase()}</td>
                        <td className="px-2 py-2"><span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${tonoStato(i.stato)}`}>{statoIt(i.stato)}</span></td>
                        <td className="px-2 py-2 text-xs">
                          {i.prospect_id
                            ? <button onClick={() => onOpen(i.prospect_id!)} className="font-semibold hover:text-navy">{n ? (n.company || n.name || n.email) : 'apri la scheda'}{i.preventivo_id ? <span className="text-spento"> (preventivo pagato)</span> : null}</button>
                            : <span className="text-spento">non collegato</span>}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
