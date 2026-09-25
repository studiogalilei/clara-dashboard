import { useState } from 'react'
import { supabase } from '../lib/supabase'
import type { Prospect } from '../lib/types'
import { Card, TitoloCard } from './ui'

// IL PREZZO SUGGERITO (Dre, 26/9): «il sistema propone, Dre decide». Lo calcola
// scripts/prezzo.py per chi e' in pipeline: dalla domanda Google della zona,
// corretto dal bilancio se c'e'. E' una fascia con l'affidabilita', non un numero
// secco, e resta interno: non entra mai in una mail. Qui si vede, e si scrivono
// i numeri che il sistema non puo' sapere: il bilancio e, dopo la chiamata, i tre
// numeri del valore (clienti extra, valore di un cliente, margine lordo).

export type Prezzo = {
  fascia: [number, number]; punto: number; spesa_ads_mese: number; formula: string; cluster: string
  tetto_mese: number | null; tetto_fonte: string; affidabilita: 'alta' | 'media' | 'bassa'; flag: string[]; perche: string[]; il: string
}
type Bilancio = { fatturato?: string; utile?: string; anno?: string; forma?: string; il?: string }
type Valore = { clienti_extra_anno?: string; valore_cliente?: string; margine_lordo?: string; il?: string }

const euro = (n: number) => `${Math.round(n).toLocaleString('it-IT')} €`

export default function PrezzoSuggerito({ p, onSalvato }: { p: Prospect; onSalvato: (enriched: Record<string, unknown>) => void }) {
  const arr = (p.enriched ?? {}) as Record<string, unknown>
  const prezzo = arr.prezzo as Prezzo | undefined
  const [bil, setBil] = useState<Bilancio>((arr.bilancio as Bilancio) ?? {})
  const [val, setVal] = useState<Valore>((arr.valore as Valore) ?? {})
  const [aperto, setAperto] = useState(false)
  const [salvo, setSalvo] = useState<'no' | 'in_corso' | 'fatto'>('no')

  async function salva() {
    setSalvo('in_corso')
    const il = new Date().toISOString()
    const enriched = { ...arr, bilancio: { ...bil, il }, valore: { ...val, il } }
    const { error } = await supabase.from('prospects').update({ enriched }).eq('id', p.id)
    if (!error) {
      onSalvato(enriched)
      void supabase.rpc('chiama_direttore', { forza: 'prezzo' })   // si ricalcola subito, non al prossimo giro
    }
    setSalvo(error ? 'no' : 'fatto')
  }

  const campo = (v: string | undefined, set: (s: string) => void, ph: string, w = 'w-28') => (
    <input value={v ?? ''} onChange={(e) => set(e.target.value)} placeholder={ph} inputMode="decimal"
           className={`${w} rounded-lg border border-bordo bg-white px-2 py-1 text-sm tabular-nums outline-none focus:border-blu`} />
  )

  return (
    <Card className="p-4">
      <div className="flex items-baseline justify-between gap-2">
        <TitoloCard>Quanto chiedere</TitoloCard>
        <span className="text-[10px] font-semibold uppercase tracking-[0.06em] text-spento">solo interno</span>
      </div>
      {prezzo ? (
        <>
          <p className="mt-1 text-2xl font-bold tabular-nums text-navy">{euro(prezzo.fascia[0])} <span className="text-base font-semibold text-tenue">a</span> {euro(prezzo.fascia[1])} <span className="text-sm font-semibold text-tenue">al mese</span></p>
          <p className="mt-0.5 text-xs text-tenue">
            affidabilità <b>{prezzo.affidabilita}</b>, dalla {prezzo.formula === 'domanda' ? 'domanda Google della zona' : 'capacità di spesa del bilancio'}; spesa Ads sostenibile ~{euro(prezzo.spesa_ads_mese)}/mese
            {prezzo.tetto_mese ? <>; tetto di valore ~{euro(prezzo.tetto_mese)} ({prezzo.tetto_fonte})</> : <>; tetto di valore {prezzo.tetto_fonte}</>}
          </p>
          {prezzo.flag.length > 0 && (
            <p className="mt-1 rounded-md bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-800">{prezzo.flag.join(' · ')}</p>
          )}
          <details className="mt-1 text-xs text-tenue">
            <summary className="cursor-pointer select-none font-semibold">com'è venuto fuori</summary>
            <ul className="mt-1 list-disc space-y-0.5 pl-4">{prezzo.perche.map((r, i) => <li key={i}>{r}</li>)}</ul>
            <p className="mt-1 text-spento">Tutte le percentuali sono ipotesi di lavoro (Impostazioni › Lo Studio): si tarano sui primi dieci preventivi veri. Il numero è interno, non entra mai in una mail.</p>
          </details>
        </>
      ) : (
        <p className="mt-1 text-sm text-tenue">Ancora niente: mancano i volumi Google della zona (settore e provincia dal fit) e il bilancio. Scrivi quello che sai qui sotto e Clara calcola.</p>
      )}
      <button onClick={() => setAperto(!aperto)} className="mt-2 text-xs font-bold text-blu hover:underline">{aperto ? 'Chiudi' : 'Bilancio e numeri della chiamata'}</button>
      {aperto && (
        <div className="mt-2 space-y-2 text-sm">
          <p className="text-[11px] font-semibold uppercase tracking-[0.06em] text-spento">Bilancio (da OpenAPI o dalla camera di commercio)</p>
          <div className="flex flex-wrap gap-2">
            {campo(bil.fatturato, (s) => setBil({ ...bil, fatturato: s }), 'fatturato €', 'w-32')}
            {campo(bil.utile, (s) => setBil({ ...bil, utile: s }), 'utile netto €', 'w-32')}
            {campo(bil.anno, (s) => setBil({ ...bil, anno: s }), 'anno', 'w-20')}
            {campo(bil.forma, (s) => setBil({ ...bil, forma: s }), 'srl / snc / ditta', 'w-28')}
          </div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.06em] text-spento">Dalla chiamata: il valore che possiamo portare</p>
          <div className="flex flex-wrap gap-2">
            {campo(val.clienti_extra_anno, (s) => setVal({ ...val, clienti_extra_anno: s }), 'clienti extra / anno')}
            {campo(val.valore_cliente, (s) => setVal({ ...val, valore_cliente: s }), 'valore di un cliente €')}
            {campo(val.margine_lordo, (s) => setVal({ ...val, margine_lordo: s }), 'margine lordo (0.4)')}
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => void salva()} disabled={salvo === 'in_corso'} className="rounded-full bg-navy px-4 py-1.5 text-xs font-bold text-white disabled:opacity-40">Salva e ricalcola</button>
            {salvo === 'fatto' && <span className="text-xs text-spento">salvato: la fascia si aggiorna fra un minuto</span>}
          </div>
        </div>
      )}
    </Card>
  )
}
