import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { Card, TitoloCard } from './ui'

// I PARAMETRI DEL PREZZO (Dre, 26/9): «scaglioni, quote e moltiplicatori stanno
// in una tabella, non nel codice. Dre cambia un numero e tutte le schede si
// ricalcolano». Al giro dopo scripts/prezzo.py rilegge tutto.
type Parametro = { chiave: string; valore: unknown; cosa: string | null }

export default function Parametri() {
  const [righe, setRighe] = useState<Parametro[] | null>(null)
  const [testi, setTesti] = useState<Record<string, string>>({})
  const [esito, setEsito] = useState<string | null>(null)

  useEffect(() => {
    supabase.from('parametri').select('chiave,valore,cosa').like('chiave', 'prezzo.%').order('chiave')
      .then(({ data }) => { const r = (data ?? []) as Parametro[]; setRighe(r); setTesti(Object.fromEntries(r.map((x) => [x.chiave, JSON.stringify(x.valore)]))) })
  }, [])

  async function scrivi(chiave: string) {
    let valore: unknown
    try { valore = JSON.parse(testi[chiave]) } catch { setEsito(`${chiave}: non è un numero o una lista valida`); return }
    const { error } = await supabase.from('parametri').update({ valore, aggiornato_il: new Date().toISOString() }).eq('chiave', chiave)
    setEsito(error ? `${chiave}: ${error.message}` : `${chiave} salvato: le schede si ricalcolano al prossimo giro`)
    if (!error) void supabase.rpc('chiama_direttore', { forza: 'prezzo' })
  }

  if (!righe) return null
  return (
    <Card>
      <header className="border-b border-velo px-4 py-3"><TitoloCard>Prezzo suggerito: i parametri</TitoloCard>
        <p className="mt-0.5 text-xs text-tenue">Ipotesi di lavoro, non benchmark: si tarano sui primi dieci preventivi veri (accettati contro rifiutati). Cambi un numero, tutte le schede in pipeline si ricalcolano.</p>
      </header>
      {righe.map((r) => (
        <div key={r.chiave} className="flex flex-wrap items-center gap-2 border-b border-velo px-4 py-2 last:border-0">
          <div className="min-w-[200px] flex-1">
            <p className="text-sm font-semibold">{r.chiave.replace('prezzo.', '')}</p>
            {r.cosa && <p className="text-[11px] text-tenue">{r.cosa}</p>}
          </div>
          <input value={testi[r.chiave] ?? ''} onChange={(e) => setTesti({ ...testi, [r.chiave]: e.target.value })}
                 onBlur={() => { if (testi[r.chiave] !== JSON.stringify(r.valore)) void scrivi(r.chiave) }}
                 className="w-64 rounded-lg border border-bordo bg-white px-2 py-1 font-mono text-xs outline-none focus:border-blu" />
        </div>
      ))}
      {esito && <p className="px-4 py-2 text-xs text-tenue">{esito}</p>}
    </Card>
  )
}
