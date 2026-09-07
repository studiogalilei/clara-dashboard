import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { Card, Dot, Micro, Spinner, fmtDateShort, fmtOra } from './ui'

// WIDGET E ISTRUZIONI: la sala di controllo (Dre, 7/9).
//
// Tre pezzi. LE OPERAZIONI: cosa gira in cloud e ogni quanto, l'ultima
// esecuzione e com'e' andata; la cadenza la cambi qui e il direttore, in
// cloud, la legge. LE ISTRUZIONI: quello che scrivi al cervello di Clara
// prima di ogni cosa, e vale subito. I WIDGET: quello che chiedi, con il suo
// stato. In fondo, i collegamenti.

interface Operazione {
  chiave: string
  nome: string
  cosa: string | null
  comando: string | null
  cadenza_minuti: number
  ora_preferita: string | null
  attiva: boolean
  richiesta_ora: boolean
  ultima_corsa: string | null
  ultimo_esito: string | null
  ultimo_dettaglio: string | null
  ultima_durata_ms: number | null
}
interface Istruzione { chiave: string; titolo: string; testo: string; aggiornata: string }
interface Richiesta {
  id: number; at: string; nome: string; cosa: string; per_chi: string | null
  fonte: string | null; cadenza: string | null; tipo: string; stato: string
}

const CADENZE: Array<[number, string]> = [
  [30, 'ogni mezz\'ora'], [60, 'ogni ora'], [180, 'ogni 3 ore'], [360, 'ogni 6 ore'], [1440, 'una volta al giorno'],
]
const STATO_RICHIESTA: Record<string, [string, string]> = {
  richiesto: ['Richiesto', 'bg-velo text-tenue'],
  in_costruzione: ['In costruzione', 'bg-blu/10 text-blu'],
  attivo: ['Attivo', 'bg-green-50 text-green-800'],
  scartato: ['Scartato', 'bg-gray-100 text-spento'],
}

const COLLEGAMENTI: Array<[string, 'ok' | 'attesa' | 'no', string]> = [
  ['Supabase', 'ok', 'collegato'],
  ['Smartlead', 'ok', 'collegato'],
  ['OpenAI', 'ok', 'il cervello di Clara'],
  ['GitHub', 'ok', 'codice, backup, direttore'],
  ['Porkbun', 'ok', 'collegato'],
  ['Google Ads API', 'ok', 'collegato'],
  ['Google Calendar', 'attesa', 'con l\'utenza tecnica di Workspace'],
  ['Google Drive', 'attesa', 'per i backup, stessa utenza'],
  ['Granola', 'attesa', 'serve la chiave API (piano Business)'],
]

export default function Plugin() {
  const [ops, setOps] = useState<Operazione[] | null>(null)
  const [istr, setIstr] = useState<Istruzione[]>([])
  const [bozze, setBozze] = useState<Record<string, string>>({})
  const [salvata, setSalvata] = useState<string | null>(null)
  const [richieste, setRichieste] = useState<Richiesta[]>([])
  const [nuovo, setNuovo] = useState(false)
  const [r, setR] = useState({ nome: '', cosa: '', per_chi: 'tutti', fonte: '', cadenza: 'ogni giorno' })
  const [problema, setProblema] = useState<string | null>(null)

  function carica() {
    supabase.from('operazioni').select('*').order('ordine', { ascending: true })
      .then(({ data, error }) => {
        if (error) setProblema('La sala di controllo non c\'è ancora sul database: manca schema_v9.')
        setOps((data as Operazione[]) ?? [])
      })
    supabase.from('istruzioni').select('*').order('chiave', { ascending: true })
      .then(({ data }) => {
        const l = (data as Istruzione[]) ?? []
        setIstr(l)
        setBozze(Object.fromEntries(l.map((i) => [i.chiave, i.testo])))
      })
    supabase.from('widget_richieste').select('*').order('at', { ascending: false }).limit(50)
      .then(({ data }) => setRichieste((data as Richiesta[]) ?? []))
  }
  useEffect(() => {
    carica()
    // il direttore scrive mentre guardi: si ricontrolla ogni mezzo minuto
    const t = setInterval(carica, 30000)
    return () => clearInterval(t)
  }, [])

  async function cambia(op: Operazione, patch: Partial<Operazione>) {
    const { error } = await supabase.from('operazioni').update(patch).eq('chiave', op.chiave)
    if (error) { setProblema('Non ho potuto salvare: ' + error.message); return }
    setOps((l) => l!.map((x) => (x.chiave === op.chiave ? { ...x, ...patch } : x)))
  }

  async function salvaIstruzione(chiave: string) {
    const testo = bozze[chiave] ?? ''
    const { error } = await supabase.from('istruzioni')
      .update({ testo, aggiornata: new Date().toISOString() }).eq('chiave', chiave)
    if (error) { setProblema('Non ho potuto salvare: ' + error.message); return }
    setSalvata(chiave)
    setTimeout(() => setSalvata(null), 2000)
  }

  async function chiediWidget() {
    if (!r.nome.trim() || !r.cosa.trim()) return
    const { data, error } = await supabase.from('widget_richieste')
      .insert({ nome: r.nome.trim(), cosa: r.cosa.trim(), per_chi: r.per_chi, fonte: r.fonte || null, cadenza: r.cadenza })
      .select().single()
    if (error) { setProblema('Non ho potuto salvare: ' + error.message); return }
    setRichieste((l) => [data as Richiesta, ...l])
    setR({ nome: '', cosa: '', per_chi: 'tutti', fonte: '', cadenza: 'ogni giorno' })
    setNuovo(false)
  }

  if (ops === null) return <Spinner />

  // il direttore gira ogni 15 minuti: se nessuna operazione accesa e' partita
  // da piu' di un'ora, qualcosa a monte e' fermo, e non deve restare muto
  const vive = ops.filter((o) => o.attiva && o.comando && o.ultima_corsa)
  const ultimaQualsiasi = vive.length ? Math.max(...vive.map((o) => new Date(o.ultima_corsa!).getTime())) : null
  const fermoDa = ultimaQualsiasi ? Math.round((Date.now() - ultimaQualsiasi) / 60000) : null

  return (
    <div className="space-y-4 pb-24 sm:pb-8">
      {fermoDa !== null && fermoDa > 75 && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          Il direttore non fa partire niente da {fermoDa >= 120 ? `${Math.round(fermoDa / 60)} ore` : `${fermoDa} minuti`}: le operazioni potrebbero essere ferme.
        </div>
      )}
      {problema && (
        <div className="flex items-start gap-2 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <span className="flex-1">{problema}</span>
          <button onClick={() => setProblema(null)} className="text-xs font-bold">chiudi</button>
        </div>
      )}

      {/* ── LE OPERAZIONI ─────────────────────────────────────── */}
      <Card>
        <header className="flex items-baseline gap-3 border-b border-velo px-4 py-3">
          <span className="text-[13px] font-bold">Operazioni</span>
          <Micro>in cloud, ogni 15 minuti il direttore fa partire quelle dovute</Micro>
        </header>
        {ops.length === 0 && <p className="px-4 py-4 text-sm text-spento">Nessuna operazione: manca schema_v9.</p>}
        {ops.map((op) => {
          const tono = !op.attiva ? 'spento' : op.ultimo_esito === 'errore' ? 'fermo' : op.ultima_corsa ? 'ok' : 'attesa'
          return (
            <div key={op.chiave} className={`border-b border-velo px-4 py-3 last:border-0 ${op.attiva ? '' : 'opacity-60'}`}>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                <Dot tone={tono} />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold">{op.nome}</p>
                  {op.cosa && <p className="text-xs text-tenue">{op.cosa}</p>}
                </div>
                {op.comando ? (
                  <>
                    <select
                      value={op.cadenza_minuti}
                      onChange={(e) => cambia(op, { cadenza_minuti: Number(e.target.value) })}
                      className="rounded-lg border border-bordo bg-white px-2 py-1 text-xs outline-none focus:border-blu"
                    >
                      {CADENZE.map(([m, nome]) => <option key={m} value={m}>{nome}</option>)}
                    </select>
                    {op.cadenza_minuti >= 1440 && (
                      <input
                        type="time"
                        value={op.ora_preferita ?? '08:00'}
                        onChange={(e) => cambia(op, { ora_preferita: e.target.value })}
                        className="rounded-lg border border-bordo bg-white px-2 py-1 text-xs outline-none focus:border-blu"
                      />
                    )}
                    <button
                      onClick={() => cambia(op, { attiva: !op.attiva })}
                      className={`rounded-full px-3 py-1 text-xs font-bold ${op.attiva ? 'bg-navy text-white' : 'border border-bordo text-tenue'}`}
                    >
                      {op.attiva ? 'accesa' : 'spenta'}
                    </button>
                    <button
                      onClick={() => cambia(op, { richiesta_ora: true })}
                      disabled={op.richiesta_ora || !op.attiva}
                      title="Parte entro 15 minuti"
                      className="rounded-full border border-bordo px-3 py-1 text-xs font-semibold text-tenue hover:border-navy hover:text-navy disabled:opacity-40"
                    >
                      {op.richiesta_ora ? 'in partenza…' : 'Fai ora'}
                    </button>
                  </>
                ) : (
                  <span className="text-xs text-spento">{op.attiva ? 'gira per conto suo' : 'in arrivo'}</span>
                )}
              </div>
              <p className="mt-1.5 pl-5 text-[11px] text-spento">
                {op.ultima_corsa
                  ? <>ultima {fmtDateShort(op.ultima_corsa)} · {fmtOra(op.ultima_corsa)} · <span className={op.ultimo_esito === 'errore' ? 'font-bold text-red-700' : 'text-green-700'}>{op.ultimo_esito}</span>{op.ultima_durata_ms ? ` · ${Math.round(op.ultima_durata_ms / 1000)}s` : ''}{op.ultimo_dettaglio && op.ultimo_esito === 'errore' ? ` · ${op.ultimo_dettaglio.slice(-120)}` : ''}</>
                  : 'mai partita'}
              </p>
            </div>
          )
        })}
      </Card>

      {/* ── LE ISTRUZIONI ─────────────────────────────────────── */}
      <Card>
        <header className="flex items-baseline gap-3 border-b border-velo px-4 py-3">
          <span className="text-[13px] font-bold">Istruzioni a Clara</span>
          <Micro>le legge prima di ogni cosa, e valgono subito</Micro>
        </header>
        {istr.length === 0 && <p className="px-4 py-4 text-sm text-spento">Le istruzioni arrivano con schema_v9.</p>}
        {istr.map((i) => (
          <div key={i.chiave} className="border-b border-velo px-4 py-3 last:border-0">
            <p className="mb-1.5 text-sm font-semibold">{i.titolo}</p>
            <textarea
              value={bozze[i.chiave] ?? ''}
              onChange={(e) => setBozze((b) => ({ ...b, [i.chiave]: e.target.value }))}
              rows={3}
              placeholder="Scrivi come vuoi che faccia. Esempio: «le aziende sotto i 5 dipendenti sono fuori target»."
              className="w-full rounded-lg border border-bordo px-3 py-2 text-sm outline-none focus:border-blu"
            />
            <div className="mt-1.5 flex items-center gap-3">
              <button
                onClick={() => salvaIstruzione(i.chiave)}
                disabled={(bozze[i.chiave] ?? '') === i.testo}
                className="rounded-full bg-navy px-4 py-1 text-xs font-bold text-white disabled:opacity-30"
              >
                Salva
              </button>
              {salvata === i.chiave && <span className="text-xs font-semibold text-green-700">salvato ✓</span>}
              {i.testo && salvata !== i.chiave && <span className="text-[11px] text-spento">aggiornata il {fmtDateShort(i.aggiornata)}</span>}
            </div>
          </div>
        ))}
      </Card>

      {/* ── I WIDGET ──────────────────────────────────────────── */}
      <Card>
        <header className="flex items-center gap-3 border-b border-velo px-4 py-3">
          <span className="text-[13px] font-bold">Widget</span>
          <Micro>quello che chiedi, con il suo stato</Micro>
          <button onClick={() => setNuovo((v) => !v)} className="ml-auto rounded-full bg-navy px-3.5 py-1 text-xs font-bold text-white">
            {nuovo ? 'Annulla' : '+ Chiedi un widget'}
          </button>
        </header>
        {nuovo && (
          <div className="salta-su space-y-2 border-b border-velo bg-velo/40 px-4 py-3">
            <input value={r.nome} onChange={(e) => setR({ ...r, nome: e.target.value })} placeholder="Come lo chiamiamo"
              className="w-full rounded-lg border border-bordo bg-white px-3 py-2 text-sm outline-none focus:border-blu" />
            <textarea value={r.cosa} onChange={(e) => setR({ ...r, cosa: e.target.value })} rows={3}
              placeholder="Cosa deve mostrare o tenere d'occhio. Scrivilo come lo diresti a una segretaria."
              className="w-full rounded-lg border border-bordo bg-white px-3 py-2 text-sm outline-none focus:border-blu" />
            <div className="flex flex-wrap gap-2">
              <input value={r.fonte} onChange={(e) => setR({ ...r, fonte: e.target.value })} placeholder="Da dove prende i dati (Smartlead, Calendar, Stripe…)"
                className="min-w-[240px] flex-1 rounded-lg border border-bordo bg-white px-3 py-2 text-sm outline-none focus:border-blu" />
              <select value={r.cadenza} onChange={(e) => setR({ ...r, cadenza: e.target.value })}
                className="rounded-lg border border-bordo bg-white px-2 py-2 text-sm outline-none focus:border-blu">
                {['ogni ora', 'ogni giorno', 'ogni settimana', 'quando succede'].map((c) => <option key={c}>{c}</option>)}
              </select>
              <select value={r.per_chi} onChange={(e) => setR({ ...r, per_chi: e.target.value })}
                className="rounded-lg border border-bordo bg-white px-2 py-2 text-sm outline-none focus:border-blu">
                <option value="tutti">per tutti</option><option value="ceo">solo per me</option><option value="coordinamento">per il coordinamento</option>
              </select>
            </div>
            <div className="flex justify-end">
              <button onClick={chiediWidget} disabled={!r.nome.trim() || !r.cosa.trim()}
                className="rounded-full bg-navy px-4 py-1.5 text-xs font-bold text-white disabled:opacity-30">
                Chiedilo
              </button>
            </div>
          </div>
        )}
        {richieste.length === 0 && !nuovo && <p className="px-4 py-4 text-sm text-spento">Nessun widget chiesto ancora.</p>}
        {richieste.map((w) => {
          const [eti, classe] = STATO_RICHIESTA[w.stato] ?? [w.stato, 'bg-velo text-tenue']
          return (
            <div key={w.id} className="flex items-start gap-3 border-b border-velo px-4 py-3 last:border-0">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold">{w.nome}</p>
                <p className="text-xs text-tenue">{w.cosa}</p>
                <p className="mt-0.5 text-[11px] text-spento">{[w.fonte, w.cadenza, w.per_chi].filter(Boolean).join(' · ')} · chiesto il {fmtDateShort(w.at)}</p>
              </div>
              <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${classe}`}>{eti}</span>
            </div>
          )
        })}
      </Card>

      {/* ── I COLLEGAMENTI ────────────────────────────────────── */}
      <Card>
        <header className="border-b border-velo px-4 py-3"><span className="text-[13px] font-bold">Collegamenti</span></header>
        {COLLEGAMENTI.map(([nome, stato, nota]) => (
          <div key={nome} className="flex items-center gap-3 border-b border-velo px-4 py-2.5 last:border-0">
            <Dot tone={stato === 'ok' ? 'ok' : stato === 'attesa' ? 'attesa' : 'spento'} />
            <p className="min-w-0 flex-1 text-sm font-semibold">{nome}</p>
            <span className={`shrink-0 text-xs ${stato === 'ok' ? 'text-green-700' : stato === 'attesa' ? 'font-semibold text-amber-700' : 'text-spento'}`}>{nota}</span>
          </div>
        ))}
      </Card>
    </div>
  )
}
