import { useEffect, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'
import { leggi as leggiPref, scrivi as scriviPref } from '../lib/preferenze'
import { PIPELINE_LABEL, type Prospect, type PipelineStage } from '../lib/types'
import { StageBadge, PipelineBadge, Card, Micro, Faccia, Spinner, Empty, sgid, daysAgo, giorni, fmtDateShort } from './ui'
import { chiuso, eCliente, ePerso, eScartato, eProspect, eInArrivo, passato, vivo, pedaggioPagato, appuntiRecenti, ricorrenteMensile, contaFasi, perFascia, MOTIVI_PERSO, type Fascia, type Appunto } from '../lib/regole'
import NuovoProgetto from './NuovoProgetto'
import { statoVivo, COLORE_STATO } from '../lib/stato'
import { sonoCeo } from '../lib/accessi'

// Tutti: l'archivio vivo, in DUE viste (Dre, 1/9). Si apre a BACHECA
// (le fasi a colonne, statica: tutto nella larghezza, niente scroll);
// un click e diventa l'elenco in ordine di arrivo, con gli ID sotto.
// LE CARTE SI TRASCINANO QUI, col pedaggio: avanti solo col riassunto
// della call; dal parco prospect si entra solo dalla Conoscitiva.

interface Props {
  onOpen: (id: string) => void
  q: string   // arriva dalla barra di ricerca in alto
}

type Vista = 'board' | 'elenco'
type Chiave = Fascia

// quante carte per colonna: oltre non si guarda una bacheca, si cerca
const LIMITE = 200

// le colonne della bacheca: le fasi vere (ordine di Dre, 1/9)
const TAPPE: Array<[string, Chiave, (p: Prospect) => boolean]> = [
  // ha risposto, l'analisi non e' ancora partita: Clara prepara, Dre manda (Dre, 9/9)
  ['In arrivo', 'arrivo', eInArrivo],
  // Dre (15/9): «uno diventa prospect dalla call tecnica in poi». Prima
  // sono lead: hanno risposto, gli abbiamo mandato l'analisi, magari
  // abbiamo fatto la conoscitiva, ma non sono ancora roba nostra. La
  // chiave resta 'prospect': ci sono appese le preferenze e gli accessi.
  ['Lead', 'prospect', eProspect],
  ['Call Conoscitiva', 'conoscitiva', (p) => p.fuori && (p.pipeline_stage ?? 'conoscitiva') === 'conoscitiva' && vivo(p)],
  ['Call Tecnica', 'tecnica', (p) => p.fuori && p.pipeline_stage === 'tecnica'],
  ['Call di Avvio', 'avvio', (p) => p.fuori && p.pipeline_stage === 'avvio'],
  ['Periodo di prova', 'prova', (p) => p.fuori && p.pipeline_stage === 'prova'],
  ['Cliente', 'cliente', eCliente],
  // perso parla del nostro processo, scartato parla della lista (Dre, 7/9):
  // ci abbiamo provato e no, oppure non era roba nostra. Due cassetti.
  ['Persi', 'perso', ePerso],
  ['Scartati', 'scartato', eScartato],
]

// I persi non stanno in fila con gli altri (Dre, 7/9): una corsia sempre
// aperta accanto alle vive e' un invito a metterci dentro qualcuno. Stanno
// in fondo, chiusi, come le task completate di Google Task. Si aprono quando
// li cerchi, e ci si puo' comunque trascinare sopra.
const VIVE = TAPPE.filter(([, c]) => c !== 'perso' && c !== 'scartato')
const PERSI = TAPPE.find(([, c]) => c === 'perso')!
const SCARTATI = TAPPE.find(([, c]) => c === 'scartato')!

// dentro i Lead si vede chi e' chi senza aprire (Dre, 7/9): non un sacco
// di 343 carte uguali, ma cinque gruppi con un nome
const GRUPPI_PROSPECT: Array<[string, (p: Prospect) => boolean]> = [
  ['Caldi', (p) => p.classificazione === 'positivo'],
  ['Rinviati', (p) => p.classificazione === 'rinvio'],
  ['Fuori ufficio', (p) => p.classificazione === 'ooo'],
  ['Tiepidi', (p) => p.classificazione === 'tiepido'],
  ['Da capire', (p) => !p.classificazione || p.classificazione === 'da_classificare'],
]

// i passati a qualcun altro non si trascinano: ci si passa dalla scheda
const aChi = (p: Prospect) => (p as unknown as { passato_a?: string }).passato_a ?? ''

const COLORE: Record<Chiave, string> = {
  arrivo: 'bg-amber-200', prospect: 'bg-amber-400', conoscitiva: 'bg-[#6b85e0]', tecnica: 'bg-blu',
  avvio: 'bg-navy', prova: 'bg-teal-600', cliente: 'bg-green-600', perso: 'bg-gray-300', scartato: 'bg-gray-200',
}

const ORDINE: Record<Chiave, number> = {
  arrivo: -1, prospect: 0, conoscitiva: 1, tecnica: 2, avvio: 3, prova: 4, cliente: 5, perso: 99, scartato: 100,
}

interface Toast {
  testo: string
  tono: 'ok' | 'stop' | 'oro'
  id?: string   // clic sul toast = apri la scheda
}

function leggiVista(): Vista {
  return (leggiPref('tutti-vista') as Vista) || 'board'
}

export default function Lista({ onOpen, q }: Props) {
  const [rows, setRows] = useState<Prospect[] | null>(null)
  const [ricorrente, setRicorrente] = useState<{ mese: number; quanti: number; senza: number } | null>(null)
  // i numeri delle colonne li conta il database, come la home: le carte
  // scaricate sono le prime 300 e non sono un conteggio (revisione 4/9)
  const [quanti, setQuanti] = useState<Record<Fascia, number> | null>(null)
  const [giro, setGiro] = useState(0)   // ogni carta mossa rifa i conti
  // la data della call di ognuno, per fase: sulla carta serve sapere QUANDO,
  // non solo che e' in Tecnica (Dre, 7/9)
  const [calls, setCalls] = useState<Record<string, Record<string, string>>>({})
  // cosa Clara ha di aperto su ognuno (bozza da approvare, domanda): va sulla carta
  const [aperte, setAperte] = useState<Record<string, { bozza: boolean; domanda: boolean }>>({})
  const [vedoSoldi, setVedoSoldi] = useState(false)
  // una colonna alla volta si puo' allargare per starci dentro
  const [fuoco, setFuoco] = useState<Chiave | null>(null)
  const [persiAperti, setPersiAperti] = useState(false)
  // quante colonne restano fuori dallo schermo, a destra
  const bacheca = useRef<HTMLDivElement | null>(null)
  const [altre, setAltre] = useState(0)
  const [scartatiAperti, setScartatiAperti] = useState(false)
  // nella vista elenco si guarda una fascia alla volta: i numeri in cima
  // sono il filtro (prima erano tre forme della stessa lista, QA Dre 14/9)
  const [fascia, setFascia] = useState<Fascia | 'tutti'>('tutti')
  const [vista, setVista] = useState<Vista>(leggiVista)
  const [dragId, setDragId] = useState<string | null>(null)
  const [sopra, setSopra] = useState<Chiave | null>(null)
  const [mosso, setMosso] = useState<string | null>(null)
  const [toast, setToast] = useState<Toast | null>(null)
  // il pedaggio al rilascio: si apre la richiesta del riassunto; senza,
  // la carta torna dov'era
  const [pedaggio, setPedaggio] = useState<{ p: Prospect; da: Chiave; target: PipelineStage } | null>(null)
  const [riassunto, setRiassunto] = useState('')
  // quello che il software ha gia' in casa su questa azienda
  const [pronti, setPronti] = useState<Appunto[]>([])
  // indietro e «Perso»: si possono fare da ogni fase, ma li confermi tu (Dre, 2/9)
  const [conferma, setConferma] = useState<
    { p: Prospect; da: Chiave; target: Chiave; tipo: 'indietro' | 'riapri' | 'perso' } | null
  >(null)
  const [motivo, setMotivo] = useState('')
  // il pedaggio del cliente: cosa gli abbiamo venduto (Dre, 4/9)
  const [nuovoCliente, setNuovoCliente] = useState<Prospect | null>(null)
  // il riassunto non si butta prima di averlo salvato (2/9)
  const [salvando, setSalvando] = useState(false)
  const [erroreP, setErroreP] = useState('')

  function misura() {
    const el = bacheca.current
    if (!el) { setAltre(0); return }
    const fuoriDx = el.scrollWidth - el.clientWidth - el.scrollLeft
    const colonna = Math.max(180, el.clientWidth / Math.max(1, Math.round(el.clientWidth / 260)))
    setAltre(fuoriDx < 24 ? 0 : Math.max(1, Math.round(fuoriDx / colonna)))
  }
  function scorri() {
    bacheca.current?.scrollBy({ left: Math.round(bacheca.current.clientWidth * 0.7), behavior: 'smooth' })
  }

  function cambiaVista(v: Vista) {
    setVista(v)
    scriviPref('tutti-vista', v)
  }

  useEffect(() => { ricorrenteMensile().then(setRicorrente) }, [])
  useEffect(() => { contaFasi().then(setQuanti) }, [giro])

  useEffect(() => {
    supabase.from('agenda').select('at,tipo,prospect_id')
      .not('prospect_id', 'is', null)
      .order('at', { ascending: false }).limit(1000)
      .then(({ data }) => {
        const m: Record<string, Record<string, string>> = {}
        for (const a of (data as Array<{ at: string; tipo: string | null; prospect_id: string }> ?? [])) {
          if (!a.tipo) continue
          const suo = (m[a.prospect_id] ??= {})
          // la piu' recente per quella fase: l'ordine e' gia' decrescente
          suo[a.tipo] ??= a.at
        }
        setCalls(m)
      })
    void sonoCeo().then(setVedoSoldi)
    supabase.from('proposte').select('prospect_id,tipo').eq('stato', 'aperta').limit(1000)
      .then(({ data }) => {
        const m: Record<string, { bozza: boolean; domanda: boolean }> = {}
        for (const pr of (data as Array<{ prospect_id: string | null; tipo: string }> ?? [])) {
          if (!pr.prospect_id) continue
          const suo = (m[pr.prospect_id] ??= { bozza: false, domanda: false })
          if (pr.tipo === 'risposta') suo.bozza = true
          else if (pr.tipo !== 'accesso') suo.domanda = true
        }
        setAperte(m)
      })
  }, [giro])

  useEffect(() => {
    let attivo = true
    const t = setTimeout(async () => {
      // UNA DOMANDA PER COLONNA (QA Dre, 14/9). Prima erano le prime 300
      // righe in ordine di ultima risposta: i 4 clienti (che non hanno
      // last_reply_at) non entravano mai, la colonna diceva «4» e sotto
      // «Nessuno», e qualunque carta ferma da prima di luglio era invisibile.
      // Le colonne chiedono al database le stesse cose che contano i numeri
      // in testa, quindi quello che leggi e quello che vedi combaciano.
      const pulito = q.trim().replace(/[,()"%]/g, ' ').trim()
      const cerca = <Q extends { or(s: string): Q }>(query: Q): Q => {
        if (!pulito) return query
        const term = `%${pulito}%`
        const campi = [`company.ilike.${term}`, `name.ilike.${term}`, `email.ilike.${term}`]
        // l'SG-ID sta in una colonna numerica: ilike non lo trova, serve l'uguale
        const num = pulito.replace(/^sg[-\s]?/i, '').replace(/\D/g, '')
        if (num && num.length <= 9 && Number(num) > 0) campi.push(`sg_id.eq.${Number(num)}`)
        return query.or(campi.join(','))
      }
      const colonna = (chiave: Chiave) => cerca(perFascia(chiave, supabase.from('prospects').select('*')))
        .order(chiave === 'cliente' ? 'canone' : 'last_reply_at', { ascending: false, nullsFirst: false })
        .limit(LIMITE)
      // cercando un nome si cerca in tutta la rubrica, anche fra le 12.500
      // aziende a cui la mail e' partita e non ha risposto nessuno: quelle
      // non stanno in nessuna colonna, ma se le cerchi devono uscire
      const giro = pulito
        ? cerca(supabase.from('prospects').select('*').eq('stage', 'nuovo').eq('fuori', false))
            .order('last_reply_at', { ascending: false, nullsFirst: false }).limit(60)
        : null
      const esiti = await Promise.all([...TAPPE.map(([, chiave]) => colonna(chiave)), ...(giro ? [giro] : [])])
      if (!attivo) return
      const visti = new Set<string>()
      const out: Prospect[] = []
      for (const e of esiti) {
        for (const r of ((e as { data: Prospect[] | null }).data ?? [])) {
          if (visti.has(r.id)) continue
          visti.add(r.id)
          out.push(r)
        }
      }
      // in ordine di arrivo: l'ultima risposta piu' recente in cima
      out.sort((a, b) => (b.last_reply_at ?? '').localeCompare(a.last_reply_at ?? ''))
      setRows(out)
    }, 200)
    return () => { attivo = false; clearTimeout(t) }
  }, [q, giro])

  useEffect(() => {
    misura()
    const r = () => misura()
    window.addEventListener('resize', r)
    return () => window.removeEventListener('resize', r)
  })

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), toast.tono === 'stop' ? 5200 : 3800)
    return () => clearTimeout(t)
  }, [toast])

  if (rows === null) return <Spinner />

  // le colonne prima del proprio perimetro non si mostrano vuote: chi entra
  // dalla call tecnica non ha «In arrivo» e «Prospect» (QA Carlo, 14/9)
  const colonne = VIVE.filter(([, c]) => !['arrivo', 'prospect'].includes(c) || rows.some(TAPPE.find(([, k]) => k === c)![2]))

  // in elenco si guarda una fascia alla volta
  const elencate = fascia === 'tutti' ? rows : rows.filter(TAPPE.find(([, c]) => c === fascia)![2])
  // mentre cerchi i cassetti si aprono da soli: prima diceva «1 risultato»
  // con le sette colonne vuote e la carta chiusa dentro Scartati (QA Dre, 14/9)
  const cercando = Boolean(q.trim())
  const vedoPersi = persiAperti || cercando
  const vedoScartati = scartatiAperti || cercando
  // quelli a cui la mail e' partita e non hanno risposto: escono solo se li cerchi
  const nelGiro = rows.filter((p) => !p.fuori && p.stage === 'nuovo')
  // il numero in testa alla colonna: quello del database, tranne quando
  // stai cercando (allora conta i trovati) o quando le carte sono tagliate
  const conta = (chiave: Chiave, dentro: number) =>
    cercando || dentro >= LIMITE || !quanti ? dentro : quanti[chiave]

  // ── il drop: le stesse regole del gioco di sempre ───────────────
  async function gestisciDrop(target: Chiave) {
    setSopra(null)
    const id = dragId
    setDragId(null)
    if (!id) return
    const p = rows!.find((x) => x.id === id)
    if (!p) return
    const nome = p.company || p.name || p.email
    const da: Chiave = p.fuori ? (p.pipeline_stage ?? 'conoscitiva') : 'prospect'
    if (da === target) return

    // «Perso» si raggiunge da ogni fase, ma col motivo (Dre, 2/9)
    if (target === 'perso') {
      setMotivo('')
      setConferma({ p, da, target, tipo: 'perso' })
      return
    }

    // tirare fuori una carta dai persi = riaprire la trattativa
    if (da === 'perso') {
      setConferma({ p, da, target, tipo: 'riapri' })
      return
    }

    const salto = ORDINE[target] - ORDINE[da]

    // indietro si può, ma non per sbaglio: prima me lo confermi (Dre, 2/9)
    if (salto < 0) {
      setConferma({ p, da, target, tipo: 'indietro' })
      return
    }

    // dal parco prospect si entra SOLO dalla Conoscitiva
    if (da === 'prospect' && target !== 'conoscitiva') {
      setToast({ testo: `${nome}: si entra dalla Conoscitiva, la prima call.`, tono: 'stop', id })
      return
    }

    // una fase alla volta, in avanti
    if (da !== 'prospect' && salto > 1) {
      setToast({ testo: 'Una fase alla volta: le call si fanno in ordine.', tono: 'stop', id })
      return
    }

    // avanti di una fase: serve il transcript della call di QUESTA fase.
    // Dalla prova al cliente no: in prova non c'e' nessuna call da
    // riassumere, il pedaggio e' il contratto (QA Dre, 14/9) e lo chiede
    // la finestra che si apre dopo
    if (da !== 'prospect' && da !== 'prova' && salto === 1) {
      const pagato = await pedaggioPagato(id, da as PipelineStage)
      if (!pagato) {
        setRiassunto('')
        setPedaggio({ p, da: da as PipelineStage, target: target as PipelineStage })
        // gli appunti di quella call spesso ci sono gia': si propongono
        void appuntiRecenti(id).then(setPronti)
        return
      }
    }

    // dal parco alla Conoscitiva non si paga niente: non c'e' ancora nessuna
    // call da riassumere, e il contesto sta gia' nella cartella (Dre, 2/9)
    if (da === 'prospect') {
      await entra(p)
      return
    }

    await muovi(id, nome, target as PipelineStage, salto)
  }

  async function entra(p: Prospect): Promise<boolean> {
    const patch: Record<string, unknown> = {
      fuori: true,
      fuori_at: new Date().toISOString(),
      pipeline_stage: 'conoscitiva',
      awaiting_us: false,
    }
    const nome = p.company || p.name || p.email
    const { data } = await supabase.from('prospects').update(patch).eq('id', p.id).select().single()
    if (!data) {
      setToast({ testo: `${nome}: non sono riuscito a salvare, la carta resta dov'era`, tono: 'stop', id: p.id })
      return false
    }
    await supabase.from('interactions').insert({
      prospect_id: p.id, at: new Date().toISOString(), kind: 'nota',
      body: 'Entra in Conoscitiva.',
    }).select().single()
    setRows((rs) => rs!.map((x) => (x.id === p.id ? (data as Prospect) : x)))
    setGiro((g) => g + 1)
    setMosso(p.id)
    setToast({ testo: `${nome} entra in Conoscitiva`, tono: 'ok', id: p.id })
    return true
  }

  // tornare nel parco prospect vuol dire uscire dalla pipeline
  async function esci(p: Prospect) {
    const nome = p.company || p.name || p.email
    const patch = { fuori: false, fuori_at: null, pipeline_stage: null, next_action: null, next_action_date: null }
    const { data } = await supabase.from('prospects').update(patch).eq('id', p.id).select().single()
    if (!data) {
      setToast({ testo: `${nome}: non sono riuscito a salvare, la carta resta dov'era`, tono: 'stop', id: p.id })
      return
    }
    await supabase.from('interactions').insert({
      prospect_id: p.id, at: new Date().toISOString(), kind: 'nota',
      body: 'Uscita dalla pipeline: torna fra i lead.',
    }).select().single()
    setRows((rs) => rs!.map((x) => (x.id === p.id ? (data as Prospect) : x)))
    setGiro((g) => g + 1)
    setMosso(p.id)
    setToast({ testo: `${nome} torna fra i lead`, tono: 'ok', id: p.id })
  }

  // «Perso» da qualunque fase: il motivo resta scritto nella storia
  async function perdi(p: Prospect, perche: string) {
    const nome = p.company || p.name || p.email
    const patch: Record<string, unknown> = p.fuori
      ? { pipeline_stage: 'perso', lost_reason: perche, next_action: null, next_action_date: null }
      : { stage: 'perso', lost_reason: perche, next_action: null, next_action_date: null }
    const { data } = await supabase.from('prospects').update(patch).eq('id', p.id).select().single()
    if (!data) {
      setToast({ testo: `${nome}: non sono riuscito a salvare, la carta resta dov'era`, tono: 'stop', id: p.id })
      return
    }
    await supabase.from('interactions').insert({
      prospect_id: p.id, at: new Date().toISOString(), kind: 'nota',
      body: `Segnato come perso: ${perche}`,
    }).select().single()
    setRows((rs) => rs!.map((x) => (x.id === p.id ? (data as Prospect) : x)))
    setGiro((g) => g + 1)
    setMosso(p.id)
    setToast({ testo: `${nome} segnato perso`, tono: 'ok', id: p.id })
  }

  async function muovi(id: string, nome: string, target: PipelineStage, salto: number, come?: 'riapri'): Promise<boolean> {
    const patch: Record<string, unknown> = { pipeline_stage: target, next_action: null, next_action_date: null }
    if (come === 'riapri') patch.lost_reason = null
    // chi smette di essere cliente si porta via anche il contratto, se no
    // resta appeso al record un canone che nessuno paga più
    const prima = rows!.find((x) => x.id === id)
    const eraCliente = prima?.pipeline_stage === 'cliente' && target !== 'cliente'
    if (eraCliente) { patch.contratto = null; patch.canone = null }
    const { data } = await supabase.from('prospects').update(patch).eq('id', id).select().single()
    if (!data) {
      setToast({ testo: `${nome}: non sono riuscito a salvare, la carta resta dov'era`, tono: 'stop', id })
      return false
    }
    await supabase.from('interactions').insert({
      prospect_id: id, at: new Date().toISOString(), kind: 'nota',
      body: come === 'riapri'
        ? `Riaperta: torna in ${PIPELINE_LABEL[target]}`
        : salto > 0
        ? (target === 'cliente' ? 'DIVENTA CLIENTE.' : `Passa a ${PIPELINE_LABEL[target]}`)
        : `Torna in ${PIPELINE_LABEL[target]}${eraCliente ? ': contratto e canone azzerati' : ''}`,
    }).select().single()
    setRows((rs) => rs!.map((x) => (x.id === id ? (data as Prospect) : x)))
    setGiro((g) => g + 1)
    setMosso(id)
    if (come === 'riapri') {
      setToast({ testo: `${nome} riaperta in ${PIPELINE_LABEL[target]}`, tono: 'ok', id })
    } else if (target === 'cliente') {
      setNuovoCliente(data as Prospect)
      setToast({ testo: `${nome} è cliente, apri la scheda e scegli il contratto`, tono: 'oro', id })
    } else if (salto > 0) {
      setToast({ testo: `${nome} passa a ${PIPELINE_LABEL[target]}`, tono: 'ok', id })
    } else {
      setToast({ testo: `${nome} torna in ${PIPELINE_LABEL[target]}`, tono: 'ok', id })
    }
    return true
  }

  const rigaElenco = (p: Prospect) => {
    const fermo = daysAgo(p.last_reply_at)
    const finito = chiuso(p)
    const tonoFermo = finito || fermo === null ? 'text-spento'
      : fermo >= 30 ? 'font-bold text-red-700'
      : fermo >= 10 ? 'font-semibold text-amber-700'
      : 'text-spento'
    return (
      <button
        key={p.id}
        onClick={() => onOpen(p.id)}
        className="flex w-full items-center gap-3 border-b border-velo px-4 py-2.5 text-left transition-colors last:border-0 hover:bg-velo/60"
      >
        <Faccia p={p} size={36} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold">
            {p.company || p.name || p.email}
            {p.company && p.name ? <span className="font-normal text-tenue">, {p.name}</span> : null}
          </p>
          <p className="truncate text-xs text-tenue">
            {sgid(p.sg_id, p) && <span className="font-semibold text-blu">{sgid(p.sg_id, p)}</span>}
            {sgid(p.sg_id, p) && ', '}
            {p.email}
            {p.last_reply_at && <>, ultima risposta {fmtDateShort(p.last_reply_at)}</>}
          </p>
        </div>
        {eCliente(p) && vedoSoldi ? (
          <span className="hidden shrink-0 text-right text-xs sm:block">
            <span className="block font-bold text-green-800">
              {p.canone ? `${Number(p.canone).toLocaleString('it-IT')} €/mese` : 'canone da mettere'}
            </span>
            <span className="block text-spento">
              {p.contratto === 'prova' ? 'in prova' : p.contratto === 'stable' ? 'stabile' : 'contratto da scegliere'}
              {p.fuori_at ? `, da ${fmtDateShort(p.fuori_at)}` : ''}
            </span>
          </span>
        ) : fermo !== null && !finito ? (
          <span className={`hidden shrink-0 text-xs sm:block ${tonoFermo}`}>{giorni(fermo)}</span>
        ) : null}
        {p.fuori && p.pipeline_stage
          ? <PipelineBadge stage={p.pipeline_stage} />
          : <StageBadge stage={p.stage} />}
      </button>
    )
  }

  const cartaBoard = (p: Prospect, fase?: Chiave) => {
    const quando = fase ? calls[p.id]?.[fase] : undefined
    // LO STATO VIVO (Dre, 14/9): la riga sotto il nome dice la verita' di
    // oggi. Rassicura o dice chiaro che c'e' qualcosa da fare.
    const stato = statoVivo(p, {
      call: quando ?? null, fase, calls: calls[p.id],
      bozza: aperte[p.id]?.bozza, domanda: aperte[p.id]?.domanda,
    })
    const colore = COLORE_STATO[stato.tono]
    // i chiusi «vecchio stile» (mai passati dalla pipeline) non si trascinano
    // un passato a qualcun altro non si trascina, se no dopo il rilascio
    // compariva in due colonne insieme (revisione 4/9)
    const trascinabile = !passato(p) && !((!p.fuori) && (p.stage === 'cliente' || p.stage === 'perso'))
    const inPresa = dragId === p.id
    const codice = sgid(p.sg_id, p)
    return (
      <button
        key={p.id}
        onClick={() => onOpen(p.id)}
        draggable={trascinabile}
        onDragStart={(e) => {
          setDragId(p.id)
          e.dataTransfer.effectAllowed = 'move'
        }}
        onDragEnd={() => { setDragId(null); setSopra(null) }}
        className={`group flex w-full flex-col gap-1.5 rounded-xl border bg-white px-3 py-2.5 text-left shadow-[0_1px_2px_rgba(16,24,40,0.05)] transition-all hover:border-blu ${
          inPresa ? 'rotate-2 scale-[1.04] border-navy opacity-50 shadow-[0_12px_28px_rgba(6,23,115,0.2)]' : stato.tono === 'azione' ? 'border-red-200' : 'border-bordo'
        } ${mosso === p.id ? 'atterra' : ''} ${trascinabile ? 'cursor-grab active:cursor-grabbing' : ''}`}
      >
        <span className="flex items-center gap-2">
          <Faccia p={p} size={24} />
          <span className="min-w-0 flex-1 truncate text-[13px] font-semibold">{p.company || p.name || p.email}</span>
          {codice && (
            <span className="shrink-0 text-[10px] font-bold text-blu/70 opacity-0 transition-opacity group-hover:opacity-100">
              {codice}
            </span>
          )}
        </span>
        <span className="flex items-start gap-1.5 text-[12px] leading-snug">
          <span className={`mt-[5px] inline-block h-[7px] w-[7px] shrink-0 rounded-full ${colore.pallino}`} />
          <span className={colore.testo}>{stato.testo}</span>
        </span>
      </button>
    )
  }

  return (
    <div className="pb-24 sm:pb-8">
      <div className="mb-2.5 flex items-center gap-1.5 overflow-x-auto pb-1">
        {/* il selettore della vista */}
        <div className="mr-2 flex shrink-0 overflow-hidden rounded-full border border-bordo bg-white">
          <button
            onClick={() => cambiaVista('board')}
            aria-label="Vista bacheca"
            className={`px-3 py-1.5 ${vista === 'board' ? 'bg-blu text-white' : 'text-tenue hover:bg-velo'}`}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4">
              <path d="M4 5h4v14H4zM10 5h4v9h-4zM16 5h4v6h-4z" />
            </svg>
          </button>
          <button
            onClick={() => cambiaVista('elenco')}
            aria-label="Vista elenco"
            className={`px-3 py-1.5 ${vista === 'elenco' ? 'bg-blu text-white' : 'text-tenue hover:bg-velo'}`}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4">
              <path d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>

        {/* i filtri per stato erano una terza forma della stessa lista: in
            bacheca le fasi sono le colonne, in elenco sono i numeri in cima
            (QA Dre, 14/9) */}
      </div>

      {q.trim() && (
        <p className="mb-1.5 text-xs text-tenue">
          «{q.trim()}»: {rows.length} risultat{rows.length === 1 ? 'o' : 'i'}
        </p>
      )}

      {/* quando guardi i clienti, il numero che conta e' uno solo: e' lo
          stesso che vedi in Tutti, perche' e' la stessa domanda al database
          e non la somma delle righe di questa pagina (revisione 4/9) */}
      {vista === 'elenco' && fascia === 'cliente' && vedoSoldi && ricorrente && ricorrente.quanti > 0 && (
        <div className="mb-2.5 flex flex-wrap items-baseline gap-x-4 gap-y-1 rounded-xl border border-bordo bg-white px-4 py-2.5">
          <span className="text-lg font-extrabold tabular-nums">{ricorrente.mese.toLocaleString('it-IT')} €</span>
          <Micro>al mese</Micro>
          <span className="text-sm font-semibold text-tenue">
            {ricorrente.quanti} client{ricorrente.quanti === 1 ? 'e' : 'i'}
          </span>
          {ricorrente.senza > 0 && (
            <span className="text-xs font-semibold text-amber-700">
              {ricorrente.senza} senza canone: il totale è più basso del vero
            </span>
          )}
        </div>
      )}

      {vista === 'elenco' && (
        <div className="mb-2.5 flex flex-wrap items-center gap-x-5 gap-y-2 rounded-xl border border-bordo bg-white px-4 py-2.5">
          <button
            onClick={() => setFascia('tutti')}
            className={`text-xs font-semibold ${fascia === 'tutti' ? 'text-blu' : 'text-tenue hover:text-inchiostro'}`}
          >
            Tutti
          </button>
          {TAPPE.map(([nome, chiave, filtro]) => (
            <button
              key={chiave}
              onClick={() => setFascia((f) => (f === chiave ? 'tutti' : chiave))}
              className={`flex items-baseline gap-1.5 text-left ${fascia === chiave ? '' : 'opacity-70 hover:opacity-100'}`}
            >
              <span className={`inline-block h-[7px] w-[7px] shrink-0 self-center rounded-full ${COLORE[chiave]}`} />
              <span className="text-base font-extrabold tabular-nums">
                {q.trim() || rows.filter(filtro).length >= LIMITE || !quanti ? rows.filter(filtro).length : quanti[chiave]}
              </span>
              <Micro className={fascia === chiave ? 'text-blu' : undefined}>{nome}</Micro>
            </button>
          ))}
        </div>
      )}

      {vista === 'elenco' ? (
        <>
          <Card>
            {elencate.length === 0
              ? <Empty text={q.trim() ? `Niente per «${q.trim()}».` : 'Nessuno qui dentro.'} />
              : elencate.map(rigaElenco)}
          </Card>
        </>
      ) : (
        <div className="relative">
        {/* si scorre di lato: prima non c'era nessun segno e le colonne oltre
            il bordo (Cliente compresa) si scoprivano per caso (QA browser, 15/9) */}
        {altre > 0 && (
          <button onClick={scorri} aria-label="Vedi le altre colonne"
                  className="absolute right-0 top-1/2 z-10 hidden -translate-y-1/2 items-center gap-1 rounded-full border border-bordo bg-white/95 px-2.5 py-2 text-xs font-bold text-navy shadow-[0_4px_14px_rgba(16,24,40,0.14)] lg:flex">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" className="h-4 w-4"><path d="M9 6l6 6-6 6" /></svg>
            {altre}
          </button>
        )}
        <div
          ref={bacheca}
          onScroll={misura}
          className="-mx-4 grid gap-3 overflow-x-auto px-4 pb-2 lg:-mx-8 lg:px-8"
          style={{
            // ogni colonna ha una larghezza minima da leggere (Dre, 14/9: le
            // carte strette «danno l'impressione di cose chiuse»): se non ci
            // stanno tutte, si scorre di lato come su Trello. La colonna a fuoco
            // si prende piu' spazio, le altre si stringono ma restano (Dre, 7/9)
            gridTemplateColumns: colonne.map(([, c]) =>
              fuoco === null ? 'minmax(236px, 1fr)'
              : fuoco === c ? 'minmax(380px, 3fr)'
              : 'minmax(170px, 0.7fr)').join(' '),
          }}
        >
          {colonne.map(([nome, chiave, filtro]) => {
            const dentro = rows.filter(filtro)
            // la corsia Persi c'e' sempre: prima compariva quando alzavi una
            // carta e spostava tutte le altre sotto il dito (revisione 4/9)
            const evidenziata = sopra === chiave && dragId !== null
            return (
              <section
                key={nome}
                onDragOver={(e) => {
                  e.preventDefault()
                  e.dataTransfer.dropEffect = 'move'
                  setSopra(chiave)
                }}
                onDragLeave={(e) => {
                  if (!(e.currentTarget as HTMLElement).contains(e.relatedTarget as Node)) setSopra(null)
                }}
                onDrop={(e) => { e.preventDefault(); gestisciDrop(chiave) }}
                className={`flex max-h-[72vh] min-w-0 flex-col rounded-2xl transition-all ${
                  evidenziata ? 'bg-navy/10 ring-2 ring-navy/40' : 'bg-velo'
                }`}
              >
                <header className="flex items-baseline justify-between gap-2 px-3 pb-2 pt-2.5">
                  <button
                    onClick={() => setFuoco((f) => (f === chiave ? null : chiave))}
                    title={fuoco === chiave ? 'Rimetti tutte uguali' : 'Allarga questa colonna'}
                    className="flex min-w-0 items-baseline gap-1.5 text-left"
                  >
                    <Micro className={fuoco === chiave ? 'text-blu' : 'text-inchiostro'}>{nome}</Micro>
                    {chiave === 'tecnica' && (
                      <span className="shrink-0 rounded-full bg-blu/10 px-1.5 text-[9px] font-bold uppercase tracking-wide text-navy">
                        prospect
                      </span>
                    )}
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
                      className={`h-3 w-3 shrink-0 self-center ${fuoco === chiave ? 'text-blu' : 'text-spento'}`}>
                      {fuoco === chiave
                        ? <path d="M9 15 4 20m0-5v5h5M15 9l5-5m0 5V4h-5" />
                        : <path d="M4 20l5-5m-5 5v-5h5M20 4l-5 5m5-5v5h-5" />}
                    </svg>
                  </button>
                  <span className="text-xs font-semibold text-tenue">{conta(chiave, dentro.length)}</span>
                </header>
                <div className="flex-1 space-y-1.5 overflow-y-auto px-2 pb-2">
                  {dentro.length === 0
                    ? <p className="px-1.5 py-1 text-xs text-spento">{evidenziata ? 'Lascia qui' : 'Nessuno'}</p>
                    : chiave === 'prospect'
                      ? GRUPPI_PROSPECT.map(([nome, dentroGruppo]) => {
                          const suoi = dentro.filter(dentroGruppo)
                          if (suoi.length === 0) return null
                          return (
                            <div key={nome} className="space-y-1.5">
                              <p className="flex items-baseline gap-1.5 px-1.5 pt-1.5 text-[10px] font-bold uppercase tracking-[0.05em] text-spento">
                                {nome} <span className="tabular-nums text-tenue">{suoi.length}</span>
                              </p>
                              {suoi.map((p) => cartaBoard(p, chiave))}
                            </div>
                          )
                        })
                      : dentro.map((p) => cartaBoard(p, chiave))}
                </div>
              </section>
            )
          })}
        </div>
        </div>
      )}

      {/* i passati: raggruppati per chi li ha ricevuti, cosi' non si perde
          il rapporto con chi te li ha presi in mano */}
      {vista === 'board' && rows.some(passato) && (
        <div className="mt-3 rounded-2xl bg-velo p-3">
          <div className="mb-2 flex items-baseline gap-2 px-1">
            <Micro className="text-inchiostro">Passati a qualcun altro</Micro>
            <span className="text-xs font-semibold text-tenue">{rows.filter(passato).length}</span>
          </div>
          <div className="flex flex-wrap gap-4">
            {[...new Set(rows.filter(passato).map(aChi))].map((chi) => (
              <div key={chi} className="min-w-[180px] flex-1">
                <p className="mb-1 px-1 text-xs font-bold text-blu">{chi}</p>
                <div className="space-y-1.5">
                  {rows.filter((p) => aChi(p) === chi).map((p) => cartaBoard(p))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {vista === 'board' && (
        <section
          onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; setSopra('perso') }}
          onDragLeave={(e) => {
            if (!(e.currentTarget as HTMLElement).contains(e.relatedTarget as Node)) setSopra(null)
          }}
          onDrop={(e) => { e.preventDefault(); gestisciDrop('perso') }}
          className={`mt-3 rounded-2xl transition-all ${
            sopra === 'perso' && dragId !== null ? 'bg-navy/10 ring-2 ring-navy/40' : ''
          }`}
        >
          <button
            onClick={() => setPersiAperti((v) => !v)}
            className="flex w-full items-center gap-2 rounded-2xl px-3 py-2 text-left hover:bg-velo"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
              className={`h-3 w-3 text-spento transition-transform ${vedoPersi ? 'rotate-90' : ''}`}>
              <path d="M9 6l6 6-6 6" />
            </svg>
            <Micro className="text-spento">Persi</Micro>
            <span className="text-xs font-semibold text-spento">
              {conta('perso', rows.filter(PERSI[2]).length)}
            </span>
            {sopra === 'perso' && dragId !== null && (
              <span className="ml-2 text-xs font-bold text-navy">lascia qui per segnarlo perso</span>
            )}
          </button>
          {vedoPersi && (
            <div className="grid gap-1.5 px-3 pb-3 sm:grid-cols-2 lg:grid-cols-4">
              {rows.filter(PERSI[2]).length === 0
                ? <p className="px-1.5 py-1 text-xs text-spento">Nessuno</p>
                : rows.filter(PERSI[2]).map((p) => cartaBoard(p))}
            </div>
          )}
        </section>
      )}

      {vista === 'board' && (
        <section className="mt-1 rounded-2xl">
          <button
            onClick={() => setScartatiAperti((v) => !v)}
            className="flex w-full items-center gap-2 rounded-2xl px-3 py-2 text-left hover:bg-velo"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
              className={`h-3 w-3 text-spento transition-transform ${vedoScartati ? 'rotate-90' : ''}`}>
              <path d="M9 6l6 6-6 6" />
            </svg>
            <Micro className="text-spento">Scartati</Micro>
            <span className="text-xs font-semibold text-spento">
              {conta('scartato', rows.filter(SCARTATI[2]).length)}
            </span>
          </button>
          {vedoScartati && (
            <div className="grid gap-1.5 px-3 pb-3 sm:grid-cols-2 lg:grid-cols-4">
              {rows.filter(SCARTATI[2]).length === 0
                ? <p className="px-1.5 py-1 text-xs text-spento">Nessuno</p>
                : rows.filter(SCARTATI[2]).map((p) => cartaBoard(p))}
            </div>
          )}
        </section>
      )}

      {/* chi non ha ancora risposto non sta in nessuna colonna: se lo cerchi,
          esce qui sotto, cosi' la lente trova tutta la rubrica (QA Dre, 14/9) */}
      {vista === 'board' && nelGiro.length > 0 && (
        <div className="mt-3 rounded-2xl bg-velo p-3">
          <div className="mb-2 flex items-baseline gap-2 px-1">
            <Micro className="text-inchiostro">Nel giro di mail</Micro>
            <span className="text-xs font-semibold text-tenue">{nelGiro.length}</span>
            <span className="text-xs text-spento">non hanno ancora risposto</span>
          </div>
          <div className="grid gap-1.5 sm:grid-cols-2 lg:grid-cols-4">
            {nelGiro.map((p) => cartaBoard(p))}
          </div>
        </div>
      )}

      {/* IL PEDAGGIO: la richiesta che si apre al rilascio della carta */}
      {pedaggio && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-inchiostro/30 px-4">
          <div className="salta-su w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
            <p className="text-base font-extrabold">Riassunto di fase</p>
            <p className="mt-1 text-sm text-tenue">
              {pedaggio.p.company || pedaggio.p.name}
              {`, da ${PIPELINE_LABEL[pedaggio.da as PipelineStage]} a ${PIPELINE_LABEL[pedaggio.target]}`}
            </p>
            {/* quello che c'e' gia': gli appunti di Gemini o il transcript
                incollato. Un clic e sono dentro, poi si corregge (Dre, 15/9) */}
            {pronti.length > 0 && riassunto.trim() === '' && (
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Micro>Ce l'ho già</Micro>
                {pronti.map((a) => (
                  <button key={a.at} onClick={() => setRiassunto(a.body)}
                          className="rounded-full border border-blu/40 bg-blu/5 px-3 py-1 text-xs font-semibold text-navy hover:border-blu">
                    {a.body.startsWith('Appunti di Gemini') ? 'Appunti di Gemini' : 'Riassunto della call'}, {fmtDateShort(a.at.slice(0, 10))}
                  </button>
                ))}
              </div>
            )}
            <textarea
              autoFocus
              value={riassunto}
              onChange={(e) => setRiassunto(e.target.value)}
              placeholder="Il riassunto della call e i prossimi passi…"
              className="mt-3 min-h-32 w-full rounded-lg border border-bordo px-3 py-2 text-sm outline-none focus:border-blu"
            />
            {erroreP && (
              <p className="mt-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-800">
                {erroreP}
              </p>
            )}
            <div className="mt-3 flex items-center justify-end gap-2.5">
              <button
                onClick={() => {
                  const nome = pedaggio.p.company || pedaggio.p.name || pedaggio.p.email
                  setToast({
                    testo: `${nome} resta in ${PIPELINE_LABEL[pedaggio.da as PipelineStage]}: senza riassunto non si avanza`,
                    tono: 'stop', id: pedaggio.p.id,
                  })
                  setPedaggio(null)
                  setRiassunto('')
                  setErroreP('')
                }}
                className="rounded-full border border-bordo px-4 py-2 text-sm font-semibold text-tenue hover:border-spento"
              >
                Annulla
              </button>
              <button
                onClick={async () => {
                  const { p, da, target } = pedaggio
                  const testo = riassunto.trim()
                  if (!testo || salvando) return
                  setSalvando(true)
                  setErroreP('')
                  const { data } = await supabase.from('interactions').insert({
                    prospect_id: p.id, at: new Date().toISOString(), kind: 'transcript',
                    body: `[${PIPELINE_LABEL[da as PipelineStage]}] ${testo}`,
                  }).select().single()
                  if (!data) {
                    setSalvando(false)
                    setErroreP('Non è stato salvato. Il testo è ancora qui: riprova.')
                    return
                  }
                  const mossa = await muovi(p.id, p.company || p.name || p.email, target, 1)
                  setSalvando(false)
                  if (!mossa) {
                    setErroreP('Il riassunto è al sicuro, ma la carta non si è mossa: riprova a trascinarla.')
                    return
                  }
                  setPedaggio(null); setRiassunto('')
                }}
                disabled={!riassunto.trim() || salvando}
                className="rounded-full bg-blu px-5 py-2 text-sm font-bold text-white hover:bg-blu-scuro disabled:cursor-not-allowed disabled:opacity-30"
              >
                {salvando ? 'Salvo…' : 'Salva e porta avanti'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* INDIETRO, RIAPERTURA E PERSO: si possono fare, ma li confermi tu (Dre, 2/9) */}
      {conferma && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-inchiostro/30 px-4">
          <div className="salta-su w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <p className="text-base font-extrabold">
              {conferma.tipo === 'perso' ? 'Segna come perso'
                : conferma.tipo === 'riapri' ? 'Riapri la trattativa'
                : 'Torna indietro'}
            </p>
            <p className="mt-1 text-sm text-tenue">
              <span className="font-semibold text-inchiostro">
                {conferma.p.company || conferma.p.name || conferma.p.email}
              </span>
              {conferma.tipo === 'perso'
                ? ' esce dalla pipeline.'
                : conferma.target === 'prospect'
                ? ' esce dalla pipeline e torna fra i lead.'
                : conferma.tipo === 'riapri'
                ? ` torna in ${PIPELINE_LABEL[conferma.target as PipelineStage]}.`
                : ` torna da ${PIPELINE_LABEL[conferma.da as PipelineStage]} a ${PIPELINE_LABEL[conferma.target as PipelineStage]}.`}
              {' Resta scritto nella storia.'}
            </p>
            {conferma.tipo === 'perso' && (
              <>
                {/* sono sempre le stesse quattro frasi: un clic invece di
                    riscriverle ogni volta (rapporto attriti, 15/9) */}
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {MOTIVI_PERSO.map((m) => (
                    <button key={m} onClick={() => setMotivo(m)}
                            className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                              motivo === m ? 'border-navy bg-blu text-white' : 'border-bordo bg-white text-tenue hover:border-navy hover:text-navy'}`}>
                      {m}
                    </button>
                  ))}
                </div>
                <textarea
                  autoFocus
                  value={motivo}
                  onChange={(e) => setMotivo(e.target.value)}
                  placeholder="O scrivilo con parole tue"
                  className="mt-2 min-h-20 w-full rounded-lg border border-bordo px-3 py-2 text-sm outline-none focus:border-blu"
                />
              </>
            )}
            <div className="mt-4 flex items-center justify-end gap-2.5">
              <button
                onClick={() => { setConferma(null); setMotivo('') }}
                className="rounded-full border border-bordo px-4 py-2 text-sm font-semibold text-tenue hover:border-spento"
              >
                Annulla
              </button>
              <button
                onClick={async () => {
                  const { p, target, tipo } = conferma
                  const perche = motivo.trim()
                  if (tipo === 'perso' && !perche) return
                  const nome = p.company || p.name || p.email
                  setConferma(null)
                  setMotivo('')
                  if (tipo === 'perso') { await perdi(p, perche); return }
                  if (target === 'prospect') { await esci(p); return }
                  await muovi(p.id, nome, target as PipelineStage, tipo === 'riapri' ? 1 : -1,
                    tipo === 'riapri' ? 'riapri' : undefined)
                }}
                disabled={conferma.tipo === 'perso' && !motivo.trim()}
                className={`rounded-full px-5 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-30 ${
                  conferma.tipo === 'perso' ? 'bg-red-700 hover:bg-red-800' : 'bg-navy hover:bg-blu-scuro'
                }`}
              >
                {conferma.tipo === 'perso' ? 'Segna come perso'
                  : conferma.tipo === 'riapri' ? 'Riapri'
                  : 'Sì, torna indietro'}
              </button>
            </div>
          </div>
        </div>
      )}

      {nuovoCliente && (
        <NuovoProgetto
          prospectId={nuovoCliente.id}
          nomeCliente={nuovoCliente.company || nuovoCliente.name || nuovoCliente.email}
          onFatto={() => setNuovoCliente(null)}
        />
      )}

      {/* il toast: la voce della bacheca */}
      {toast && (
        <button
          onClick={() => { if (toast.id) onOpen(toast.id); setToast(null) }}
          className={`salta-su fixed bottom-20 left-1/2 z-40 -translate-x-1/2 rounded-full px-5 py-2.5 text-sm font-bold shadow-[0_8px_24px_rgba(16,24,40,0.2)] sm:bottom-6 ${
            toast.tono === 'oro' ? 'bg-blu text-white'
            : toast.tono === 'stop' ? 'border border-amber-300 bg-amber-50 text-amber-900'
            : 'border border-green-200 bg-green-50 text-green-800'
          }`}
        >
          {toast.testo}
        </button>
      )}
    </div>
  )
}
