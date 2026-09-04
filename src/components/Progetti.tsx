import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { Card, TitoloCard, Micro, Spinner, fmtDateShort } from './ui'
import { giorno } from '../lib/regole'

// PROGETTI (Dre, 4/9): il lavoro a scadenza, quello che non e' canone.
// Senza entrare dentro si vede gia' chi ce l'ha in mano, la scadenza e il
// valore. Il dettaglio con i documenti sta nella scheda del suo cliente.
// Fuori di proposito: POD, specialist, generazione dei preventivi,
// fatturazione. Quello e' il foglio di Giacomo e li' resta.

export interface Progetto {
  id: number
  prospect_id: string
  nome: string
  natura: string | null
  chi_segue: string | null
  scadenza: string | null
  valore: number | null
  stato: 'da_iniziare' | 'in_corso' | 'consegnato'
  note: string | null
}

// il lavoro vivo sta sopra, il consegnato scende; a parita' comanda la
// scadenza, e chi non ce l'ha va in coda (revisione 4/9)
export function ordineProgetti(a: Progetto, b: Progetto): number {
  const finito = (p: Progetto) => (p.stato === 'consegnato' ? 1 : 0)
  if (finito(a) !== finito(b)) return finito(a) - finito(b)
  if (!a.scadenza) return b.scadenza ? 1 : 0
  if (!b.scadenza) return -1
  return a.scadenza.localeCompare(b.scadenza)
}

export const STATI: Array<[Progetto['stato'], string, string]> = [
  ['da_iniziare', 'Da iniziare', 'bg-velo text-tenue'],
  ['in_corso', 'In corso', 'bg-blu/10 text-blu'],
  ['consegnato', 'Consegnato', 'bg-green-50 text-green-800'],
]

interface Props { onOpen: (id: string) => void }

export default function Progetti({ onOpen }: Props) {
  const [righe, setRighe] = useState<Progetto[] | null>(null)
  const [nomi, setNomi] = useState<Record<string, string>>({})
  const [chiusi, setChiusi] = useState(false)

  useEffect(() => {
    supabase.from('progetti').select('*')
      .order('scadenza', { ascending: true, nullsFirst: false }).limit(300)
      .then(({ data }) => setRighe((data as Progetto[]) ?? []))
    supabase.from('prospects').select('id,company,name,email').neq('stage', 'nuovo')
      .order('last_reply_at', { ascending: false, nullsFirst: false }).limit(500)
      .then(({ data }) => {
        const m: Record<string, string> = {}
        for (const p of (data as Array<{ id: string; company: string | null; name: string | null; email: string }>) ?? []) {
          m[p.id] = p.company || p.name || p.email
        }
        setNomi(m)
      })
  }, [])

  const [problema, setProblema] = useState<string | null>(null)

  async function cambiaStato(p: Progetto, stato: Progetto['stato']) {
    const { data, error } = await supabase.from('progetti').update({ stato }).eq('id', p.id).select().single()
    if (error || !data) {
      // prima il menu tornava indietro da solo e sembrava un ripensamento
      setProblema(`«${p.nome}» non è cambiato di stato: ${error?.message ?? 'nessuna riga aggiornata'}`)
      return
    }
    setProblema(null)
    setRighe((r) => r!.map((x) => (x.id === p.id ? (data as Progetto) : x)))
  }

  if (righe === null) return <Spinner />

  const vivi = righe.filter((p) => p.stato !== 'consegnato')
  const fatti = righe.filter((p) => p.stato === 'consegnato')
  const valore = vivi.reduce((t, p) => t + (Number(p.valore) || 0), 0)
  const oggi = giorno()

  const riga = (p: Progetto) => {
    const tardi = p.scadenza && p.scadenza < oggi && p.stato !== 'consegnato'
    return (
      <div key={p.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-velo px-4 py-3 last:border-0 hover:bg-velo/40">
        <button onClick={() => onOpen(p.prospect_id)} className="min-w-0 flex-1 text-left">
          <p className="truncate text-sm font-semibold">{p.nome}</p>
          <p className="truncate text-xs text-tenue">
            {nomi[p.prospect_id] ?? 'cliente'}
            {p.natura ? ` · ${p.natura}` : ''}
          </p>
        </button>

        <span className="shrink-0 text-xs text-tenue">
          {p.chi_segue || <span className="text-spento">da assegnare</span>}
        </span>

        <span className={`shrink-0 text-xs font-semibold ${tardi ? 'text-red-700' : 'text-tenue'}`}>
          {p.scadenza ? (tardi ? `scaduto il ${fmtDateShort(p.scadenza)}` : fmtDateShort(p.scadenza)) : 'senza scadenza'}
        </span>

        <span className="shrink-0 text-sm font-bold tabular-nums">
          {p.valore ? `${Number(p.valore).toLocaleString('it-IT')} €` : '—'}
        </span>

        <select
          value={p.stato}
          onChange={(e) => cambiaStato(p, e.target.value as Progetto['stato'])}
          className={`shrink-0 rounded-full border-0 px-2.5 py-1 text-[11px] font-semibold outline-none ${
            STATI.find(([s]) => s === p.stato)?.[2] ?? ''
          }`}
        >
          {STATI.map(([s, etichetta]) => <option key={s} value={s}>{etichetta}</option>)}
        </select>
      </div>
    )
  }

  return (
    <div className="space-y-3 pb-24 sm:pb-8">
      {problema && (
        <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <span className="flex-1">{problema}</span>
          <button onClick={() => setProblema(null)} className="shrink-0 text-xs font-bold text-red-600 hover:text-red-900">chiudi</button>
        </div>
      )}
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 rounded-xl border border-bordo bg-white px-4 py-3">
        <span className="text-xl font-extrabold tabular-nums">{valore.toLocaleString('it-IT')} €</span>
        <Micro>in lavorazione</Micro>
        <span className="text-sm font-semibold text-tenue">
          {vivi.length} progett{vivi.length === 1 ? 'o' : 'i'}
        </span>
        {vivi.some((p) => p.scadenza && p.scadenza < oggi) && (
          <span className="text-xs font-bold text-red-700">
            {vivi.filter((p) => p.scadenza && p.scadenza < oggi).length} oltre la scadenza
          </span>
        )}
      </div>

      {vivi.length === 0 ? (
        <Card className="p-6">
          <p className="text-center text-sm text-spento">
            Nessun progetto in corso. Ne nasce uno ogni volta che un prospect diventa cliente.
          </p>
        </Card>
      ) : (
        <Card>{vivi.map(riga)}</Card>
      )}

      {fatti.length > 0 && (
        <Card>
          <button
            onClick={() => setChiusi(!chiusi)}
            className="flex w-full items-center gap-2 px-4 py-3 text-left hover:bg-velo/40"
          >
            <svg viewBox="0 0 24 24" className={`h-4 w-4 text-tenue transition-transform ${chiusi ? 'rotate-90' : ''}`}>
              <path fill="currentColor" d="M9 6l6 6-6 6z" />
            </svg>
            <TitoloCard>Consegnati ({fatti.length})</TitoloCard>
          </button>
          {chiusi && fatti.map(riga)}
        </Card>
      )}
    </div>
  )
}
