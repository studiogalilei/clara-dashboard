import { useEffect, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'
import { Card, Spinner, Micro } from './ui'
import { giorno } from '../lib/regole'

// PROGETTI = IL FOGLIO DI GIACOMO (Dre, 8/9): «un excel con selettore, serve
// per seguire i progetti in corso». Una riga per progetto, si scrive dentro
// le celle come in un foglio, e il selettore ha esattamente le sue tre voci:
// Trial, Retainer, onboarding. Il cliente si scrive libero (non tutti sono
// prospect del CRM); se e' un prospect, il nome porta alla sua scheda.
// Il dettaglio con i documenti resta nella scheda del cliente.

export interface Progetto {
  id: number
  prospect_id: string | null
  cliente: string | null
  nome: string
  natura: string | null
  chi_segue: string | null
  data_inizio: string | null
  scadenza: string | null
  valore: number | null
  tipo: 'trial' | 'retainer' | 'onboarding' | null
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

// le tre voci del suo foglio, con i suoi colori (verde, giallo, azzurro)
export const TIPI: Array<[NonNullable<Progetto['tipo']>, string, string]> = [
  ['trial', 'Trial', 'bg-amber-100 text-amber-900'],
  ['retainer', 'Retainer', 'bg-green-100 text-green-900'],
  ['onboarding', 'onboarding', 'bg-sky-100 text-sky-900'],
]

interface Props { onOpen: (id: string) => void }

type Campo = 'cliente' | 'nome' | 'natura' | 'chi_segue' | 'data_inizio' | 'scadenza' | 'valore' | 'note'

// una cella del foglio: si scrive dentro, si salva quando esci (blur o Invio)
function Cella({ valore, tipo = 'text', su, className = '', placeholder }: {
  valore: string; tipo?: 'text' | 'date' | 'number'; su: (v: string) => void; className?: string; placeholder?: string
}) {
  const [v, setV] = useState(valore)
  const ultimo = useRef(valore)
  useEffect(() => { setV(valore); ultimo.current = valore }, [valore])
  function chiudi() { if (v !== ultimo.current) { ultimo.current = v; su(v) } }
  return (
    <input
      type={tipo}
      value={v}
      placeholder={placeholder}
      onChange={(e) => setV(e.target.value)}
      onBlur={chiudi}
      onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur() }}
      className={`w-full min-w-0 bg-transparent px-2 py-1.5 text-sm outline-none focus:bg-blu/5 focus:ring-1 focus:ring-blu ${className}`}
    />
  )
}

export default function Progetti({ onOpen }: Props) {
  const [righe, setRighe] = useState<Progetto[] | null>(null)
  const [nomi, setNomi] = useState<Record<string, string>>({})
  const [chiusi, setChiusi] = useState(false)
  const [problema, setProblema] = useState<string | null>(null)

  useEffect(() => {
    supabase.from('progetti').select('*')
      .order('data_inizio', { ascending: true, nullsFirst: false }).order('id', { ascending: true }).limit(300)
      .then(({ data, error }) => {
        if (error) setProblema('Il foglio non si legge: ' + error.message)
        setRighe((data as Progetto[]) ?? [])
      })
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

  async function scrivi(p: Progetto, patch: Partial<Progetto>) {
    const { data, error } = await supabase.from('progetti').update(patch).eq('id', p.id).select().single()
    if (error || !data) {
      setProblema(`«${p.nome || p.cliente || 'la riga'}» non è stato salvato: ${error?.message ?? 'nessuna riga aggiornata'}`)
      return
    }
    setProblema(null)
    setRighe((r) => r!.map((x) => (x.id === p.id ? (data as Progetto) : x)))
  }

  function campo(p: Progetto, k: Campo, v: string) {
    const patch: Partial<Progetto> = {}
    if (k === 'valore') patch.valore = v.trim() ? Number(v.replace(',', '.')) : null
    else if (k === 'nome') patch.nome = v.trim()          // nome non ammette il vuoto nel database
    else patch[k] = v.trim() ? v : null
    void scrivi(p, patch)
  }

  async function aggiungi() {
    const { data, error } = await supabase.from('progetti')
      .insert({ nome: '', stato: 'in_corso' }).select().single()
    if (error || !data) { setProblema('La riga nuova non si è creata: ' + (error?.message ?? '')); return }
    setRighe((r) => [...(r ?? []), data as Progetto])
  }

  async function togli(p: Progetto) {
    if (!confirm(`Tolgo «${p.nome || p.cliente || 'questa riga'}» dal foglio?`)) return
    const { error } = await supabase.from('progetti').delete().eq('id', p.id)
    if (error) { setProblema('Non si è tolta: ' + error.message); return }
    setRighe((r) => r!.filter((x) => x.id !== p.id))
  }

  if (righe === null) return <Spinner />

  const vivi = righe.filter((p) => p.stato !== 'consegnato')
  const fatti = righe.filter((p) => p.stato === 'consegnato')
  const oggi = giorno()
  const retainer = vivi.filter((p) => p.tipo === 'retainer').reduce((t, p) => t + (Number(p.valore) || 0), 0)
  const totale = vivi.reduce((t, p) => t + (Number(p.valore) || 0), 0)

  const riga = (p: Progetto) => {
    const tardi = p.scadenza && p.scadenza < oggi && p.stato !== 'consegnato'
    const nomeCliente = p.prospect_id ? (nomi[p.prospect_id] ?? p.cliente ?? '') : (p.cliente ?? '')
    return (
      <tr key={p.id} className="border-b border-velo last:border-0 hover:bg-velo/30">
        <td className="border-r border-velo">
          {p.prospect_id ? (
            <button onClick={() => onOpen(p.prospect_id!)} className="w-full px-2 py-1.5 text-left text-sm font-semibold text-blu hover:underline">
              {nomeCliente}
            </button>
          ) : (
            <Cella valore={nomeCliente} su={(v) => campo(p, 'cliente', v)} className="font-semibold" placeholder="cliente" />
          )}
        </td>
        <td className="border-r border-velo"><Cella valore={p.nome} su={(v) => campo(p, 'nome', v)} placeholder="cosa gli facciamo" /></td>
        <td className="border-r border-velo"><Cella tipo="date" valore={p.data_inizio ?? ''} su={(v) => campo(p, 'data_inizio', v)} className="tabular-nums" /></td>
        <td className="border-r border-velo"><Cella tipo="number" valore={p.valore == null ? '' : String(p.valore)} su={(v) => campo(p, 'valore', v)} className="text-right tabular-nums" placeholder="€" /></td>
        <td className="border-r border-velo px-1">
          <select
            value={p.tipo ?? ''}
            onChange={(e) => scrivi(p, { tipo: (e.target.value || null) as Progetto['tipo'] })}
            className={`w-full rounded-md border-0 px-2 py-1 text-xs font-semibold outline-none ${TIPI.find(([t]) => t === p.tipo)?.[2] ?? 'bg-transparent text-spento'}`}
          >
            <option value="">—</option>
            {TIPI.map(([t, etichetta]) => <option key={t} value={t}>{etichetta}</option>)}
          </select>
        </td>
        <td className="border-r border-velo"><Cella valore={p.chi_segue ?? ''} su={(v) => campo(p, 'chi_segue', v)} placeholder="chi" /></td>
        <td className="border-r border-velo"><Cella tipo="date" valore={p.scadenza ?? ''} su={(v) => campo(p, 'scadenza', v)} className={`tabular-nums ${tardi ? 'text-red-700 font-semibold' : ''}`} /></td>
        <td className="border-r border-velo"><Cella valore={p.natura ?? ''} su={(v) => campo(p, 'natura', v)} placeholder="sito vetrina, ads…" /></td>
        <td className="border-r border-velo"><Cella valore={p.note ?? ''} su={(v) => campo(p, 'note', v)} placeholder="note" /></td>
        <td className="border-r border-velo px-1">
          <select
            value={p.stato}
            onChange={(e) => scrivi(p, { stato: e.target.value as Progetto['stato'] })}
            className={`w-full rounded-md border-0 px-2 py-1 text-xs font-semibold outline-none ${STATI.find(([s]) => s === p.stato)?.[2] ?? ''}`}
          >
            {STATI.map(([s, etichetta]) => <option key={s} value={s}>{etichetta}</option>)}
          </select>
        </td>
        <td className="px-1 text-center">
          <button onClick={() => togli(p)} aria-label="Togli la riga" className="rounded px-1.5 text-spento hover:bg-red-50 hover:text-red-700">×</button>
        </td>
      </tr>
    )
  }

  const testata = (
    <thead>
      <tr className="bg-velo/60 text-left text-[11px] font-bold uppercase tracking-wide text-tenue">
        <th className="min-w-[160px] border-r border-velo px-2 py-2">Cliente</th>
        <th className="min-w-[180px] border-r border-velo px-2 py-2">Progetto</th>
        <th className="min-w-[130px] border-r border-velo px-2 py-2">Inizio</th>
        <th className="min-w-[90px] border-r border-velo px-2 py-2 text-right">€</th>
        <th className="min-w-[130px] border-r border-velo px-2 py-2">Trial o Retainer</th>
        <th className="min-w-[100px] border-r border-velo px-2 py-2">Chi segue</th>
        <th className="min-w-[130px] border-r border-velo px-2 py-2">Scadenza</th>
        <th className="min-w-[140px] border-r border-velo px-2 py-2">Natura</th>
        <th className="min-w-[220px] border-r border-velo px-2 py-2">Note</th>
        <th className="min-w-[120px] border-r border-velo px-2 py-2">Stato</th>
        <th className="w-8"></th>
      </tr>
    </thead>
  )

  return (
    <div className="space-y-3 pb-24 sm:pb-8">
      {problema && (
        <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <span className="flex-1">{problema}</span>
          <button onClick={() => setProblema(null)} className="shrink-0 text-xs font-bold text-red-600 hover:text-red-900">chiudi</button>
        </div>
      )}

      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 rounded-xl border border-bordo bg-white px-4 py-3">
        <span className="text-xl font-extrabold tabular-nums">{retainer.toLocaleString('it-IT')} €</span>
        <Micro>di retainer al mese</Micro>
        <span className="text-sm font-semibold text-tenue">{totale.toLocaleString('it-IT')} € in tutto · {vivi.length} progett{vivi.length === 1 ? 'o' : 'i'} in corso</span>
        {vivi.some((p) => p.scadenza && p.scadenza < oggi) && (
          <span className="text-xs font-bold text-red-700">
            {vivi.filter((p) => p.scadenza && p.scadenza < oggi).length} oltre la scadenza
          </span>
        )}
        <button onClick={aggiungi} className="ml-auto rounded-full bg-navy px-4 py-1.5 text-sm font-semibold text-white hover:bg-navy/90">
          + Riga
        </button>
      </div>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            {testata}
            <tbody>
              {vivi.length === 0 ? (
                <tr><td colSpan={11} className="px-4 py-6 text-center text-sm text-spento">Foglio vuoto. «+ Riga» e scrivi dentro le celle, come in un foglio.</td></tr>
              ) : vivi.map(riga)}
            </tbody>
          </table>
        </div>
      </Card>

      {fatti.length > 0 && (
        <Card>
          <button onClick={() => setChiusi(!chiusi)} className="flex w-full items-center gap-2 px-4 py-3 text-left hover:bg-velo/40">
            <svg viewBox="0 0 24 24" className={`h-4 w-4 text-tenue transition-transform ${chiusi ? 'rotate-90' : ''}`}>
              <path fill="currentColor" d="M9 6l6 6-6 6z" />
            </svg>
            <span className="text-sm font-bold">Consegnati ({fatti.length})</span>
          </button>
          {chiusi && (
            <div className="overflow-x-auto border-t border-velo">
              <table className="w-full border-collapse">{testata}<tbody>{fatti.map(riga)}</tbody></table>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
