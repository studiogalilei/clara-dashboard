import { useEffect, useMemo, useState } from 'react'
import { supabase } from '../lib/supabase'
import { Spinner, fmtDateShort } from './ui'

// LA POSTA PER CONVERSAZIONI (Dre, 5/10: «nel workspace devo avere solo le
// conversazioni e i follow-up», «tanto rumore e rimbalzo tra Smartlead e
// Workspace senza una logica»). Il workflow, scritto prima della schermata:
// 1. arrivo: chi risponde riceve la prima consegna dalla corsia automatica;
// 2. chiamata: il caso che richiede Dre sale qui, con l'eta' e il perche';
// 3. decisione: si apre il filo a bolle e si decide li', un click;
// 4. esito: la conversazione scende tra quelle in corsa, il battito la conta.
// L'ordine e' il tempo dal posto del lead: chi aspetta da piu' tempo sta in cima.

interface PropostaMin {
  id: number
  tipo: string
  prospect_id: string | null
  titolo: string
  perche: string | null
  azione: { bozza?: string; intento?: string; prima_risposta?: { esito?: string; motivo?: string } } & Record<string, unknown>
}

interface Riga {
  id: string
  nome: string
  email: string
  classificazione: string | null
  stage: string | null
  ore: number
  proposta: PropostaMin | null
  daTe: boolean
  perche: string
}

interface Battuta {
  id: number
  kind: string
  at: string
  body: string | null
}

const MORTI = ['fuori_target', 'soppresso', 'nervoso']
const AUTO = ['INT-01', 'INT-02', 'INT-03', 'INT-23', 'INT-GB']

function eta(ore: number): string {
  if (ore < 1) return 'da meno di un ora'
  if (ore < 48) return `da ${Math.round(ore)} ore`
  return `da ${Math.round(ore / 24)} giorni`
}

// il perche' in una riga, in italiano: mai il codice intento
function perRiga(p: { classificazione: string | null }, pr: PropostaMin | null): { daTe: boolean; perche: string } {
  if (!pr) {
    if (p.classificazione === 'ooo') return { daTe: false, perche: 'fuori ufficio, si riprende al rientro' }
    if (p.classificazione === 'negativo') return { daTe: false, perche: 'ha detto no, il saluto con l’analisi è in preparazione' }
    return { daTe: false, perche: 'in lavorazione' }
  }
  const esito = pr.azione?.prima_risposta
  if (pr.tipo === 'umano') return { daTe: true, perche: pr.perche?.split('.')[0] ?? 'serve una tua decisione' }
  if (esito?.esito === 'resta a Dre') return { daTe: true, perche: esito.motivo?.split('.')[0] ?? 'la bozza aspetta te' }
  if (pr.azione?.bozza && !AUTO.includes(pr.azione?.intento ?? '')) return { daTe: true, perche: 'c’è una risposta pronta, la mandi tu' }
  return { daTe: false, perche: 'risposta in corsia automatica' }
}

export default function Conversazioni({ proposte, rispondi, occupato }: {
  proposte: PropostaMin[]
  rispondi: (p: PropostaMin, si: boolean) => Promise<boolean>
  occupato: number | null
}) {
  const [righe, setRighe] = useState<Riga[] | null>(null)
  const [aperta, setAperta] = useState<Riga | null>(null)
  const [filo, setFilo] = useState<Battuta[] | null>(null)
  const [testo, setTesto] = useState('')
  const [aiuto, setAiuto] = useState(false)

  useEffect(() => {
    let vivo = true
    supabase.from('prospects')
      .select('id,company,name,email,last_reply_at,classificazione,stage')
      .eq('awaiting_us', true).eq('fuori', false)
      .then(({ data }) => {
        if (!vivo) return
        const adesso = Date.now()
        const perProspect = new Map<string, PropostaMin>()
        for (const pr of proposte) if (pr.prospect_id && !perProspect.has(pr.prospect_id)) perProspect.set(pr.prospect_id, pr)
        const lista = ((data as Array<{ id: string; company: string | null; name: string | null; email: string; last_reply_at: string | null; classificazione: string | null; stage: string | null }>) ?? [])
          .filter((p) => !MORTI.includes(p.classificazione ?? ''))
          .map((p) => {
            const pr = perProspect.get(p.id) ?? null
            const { daTe, perche } = perRiga(p, pr)
            return {
              id: p.id, nome: p.company || p.name || p.email, email: p.email,
              classificazione: p.classificazione, stage: p.stage,
              ore: p.last_reply_at ? (adesso - new Date(p.last_reply_at).getTime()) / 3600_000 : 0,
              proposta: pr, daTe, perche,
            }
          })
          .sort((a, b) => (Number(b.daTe) - Number(a.daTe)) || b.ore - a.ore)
        setRighe(lista)
      })
    return () => { vivo = false }
  }, [proposte])

  // il filo a bolle della conversazione aperta: le sue mail, le nostre, le call
  useEffect(() => {
    if (!aperta) { setFilo(null); return }
    let vivo = true
    setFilo(null)
    setTesto(aperta.proposta?.azione?.bozza ?? '')
    supabase.from('interactions')
      .select('id,kind,at,body')
      .eq('prospect_id', aperta.id)
      .in('kind', ['email_in', 'email_out', 'call', 'nota'])
      .order('at', { ascending: true })
      .limit(40)
      .then(({ data }) => { if (vivo) setFilo((data as Battuta[]) ?? []) })
    return () => { vivo = false }
  }, [aperta])

  const daTe = useMemo(() => (righe ?? []).filter((r) => r.daTe), [righe])
  const inCorsa = useMemo(() => (righe ?? []).filter((r) => !r.daTe), [righe])

  async function decidi(si: boolean) {
    if (!aperta?.proposta) return
    const p = { ...aperta.proposta, azione: { ...aperta.proposta.azione, bozza: aperta.proposta.azione?.bozza !== undefined ? testo : undefined } }
    // prima lo schermo, poi il database (regola 17): la riga scende subito
    const era = aperta
    setAperta(null)
    setRighe((l) => (l ?? []).map((r) => r.id === era.id ? { ...r, daTe: false, proposta: null, perche: si ? 'approvata, parte da Smartlead' : 'lasciata andare' } : r))
    const ok = await rispondi(p as PropostaMin, si)
    if (!ok) setAperta(era)
  }

  if (righe === null) return <div className="flex justify-center py-10"><Spinner /></div>

  // ── la conversazione aperta: il filo a bolle e la decisione ──
  if (aperta) {
    return (
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="flex items-center gap-2 border-b border-velo px-4 py-2.5">
          <button onClick={() => setAperta(null)} className="rounded-lg px-2 py-1 text-sm font-bold text-blu hover:bg-velo">&lsaquo; Torna</button>
          <div className="min-w-0">
            <p className="truncate text-[15px] font-extrabold text-navy">{aperta.nome}</p>
            <p className="truncate text-[11px] text-tenue">aspetta {eta(aperta.ore)}, {aperta.perche}</p>
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
          {filo === null ? <div className="flex justify-center py-8"><Spinner /></div> : filo.length === 0 ? (
            <p className="py-8 text-center text-sm text-tenue">Niente nel filo. Il resto sta nella scheda.</p>
          ) : filo.map((b) => (
            b.kind === 'email_in' || b.kind === 'email_out' ? (
              <div key={b.id} className={`mb-2 flex ${b.kind === 'email_out' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed ${b.kind === 'email_out' ? 'rounded-br-md bg-navy text-white' : 'rounded-bl-md border border-bordo bg-white text-inchiostro'}`}>
                  <p className="whitespace-pre-wrap">{(b.body ?? '').slice(0, 900)}</p>
                  <p className={`mt-1 text-right text-[10px] ${b.kind === 'email_out' ? 'text-white/60' : 'text-tenue'}`}>{fmtDateShort(b.at)}</p>
                </div>
              </div>
            ) : (
              <p key={b.id} className="my-3 text-center text-[11px] font-semibold text-tenue">
                {b.kind === 'call' ? 'Call' : 'Nota'}, {fmtDateShort(b.at)}: {(b.body ?? '').slice(0, 120)}
              </p>
            )
          ))}
          {aperta.proposta?.azione?.bozza !== undefined && (
            <div className="mt-3 rounded-2xl border-2 border-dashed border-blu/40 bg-blu/5 p-3">
              <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.05em] text-blu">La risposta di Clara, da mandare</p>
              <textarea value={testo} onChange={(e) => setTesto(e.target.value)} rows={Math.min(14, testo.split('\n').length + 2)}
                        className="w-full resize-y rounded-xl border border-bordo bg-white p-3 text-[13px] leading-relaxed text-inchiostro focus:border-blu focus:outline-none" />
            </div>
          )}
          {aperta.proposta && aperta.proposta.azione?.bozza === undefined && (
            <div className="mt-3 rounded-2xl border border-bordo bg-white p-3">
              <p className="text-[13px] font-semibold text-inchiostro">{aperta.proposta.titolo}</p>
              {aperta.proposta.perche && <p className="mt-1 text-[12px] text-tenue">{aperta.proposta.perche}</p>}
            </div>
          )}
        </div>
        {aperta.proposta && (
          <div className="flex items-center gap-2 border-t border-velo px-4 py-3">
            <button onClick={() => void decidi(true)} disabled={occupato !== null}
                    className="rounded-full bg-blu px-4 py-2 text-[13px] font-bold text-white disabled:opacity-40">
              {aperta.proposta.azione?.bozza !== undefined ? 'Approva e manda' : 'Fai così'}
            </button>
            <button onClick={() => void decidi(false)} disabled={occupato !== null}
                    className="rounded-full border border-bordo px-4 py-2 text-[13px] font-semibold text-tenue hover:border-spento disabled:opacity-40">
              Lascia stare
            </button>
          </div>
        )}
      </div>
    )
  }

  // ── l'elenco: prima chi aspetta te, poi chi e' in corsa ──
  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="flex items-center gap-2 bg-fondo px-5 pb-1.5 pt-3">
        <span className="text-[10px] font-bold uppercase tracking-[0.05em] text-navy/70">Aspettano te</span>
        <span className="text-[10px] font-bold tabular-nums text-tenue">{daTe.length}</span>
        <button onClick={() => setAiuto((v) => !v)} title="Come si usa"
                className="ml-auto flex h-5 w-5 items-center justify-center rounded-full border border-bordo text-[11px] font-bold text-tenue hover:border-blu hover:text-blu">?</button>
      </div>
      {aiuto && (
        <div className="mx-4 mb-2 rounded-xl border border-bordo bg-white p-3 text-[12px] leading-relaxed text-inchiostro">
          <p className="font-bold text-navy">Come funziona questa posta</p>
          <p className="mt-1">Chi risponde riceve la prima consegna da sola: qui arrivano solo le conversazioni che chiedono te, con in cima chi aspetta da più tempo.</p>
          <p className="mt-1">Apri una conversazione, leggi il filo, e decidi lì: Approva e manda, oppure Lascia stare. Il resto corre da solo e lo conta il battito.</p>
        </div>
      )}
      {daTe.length === 0 && <p className="px-5 py-3 text-sm text-tenue">Nessuna conversazione aspetta te.</p>}
      {daTe.map((r) => (
        <button key={r.id} onClick={() => setAperta(r)}
                className="flex w-full items-start gap-3 border-b border-velo px-5 py-3 text-left hover:bg-velo/40">
          <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-red-500" />
          <span className="min-w-0 flex-1">
            <span className="flex items-baseline justify-between gap-2">
              <span className="truncate text-[14px] font-bold text-navy">{r.nome}</span>
              <span className="shrink-0 text-[11px] font-semibold tabular-nums text-tenue">{eta(r.ore)}</span>
            </span>
            <span className="block truncate text-[12px] text-tenue">{r.perche}</span>
          </span>
        </button>
      ))}
      <div className="flex items-center gap-2 bg-fondo px-5 pb-1.5 pt-4">
        <span className="text-[10px] font-bold uppercase tracking-[0.05em] text-navy/70">In corsa da sole</span>
        <span className="text-[10px] font-bold tabular-nums text-tenue">{inCorsa.length}</span>
      </div>
      {inCorsa.length === 0 && <p className="px-5 py-3 text-sm text-tenue">Niente in corsa.</p>}
      {inCorsa.map((r) => (
        <button key={r.id} onClick={() => setAperta(r)}
                className="flex w-full items-start gap-3 border-b border-velo px-5 py-2.5 text-left hover:bg-velo/40">
          <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${r.classificazione === 'ooo' ? 'bg-spento' : 'bg-blu'}`} />
          <span className="min-w-0 flex-1">
            <span className="flex items-baseline justify-between gap-2">
              <span className="truncate text-[13px] font-semibold text-inchiostro">{r.nome}</span>
              <span className="shrink-0 text-[11px] tabular-nums text-tenue">{eta(r.ore)}</span>
            </span>
            <span className="block truncate text-[12px] text-tenue">{r.perche}</span>
          </span>
        </button>
      ))}
    </div>
  )
}
