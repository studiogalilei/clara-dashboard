import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { sonoCeo } from '../lib/accessi'
import { soldiClienti, soldiProgetti } from '../lib/soldi'

// I SOLDI PRIMA DELLA CALL, SOLO PER DRE E GIACOMO (29/9). La preparazione della
// call la vede anche chi fa la call con noi, quindi i numeri li' non entrano piu'.
// Dre: «da dove lo vedo io quando devo andare in call?». Da qui: in fondo alla
// preparazione, un riquadro che esiste solo per i ceo. Per gli altri non si
// disegna nemmeno, e il database a loro risponde vuoto comunque (schema_v67).

type Prezzo = { fascia?: [number, number]; punto?: number; affidabilita?: string; spesa_ads_mese?: number; flag?: string[] }
type Bilancio = { fatturato?: string | number; utile?: string | number; anno?: string | number; dipendenti?: string | number }

const euro = (n: number | string | null | undefined) =>
  n == null || n === '' ? '' : `${Math.round(Number(n)).toLocaleString('it-IT')} €`

export default function SoldiDellaCall({ prospectId, className = '' }: { prospectId: string | null | undefined; className?: string }) {
  const [ceo, setCeo] = useState(false)
  const [dati, setDati] = useState<{
    canone: number | null; prezzo: Prezzo | null; bilancio: Bilancio | null
    progetti: Array<{ nome: string; valore: number }>
    preventivi: Array<{ numero: string | null; titolo: string | null; importo: number | null; mensile: number | null; stato: string | null }>
  } | null>(null)

  useEffect(() => {
    let vivo = true
    if (!prospectId) return
    void (async () => {
      if (!(await sonoCeo())) return
      const [soldi, valori, prog, prev] = await Promise.all([
        soldiClienti(), soldiProgetti(),
        supabase.from('progetti').select('id,nome').eq('prospect_id', prospectId).limit(20),
        supabase.from('preventivi').select('numero,titolo,importo,mensile,stato').eq('prospect_id', prospectId)
          .order('creato_il', { ascending: false }).limit(3),
      ])
      const s = soldi.get(prospectId)
      const progetti = ((prog.data ?? []) as Array<{ id: number; nome: string }>)
        .filter((g) => valori.has(Number(g.id))).map((g) => ({ nome: g.nome, valore: valori.get(Number(g.id)) ?? 0 }))
      if (vivo) {
        setCeo(true)
        setDati({
          canone: s?.canone ?? null, prezzo: (s?.prezzo as Prezzo) ?? null, bilancio: (s?.bilancio as Bilancio) ?? null,
          progetti, preventivi: (prev.data ?? []) as never,
        })
      }
    })()
    return () => { vivo = false }
  }, [prospectId])

  if (!ceo || !dati) return null
  const { canone, prezzo, bilancio, progetti, preventivi } = dati
  const niente = !canone && !prezzo?.fascia && !bilancio?.fatturato && !progetti.length && !preventivi.length

  return (
    <div className={`rounded-xl border border-amber-200 bg-amber-50/60 px-3 py-2.5 text-[13px] leading-relaxed ${className}`}>
      <p className="mb-1 text-[11px] font-bold uppercase tracking-[0.06em] text-amber-900">Solo per te, i soldi</p>
      {niente ? (
        <p className="text-tenue">Ancora nessun numero: il prezzo suggerito si calcola quando c'è il fit.</p>
      ) : (
        <ul className="space-y-0.5 text-inchiostro">
          {canone != null && <li>Canone: <b>{euro(canone)}</b> al mese</li>}
          {prezzo?.fascia && (
            <li>
              Prezzo suggerito: <b>{euro(prezzo.fascia[0])} - {euro(prezzo.fascia[1])}</b> al mese
              {prezzo.affidabilita ? `, affidabilità ${prezzo.affidabilita}` : ''}
              {prezzo.spesa_ads_mese ? `, spesa Ads sostenibile circa ${euro(prezzo.spesa_ads_mese)}` : ''}
            </li>
          )}
          {prezzo?.flag?.length ? <li className="text-amber-900">Attenzione: {prezzo.flag.join('; ')}</li> : null}
          {bilancio?.fatturato && (
            <li>
              Bilancio{bilancio.anno ? ` ${bilancio.anno}` : ''}: fatturato <b>{euro(bilancio.fatturato)}</b>
              {bilancio.utile ? `, utile ${euro(bilancio.utile)}` : ''}{bilancio.dipendenti ? `, ${bilancio.dipendenti} dipendenti` : ''}
            </li>
          )}
          {progetti.map((g) => <li key={g.nome}>{g.nome}: <b>{euro(g.valore)}</b></li>)}
          {preventivi.map((q, i) => (
            <li key={i}>
              Preventivo {q.numero ?? ''} {q.titolo ? `«${q.titolo}»` : ''}: {q.mensile ? `${euro(q.mensile)} al mese` : euro(q.importo)}
              {q.stato ? `, ${q.stato}` : ''}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
