import { useCallback, useEffect, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'
import type { Prospect } from '../lib/types'
import ClaraLogo from './ClaraLogo'
import { Spinner, ZonaFile, fmtDateShort, fmtOra } from './ui'
import { pulisci as senzaTrattino } from '../lib/regole'

// Clara volante: pannello allargabile (trascina il bordo sinistro), la
// conversazione stile Claude, e i COMANDI RAPIDI. Regola del workflow
// (Dre, 31/8): lei PROPONE nome, giorno/ora e invitati — si procede solo
// alla sua conferma, mai in autonomia. Senza l'OAuth, l'evento si apre
// precompilato su Google Calendar e l'ultimo click resta di Dre.

interface Messaggio {
  id: number
  at: string
  tipo: 'brief' | 'saluto' | 'promemoria' | 'domanda' | 'controllo' | 'anomalia' | 'dre'
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

function pulisci(t: string): string {
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
      const n = pulisci(nome)
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
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setUtenteId(data.session?.user?.id ?? null))
  }, [])
  const [aperta, setAperta] = useState(false)
  const [larghezza, setLarghezza] = useState<number>(() => {
    try { return Number(localStorage.getItem('clara-larghezza')) || 420 } catch { return 420 }
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
  const caricaMessaggi = useCallback(() => {
    supabase
      .from('clara_messaggi')
      .select('*')
      .neq('tipo', 'saluto')
      .order('at', { ascending: false })
      .limit(80)
      .then(({ data }) => {
        const tutti = (data as Array<Messaggio & { owner?: string | null }>) ?? []
        const miei = tutti.filter((m) => !m.owner || m.owner === utenteId)
        setMessaggi([...miei].reverse())
      })
  }, [utenteId])

  useEffect(() => {
    caricaMessaggi()
    supabase.from('prospects').select('*').neq('stage', 'nuovo').limit(300)
      .then(({ data }) => setProspects((data as Prospect[]) ?? []))
  }, [aperta, caricaMessaggi])

  // il giro di Clara scrive mentre la Dashboard è aperta: si ricontrolla
  useEffect(() => {
    const t = setInterval(caricaMessaggi, 60000)
    return () => clearInterval(t)
  }, [caricaMessaggi])

  useEffect(() => {
    fondoRef.current?.scrollIntoView({ block: 'end' })
  }, [messaggi, aperta, comando])

  useEffect(() => {
    if (invio) { setPensa(true); return }
    const t = setTimeout(() => setPensa(false), 900)
    return () => clearTimeout(t)
  }, [invio])

  useEffect(() => {
    function esc(e: KeyboardEvent) {
      if (e.key === 'Escape') { setComando(null); setPendente(null); setAperta(false) }
    }
    function muovi(e: PointerEvent) {
      if (!tiro.current.attivo) return
      const w = Math.min(Math.max(window.innerWidth - e.clientX, 360), Math.min(760, window.innerWidth - 40))
      setLarghezza(w)
    }
    function su() {
      if (tiro.current.attivo) {
        tiro.current.attivo = false
        try { localStorage.setItem('clara-larghezza', String(larghezza)) } catch { /* niente */ }
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

  async function segnaLette() {
    for (const m of nonLetti) {
      await supabase.from('clara_messaggi').update({ letto: true }).eq('id', m.id).select().single()
    }
    setMessaggi(messaggi!.map((m) => ({ ...m, letto: true })))
  }

  async function scriviMessaggio(tipo: Messaggio['tipo'], t: string, prospect_id: string | null = null) {
    const { data } = await supabase.from('clara_messaggi')
      .insert({ tipo, testo: senzaTrattino(t), letto: true, prospect_id, owner: utenteId })
      .select().single()
    if (data) setMessaggi((m) => [...(m ?? []), data as Messaggio])
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
    const t = pulisci(originale)

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
      await scriviMessaggio('dre', `📎 ${f.name} · messo nei Documenti`)
    }
    setInvio(false)
  }

  function apriComando(c: Comando) {
    setComando(c)
    setPProspect('')
    setPInvitati('')
    setPData('')
    setPQuando(proposta())
    setPTitolo(c === 'task' ? '' : CALL[c])
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
    await supabase.from('task_dre')
      .insert({ titolo: t, scadenza: pData || null, fatta: false, ordine: -1 })
      .select().single()
    await scriviMessaggio('controllo', `Task aggiunta: «${t}»${pData ? ` · ${fmtDateShort(pData)}` : ''}`)
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
      `Preparata: ${pTitolo.trim()} · ${fmtDateShort(pQuando)} ${fmtOra(pQuando)}` +
      `${pInvitati ? ` · con ${pInvitati}` : ''}; confermala su Calendar`,
      pProspect || null)
    window.open(url, '_blank')
    setComando(null)
  }

  const campo = 'w-full rounded-lg border border-bordo px-2.5 py-1.5 text-sm outline-none focus:border-blu'

  return (
    <>
      <button
        onClick={() => setAperta(!aperta)}
        aria-label="Clara"
        className="fixed bottom-20 right-4 z-[70] flex h-14 w-14 items-center justify-center rounded-full border border-bordo bg-white text-navy shadow-[0_8px_28px_rgba(6,23,115,0.28)] transition-transform hover:-translate-y-0.5 sm:bottom-6 sm:right-6"
      >
        <ClaraLogo size={38} lavora={pensa} />
        {nonLetti.length > 0 && !aperta && (
          <span className="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-bold text-white">
            {nonLetti.length}
          </span>
        )}
      </button>

      {aperta && (
        <>
          <button
            aria-label="Chiudi"
            onClick={() => setAperta(false)}
            className="fixed inset-0 z-[64] bg-inchiostro/20"
          />
          <aside
            style={{ width: `min(${larghezza}px, 100vw)` }}
            className="salta-su fixed bottom-0 right-0 top-0 z-[65] flex flex-col bg-white shadow-[-8px_0_40px_rgba(16,24,40,0.15)]"
          >
            {/* la maniglia per allargare */}
            <div
              onPointerDown={(e) => { e.preventDefault(); tiro.current.attivo = true }}
              className="absolute bottom-0 left-0 top-0 hidden w-2 cursor-col-resize hover:bg-blu/20 sm:block"
              aria-hidden
            />

            <header className="flex items-center gap-3 border-b border-velo px-5 py-3.5">
              <span className="text-navy"><ClaraLogo size={30} lavora={pensa} /></span>
              <span className="text-[15px] font-extrabold">Clara</span>
              {nonLetti.length > 0 && (
                <button onClick={segnaLette} className="ml-auto text-xs font-semibold text-blu hover:underline">
                  Segna lette
                </button>
              )}
              <button
                onClick={() => setAperta(false)}
                aria-label="Chiudi"
                className={`${nonLetti.length > 0 ? '' : 'ml-auto '}flex h-8 w-8 items-center justify-center rounded-full text-tenue hover:bg-velo`}
              >
                ×
              </button>
            </header>

            {/* comandi rapidi */}
            <div className="flex gap-1.5 overflow-x-auto border-b border-velo px-4 py-2.5">
              {([['task', '+ Task'], ['conoscitiva', 'Call conoscitiva'],
                 ['tecnica', 'Call tecnica'], ['avvio', 'Call di avvio']] as Array<[Comando, string]>)
                .map(([c, label]) => (
                <button
                  key={c}
                  onClick={() => (comando === c ? setComando(null) : apriComando(c))}
                  className={`shrink-0 rounded-full border px-3 py-1 text-xs font-semibold transition-colors ${
                    comando === c ? 'border-navy bg-navy text-white' : 'border-bordo text-tenue hover:border-spento'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* la conversazione */}
            <ZonaFile onFile={allega} messaggio="Lascia qui: lo passo ai Documenti" className="flex-1 space-y-2.5 overflow-y-auto p-4">
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
                        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-navy px-3.5 py-2 text-white">
                          <p className="whitespace-pre-wrap text-sm">{m.testo}</p>
                          <p className="mt-0.5 text-right text-[10px] text-white/60">{fmtOra(m.at)} ✓</p>
                        </div>
                      </div>
                    )
                  }
                  const [label, classe] = CHIP[m.tipo] ?? CHIP.promemoria
                  const dentro = (
                    <>
                      <span className={`mb-1 inline-block rounded-full px-2.5 py-0.5 text-[10px] font-bold ${classe}`}>
                        {m.tipo === 'brief' ? `${label} · ${fmtDateShort(m.at)}` : label}
                      </span>
                      <p className={`whitespace-pre-wrap text-sm ${m.letto ? 'text-tenue' : 'font-medium'}`}>
                        {m.testo}
                      </p>
                      <p className="mt-0.5 text-[10px] text-spento">{fmtOra(m.at)}</p>
                    </>
                  )
                  return (
                    <div key={m.id} className="flex justify-start">
                      {m.prospect_id ? (
                        <button
                          onClick={() => { setAperta(false); onOpen(m.prospect_id!) }}
                          className="max-w-[85%] rounded-2xl rounded-bl-md bg-velo/70 px-3.5 py-2 text-left hover:bg-velo"
                        >
                          {dentro}
                        </button>
                      ) : (
                        <div className="max-w-[85%] rounded-2xl rounded-bl-md bg-velo/70 px-3.5 py-2">
                          {dentro}
                        </div>
                      )}
                    </div>
                  )
                })
              )}
              <div ref={fondoRef} />
            </ZonaFile>

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
                        className="rounded-full bg-navy px-4 py-1.5 text-xs font-bold text-white disabled:opacity-30"
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
                        className="rounded-full bg-navy px-4 py-1.5 text-xs font-bold text-white disabled:opacity-30"
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
                  aria-label="Invia"
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-navy text-white transition-opacity disabled:opacity-25"
                >
                  <svg viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
                    <path d="M3 20v-6l8-2-8-2V4l19 8z" />
                  </svg>
                </button>
              </div>
            </div>
          </aside>
        </>
      )}
    </>
  )
}
