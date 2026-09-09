import { useEffect, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'
import { leggi as leggiPref, scrivi as scriviPref } from '../lib/preferenze'
import type { Prospect } from '../lib/types'
import { eCliente, eProspect, ricorrenteMensile } from '../lib/regole'
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
  return (leggiPref('tutti-filtro') as Filtro) || 'clienti'
}

export default function TuttiElenco({ onOpen }: Props) {
  const [righe, setRighe] = useState<Riga[] | null>(null)
  const [filtro, setFiltro] = useState<Filtro>(leggiFiltro)
  const [scrivo, setScrivo] = useState<string | null>(null)
  const [bozza, setBozza] = useState('')
  const [problema, setProblema] = useState('')
  const scrivoRef = useRef<string | null>(null)
  useEffect(() => { scrivoRef.current = scrivo }, [scrivo])

  // il ricorrente non si somma su questa pagina di 500 righe: e' una domanda
  // sull'azienda, e la fa regole.ts al database (revisione 4/9)
  const [ricorrente, setRicorrente] = useState<{ mese: number; quanti: number; senza: number } | null>(null)
  useEffect(() => { ricorrenteMensile().then(setRicorrente) }, [])

  useEffect(() => {
    supabase.from('prospects').select('*').neq('stage', 'nuovo')
      .order('last_reply_at', { ascending: false, nullsFirst: false })
      .limit(500)
      .then(({ data }) => setRighe((data as Riga[]) ?? []))
  }, [])

  function cambia(f: Filtro) {
    setFiltro(f)
    scriviPref('tutti-filtro', f)
  }

  async function assegna(p: Riga, chi: string) {
    const { data } = await supabase.from('prospects')
      .update({ chi_segue: chi.trim() || null }).eq('id', p.id).select().single()
    if (!data) {
      // se non si salva lo schermo non deve fingere di aver salvato
      setProblema(`«${p.company || p.name}»: non sono riuscito a salvare chi lo segue.`)
      return
    }
    setRighe((r) => r!.map((x) => (x.id === p.id ? (data as Riga) : x)))
    setProblema('')
    // si chiude solo se stai ancora scrivendo su QUESTA riga: se nel
    // frattempo ne hai aperta un'altra, la sua bozza non si tocca
    setScrivo((s) => (s === p.id ? null : s))
    setBozza((b) => (scrivoRef.current === p.id ? '' : b))
  }

  if (righe === null) return <Spinner />

  const clienti = righe.filter(eCliente)
  const prospetti = righe.filter(eProspect)
  const mostrate = filtro === 'clienti' ? clienti : filtro === 'prospect' ? prospetti : [...clienti, ...prospetti]


  const riga = (p: Riga) => (
    <div key={p.id} className="flex items-center gap-3 border-b border-velo px-4 py-2.5 last:border-0 hover:bg-velo/40">
      <Faccia p={p} size={32} />
      <button onClick={() => onOpen(p.id)} className="min-w-0 flex-1 text-left">
        <p className="truncate text-sm font-semibold">{p.company || p.name || p.email}</p>
        <p className="truncate text-xs text-tenue">
          {sgid(p.sg_id, p) && <span className="font-semibold text-blu">{sgid(p.sg_id, p)}</span>}
          {sgid(p.sg_id, p) && ', '}
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
            {p.fuori_at ? `, da ${fmtDateShort(p.fuori_at)}` : ''}
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
      {problema && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm font-semibold text-red-800">
          {problema}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex overflow-hidden rounded-full border border-bordo bg-white">
          {FILTRI.map(([f, etichetta]) => (
            <button
              key={f}
              onClick={() => cambia(f)}
              className={`px-4 py-1.5 text-xs font-bold transition-colors ${
                filtro === f ? 'bg-blu text-white' : 'text-tenue hover:bg-velo'
              }`}
            >
              {etichetta}
            </button>
          ))}
        </div>
        <span className="text-sm font-semibold text-tenue">
          {mostrate.length} {filtro === 'prospect' ? 'prospect' : filtro === 'clienti' ? (mostrate.length === 1 ? 'cliente' : 'clienti') : 'in tutto'}
        </span>
        {filtro !== 'prospect' && ricorrente && ricorrente.mese > 0 && (
          <span className="ml-auto text-sm">
            <span className="text-lg font-extrabold tabular-nums">{ricorrente.mese.toLocaleString('it-IT')} €</span>
            <span className="ml-1.5 text-xs text-spento">al mese</span>
            {ricorrente.senza > 0 && (
              <span className="ml-2 text-xs text-amber-700">{ricorrente.senza} senza canone</span>
            )}
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
                <Micro>{suoi.length}, {loro.toLocaleString('it-IT')} €/mese</Micro>
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
