import { useEffect, useState } from 'react'
import { supabase } from '../../lib/supabase'
import type { AgendaItem, Interaction, PipelineStage, Prospect } from '../../lib/types'
import { marcaFase, ultimoMovimento } from '../../lib/regole'
import { CAMMINO, IN_TRATTATIVA, NOME_TAPPA, precedente, prossima, tappaDi, toccaANoi, type Tappa } from '../../lib/percorso'
import { daysAgo, fmtDateShort, giorni } from '../ui'
import type { Esegui } from './Aziende'

// IL PANNELLO DI UN'AZIENDA (Dre, 30/9: «se vado nella scheda del cliente non posso
// mandare avanti da la', devo uscire»). Da qui si fa tutto quello che serve ogni
// giorno: avanzare, dire di chi e' la palla e qual e' il prossimo passo, aggiungere
// una nota o il riassunto della call, leggere la storia. Il resto (preventivi,
// progetti, documenti, prezzo) sta nella scheda completa, a un tocco.

const CHI: Record<string, string> = {
  email_in: 'Loro', email_out: 'Noi', followup: 'Noi, follow-up', analisi: 'Analisi', call: 'Call',
  nota: 'Nota', transcript: 'Riassunto call', postit: 'Post-it', prep: 'Preparazione',
}

// la nostra mail citata sotto la loro non e' storia loro (lettura.solo_suo, 29/9)
function soloLoro(b: string): string {
  const t = b.replace(/\r/g, '')
  const m = t.search(/\n\s*(?:>|il giorno\s|on .{0,80}wrote:|da:\s|from:\s|-{3,}\s*original)|\b(?:il|on)\s[^\n]{0,120}?\d{1,2}[:.]\d{2}[^\n]{0,120}?(?:ha scritto|wrote)\s*:/i)
  return (m > 0 ? t.slice(0, m) : t).replace(/\s+/g, ' ').trim()
}

interface Fatto { quando: string; chi: string; testo: string }

export default function Pannello({ p, bozze, onChiudi, onEsegui, onIndietro, onCambiato, onScheda }: {
  p: Prospect; bozze: number; onChiudi: () => void; onEsegui: Esegui
  onIndietro: (verso: Tappa | 'lead') => void; onCambiato: (p: Prospect) => void; onScheda: () => void
}) {
  const t = tappaDi(p)
  const avanti = prossima(t)
  const dietro = precedente(t)
  const [storia, setStoria] = useState<Fatto[] | null>(null)
  const [tutta, setTutta] = useState(false)
  const [passo, setPasso] = useState(p.next_action ?? '')
  const [data, setData] = useState(p.next_action_date ?? '')
  const [testo, setTesto] = useState('')
  const [riassunto, setRiassunto] = useState(false)
  const [perso, setPerso] = useState<string | null>(null)
  const [lavoro, setLavoro] = useState(false)
  const [guaio, setGuaio] = useState<string | null>(null)
  const [giro, setGiro] = useState(0)

  useEffect(() => {
    let vivo = true
    void Promise.all([
      supabase.from('interactions').select('id,at,kind,body').eq('prospect_id', p.id).order('at', { ascending: false }).limit(60),
      supabase.from('agenda').select('id,at,titolo').eq('prospect_id', p.id).order('at', { ascending: false }).limit(20),
    ]).then(([i, a]) => {
      if (!vivo) return
      const fatti: Fatto[] = [
        ...((i.data as Interaction[]) ?? []).map((x) => ({ quando: x.at, chi: CHI[x.kind] ?? x.kind, testo: x.kind === 'email_in' ? soloLoro(x.body ?? '') : (x.body ?? '').replace(/\s+/g, ' ').trim() })),
        ...((a.data as AgendaItem[]) ?? []).map((x) => ({ quando: x.at, chi: new Date(x.at) > new Date() ? 'In calendario' : 'Call', testo: x.titolo })),
      ].sort((x, y) => y.quando.localeCompare(x.quando))
      setStoria(fatti)
    })
    return () => { vivo = false }
  }, [p.id, giro])

  useEffect(() => {
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape' && !(e.target instanceof HTMLTextAreaElement) && !(e.target instanceof HTMLInputElement)) onChiudi() }
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [onChiudi])

  async function salvaPasso() {
    const na = passo.trim() || null, nd = data || null
    if (na === (p.next_action ?? null) && nd === (p.next_action_date ?? null)) return
    const { data: x } = await supabase.from('prospects').update({ next_action: na, next_action_date: nd }).eq('id', p.id).select().single()
    if (x) onCambiato(x as Prospect)
  }

  async function aggiungi() {
    const s = testo.trim()
    if (!s || lavoro) return
    setLavoro(true)
    const kind = riassunto && ['conoscitiva', 'tecnica', 'avvio'].includes(t) ? 'transcript' : 'nota'
    const body = kind === 'transcript' ? `${marcaFase(t as PipelineStage)} ${s}` : s
    const { error } = await supabase.from('interactions').insert({ prospect_id: p.id, at: new Date().toISOString(), kind, body })
    setLavoro(false)
    // 5/10: se non si salva, il testo resta li' e si dice perche' (prima si svuotava comunque)
    if (error) { setGuaio(`Non salvata: ${error.message}. Il testo è ancora qui, riprova.`); return }
    setGuaio(null); setTesto(''); setRiassunto(false); setGiro((g) => g + 1)
  }

  async function muovi(verso: Tappa | 'lead', motivo?: string) {
    setLavoro(true)
    const ok = await onEsegui(p, verso, { motivo })
    setLavoro(false)
    if (ok) { setPerso(null); setGiro((g) => g + 1) }
  }

  const nostra = toccaANoi(p, bozze > 0)
  // ogni azienda in trattativa ha sempre un prossimo passo con la data (Falcon, vincolo 2)
  const senzaPasso = IN_TRATTATIVA.includes(t) && !p.next_action_date
  const fermo = daysAgo(ultimoMovimento(p))
  const telefono = p.phone?.replace(/\s+/g, '')
  const diCall = ['conoscitiva', 'tecnica', 'avvio'].includes(t)
  const fatti = storia ? (tutta ? storia : storia.slice(0, 8)) : []

  return (
    <div className="fixed inset-0 z-[70] flex justify-end bg-black/10" onClick={onChiudi}>
      <aside onClick={(e) => e.stopPropagation()}
             className="flex h-full w-full flex-col overflow-y-auto bg-white shadow-[-8px_0_30px_rgba(16,24,40,0.10)] sm:w-[520px]">
        <div className="sticky top-0 z-10 flex items-center gap-3 border-b border-bordo bg-white/95 px-5 py-3 backdrop-blur">
          <button onClick={onChiudi} className="text-sm font-semibold text-blu hover:text-navy">‹ Chiudi</button>
          <span className="flex-1" />
          <button onClick={onScheda} className="text-sm font-semibold text-tenue hover:text-navy">Scheda completa ›</button>
        </div>

        <div className="space-y-6 px-5 py-5">
          {/* chi e', e a che tappa */}
          <div>
            <h2 className="text-[22px] font-extrabold leading-tight text-navy">{p.company || p.name || p.email}</h2>
            {(p.city || p.website) && (
              <p className="mt-0.5 text-sm text-tenue">
                {p.city}{p.city && p.website ? ', ' : ''}
                {p.website && <a href={p.website.startsWith('http') ? p.website : `https://${p.website}`} target="_blank" rel="noreferrer" className="hover:text-blu">{p.website.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '')}</a>}
              </p>
            )}
            <ol className="mt-4 flex flex-wrap gap-x-1 gap-y-1.5">
              {CAMMINO.map((k, i) => {
                const qui = k === t, fatta = t !== 'perso' && CAMMINO.indexOf(t) > i
                return (
                  <li key={k} className={`rounded-full px-2.5 py-1 text-[11.5px] font-semibold ${qui ? 'bg-navy text-white' : fatta ? 'text-navy' : 'text-spento'}`}>
                    {NOME_TAPPA[k]}
                  </li>
                )
              })}
              {t === 'perso' && <li className="rounded-full bg-red-50 px-2.5 py-1 text-[11.5px] font-semibold text-red-700">Perso{p.lost_reason ? `: ${p.lost_reason}` : ''}</li>}
            </ol>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              {avanti && t !== 'perso' && (
                <button onClick={() => void muovi(avanti)} disabled={lavoro}
                        className="rounded-full bg-blu px-5 py-2 text-sm font-bold text-white hover:bg-blu-scuro disabled:opacity-50">
                  Avanza a {NOME_TAPPA[avanti]}
                </button>
              )}
              {t === 'perso' && (
                <button onClick={() => void muovi('conoscitiva')} disabled={lavoro}
                        className="rounded-full bg-blu px-5 py-2 text-sm font-bold text-white disabled:opacity-50">Riapri</button>
              )}
              {dietro && t !== 'perso' && (
                <button onClick={() => onIndietro(dietro)} className="rounded-full px-3 py-2 text-sm font-semibold text-tenue hover:text-navy">
                  Indietro
                </button>
              )}
              {t !== 'perso' && t !== 'cliente' && (
                <button onClick={() => setPerso(perso === null ? '' : null)} className="rounded-full px-3 py-2 text-sm font-semibold text-tenue hover:text-red-700">
                  Perso
                </button>
              )}
            </div>
            {perso !== null && (
              <div className="mt-3 flex gap-2">
                <input autoFocus value={perso} onChange={(e) => setPerso(e.target.value)} placeholder="Perché? Resta nella storia"
                       onKeyDown={(e) => { if (e.key === 'Enter') void muovi('perso', perso) }}
                       className="min-w-0 flex-1 rounded-xl border border-bordo px-3 py-2 text-sm outline-none focus:border-red-600" />
                <button onClick={() => void muovi('perso', perso)} disabled={!perso.trim() || lavoro}
                        className="rounded-full bg-red-700 px-4 py-2 text-sm font-bold text-white disabled:opacity-40">Segna perso</button>
              </div>
            )}
          </div>

          {/* di chi e' la palla, e il prossimo passo: le tre cose che ogni azienda ha sempre (Falcon) */}
          <div className="rounded-xl border border-bordo p-4">
            <p className={`text-sm font-bold ${nostra ? 'text-red-700' : senzaPasso ? 'text-amber-700' : 'text-inchiostro'}`}>
              {bozze > 0 ? 'Tocca a te: la bozza è pronta in Posta'
                : senzaPasso && !p.awaiting_us ? 'Manca il prossimo passo: scrivilo qui sotto, con la data'
                : p.awaiting_us ? `Tocca a te: ha scritto${p.last_reply_at ? ` il ${fmtDateShort(p.last_reply_at)}` : ''}`
                : nostra ? 'Tocca a te: il prossimo passo è scaduto'
                : `Tocca a loro${fermo !== null && fermo >= 1 ? `, da ${giorni(fermo)}` : ''}`}
            </p>
            <div className="mt-3 flex flex-col gap-2 sm:flex-row">
              <input value={passo} onChange={(e) => setPasso(e.target.value)} onBlur={() => void salvaPasso()}
                     placeholder="Prossimo passo, per esempio: mandare la proposta"
                     className="min-w-0 flex-1 rounded-xl border border-bordo px-3 py-2 text-sm outline-none focus:border-blu" />
              <input type="date" value={data} onChange={(e) => setData(e.target.value)} onBlur={() => void salvaPasso()}
                     className="rounded-xl border border-bordo px-3 py-2 text-sm outline-none focus:border-blu" />
            </div>
          </div>

          {/* come contattarlo */}
          {(p.name || p.email || p.phone) && (
            <div className="text-sm">
              {p.name && <p className="font-semibold text-inchiostro">{p.name}{p.role ? <span className="font-normal text-tenue">, {p.role}</span> : null}</p>}
              <p className="mt-0.5 flex flex-wrap gap-x-4 gap-y-1">
                {p.email && <a href={`mailto:${p.email}`} className="text-blu hover:underline">{p.email}</a>}
                {telefono && <a href={`tel:${telefono}`} className="text-blu hover:underline">{p.phone}</a>}
              </p>
            </div>
          )}

          {/* un posto solo per aggiungere */}
          <div>
            {guaio && <p className="mb-1.5 text-[12px] font-semibold text-red-700">{guaio}</p>}
            <textarea value={testo} onChange={(e) => setTesto(e.target.value)} rows={3}
                      placeholder={diCall ? 'Una nota, o il riassunto della call' : 'Una nota: cosa è successo, cosa ricordare'}
                      className="w-full resize-y rounded-xl border border-bordo px-3 py-2.5 text-sm outline-none focus:border-blu" />
            <div className="mt-2 flex items-center gap-3">
              {diCall && (
                <label className="flex items-center gap-2 text-[13px] text-tenue">
                  <input type="checkbox" checked={riassunto} onChange={(e) => setRiassunto(e.target.checked)} />
                  È il riassunto della call {NOME_TAPPA[t]}
                </label>
              )}
              <button onClick={() => void aggiungi()} disabled={!testo.trim() || lavoro}
                      className="ml-auto rounded-full bg-navy px-4 py-1.5 text-sm font-bold text-white disabled:opacity-40">Aggiungi</button>
            </div>
          </div>

          {/* la storia, la piu' recente in alto */}
          <div>
            <h3 className="mb-2 text-[11px] font-bold uppercase tracking-[0.06em] text-navy">Storia</h3>
            {!storia ? <p className="text-sm text-spento">Leggo…</p> : fatti.length === 0 ? <p className="text-sm text-spento">Ancora niente.</p> : (
              <ul className="space-y-2.5">
                {fatti.map((f, i) => (
                  <li key={i} className="flex gap-3 text-[13px] leading-relaxed">
                    <span className="w-14 shrink-0 tabular-nums text-spento">{fmtDateShort(f.quando)}</span>
                    <span className="min-w-0"><b className="font-semibold text-inchiostro">{f.chi}</b> <span className="text-tenue">{f.testo.length > 260 ? `${f.testo.slice(0, 260)}…` : f.testo}</span></span>
                  </li>
                ))}
              </ul>
            )}
            {storia && storia.length > 8 && !tutta && (
              <button onClick={() => setTutta(true)} className="mt-3 text-xs font-semibold text-blu hover:text-navy">Tutta la storia ({storia.length})</button>
            )}
          </div>
        </div>
      </aside>
    </div>
  )
}
