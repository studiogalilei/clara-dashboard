import { useCallback, useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { Card } from './ui'

// IL METRO DELLE RISPOSTE (Dre, 29/9). Una mail alla volta: Dre dice cosa dice LEI,
// con un tocco o con i tasti da 1 a 6. Il modello ha gia' letto la stessa mail, ma
// qui non si vede: se Dre la vedesse, si misurerebbe il modello contro se stesso.
// Con queste etichette scripts/metro.py decide se il lettore unico puo' prendere il
// posto delle quattro regole di oggi.

const SCELTE: Array<[string, string]> = [
  ['si', 'Sì, vuole'], ['no', 'No'], ['non_scrivere', 'Non scrivetemi più'],
  ['fuori_ufficio', 'Fuori ufficio'], ['rinvio', 'Più avanti'], ['altro', 'Altro'],
]

interface Riga { interaction_id: string; testo: string; etichetta: string | null }

export default function Metro() {
  const [righe, setRighe] = useState<Riga[] | null>(null)
  const [i, setI] = useState(0)
  const [salvo, setSalvo] = useState(false)

  useEffect(() => {
    supabase.from('metro_risposte').select('interaction_id,testo,etichetta').order('creato_il', { ascending: true }).limit(500)
      .then(({ data }) => {
        const l = (data as Riga[]) ?? []
        setRighe(l)
        const primo = l.findIndex((r) => !r.etichetta)
        setI(primo === -1 ? l.length : primo)
      })
  }, [])

  const scegli = useCallback(async (etichetta: string) => {
    if (!righe || i >= righe.length || salvo) return
    setSalvo(true)
    const r = righe[i]
    await supabase.from('metro_risposte').update({ etichetta, etichettata_il: new Date().toISOString() }).eq('interaction_id', r.interaction_id)
    setRighe((l) => (l ?? []).map((x, k) => (k === i ? { ...x, etichetta } : x)))
    const dopo = righe.findIndex((x, k) => k > i && !x.etichetta)
    setI(dopo === -1 ? righe.length : dopo)
    setSalvo(false)
  }, [righe, i, salvo])

  useEffect(() => {
    function tasto(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      const n = Number(e.key)
      if (n >= 1 && n <= SCELTE.length) { e.preventDefault(); void scegli(SCELTE[n - 1][0]) }
      if (e.key === 'ArrowLeft' && i > 0) setI(i - 1)
    }
    window.addEventListener('keydown', tasto)
    return () => window.removeEventListener('keydown', tasto)
  }, [scegli, i])

  if (!righe) return null
  const fatte = righe.filter((r) => r.etichetta).length
  if (righe.length === 0) return <Card className="p-5 text-sm text-tenue">Il metro è vuoto: lo prepara Clara.</Card>
  if (i >= righe.length) {
    return (
      <Card className="p-6">
        <p className="text-lg font-extrabold text-navy">Fatto: {fatte} di {righe.length}.</p>
        <p className="mt-1 text-sm text-tenue">Adesso Clara misura il lettore nuovo contro le regole di oggi e ti porta i numeri.</p>
        <button onClick={() => setI(0)} className="mt-3 rounded-full border border-bordo px-3 py-1 text-xs font-semibold text-navy">Rivedi dall'inizio</button>
      </Card>
    )
  }
  const r = righe[i]
  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-3 flex items-center gap-3">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-velo">
          <div className="h-full rounded-full bg-blu transition-[width] duration-200" style={{ width: `${(fatte / righe.length) * 100}%` }} />
        </div>
        <span className="text-xs font-semibold tabular-nums text-tenue">{fatte} di {righe.length}</span>
      </div>
      <Card className="p-5">
        <p className="text-[11px] font-bold uppercase tracking-[0.06em] text-navy">Cosa dice questa persona?</p>
        <p className="mt-2 whitespace-pre-wrap text-[15px] leading-relaxed text-inchiostro">{r.testo}</p>
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
      {i > 0 && <button onClick={() => setI(i - 1)} className="mt-3 text-xs font-semibold text-tenue hover:text-navy">‹ Indietro</button>}
    </div>
  )
}
