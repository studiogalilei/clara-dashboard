import { useCallback, useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { Card } from './ui'

// IL METRO DELLE RISPOSTE (Dre, 29/9). Una mail alla volta: Dre dice cosa dice LEI,
// con un tocco o con i tasti da 1 a 6. Il modello ha gia' letto la stessa mail, ma
// qui non si vede: se Dre la vedesse, si misurerebbe il modello contro se stesso.
// Con queste etichette scripts/metro.py decide se il lettore unico puo' prendere il
// posto delle quattro regole di oggi.
//
// Il commento e il contesto (Dre, 29/9 sera: «dammi la possibilita' di scrivere
// commenti, qui bisognerebbe avere il contesto»). Il contesto mostra la mail intera,
// con la nostra citata sotto, e quello che era successo PRIMA: mail, call, note. Il
// dopo no, se no si etichetta com'e' finita con l'azienda invece di cosa dice la mail.

const SCELTE: Array<[string, string]> = [
  ['si', 'Sì, vuole'], ['no', 'No'], ['non_scrivere', 'Non scrivetemi più'],
  ['fuori_ufficio', 'Fuori ufficio'], ['rinvio', 'Più avanti'], ['altro', 'Altro'],
]

interface Riga { interaction_id: string; prospect_id: string | null; testo: string; etichetta: string | null; nota: string | null }
interface Fatto { quando: string; cosa: string; testo: string }
interface Contesto { azienda: string | null; intera: string; prima: Fatto[] }

const NOMI: Record<string, string> = {
  email_in: 'Loro', email_out: 'Noi', followup: 'Noi, follow-up', analisi: 'Analisi', call: 'Call', nota: 'Nota', calendario: 'In calendario',
}
const giorno = (iso: string) => new Date(iso).toLocaleDateString('it-IT', { day: 'numeric', month: 'short', year: 'numeric' })

async function leggiContesto(r: Riga): Promise<Contesto> {
  const { data: m } = await supabase.from('interactions').select('at,body').eq('id', r.interaction_id).maybeSingle()
  const mail = m as { at: string; body: string | null } | null
  if (!r.prospect_id || !mail) return { azienda: null, intera: mail?.body ?? r.testo, prima: [] }
  const entro = new Date(new Date(mail.at).getTime() + 14 * 864e5).toISOString()
  const [az, storia, cal] = await Promise.all([
    supabase.from('prospects').select('company').eq('id', r.prospect_id).maybeSingle(),
    supabase.from('interactions').select('id,at,kind,body').eq('prospect_id', r.prospect_id)
      .in('kind', ['email_in', 'email_out', 'followup', 'analisi', 'call', 'nota']).lte('at', mail.at).order('at', { ascending: true }).limit(40),
    // una call fissata poco dopo la mail si sapeva gia' quando l'ha scritta
    supabase.from('agenda').select('at,titolo').eq('prospect_id', r.prospect_id).lte('at', entro).order('at', { ascending: true }).limit(10),
  ])
  const prima: Fatto[] = [
    ...((storia.data ?? []) as Array<{ id: string; at: string; kind: string; body: string | null }>)
      .filter((x) => x.id !== r.interaction_id)
      .map((x) => ({ quando: x.at, cosa: NOMI[x.kind] ?? x.kind, testo: (x.body ?? '').replace(/\s+/g, ' ').slice(0, 280) })),
    ...((cal.data ?? []) as Array<{ at: string; titolo: string | null }>)
      .map((x) => ({ quando: x.at, cosa: NOMI.calendario, testo: x.titolo ?? '' })),
  ].sort((a, b) => a.quando.localeCompare(b.quando))
  return { azienda: (az.data as { company: string | null } | null)?.company ?? null, intera: mail.body ?? r.testo, prima }
}

export default function Metro() {
  const [righe, setRighe] = useState<Riga[] | null>(null)
  const [i, setI] = useState(0)
  const [salvo, setSalvo] = useState(false)
  const [nota, setNota] = useState('')
  const [apri, setApri] = useState(false)
  const [contesto, setContesto] = useState<Contesto | null>(null)

  useEffect(() => {
    supabase.from('metro_risposte').select('interaction_id,prospect_id,testo,etichetta,nota').order('creato_il', { ascending: true }).limit(500)
      .then(({ data }) => {
        const l = (data as Riga[]) ?? []
        setRighe(l)
        const primo = l.findIndex((r) => !r.etichetta)
        setI(primo === -1 ? l.length : primo)
      })
  }, [])

  const r = righe && i < righe.length ? righe[i] : null
  useEffect(() => { setNota(r?.nota ?? '') }, [r?.interaction_id])  // eslint-disable-line react-hooks/exhaustive-deps

  // il contesto si legge solo se e' aperto, e resta aperto passando alla mail dopo
  useEffect(() => {
    let vivo = true
    setContesto(null)
    if (apri && r) void leggiContesto(r).then((c) => { if (vivo) setContesto(c) })
    return () => { vivo = false }
  }, [apri, r?.interaction_id])  // eslint-disable-line react-hooks/exhaustive-deps

  const salvaNota = useCallback(async () => {
    if (!r || (r.nota ?? '') === nota.trim()) return
    const n = nota.trim() || null
    await supabase.from('metro_risposte').update({ nota: n }).eq('interaction_id', r.interaction_id)
    setRighe((l) => (l ?? []).map((x) => (x.interaction_id === r.interaction_id ? { ...x, nota: n } : x)))
  }, [r, nota])

  const scegli = useCallback(async (etichetta: string) => {
    if (!righe || !r || salvo) return
    setSalvo(true)
    const n = nota.trim() || null
    await supabase.from('metro_risposte').update({ etichetta, nota: n, etichettata_il: new Date().toISOString() }).eq('interaction_id', r.interaction_id)
    setRighe((l) => (l ?? []).map((x, k) => (k === i ? { ...x, etichetta, nota: n } : x)))
    const dopo = righe.findIndex((x, k) => k > i && !x.etichetta)
    setI(dopo === -1 ? righe.length : dopo)
    setSalvo(false)
  }, [righe, r, i, salvo, nota])

  useEffect(() => {
    function tasto(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (e.metaKey || e.ctrlKey || e.altKey) return        // Cmd+C copia, Cmd+1 cambia scheda: non sono etichette
      const n = Number(e.key)
      if (n >= 1 && n <= SCELTE.length) { e.preventDefault(); void scegli(SCELTE[n - 1][0]) }
      if (e.key === 'ArrowLeft' && i > 0) { void salvaNota(); setI(i - 1) }
      if (e.key === 'c') setApri((a) => !a)
    }
    window.addEventListener('keydown', tasto)
    return () => window.removeEventListener('keydown', tasto)
  }, [scegli, salvaNota, i])

  if (!righe) return null
  const fatte = righe.filter((x) => x.etichetta).length
  if (righe.length === 0) return <Card className="p-5 text-sm text-tenue">Il metro è vuoto: lo prepara Clara.</Card>
  if (!r) {
    return (
      <Card className="p-6">
        <p className="text-lg font-extrabold text-navy">Fatto: {fatte} di {righe.length}.</p>
        <p className="mt-1 text-sm text-tenue">Adesso Clara misura il lettore nuovo contro le regole di oggi e ti porta i numeri.</p>
        <button onClick={() => setI(0)} className="mt-3 rounded-full border border-bordo px-3 py-1 text-xs font-semibold text-navy">Rivedi dall'inizio</button>
      </Card>
    )
  }
  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-3 flex items-center gap-3">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-velo">
          <div className="h-full rounded-full bg-blu transition-[width] duration-200" style={{ width: `${(fatte / righe.length) * 100}%` }} />
        </div>
        <span className="text-xs font-semibold tabular-nums text-tenue">{fatte} di {righe.length}</span>
      </div>
      <Card className="p-5">
        <p className="text-[11px] font-bold uppercase tracking-[0.06em] text-navy">Cosa dice questa mail?</p>
        <p className="mt-2 whitespace-pre-wrap text-[15px] leading-relaxed text-inchiostro">{r.testo}</p>
        <button onClick={() => setApri((a) => !a)} className="mt-3 text-xs font-semibold text-blu hover:text-navy">
          {apri ? 'Chiudi il contesto' : 'Contesto'} <span className="text-spento">C</span>
        </button>
        {apri && (
          <div className="mt-3 border-t border-bordo pt-3 text-[13px] leading-relaxed">
            {!contesto ? <p className="text-tenue">Leggo…</p> : (
              <>
                {contesto.azienda && <p className="mb-2 font-bold text-navy">{contesto.azienda}</p>}
                {contesto.prima.length === 0 && <p className="text-tenue">Niente prima di questa mail.</p>}
                <ul className="space-y-1.5">
                  {contesto.prima.map((f, k) => (
                    <li key={k} className="flex gap-2">
                      <span className="w-24 shrink-0 tabular-nums text-tenue">{giorno(f.quando)}</span>
                      <span><b className="text-inchiostro">{f.cosa}</b> <span className="text-tenue">{f.testo}</span></span>
                    </li>
                  ))}
                </ul>
                <details className="mt-3">
                  <summary className="cursor-pointer text-xs font-semibold text-tenue hover:text-navy">La mail intera, con la nostra sotto</summary>
                  <p className="mt-2 max-h-72 overflow-y-auto whitespace-pre-wrap rounded-lg bg-velo p-3 text-[12px] text-tenue">{contesto.intera}</p>
                </details>
              </>
            )}
          </div>
        )}
      </Card>
      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
        {SCELTE.map(([k, nome], n) => (
          <button key={k} onClick={() => void scegli(k)} disabled={salvo}
                  className={`flex items-center justify-between rounded-xl border px-4 py-3 text-left text-sm font-bold disabled:opacity-50 ${
                    r.etichetta === k ? 'border-blu bg-blu text-white' : 'border-bordo bg-white text-navy hover:border-blu'
                  }`}>
            {nome}<span className={`text-[11px] font-semibold ${r.etichetta === k ? 'text-white/80' : 'text-spento'}`}>{n + 1}</span>
          </button>
        ))}
      </div>
      <textarea value={nota} onChange={(e) => setNota(e.target.value)} onBlur={() => void salvaNota()}
                onKeyDown={(e) => { if (e.key === 'Escape') (e.target as HTMLTextAreaElement).blur() }}
                rows={2} placeholder="Commento: il perché, quello che la mail non dice"
                className="mt-3 w-full resize-y rounded-xl border border-bordo bg-white px-4 py-3 text-sm text-inchiostro placeholder:text-spento focus:border-blu focus:outline-none" />
      {i > 0 && <button onClick={() => { void salvaNota(); setI(i - 1) }} className="mt-2 text-xs font-semibold text-tenue hover:text-navy">‹ Indietro</button>}
    </div>
  )
}
