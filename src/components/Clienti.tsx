import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { leggi as leggiPref, scrivi as scriviPref } from '../lib/preferenze'
import { PIPELINE_LABEL, type Prospect, type PipelineStage } from '../lib/types'
import { Card, Spinner, Faccia, sgid, fmtDateShort } from './ui'
import Progetti, { STATI, TIPI, ordineProgetti, type Progetto } from './Progetti'
import Preventivi from './Preventivi'
import { euro, mensile, type Preventivo, type Incasso } from './TuttiFoglio'

// CLIENTI (Dre, 12/9): «non sono solo progetti, sono proprio i clienti».
// Chi e' dentro, dopo la firma: una riga per cliente e sotto di lui tutto
// quello che facciamo (prova o retainer, i progetti, il preventivo, i
// pagamenti, il prossimo passo). Il foglio di Giacomo e i preventivi sono
// altre due forme della stessa pagina, non altre pagine.

type Modo = 'elenco' | 'foglio' | 'preventivi'
const MODI: Array<[Modo, string]> = [['elenco', 'Clienti'], ['foglio', 'Foglio progetti'], ['preventivi', 'Preventivi e incassi']]
const DENTRO: PipelineStage[] = ['avvio', 'prova', 'cliente']
const TONO: Record<string, string> = { avvio: 'bg-sky-100 text-sky-900', prova: 'bg-amber-100 text-amber-900', cliente: 'bg-green-100 text-green-900' }
const ATTIVI = new Set(['active', 'trialing', 'past_due', 'unpaid'])

interface Props { onOpen: (id: string) => void }

export default function Clienti({ onOpen }: Props) {
  const [modo, setModo] = useState<Modo>(() => (leggiPref('clienti-modo') as Modo) || 'elenco')
  function cambia(m: Modo) { setModo(m); scriviPref('clienti-modo', m) }
  return (
    <div className="space-y-4">
      <div className="flex gap-6 border-b border-bordo">
        {MODI.map(([m, etichetta]) => (
          <button key={m} onClick={() => cambia(m)}
            className={`-mb-px border-b-2 pb-2.5 text-[15px] font-semibold transition-colors ${
              modo === m ? 'border-navy text-navy' : 'border-transparent text-tenue hover:text-inchiostro'}`}>
            {etichetta}
          </button>
        ))}
      </div>
      {modo === 'elenco' ? <Elenco onOpen={onOpen} /> : modo === 'foglio' ? <Progetti onOpen={onOpen} /> : <Preventivi onOpen={onOpen} />}
    </div>
  )
}

type Riga = Prospect & { chi_segue?: string | null; canone?: number | null; prova_fine?: string | null; next_action?: string | null; next_action_date?: string | null }

function Elenco({ onOpen }: Props) {
  const [clienti, setClienti] = useState<Riga[] | null>(null)
  const [progetti, setProgetti] = useState<Progetto[]>([])
  const [preventivi, setPreventivi] = useState<Preventivo[]>([])
  const [incassi, setIncassi] = useState<Incasso[]>([])
  const [aperto, setAperto] = useState<string | null>(null)

  useEffect(() => {
    supabase.from('prospects').select('*').eq('fuori', true).in('pipeline_stage', DENTRO).limit(500)
      .then(({ data }) => setClienti((data as Riga[]) ?? []))
    supabase.from('progetti').select('*').limit(1000).then(({ data }) => setProgetti(((data as Progetto[]) ?? []).sort(ordineProgetti)))
    supabase.from('preventivi').select('*').limit(2000).then(({ data }) => setPreventivi((data as Preventivo[]) ?? []))
    supabase.from('incassi').select('id,genere,importo,valuta,stato,quando,ricorrenza,metodo,prossimo_il,fine_il,cliente_nome,prospect_id')
      .order('quando', { ascending: false }).limit(1000).then(({ data }) => setIncassi((data as Incasso[]) ?? []))
  }, [])

  if (clienti === null) return <Spinner />

  const ordine: Record<string, number> = { cliente: 0, prova: 1, avvio: 2 }
  const lista = [...clienti].sort((a, b) => (ordine[a.pipeline_stage ?? ''] ?? 9) - (ordine[b.pipeline_stage ?? ''] ?? 9)
    || (a.company || a.name || '').localeCompare(b.company || b.name || ''))
  const vedoSoldi = preventivi.length > 0 || incassi.length > 0
  const retainer = lista.filter((c) => c.pipeline_stage === 'cliente').reduce((t, c) => t + (Number(c.canone) || 0), 0)

  return (
    <div className="space-y-3 pb-24 sm:pb-8">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 rounded-xl border border-bordo bg-white px-4 py-3">
        <span className="text-xl font-extrabold tabular-nums">{lista.length}</span>
        <span className="text-[11px] font-bold uppercase tracking-wide text-tenue">client{lista.length === 1 ? 'e' : 'i'} dentro</span>
        <span className="text-sm font-semibold text-tenue">
          {lista.filter((c) => c.pipeline_stage === 'cliente').length} a retainer, {lista.filter((c) => c.pipeline_stage === 'prova').length} in prova, {lista.filter((c) => c.pipeline_stage === 'avvio').length} in avvio
        </span>
        {retainer > 0 && <span className="ml-auto text-sm font-bold tabular-nums">{retainer.toLocaleString('it-IT')} € al mese di retainer</span>}
      </div>

      {lista.length === 0 && <Card><p className="px-4 py-6 text-center text-sm text-spento">Nessun cliente ancora. Arrivano da Pipeline, con «Avanza» sulla scheda.</p></Card>}

      {lista.map((c) => {
        const suoi = progetti.filter((g) => g.prospect_id === c.id)
        const quote = preventivi.filter((q) => q.prospect_id === c.id)
        const soldi = incassi.filter((i) => i.prospect_id === c.id)
        const abb = soldi.find((i) => i.genere === 'abbonamento' && ATTIVI.has(i.stato ?? ''))
        const pagati = soldi.filter((i) => i.genere === 'addebito' && i.stato === 'succeeded')
        const apertoQui = aperto === c.id
        const stage = c.pipeline_stage ?? 'cliente'
        return (
          <Card key={c.id} className="overflow-hidden">
            <button onClick={() => setAperto(apertoQui ? null : c.id)} className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-velo/40">
              <Faccia p={c} size={36} />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                  <span className="truncate text-[15px] font-bold">{c.company || c.name || c.email}</span>
                  {sgid(c.sg_id, c) && <span className="text-[11px] font-semibold text-spento">{sgid(c.sg_id, c)}</span>}
                  <span className={`rounded-md px-2 py-0.5 text-[11px] font-bold ${TONO[stage] ?? ''}`}>{PIPELINE_LABEL[stage]}</span>
                  {stage === 'prova' && c.prova_fine && <span className="text-[11px] text-tenue">fino al {fmtDateShort(c.prova_fine)}</span>}
                </div>
                <p className="truncate text-xs text-tenue">
                  {c.chi_segue ? `segue ${c.chi_segue}` : 'nessuno lo segue'}
                  {suoi.length ? `, ${suoi.length} progett${suoi.length === 1 ? 'o' : 'i'}` : ''}
                  {c.next_action ? `, prossimo: ${c.next_action}${c.next_action_date ? ` (${fmtDateShort(c.next_action_date)})` : ''}` : ''}
                </p>
              </div>
              <div className="hidden shrink-0 text-right sm:block">
                {c.canone != null && <p className="text-sm font-bold tabular-nums">{Number(c.canone).toLocaleString('it-IT')} € <span className="text-xs font-semibold text-tenue">al mese</span></p>}
                {abb && <p className="text-[11px] text-green-800">{Math.round(mensile(abb)).toLocaleString('it-IT')} € su Stripe{abb.prossimo_il ? `, prossimo ${fmtDateShort(abb.prossimo_il.slice(0, 10))}` : ''}</p>}
              </div>
              <span className={`shrink-0 text-spento transition-transform ${apertoQui ? 'rotate-90' : ''}`} aria-hidden>›</span>
            </button>

            {apertoQui && (
              <div className="grid grid-cols-1 gap-4 border-t border-velo px-4 py-3 md:grid-cols-2">
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-wide text-tenue">Progetti</p>
                  {suoi.length === 0 ? <p className="py-1.5 text-sm text-spento">Nessun progetto ancora.</p> : (
                    <ul className="divide-y divide-velo">
                      {suoi.map((g) => (
                        <li key={g.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-1.5 text-sm">
                          <span className="min-w-0 flex-1 truncate font-semibold">{g.nome}</span>
                          {g.tipo && <span className={`rounded-md px-1.5 py-0.5 text-[11px] font-semibold ${TIPI.find(([t]) => t === g.tipo)?.[2] ?? ''}`}>{TIPI.find(([t]) => t === g.tipo)?.[1]}</span>}
                          {g.chi_segue && <span className="text-xs text-tenue">{g.chi_segue}</span>}
                          {g.valore != null && <span className="font-bold tabular-nums">{Number(g.valore).toLocaleString('it-IT')} €</span>}
                          <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${STATI.find(([s]) => s === g.stato)?.[2] ?? ''}`}>{STATI.find(([s]) => s === g.stato)?.[1]}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <div>
                  {vedoSoldi ? (
                    <>
                      <p className="text-[11px] font-bold uppercase tracking-wide text-tenue">Preventivi e pagamenti</p>
                      {quote.length === 0 && pagati.length === 0 && !abb && <p className="py-1.5 text-sm text-spento">Niente ancora.</p>}
                      <ul className="divide-y divide-velo">
                        {quote.map((q) => (
                          <li key={q.id} className="flex items-center gap-3 py-1.5 text-sm">
                            <span className="min-w-0 flex-1 truncate">{q.titolo || 'preventivo'}</span>
                            <span className="font-bold tabular-nums">{euro(q.importo)}</span>
                            <span className={`text-[11px] font-semibold ${q.pagato_il ? 'text-green-800' : q.stato === 'accettato' ? 'text-amber-800' : 'text-tenue'}`}>
                              {q.pagato_il ? `pagato il ${fmtDateShort(q.pagato_il)}` : q.stato}
                            </span>
                          </li>
                        ))}
                        {abb && (
                          <li className="flex items-center gap-3 py-1.5 text-sm">
                            <span className="min-w-0 flex-1 truncate">Abbonamento Stripe{abb.metodo ? `, ${abb.metodo}` : ''}</span>
                            <span className="font-bold tabular-nums">{Math.round(mensile(abb)).toLocaleString('it-IT')} € al mese</span>
                          </li>
                        )}
                        {pagati.slice(0, 3).map((i) => (
                          <li key={i.id} className="flex items-center gap-3 py-1.5 text-xs text-tenue">
                            <span className="min-w-0 flex-1 truncate">pagamento riuscito</span>
                            <span className="font-semibold tabular-nums">{i.importo.toLocaleString('it-IT')} {i.valuta.toUpperCase()}</span>
                            <span>{fmtDateShort((i.quando ?? '').slice(0, 10))}</span>
                          </li>
                        ))}
                      </ul>
                    </>
                  ) : (
                    <p className="text-sm text-spento">Preventivi e pagamenti li vedono Dre e Giacomo.</p>
                  )}
                </div>
                <div className="md:col-span-2">
                  <button onClick={() => onOpen(c.id)} className="rounded-full bg-blu px-4 py-1.5 text-sm font-bold text-white hover:bg-blu-scuro">Apri la scheda</button>
                </div>
              </div>
            )}
          </Card>
        )
      })}
    </div>
  )
}
