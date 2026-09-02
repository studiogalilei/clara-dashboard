import { useEffect, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'
import {
  STAGES, STAGE_LABEL, KIND_LABEL,
  PIPELINE_LABEL, PIPELINE_NEXT,
  CLASSIFICAZIONI, CLS_LABEL,
  type Prospect, type Interaction, type Stage, type PipelineStage, type Classificazione,
  type AgendaItem,
} from '../lib/types'
import { mercatoDi } from '../lib/mercato'
import { eCliente, ePerso, oggi, pedaggioPagato, marcaFase } from '../lib/regole'
import {
  Card, TitoloCard, Auto, SeasonChart, Spinner, ZonaFile, Faccia,
  fmtDate, fmtDateShort, fmtOra, daysAgo, giorni, fmtNum, sgid,
} from './ui'

// La scheda del prospect, riordinata (sintesi 31/8): in 5 secondi si deve
// capire CHI e', DOVE siamo e COSA fare adesso. Testata con stepper delle
// fasi e UN solo bottone d'azione calcolato; carta «Adesso» col presente;
// mercato compresso nel verdetto; il cancello fuori-binario e' una domanda
// al primo gesto di scrittura, non un banner fisso.

interface Props {
  id: string
  onClose: () => void
}

const CAMPI: Array<{ key: keyof Prospect; label: string; type?: string }> = [
  { key: 'name', label: 'Referente' },
  { key: 'role', label: 'Ruolo' },
  { key: 'email', label: 'Email', type: 'email' },
  { key: 'phone', label: 'Telefono', type: 'tel' },
  { key: 'linkedin', label: 'LinkedIn' },
  { key: 'company', label: 'Azienda' },
  { key: 'website', label: 'Sito' },
  { key: 'sector', label: 'Settore' },
  { key: 'city', label: 'Città' },
  { key: 'descrizione', label: 'Chi sono' },
  { key: 'campaign', label: 'Campagna' },
  { key: 'next_action', label: 'Prossima azione' },
  { key: 'next_action_date', label: 'Data prossima azione', type: 'date' },
  { key: 'lost_reason', label: 'Motivo perso / rinvio' },
]

// le sette tappe del percorso, per lo stepper in testata
const TAPPE = ['Risposta', 'Analisi', 'Follow-up', 'Conoscitiva', 'Tecnica', 'Avvio', 'Cliente']

function tappaCorrente(p: Prospect): number {
  if (p.fuori && p.pipeline_stage) {
    return { conoscitiva: 3, tecnica: 4, avvio: 5, cliente: 6, perso: 3 }[p.pipeline_stage] ?? 3
  }
  if (p.stage === 'in_follow_up') return 2
  if (p.stage === 'analisi_inviata') return 1
  return 0
}

export default function Scheda({ id, onClose }: Props) {
  const [p, setP] = useState<Prospect | null>(null)
  const [timeline, setTimeline] = useState<Interaction[] | null>(null)
  const [draft, setDraft] = useState<Partial<Prospect>>({})
  const [nota, setNota] = useState('')
  const [transcript, setTranscript] = useState('')
  const [modifica, setModifica] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [errore, setErrore] = useState<string | null>(null)
  const [avanzataA, setAvanzataA] = useState<PipelineStage | null>(null)
  const [dataPasso, setDataPasso] = useState('')
  const [premio, setPremio] = useState<string[]>([])
  const [pagato, setPagato] = useState(false)
  // «Perso» si raggiunge da ogni fase, anche da qui (Dre, 2/9)
  const [persoAperto, setPersoAperto] = useState(false)
  const [motivoPerso, setMotivoPerso] = useState('')
  const [giro, setGiro] = useState(0)
  const [binarioSegnato, setBinarioSegnato] = useState(false)
  // il cancello: se fuori_binario e' null, la prima azione di scrittura
  // apre la domanda e l'azione riparte dopo la risposta
  const [cancello, setCancello] = useState<(() => void) | null>(null)
  const [noteAperte, setNoteAperte] = useState(false)
  const [notaTesto, setNotaTesto] = useState('')
  const [notaData, setNotaData] = useState('')
  const [notaClara, setNotaClara] = useState(false)
  const [notaEsito, setNotaEsito] = useState<string | null>(null)
  const docRef = useRef<HTMLInputElement>(null)
  const [prossimaCall, setProssimaCall] = useState<AgendaItem | null>(null)
  const [prepAperta, setPrepAperta] = useState(false)
  const [prepChiesta, setPrepChiesta] = useState(false)
  const appuntiRef = useRef<HTMLTextAreaElement>(null)
  const transcriptRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    supabase.from('prospects').select('*').eq('id', id).single()
      .then(({ data }) => setP(data as Prospect))
    supabase.from('interactions').select('*').eq('prospect_id', id)
      .order('at', { ascending: false }).limit(200)
      .then(({ data }) => setTimeline([...((data as Interaction[]) ?? [])].reverse()))
    supabase.from('agenda').select('*').eq('prospect_id', id)
      .gte('at', new Date().toISOString())
      .order('at', { ascending: true }).limit(1)
      .then(({ data }) => setProssimaCall(((data as AgendaItem[]) ?? [])[0] ?? null))
  }, [id])

  useEffect(() => {
    if (!p?.pipeline_stage) { setPagato(false); return }
    pedaggioPagato(id, p.pipeline_stage).then(setPagato)
  }, [id, p?.pipeline_stage, giro])

  const dirty = Object.keys(draft).length > 0

  async function chiudi() {
    if (dirty) await save()
    onClose()
  }

  function edit(key: keyof Prospect, value: string) {
    setSaved(false)
    setDraft((d) => ({ ...d, [key]: value === '' ? null : value }))
  }

  async function save() {
    if (!p) return
    setSaving(true)
    // le correzioni a mano vincono per sempre: campo marcato 'manual',
    // il sync non lo tocca piu'
    const enriched = { ...(p.enriched ?? {}) }
    for (const k of Object.keys(draft)) enriched[k] = 'manual'
    const { data, error } = await supabase.from('prospects')
      .update({ ...draft, enriched }).eq('id', id).select().single()
    if (!error && data) {
      setP(data as Prospect)
      setDraft({})
      setSaved(true)
    } else if (error) {
      setErrore('Salvataggio non riuscito: il database non è aggiornato (schema v4).')
    }
    setSaving(false)
  }

  async function aggiorna(patch: Partial<Prospect>): Promise<boolean> {
    if (!p) return false
    const { data, error } = await supabase.from('prospects')
      .update(patch).eq('id', id).select().single()
    if (data) setP(data as Prospect)
    if (error) setErrore('Salvataggio non riuscito: il database non è aggiornato (schema v4).')
    return Boolean(data) && !error
  }

  async function setCls(classificazione: Classificazione) {
    if (!p) return
    const enriched = { ...(p.enriched ?? {}), classificazione: 'manual' as const }
    await aggiorna({ classificazione, enriched } as Partial<Prospect>)
  }

  async function segna(kind: Interaction['kind'], body: string): Promise<boolean> {
    const { data, error } = await supabase.from('interactions')
      .insert({ prospect_id: id, at: new Date().toISOString(), kind, body })
      .select().single()
    if (data) setTimeline((t) => [...(t ?? []), data as Interaction])
    if (error) setErrore('Salvataggio non riuscito: il database non è aggiornato (schema v4).')
    return Boolean(data) && !error
  }

  // SALVARE il transcript e' un gesto suo: si puo' incollare senza avanzare
  async function salvaTranscript() {
    if (!p || !p.pipeline_stage || !transcript.trim()) return
    const testo = transcript.trim()
    const salvato = await segna('transcript', `${marcaFase(p.pipeline_stage)} ${testo}`)
    if (!salvato) return
    setGiro((n) => n + 1)
    // il premio: cosa mi porto via, subito
    const parole = testo.split(/\s+/).length
    const SEGNALI: Array<[string, string]> = [
      ['budget', 'budget'], ['prezzo', 'prezzo'], ['costo', 'costi'],
      ['preventivo', 'preventivo'], ['sito', 'sito'], ['campagn', 'campagne'],
      ['google', 'Google'], ['concorren', 'concorrenti'], ['urgen', 'urgenza'],
      ['settembre', 'settembre'], ['ottobre', 'ottobre'], ['novembre', 'novembre'],
      ['carlo', 'Carlo'],
    ]
    const trovati = SEGNALI
      .filter(([k]) => testo.toLowerCase().includes(k))
      .map(([, parola]) => parola)
      .slice(0, 4)
    const righe = [`${fmtNum(parole)} parole archiviate in «Call fatte»`]
    if (trovati.length) righe.push(`Ho notato: ${trovati.join(', ')}`)
    setPremio(righe)
    setTranscript('')
  }

  // AVANZARE e' l'altro gesto: possibile solo se il transcript della fase c'e'
  async function portaAvanti() {
    if (!p || !p.pipeline_stage) return
    const next = PIPELINE_NEXT[p.pipeline_stage]
    if (!next) return
    if (await aggiorna({ pipeline_stage: next, next_action: null, next_action_date: null })) {
      await segna('nota', next === 'cliente' ? 'È DIVENTATO CLIENTE.' : `Avanzata a ${PIPELINE_LABEL[next]}`)
      setAvanzataA(next)
    }
  }

  // segna come perso: il motivo è obbligatorio e resta nella storia
  async function segnaPerso() {
    const perche = motivoPerso.trim()
    if (!p || !perche) return
    const patch = p.fuori
      ? { pipeline_stage: 'perso' as PipelineStage, lost_reason: perche, next_action: null, next_action_date: null }
      : { stage: 'perso' as Stage, lost_reason: perche, next_action: null, next_action_date: null }
    if (!(await aggiorna(patch))) return
    await segna('nota', `Segnato come perso: ${perche}`)
    setPersoAperto(false)
    setMotivoPerso('')
  }

  async function addNota() {
    if (!nota.trim() || !p) return
    await segna('nota', nota.trim())
    setNota('')
  }

  async function rispondiCancello(risposta: 'si' | 'no') {
    const poi = cancello
    setCancello(null)
    await aggiorna({ fuori_binario: risposta })
    await segna('nota', risposta === 'si'
      ? 'Fuori binario: SÌ, già sentito fuori dai sistemi.'
      : 'Fuori binario: no, mai sentito prima.')
    setBinarioSegnato(true)
    setTimeout(() => setBinarioSegnato(false), 6000)
    if (risposta === 'si') appuntiRef.current?.focus()
    else poi?.()
  }

  async function chiediPrep() {
    await supabase.from('clara_messaggi').insert({
      tipo: 'dre', letto: true, prospect_id: p!.id,
      testo: `Prepara la pre-call di ${p!.company || p!.name}${prossimaCall ? ` (call del ${fmtDateShort(prossimaCall.at)} alle ${fmtOra(prossimaCall.at)})` : ''}`,
    }).select().single()
    setPrepChiesta(true)
  }

  async function allegaDocumento(f: File) {
    const path = `${Date.now()}-${f.name.replace(/[^a-zA-Z0-9._-]/g, '_')}`
    const { error } = await supabase.storage.from('vault').upload(path, f)
    if (error) {
      setNotaEsito('Caricamento non riuscito: serve schema_v4 su Supabase')
      return
    }
    const nome = f.name.replace(/\.[^.]+$/, '')
    await supabase.from('vault_file')
      .insert({ nome, path, mime: f.type || null, dimensione: f.size, prospect_id: p!.id })
      .select().single()
    await segna('nota', `📎 ${f.name} · nel Vault`)
    setNotaEsito(`«${nome}» nel Vault, agganciato a ${p!.company || p!.name} ✓`)
    setTimeout(() => { setNotaEsito(null); setNoteAperte(false) }, 2200)
  }

  if (!p) return (
    <div className="fixed inset-0 z-50 bg-fondo">
      <div className="flex items-center gap-3 border-b border-bordo bg-white px-4 py-2">
        <button onClick={onClose} className="text-sm font-semibold text-tenue hover:text-inchiostro">← Indietro</button>
      </div>
      <Spinner />
    </div>
  )

  const fermo = daysAgo(p.last_reply_at)
  const next = p.pipeline_stage ? PIPELINE_NEXT[p.pipeline_stage] : undefined
  const transcripts = (timeline ?? []).filter((t) => t.kind === 'transcript')
  const transcriptCorrente = pagato
  const postit = (timeline ?? []).filter((t) => t.kind === 'postit')
  const prep = [...(timeline ?? [])].reverse().find((t) => t.kind === 'prep')
  const storia = [...(timeline ?? [])]
    .filter((t) => t.kind !== 'transcript' && t.kind !== 'postit' && t.kind !== 'prep')
    .reverse()
  const primaRisposta = (timeline ?? []).find((t) => t.kind === 'email_in')
  const mercato = p.market ?? mercatoDi(p.sector, p.city)
  const soppresso = p.classificazione === 'soppresso'
  const tappa = tappaCorrente(p)
  const codice = sgid(p.sg_id)
  const val = (k: keyof Prospect) =>
    (draft[k] !== undefined ? draft[k] : p[k]) as string | number | null

  // «fermo da X»: verde <3, ambra 3-5, rosso >5 (il ritmo del follow-up)
  const tonoFermo = fermo === null ? '' : fermo < 3 ? 'text-green-700' : fermo <= 5 ? 'text-amber-700' : 'text-red-700'

  function fraQuanto(at: string): string {
    const ms = new Date(at).getTime() - Date.now()
    const ore = Math.round(ms / 3600e3)
    if (ore <= 1) return 'fra meno di un\'ora'
    if (ore < 24) return `fra ${ore} ore`
    const gg2 = Math.round(ms / 86400e3)
    return gg2 === 1 ? 'domani' : `fra ${gg2} giorni`
  }

  // ── la frase del presente («Adesso») ─────────────────────────────
  function adesso(): string {
    if (soppresso) return 'Soppresso: mai ricontattare. Il blocco è nei dati.'
    if (ePerso(p!)) return `Perso${p!.lost_reason ? `: ${p!.lost_reason}` : '. Nessun motivo scritto.'}`
    if (p!.pipeline_stage === 'cliente') {
      return p!.contratto === 'stable'
        ? `Cliente stabile${p!.canone ? `, ${fmtNum(Number(p!.canone))} € al mese` : ''}.`
        : p!.contratto === 'prova' ? 'Cliente in periodo di prova (1.500 € × 2 mesi).' : 'Cliente: contratto da definire qui sotto.'
    }
    if (p!.awaiting_us) return `Ha scritto lui per ultimo (${fmtDateShort(p!.last_reply_at)}): aspetta la tua risposta.`
    if (p!.fuori && next) {
      if (p!.next_action_date && p!.next_action_date >= oggi())
        return `In ${PIPELINE_LABEL[p!.pipeline_stage!]}: ${p!.next_action ?? 'prossimo passo'} il ${fmtDateShort(p!.next_action_date)}.`
      return `In ${PIPELINE_LABEL[p!.pipeline_stage!]}: la call è da fare o è fatta, col riassunto si avanza.`
    }
    if (p!.analysis_sent && fermo !== null && fermo >= 5)
      return `Ha ricevuto l'analisi il ${fmtDateShort(p!.analysis_sent_at)}, silenzio da ${giorni(fermo)}: tocca il follow-up.`
    if (p!.analysis_sent) return `Ha ricevuto l'analisi il ${fmtDateShort(p!.analysis_sent_at)}: si aspetta la sua mossa.`
    if (primaRisposta) return `Ha risposto il ${fmtDateShort(primaRisposta.at)}: l'analisi è il prossimo dono.`
    return 'In lista, nessuna conversazione ancora.'
  }

  // ── la nota personale: un post-it che resta attaccato alla scheda ─
  async function salvaNota() {
    const t = notaTesto.trim()
    if (!t) return
    await segna('postit', notaData ? `${t} · ricordamelo il ${fmtDateShort(notaData)}` : t)
    if (notaData) {
      await supabase.from('task_dre').insert({
        titolo: `${t.slice(0, 60)} · ${p!.company || p!.name}`,
        scadenza: notaData, fatta: false, ordine: -1,
      }).select().single()
    }
    if (notaClara) {
      await supabase.from('clara_messaggi').insert({
        tipo: 'dre', letto: true, prospect_id: p!.id,
        testo: `[Nota su ${p!.company || p!.name}] ${t}${notaData ? `; ricordamelo il ${fmtDateShort(notaData)}` : ''}`,
      }).select().single()
    }
    setNotaEsito(`Post-it attaccato ✓${notaData ? ' · promemoria in Task' : ''}${notaClara ? ' · girata a Clara' : ''}`)
    setNotaTesto('')
    setNotaData('')
    setNotaClara(false)
    setTimeout(() => { setNotaEsito(null); setNoteAperte(false) }, 2200)
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-fondo">
      {/* barra alta */}
      <div className="sticky top-0 z-10 flex items-center gap-3 border-b border-bordo bg-white px-4 py-2">
        <button onClick={chiudi} className="text-sm font-semibold text-tenue hover:text-inchiostro">
          ← Indietro
        </button>
        <p className="min-w-0 flex-1 truncate text-center text-sm font-bold">
          {p.company || p.name || p.email}
        </p>
        <button
          onClick={save}
          disabled={!dirty || saving}
          className={`rounded-full px-4 py-1.5 text-sm font-semibold ${
            dirty ? 'bg-navy text-white hover:bg-navy-scuro' : 'text-bordo'
          }`}
        >
          {saving ? 'Salvo…' : saved ? 'Salvato ✓' : 'Salva'}
        </button>
      </div>

      {/* IL CANCELLO: domanda al primo gesto di scrittura */}
      {cancello && (
        <div className="fixed inset-0 z-30 flex items-center justify-center bg-inchiostro/30 px-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <p className="text-base font-bold">L'hai già sentito tu, fuori dai sistemi?</p>
            <p className="mt-1 text-sm text-tenue">Telefono, WhatsApp, di persona.</p>
            <div className="mt-4 flex gap-2">
              <button
                onClick={() => rispondiCancello('si')}
                className="flex-1 rounded-full border border-bordo py-2 text-sm font-bold hover:border-spento"
              >
                Sì, l'ho sentito
              </button>
              <button
                onClick={() => rispondiCancello('no')}
                className="flex-1 rounded-full bg-navy py-2 text-sm font-bold text-white hover:bg-navy-scuro"
              >
                No, mai
              </button>
            </div>
          </div>
        </div>
      )}

      {errore && (
        <div className="mx-auto mt-3 max-w-5xl px-4">
          <p className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900">{errore}</p>
        </div>
      )}

      {/* dopo l'avanzamento: conferma, e per il CLIENTE l'onore che merita */}
      {avanzataA && (
        <div className="mx-auto mt-3 max-w-5xl px-4">
          {avanzataA === 'cliente' ? (
            <div className="rounded-2xl bg-navy px-5 py-4 text-white shadow-[0_8px_24px_rgba(6,23,115,0.3)]">
              <p className="text-lg font-extrabold">
                🏆 Nuovo cliente · {p.company || p.name} {codice && <span className="font-semibold text-white/70">{codice}</span>}
              </p>
              <p className="mt-0.5 text-sm text-white/80">
                Da prospect a cliente: è l'obiettivo del gioco. L'ID resta lo stesso, cambia la relazione.
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-3">
              <span className="text-sm text-white/80">Il contratto:</span>
              {(['prova', 'stable'] as const).map((c) => (
                <button
                  key={c}
                  onClick={async () => {
                    await aggiorna({ contratto: c, canone: c === 'prova' ? 1500 : 1400 })
                    setAvanzataA(null)
                  }}
                  className="rounded-full border border-white/40 px-4 py-1.5 text-sm font-bold hover:bg-white/10"
                >
                  {c === 'prova' ? 'Prova · 1.500 € × 2' : 'Stable · 1.400 €/mese'}
                </button>
              ))}
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-green-300 bg-green-50 px-4 py-3">
              <p className="text-sm font-bold text-green-800">Avanzata a {PIPELINE_LABEL[avanzataA]} ✓</p>
              <div className="mt-2 flex flex-wrap items-center gap-3">
              <span className="text-sm text-green-900">Prossima call?</span>
              <input
                type="date"
                value={dataPasso}
                onChange={(e) => setDataPasso(e.target.value)}
                className="rounded-lg border border-bordo bg-white px-2 py-1 text-sm outline-none focus:border-blu"
              />
              <button
                onClick={async () => {
                  if (dataPasso) await aggiorna({ next_action: `Call ${PIPELINE_LABEL[avanzataA].toLowerCase()}`, next_action_date: dataPasso })
                  setAvanzataA(null); setDataPasso('')
                }}
                disabled={!dataPasso}
                className="rounded-full bg-navy px-3.5 py-1 text-xs font-bold text-white disabled:opacity-30"
              >
                Segna
              </button>
              <button onClick={() => { setAvanzataA(null); setDataPasso('') }} className="text-xs font-semibold text-tenue hover:text-inchiostro">
                Dopo
              </button>
              </div>
            </div>
          )}
        </div>
      )}

      <ZonaFile
        onFile={(f) => { setNoteAperte(true); allegaDocumento(f) }}
        messaggio={`Lascia qui: nel Vault, agganciato a ${p.company || p.name}`}
        className="mx-auto max-w-5xl space-y-3 px-4 py-4 pb-16"
      >

        {binarioSegnato && (
          <p className="rounded-xl border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-800">
            Segnato ✓ · non te lo chiedo più per questa scheda.
          </p>
        )}

        {soppresso && (
          <p className="rounded-xl border border-red-300 bg-red-50 px-4 py-2.5 text-sm font-bold text-red-800">
            SOPPRESSO: mai ricontattare. Il blocco è nei dati, nessuna campagna lo aggira.
          </p>
        )}

        {/* ── testata: chi e', dove siamo, cosa fare ───────────── */}
        <Card className="p-5">
          <div className="flex flex-wrap items-start gap-4">
            <Faccia p={p} size={44} />
            <div className="min-w-0 flex-1">
              <p className="flex items-center gap-2 text-[11px] font-bold tracking-wide text-blu">
                {codice ?? '—'}
                {eCliente(p)
                  ? <span className="rounded-full bg-green-50 px-2.5 py-0.5 font-semibold text-green-800">CLIENTE</span>
                  : ePerso(p)
                  ? <span className="rounded-full bg-gray-100 px-2.5 py-0.5 font-semibold text-gray-500">PERSO</span>
                  : <span className="rounded-full bg-amber-50 px-2.5 py-0.5 font-semibold text-amber-700">PROSPECT</span>}
                {p.fuori_binario === 'si' && (
                  <span className="rounded-full bg-amber-50 px-2.5 py-0.5 font-semibold text-amber-800" title="già sentito fuori dai sistemi">
                    sentito a voce
                  </span>
                )}
              </p>
              <h2 className="mt-0.5 truncate text-lg font-extrabold">{p.company || p.name || p.email}</h2>
              <p className="mt-0.5 text-sm text-tenue">{adesso()}</p>
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-2">
              {!ePerso(p) && !soppresso && (
                <button
                  onClick={() => { setPersoAperto(true); setMotivoPerso('') }}
                  className="rounded-full border border-bordo px-3.5 py-2.5 text-sm font-semibold text-tenue transition-colors hover:border-red-300 hover:text-red-700"
                >
                  Segna come perso
                </button>
              )}
              <button
                onClick={() => { setNoteAperte(!noteAperte); setNotaEsito(null) }}
                className={`rounded-full border px-4 py-2.5 text-sm font-bold transition-colors ${
                  noteAperte ? 'border-navy bg-navy text-white' : 'border-bordo text-tenue hover:border-navy hover:text-navy'
                }`}
              >
                ✎ Note e documenti
              </button>
            </div>
          </div>

          {persoAperto && (
            <div className="salta-su mt-3 rounded-xl border border-red-200 bg-red-50/60 p-3">
              <textarea
                autoFocus
                rows={2}
                value={motivoPerso}
                onChange={(e) => setMotivoPerso(e.target.value)}
                placeholder="Perché è saltata? (prezzo, tempi, ha scelto un altro…)"
                className="w-full resize-none rounded-lg border border-bordo bg-white px-3 py-2 text-sm outline-none focus:border-red-400"
              />
              <div className="mt-2 flex justify-end gap-2">
                <button
                  onClick={() => { setPersoAperto(false); setMotivoPerso('') }}
                  className="rounded-full border border-bordo bg-white px-3.5 py-1.5 text-xs font-semibold text-tenue"
                >
                  Annulla
                </button>
                <button
                  onClick={segnaPerso}
                  disabled={!motivoPerso.trim()}
                  className="rounded-full bg-red-700 px-4 py-1.5 text-xs font-bold text-white hover:bg-red-800 disabled:opacity-30"
                >
                  Segna come perso
                </button>
              </div>
            </div>
          )}

          {noteAperte && (
            <div className="salta-su mt-3 space-y-2 rounded-xl bg-velo/50 p-3">
              {notaEsito ? (
                <p className="text-sm font-bold text-green-700">{notaEsito}</p>
              ) : (
                <>
                  <textarea
                    autoFocus
                    rows={2}
                    value={notaTesto}
                    onChange={(e) => setNotaTesto(e.target.value)}
                    placeholder="Scrivi la nota…"
                    className="w-full resize-none rounded-lg border border-bordo bg-white px-3 py-2 text-sm outline-none focus:border-blu"
                  />
                  <div className="flex flex-wrap items-center gap-3">
                    <label className="flex items-center gap-1.5 text-xs text-tenue">
                      Ricordamelo il
                      <input
                        type="date"
                        value={notaData}
                        onChange={(e) => setNotaData(e.target.value)}
                        className="rounded-full border border-bordo bg-white px-2 py-0.5 text-xs outline-none focus:border-blu"
                      />
                    </label>
                    <label className="flex cursor-pointer items-center gap-1.5 text-xs font-semibold text-tenue">
                      <input
                        type="checkbox"
                        checked={notaClara}
                        onChange={(e) => setNotaClara(e.target.checked)}
                        className="h-4 w-4 accent-[#061773]"
                      />
                      Condividi con Clara
                    </label>
                    <button
                      onClick={() => docRef.current?.click()}
                      className="rounded-full border border-bordo bg-white px-3.5 py-1.5 text-xs font-bold text-navy hover:border-navy"
                    >
                      📎 Allega documento
                    </button>
                    <input
                      ref={docRef}
                      type="file"
                      className="hidden"
                      onChange={(e) => { const f = e.target.files?.[0]; if (f) allegaDocumento(f); e.target.value = '' }}
                    />
                    <div className="ml-auto flex gap-2">
                      <button onClick={() => setNoteAperte(false)} className="rounded-full border border-bordo px-3.5 py-1.5 text-xs font-semibold text-tenue">
                        Annulla
                      </button>
                      <button
                        onClick={salvaNota}
                        disabled={!notaTesto.trim()}
                        className="rounded-full bg-navy px-4 py-1.5 text-xs font-bold text-white disabled:opacity-30"
                      >
                        Salva
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* lo stepper delle fasi */}
          <div className="mt-4 flex items-center gap-1 overflow-x-auto pb-1">
            {TAPPE.map((t, i) => (
              <div key={t} className="flex shrink-0 items-center gap-1">
                {i > 0 && <span className={`h-px w-4 ${i <= tappa ? 'bg-navy' : 'bg-bordo'}`} />}
                <span className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                  i === tappa ? 'bg-navy text-white'
                  : i < tappa ? 'text-navy'
                  : 'text-spento'
                }`}>
                  <span className={`h-1.5 w-1.5 rounded-full ${i <= tappa ? 'bg-current' : 'bg-bordo'}`} />
                  {t}
                </span>
              </div>
            ))}
            {fermo !== null && p.pipeline_stage !== 'cliente' && !soppresso && (
              <span className={`ml-auto shrink-0 pl-3 text-xs font-bold ${tonoFermo}`}>
                fermo da {giorni(fermo)}
              </span>
            )}
          </div>
        </Card>

        {/* la prossima call: quando c'è, sta sopra a tutto */}
        {prossimaCall && (
          <Card className="border-l-4 border-l-navy">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3.5">
              <div className="min-w-0 flex-1">
                <p className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
                  <span className={`text-[15px] font-extrabold ${
                    new Date(prossimaCall.at).getTime() - Date.now() < 26 * 3600e3 ? 'text-amber-700' : ''
                  }`}>
                    {fraQuanto(prossimaCall.at)}
                  </span>
                  <span className="min-w-0 truncate text-sm font-semibold">{prossimaCall.titolo}</span>
                </p>
                <p className="text-xs text-spento">
                  {fmtDate(prossimaCall.at)} · {fmtOra(prossimaCall.at)}
                </p>
              </div>
              <div className="flex shrink-0 gap-2">
                {prossimaCall.link && (
                  <a
                    href={prossimaCall.link}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-full border border-bordo px-4 py-2 text-xs font-bold text-blu hover:border-blu"
                  >
                    Apri l'evento ↗
                  </a>
                )}
                <button
                  onClick={() => setPrepAperta(!prepAperta)}
                  className={`rounded-full px-4 py-2 text-xs font-bold transition-colors ${
                    prepAperta ? 'bg-navy text-white' : prep ? 'bg-navy text-white' : 'border border-navy text-navy hover:bg-navy/5'
                  }`}
                >
                  Preparazione pre-call
                </button>
              </div>
            </div>
            {prepAperta && (
              <div className="salta-su border-t border-velo px-5 py-4">
                {prep ? (
                  <p className="whitespace-pre-wrap text-sm leading-relaxed">{prep.body}</p>
                ) : prepChiesta ? (
                  <p className="text-sm font-semibold text-green-700">
                    Chiesta a Clara ✓: la troverai qui.
                  </p>
                ) : (
                  <div className="flex flex-wrap items-center gap-3">
                    <p className="text-sm text-tenue">La prep non è ancora pronta.</p>
                    <button
                      onClick={chiediPrep}
                      className="rounded-full bg-navy px-4 py-1.5 text-xs font-bold text-white hover:bg-navy-scuro"
                    >
                      Chiedila a Clara
                    </button>
                  </div>
                )}
              </div>
            )}
          </Card>
        )}

        {/* i post-it: restano attaccati qui finché non li togli */}
        {postit.length > 0 && (
          <div className="flex flex-wrap gap-2.5">
            {postit.map((t, i) => (
              <div
                key={t.id}
                className={`salta-su relative max-w-64 rounded-md bg-amber-100 px-3.5 py-2.5 shadow-[0_3px_10px_rgba(140,100,0,0.18)] ${
                  i % 2 === 0 ? '-rotate-1' : 'rotate-1'
                }`}
              >
                <p className="whitespace-pre-wrap text-sm leading-snug text-amber-950">{t.body}</p>
                <p className="mt-1 text-[10px] text-amber-700/70">{fmtDateShort(t.at)}</p>
                <button
                  onClick={async () => {
                    const { data } = await supabase.from('interactions')
                      .update({ kind: 'nota' }).eq('id', t.id).select().single()
                    if (data) setTimeline((tl) => tl!.map((x) => (x.id === t.id ? (data as Interaction) : x)))
                  }}
                  title="Togli il post-it (resta nella storia)"
                  className="absolute -right-1.5 -top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-amber-950/80 text-[10px] font-bold text-white hover:bg-amber-950"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        {/* ── due colonne: identita' | il vivo ─────────────────── */}
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-[250px_1fr]">

          {/* SX: l'identita' */}
          <div className="space-y-3">
            <Card className="p-4">
              <div className="flex items-baseline justify-between">
                <TitoloCard>Contatti</TitoloCard>
                <button onClick={() => setModifica(!modifica)} className="text-[11px] font-semibold text-blu hover:underline">
                  {modifica ? 'chiudi' : 'modifica'}
                </button>
              </div>
              {modifica ? (
                <div className="space-y-2">
                  {CAMPI.map(({ key, label, type }) => (
                    <label key={key} className="block">
                      <span className="mb-0.5 flex items-center gap-1 text-[11px] text-tenue">
                        {label}
                        {p.enriched?.[key] === 'auto' && <Auto />}
                      </span>
                      <input
                        type={type ?? 'text'}
                        value={val(key) == null ? '' : String(val(key))}
                        onChange={(e) => edit(key, e.target.value)}
                        className="w-full rounded-lg border border-bordo px-2 py-1.5 text-sm outline-none focus:border-blu"
                      />
                    </label>
                  ))}
                </div>
              ) : (
                <div className="space-y-1.5 text-sm">
                  <a href={`mailto:${p.email}`} className="block truncate text-blu hover:underline">{p.email}</a>
                  {p.phone
                    ? <a href={`tel:${p.phone}`} className="block text-blu hover:underline">{p.phone}</a>
                    : <p className="text-spento">Telefono: non trovato</p>}
                  {p.website && (
                    <a href={p.website.startsWith('http') ? p.website : `https://${p.website}`}
                       target="_blank" rel="noreferrer" className="block truncate text-blu hover:underline">
                      {p.website.replace(/^https?:\/\//, '')}
                    </a>
                  )}
                  {p.linkedin
                    ? <a href={p.linkedin} target="_blank" rel="noreferrer" className="block truncate text-blu hover:underline">LinkedIn</a>
                    : <p className="text-spento">Nessun LinkedIn</p>}
                  {p.city && <p>{p.city}</p>}
                  {p.campaign && <p className="text-xs text-spento">campagna: {p.campaign}</p>}
                </div>
              )}
            </Card>

            {p.descrizione && !modifica && (
              <Card className="p-4">
                <div className="flex items-baseline justify-between">
                  <TitoloCard>Chi sono</TitoloCard>
                  {p.enriched?.descrizione === 'auto' && <Auto />}
                </div>
                <p className="text-sm leading-relaxed">{p.descrizione}</p>
              </Card>
            )}

            {/* il mercato, compresso nel verdetto */}
            {mercato && (
              <Card>
                <details>
                  <summary className="cursor-pointer list-none p-4 hover:bg-velo/40">
                    <span className="flex items-center justify-between">
                      <TitoloCard>Il suo mercato</TitoloCard>
                      <span className="text-sm text-spento">›</span>
                    </span>
                    <span className="text-sm font-semibold">
                      Vale la pena: <span className={mercato.fit === 'si' ? 'text-green-700' : 'text-red-700'}>{mercato.fit === 'si' ? 'Sì' : 'No'}</span>
                      <span className="font-normal text-tenue"> · {fmtNum(mercato.ricerche)}/mese · CPC {mercato.cpc.toLocaleString('it-IT', { minimumFractionDigits: 2 })} €</span>
                    </span>
                  </summary>
                  <div className="space-y-3 border-t border-velo p-4">
                    <SeasonChart bars={mercato.bars} />
                    <div className="flex justify-between text-sm">
                      <span className="text-tenue">Mesi vivi</span>
                      <span className="font-bold">{mercato.mesi_vivi} su 12</span>
                    </div>
                    <p className="text-[11px] text-spento">{mercato.zona} · misurato il {fmtDate(mercato.misurato_il)}</p>
                  </div>
                </details>
              </Card>
            )}

            {/* classificazione: ripiegata, non 16 chip in faccia */}
            {!p.fuori && !soppresso && (
              <Card>
                <details>
                  <summary className="cursor-pointer list-none p-4 hover:bg-velo/40">
                    <span className="flex items-center justify-between">
                      <TitoloCard>Classificazione</TitoloCard>
                      <span className="text-sm text-spento">›</span>
                    </span>
                    <span className="text-sm font-semibold">
                      {p.classificazione ? CLS_LABEL[p.classificazione] : '—'}
                      <span className="font-normal text-tenue"> · {STAGE_LABEL[p.stage]}</span>
                    </span>
                  </summary>
                  <div className="space-y-3 border-t border-velo p-4">
                    <div className="flex flex-wrap gap-1">
                      {CLASSIFICAZIONI.map((c) => (
                        <button
                          key={c}
                          onClick={() => setCls(c)}
                          className={`rounded-full px-3 py-1 text-[11px] font-semibold ${
                            p.classificazione === c ? 'bg-navy text-white' : 'border border-bordo bg-white text-tenue hover:border-spento'
                          }`}
                        >
                          {CLS_LABEL[c]}
                        </button>
                      ))}
                    </div>
                    {p.enriched?.classificazione === 'manual' && (
                      <p className="text-[11px] text-spento">corretta a mano: il sync non la tocca più</p>
                    )}
                    <div className="flex flex-wrap gap-1">
                      {STAGES.filter((s) => s !== 'cliente' && s !== 'perso').map((s) => (
                        <button
                          key={s}
                          onClick={() => aggiorna({ stage: s as Stage })}
                          className={`rounded-full px-3 py-1 text-[11px] font-semibold ${
                            p.stage === s ? 'bg-navy text-white' : 'border border-bordo bg-white text-tenue hover:border-spento'
                          }`}
                        >
                          {STAGE_LABEL[s]}
                        </button>
                      ))}
                    </div>
                  </div>
                </details>
              </Card>
            )}

            {p.pipeline_stage === 'cliente' && (
              <Card className="p-4">
                <TitoloCard>Contratto</TitoloCard>
                <div className="flex flex-wrap gap-1">
                  {(['prova', 'stable'] as const).map((c) => (
                    <button
                      key={c}
                      onClick={() => aggiorna({ contratto: c, canone: c === 'prova' ? 1500 : 1400 })}
                      className={`rounded-full px-3 py-1 text-[11px] font-semibold ${
                        p.contratto === c ? 'bg-navy text-white' : 'border border-bordo bg-white text-tenue hover:border-spento'
                      }`}
                    >
                      {c === 'prova' ? 'Prova · 1.500 € × 2' : 'Stable · 1.400 €/mese'}
                    </button>
                  ))}
                </div>
              </Card>
            )}
          </div>

          {/* CENTRO: il vivo */}
          <div className="space-y-3">

            {/* il pedaggio, quando serve */}
            {p.fuori && next && !soppresso && (
              <Card className="border-amber-200">
                <header className="flex flex-wrap items-baseline gap-2 border-b border-velo bg-amber-50/60 px-4 py-2.5">
                  <h3 className="text-xs font-bold">Riassunto di fase</h3>

                </header>
                <div className="p-4">
                  <textarea
                    ref={transcriptRef}
                    value={transcript}
                    onChange={(e) => setTranscript(e.target.value)}
                    placeholder="Incolla il transcript di Granola o scrivi il riassunto e i prossimi passi"
                    className="min-h-24 w-full rounded-lg border border-bordo px-3 py-2 text-sm outline-none focus:border-blu"
                  />
                  {premio.length > 0 && (
                    <div className="salta-su mt-2 rounded-xl border border-green-200 bg-green-50 px-3 py-2">
                      <p className="text-xs font-bold text-green-800">Riassunto salvato ✓</p>
                      {premio.map((r, i) => (
                        <p key={i} className="text-xs text-green-900">{r}</p>
                      ))}
                    </div>
                  )}
                  <div className="mt-2 flex flex-wrap items-center gap-2.5">
                    <button
                      onClick={salvaTranscript}
                      disabled={!transcript.trim()}
                      className="rounded-full border border-navy px-5 py-2 text-sm font-bold text-navy hover:bg-navy/5 disabled:cursor-not-allowed disabled:opacity-30"
                    >
                      Salva il riassunto
                    </button>
                    <button
                      onClick={portaAvanti}
                      disabled={!transcriptCorrente}
                      title={transcriptCorrente ? undefined : 'Prima il riassunto: senza non si avanza'}
                      className="rounded-full bg-navy px-5 py-2 text-sm font-bold text-white hover:bg-navy-scuro disabled:cursor-not-allowed disabled:opacity-30"
                    >
                      Porta avanti → {PIPELINE_LABEL[next]}
                    </button>
                  </div>
                </div>
              </Card>
            )}

            <Card className="p-4">
              <TitoloCard>Cosa è successo</TitoloCard>
              {timeline === null ? (
                <Spinner />
              ) : storia.length === 0 ? (
                <p className="text-sm text-spento">Nessun evento ancora.</p>
              ) : (
                <ul className="divide-y divide-velo">
                  {storia.map((t) => (
                    <li key={t.id} className="grid grid-cols-[52px_1fr] gap-2.5 py-1.5 text-sm">
                      <span className="pt-px text-[11px] text-spento">{fmtDate(t.at)}</span>
                      <span>
                        <span className={`font-semibold ${t.kind === 'email_in' ? 'text-green-700' : ''}`}>
                          {KIND_LABEL[t.kind] ?? t.kind}
                        </span>
                        {t.id === primaRisposta?.id && (
                          <span className="ml-1.5 rounded-full bg-green-50 px-2 py-px text-[10px] font-semibold text-green-800">
                            diventa prospect
                          </span>
                        )}
                        {t.body && <span className="block whitespace-pre-wrap text-tenue">{t.body}</span>}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              <div className="mt-3 flex gap-2">
                <input
                  value={nota}
                  onChange={(e) => setNota(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && addNota()}
                  placeholder="Aggiungi una nota…"
                  className="flex-1 rounded-lg border border-bordo px-3 py-1.5 text-sm outline-none focus:border-blu"
                />
                <button onClick={addNota} className="rounded-full bg-navy px-3.5 py-1.5 text-sm font-semibold text-white hover:bg-navy-scuro">+</button>
              </div>
            </Card>

            {transcripts.length > 0 && (
              <Card className="p-4">
                <TitoloCard>Call fatte</TitoloCard>
                <ul className="space-y-2">
                  {[...transcripts].reverse().map((t) => (
                    <li key={t.id} className="text-sm">
                      <span className="text-[11px] text-spento">{fmtDate(t.at)}</span>
                      <details>
                        <summary className="cursor-pointer font-semibold text-blu">{(t.body ?? '').slice(0, 70)}…</summary>
                        <p className="mt-1 whitespace-pre-wrap text-tenue">{t.body}</p>
                      </details>
                    </li>
                  ))}
                </ul>
              </Card>
            )}

            <Card className="bg-velo/40 p-4">
              <TitoloCard>Contatti fuori binario</TitoloCard>
              <textarea
                ref={appuntiRef}
                rows={3}
                value={val('notes') == null ? '' : String(val('notes'))}
                onChange={(e) => edit('notes', e.target.value)}
                onBlur={() => { if (draft.notes !== undefined) save() }}
                placeholder="Telefonate, incontri, cose dette a voce, motivi per cui NON scrivergli…"
                className="w-full rounded-lg border border-bordo bg-white px-3 py-2 text-sm outline-none focus:border-blu"
              />
              {saved && <p className="mt-1 text-[11px] font-semibold text-green-700">Salvato ✓</p>}
            </Card>

            {(p.followup_due || p.ooo_until || p.no_followup) && (
              <Card className="space-y-1 p-4 text-xs text-tenue">
                {p.followup_due && <p>Follow-up dovuto il {fmtDate(p.followup_due)}</p>}
                {p.ooo_until && <p>Fuori ufficio fino al {fmtDate(p.ooo_until)}</p>}
                {p.no_followup && <p className="font-semibold text-amber-700">Ricontatta lui: niente follow-up automatici</p>}
              </Card>
            )}
          </div>
        </div>
      </ZonaFile>
    </div>
  )
}
