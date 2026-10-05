import { useCallback, useEffect, useMemo, useState } from 'react'
import { supabase } from '../lib/supabase'
import type { Prospect } from '../lib/types'
import { tappaDi, mossa, type Tappa } from '../lib/percorso'
import { Spinner } from './ui'

// IN TRATTATIVA (Dre, 5/10): «voglio solo 3 colonne stile Trello, solo quelli che
// hanno detto si'. Prima il workflow, poi il software.» Il workflow sta nel vault
// («La Pipeline rifatta»): questa schermata risponde a UNA domanda, a che punto
// sono con chi ha detto si' e qual e' la prossima mossa con ognuno.
// Colonna 1 Hanno detto si' (sì ricevuto, call da fissare), 2 Call conoscitiva,
// 3 Call tecnica. Il perso si fa dalla carta, col motivo, e resta recuperabile
// dal cassetto in fondo. I no non esistono qui.

type Colonna = 'si' | 'conoscitiva' | 'tecnica'

const COLONNE: Array<{ k: Colonna; nome: string; vuoto: string }> = [
  { k: 'si', nome: 'Hanno detto sì', vuoto: 'Nessun sì in attesa: i prossimi arrivano dalle risposte alle campagne.' },
  { k: 'conoscitiva', nome: 'Call conoscitiva', vuoto: 'Nessuna conoscitiva in ballo: si fissa dalla colonna dei sì.' },
  { k: 'tecnica', nome: 'Call tecnica', vuoto: 'Nessuna tecnica in ballo: le conoscitive di questa settimana sono la strada.' },
]

function colonnaDi(p: Prospect): Colonna | 'persa' | null {
  const t = tappaDi(p)
  if (t === 'perso') return 'persa'
  if (t === 'conoscitiva') return 'conoscitiva'
  if (t === 'tecnica') return 'tecnica'
  // hanno detto si': prima della call, con una classificazione da si'
  if ((t === 'risposta' || t === 'analisi' || t === 'follow_up')
      && ['positivo', 'tiepido', 'rinvio'].includes(p.classificazione ?? '')) return 'si'
  return null
}

function giorniDa(iso: string | null | undefined): number | null {
  if (!iso) return null
  return Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000)
}

// la riga di stato in italiano, col colore che ritorna: ambra aspetta te,
// blu corre da solo, rosso fermo da troppo
function statoDi(p: Prospect, col: Colonna): { testo: string; colore: string } {
  const fermo = giorniDa((p as Prospect & { mosso_il?: string | null }).mosso_il ?? p.last_reply_at)
  if (p.awaiting_us) return { testo: 'ha scritto: c’è da rispondere', colore: 'bg-amber-400' }
  if (col === 'si') {
    const g = giorniDa(p.last_reply_at)
    if (fermo !== null && fermo > 7) return { testo: `fermo da ${fermo} giorni`, colore: 'bg-red-500' }
    if (!p.analysis_sent) return { testo: 'sì ricevuto, l’analisi sta partendo', colore: 'bg-blu' }
    return { testo: g !== null ? `sì di ${g === 0 ? 'oggi' : `${g} giorni fa`}, call da fissare` : 'call da fissare', colore: 'bg-blu' }
  }
  if (p.next_action_date && p.next_action_date <= new Date().toISOString().slice(0, 10)) {
    return { testo: `${p.next_action ?? 'prossimo passo'} scaduto`, colore: 'bg-amber-400' }
  }
  if (fermo !== null && fermo > 7) return { testo: `fermo da ${fermo} giorni`, colore: 'bg-red-500' }
  return { testo: p.next_action ? `${p.next_action}${p.next_action_date ? `, ${p.next_action_date.slice(8, 10)}/${p.next_action_date.slice(5, 7)}` : ''}` : 'in corso', colore: 'bg-blu' }
}

export default function Trattativa({ onOpen }: { onOpen: (id: string) => void }) {
  const [righe, setRighe] = useState<Prospect[] | null>(null)
  const [sopra, setSopra] = useState<Colonna | null>(null)
  const [perdo, setPerdo] = useState<Prospect | null>(null)
  const [motivo, setMotivo] = useState('')
  const [cassetto, setCassetto] = useState(false)
  const [guaio, setGuaio] = useState<string | null>(null)

  const carica = useCallback(() => {
    void supabase.from('prospects').select('*')
      .or('and(fuori.eq.false,stage.in.(risposto,analisi_inviata,in_follow_up,call_fissata,rinviato,perso)),fuori.eq.true')
      .limit(800)
      .then(({ data }) => setRighe((data as Prospect[]) ?? []))
  }, [])
  useEffect(() => { carica() }, [carica])

  const gruppi = useMemo(() => {
    const g: Record<Colonna | 'persa', Prospect[]> = { si: [], conoscitiva: [], tecnica: [], persa: [] }
    for (const p of righe ?? []) {
      const c = colonnaDi(p)
      if (c) g[c].push(p)
    }
    // chi aspetta una mossa sta in cima, poi i piu' fermi
    for (const k of Object.keys(g) as Array<keyof typeof g>) {
      g[k].sort((a, b) => Number(b.awaiting_us) - Number(a.awaiting_us)
        || (a.last_reply_at ?? '') .localeCompare(b.last_reply_at ?? ''))
    }
    return g
  }, [righe])

  // la mossa: prima lo schermo, poi il database (regola 17)
  const muovi = useCallback(async (p: Prospect, verso: Tappa | 'perso', mot?: string) => {
    setGuaio(null)
    const m = mossa(p, verso as Tappa, { motivo: mot })
    if ('no' in m) { setGuaio(m.no); return false }
    const prima = righe
    setRighe((l) => (l ?? []).map((x) => (x.id === p.id ? { ...x, ...m.patch } as Prospect : x)))
    const { error } = await supabase.from('prospects').update(m.patch).eq('id', p.id)
    if (error) { setRighe(prima); setGuaio(error.message); return false }
    void supabase.from('interactions').insert({ prospect_id: p.id, at: new Date().toISOString(), kind: 'nota', body: m.nota })
    return true
  }, [righe])

  async function lascia() {
    if (!perdo || !motivo.trim()) return
    const p = perdo
    setPerdo(null)
    if (await muovi(p, 'perso', motivo.trim())) setMotivo('')
  }

  if (righe === null) return <div className="flex justify-center py-16"><Spinner /></div>

  const perse = gruppi.persa

  return (
    <div>
      {guaio && <p className="mb-3 inline-block rounded-full bg-red-50 px-3 py-1 text-[12px] font-semibold text-red-700">{guaio}</p>}
      <div className="grid gap-4 lg:grid-cols-3">
        {COLONNE.map(({ k, nome, vuoto }) => (
          <div key={k}
               onDragOver={(e) => { e.preventDefault(); setSopra(k) }}
               onDragLeave={() => setSopra(null)}
               onDrop={(e) => {
                 e.preventDefault(); setSopra(null)
                 const p = (righe ?? []).find((x) => x.id === e.dataTransfer.getData('text/plain'))
                 if (p) void muovi(p, k === 'si' ? 'follow_up' : k)
               }}
               className={`rounded-2xl p-3 transition-colors ${sopra === k ? 'bg-blu/10 ring-2 ring-blu/40' : 'bg-velo/50'}`}>
            <div className="mb-2 flex items-baseline gap-2 px-1">
              <h2 className="text-[13px] font-extrabold uppercase tracking-[0.04em] text-navy">{nome}</h2>
              <span className="text-[12px] font-bold tabular-nums text-tenue">{gruppi[k].length}</span>
            </div>
            {gruppi[k].length === 0 && <p className="px-2 py-6 text-[13px] leading-relaxed text-tenue">{vuoto}</p>}
            {gruppi[k].map((p) => {
              const { testo, colore } = statoDi(p, k)
              return (
                <div key={p.id} draggable onDragStart={(e) => e.dataTransfer.setData('text/plain', p.id)}
                     className="group mb-2 cursor-grab rounded-2xl border border-bordo bg-white p-3.5 shadow-sm transition-shadow hover:shadow-md active:cursor-grabbing">
                  <button onClick={() => onOpen(p.id)} className="block w-full text-left">
                    <p className="truncate text-[15px] font-extrabold text-navy">{p.company || p.name || p.email}</p>
                    <p className="mt-1 flex items-center gap-1.5 text-[12px] text-tenue">
                      <span className={`h-2 w-2 shrink-0 rounded-full ${colore}`} />
                      <span className="truncate">{testo}</span>
                    </p>
                  </button>
                  <div className="mt-2.5 flex items-center gap-1.5">
                    <button onClick={() => onOpen(p.id)}
                            className="rounded-full bg-blu px-3 py-1.5 text-[11px] font-bold text-white hover:bg-navy">
                      {k === 'si' ? 'Fissa la call' : k === 'conoscitiva' ? 'Dopo la call' : 'Verso il preventivo'}
                    </button>
                    <button onClick={() => { setPerdo(p); setMotivo('') }}
                            className="rounded-full px-2.5 py-1.5 text-[11px] font-semibold text-tenue opacity-0 transition-opacity hover:bg-velo hover:text-inchiostro group-hover:opacity-100">
                      Lascia andare
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        ))}
      </div>

      {/* il cassetto: nulla si cancella davvero */}
      <div className="mt-6">
        <button onClick={() => setCassetto((v) => !v)} className="text-[12px] font-semibold text-tenue hover:text-navy">
          {cassetto ? '▾' : '▸'} Lasciati andare, recuperabili ({perse.length})
        </button>
        {cassetto && (
          <div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {perse.length === 0 && <p className="text-[13px] text-tenue">Nessuno.</p>}
            {perse.map((p) => (
              <div key={p.id} className="flex items-center gap-2 rounded-xl border border-bordo bg-white px-3 py-2">
                <button onClick={() => onOpen(p.id)} className="min-w-0 flex-1 text-left">
                  <p className="truncate text-[13px] font-semibold text-inchiostro">{p.company || p.name || p.email}</p>
                  <p className="truncate text-[11px] text-tenue">{p.lost_reason ?? ''}</p>
                </button>
                <button onClick={() => void muovi(p, 'conoscitiva')}
                        className="shrink-0 rounded-full border border-bordo px-2.5 py-1 text-[11px] font-bold text-navy hover:bg-velo">
                  Riapri
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* lascia andare: il motivo resta nella storia */}
      {perdo && (
        <div className="fixed inset-0 z-[90] flex items-center justify-center px-4" onMouseDown={() => setPerdo(null)}>
          <div className="absolute inset-0 bg-inchiostro/25" />
          <div onMouseDown={(e) => e.stopPropagation()} className="relative w-full max-w-[380px] rounded-2xl border border-bordo bg-white p-4 shadow-xl">
            <p className="text-[15px] font-extrabold text-navy">Lascio andare {perdo.company || perdo.name}?</p>
            <p className="mt-1 text-[12px] text-tenue">Il motivo resta nella storia e lo ritrovi nel cassetto, recuperabile.</p>
            <input autoFocus value={motivo} onChange={(e) => setMotivo(e.target.value)}
                   onKeyDown={(e) => { if (e.key === 'Enter') void lascia() }}
                   placeholder="Il motivo, con parole tue"
                   className="mt-3 w-full rounded-xl border border-bordo p-2.5 text-[13px] focus:border-blu focus:outline-none" />
            <div className="mt-3 flex gap-2">
              <button onClick={() => void lascia()} disabled={!motivo.trim()}
                      className="rounded-full bg-navy px-4 py-2 text-[12px] font-bold text-white disabled:opacity-40">Lascia andare</button>
              <button onClick={() => setPerdo(null)} className="rounded-full border border-bordo px-4 py-2 text-[12px] font-semibold text-tenue">Annulla</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
