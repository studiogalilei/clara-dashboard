import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { Card, Spinner, Micro, sgid, fmtDateShort } from './ui'
import { STATI_PREVENTIVO, euro, type Preventivo } from './TuttiFoglio'

// TUTTI I PREVENTIVI (Dre, 9/9): una lista sola, dal primo all'ultimo, con
// i totali in alto. Ogni riga porta alla scheda dell'azienda. Si scrive
// dentro dal foglio (il «€» sulla riga), qui si guarda.

interface Props { onOpen: (id: string) => void }
interface Nome { company: string | null; name: string | null; email: string; sg_id: number | null }

export default function Preventivi({ onOpen }: Props) {
  const [righe, setRighe] = useState<Preventivo[] | null>(null)
  const [nomi, setNomi] = useState<Record<string, Nome>>({})

  useEffect(() => {
    supabase.from('preventivi').select('*').order('inviato_il', { ascending: true }).order('id', { ascending: true }).limit(2000)
      .then(async ({ data }) => {
        const l = (data as Preventivo[]) ?? []
        setRighe(l)
        const ids = [...new Set(l.map((q) => q.prospect_id))]
        if (ids.length === 0) return
        const { data: p } = await supabase.from('prospects').select('id,company,name,email,sg_id').in('id', ids)
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
                      <button onClick={() => onOpen(q.prospect_id)} className="text-left text-sm font-semibold hover:underline">
                        {n?.sg_id != null && <span className="mr-1.5 font-mono text-[11px] font-normal text-spento">{sgid(n.sg_id)}</span>}
                        {n ? (n.company || n.name || n.email) : '…'}
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
    </div>
  )
}
