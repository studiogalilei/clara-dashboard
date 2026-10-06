import { useEffect, useMemo, useState } from 'react'
import { supabase } from '../lib/supabase'
import type { Prospect } from '../lib/types'

// IL TRIAGE FUORI TARGET (Dre, a voce, 6/10): «la soppressione non la fa il
// sistema. Se non supera il Google Fit mi scrive fuori target, col motivo, e
// io ho due opzioni: sopprimerlo, oppure inviare comunque».
//
// Sta in testa alla Pipeline: chiuso e' una riga sottile col conteggio, aperto
// e' una lista piatta: azienda, il motivo del fit, cosa ha scritto LUI (il
// contesto del prima), un commento libero e le due scelte. La decisione finisce
// nel prospect (enriched.google_fit_decisione), nella storia, e per il
// soppresso anche in suppressions: il motore la legge da li'.

interface FitRiga {
  p: Prospect
  motivo: string
}

function fitDi(p: Prospect): { verdetto: string | null; motivo: string | null; decisione: string | null } {
  const e = (p.enriched ?? {}) as Record<string, unknown>
  const v2 = e.google_fit_v2 as { verdetto?: string; motivo?: string } | undefined
  const v1 = e.google_fit as { verdetto?: string } | undefined
  return {
    verdetto: v2?.verdetto ?? v1?.verdetto ?? null,
    motivo: v2?.motivo ?? (v1?.verdetto === 'NO' ? 'il Google Fit vecchio ha detto no (senza motivo scritto)' : null),
    decisione: (e.google_fit_decisione as string) ?? null,
  }
}

const VIVE = new Set(['positivo', 'tiepido', 'rinvio', 'da_classificare'])

export function daDecidere(righe: Prospect[]): FitRiga[] {
  return righe
    .filter((p) => {
      const { verdetto, decisione } = fitDi(p)
      return verdetto === 'NO' && !decisione && !p.fuori
        && VIVE.has(p.classificazione ?? 'da_classificare')
    })
    .map((p) => ({ p, motivo: fitDi(p).motivo ?? 'fuori target' }))
    .sort((a, b) => (b.p.last_reply_at ?? '').localeCompare(a.p.last_reply_at ?? ''))
}

export default function Triage({ righe, onOpen, onDeciso }: {
  righe: Prospect[]
  onOpen: (id: string) => void
  onDeciso: (id: string) => void       // il padre toglie la riga dalla sua lista
}) {
  const [aperto, setAperto] = useState(false)
  const [parole, setParole] = useState<Record<string, string>>({})   // cosa ha scritto lui
  const [commenti, setCommenti] = useState<Record<string, string>>({})
  const [guaio, setGuaio] = useState<string | null>(null)
  const [scrivo, setScrivo] = useState<string | null>(null)

  const lista = useMemo(() => daDecidere(righe), [righe])

  // il contesto del prima: l'ultima cosa che HA SCRITTO LUI, mai quella dopo
  useEffect(() => {
    if (!aperto || lista.length === 0) return
    const ids = lista.map((r) => r.p.id).filter((id) => !(id in parole))
    if (!ids.length) return
    void supabase.from('interactions').select('prospect_id,at,body')
      .in('prospect_id', ids).eq('kind', 'email_in')
      .order('at', { ascending: false }).limit(ids.length * 4)
      .then(({ data }) => {
        const out: Record<string, string> = {}
        for (const r of ((data as Array<{ prospect_id: string; body: string | null }>) ?? [])) {
          if (!(r.prospect_id in out)) out[r.prospect_id] = (r.body ?? '').replace(/\s+/g, ' ').trim().slice(0, 180)
        }
        setParole((v) => ({ ...v, ...out }))
      })
  }, [aperto, lista])   // eslint-disable-line react-hooks/exhaustive-deps

  async function decidi(r: FitRiga, scelta: 'invia' | 'soppresso') {
    const p = r.p
    setScrivo(p.id)
    setGuaio(null)
    const commento = (commenti[p.id] ?? '').trim()
    const enriched = {
      ...(p.enriched ?? {}),
      google_fit_decisione: scelta,
      google_fit_deciso_il: new Date().toISOString(),
      ...(commento ? { google_fit_commento: commento } : {}),
    }
    const patch = scelta === 'soppresso'
      ? { enriched, classificazione: 'soppresso', awaiting_us: false, no_followup: true }
      : { enriched }
    const { error } = await supabase.from('prospects').update(patch).eq('id', p.id)
    if (error) { setGuaio(`Non ho salvato la decisione: ${error.message}`); setScrivo(null); return }
    if (scelta === 'soppresso' && p.email) {
      const { error: e2 } = await supabase.from('suppressions').insert({
        kind: 'email', email: p.email, pid: p.id,
        reason: `fuori target: ${r.motivo}${commento ? `. ${commento}` : ''}`, source: 'workspace',
      })
      if (e2) { setGuaio(`Soppresso sulla scheda, ma la riga in suppressions non è nata: ${e2.message}`); setScrivo(null); return }
    }
    const nota = scelta === 'soppresso'
      ? `SOPPRESSO da Dre dal triage fuori target. Motivo del fit: ${r.motivo}${commento ? `. Nota: ${commento}` : ''}`
      : `Fuori target per il fit, ma Dre ha detto di mandare lo stesso. Motivo del fit: ${r.motivo}${commento ? `. Nota: ${commento}` : ''}`
    void supabase.from('interactions').insert({ prospect_id: p.id, at: new Date().toISOString(), kind: 'nota', body: nota })
    setScrivo(null)
    onDeciso(p.id)
  }

  if (lista.length === 0) return null

  return (
    <div className="mb-3 rounded-2xl border border-amber-300 bg-white">
      <button onClick={() => setAperto(!aperto)} className="flex w-full items-center gap-2 px-4 py-2.5 text-left">
        <svg viewBox="0 0 24 24" className="h-[14px] w-[14px] shrink-0 fill-amber-400"><path d="M12 3 22 20H2z" /></svg>
        <span className="text-[13px] font-bold text-amber-900">
          {lista.length === 1 ? '1 fuori target da decidere' : `${lista.length} fuori target da decidere`}
        </span>
        <span className="min-w-0 flex-1 truncate text-[12px] text-tenue">
          {aperto ? '' : 'vogliono l’analisi, ma il Google Fit dice no: scegli tu'}
        </span>
        <span className="shrink-0 text-xs text-spento">{aperto ? '▴' : '▾'}</span>
      </button>
      {aperto && (
        <div className="divide-y divide-velo border-t border-velo px-4">
          {guaio && <p className="py-2 text-[12px] font-semibold text-red-700">{guaio}</p>}
          {lista.map((r) => (
            <div key={r.p.id} className="py-3">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
                <button onClick={() => onOpen(r.p.id)} className="text-[14px] font-extrabold text-navy hover:underline">
                  {r.p.company || r.p.name || r.p.email}
                </button>
                <span className="text-[12px] font-semibold text-amber-900">{r.motivo}</span>
              </div>
              {parole[r.p.id] && (
                <p className="mt-1 text-[12.5px] leading-snug text-tenue">Ha scritto: «{parole[r.p.id]}»</p>
              )}
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <input
                  value={commenti[r.p.id] ?? ''}
                  onChange={(e) => setCommenti((v) => ({ ...v, [r.p.id]: e.target.value }))}
                  placeholder="Una nota, se vuoi"
                  className="w-full max-w-[320px] rounded-full border border-bordo px-3 py-1.5 text-[12px] outline-none focus:border-blu"
                />
                <button onClick={() => void decidi(r, 'invia')} disabled={scrivo === r.p.id}
                        className="rounded-full bg-blu px-3.5 py-1.5 text-[12px] font-bold text-white hover:bg-navy disabled:opacity-40">
                  Invia comunque
                </button>
                <button onClick={() => void decidi(r, 'soppresso')} disabled={scrivo === r.p.id}
                        className="rounded-full border border-red-300 px-3.5 py-1.5 text-[12px] font-bold text-red-700 hover:bg-red-50 disabled:opacity-40">
                  Sopprimi
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
