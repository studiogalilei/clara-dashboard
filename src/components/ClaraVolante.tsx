import { useCallback, useEffect, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'
import { decidi as decidiAccesso, sonoCeo } from '../lib/accessi'
import { leggi as leggiPref, scrivi as scriviPref } from '../lib/preferenze'
import type { Prospect } from '../lib/types'
import ClaraLogo from './ClaraLogo'
import ClaraPensa from './ClaraPensa'
import { Spinner, ZonaFile, fmtDateShort, fmtOra } from './ui'
import { CLS_LABEL } from '../lib/types'
import { pulisci, creaTask } from '../lib/regole'

// Clara volante: pannello allargabile (trascina il bordo sinistro), la
// conversazione stile Claude, e i COMANDI RAPIDI. Regola del workflow
// (Dre, 31/8): lei PROPONE nome, giorno/ora e invitati — si procede solo
// alla sua conferma, mai in autonomia. Senza l'OAuth, l'evento si apre
// precompilato su Google Calendar e l'ultimo click resta di Dre.

// una proposta nella stanza di Clara: cosa vuole fare, su chi, perche'.
// Sul si' si scrive azione.prospects sulla scheda; sul no si annota e basta.
// Vedi docs/LA-STANZA-DI-CLARA.md
interface Proposta {
  id: number
  at: string
  tipo: string
  prospect_id: string | null
  titolo: string
  perche: string | null
  azione: {
    prospects?: Record<string, unknown>
    task?: { titolo: string; scadenza?: string | null }
    bozza?: string; intento?: string; template?: string
    // «non e' nel CRM, lo aggiungo?»: il prospect da creare e le call da attaccargli
    nuovo?: Record<string, unknown>; agenda_ids?: number[]
    // «X chiede il widget Y»: la decide un ceo (lib/accessi.ts)
    accesso?: { user_id: string; widget: string; nome?: string }
  }
  stato: 'aperta' | 'si' | 'no' | 'fatta'
}

interface Messaggio {
  id: number
  at: string
  tipo: 'brief' | 'saluto' | 'promemoria' | 'domanda' | 'controllo' | 'anomalia' | 'dre' | 'clara'
  testo: string
  prospect_id: string | null
  letto: boolean
}

const CHIP: Record<string, [string, string]> = {
  brief: ['Brief', 'bg-velo text-navy'],
  promemoria: ['Promemoria', 'bg-amber-50 text-amber-800'],
  domanda: ['Domanda', 'bg-red-50 text-red-700'],
  controllo: ['Fatto', 'bg-green-50 text-green-800'],
  anomalia: ['Anomalia', 'bg-red-600 text-white'],
}

type Comando = 'task' | 'conoscitiva' | 'tecnica' | 'avvio'

const CALL: Record<Exclude<Comando, 'task'>, string> = {
  conoscitiva: 'Chiamata Conoscitiva',
  tecnica: 'Chiamata Tecnica',
  avvio: 'Chiamata di Avvio',
}

// il prossimo giorno lavorativo alle 15, come proposta di partenza
function proposta(): string {
  const d = new Date(Date.now() + 86400e3)
  while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() + 1)
  d.setHours(15, 0, 0, 0)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`
}

function linkCalendar(titolo: string, quando: string, invitati: string): string {
  const inizio = quando.replace(/[-:]/g, '')
  const fine = (() => {
    const d = new Date(quando)
    d.setMinutes(d.getMinutes() + 45)
    const p = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}T${p(d.getHours())}${p(d.getMinutes())}00`
  })()
  const mail = invitati.split(/[,;\s]+/).filter(Boolean).join(',')
  return 'https://calendar.google.com/calendar/render?action=TEMPLATE'
    + `&text=${encodeURIComponent(titolo)}`
    + `&dates=${inizio}00/${fine}`
    + (mail ? `&add=${encodeURIComponent(mail)}` : '')
}

interface Props {
  onOpen: (id: string) => void
}

// ── capire i comandi detti in chat (dominio stretto: call e task) ──
// Regola di Dre (31/8): se ha tutte le info mostra la proposta compilata
// e lui conferma; se manca qualcosa lo CHIEDE, e non procede finche' non
// ce l'ha.

interface Pendente {
  genere: 'call' | 'task'
  tipo?: Exclude<Comando, 'task'>
  prospectId?: string
  giorno?: string      // YYYY-MM-DD
  ora?: string         // HH:MM
  titolo?: string      // per le task
  extraMail?: string[]
}

const GIORNI_SETT = ['domenica', 'lunedi', 'martedi', 'mercoledi', 'giovedi', 'venerdi', 'sabato']
const MESI_NOMI = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno',
  'luglio', 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre']

function senzaAccenti(t: string): string {
  return t.toLowerCase()
    .replace(/[àá]/g, 'a').replace(/[èé]/g, 'e').replace(/[ìí]/g, 'i')
    .replace(/[òó]/g, 'o').replace(/[ùú]/g, 'u')
}

function trovaTipoCall(t: string): Pendente['tipo'] | undefined {
  if (/conoscitiv/.test(t)) return 'conoscitiva'
  if (/tecnic/.test(t)) return 'tecnica'
  if (/avvio|onboarding/.test(t)) return 'avvio'
  return undefined
}

function trovaGiorno(t: string, secco = false): string | undefined {
  const oggi = new Date()
  const iso = (d: Date) => {
    const p = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
  }
  if (/dopodomani/.test(t)) { const d = new Date(oggi); d.setDate(d.getDate() + 2); return iso(d) }
  if (/domani/.test(t)) { const d = new Date(oggi); d.setDate(d.getDate() + 1); return iso(d) }
  if (/\boggi\b/.test(t)) return iso(oggi)
  for (let g = 0; g < 7; g++) {
    if (new RegExp(`\\b${GIORNI_SETT[g]}\\b`).test(t)) {
      const d = new Date(oggi)
      let salto = (g - d.getDay() + 7) % 7
      if (salto === 0) salto = 7
      d.setDate(d.getDate() + salto)
      return iso(d)
    }
  }
  const conMese = t.match(new RegExp(`\\b(?:il\\s+)?(\\d{1,2})\\s+(${MESI_NOMI.join('|')})`))
  if (conMese) return componi(Number(conMese[1]), MESI_NOMI.indexOf(conMese[2]) + 1, oggi)
  const numerico = t.match(/\b(\d{1,2})[/](\d{1,2})\b/)
  if (numerico) return componi(Number(numerico[1]), Number(numerico[2]), oggi)
  // «il 4» secco: vale solo quando la domanda in corso è proprio «Che giorno?»
  if (secco) {
    const solo = t.match(/^\s*(?:il\s+)?(\d{1,2})\s*$/)
    if (solo) {
      const g = Number(solo[1])
      const d = new Date(oggi.getFullYear(), oggi.getMonth(), g)
      if (d.getDate() !== g) return undefined
      if (d.getTime() < oggi.getTime() - 86400e3) d.setMonth(d.getMonth() + 1)
      return iso(d)
    }
  }
  return undefined
}

// giorno e mese scritti a mano: si rifiutano i mesi che non esistono, e
// l'anno NON si sposta in avanti per una data appena passata (prima «il 31/8»
// detto il 1/9 diventava 2027 senza dirlo)
function componi(g: number, m: number, oggi: Date): string | undefined {
  if (m < 1 || m > 12 || g < 1 || g > 31) return undefined
  const d = new Date(oggi.getFullYear(), m - 1, g)
  if (d.getMonth() !== m - 1) return undefined
  if (d.getTime() < oggi.getTime() - 60 * 86400e3) d.setFullYear(d.getFullYear() + 1)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function trovaOra(t: string): string | undefined {
  const m = t.match(/\balle?\s+(\d{1,2})(?:[:.](\d{2}))?/) ?? t.match(/\b(\d{1,2})[:.](\d{2})\b/)
  if (!m) return undefined
  let h = Number(m[1])
  const min = m[2] ? Number(m[2]) : 0
  const mattina = /mattin|di mattina|am\b/.test(t)
  if (!mattina && h < 7 && /pomeriggio|sera|alle\s+[1-6]\b/.test(t)) h += 12
  if (h > 23 || min > 59) return undefined
  return `${String(h).padStart(2, '0')}:${String(min).padStart(2, '0')}`
}

// parole che stanno in mezzo a ogni frase italiana o in mezza Italia:
// agganciavano il prospect sbagliato in silenzio («della», «studio»)
const PAROLE_VUOTE = new Set([
  'della', 'dello', 'delle', 'degli', 'dell', 'sull', 'sulla', 'nella', 'nelle',
  'studio', 'gruppo', 'societa', 'azienda', 'ditta', 'impresa', 'italia', 'italiana',
  'srl', 'spa', 'snc', 'sas', 'sagl', 'group', 'servizi', 'service', 'casa', 'centro',
  'call', 'chiamata', 'prossima', 'settimana', 'domani', 'giorno', 'mattina', 'sera',
])

function intero(ago: string, pagliaio: string): boolean {
  const fuga = ago.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return new RegExp(`(^|[^a-z0-9])${fuga}([^a-z0-9]|$)`).test(pagliaio)
}

function trovaProspect(t: string, lista: Prospect[]): string | undefined {
  // 1) il nome intero vince sempre
  let pieno: { id: string; lung: number } | null = null
  const parziali: Array<{ id: string; lung: number }> = []
  for (const p of lista) {
    for (const nome of [p.company, p.name]) {
      if (!nome) continue
      const n = senzaAccenti(nome)
      if (n.length >= 4 && intero(n, t)) {
        if (!pieno || n.length > pieno.lung) pieno = { id: p.id, lung: n.length }
        continue
      }
      // 2) un pezzo solo vale se è lungo, non è una parola comune e sta
      //    lì come parola intera; se aggancia più persone, non si indovina
      for (const pezzo of n.split(/\s+/)) {
        if (pezzo.length < 5 || PAROLE_VUOTE.has(pezzo)) continue
        if (intero(pezzo, t)) parziali.push({ id: p.id, lung: pezzo.length })
      }
    }
  }
  if (pieno) return pieno.id
  const candidati = [...new Set(parziali.map((x) => x.id))]
  return candidati.length === 1 ? candidati[0] : undefined
}

function trovaMail(testo: string): string[] {
  return (testo.match(/[\w.+-]+@[\w-]+(?:\.[\w-]+)+/g) ?? []).map((m) => m.replace(/\.+$/, ''))
}

export default function ClaraVolante({ onOpen }: Props) {
  const [utenteId, setUtenteId] = useState<string | null>(null)
  const [ceo, setCeo] = useState(false)
  useEffect(() => { void sonoCeo().then(setCeo) }, [utenteId])
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setUtenteId(data.session?.user?.id ?? null))
  }, [])
  // Intervista a Dre (9/9): sul desktop Clara e' una colonna fissa a destra,
  // stretta (320), aperta di default sulla posta; la chiudi se vuoi e torna
  // il logo. Sul telefono resta il pannello che si apre sopra.
  const desktop = typeof window !== 'undefined' && window.matchMedia('(min-width: 1024px)').matches
  const [aperta, setApertaStato] = useState<boolean>(() => desktop && leggiPref('clara-aperta') === 'si')
  const setAperta = (v: boolean) => { setApertaStato(v); if (desktop) scriviPref('clara-aperta', v ? 'si' : 'no') }
  const fissa = desktop && aperta
  const [larghezza, setLarghezza] = useState<number>(() => {
    const salvata = Number(leggiPref('clara-larghezza')) || 320
    return salvata > 480 ? 320 : salvata      // la colonna fissa e' stretta: sopra i 480 era il vecchio pannello
  })
  const [messaggi, setMessaggi] = useState<Messaggio[] | null>(null)
  const [prospects, setProspects] = useState<Prospect[]>([])
  const [testo, setTesto] = useState('')
  const [invio, setInvio] = useState(false)
  // il logo che lavora: resta acceso un momento anche dopo la fine, se no
  // su un lavoro veloce lampeggia e non lo vedi
  const [pensa, setPensa] = useState(false)
  const [comando, setComando] = useState<Comando | null>(null)
  const [pendente, setPendente] = useState<Pendente | null>(null)
  // il modulo della proposta
  const [pTitolo, setPTitolo] = useState('')
  const [pQuando, setPQuando] = useState(proposta())
  const [pInvitati, setPInvitati] = useState('')
  const [pProspect, setPProspect] = useState('')
  const [pData, setPData] = useState('')
  const fondoRef = useRef<HTMLDivElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const tiro = useRef<{ attivo: boolean }>({ attivo: false })

  // gli ULTIMI 80, non i primi: prima oltre le 80 righe i messaggi nuovi
  // non comparivano più e il badge restava a zero
  // Clara e' una sola, ma la casella e' di ognuno (Dre, 3/9): si vedono i
  // messaggi indirizzati a te, piu' quelli di tutti che non hanno un
  // destinatario. Quello che lei SA resta comune, quello che DICE e' tuo.
  const [proposte, setProposte] = useState<Proposta[]>([])
  const [rispondo, setRispondo] = useState<number | null>(null)
  const [vista, setVista] = useState<'chat' | 'posta'>('chat')
  const [apertaId, setApertaId] = useState<number | null>(null)
  // il contesto di una proposta si carica quando la apri, non prima
  const [contesto, setContesto] = useState<Record<number, { p: Prospect | null; ultimo: string | null; quando: string | null }>>({})
  const [bozze, setBozze] = useState<Record<number, string>>({})
  const [copiata, setCopiata] = useState<number | null>(null)

  // il corpo di una proposta: lo stesso in posta e in chat. In chat parla come
  // una persona (Dre, 9/9): breve, naturale, e i bottoni subito sotto.
  function aParole(pr: Proposta): string {
    const nome = pr.titolo.split(':')[0].replace(/^Bozza per |^Da guardare tu: /, '').split(',')[0].trim()
    if (pr.tipo === 'risposta') return `${nome} ha risposto, ti ho preparato la risposta. La leggi?`
    if (pr.tipo === 'umano') return `${nome}: qui serve tu. ${(pr.perche ?? '').split('.')[0]}`.trim()
    if (pr.tipo === 'accesso') return `${pr.titolo}. Glielo do?`
    return pr.titolo
  }
  function corpoProposta(pr: Proposta, stile: 'posta' | 'chat') {
    const aperto = apertaId === pr.id
    const c = contesto[pr.id]
    return (
      <>
                      <button onClick={() => apriProposta(pr)} className={stile === 'chat' ? 'flex w-full items-start gap-2 text-left' : 'flex w-full items-start gap-3 px-5 py-3 text-left hover:bg-velo/60'}>
                        {stile === 'posta' && <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${pr.tipo === 'scarta' || pr.tipo === 'perso' ? 'bg-red-500' : pr.tipo === 'classifica' ? 'bg-amber-400' : 'bg-blu'}`} />}
                        <span className="min-w-0 flex-1">
                          <span className={`block leading-snug ${stile === 'chat' ? 'text-sm' : 'text-[14px] font-bold'}`}>{stile === 'chat' ? aParole(pr) : pr.titolo}</span>
                          {stile === 'posta' && <span className="block truncate text-xs text-tenue">{pr.perche}</span>}
                        </span>
                        <span className={`mt-1 shrink-0 text-[11px] text-spento transition-transform ${aperto ? 'rotate-90' : ''}`}>▸</span>
                      </button>
                      {aperto && (
                        <div className={stile === 'chat' ? 'salta-su pt-2' : 'salta-su px-5 pb-4 pl-10'}>
                          {!c ? (
                            <p className="text-xs text-spento">carico…</p>
                          ) : (
                            <div className="space-y-2 text-sm">
                              {c.p && (
                                <p className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-tenue">
                                  <span>oggi: <b className="text-inchiostro">{CLS_LABEL[c.p.classificazione ?? 'da_classificare'] ?? c.p.classificazione}</b></span>
                                  {c.p.last_reply_at && <span>ultima sua mail: <b className="text-inchiostro">{fmtDateShort(c.p.last_reply_at)}</b></span>}
                                  {c.p.next_action_date && <span>risentirlo: <b className="text-inchiostro">{fmtDateShort(c.p.next_action_date)}</b></span>}
                                  {c.p.canone && <span>{Number(c.p.canone).toLocaleString('it-IT')} €/mese</span>}
                                </p>
                              )}
                              {c.ultimo && (
                                <blockquote className="border-l-2 border-bordo pl-3 text-[13px] leading-snug text-tenue">
                                  <span className="mb-0.5 block text-[10px] font-bold uppercase tracking-[0.05em] text-spento">
                                    cosa ha scritto{c.quando ? `, ${fmtDateShort(c.quando)}` : ''}
                                  </span>
                                  <span className="line-clamp-5 whitespace-pre-wrap">{c.ultimo}</span>
                                </blockquote>
                              )}
                              {pr.perche && <p className="text-xs text-tenue">Clara: {pr.perche}</p>}
                              {pr.azione?.bozza !== undefined && (
                                <div className="mt-2">
                                  <p className="mb-1 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.05em] text-spento">
                                    la bozza{pr.azione.template ? `, ${pr.azione.template}` : ''}
                                    <button
                                      onClick={async () => {
                                        try { await navigator.clipboard.writeText(bozze[pr.id] ?? pr.azione.bozza ?? '') } catch { /* niente */ }
                                        setCopiata(pr.id); setTimeout(() => setCopiata(null), 1800)
                                      }}
                                      className="ml-auto rounded-full border border-bordo px-2.5 py-0.5 text-[10px] font-bold normal-case tracking-normal text-navy hover:border-navy"
                                    >
                                      {copiata === pr.id ? 'copiata ✓' : 'Copia'}
                                    </button>
                                  </p>
                                  <textarea
                                    value={bozze[pr.id] ?? pr.azione.bozza}
                                    onChange={(e) => setBozze((b) => ({ ...b, [pr.id]: e.target.value }))}
                                    rows={9}
                                    className="w-full rounded-lg border border-bordo bg-white px-3 py-2 text-[13px] leading-snug outline-none focus:border-blu"
                                  />
                                </div>
                              )}
                            </div>
                          )}
                          <div className="mt-3 flex items-center gap-2">
                            <button onClick={() => rispondi(pr, true)} disabled={rispondo === pr.id} className="rounded-full bg-blu px-4 py-1.5 text-xs font-bold text-white disabled:opacity-40">
                              {pr.azione?.bozza !== undefined ? 'L\'ho mandata' : 'Sì'}
                            </button>
                            <button onClick={() => rispondi(pr, false)} disabled={rispondo === pr.id} className="rounded-full border border-bordo px-4 py-1.5 text-xs font-semibold text-tenue hover:border-spento disabled:opacity-40">No</button>
                            {pr.prospect_id && (
                              <button onClick={() => vaiAllaStoria(pr)} className="ml-auto text-xs font-bold text-blu hover:underline">Storia →</button>
                            )}
                          </div>
                        </div>
                      )}
      </>
    )
  }

  async function apriProposta(pr: Proposta) {
    setApertaId((a) => (a === pr.id ? null : pr.id))
    if (contesto[pr.id] || !pr.prospect_id) return
    const [{ data: p }, { data: ult }] = await Promise.all([
      supabase.from('prospects').select('*').eq('id', pr.prospect_id).single(),
      supabase.from('interactions').select('body,at').eq('prospect_id', pr.prospect_id)
        .eq('kind', 'email_in').order('at', { ascending: false }).limit(1),
    ])
    const u = (ult as Array<{ body: string | null; at: string }> | null)?.[0]
    setContesto((c) => ({ ...c, [pr.id]: { p: (p as Prospect) ?? null, ultimo: u?.body ?? null, quando: u?.at ?? null } }))
  }

  // «Storia»: alla scheda, dritto sulla sua storia
  function vaiAllaStoria(pr: Proposta) {
    if (!pr.prospect_id) return
    setAperta(false)
    onOpen(pr.prospect_id)
    setTimeout(() => document.getElementById('storia')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 600)
  }

  const caricaMessaggi = useCallback(() => {
    // la scelta la fa il database, non il browser: se no gli 80 posti se li
    // prende chi ha parlato di piu' e i tuoi messaggi non arrivano mai
    const miei = utenteId ? `owner.is.null,owner.eq.${utenteId}` : 'owner.is.null'
    supabase.from('proposte').select('*').eq('stato', 'aperta').or(miei)
      .order('at', { ascending: true }).limit(300)
      .then(({ data: grezzi }) => {
        const data = (grezzi as Proposta[] | null)?.filter((p) => p.tipo !== 'accesso' || ceo) ?? null
        // le bozze prima di tutto: sono lavoro che parte oggi. Poi le
        // domande, poi gli scarti
        const peso: Record<string, number> = { risposta: 0, umano: 0, avanza: 1, richiesta: 1, tornato: 1, classifica: 2, data: 2, scarta: 3 }
        const l = ((data as Proposta[]) ?? []).sort((a, b) => (peso[a.tipo] ?? 9) - (peso[b.tipo] ?? 9))
        setProposte(l)
      })
    supabase
      .from('clara_messaggi')
      .select('*')
      .neq('tipo', 'saluto')
      .or(miei)
      .order('at', { ascending: false })
      .limit(80)
      .then(({ data }) => {
        const tutti = (data as Array<Messaggio & { owner?: string | null }>) ?? []
        setMessaggi([...tutti].reverse())
      })
  }, [utenteId, ceo])

  // la home dice «N bozze da approvare»: cliccando si apre qui, sulla posta
  useEffect(() => {
    function apri() { setAperta(true); setVista('posta') }
    window.addEventListener('clara:apri-posta', apri)
    return () => window.removeEventListener('clara:apri-posta', apri)
  }, [])

  useEffect(() => {
    caricaMessaggi()
    supabase.from('prospects').select('*').neq('stage', 'nuovo')
      .order('last_reply_at', { ascending: false, nullsFirst: false })
      .limit(300)
      .then(({ data }) => setProspects((data as Prospect[]) ?? []))
  }, [aperta, caricaMessaggi])

  // il giro di Clara scrive mentre la Dashboard è aperta: si ricontrolla
  useEffect(() => {
    const t = setInterval(caricaMessaggi, aperta ? 8000 : 60000)
    return () => clearInterval(t)
  }, [caricaMessaggi, aperta])

  // Clara sta pensando: l'ultimo messaggio e' di Dre (o si sta mandando) e
  // la risposta non e' ancora arrivata. Dopo due minuti smette: se non ha
  // risposto, e' un problema, non un pensiero lungo.
  const ultimo = messaggi && messaggi.length > 0 ? messaggi[messaggi.length - 1] : null
  const inAttesa = invio ? Date.now()
    : ultimo && ultimo.tipo === 'dre' && Date.now() - new Date(ultimo.at).getTime() < 120_000 ? new Date(ultimo.at).getTime()
    : null
  useEffect(() => {
    fondoRef.current?.scrollIntoView({ block: 'end' })
  }, [messaggi, aperta, comando, inAttesa])
  // finche' aspetta, si ricontrolla piu' spesso e il logo lavora
  useEffect(() => {
    if (!inAttesa) return
    setPensa(true)
    const t = setInterval(caricaMessaggi, 2500)
    return () => { clearInterval(t); setPensa(false) }
  }, [inAttesa, caricaMessaggi])

  useEffect(() => {
    if (invio) { setPensa(true); return }
    const t = setTimeout(() => setPensa(false), 900)
    return () => clearTimeout(t)
  }, [invio])

  useEffect(() => {
    function esc(e: KeyboardEvent) {
      if (e.key === 'Escape') { setComando(null); setPendente(null); if (!fissa) setAperta(false) }
    }
    function muovi(e: PointerEvent) {
      if (!tiro.current.attivo) return
      const w = Math.min(Math.max(window.innerWidth - e.clientX, 300), Math.min(fissa ? 480 : 760, window.innerWidth - 40))
      setLarghezza(w)
    }
    function su() {
      if (tiro.current.attivo) {
        tiro.current.attivo = false
        scriviPref('clara-larghezza', String(larghezza))
      }
    }
    window.addEventListener('keydown', esc)
    window.addEventListener('pointermove', muovi)
    window.addEventListener('pointerup', su)
    return () => {
      window.removeEventListener('keydown', esc)
      window.removeEventListener('pointermove', muovi)
      window.removeEventListener('pointerup', su)
    }
  }, [larghezza])

  const nonLetti = (messaggi ?? []).filter((m) => !m.letto && m.tipo !== 'dre')
  // la presenza (Dre, 9/9): cosa sta facendo Clara adesso, in una riga, come una collega
  const bozzeAperte = proposte.filter((p) => p.tipo === 'risposta' || p.tipo === 'umano').length
  const presenza = pensa ? 'Sto pensando…'
    : bozzeAperte > 0 ? `Ho ${bozzeAperte} bozz${bozzeAperte === 1 ? 'a' : 'e'} pronte per te`
    : proposte.length > 0 ? `Ho ${proposte.length} cos${proposte.length === 1 ? 'a' : 'e'} da chiederti`
    : nonLetti.length > 0 ? `${nonLetti.length} messagg${nonLetti.length === 1 ? 'io' : 'i'} da leggere`
    : 'Tutto letto, ti aspetto'

  // un messaggio si segna letto da dentro, dopo averlo aperto (Dre, 9/9)
  const [apertoMsg, setApertoMsg] = useState<number | null>(null)
  const [inChat, setInChat] = useState(5)     // quante proposte in chat per volta
  // dove sta la pallina: dove l'hai messa tu, se l'hai spostata
  const [pallina, setPallina] = useState<{ x: number; y: number } | null>(() => {
    try { const v = localStorage.getItem('clara-pallina'); return v ? JSON.parse(v) : null } catch { return null }
  })
  const presa = useRef<{ x: number; y: number; mosso: boolean; t: number } | null>(null)
  async function segnaLetto(m: Messaggio) {
    await supabase.from('clara_messaggi').update({ letto: true }).eq('id', m.id).select().single()
    setMessaggi((l) => (l ?? []).map((x) => (x.id === m.id ? { ...x, letto: true } : x)))
  }

  async function scriviMessaggio(tipo: Messaggio['tipo'], t: string, prospect_id: string | null = null) {
    const { data } = await supabase.from('clara_messaggi')
      .insert({ tipo, testo: pulisci(t), letto: true, prospect_id, owner: utenteId })
      .select().single()
    if (data) setMessaggi((m) => [...(m ?? []), data as Messaggio])
  }

  async function rispondi(p: Proposta, si: boolean) {
    setRispondo(p.id)
    let esito = si ? `Fatto: ${p.titolo}` : `Ok, lascio com'è: ${p.titolo}`
    if (si && p.azione?.bozza !== undefined && p.prospect_id) {
      // «l'ho mandata»: la mail nostra entra nella storia, e lei smette di aspettare
      const testo = (bozze[p.id] ?? p.azione.bozza).trim()
      const { error } = await supabase.from('interactions')
        .insert({ prospect_id: p.prospect_id, at: new Date().toISOString(), kind: 'email_out', body: testo })
      if (error) esito = `Non sono riuscita a segnarla: ${error.message}`
      else await supabase.from('prospects').update({ awaiting_us: false }).eq('id', p.prospect_id)
      esito = error ? esito : `Segnata come mandata: ${p.titolo}`
    } else if (p.azione?.accesso) {
      const err = await decidiAccesso(p.azione.accesso.user_id, p.azione.accesso.widget, si)
      esito = err ? `Non sono riuscita a scriverlo: ${err}` : si ? `Fatto: ${p.azione.accesso.nome ?? 'la persona'} ha il widget` : `Ok, non lo do: ${p.titolo}`
    } else if (si) {
      if (p.azione?.nuovo) {
        const { data: creato, error } = await supabase.from('prospects')
          .insert(p.azione.nuovo).select('id').single()
        if (error) esito = `Non sono riuscita a crearlo: ${error.message}`
        else if (p.azione.agenda_ids?.length) {
          await supabase.from('agenda').update({ prospect_id: (creato as { id: string }).id }).in('id', p.azione.agenda_ids)
        }
      }
      if (p.azione?.prospects && p.prospect_id) {
        const { error } = await supabase.from('prospects').update(p.azione.prospects).eq('id', p.prospect_id)
        if (error) esito = `Non sono riuscita a scriverlo: ${error.message}`
      }
      if (p.azione?.task) {
        const { problema } = await creaTask({ titolo: p.azione.task.titolo, scadenza: p.azione.task.scadenza ?? null, prospect_id: p.prospect_id })
        if (problema) esito = `La task non si è salvata: ${problema}`
      }
    }
    await supabase.from('proposte')
      .update({ stato: si ? 'fatta' : 'no', risposta_il: new Date().toISOString() }).eq('id', p.id)
    setProposte((l) => l.filter((x) => x.id !== p.id))
    await scriviMessaggio('controllo', esito, p.prospect_id)
    setRispondo(null)
  }

  async function manda(contenuto: string) {
    const t = contenuto.trim()
    if (!t) return
    setInvio(true)
    await scriviMessaggio('dre', t)
    setTesto('')
    await interpreta(t)
    setInvio(false)
  }

  // il pezzo che ascolta: call e task detti a parole
  async function interpreta(originale: string) {
    const t = senzaAccenti(originale)

    // ── uscire da un giro a metà, a parole ────────────────────────
    if (pendente && /^(annulla|lascia stare|lascia perdere|niente|stop|basta|fa nulla|non importa)\b/.test(t)) {
      setPendente(null)
      await scriviMessaggio('controllo', 'Ok, lascio stare.')
      return
    }

    // il «sì» alla sua sentinella («vuoi che la preparo io?») apre il giro.
    // Vale solo se quella domanda è l'ULTIMA cosa che ha detto Clara ed è di
    // oggi: prima un «ok» a tutt'altro, giorni dopo, riapriva una call vecchia
    const affermazione = /^(si|ok|okay|vai|certo|procedi|fissala|preparala|dai)\b[\s,.!]*/.exec(t)
    if (!pendente && affermazione) {
      const resto = t.slice(affermazione[0].length).trim()
      // «si vede che il problema e altrove» non è un sì: dopo l'assenso ci
      // può stare solo un giorno o un'ora, o niente
      const eUnSi = !resto || Boolean(trovaGiorno(resto) || trovaOra(resto))
      const ultima = [...(messaggi ?? [])].reverse().find((m) => m.tipo !== 'dre')
      const fresca = ultima ? Date.now() - new Date(ultima.at).getTime() < 24 * 3600e3 : false
      const eLaSentinella = ultima?.tipo === 'domanda'
        && ultima.testo.includes('Vuoi che la preparo io')
        && fresca
      if (eUnSi && eLaSentinella && ultima?.prospect_id) {
        const seguito: Pendente = {
          genere: 'call', tipo: 'conoscitiva',
          prospectId: ultima.prospect_id, extraMail: [],
        }
        seguito.giorno = trovaGiorno(t)
        seguito.ora = trovaOra(t)
        if (!seguito.giorno) {
          setPendente(seguito)
          await scriviMessaggio('domanda', 'Che giorno?')
          return
        }
        if (!seguito.ora) {
          setPendente(seguito)
          await scriviMessaggio('domanda', 'A che ora?')
          return
        }
        setPendente(null)
        const scelto = prospects.find((x) => x.id === seguito.prospectId)
        setComando('conoscitiva')
        setPProspect(seguito.prospectId!)
        setPTitolo(`${CALL.conoscitiva}: ${scelto?.company || scelto?.name || ''}`.trim())
        setPQuando(`${seguito.giorno}T${seguito.ora}`)
        setPInvitati(scelto?.email ?? '')
        return
      }
    }

    const vuoleCall = /\b(fissa|prepara|metti|crea|organizza)\b.*\b(call|chiamata)\b/.test(t)
      || /\b(call|chiamata)\s+(conoscitiv|tecnic|di avvio|onboarding)/.test(t)
    const vuoleTask = /\b(ricordami|aggiungi.*task|segna(mi)? di)\b/.test(t) || /\btask:/.test(t)

    // se mentre riempie una call gli chiedi una task (o viceversa), si
    // riparte da capo con la cosa nuova invece di macinarla come risposta
    const cambioRotta = Boolean(pendente
      && ((vuoleCall && pendente.genere !== 'call') || (vuoleTask && pendente.genere !== 'task')))
    const inCorso = cambioRotta ? null : pendente

    const p: Pendente = inCorso ? { ...inCorso } : { genere: 'task' }

    if (!inCorso && !vuoleCall && !vuoleTask) return

    if (!inCorso) {
      p.genere = vuoleCall ? 'call' : 'task'
      p.extraMail = []
    }

    if (p.genere === 'task') {
      if (!p.titolo) {
        const dopo = originale
          .replace(/^(clara[,\s]*)?/i, '')
          .replace(/\b(ricordami di|ricordami|aggiungi (una )?task( di| per)?|segna(mi)? di|task:)\s*/i, '')
          .trim()
        if (dopo.length >= 3) p.titolo = dopo.charAt(0).toUpperCase() + dopo.slice(1)
      }
      p.giorno = p.giorno ?? trovaGiorno(t, Boolean(inCorso))
      if (!p.titolo) {
        setPendente(p)
        await scriviMessaggio('domanda', 'Cosa scrivo nella task?')
        return
      }
      // ha tutto: mostra la proposta, conferma lui
      setPendente(null)
      setComando('task')
      setPTitolo(p.titolo)
      setPData(p.giorno ?? '')
      return
    }

    // una call
    p.tipo = p.tipo ?? trovaTipoCall(t)
    p.prospectId = p.prospectId ?? trovaProspect(t, prospects)
    p.giorno = p.giorno ?? trovaGiorno(t, Boolean(inCorso))
    p.ora = p.ora ?? trovaOra(t)
    p.extraMail = [...new Set([...(p.extraMail ?? []), ...trovaMail(originale)])]

    if (!p.tipo) {
      setPendente(p)
      await scriviMessaggio('domanda', 'Che call è: conoscitiva, tecnica o di avvio?')
      return
    }
    if (!p.prospectId) {
      setPendente(p)
      await scriviMessaggio('domanda', 'Con chi la fisso?')
      return
    }
    if (!p.giorno) {
      setPendente(p)
      await scriviMessaggio('domanda', 'Che giorno?')
      return
    }
    if (!p.ora) {
      setPendente(p)
      await scriviMessaggio('domanda', 'A che ora?')
      return
    }

    // ha TUTTO: compila la proposta e la mostra — conferma lui
    setPendente(null)
    const scelto = prospects.find((x) => x.id === p.prospectId)
    setComando(p.tipo)
    setPProspect(p.prospectId)
    setPTitolo(`${CALL[p.tipo]}: ${scelto?.company || scelto?.name || ''}`.trim())
    setPQuando(`${p.giorno}T${p.ora}`)
    setPInvitati([...new Set([scelto?.email, ...(p.extraMail ?? [])].filter(Boolean))].join(', '))
  }

  async function allega(f: File) {
    setInvio(true)
    const path = `${Date.now()}-${f.name.replace(/[^a-zA-Z0-9._-]/g, '_')}`
    const { error } = await supabase.storage.from('vault').upload(path, f)
    if (!error) {
      const nome = f.name.replace(/\.[^.]+$/, '')
      await supabase.from('vault_file')
        .insert({ nome, path, mime: f.type || null, dimensione: f.size })
        .select().single()
      await scriviMessaggio('dre', `📎 ${f.name}, messo nei Documenti`)
    }
    setInvio(false)
  }

  function scegliProspect(id: string) {
    setPProspect(id)
    const p = prospects.find((x) => x.id === id)
    if (p && comando && comando !== 'task') {
      setPTitolo(`${CALL[comando]}: ${p.company || p.name || ''}`.trim())
      setPInvitati(p.email)
    }
  }

  async function confermaTask() {
    const t = pTitolo.trim()
    if (!t) return
    const { problema } = await creaTask({
      titolo: t, scadenza: pData || null, prospect_id: pProspect || null,
    })
    if (problema) {
      await scriviMessaggio('controllo', `La task «${t}» non si è salvata: ${problema}`)
      setComando(null)
      return
    }
    await scriviMessaggio('controllo', `Task aggiunta: «${t}»${pData ? `, ${fmtDateShort(pData)}` : ''}`)
    setComando(null)
  }

  async function confermaCall() {
    if (!pTitolo.trim() || !pQuando) return
    const url = linkCalendar(pTitolo.trim(), pQuando, pInvitati)
    await supabase.from('agenda').insert({
      at: new Date(pQuando).toISOString(),
      titolo: pTitolo.trim(),
      tipo: comando,
      prospect_id: pProspect || null,
      fonte: 'clara',
    }).select().single()
    await scriviMessaggio('controllo',
      `Preparata: ${pTitolo.trim()}, ${fmtDateShort(pQuando)} ${fmtOra(pQuando)}` +
      `${pInvitati ? `, con ${pInvitati}` : ''}; confermala su Calendar`,
      pProspect || null)
    window.open(url, '_blank')
    setComando(null)
  }

  const campo = 'w-full rounded-lg border border-bordo px-2.5 py-1.5 text-sm outline-none focus:border-blu'

  return (
    <>
      {!aperta && (
        // la pallina (Dre, 9/9): un po' piu' grande, il nome sotto, e si sposta dove vuoi
        <div
          style={pallina ? { left: pallina.x, top: pallina.y, right: 'auto', bottom: 'auto' } : undefined}
          className="fixed bottom-20 right-4 z-[70] flex flex-col items-center gap-1 sm:bottom-6 sm:right-6"
        >
          <button
            onPointerDown={(e) => {
              presa.current = { x: e.clientX, y: e.clientY, mosso: false, t: Date.now() }
              ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
            }}
            onPointerMove={(e) => {
              const p = presa.current
              if (!p) return
              const dx = e.clientX - p.x, dy = e.clientY - p.y
              if (!p.mosso && Math.hypot(dx, dy) < 5) return
              p.mosso = true
              const el = (e.currentTarget as HTMLElement).parentElement!
              const r = el.getBoundingClientRect()
              const x = Math.min(Math.max(r.left + dx, 6), window.innerWidth - r.width - 6)
              const y = Math.min(Math.max(r.top + dy, 6), window.innerHeight - r.height - 6)
              p.x = e.clientX; p.y = e.clientY
              setPallina({ x, y })
            }}
            onPointerUp={() => {
              const p = presa.current
              presa.current = null
              if (p && !p.mosso) setAperta(true)
              else if (pallina) { try { localStorage.setItem('clara-pallina', JSON.stringify(pallina)) } catch { /* niente */ } }
            }}
            aria-label="Clara"
            title="Trascinami dove vuoi"
            className="relative flex w-[76px] cursor-grab touch-none flex-col items-center gap-0.5 rounded-[22px] border border-bordo bg-white px-2 pb-2 pt-2.5 text-navy shadow-[0_8px_28px_rgba(6,23,115,0.22)] transition-transform hover:-translate-y-0.5 active:cursor-grabbing"
          >
            <ClaraLogo size={44} lavora={pensa} />
            {/* il nome fa parte del logo: stesso blu, stessa forma bianca (Dre, 9/9) */}
            <span className="text-[13px] font-bold leading-none tracking-tight">Clara</span>
            {nonLetti.length + proposte.length > 0 && (
              <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-bold text-white">
                {nonLetti.length + proposte.length}
              </span>
            )}
          </button>
        </div>
      )}

      {aperta && (
        <>
          {!fissa && (
            <button
              aria-label="Chiudi"
              onClick={() => setAperta(false)}
              className="fixed inset-0 z-[64] bg-inchiostro/20"
            />
          )}
          <aside
            style={{ width: `min(${fissa ? Math.min(larghezza, 480) : larghezza}px, 100vw)` }}
            className={fissa
              ? 'sticky top-0 flex h-dvh shrink-0 flex-col border-l border-bordo bg-white'
              : 'salta-su fixed bottom-0 right-0 top-0 z-[65] flex flex-col bg-white shadow-[-8px_0_40px_rgba(16,24,40,0.15)]'}
          >
            {/* la maniglia per allargare: si vede, se no nessuno sa che
                c'e' (Dre, 4/9). Il filo si scurisce quando ci passi sopra */}
            <div
              onPointerDown={(e) => { e.preventDefault(); tiro.current.attivo = true }}
              aria-label="Allarga o stringi il pannello di Clara"
              className="group absolute bottom-0 left-0 top-0 z-10 hidden w-3 -translate-x-1.5 cursor-col-resize sm:block"
            >
              <span className="absolute inset-y-0 left-1.5 w-px bg-bordo transition-colors group-hover:bg-blu" />
              <span className="absolute left-[1px] top-1/2 h-8 w-[5px] -translate-y-1/2 rounded-full bg-transparent transition-colors group-hover:bg-blu/30" />
            </div>

            <header className="flex items-center gap-3 border-b border-velo px-5 py-3.5">
              {vista === 'posta' ? (
                <button onClick={() => setVista('chat')} className="-ml-2 rounded-full px-2 py-1 text-sm font-semibold text-tenue hover:bg-velo" aria-label="Torna alla chat">←</button>
              ) : (
                <span className="text-navy"><ClaraLogo size={30} lavora={pensa} /></span>
              )}
              <span className="min-w-0">
                <span className="block text-[15px] font-extrabold leading-tight">{vista === 'posta' ? 'Clara chiede' : 'Clara'}</span>
                {vista === 'chat' && <span className="block truncate text-[11px] text-tenue">{presenza}</span>}
              </span>
              {vista === 'posta' && <span className="text-sm font-bold tabular-nums text-navy">{proposte.length}</span>}
              <div className="ml-auto flex items-center gap-1">
                {vista === 'chat' && (
                  <button
                    onClick={() => setVista('posta')}
                    aria-label="Le cose che Clara chiede"
                    title="Le cose che Clara chiede"
                    className="relative flex h-9 w-9 items-center justify-center rounded-full text-navy hover:bg-velo"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
                      <rect x="3" y="5" width="18" height="14" rx="2.5" />
                      <path d="M3.5 7l8.5 6 8.5-6" />
                    </svg>
                    {proposte.length > 0 && (
                      <span className="absolute -right-0.5 -top-0.5 flex h-4.5 min-w-4.5 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-bold text-white">
                        {proposte.length}
                      </span>
                    )}
                  </button>
                )}
                <button onClick={() => setAperta(false)} aria-label={fissa ? 'Metti da parte Clara' : 'Chiudi'} title={fissa ? 'Metti da parte' : 'Chiudi'}
                        className="flex h-8 w-8 items-center justify-center rounded-full text-tenue hover:bg-velo hover:text-navy">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
                    {fissa ? <path d="M9 6l6 6-6 6M4 12h11" /> : <path d="M6 6l12 12M18 6L6 18" />}
                  </svg>
                </button>
              </div>
            </header>

            {/* LA POSTA: i quesiti in ordine, uno si allarga col suo contesto */}
            {vista === 'posta' && (
              <div className="min-h-0 flex-1 overflow-y-auto">
                {proposte.length === 0 ? (
                  <p className="px-5 py-8 text-center text-sm text-spento">Niente da chiedere. Tutto in ordine.</p>
                ) : proposte.map((pr, i) => {
                  const aperto = apertaId === pr.id
                  const GRUPPO: Record<string, string> = { risposta: 'Bozze da approvare', umano: 'Da guardare tu', richiesta: 'Richieste', tornato: 'Tornati', avanza: 'Dalle call', classifica: 'Classificazioni', data: 'Date', scarta: 'Da scartare' }
                  const nuovoGruppo = i === 0 || proposte[i - 1].tipo !== pr.tipo
                  return (
                    <div key={pr.id} className={`border-b border-velo ${aperto ? 'bg-velo/40' : ''}`}>
                      {nuovoGruppo && (
                        <p className="flex items-baseline gap-2 bg-fondo px-5 pb-1 pt-3 text-[10px] font-bold uppercase tracking-[0.05em] text-spento">
                          {GRUPPO[pr.tipo] ?? pr.tipo}
                          <span className="tabular-nums text-tenue">{proposte.filter((x) => x.tipo === pr.tipo).length}</span>
                        </p>
                      )}
                      {corpoProposta(pr, 'posta')}
                    </div>
                  )
                })}
              </div>
            )}

            {/* la conversazione */}
            {vista === 'chat' && (
            <ZonaFile onFile={allega} messaggio="Lascia qui: lo passo ai Documenti" className="min-h-0 flex-1 space-y-2.5 overflow-y-auto p-4">
              {messaggi === null ? (
                <Spinner />
              ) : messaggi.length === 0 ? (
                <p className="px-1 py-6 text-center text-sm text-spento">
                  Ancora nessun messaggio. Scrivile qui sotto.
                </p>
              ) : (
                messaggi.map((m) => {
                  if (m.tipo === 'dre') {
                    return (
                      <div key={m.id} className="flex justify-end">
                        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-blu px-3.5 py-2 text-white">
                          <p className="whitespace-pre-wrap text-sm">{m.testo}</p>
                          <p className="mt-0.5 text-right text-[10px] text-white/60">{fmtOra(m.at)} ✓</p>
                        </div>
                      </div>
                    )
                  }
                  const [label, classe] = m.tipo === 'clara' ? ['', ''] : (CHIP[m.tipo] ?? CHIP.promemoria)
                  const dentro = (
                    <>
                      {label && (
                        <span className={`mb-1 inline-block rounded-full px-2.5 py-0.5 text-[10px] font-bold ${classe}`}>
                          {m.tipo === 'brief' ? `${label}, ${fmtDateShort(m.at)}` : label}
                        </span>
                      )}
                      <p className={`whitespace-pre-wrap text-sm ${m.letto ? 'text-tenue' : 'font-medium'}`}>
                        {m.testo}
                      </p>
                      <p className="mt-0.5 flex items-center gap-2 text-[10px] text-spento">
                        {fmtOra(m.at)}
                        {!m.letto && <span className="h-1.5 w-1.5 rounded-full bg-blu" aria-label="da leggere" />}
                      </p>
                      {apertoMsg === m.id && (
                        <p className="salta-su mt-1.5 flex gap-3 text-[11px] font-semibold">
                          {!m.letto && <button onClick={(e) => { e.stopPropagation(); void segnaLetto(m) }} className="text-blu hover:underline">Segna letto</button>}
                          {m.prospect_id && <button onClick={(e) => { e.stopPropagation(); if (!fissa) setAperta(false); onOpen(m.prospect_id!) }} className="text-navy hover:underline">Apri la scheda ›</button>}
                        </p>
                      )}
                    </>
                  )
                  return (
                    <div key={m.id} className="flex justify-start">
                      <button
                        onClick={() => setApertoMsg(apertoMsg === m.id ? null : m.id)}
                        className={`max-w-[85%] rounded-2xl rounded-bl-md px-3.5 py-2 text-left ${m.letto ? 'bg-velo/60 hover:bg-velo' : 'bg-white ring-1 ring-blu/25 hover:ring-blu/50'}`}
                      >
                        {dentro}
                      </button>
                    </div>
                  )
                })
              )}
              {/* le cose che Clara chiede e propone: messaggi come gli altri, le piu' vecchie prima, cinque alla volta */}
              {proposte.slice(0, inChat).map((pr) => (
                <div key={`pr-${pr.id}`} className="flex justify-start">
                  <div className={`w-full max-w-[92%] rounded-2xl rounded-bl-md px-3.5 py-2.5 ${apertaId === pr.id ? 'bg-white ring-1 ring-blu/40' : 'bg-white ring-1 ring-blu/20'}`}>
                    {corpoProposta(pr, 'chat')}
                    {apertaId !== pr.id && (
                      <div className="mt-1.5 flex items-center gap-2">
                        {pr.azione?.bozza !== undefined ? (
                          <button onClick={() => apriProposta(pr)} className="rounded-full bg-blu px-3.5 py-1 text-xs font-bold text-white">Leggi</button>
                        ) : (
                          <button onClick={() => rispondi(pr, true)} disabled={rispondo === pr.id} className="rounded-full bg-blu px-3.5 py-1 text-xs font-bold text-white disabled:opacity-40">Sì</button>
                        )}
                        <button onClick={() => rispondi(pr, false)} disabled={rispondo === pr.id} className="rounded-full border border-bordo px-3 py-1 text-xs font-semibold text-tenue hover:border-spento disabled:opacity-40">No</button>
                        {pr.azione?.bozza === undefined && <button onClick={() => apriProposta(pr)} className="ml-auto text-[11px] font-semibold text-blu hover:underline">contesto</button>}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {proposte.length > inChat && (
                <button onClick={() => setInChat((n) => n + 5)} className="w-full rounded-xl border border-dashed border-bordo py-2 text-xs font-semibold text-tenue hover:border-navy hover:text-navy">
                  altre {proposte.length - inChat} cose: mostrane 5
                </button>
              )}
              {inAttesa && <ClaraPensa da={inAttesa} />}
              <div ref={fondoRef} />
            </ZonaFile>
            )}

            {vista === 'chat' && (
            <>
            {/* la proposta del comando: lei compila, Dre conferma */}
            {comando && (
              <div className="salta-su space-y-2 border-t border-velo bg-velo/40 p-4">
                {comando === 'task' ? (
                  <>
                    <p className="text-xs font-bold uppercase tracking-wide text-spento">Nuova task</p>
                    <input
                      autoFocus
                      value={pTitolo}
                      onChange={(e) => setPTitolo(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && confermaTask()}
                      placeholder="Titolo"
                      className={campo}
                    />
                    <input type="date" value={pData} onChange={(e) => setPData(e.target.value)} className={campo} />
                    <div className="flex justify-end gap-2">
                      <button onClick={() => setComando(null)} className="rounded-full border border-bordo px-4 py-1.5 text-xs font-semibold text-tenue">
                        Annulla
                      </button>
                      <button
                        onClick={confermaTask}
                        disabled={!pTitolo.trim()}
                        className="rounded-full bg-blu px-4 py-1.5 text-xs font-bold text-white disabled:opacity-30"
                      >
                        Aggiungi
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <p className="text-xs font-bold uppercase tracking-wide text-spento">{CALL[comando]}</p>
                    <select value={pProspect} onChange={(e) => scegliProspect(e.target.value)} className={campo}>
                      <option value="">Con chi?</option>
                      {prospects.map((p) => (
                        <option key={p.id} value={p.id}>{p.company || p.name || p.email}</option>
                      ))}
                    </select>
                    <input value={pTitolo} onChange={(e) => setPTitolo(e.target.value)} placeholder="Nome della call" className={campo} />
                    <input type="datetime-local" value={pQuando} onChange={(e) => setPQuando(e.target.value)} className={campo} />
                    <input value={pInvitati} onChange={(e) => setPInvitati(e.target.value)} placeholder="Invitati (mail, separate da virgola)" className={campo} />
                    <div className="flex justify-end gap-2">
                      <button onClick={() => setComando(null)} className="rounded-full border border-bordo px-4 py-1.5 text-xs font-semibold text-tenue">
                        Annulla
                      </button>
                      <button
                        onClick={confermaCall}
                        disabled={!pTitolo.trim() || !pQuando}
                        className="rounded-full bg-blu px-4 py-1.5 text-xs font-bold text-white disabled:opacity-30"
                      >
                        Conferma su Calendar →
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* la barra */}
            <div className="border-t border-velo p-3">
              <div className="flex items-end gap-1.5 rounded-3xl border border-bordo bg-white px-2 py-1.5 focus-within:border-blu">
                <button
                  onClick={() => fileRef.current?.click()}
                  aria-label="Allega un file"
                  disabled={invio}
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-tenue hover:bg-velo"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
                       strokeLinecap="round" className="h-5 w-5">
                    <path d="M21 12.5l-8.5 8.5a6 6 0 0 1-8.5-8.5L12.5 4a4 4 0 0 1 5.7 5.7L9.7 18.2a2 2 0 0 1-2.9-2.9l7.8-7.8" />
                  </svg>
                </button>
                <input
                  ref={fileRef}
                  type="file"
                  className="hidden"
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) allega(f); e.target.value = '' }}
                />
                <textarea
                  rows={1}
                  value={testo}
                  onChange={(e) => setTesto(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); manda(testo) }
                  }}
                  placeholder="Scrivi a Clara…"
                  className="max-h-28 min-h-9 flex-1 resize-none bg-transparent py-1.5 text-sm outline-none placeholder:text-spento"
                />
                <button
                  onClick={() => manda(testo)}
                  disabled={!testo.trim() || invio}
                  aria-label="Manda a Clara"
                  title="Manda a Clara"
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-navy transition-all hover:bg-velo disabled:opacity-25 disabled:hover:bg-transparent"
                >
                  <ClaraLogo size={26} lavora={invio || pensa} />
                </button>
              </div>
            </div>
            </>
            )}
          </aside>
        </>
      )}
    </>
  )
}
