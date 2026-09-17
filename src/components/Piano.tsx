import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { creaTask } from '../lib/regole'
import { Spinner } from './ui'
import ClaraLogo from './ClaraLogo'

// IL PIANO DI CLARA (Dre, 17/9): «questo e' top per Clara dopo le call
// oppure per riprendere cose». Gli appunti di una call, o le idee sparse
// che uno si porta in testa, diventano una lista corta di cose da fare con
// una data ciascuna. Si legge, si toglie quello che non serve, si sposta
// una data, e con un clic sono task vere: in Oggi, e sulla scheda del
// cliente. Clara propone, la persona decide: come per tutto il resto.

interface Passo { giorno: string | null; titolo: string; perche: string; prendo: boolean }

interface Props {
  prospectId?: string | null
  azienda?: string | null
  testo?: string | null           // le idee sparse, quando non si parte da una scheda
  onChiudi: () => void
}

const NOMI_GIORNO = ['dom', 'lun', 'mar', 'mer', 'gio', 'ven', 'sab']
function etichettaGiorno(g: string | null): string {
  if (!g) return 'Senza data'
  const d = new Date(`${g}T12:00:00`)
  if (Number.isNaN(d.getTime())) return g
  return `${NOMI_GIORNO[d.getDay()]} ${d.getDate()}/${d.getMonth() + 1}`
}

export default function Piano({ prospectId, azienda, testo, onChiudi }: Props) {
  const [titolo, setTitolo] = useState('')
  const [passi, setPassi] = useState<Passo[] | null>(null)
  const [errore, setErrore] = useState('')
  const [indicazione, setIndicazione] = useState('')
  const [creo, setCreo] = useState(false)
  const [fatte, setFatte] = useState<number | null>(null)

  async function chiedi(come?: string) {
    setPassi(null); setErrore(''); setFatte(null)
    const { data, error } = await supabase.functions.invoke('piano', {
      body: { prospect_id: prospectId ?? null, testo: testo ?? null, indicazione: come ?? null },
    })
    const r = (data ?? {}) as { errore?: string; titolo?: string; passi?: Array<{ giorno: string | null; titolo: string; perche: string }> }
    if (error || r.errore || !r.passi) { setErrore(r.errore ?? error?.message ?? 'Non sono riuscita a fare il piano, riprova.'); setPassi([]); return }
    setTitolo(r.titolo ?? 'Il piano')
    setPassi(r.passi.map((p) => ({ ...p, prendo: true })))
  }
  useEffect(() => { void chiedi() }, [])   // eslint-disable-line react-hooks/exhaustive-deps

  const scelti = (passi ?? []).filter((p) => p.prendo && p.titolo.trim())

  async function crea() {
    if (scelti.length === 0) return
    setCreo(true)
    let n = 0
    for (const p of scelti) {
      const { task } = await creaTask({ titolo: p.titolo.trim(), scadenza: p.giorno, prospect_id: prospectId ?? null })
      if (task) n += 1
    }
    setCreo(false)
    setFatte(n)
  }

  function cambia(i: number, patch: Partial<Passo>) {
    setPassi((ps) => (ps ? ps.map((p, k) => (k === i ? { ...p, ...patch } : p)) : ps))
  }

  // raggruppati per giorno, in ordine: e' quello che rende il piano
  // leggibile in tre secondi
  const giorni = [...new Set((passi ?? []).map((p) => p.giorno ?? ''))].sort((a, b) => (a || '9999').localeCompare(b || '9999'))

  return (
    <div className="fixed inset-0 z-[110] flex items-end justify-center bg-navy/45 p-0 sm:items-center sm:p-6" onClick={onChiudi}>
      <div className="salta-su flex max-h-[92vh] w-full max-w-[560px] flex-col rounded-t-2xl bg-white shadow-[0_18px_50px_rgba(6,23,115,0.3)] sm:rounded-2xl"
           onClick={(e) => e.stopPropagation()}>
        <header className="flex items-center gap-3 border-b border-velo px-5 py-3.5">
          <ClaraLogo size={28} lavora={passi === null || creo} />
          <div className="min-w-0 flex-1">
            <p className="truncate text-[15px] font-extrabold text-navy">{passi === null ? 'Sto mettendo in fila le cose' : titolo}</p>
            <p className="truncate text-[11px] text-tenue">
              {azienda ? `per ${azienda}, ` : ''}{passi === null ? 'leggo gli appunti e la scheda' : 'togli quello che non serve, sposta le date, poi crea le task'}
            </p>
          </div>
          <button onClick={onChiudi} aria-label="Chiudi" className="flex h-8 w-8 items-center justify-center rounded-full text-tenue hover:bg-velo">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="h-4 w-4"><path d="M6 6l12 12M18 6L6 18" /></svg>
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          {passi === null && <div className="flex justify-center py-10"><Spinner /></div>}
          {errore && <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{errore}</p>}

          {fatte !== null ? (
            <div className="py-6 text-center">
              <p className="text-[17px] font-extrabold text-navy">{fatte === 1 ? 'Una task creata' : `${fatte} task create`}</p>
              <p className="mt-1 text-sm text-tenue">
                Le trovi in Oggi{azienda ? `, e sulla scheda di ${azienda}` : ''}. Quando ne spunti una, la prossima è già lì.
              </p>
            </div>
          ) : passi && passi.length > 0 && (
            <div className="space-y-4">
              {giorni.map((g) => (
                <section key={g || 'senza'}>
                  <p className="mb-1.5 text-[11px] font-bold uppercase tracking-[0.08em] text-blu">{etichettaGiorno(g || null)}</p>
                  <ul className="space-y-2">
                    {passi.map((p, i) => (p.giorno ?? '') === g && (
                      <li key={i} className={`flex items-start gap-2.5 rounded-xl border px-3 py-2.5 ${p.prendo ? 'border-bordo bg-white' : 'border-velo bg-velo/40 opacity-60'}`}>
                        <input type="checkbox" checked={p.prendo} onChange={(e) => cambia(i, { prendo: e.target.checked })}
                               className="mt-1 h-4 w-4 shrink-0 accent-blu" aria-label="Tienila" />
                        <div className="min-w-0 flex-1">
                          <textarea value={p.titolo} onChange={(e) => cambia(i, { titolo: e.target.value })}
                                    rows={Math.max(1, Math.ceil(p.titolo.length / 44))}
                                    className="w-full resize-none bg-transparent text-sm font-semibold leading-snug text-navy outline-none" />
                          {p.perche && <p className="mt-0.5 text-xs leading-snug text-tenue">{p.perche}</p>}
                        </div>
                        <input type="date" value={p.giorno ?? ''} onChange={(e) => cambia(i, { giorno: e.target.value || null })}
                               aria-label="Che giorno"
                               className="w-[118px] shrink-0 rounded-md border border-bordo px-1.5 py-1 text-[11px] text-navy outline-none focus:border-blu" />
                      </li>
                    ))}
                  </ul>
                </section>
              ))}
            </div>
          )}
        </div>

        {passi && passi.length > 0 && fatte === null && (
          <footer className="space-y-2.5 border-t border-velo px-5 py-3.5">
            <div className="flex items-center gap-2">
              <input value={indicazione} onChange={(e) => setIndicazione(e.target.value)}
                     onKeyDown={(e) => { if (e.key === 'Enter' && indicazione.trim()) void chiedi(indicazione.trim()) }}
                     placeholder="Rifallo diverso: più corto, in due settimane, solo la parte tecnica…"
                     className="min-w-0 flex-1 rounded-full border border-bordo px-3.5 py-1.5 text-xs outline-none focus:border-blu" />
              <button onClick={() => void chiedi(indicazione.trim() || undefined)}
                      className="shrink-0 rounded-full border border-bordo px-3.5 py-1.5 text-xs font-semibold text-navy hover:border-navy">
                Rifai
              </button>
            </div>
            <div className="flex items-center justify-end gap-2">
              <button onClick={onChiudi} className="rounded-full px-4 py-2 text-xs font-semibold text-tenue hover:text-inchiostro">Lascia stare</button>
              <button onClick={() => void crea()} disabled={scelti.length === 0 || creo}
                      className="rounded-full bg-blu px-5 py-2 text-sm font-bold text-white hover:bg-blu-scuro disabled:opacity-30">
                {creo ? 'Le creo' : scelti.length === 1 ? 'Crea la task' : `Crea ${scelti.length} task`}
              </button>
            </div>
          </footer>
        )}
        {fatte !== null && (
          <footer className="flex justify-end border-t border-velo px-5 py-3.5">
            <button onClick={onChiudi} className="rounded-full bg-blu px-5 py-2 text-sm font-bold text-white hover:bg-blu-scuro">Fatto</button>
          </footer>
        )}
      </div>
    </div>
  )
}
