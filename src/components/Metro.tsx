import { useCallback, useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { Card } from './ui'

// IL METRO, LA PAGINA DEGLI ESAMI (Dre, 29/9 e 1/10: «così tiriamo fuori le robe
// del mio cervello»). Un caso alla volta: Dre risponde con un tocco o coi tasti,
// e un commento libero tiene il perché. Prima l'esame delle risposte (metro_risposte,
// le 150 mail), poi ogni esame nuovo da metro_casi (schema_v73): seguiti, persi,
// prezzi... La proposta del sistema NON si mostra mai: se Dre la vedesse, si
// misurerebbe il sistema contro se stesso.
//
// Il contesto (29/9, su sua richiesta): la storia PRIMA del caso, mai il dopo,
// se no si etichetta com'è finita invece di cosa dice il caso.

const SCELTE_RISPOSTE: Array<[string, string]> = [
  ['si', 'Sì, vuole'], ['no', 'No'], ['non_scrivere', 'Non scrivetemi più'],
  ['fuori_ufficio', 'Fuori ufficio'], ['rinvio', 'Più avanti'], ['altro', 'Altro'],
]

interface Blocco { eti?: string; testo: string }
interface Caso {
  tavola: 'metro_risposte' | 'metro_casi'
  chiave: string | number
  prospect_id: string | null
  domanda: string
  blocchi: Blocco[]
  scelte: Array<[string, string]>
  etichetta: string | null
  nota: string | null
  interaction_id?: string
}

interface Fatto { quando: string; cosa: string; testo: string }
interface Contesto { azienda: string | null; intera: string | null; prima: Fatto[] }

const NOMI: Record<string, string> = {
  email_in: 'Loro', email_out: 'Noi', followup: 'Noi, follow-up', analisi: 'Analisi', call: 'Call', nota: 'Nota', transcript: 'Riassunto call', calendario: 'In calendario',
}
const giorno = (iso: string) => new Date(iso).toLocaleDateString('it-IT', { day: 'numeric', month: 'short', year: 'numeric' })

async function leggiContesto(c: Caso): Promise<Contesto> {
  let riferimento = new Date().toISOString()
  let intera: string | null = null
  if (c.interaction_id) {
    const { data: m } = await supabase.from('interactions').select('at,body').eq('id', c.interaction_id).maybeSingle()
    if (m) { riferimento = (m as { at: string }).at; intera = (m as { body: string | null }).body }
  }
  if (!c.prospect_id) return { azienda: null, intera, prima: [] }
  const entro = new Date(new Date(riferimento).getTime() + 14 * 864e5).toISOString()
  const [az, storia, cal] = await Promise.all([
    supabase.from('prospects').select('company').eq('id', c.prospect_id).maybeSingle(),
    supabase.from('interactions').select('id,at,kind,body').eq('prospect_id', c.prospect_id)
      .in('kind', ['email_in', 'email_out', 'followup', 'analisi', 'call', 'nota', 'transcript']).lte('at', riferimento).order('at', { ascending: false }).limit(40),
    supabase.from('agenda').select('at,titolo').eq('prospect_id', c.prospect_id).lte('at', entro).order('at', { ascending: true }).limit(10),
  ])
  const prima: Fatto[] = [
    ...((storia.data ?? []) as Array<{ id: string; at: string; kind: string; body: string | null }>).reverse()
      .filter((x) => x.id !== c.interaction_id)
      .map((x) => ({ quando: x.at, cosa: NOMI[x.kind] ?? x.kind, testo: (x.body ?? '').replace(/\s+/g, ' ').slice(0, 280) })),
    ...((cal.data ?? []) as Array<{ at: string; titolo: string | null }>)
      .map((x) => ({ quando: x.at, cosa: NOMI.calendario, testo: x.titolo ?? '' })),
  ].sort((a, b) => a.quando.localeCompare(b.quando))
  return { azienda: (az.data as { company: string | null } | null)?.company ?? null, intera, prima }
}

export default function Metro() {
  const [casi, setCasi] = useState<Caso[] | null>(null)
  const [i, setI] = useState(0)
  const [salvo, setSalvo] = useState(false)
  const [nota, setNota] = useState('')
  const [apri, setApri] = useState(false)
  const [contesto, setContesto] = useState<Contesto | null>(null)

  useEffect(() => {
    void (async () => {
      const [r, k] = await Promise.all([
        supabase.from('metro_risposte').select('interaction_id,prospect_id,testo,etichetta,nota').order('creato_il', { ascending: true }).limit(500),
        // MAI leggere `proposta`: Dre non deve vederla, e l'invariante lo controlla
        supabase.from('metro_casi').select('id,tema,prospect_id,domanda,mostra,scelte,etichetta,nota').order('creato_il', { ascending: true }).limit(500),
      ])
      const lista: Caso[] = [
        ...(((r.data ?? []) as Array<{ interaction_id: string; prospect_id: string | null; testo: string; etichetta: string | null; nota: string | null }>).map((x) => ({
          tavola: 'metro_risposte' as const, chiave: x.interaction_id, interaction_id: x.interaction_id, prospect_id: x.prospect_id,
          domanda: 'Cosa dice questa mail?', blocchi: [{ testo: x.testo }], scelte: SCELTE_RISPOSTE, etichetta: x.etichetta, nota: x.nota,
        }))),
        ...(((k.data ?? []) as Array<{ id: number; prospect_id: string | null; domanda: string; mostra: Blocco[]; scelte: Array<[string, string]>; etichetta: string | null; nota: string | null }>).map((x) => ({
          tavola: 'metro_casi' as const, chiave: x.id, prospect_id: x.prospect_id,
          domanda: x.domanda, blocchi: x.mostra ?? [], scelte: x.scelte ?? [], etichetta: x.etichetta, nota: x.nota,
        }))),
      ]
      setCasi(lista)
      const primo = lista.findIndex((c) => !c.etichetta)
      setI(primo === -1 ? lista.length : primo)
    })()
  }, [])

  const c = casi && i < casi.length ? casi[i] : null
  useEffect(() => { setNota(c?.nota ?? '') }, [c?.tavola, c?.chiave])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    let vivo = true
    setContesto(null)
    if (apri && c) void leggiContesto(c).then((x) => { if (vivo) setContesto(x) })
    return () => { vivo = false }
  }, [apri, c?.chiave])  // eslint-disable-line react-hooks/exhaustive-deps

  const colonna = (x: Caso) => (x.tavola === 'metro_risposte' ? 'interaction_id' : 'id')

  const salvaNota = useCallback(async () => {
    if (!c || (c.nota ?? '') === nota.trim()) return
    const n = nota.trim() || null
    await supabase.from(c.tavola).update({ nota: n }).eq(colonna(c), c.chiave)
    setCasi((l) => (l ?? []).map((x) => (x.chiave === c.chiave && x.tavola === c.tavola ? { ...x, nota: n } : x)))
  }, [c, nota])

  const scegli = useCallback(async (etichetta: string) => {
    if (!casi || !c || salvo) return
    setSalvo(true)
    const n = nota.trim() || null
    await supabase.from(c.tavola).update({ etichetta, nota: n, etichettata_il: new Date().toISOString() }).eq(colonna(c), c.chiave)
    setCasi((l) => (l ?? []).map((x, k) => (k === i ? { ...x, etichetta, nota: n } : x)))
    const dopo = casi.findIndex((x, k) => k > i && !x.etichetta)
    setI(dopo === -1 ? casi.length : dopo)
    setSalvo(false)
  }, [casi, c, i, salvo, nota])

  useEffect(() => {
    // 5/10: «g» poi una lettera e' il salto di sezione dell'app: dopo una «g» il tasto non e' degli esami
    // (prima «g c» apriva il contesto E saltava ai Clienti)
    let gAlle = 0
    function tasto(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (e.metaKey || e.ctrlKey || e.altKey) return        // Cmd+C copia, Cmd+1 cambia scheda: non sono etichette
      if (e.key.toLowerCase() === 'g') { gAlle = Date.now(); return }
      if (Date.now() - gAlle < 1200) { gAlle = 0; return }
      const n = Number(e.key)
      if (c && n >= 1 && n <= c.scelte.length) { e.preventDefault(); void scegli(c.scelte[n - 1][0]) }
      if (e.key === 'ArrowLeft' && i > 0) { void salvaNota(); setI(i - 1) }
      if (e.key === 'c') setApri((a) => !a)
    }
    window.addEventListener('keydown', tasto)
    return () => window.removeEventListener('keydown', tasto)
  }, [scegli, salvaNota, i, c])

  if (!casi) return null
  const fatte = casi.filter((x) => x.etichetta).length
  if (casi.length === 0) return <Card className="p-5 text-sm text-tenue">Nessun esame aperto: li prepara Clara.</Card>
  if (!c) {
    return (
      <Card className="p-6">
        <p className="text-lg font-extrabold text-navy">Fatto: {fatte} di {casi.length}.</p>
        <p className="mt-1 text-sm text-tenue">Adesso Clara misura il sistema contro le tue mosse e ti porta i numeri.</p>
        <button onClick={() => setI(0)} className="mt-3 rounded-full border border-bordo px-3 py-1 text-xs font-semibold text-navy">Rivedi dall'inizio</button>
      </Card>
    )
  }
  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-3 flex items-center gap-3">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-velo">
          <div className="h-full rounded-full bg-blu transition-[width] duration-200" style={{ width: `${(fatte / casi.length) * 100}%` }} />
        </div>
        <span className="text-xs font-semibold tabular-nums text-tenue">{fatte} di {casi.length}</span>
      </div>
      <Card className="p-5">
        <p className="text-[11px] font-bold uppercase tracking-[0.06em] text-navy">{c.domanda}</p>
        {c.blocchi.map((b, k) => (
          <div key={k} className={k > 0 ? 'mt-3' : 'mt-2'}>
            {b.eti && <p className="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-spento">{b.eti}</p>}
            <p className="whitespace-pre-wrap text-[14.5px] leading-relaxed text-inchiostro">{b.testo}</p>
          </div>
        ))}
        <button onClick={() => setApri((a) => !a)} className="mt-3 text-xs font-semibold text-blu hover:text-navy">
          {apri ? 'Chiudi il contesto' : 'Contesto'} <span className="text-spento">C</span>
        </button>
        {apri && (
          <div className="mt-3 border-t border-bordo pt-3 text-[13px] leading-relaxed">
            {!contesto ? <p className="text-tenue">Leggo…</p> : (
              <>
                {contesto.azienda && <p className="mb-2 font-bold text-navy">{contesto.azienda}</p>}
                {contesto.prima.length === 0 && <p className="text-tenue">Niente prima di questo caso.</p>}
                <ul className="space-y-1.5">
                  {contesto.prima.map((f, k) => (
                    <li key={k} className="flex gap-2">
                      <span className="w-24 shrink-0 tabular-nums text-tenue">{giorno(f.quando)}</span>
                      <span><b className="text-inchiostro">{f.cosa}</b> <span className="text-tenue">{f.testo}</span></span>
                    </li>
                  ))}
                </ul>
                {contesto.intera && (
                  <details className="mt-3">
                    <summary className="cursor-pointer text-xs font-semibold text-tenue hover:text-navy">La mail intera, con la nostra sotto</summary>
                    <p className="mt-2 max-h-72 overflow-y-auto whitespace-pre-wrap rounded-lg bg-velo p-3 text-[12px] text-tenue">{contesto.intera}</p>
                  </details>
                )}
              </>
            )}
          </div>
        )}
      </Card>
      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
        {c.scelte.map(([k, nome], n) => (
          <button key={k} onClick={() => void scegli(k)} disabled={salvo}
                  className={`flex items-center justify-between rounded-xl border px-4 py-3 text-left text-sm font-bold disabled:opacity-50 ${
                    c.etichetta === k ? 'border-blu bg-blu text-white' : 'border-bordo bg-white text-navy hover:border-blu'
                  }`}>
            {nome}<span className={`text-[11px] font-semibold ${c.etichetta === k ? 'text-white/80' : 'text-spento'}`}>{n + 1}</span>
          </button>
        ))}
      </div>
      <textarea value={nota} onChange={(e) => setNota(e.target.value)} onBlur={() => void salvaNota()}
                onKeyDown={(e) => { if (e.key === 'Escape') (e.target as HTMLTextAreaElement).blur() }}
                rows={2} placeholder="Commento: il perché, quello che il caso non dice"
                className="mt-3 w-full resize-y rounded-xl border border-bordo bg-white px-4 py-3 text-sm text-inchiostro placeholder:text-spento focus:border-blu focus:outline-none" />
      {i > 0 && <button onClick={() => { void salvaNota(); setI(i - 1) }} className="mt-2 text-xs font-semibold text-tenue hover:text-navy">‹ Indietro</button>}
    </div>
  )
}
