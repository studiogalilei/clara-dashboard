import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import type { Prospect } from '../lib/types'
import { eCliente, ePerso, vivo } from '../lib/regole'
import { Card, TitoloCard, Micro, Spinner, Faccia, PipelineBadge, StageBadge, fmtDateShort, sgid } from './ui'

// TUTTI (Dre, 4/9): una lista sola con tutti dentro, tarata sui clienti.
// Un click in alto e vedi i prospect, o tutti insieme. Da qui si entra nella
// scheda, che e' il posto dove sta tutto di quella persona.
// Sui clienti la lista si raggruppa per chi li segue: e' il POD di Giacomo,
// senza costruire la gestione della delivery.

interface Props { onOpen: (id: string) => void }

type Riga = Prospect & { chi_segue?: string | null }
type Filtro = 'clienti' | 'prospect' | 'tutti'

const FILTRI: Array<[Filtro, string]> = [
  ['clienti', 'Clienti'],
  ['prospect', 'Prospect'],
  ['tutti', 'Tutti'],
]

function leggiFiltro(): Filtro {
  try { return (localStorage.getItem('tutti-filtro') as Filtro) || 'clienti' } catch { return 'clienti' }
}

export default function TuttiElenco({ onOpen }: Props) {
  const [righe, setRighe] = useState<Riga[] | null>(null)
  const [filtro, setFiltro] = useState<Filtro>(leggiFiltro)
  const [scrivo, setScrivo] = useState<string | null>(null)
  const [bozza, setBozza] = useState('')

  useEffect(() => {
    supabase.from('prospects').select('*').neq('stage', 'nuovo')
      .order('last_reply_at', { ascending: false, nullsFirst: false })
      .limit(500)
      .then(({ data }) => setRighe((data as Riga[]) ?? []))
  }, [])

  function cambia(f: Filtro) {
    setFiltro(f)
    try { localStorage.setItem('tutti-filtro', f) } catch { /* niente */ }
  }

  async function assegna(p: Riga, chi: string) {
    const { data } = await supabase.from('prospects')
      .update({ chi_segue: chi.trim() || null }).eq('id', p.id).select().single()
    if (data) setRighe((r) => r!.map((x) => (x.id === p.id ? (data as Riga) : x)))
    setScrivo(null); setBozza('')
  }

  if (righe === null) return <Spinner />

  const clienti = righe.filter(eCliente)
  const prospetti = righe.filter((p) => !eCliente(p) && !ePerso(p) && vivo(p))
  const mostrate = filtro === 'clienti' ? clienti : filtro === 'prospect' ? prospetti : [...clienti, ...prospetti]
  const mese = clienti.reduce((t, p) => t + (Number(p.canone) || 0), 0)

  const riga = (p: Riga) => (
    <div key={p.id} className="flex items-center gap-3 border-b border-velo px-4 py-2.5 last:border-0 hover:bg-velo/40">
      <Faccia p={p} size={32} />
      <button onClick={() => onOpen(p.id)} className="min-w-0 flex-1 text-left">
        <p className="truncate text-sm font-semibold">{p.company || p.name || p.email}</p>
        <p className="truncate text-xs text-tenue">
          {sgid(p.sg_id) && <span className="font-semibold text-blu">{sgid(p.sg_id)}</span>}
          {sgid(p.sg_id) && ' · '}
          {p.email}
        </p>
      </button>

      {eCliente(p) ? (
        <span className="hidden shrink-0 text-right text-xs sm:block">
          <span className="block font-bold text-green-800">
            {p.canone ? `${Number(p.canone).toLocaleString('it-IT')} €/mese` : 'canone da mettere'}
          </span>
          <span className="block text-spento">
            {p.contratto === 'prova' ? 'in prova' : p.contratto === 'stable' ? 'stabile' : 'contratto da scegliere'}
            {p.fuori_at ? ` · da ${fmtDateShort(p.fuori_at)}` : ''}
          </span>
        </span>
      ) : p.fuori && p.pipeline_stage ? (
        <PipelineBadge stage={p.pipeline_stage} />
      ) : (
        <StageBadge stage={p.stage} />
      )}

      {eCliente(p) && (scrivo === p.id ? (
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
      ))}
    </div>
  )

  return (
    <div className="space-y-3 pb-24 sm:pb-8">
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex overflow-hidden rounded-full border border-bordo bg-white">
          {FILTRI.map(([f, etichetta]) => (
            <button
              key={f}
              onClick={() => cambia(f)}
              className={`px-4 py-1.5 text-xs font-bold transition-colors ${
                filtro === f ? 'bg-navy text-white' : 'text-tenue hover:bg-velo'
              }`}
            >
              {etichetta}
            </button>
          ))}
        </div>
        <span className="text-sm font-semibold text-tenue">
          {mostrate.length} {filtro === 'prospect' ? 'prospect' : filtro === 'clienti' ? (mostrate.length === 1 ? 'cliente' : 'clienti') : 'in tutto'}
        </span>
        {filtro !== 'prospect' && mese > 0 && (
          <span className="ml-auto text-sm">
            <span className="text-lg font-extrabold tabular-nums">{mese.toLocaleString('it-IT')} €</span>
            <span className="ml-1.5 text-xs text-spento">al mese</span>
          </span>
        )}
      </div>

      {mostrate.length === 0 ? (
        <Card className="p-6"><p className="text-center text-sm text-spento">Nessuno qui dentro.</p></Card>
      ) : filtro === 'clienti' ? (
        // sui clienti si raggruppa per chi li segue: e' il POD di Giacomo
        [...new Set(mostrate.map((p) => p.chi_segue?.trim() || ''))].sort().map((chi) => {
          const suoi = mostrate.filter((p) => (p.chi_segue?.trim() || '') === chi)
          const loro = suoi.reduce((t, p) => t + (Number(p.canone) || 0), 0)
          return (
            <Card key={chi || 'nessuno'}>
              <header className="flex items-baseline justify-between gap-2 border-b border-velo px-4 py-2.5">
                <TitoloCard>{chi || 'Non assegnati'}</TitoloCard>
                <Micro>{suoi.length} · {loro.toLocaleString('it-IT')} €/mese</Micro>
              </header>
              {suoi.map(riga)}
            </Card>
          )
        })
      ) : (
        <Card>{mostrate.map(riga)}</Card>
      )}
    </div>
  )
}
