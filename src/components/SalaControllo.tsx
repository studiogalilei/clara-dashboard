import { useEffect, useMemo, useState } from 'react'
import { supabase } from '../lib/supabase'
import { useVivo } from '../lib/vivo'
import { apriInPosta } from '../lib/posta'
import { Card, Avviso, Spinner, fmtOra } from './ui'

// LA SALA DI CONTROLLO (Dre, 7/10: «devo potermi sedere e avere tutto in controllo con
// poco sforzo, e avvertire subito quando c'e' un problema; tanto noise e poco signal»).
//
// Una schermata, una domanda: va tutto bene, e cosa aspetta me?
// Quattro risposte, in quest'ordine: 1) i guasti, gridati, o una riga di calma;
// 2) cosa aspetta te, dal piu' vecchio; 3) chi e' in conversazione adesso;
// 4) le call di oggi (la preparazione sta su Google Calendar, qui solo il rimando).
// I tempi di Clara sono UNA riga, non una sezione: un numero sta qui solo se decide.
//
// Tutto cio' che mostra l'ha letto adesso dal database, niente stati di fantasia
// (regola del 28/9: mai affermare cio' che non si e' verificato).

interface Operazione { chiave: string; nome: string; attiva: boolean; cadenza_minuti: number; ultima_corsa: string | null; ultimo_esito: string | null }
interface Proposta { id: number; at: string; tipo: string; titolo: string; prospect_id: string | null }
interface Vivo { id: string; company: string | null; email: string; awaiting_us: boolean; last_reply_at: string; classificazione: string | null }
interface CallOggi { id: number; at: string; titolo: string; prospect_id: string | null }

const MORTI = ['negativo', 'ooo', 'fuori_target', 'soppresso', 'nervoso', 'persona_sbagliata']
const GG = 86400e3

function eta(iso: string): string {
  const h = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 3600e3))
  if (h < 1) return 'adesso'
  if (h < 24) return `${h} ${h === 1 ? 'ora' : 'ore'}`
  const g = Math.round(h / 24)
  return `${g} ${g === 1 ? 'giorno' : 'giorni'}`
}

// un'operazione e' ferma se ha saltato due giri (per le giornaliere: un giorno e tre ore)
function ferma(o: Operazione): boolean {
  if (!o.attiva || !o.ultima_corsa) return false
  const ritardo = Date.now() - new Date(o.ultima_corsa).getTime()
  const soglia = o.cadenza_minuti >= 1440 ? GG + 3 * 3600e3 : Math.max(2 * o.cadenza_minuti * 60e3, 30 * 60e3)
  return ritardo > soglia
}

export default function SalaControllo({ onOpen }: { onOpen: (id: string) => void }) {
  const [giro, setGiro] = useState<string | null>(null)
  const [ops, setOps] = useState<Operazione[]>([])
  const [aperte, setAperte] = useState<Proposta[] | null>(null)
  const [vivi, setVivi] = useState<Vivo[]>([])
  const [call, setCall] = useState<CallOggi[]>([])
  const [mandateOggi, setMandateOggi] = useState(0)
  const [battito, setBattito] = useState(0)
  useVivo(['proposte', 'prospects'], () => setBattito((n) => n + 1))

  useEffect(() => {
    const oggi = new Date(); oggi.setHours(0, 0, 0, 0)
    const sette = new Date(Date.now() - 7 * GG).toISOString()
    void supabase.rpc('ultimo_giro').then(({ data }) => setGiro((data as string) ?? null))
    void supabase.from('operazioni')
      .select('chiave,nome,attiva,cadenza_minuti,ultima_corsa,ultimo_esito')
      .then(({ data }) => setOps((data as Operazione[]) ?? []))
    void supabase.from('proposte').select('id,at,tipo,titolo,prospect_id').eq('stato', 'aperta')
      .order('at').limit(400)
      .then(({ data }) => setAperte((data as Proposta[]) ?? []))
    void supabase.from('prospects')
      .select('id,company,email,awaiting_us,last_reply_at,classificazione')
      .eq('fuori', false).neq('stage', 'perso').gte('last_reply_at', sette)
      .order('last_reply_at', { ascending: false }).limit(200)
      .then(({ data }) => setVivi(((data as Vivo[]) ?? []).filter((v) => !MORTI.includes(v.classificazione ?? ''))))
    void supabase.from('agenda').select('id,at,titolo,prospect_id,tipo')
      .gte('at', oggi.toISOString()).lt('at', new Date(oggi.getTime() + GG).toISOString())
      .not('prospect_id', 'is', null).in('tipo', ['conoscitiva', 'tecnica', 'avvio', 'call']).order('at')
      .then(({ data }) => {
        const righe = (data as CallOggi[]) ?? []
        const una = new Map<string, CallOggi>()     // l'agenda vede le call doppie: una per orario e azienda
        righe.forEach((r) => una.set(`${r.prospect_id}|${r.at.slice(0, 16)}`, r))
        setCall([...una.values()])
      })
    void supabase.from('proposte').select('id', { count: 'exact', head: true })
      .eq('stato', 'fatta').in('tipo', ['risposta', 'umano']).gte('risposta_il', oggi.toISOString())
      .then(({ count }) => setMandateOggi(count ?? 0))
  }, [battito])

  // i guasti: prima di tutto, o non e' una sala di controllo
  const guasti = useMemo(() => {
    const g: string[] = []
    if (giro && Date.now() - new Date(giro).getTime() > 30 * 60e3) {
      g.push(`Clara e' ferma: l'ultimo giro e' delle ${fmtOra(giro)}`)
    }
    ops.filter(ferma).forEach((o) => g.push(`${o.nome}: ferma da ${eta(o.ultima_corsa!)}`))
    ops.filter((o) => o.attiva && o.ultimo_esito && !/^ok/i.test(o.ultimo_esito))
      .forEach((o) => g.push(`${o.nome}: ${o.ultimo_esito}`))
    return g
  }, [giro, ops])

  const inCorsa = useMemo(() => {
    const nomi: Record<string, string> = { prima_risposta: 'prima risposta', seguiti: 'follow-up', manda: 'invio' }
    const spenti = ops.filter((o) => nomi[o.chiave] && !o.attiva).map((o) => nomi[o.chiave])
    return spenti.length ? `${spenti.join(' e ')} ${spenti.length === 1 ? 'e’ spento' : 'sono spenti'}` : null
  }, [ops])

  const aspettanoNoi = vivi.filter((v) => v.awaiting_us)
  const aspettanoLoro = vivi.filter((v) => !v.awaiting_us)
  const vecchie = (aperte ?? []).filter((p) => Date.now() - new Date(p.at).getTime() > GG)

  return (
    <div className="mx-auto flex max-w-[760px] flex-col gap-3">
      {guasti.length > 0 ? (
        <Avviso tono="rosso" titolo={`${guasti.length === 1 ? 'Un problema' : `${guasti.length} problemi`}, adesso`}>
          {guasti.slice(0, 5).map((g) => <p key={g}>{g}</p>)}
        </Avviso>
      ) : (
        <Card className="px-4 py-3">
          <p className="text-[14px]">
            <span className="mr-2 inline-block h-2 w-2 rounded-full bg-green-600 align-middle" />
            <span className="font-bold">Clara lavora.</span>{' '}
            <span className="text-tenue">
              Ultimo giro alle {giro ? fmtOra(giro) : '…'}, {mandateOggi} mail mandate oggi{inCorsa ? `, ${inCorsa}` : ''}.
            </span>
          </p>
        </Card>
      )}

      <Card>
        <header className="flex items-baseline justify-between border-b border-velo px-4 py-2.5">
          <p className="text-[14px] font-bold">Aspetta te</p>
          <span className="text-[11px] font-semibold text-tenue">
            {aperte === null ? '…' : aperte.length === 0 ? 'niente' : vecchie.length ? `${aperte.length}, ${vecchie.length} da piu' di un giorno` : aperte.length}
          </span>
        </header>
        {aperte === null && <Spinner />}
        {aperte !== null && aperte.length === 0 && (
          <p className="px-4 py-4 text-[13px] text-tenue">Niente: quando serve un tuo gesto, compare qui.</p>
        )}
        {(aperte ?? []).slice(0, 10).map((p) => (
          <button
            key={p.id}
            onClick={() => apriInPosta(p.id, p.prospect_id)}
            className="flex w-full items-center gap-3 border-b border-velo px-4 py-2.5 text-left last:border-0 hover:bg-velo/50"
          >
            <span className="min-w-0 flex-1 truncate text-[13px]">{p.titolo}</span>
            <span className={`shrink-0 text-[11px] font-semibold tabular-nums ${Date.now() - new Date(p.at).getTime() > GG ? 'text-red-700' : 'text-tenue'}`}>
              {eta(p.at)}
            </span>
          </button>
        ))}
        {(aperte?.length ?? 0) > 10 && (
          <button onClick={() => apriInPosta((aperte as Proposta[])[0].id, null)} className="w-full px-4 py-2 text-left text-[12px] font-semibold text-blu hover:underline">
            Tutte e {aperte!.length} in Posta
          </button>
        )}
      </Card>

      <Card>
        <header className="flex items-baseline justify-between border-b border-velo px-4 py-2.5">
          <p className="text-[14px] font-bold">In conversazione</p>
          <span className="text-[11px] font-semibold text-tenue">
            {vivi.length ? `${aspettanoNoi.length} aspettano noi, ${aspettanoLoro.length} aspettano loro` : 'ultimi 7 giorni'}
          </span>
        </header>
        {vivi.length === 0 && <p className="px-4 py-4 text-[13px] text-tenue">Nessuna risposta negli ultimi 7 giorni.</p>}
        {[...aspettanoNoi, ...aspettanoLoro].slice(0, 12).map((v) => (
          <button
            key={v.id}
            onClick={() => onOpen(v.id)}
            className="flex w-full items-center gap-3 border-b border-velo px-4 py-2.5 text-left last:border-0 hover:bg-velo/50"
          >
            <span className="min-w-0 flex-1 truncate text-[13px] font-semibold">{v.company || v.email}</span>
            {v.awaiting_us && <span className="shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-[10.5px] font-bold text-amber-900">aspetta noi</span>}
            <span className="shrink-0 text-[11px] tabular-nums text-tenue">{eta(v.last_reply_at)}</span>
          </button>
        ))}
      </Card>

      {call.length > 0 && (
        <Card>
          <header className="border-b border-velo px-4 py-2.5">
            <p className="text-[14px] font-bold">Le call di oggi</p>
          </header>
          {call.map((c) => (
            <button
              key={c.id}
              onClick={() => { if (c.prospect_id) onOpen(c.prospect_id) }}
              className="flex w-full items-center gap-3 border-b border-velo px-4 py-2.5 text-left last:border-0 hover:bg-velo/50"
            >
              <span className="shrink-0 text-[12px] font-bold tabular-nums text-navy">{fmtOra(c.at)}</span>
              <span className="min-w-0 flex-1 truncate text-[13px]">{c.titolo}</span>
            </button>
          ))}
          <p className="px-4 py-2 text-[11.5px] text-tenue">La preparazione ti aspetta su Google Calendar, mezz'ora prima.</p>
        </Card>
      )}
    </div>
  )
}
