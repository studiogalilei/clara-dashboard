import { useEffect, useMemo, useState } from 'react'
import { supabase } from '../lib/supabase'
import { Card, Spinner, fmtOra } from './ui'

// IL CALENDARIO DI CLARA (Dre, 7/10: «il calendario e' inutile, dovrebbe essere il
// calendario di Clara: vedo le cose che lei fa quel giorno, e quando clicco si apre
// l'elenco completo»).
//
// Le tue call le hai gia' su Google: qui c'e' il diario di bordo di Clara, i prossimi
// 14 giorni. Per ogni giorno: i follow-up che prepara (seguiti_calendario, la stessa
// tabella che riempie la coda: una verita' sola), le call con un'azienda, e oggi anche
// cio' che sta partendo. Clic sul giorno = l'elenco completo, col perche' di ogni riga.

interface Seguito { prospect_id: string; gruppo: string; il: string; perche: string }
interface CallRiga { id: number; at: string; titolo: string; prospect_id: string | null }
interface InPartenza { id: number; titolo: string; prospect_id: string | null; stato: string }

const GG = 86400e3
const GIORNI = 14
const chiave = (d: Date) => d.toLocaleDateString('sv-SE', { timeZone: 'Europe/Rome' })
const NOME_GRUPPO: Record<string, string> = {
  'FOLLOW UP 1': 'Follow-up', 'FOLLOW UP SU MISURA': 'Follow-up su misura', 'MINI FOLLOW UP': 'Mini follow-up',
  'RINVIO SCADUTO': 'Rinvio scaduto', 'RICONTATTO OOO': 'Ricontatto dopo le ferie', RIPRESA: 'Ripresa',
}

function nomeGiorno(k: string): string {
  const oggi = chiave(new Date())
  if (k === oggi) return 'Oggi'
  if (k === chiave(new Date(Date.now() + GG))) return 'Domani'
  return new Date(`${k}T12:00:00`).toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long' })
}

export default function CalendarioClara({ onOpen }: { onOpen: (id: string) => void }) {
  const [seguiti, setSeguiti] = useState<Seguito[] | null>(null)
  const [call, setCall] = useState<CallRiga[]>([])
  const [partenza, setPartenza] = useState<InPartenza[]>([])
  const [nomi, setNomi] = useState<Record<string, string>>({})
  const [aperto, setAperto] = useState<string>(chiave(new Date()))

  useEffect(() => {
    const oggi = chiave(new Date())
    const fine = chiave(new Date(Date.now() + GIORNI * GG))
    void supabase.from('seguiti_calendario').select('prospect_id,gruppo,il,perche')
      .gte('il', oggi).lte('il', fine).order('il')
      .then(({ data }) => setSeguiti((data as Seguito[]) ?? []))
    void supabase.from('agenda').select('id,at,titolo,prospect_id')
      .gte('at', `${oggi}T00:00:00`).lte('at', `${fine}T23:59:59`)
      .not('prospect_id', 'is', null).order('at')
      .then(({ data }) => {
        const una = new Map<string, CallRiga>()
        ;((data as CallRiga[]) ?? []).forEach((r) => una.set(`${r.prospect_id}|${r.at.slice(0, 16)}`, r))
        setCall([...una.values()])
      })
    void supabase.from('proposte').select('id,titolo,prospect_id,stato')
      .in('stato', ['approvata', 'in_invio']).in('tipo', ['risposta', 'umano'])
      .then(({ data }) => setPartenza((data as InPartenza[]) ?? []))
  }, [])

  useEffect(() => {
    const ids = [...new Set((seguiti ?? []).map((s) => s.prospect_id))].slice(0, 200)
    if (!ids.length) return
    void supabase.from('prospects').select('id,company,email').in('id', ids)
      .then(({ data }) => {
        const m: Record<string, string> = {}
        ;(data as Array<{ id: string; company: string | null; email: string }> ?? []).forEach((p) => { m[p.id] = p.company || p.email })
        setNomi(m)
      })
  }, [seguiti])

  const giorni = useMemo(() => {
    const m = new Map<string, { seguiti: Seguito[]; call: CallRiga[] }>()
    for (let i = 0; i <= GIORNI; i++) {
      m.set(chiave(new Date(Date.now() + i * GG)), { seguiti: [], call: [] })
    }
    ;(seguiti ?? []).forEach((s) => m.get(s.il.slice(0, 10))?.seguiti.push(s))
    call.forEach((c) => m.get(chiave(new Date(c.at)))?.call.push(c))
    return m
  }, [seguiti, call])

  if (seguiti === null) return <Spinner />

  return (
    <div className="mx-auto flex max-w-[760px] flex-col gap-3">
      {partenza.length > 0 && (
        <Card className="px-4 py-3">
          <p className="text-[13px]">
            <span className="font-bold">{partenza.length} in partenza adesso</span>
            <span className="text-tenue">, 12 ogni cinque minuti dal thread di Smartlead.</span>
          </p>
        </Card>
      )}
      {[...giorni.entries()].map(([k, g]) => {
        const totale = g.seguiti.length + g.call.length
        const apertoQui = aperto === k
        if (totale === 0 && !apertoQui) return null
        return (
          <Card key={k}>
            <button
              onClick={() => setAperto(apertoQui ? '' : k)}
              className="flex w-full items-baseline justify-between gap-3 px-4 py-2.5 text-left hover:bg-velo/40"
            >
              <span className="text-[14px] font-bold capitalize">{nomeGiorno(k)}</span>
              <span className="text-[11.5px] font-semibold text-tenue">
                {totale === 0 ? 'niente in programma' : [
                  g.call.length ? `${g.call.length} call` : '',
                  g.seguiti.length ? `${g.seguiti.length} follow-up` : '',
                ].filter(Boolean).join(', ')}
              </span>
            </button>
            {apertoQui && totale > 0 && (
              <div className="border-t border-velo">
                {g.call.map((c) => (
                  <button key={`c${c.id}`} onClick={() => { if (c.prospect_id) onOpen(c.prospect_id) }}
                    className="flex w-full items-center gap-3 border-b border-velo px-4 py-2 text-left last:border-0 hover:bg-velo/50">
                    <span className="w-12 shrink-0 text-[12px] font-bold tabular-nums text-navy">{fmtOra(c.at)}</span>
                    <span className="min-w-0 flex-1 truncate text-[13px]">{c.titolo}</span>
                  </button>
                ))}
                {g.seguiti.map((s) => (
                  <button key={s.prospect_id} onClick={() => onOpen(s.prospect_id)}
                    className="flex w-full items-center gap-3 border-b border-velo px-4 py-2 text-left last:border-0 hover:bg-velo/50">
                    <span className="min-w-0 flex-1 truncate text-[13px] font-semibold">{nomi[s.prospect_id] ?? '…'}</span>
                    <span className="shrink-0 rounded-full bg-velo px-2 py-0.5 text-[10.5px] font-bold text-navy/80">{NOME_GRUPPO[s.gruppo] ?? s.gruppo}</span>
                    <span className="hidden max-w-[220px] shrink-0 truncate text-[11px] text-tenue sm:block">{s.perche}</span>
                  </button>
                ))}
              </div>
            )}
          </Card>
        )
      })}
    </div>
  )
}
