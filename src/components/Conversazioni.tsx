import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'
import { Spinner, fmtDateShort } from './ui'
import { percheCosi, prendiDaAprire, quandoProposto, rimandata } from '../lib/posta'
import { giorno } from '../lib/regole'

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
  seguito?: boolean
  giorno?: string
}

interface Battuta {
  id: number
  kind: string
  at: string
  body: string | null
}

const MORTI = ['fuori_target', 'soppresso', 'nervoso']
const AUTO = ['INT-01', 'INT-02', 'INT-03', 'INT-23', 'INT-GB']

// «oggi alle 15:00», «domani alle 9:30», «giovedì alle 15:00»: come lo dice una persona
function quandoCall(at: string): string {
  const d = new Date(at)
  const ora = d.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
  const g = (x: Date) => x.toLocaleDateString('sv-SE')      // il giorno di qui, non quello di Greenwich
  const oggi = new Date()
  const domani = new Date(Date.now() + 86400e3)
  if (g(d) === g(oggi)) return `oggi alle ${ora}`
  if (g(d) === g(domani)) return `domani alle ${ora}`
  return `${d.toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long' })} alle ${ora}`
}

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
  if (pr.azione?.bozza && !AUTO.includes(pr.azione?.intento ?? '')) return { daTe: true, perche: 'c’è una risposta pronta, la approvi tu' }
  return { daTe: false, perche: 'risposta in corsia automatica' }
}

// i follow-up decisi da noi (la coda di Clara e quelli su misura): non sono risposte a una mail
// appena arrivata, quindi non stanno fra chi aspetta. Prima non comparivano proprio (5/10).
const SEGUITI = ['FOLLOW UP 1', 'MINI FOLLOW UP', 'RINVIO SCADUTO', 'RICONTATTO OOO', 'RIPRESA', 'FOLLOW UP SU MISURA']

export default function Conversazioni({ proposte, rispondi, occupato, invioAcceso = true, onOpen }: {
  proposte: PropostaMin[]
  rispondi: (p: PropostaMin, si: boolean, muto?: boolean) => Promise<boolean>
  occupato: number | null
  invioAcceso?: boolean
  onOpen?: (id: string) => void
}) {
  // le rimandate a domani non stanno nella fila finche' non arriva il loro giorno
  const visibili = useMemo(() => proposte.filter((p) => !rimandata(p.azione)), [proposte])
  const [righe, setRighe] = useState<Riga[] | null>(null)
  const [aperta, setAperta] = useState<Riga | null>(null)
  const [filo, setFilo] = useState<Battuta[] | null>(null)
  const [testo, setTesto] = useState('')
  const [aiuto, setAiuto] = useState(false)
  const [seguiti, setSeguiti] = useState<Riga[]>([])
  // LETTA FINO IN FONDO (gold, 6/10): il bottone si accende quando la fine della bozza e' passata
  // sotto gli occhi. Sul telefono la barra fissa arrivava prima della fine della mail (V3).
  const [visto, setVisto] = useState(false)
  const fine = useRef<HTMLDivElement | null>(null)
  const lettore = useRef<HTMLDivElement | null>(null)
  const area = useRef<HTMLTextAreaElement | null>(null)
  const cresci = useCallback((el: HTMLTextAreaElement | null) => {
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight + 2}px`
  }, [])
  useLayoutEffect(() => { cresci(area.current) }, [testo, filo, cresci])
  // ogni conversazione si legge dall'inizio: aprendo la successiva della fila la pagina
  // restava in fondo, la fine della bozza era gia' a vista e Approva si accendeva da solo
  useEffect(() => {
    if (aperta) lettore.current?.scrollIntoView({ block: 'start' })
  }, [aperta])

  // I FOLLOW-UP PRONTI (5/10): le bozze di follow-up con il nome dell'azienda, in ordine alfabetico
  useEffect(() => {
    const ps = visibili.filter((p) => p.tipo === 'risposta' && p.prospect_id && p.azione?.bozza !== undefined
      && SEGUITI.includes(String(p.azione?.template ?? '')))
    if (!ps.length) { setSeguiti([]); return }
    let vivo = true
    const ids = [...new Set(ps.map((p) => p.prospect_id as string))]
    const pezzi: string[][] = []
    for (let i = 0; i < ids.length; i += 100) pezzi.push(ids.slice(i, i + 100))
    void Promise.all(pezzi.map((c) => supabase.from('prospects').select('id,company,name,email,classificazione,stage').in('id', c)))
      .then((rs) => {
        if (!vivo) return
        const nomi = new Map<string, { company: string | null; name: string | null; email: string; classificazione: string | null; stage: string | null }>()
        for (const r of rs) for (const x of (r.data ?? []) as Array<{ id: string; company: string | null; name: string | null; email: string; classificazione: string | null; stage: string | null }>) nomi.set(x.id, x)
        setSeguiti(ps.map((p) => {
          const x = nomi.get(p.prospect_id as string)
          return {
            id: p.prospect_id as string, nome: x?.company || x?.name || x?.email || p.titolo, email: x?.email ?? '',
            classificazione: x?.classificazione ?? null, stage: x?.stage ?? null, ore: 0, proposta: p, daTe: true,
            perche: (p.perche ?? '').split(/[.:]/)[0] || 'follow-up pronto', seguito: true,
            giorno: String(p.azione?.giorno_proposto ?? ''),
          }
        }).sort((a, b) => (quandoProposto(a.giorno) - quandoProposto(b.giorno)) || a.nome.localeCompare(b.nome)))
      })
    return () => { vivo = false }
  }, [visibili])


  useEffect(() => {
    let vivo = true
    supabase.from('prospects')
      .select('id,company,name,email,last_reply_at,classificazione,stage')
      .eq('awaiting_us', true).eq('fuori', false)
      .then(({ data }) => {
        if (!vivo) return
        const adesso = Date.now()
        const perProspect = new Map<string, PropostaMin>()
        for (const pr of visibili) if (pr.prospect_id && !perProspect.has(pr.prospect_id)) perProspect.set(pr.prospect_id, pr)
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
  }, [visibili])

  // il filo a bolle della conversazione aperta: le sue mail, le nostre, le call.
  // LA SUCCESSIVA E' GIA' PRONTA (gold, 6/10): mentre leggi questa si carica il filo di quella
  // dopo, cosi' quando approvi la fila va avanti senza la rotella. Ogni filo si legge una volta.
  const fili = useRef(new Map<string, Promise<Battuta[]>>())
  const leggiFilo = useCallback((id: string): Promise<Battuta[]> => {
    let p = fili.current.get(id)
    if (!p) {
      p = Promise.resolve(supabase.from('interactions')
        .select('id,kind,at,body')
        .eq('prospect_id', id)
        .in('kind', ['email_in', 'email_out', 'call', 'nota'])
        .order('at', { ascending: false })
        .limit(40))
        .then(({ data }) => ((data as Battuta[]) ?? []).reverse())
      fili.current.set(id, p)
    }
    return p
  }, [])
  useEffect(() => {
    if (!aperta) { setFilo(null); return }
    let vivo = true
    setFilo(null)
    setTesto(aperta.proposta?.azione?.bozza ?? '')
    void leggiFilo(aperta.id).then((f) => { if (vivo) setFilo(f) })
    const dopo = dopoDi(aperta, righe, seguiti)
    if (dopo) void leggiFilo(dopo.id)
    return () => { vivo = false }
    // la fila (righe, seguiti) serve solo a sapere chi viene dopo: non deve ricaricare il filo aperto
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aperta, leggiFilo])

  useEffect(() => {
    setVisto(false)
    if (!aperta || filo === null) return
    const el = fine.current
    if (!el || typeof IntersectionObserver === 'undefined') { setVisto(true); return }
    // lo schermo vero, non il riquadro: al telefono e' la pagina intera a scorrere, e in basso
    // ci sono la barra delle sezioni e quella dei bottoni: la fine conta se sta sopra di loro
    const oss = new IntersectionObserver((v) => { if (v.some((x) => x.isIntersecting)) setVisto(true) }, { threshold: 0, rootMargin: '0px 0px -96px 0px' })
    oss.observe(el)
    return () => oss.disconnect()
  }, [aperta, filo])

  // arrivati da «Leggi e approva» di Oggi: si apre quella conversazione appena c'e'
  const [voglio, setVoglio] = useState(() => prendiDaAprire())
  useEffect(() => {
    if (voglio === null || righe === null) return
    const tutte = [...righe, ...seguiti]
    const r = tutte.find((x) => x.proposta?.id === voglio.proposta)
      ?? tutte.find((x) => x.proposta && x.id === voglio.azienda)
    if (r) { setAperta(r); setVoglio(null) }
  }, [voglio, righe, seguiti])

  // POSTA FINITA (gold, 6/10, dalla V1): a fila vuota la Posta non resta una lista vuota,
  // dice cosa viene dopo: la prossima call, con «Prepara» che apre la scheda per la call
  const [prossimaCall, setProssimaCall] = useState<{ at: string; tipo: string | null; titolo: string | null; prospect_id: string | null } | null>(null)
  const vuota = righe !== null && !(righe ?? []).some((r) => r.daTe) && seguiti.length === 0
  useEffect(() => {
    if (!vuota) return
    let vivo = true
    supabase.from('agenda').select('at,tipo,titolo,prospect_id').gte('at', new Date().toISOString())
      .not('prospect_id', 'is', null).order('at', { ascending: true }).limit(1)
      .then(({ data }) => { if (vivo) setProssimaCall(((data ?? []) as Array<{ at: string; tipo: string | null; titolo: string | null; prospect_id: string | null }>)[0] ?? null) })
    return () => { vivo = false }
  }, [vuota])

  const daTe = useMemo(() => (righe ?? []).filter((r) => r.daTe), [righe])
  const inCorsa = useMemo(() => (righe ?? []).filter((r) => !r.daTe), [righe])

  async function decidi(si: boolean) {
    if (!aperta?.proposta) return
    const p = { ...aperta.proposta, azione: { ...aperta.proposta.azione, bozza: aperta.proposta.azione?.bozza !== undefined ? testo : undefined } }
    // prima lo schermo, poi il database (regola 17): la riga scende subito
    const era = aperta
    const primaRighe = righe
    const primaSeguiti = seguiti
    setAperta(null)
    if (era.seguito) setSeguiti((l) => l.filter((x) => x.proposta?.id !== era.proposta?.id))
    setRighe((l) => (l ?? []).map((r) => r.id === era.id ? { ...r, daTe: false, proposta: null, perche: si ? 'approvata, parte da Smartlead' : 'lasciata andare' } : r))
    const ok = await rispondi(p as PropostaMin, si)
    // 5/10: se non riesce torna tutto com'era, anche la riga (restava fra «in corsa» come partita)
    if (!ok) { setRighe(primaRighe); setSeguiti(primaSeguiti); setAperta(era); return }
    // LA FILA (5/10, estesa a tutta la Posta nel gold del 6/10): decisa una conversazione si apre
    // la successiva dello stesso gruppo, gia' col filo e la bozza; finito un gruppo si passa al dopo.
    // Non c'e' un «Approva tutti»: Dre il 25/9 l'ha fatto togliere («ogni bozza si legge e si approva da sola»).
    const prossimo = dopoDi(era, primaRighe, primaSeguiti)
    if (prossimo) setAperta(prossimo)
  }

  // DOMANI: si rimanda senza rifiutare, e si va avanti nella fila
  async function rimanda() {
    if (!aperta?.proposta) return
    const era = aperta
    const pr = aperta.proposta
    const primaRighe = righe
    const primaSeguiti = seguiti
    const al = giorno(new Date(Date.now() + 86400e3))
    setAperta(null)
    if (era.seguito) setSeguiti((l) => l.filter((x) => x.proposta?.id !== era.proposta?.id))
    else setRighe((l) => (l ?? []).map((r) => (r.id === era.id ? { ...r, daTe: false, proposta: null, perche: 'rimandata a domani' } : r)))
    const { error } = await supabase.from('proposte')
      .update({ azione: { ...pr.azione, bozza: testo, rimandata_al: al } }).eq('id', pr.id).eq('stato', 'aperta')
    if (error) { setRighe(primaRighe); setSeguiti(primaSeguiti); setAperta(era); return }
    const prossimo = dopoDi(era, primaRighe, primaSeguiti)
    if (prossimo) setAperta(prossimo)
  }

  // IL TASTO E (gold, 6/10, dalla V2): approva la bozza aperta senza il mouse. Solo a bozza letta
  // fino in fondo, e mai mentre si scrive in un campo (li' la «e» e' una lettera).
  const tastoE = useRef<() => void>(() => {})
  useEffect(() => {
    const su = (e: KeyboardEvent) => {
      if (e.key !== 'e' || e.metaKey || e.ctrlKey || e.altKey) return
      const t = e.target as HTMLElement | null
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
      tastoE.current()
    }
    window.addEventListener('keydown', su)
    return () => window.removeEventListener('keydown', su)
  }, [])

  // la fila in cui sta la conversazione aperta, e chi viene dopo
  const filaDi = useCallback((r: Riga, rs: Riga[] | null, sg: Riga[]): Riga[] =>
    r.seguito ? sg : (rs ?? []).filter((x) => x.daTe && x.proposta), [])
  function dopoDi(r: Riga, rs: Riga[] | null, sg: Riga[]): Riga | null {
    const stessa = (x: Riga) => (x.seguito ? x.proposta?.id === r.proposta?.id : x.id === r.id)
    const fila = filaDi(r, rs, sg)
    const i = fila.findIndex(stessa)
    const resto = fila.filter((x) => !stessa(x))
    if (resto.length) return resto[Math.min(Math.max(0, i), resto.length - 1)]
    // finita la fila delle risposte si passa ai follow-up pronti
    if (!r.seguito && sg.length) return sg[0]
    return null
  }

  if (righe === null) return <div className="flex justify-center py-10"><Spinner /></div>

  // ── la conversazione aperta: il filo a bolle e la decisione ──
  if (!aperta) tastoE.current = () => {}
  if (aperta) {
    const fila = filaDi(aperta, righe, seguiti)
    const posto = fila.findIndex((x) => (x.seguito ? x.proposta?.id === aperta.proposta?.id : x.id === aperta.id))
    const dopo = dopoDi(aperta, righe, seguiti)
    const perche = percheCosi(aperta.proposta?.perche)
    const conBozza = aperta.proposta?.azione?.bozza !== undefined
    const pronto = !conBozza || visto
    tastoE.current = () => { if (pronto && conBozza && occupato === null) void decidi(true) }
    return (
      <div ref={lettore} className="flex min-h-0 flex-1 flex-col scroll-mt-16">
        <div className="flex items-center gap-2 border-b border-velo px-4 py-2.5">
          <button onClick={() => setAperta(null)} className="rounded-lg px-2 py-1 text-sm font-bold text-blu hover:bg-velo">&lsaquo; Torna</button>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[15px] font-extrabold text-navy">{aperta.nome}</p>
            <p className="truncate text-[11px] text-tenue">{aperta.seguito ? `follow-up pronto${aperta.giorno ? `, propone ${aperta.giorno}` : ''}` : `aspetta ${eta(aperta.ore)}, ${aperta.perche}`}</p>
          </div>
          {posto >= 0 && fila.length > 1 && <span className="shrink-0 text-[11px] font-semibold tabular-nums text-tenue">{posto + 1} di {fila.length}</span>}
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
          {conBozza && (
            <div className="mt-3 rounded-2xl border-2 border-dashed border-blu/40 bg-blu/5 p-3">
              <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.05em] text-blu">{aperta.seguito ? 'Il follow-up, da mandare' : 'La risposta di Clara, da mandare'}</p>
              {perche && (
                <p className="mb-2 rounded-xl bg-white/70 px-3 py-2 text-[12px] leading-snug text-inchiostro">
                  <span className="font-bold text-blu">Perché così: </span>{perche}
                </p>
              )}
              {/* alta quanto il testo, mai con la fine nascosta dentro (gold, 6/10) */}
              <textarea ref={area} value={testo} onChange={(e) => setTesto(e.target.value)} rows={3}
                        onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && pronto && occupato === null) { e.preventDefault(); void decidi(true) } }}
                        className="w-full resize-none overflow-hidden rounded-xl border border-bordo bg-white p-3 text-[13px] leading-relaxed text-inchiostro focus:border-blu focus:outline-none" />
            </div>
          )}
          <div ref={fine} className="h-px" aria-hidden />
          {aperta.proposta && aperta.proposta.azione?.bozza === undefined && (
            <div className="mt-3 rounded-2xl border border-bordo bg-white p-3">
              <p className="text-[13px] font-semibold text-inchiostro">{aperta.proposta.titolo}</p>
              {aperta.proposta.perche && <p className="mt-1 text-[12px] text-tenue">{aperta.proposta.perche}</p>}
            </div>
          )}
        </div>
        {aperta.proposta && (
          <div className="border-t border-velo px-4 py-3">
            {dopo && <p className="mb-2 truncate text-[11px] text-tenue">Dopo questa: <span className="font-semibold text-inchiostro">{dopo.nome}</span></p>}
            <div className="flex items-center gap-2">
              {pronto ? (
                <button onClick={() => void decidi(true)} disabled={occupato !== null} title={conBozza ? 'E, oppure ⌘ Invio' : undefined}
                        className="min-h-[44px] rounded-full bg-blu px-5 py-2 text-[13px] font-bold text-white disabled:opacity-40">
                  {conBozza ? (invioAcceso ? 'Approva e manda' : 'Approva (non parte)') : 'Fai così'}
                </button>
              ) : (
                <button onClick={() => fine.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })}
                        className="min-h-[44px] rounded-full border border-blu px-5 py-2 text-[13px] font-bold text-blu">
                  Leggi fino in fondo
                </button>
              )}
              {conBozza && (
                <button onClick={() => void rimanda()} disabled={occupato !== null} title="La rivedi domani: non la rifiuti"
                        className="min-h-[44px] rounded-full border border-bordo px-4 py-2 text-[13px] font-semibold text-tenue hover:border-spento disabled:opacity-40">
                  Domani
                </button>
              )}
              <button onClick={() => void decidi(false)} disabled={occupato !== null}
                      className="min-h-[44px] rounded-full border border-bordo px-4 py-2 text-[13px] font-semibold text-tenue hover:border-spento disabled:opacity-40">
                Lascia stare
              </button>
            </div>
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
      {vuota ? (
        <div className="mx-4 my-2 rounded-2xl border border-bordo bg-white px-4 py-3.5">
          <p className="text-[15px] font-extrabold text-navy">Posta finita</p>
          {prossimaCall ? (
            <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-2">
              <p className="min-w-0 flex-1 text-[13px] text-inchiostro">
                Poi: <span className="font-semibold">{prossimaCall.titolo || prossimaCall.tipo || 'una call'}</span>, {quandoCall(prossimaCall.at)}
              </p>
              {onOpen && prossimaCall.prospect_id && (
                <button onClick={() => onOpen(prossimaCall.prospect_id as string)}
                        className="min-h-[40px] rounded-full bg-blu px-4 py-1.5 text-[13px] font-bold text-white">Prepara</button>
              )}
            </div>
          ) : <p className="mt-0.5 text-[13px] text-tenue">Niente aspetta te, e nessuna call in agenda.</p>}
        </div>
      ) : daTe.length === 0 && <p className="px-5 py-3 text-sm text-tenue">Nessuna conversazione aspetta te.</p>}
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
      {seguiti.length > 0 && (
        <>
          <div className="flex items-center gap-2 bg-fondo px-5 pb-1.5 pt-4">
            <span className="text-[10px] font-bold uppercase tracking-[0.05em] text-navy/70">Follow-up pronti</span>
            <span className="text-[10px] font-bold tabular-nums text-tenue">{seguiti.length}</span>
          </div>
          {seguiti.map((r) => (
            <button key={r.proposta?.id} onClick={() => setAperta(r)}
                    className="flex w-full items-start gap-3 border-b border-velo px-5 py-2.5 text-left hover:bg-velo/40">
              <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-amber-400" />
              <span className="min-w-0 flex-1">
                <span className="flex items-baseline justify-between gap-2">
                  <span className="truncate text-[13px] font-semibold text-inchiostro">{r.nome}</span>
                  {r.giorno && <span className="shrink-0 text-[11px] tabular-nums text-tenue">{r.giorno.replace(/ alle .*/, '')}</span>}
                </span>
                <span className="block truncate text-[12px] text-tenue">{r.perche}</span>
              </span>
            </button>
          ))}
        </>
      )}
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
