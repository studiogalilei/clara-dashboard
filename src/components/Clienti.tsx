import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import type { Prospect } from '../lib/types'
import { eCliente } from '../lib/regole'
import { Card, TitoloCard, Micro, Spinner, Faccia, fmtDateShort } from './ui'

// CLIENTI: il cuore del POD di Giacomo senza costruire la gestione della
// delivery (Dre, 3/9). Un campo solo, «chi lo segue», e i clienti si
// raggruppano da soli per persona, col canone e da quando pagano.
// Quello che NON c'e', ed e' voluto: specialist, preventivi, natura del
// progetto. Quello e' il foglio di Giacomo e li' resta.

interface Props { onOpen: (id: string) => void }

type Cliente = Prospect & { chi_segue?: string | null }

export default function Clienti({ onOpen }: Props) {
  const [righe, setRighe] = useState<Cliente[] | null>(null)
  const [scrivo, setScrivo] = useState<string | null>(null)
  const [bozza, setBozza] = useState('')

  useEffect(() => {
    supabase.from('prospects').select('*')
      .or('pipeline_stage.eq.cliente,stage.eq.cliente')
      .limit(300)
      .then(({ data }) => setRighe(((data as Cliente[]) ?? []).filter(eCliente)))
  }, [])

  async function assegna(p: Cliente, chi: string) {
    const valore = chi.trim() || null
    const { data } = await supabase.from('prospects')
      .update({ chi_segue: valore }).eq('id', p.id).select().single()
    if (data) setRighe((r) => r!.map((x) => (x.id === p.id ? (data as Cliente) : x)))
    setScrivo(null); setBozza('')
  }

  if (righe === null) return <Spinner />
  if (righe.length === 0) {
    return <Card className="p-6"><p className="text-center text-sm text-spento">Nessun cliente ancora.</p></Card>
  }

  const persone = [...new Set(righe.map((p) => p.chi_segue?.trim() || ''))].sort()
  const totale = righe.reduce((t, p) => t + (Number(p.canone) || 0), 0)

  return (
    <div className="space-y-4 pb-24 sm:pb-8">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 rounded-xl border border-bordo bg-white px-4 py-3">
        <span className="text-xl font-extrabold tabular-nums">{totale.toLocaleString('it-IT')} €</span>
        <Micro>al mese</Micro>
        <span className="text-sm font-semibold text-tenue">
          {righe.length} client{righe.length === 1 ? 'e' : 'i'}
        </span>
      </div>

      {persone.map((chi) => {
        const suoi = righe.filter((p) => (p.chi_segue?.trim() || '') === chi)
        const mese = suoi.reduce((t, p) => t + (Number(p.canone) || 0), 0)
        return (
          <Card key={chi || 'nessuno'}>
            <header className="flex items-baseline justify-between gap-2 border-b border-velo px-4 py-2.5">
              <TitoloCard>{chi || 'Non assegnati'}</TitoloCard>
              <span className="text-xs font-semibold text-tenue">
                {suoi.length} · {mese.toLocaleString('it-IT')} €/mese
              </span>
            </header>
            {suoi.map((p) => (
              <div key={p.id} className="flex items-center gap-3 border-b border-velo px-4 py-2.5 last:border-0">
                <Faccia p={p} size={30} />
                <button onClick={() => onOpen(p.id)} className="min-w-0 flex-1 text-left">
                  <p className="truncate text-sm font-semibold">{p.company || p.name || p.email}</p>
                  <p className="truncate text-xs text-tenue">
                    {p.contratto === 'prova' ? 'in prova' : p.contratto === 'stable' ? 'stabile' : 'contratto da scegliere'}
                    {p.fuori_at ? ` · da ${fmtDateShort(p.fuori_at)}` : ''}
                  </p>
                </button>
                <span className="shrink-0 text-sm font-bold tabular-nums text-green-800">
                  {p.canone ? `${Number(p.canone).toLocaleString('it-IT')} €` : '—'}
                </span>
                {scrivo === p.id ? (
                  <input
                    autoFocus
                    value={bozza}
                    onChange={(e) => setBozza(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') assegna(p, bozza)
                      if (e.key === 'Escape') { setScrivo(null); setBozza('') }
                    }}
                    onBlur={() => assegna(p, bozza)}
                    placeholder="Chi lo segue"
                    className="w-32 shrink-0 rounded-full border border-blu px-2.5 py-1 text-xs outline-none"
                  />
                ) : (
                  <button
                    onClick={() => { setScrivo(p.id); setBozza(p.chi_segue ?? '') }}
                    className="shrink-0 rounded-full border border-bordo px-2.5 py-1 text-xs font-semibold text-spento hover:border-navy hover:text-navy"
                  >
                    {p.chi_segue ? 'cambia' : 'assegna'}
                  </button>
                )}
              </div>
            ))}
          </Card>
        )
      })}
    </div>
  )
}
