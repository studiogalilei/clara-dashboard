import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { supabase } from '../lib/supabase'
import { sonoCeo } from '../lib/accessi'
import {
  PIPELINE_LABEL,
  type Prospect, type Interaction, type AgendaItem, type PipelineStage,
} from '../lib/types'
import { eCliente, ePerso } from '../lib/regole'
import { apriFile, caricaFile } from '../lib/file'
import { linkDi } from '../lib/indirizzo'
import { apriFascicolo } from '../lib/fascicolo'
import { azzeraCanone } from '../lib/soldi'
import Copia from './Copia'
import Scheda from './Scheda'
import { StoriaCompleta } from './Storia'
import { Card, Micro, Spinner, ZonaFile, Faccia, fmtDateShort, fmtOra, sgid } from './ui'

// IL VAULT DEL CLIENTE (Dre, a voce, 6/10; ridisegnato il 7/10 dalla bozza C).
// La v1 erano quattro fisarmoniche chiuse e Dre l'ha bocciata: «quella di prima
// sembrava di piu' un vault cliente; Marco non e' navigabile; vorrei che alcune
// info si vedessero gia' a vista». Fra tre strade disegnate sul canvas ha scelto
// «il filo del rapporto»: una testata col referente gia' contattabile, a sinistra
// le cose ferme (referenti, preventivi, documenti), a destra «Adesso» e il filo
// delle tappe vere, dalla piu' recente. Niente e' chiuso: il clic serve per
// aggiungere o andare piu' a fondo, mai per scoprire cosa c'e'.

interface Props {
  id: string
  sezione?: string | null
  onSezione?: (s: string | null) => void
  onClose: () => void
  onApri?: (id: string) => void
}

interface Referente {
  id: number               // 0 = il referente principale, che vive nelle colonne di prospects
  nome: string; ruolo: string | null; email: string | null; telefono: string | null
  linkedin: string | null; decide: string | null; nota: string | null
}
interface Prev {
  id: number; numero: string | null; titolo: string | null; importo: number | null; mensile: number | null; stato: string
  pagato_il: string | null; inviato_il: string | null; accettato_il: string | null; rifiutato_il: string | null; pdf_path: string | null
}
interface Doc { id: number; nome: string; path: string; at: string }

// una chiamata del Vault: l'evento in agenda sposato col suo riassunto
interface Chiamata { chiave: string; at: string; titolo: string; riassunto: string | null; link: string | null }

// in agenda ci sono anche promemoria che non sono call (budget, rinnovi, invii)
const NON_CALL = new Set(['budget', 'rinnovo', 'invio', 'scadenza', 'promemoria'])
const PAROLE_CALL = /call|chiamata|conoscitiva|tecnica|avvio|meet|incontro|riunione|studio galilei/i
const FINESTRA = 36 * 3600e3            // Gemini e Granola arrivano col loro tempo
const LUNGO = 2500                      // oltre, e' una trascrizione grezza, non un riassunto

// il riassunto di Gemini arriva nel body del transcript, con il link agli
// appunti interi in fondo (scripts/appunti.py). Qui si separano le due cose.
function spezzaTranscript(body: string): { riassunto: string; link: string | null } {
  const link = /https:\/\/(?:docs|drive)\.google\.com\/\S+/.exec(body)?.[0] ?? null
  const riassunto = body
    .replace(/^\[.+?\]\s*/, '')                       // la marca di fase
    .replace(/^\[granola:[^\]]*\]\s*/, '')
    .split('\n').filter((r) => !/^appunti (interi|di gemini)/i.test(r.trim())).join('\n')
    .replace(link ?? '\u0000', '').trim()
  return { riassunto, link }
}

const vicino = (x: string, y: string) => Math.abs(new Date(x).getTime() - new Date(y).getTime()) < FINESTRA

// IL RIASSUNTO GIUSTO (caccia ai bug 6/10): fra piu' testi della stessa call si preferisce
// quello di Gemini col link (breve e ordinato), poi la nota «Dalla call» che Clara scrive
// leggendo il transcript, e solo per ultimo l'inizio di una trascrizione grezza, tagliato.
function sceltaRiassunto(trans: Interaction[], note: Interaction[], at: string): { riassunto: string | null; link: string | null } {
  const pezzi = trans.map((t) => spezzaTranscript(t.body ?? ''))
  const link = pezzi.find((x) => x.link)?.link ?? null
  const breve = pezzi.find((x) => x.link && x.riassunto && x.riassunto.length <= LUNGO)
    ?? pezzi.find((x) => x.riassunto && x.riassunto.length <= LUNGO)
  if (breve) return { riassunto: breve.riassunto, link }
  const nota = note.find((n) => vicino(n.at, at) || trans.some((t) => vicino(n.at, t.at)))
  if (nota?.body) return { riassunto: nota.body.replace(/^Dalla call:\s*/i, '').trim(), link }
  const lungo = pezzi.find((x) => x.riassunto)?.riassunto
  return { riassunto: lungo ? `${lungo.slice(0, 900).trim()}…\n\n(La trascrizione intera sta negli appunti.)` : null, link }
}

function chiamateDi(timeline: Interaction[], agenda: AgendaItem[]): Chiamata[] {
  const adesso = new Date().toISOString()
  const trans = timeline.filter((t) => t.kind === 'transcript' || t.kind === 'call')
  const note = timeline.filter((t) => t.kind === 'nota' && /^dalla call/i.test(t.body ?? ''))
  const usati = new Set<string>()
  const out: Chiamata[] = []
  // un evento per call: in agenda ci sono doppioni identici (stesso titolo, stesso minuto)
  const visti = new Set<string>()
  const eventi = agenda.filter((a) => {
    if (a.at > adesso || NON_CALL.has(a.tipo ?? '')) return false
    const k = `${a.titolo.trim().toLowerCase()}|${a.at.slice(0, 16)}`
    if (visti.has(k)) return false
    visti.add(k)
    return true
  })
  // ogni transcript va all'evento PIU' VICINO nel tempo, non al primo della finestra
  // (revisione 7/10: due call in due giorni di fila si rubavano gli appunti)
  const delEvento = new Map<number, Interaction[]>()
  for (const t of trans) {
    let meglio: AgendaItem | null = null
    for (const a of eventi) {
      if (!vicino(t.at, a.at)) continue
      if (!meglio || Math.abs(new Date(t.at).getTime() - new Date(a.at).getTime())
          < Math.abs(new Date(t.at).getTime() - new Date(meglio.at).getTime())) meglio = a
    }
    if (meglio) delEvento.set(meglio.id, [...(delEvento.get(meglio.id) ?? []), t])
  }
  for (const a of eventi) {
    const suoi = delEvento.get(a.id) ?? []
    const eCall = ['conoscitiva', 'tecnica', 'avvio'].includes(a.tipo ?? '') || suoi.length > 0
      || Boolean(a.link) || PAROLE_CALL.test(a.titolo)
    if (!eCall) continue
    suoi.forEach((x) => usati.add(x.id))
    const { riassunto, link } = sceltaRiassunto(suoi, note, a.at)
    out.push({ chiave: `ag-${a.id}`, at: a.at, titolo: a.titolo, riassunto, link })
  }
  // i transcript senza evento in agenda, raggruppati per call (a 36 ore l'uno dall'altro)
  const orfani = trans.filter((t) => !usati.has(t.id) && t.body)
  for (const t of orfani) {
    if (usati.has(t.id)) continue
    const gruppo = orfani.filter((x) => !usati.has(x.id) && vicino(x.at, t.at))
    gruppo.forEach((x) => usati.add(x.id))
    const fase = gruppo.map((x) => /^\[(.+?)\]/.exec(x.body ?? '')?.[1]).find(Boolean)
    const { riassunto, link } = sceltaRiassunto(gruppo, note, t.at)
    out.push({ chiave: t.id, at: t.at, titolo: fase ? `Call, ${fase.toLowerCase()}` : 'Call', riassunto, link })
  }
  return out.sort((x, y) => y.at.localeCompare(x.at))
}

// il triangolo giallo, stile nostro: pieno, netto
const Triangolo = ({ size = 13 }: { size?: number }) => (
  <svg viewBox="0 0 24 24" style={{ width: size, height: size }} className="shrink-0 fill-amber-400" aria-hidden="true"><path d="M12 3 22 20H2z" /></svg>
)

const scarica = (nome: string, testo: string) => {
  const url = URL.createObjectURL(new Blob([testo], { type: 'text/plain;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url; a.download = nome; a.click()
  setTimeout(() => URL.revokeObjectURL(url), 5000)
}

// le azioni secondarie sono link, non trenta bottoni uguali (regola del 7/10)
const Link_ = ({ su, children, tip, href }: { su?: () => void; children: ReactNode; tip?: string; href?: string }) => href
  ? <a href={href} target="_blank" rel="noreferrer" data-tip={tip} className="shrink-0 text-[12px] font-semibold text-blu hover:underline">{children}</a>
  : <button onClick={su} data-tip={tip} className="shrink-0 text-[12px] font-semibold text-blu hover:underline">{children}</button>

const Titolo = ({ children, azione }: { children: ReactNode; azione?: ReactNode }) => (
  <div className="mb-2 flex items-baseline justify-between gap-2">
    <Micro>{children}</Micro>
    {azione}
  </div>
)

// etichette neutre: dal nome non si indovina il genere (Luca, Andrea, Nicola)
const DECIDE: Array<[string, string]> = [['si', 'Decide'], ['insieme', 'Decide con altri'], ['no', 'Non decide']]
const decideDi = (r: Pick<Referente, 'decide'>) => DECIDE.find(([k]) => k === r.decide)?.[1] ?? null

// una tappa del filo: quando, cosa, e i gesti che servono li'
interface Tappa {
  chiave: string
  at: string
  titolo: string
  testo?: string | null
  citazione?: boolean
  aperto?: string | null     // il testo lungo che si legge con «Vedi»
  attesa?: boolean           // col triangolo giallo
  azioni?: ReactNode
}

function Filo({ tappe, onTutto, totale, extra }: { tappe: Tappa[]; onTutto: () => void; totale: number; extra: ReactNode }) {
  const [vedo, setVedo] = useState<string | null>(null)
  return (
    <ol className="relative">
      {tappe.map((t, i) => (
        <li key={t.chiave} className="relative flex gap-3 pb-4">
          <div className="flex w-3 shrink-0 flex-col items-center">
            <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${i === 0 ? 'bg-navy' : 'bg-bordo'}`} />
            <span className="w-px flex-1 bg-bordo" />
          </div>
          <article className="min-w-0 flex-1">
            <p className="text-[11px] font-semibold tabular-nums text-tenue">{fmtDateShort(t.at)}{t.at.length > 10 ? `, ${fmtOra(t.at)}` : ''}</p>
            <h3 className="text-[15px] font-bold text-navy">{t.titolo}</h3>
            {t.testo && (
              <p className={`mt-0.5 text-[14px] leading-snug ${t.citazione ? 'italic text-inchiostro/80' : 'text-inchiostro/90'}`}>
                {t.attesa && <span className="mr-1.5 inline-flex translate-y-[1px]"><Triangolo /></span>}
                {t.citazione ? `«${t.testo}»` : t.testo}
              </p>
            )}
            {t.aperto && vedo === t.chiave && (
              <p className="mt-2 whitespace-pre-wrap rounded-xl bg-velo/70 px-3.5 py-2.5 text-[14px] leading-relaxed">{t.aperto}</p>
            )}
            <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1">
              {t.aperto && <Link_ su={() => setVedo(vedo === t.chiave ? null : t.chiave)}>{vedo === t.chiave ? 'Chiudi' : 'Vedi'}</Link_>}
              {t.azioni}
            </div>
          </article>
        </li>
      ))}
      <li className="flex flex-wrap items-center gap-x-4 gap-y-1 pl-6">
        <button onClick={onTutto} className="text-[14px] font-bold text-blu hover:underline">
          Storico completo{totale ? `, ${totale} eventi` : ''} ›
        </button>
        {extra}
      </li>
    </ol>
  )
}

// LA SCHEDA DI UN REFERENTE (Dre, 7/10: «Marco: non c'e' modo di aggiungere piu' info
// su di lui»). Si apre sul posto. Il principale vive nelle colonne di prospects (l'email
// e' la chiave con Smartlead: si copia, non si cambia da qui); gli altri in `referenti`.
function SchedaReferente({ r, principale, onSalva, onChiudi }: {
  r: Referente
  principale: boolean
  onSalva: (r: Referente) => Promise<boolean>
  onChiudi: () => void
}) {
  const [d, setD] = useState<Referente>(r)
  const [salvo, setSalvo] = useState(false)
  const campo = (k: keyof Referente, label: string, tipo = 'text', bloccato = false) => (
    <label className="block">
      <span className="mb-0.5 block text-[11px] font-semibold text-tenue">{label}</span>
      <input type={tipo} value={(d[k] as string | null) ?? ''} disabled={bloccato}
             onChange={(e) => setD({ ...d, [k]: e.target.value || null })}
             className="w-full rounded-lg border border-bordo bg-white px-2.5 py-1.5 text-[14px] outline-none focus:border-blu disabled:bg-velo/60 disabled:text-tenue" />
    </label>
  )
  return (
    <div className="mt-2 space-y-2.5 rounded-xl border border-bordo bg-fondo p-3">
      {campo('nome', 'Nome')}
      {campo('ruolo', 'Ruolo')}
      {campo('email', principale ? 'Email (la chiave con Smartlead: non si cambia da qui)' : 'Email', 'email', principale)}
      {campo('telefono', 'Telefono', 'tel')}
      {campo('linkedin', 'LinkedIn')}
      <div>
        <span className="mb-1 block text-[11px] font-semibold text-tenue">Chi decide</span>
        <div className="flex flex-wrap gap-1.5">
          {DECIDE.map(([k, t]) => (
            <button key={k} onClick={() => setD({ ...d, decide: d.decide === k ? null : k })}
                    className={`rounded-full px-3 py-1 text-[12px] font-semibold ${d.decide === k ? 'bg-navy text-white' : 'border border-bordo bg-white text-tenue hover:border-navy hover:text-navy'}`}>
              {t}
            </button>
          ))}
        </div>
      </div>
      <label className="block">
        <span className="mb-0.5 block text-[11px] font-semibold text-tenue">Note su di lui</span>
        <textarea value={d.nota ?? ''} onChange={(e) => setD({ ...d, nota: e.target.value || null })} rows={3}
                  placeholder="Come preferisce essere sentito, cosa gli sta a cuore, chi c'e' dietro"
                  className="w-full resize-y rounded-lg border border-bordo bg-white px-2.5 py-1.5 text-[14px] leading-snug outline-none focus:border-blu" />
      </label>
      <div className="flex gap-2">
        <button disabled={(!principale && !d.nome.trim()) || salvo}
                onClick={async () => { setSalvo(true); if (await onSalva(d)) onChiudi(); setSalvo(false) }}
                className="rounded-full bg-blu px-4 py-1.5 text-[12px] font-bold text-white hover:bg-navy disabled:opacity-40">
          Salva
        </button>
        <button onClick={onChiudi} className="rounded-full px-3 py-1.5 text-[12px] font-semibold text-tenue hover:text-inchiostro">Annulla</button>
      </div>
    </div>
  )
}

export default function VaultCliente({ id, sezione, onSezione, onClose, onApri }: Props) {
  const [completa, setCompleta] = useState(Boolean(sezione))   // #/azienda/<id>/lavoro apre gia' la Scheda
  const [p, setP] = useState<Prospect | null>(null)
  const [nonCe, setNonCe] = useState(false)
  const [timeline, setTimeline] = useState<Interaction[]>([])
  const [agendaSua, setAgendaSua] = useState<AgendaItem[]>([])
  const [referenti, setReferenti] = useState<Referente[]>([])
  const [preventivi, setPreventivi] = useState<Prev[]>([])
  const [documenti, setDocumenti] = useState<Doc[]>([])
  const [utenteId, setUtenteId] = useState<string | null>(null)
  const [statoAperto, setStatoAperto] = useState(false)
  const [storiaAperta, setStoriaAperta] = useState(false)
  const [esito, setEsito] = useState<string | null>(null)
  const [apertoRef, setApertoRef] = useState<number | 'nuovo' | null>(null)
  // i preventivi li vedono solo i ceo (il database lo fa gia', schema_v23): agli altri la
  // sezione non si mostra, invece di dire «nessuno ancora» quando non e' vero (7/10)
  const [ceo, setCeo] = useState(false)
  useEffect(() => { void sonoCeo().then(setCeo) }, [])

  useEffect(() => {
    let vivo = true
    setP(null); setNonCe(false); setApertoRef(null); setEsito(null)
    supabase.auth.getSession().then(({ data }) => { if (vivo) setUtenteId(data.session?.user?.id ?? null) })
    supabase.from('prospects').select('*').eq('id', id).maybeSingle()
      .then(({ data }) => { if (vivo) { setP(data as Prospect | null); if (!data) setNonCe(true) } })
    supabase.from('interactions').select('*').eq('prospect_id', id)
      .order('at', { ascending: false }).limit(200)
      .then(({ data }) => { if (vivo) setTimeline([...((data as Interaction[]) ?? [])].reverse()) })
    supabase.from('agenda').select('*').eq('prospect_id', id)
      .order('at', { ascending: true }).limit(100)
      .then(({ data }) => { if (vivo) setAgendaSua((data as AgendaItem[]) ?? []) })
    supabase.from('referenti').select('id,nome,ruolo,email,telefono,linkedin,decide,nota').eq('prospect_id', id)
      .order('at', { ascending: true }).limit(30)
      .then(({ data, error }) => {
        if (!vivo) return
        // un errore non e' «nessun referente» (la tabella v75 puo' non essere ancora attiva)
        if (error) { setEsito(`I referenti in più non si leggono: ${error.message}`); setTimeout(() => setEsito(null), 6000) }
        setReferenti((data as Referente[]) ?? [])
      })
    supabase.from('preventivi').select('id,numero,titolo,importo,mensile,stato,pagato_il,inviato_il,accettato_il,rifiutato_il,pdf_path')
      .eq('prospect_id', id).order('creato_il', { ascending: false }).limit(20)
      .then(({ data }) => { if (vivo) setPreventivi((data as Prev[]) ?? []) })
    supabase.from('vault_file').select('id,nome,path,at').eq('prospect_id', id)
      .order('at', { ascending: false }).limit(50)
      .then(({ data }) => { if (vivo) setDocumenti((data as Doc[]) ?? []) })
    return () => { vivo = false }
  }, [id])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape' || completa || storiaAperta || document.body.dataset.sopra || e.defaultPrevented) return
      const el = document.activeElement as HTMLElement | null
      if (el && /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName)) { el.blur(); return }
      onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose, completa, storiaAperta])

  const chiamate = useMemo(() => chiamateDi(timeline, agendaSua), [timeline, agendaSua])

  function di(secondi: number, msg: string) { setEsito(msg); setTimeout(() => setEsito(null), secondi * 1000) }

  async function aggiorna(patch: Partial<Prospect>) {
    if (!p) return false
    const prima = p
    setP({ ...p, ...patch } as Prospect)
    const { data, error } = await supabase.from('prospects').update(patch).eq('id', id).select().single()
    if (data) setP(data as Prospect)
    if (error) { setP(prima); di(5, 'Salvataggio non riuscito: ' + error.message) }
    return Boolean(data) && !error
  }

  async function nota(body: string) {
    const { data } = await supabase.from('interactions')
      .insert({ prospect_id: id, at: new Date().toISOString(), kind: 'nota', body }).select().single()
    if (data) setTimeline((t) => [...t, data as Interaction])   // il filo la vede subito
  }

  // la pillola di stato: Prospect o Cliente, lo decide Dre con un clic.
  // «Cliente» usa la stessa scrittura del Foglio (TuttiFoglio.cambiaStato);
  // «Prospect» lo rimette in pipeline, in Conoscitiva.
  async function cambiaStato(s: 'prospect' | 'cliente') {
    if (!p) return
    const cliente = eCliente(p)
    setStatoAperto(false)
    const adesso = new Date().toISOString()
    // revisione 7/10, le stesse regole di percorso.ts: da Cliente a Prospect il contratto e il
    // canone non restano appesi (riclicando Cliente tornavano in vita da soli), da Perso il
    // motivo dell'uscita si toglie
    const patch = s === 'cliente'
      ? { fuori: true, fuori_at: p.fuori_at ?? adesso, pipeline_stage: 'cliente', contratto: 'stable', awaiting_us: false, no_followup: true, lost_reason: null }
      : { fuori: true, fuori_at: p.fuori_at ?? adesso, pipeline_stage: 'conoscitiva', contratto: null, lost_reason: null }
    const eraCliente = cliente
    if (!(await aggiorna(patch as Partial<Prospect>))) return
    if (s === 'prospect' && eraCliente) void azzeraCanone(id)
    await nota(s === 'cliente' ? 'DIVENTA CLIENTE.' : 'Torna prospect, in Conoscitiva.')
  }

  // condividere in chat: un messaggio nella stanza comune, taggato su di lui.
  // Il file e' GIA' nei Documenti: si passa il riferimento, non una copia.
  async function inChat(testo: string, file_id?: number) {
    const { error } = await supabase.from('chat').insert({ da: utenteId, a: null, testo, prospect_id: id, file_id: file_id ?? null })
    di(3, error ? 'Non è partito: ' + error.message : 'In chat, a tutta la squadra')
  }

  async function accogli(f: File) {
    const { file, errore } = await caricaFile(id, f)
    if (errore || !file) { di(6, errore ?? 'Caricamento non riuscito'); return }
    setDocumenti((v) => [{ id: file.id, nome: file.nome, path: file.path, at: file.at ?? new Date().toISOString() }, ...v])
    await nota(`${f.name}, nei Documenti`)
    di(3, `«${file.nome}» nei Documenti`)
  }

  // il referente principale: colonne di prospects + enriched.referente (decide, nota)
  const principale: Referente | null = p ? {
    id: 0, nome: p.name ?? '', ruolo: p.role, email: p.email, telefono: p.phone, linkedin: p.linkedin,
    decide: ((p.enriched as Record<string, unknown> | null)?.referente as { decide?: string } | undefined)?.decide ?? null,
    nota: ((p.enriched as Record<string, unknown> | null)?.referente as { nota?: string } | undefined)?.nota ?? null,
  } : null

  async function salvaReferente(r: Referente): Promise<boolean> {
    if (r.id === 0 && p) {
      // revisione 7/10: il pannello resta aperto a lungo, e intanto Clara riscrive enriched (il
      // punto, il fit). Si rilegge adesso e si cambia solo la chiave del referente
      const { data: fresco } = await supabase.from('prospects').select('enriched').eq('id', id).maybeSingle()
      const base = ((fresco as { enriched?: Record<string, unknown> } | null)?.enriched ?? p.enriched ?? {}) as Record<string, unknown>
      const enriched = { ...base, referente: { decide: r.decide, nota: r.nota } } as unknown as Prospect['enriched']
      return aggiorna({ name: r.nome.trim() || null, role: r.ruolo, phone: r.telefono, linkedin: r.linkedin, enriched } as Partial<Prospect>)
    }
    const riga = { nome: r.nome.trim(), ruolo: r.ruolo, email: r.email, telefono: r.telefono, linkedin: r.linkedin, decide: r.decide, nota: r.nota }
    if (r.id < 0) {
      const { data, error } = await supabase.from('referenti').insert({ prospect_id: id, ...riga })
        .select('id,nome,ruolo,email,telefono,linkedin,decide,nota').single()
      if (error || !data) { di(6, /referenti/.test(error?.message ?? '') ? 'I referenti in più chiedono un passo in Supabase (schema_v75): è nel foglio «Da incollare in Supabase».' : 'Il referente non si salva: ' + (error?.message ?? '')); return false }
      setReferenti((v) => [...v, data as Referente])
      return true
    }
    const { error } = await supabase.from('referenti').update(riga).eq('id', r.id)
    if (error) { di(6, 'Il referente non si salva: ' + error.message); return false }
    setReferenti((v) => v.map((x) => (x.id === r.id ? r : x)))
    return true
  }

  // lo storico in un testo solo, da scaricare: le stesse tappe della Storia
  function storicoTesto(): string {
    const righe = [
      `${p?.company || p?.name || p?.email}, storico completo al ${fmtDateShort(new Date().toISOString())}`,
      '',
      ...[...timeline.filter((t) => t.kind !== 'postit' && t.kind !== 'prep').map((t) => ({ at: t.at, r: `[${fmtDateShort(t.at)} ${fmtOra(t.at)}] ${t.kind}: ${(t.body ?? '').trim()}` })),
        ...agendaSua.map((a) => ({ at: a.at, r: `[${fmtDateShort(a.at)} ${fmtOra(a.at)}] in calendario: ${a.titolo}` }))]
        .sort((x, y) => x.at.localeCompare(y.at)).map((x) => x.r),
    ]
    return righe.join('\n\n')
  }

  // IL FILO: le tappe vere, dalla piu' recente. Le mail, l'analisi, ogni call col suo
  // riassunto, i preventivi, i cambi di fase, i documenti. Le note di servizio no.
  const tappe = useMemo((): Tappa[] => {
    if (!p) return []
    const out: Tappa[] = []
    const prima = timeline.find((t) => t.kind === 'email_in')
    for (const t of timeline) {
      const b = (t.body ?? '').replace(/\s+/g, ' ').trim()
      const corto = b.length > 160 ? `${b.slice(0, 159)}…` : b
      if (t.kind === 'email_in') {
        out.push({ chiave: t.id, at: t.at, titolo: t.id === prima?.id ? 'Prima risposta' : 'Ha scritto', testo: corto, citazione: true,
          aperto: b.length > 160 ? t.body : null })
      } else if (t.kind === 'email_out' || t.kind === 'followup') {
        out.push({ chiave: t.id, at: t.at, titolo: t.kind === 'followup' ? 'Follow-up' : 'Gli abbiamo scritto', testo: corto,
          aperto: b.length > 160 ? t.body : null })
      } else if (t.kind === 'analisi') {
        out.push({ chiave: t.id, at: t.at, titolo: 'Analisi Google Ads inviata',
          azioni: p.analysis_pdf ? <>
            <Link_ href={p.analysis_pdf}>Apri</Link_>
            <Link_ su={() => void inChat(`L'analisi di ${p.company || p.name}: ${p.analysis_pdf}`)}>In chat</Link_>
          </> : undefined })
      } else if (t.kind === 'nota') {
        const fase = /^\[(.+?)\]/.exec(t.body ?? '')?.[1]
        if (fase) out.push({ chiave: t.id, at: t.at, titolo: fase, testo: (t.body ?? '').replace(/^\[.+?\]\s*/, '').slice(0, 160) })
        else if (/^DIVENTA CLIENTE/i.test(b)) out.push({ chiave: t.id, at: t.at, titolo: 'Diventa cliente' })
        // le note che scrivono le mosse vere (percorso.ts, triage, archivio): revisione 7/10
        else if (/^(Passa a|Torna prospect|Torna in|Entra in|Riaperta|Segnato come perso|Uscita dalla pipeline|Ripreso dall'archivio|SOPPRESSO|Fuori target)/i.test(b)) {
          out.push({ chiave: t.id, at: t.at, titolo: b.split(/[.:]/)[0].slice(0, 80), testo: b.includes(':') ? b.slice(b.indexOf(':') + 1).trim().slice(0, 160) : null })
        }
      }
    }
    for (const c of chiamate) {
      out.push({ chiave: c.chiave, at: c.at, titolo: c.titolo,
        testo: c.riassunto ? (c.riassunto.length > 220 ? `${c.riassunto.slice(0, 219).trim()}…` : c.riassunto)
          : Date.now() - new Date(c.at).getTime() > 3 * 86400e3 ? 'Senza appunti.' : 'Gli appunti non sono ancora arrivati.',
        aperto: c.riassunto && c.riassunto.length > 220 ? c.riassunto : null,
        azioni: <>
          {c.link && <Link_ href={c.link}>Appunti su Drive</Link_>}
          {c.riassunto && <Link_ su={() => scarica(`call-${fmtDateShort(c.at).replace(/\//g, '-')}.txt`, `${c.titolo}, ${fmtDateShort(c.at)}\n\n${c.riassunto}`)}>Scarica</Link_>}
          {c.riassunto && <Link_ su={() => void inChat(`Call «${c.titolo}» del ${fmtDateShort(c.at)}, il riassunto:\n${c.riassunto}`)}>In chat</Link_>}
        </> })
    }
    for (const q of preventivi) {
      const cosa = `${q.titolo || 'Preventivo'}${q.importo ? `, ${Number(q.importo).toLocaleString('it-IT')} €` : ''}${q.mensile ? ` + ${Number(q.mensile).toLocaleString('it-IT')} €/mese` : ''}`
      const pdf = q.pdf_path ? <Link_ su={() => void apriFile(q.pdf_path!)}>Apri il PDF</Link_> : null
      if (q.inviato_il) out.push({ chiave: `pi-${q.id}`, at: q.inviato_il, titolo: 'Preventivo inviato', testo: cosa,
        attesa: q.stato === 'inviato', azioni: pdf })
      if (q.accettato_il) out.push({ chiave: `pa-${q.id}`, at: q.accettato_il, titolo: 'Preventivo accettato', testo: cosa, azioni: pdf })
      if (q.rifiutato_il) out.push({ chiave: `pr-${q.id}`, at: q.rifiutato_il, titolo: 'Preventivo rifiutato', testo: cosa })
      if (q.pagato_il) out.push({ chiave: `pp-${q.id}`, at: q.pagato_il, titolo: 'Pagato', testo: cosa })
    }
    const chiave = (at: string) => (at.length === 10 ? `${at}T23:59:59` : at)
    return out.sort((x, y) => chiave(y.at).localeCompare(chiave(x.at)))
  }, [p, timeline, chiamate, preventivi])   // eslint-disable-line react-hooks/exhaustive-deps

  if (completa) return <Scheda key={id} id={id} sezione={sezione} onSezione={onSezione} onClose={onClose} onApri={onApri} />

  if (!p) return (
    <div className="fixed inset-0 z-50">
      <div onClick={onClose} className="absolute inset-0 bg-inchiostro/15" />
      <aside className="scivola absolute inset-y-0 right-0 w-full max-w-[920px] overflow-y-auto border-l border-bordo bg-fondo">
        <div className="flex items-center gap-3 border-b border-bordo bg-white px-4 py-2.5">
          <button onClick={onClose} className="text-sm font-semibold text-blu hover:underline">‹ Torna</button>
        </div>
        {nonCe
          ? <p className="px-5 py-8 text-sm text-spento">Questa azienda non è nel tuo perimetro: chiedi a Dre o a Giacomo.</p>
          : <Spinner />}
      </aside>
    </div>
  )

  const cliente = eCliente(p)
  const perso = ePerso(p)
  const nome = p.company || p.name || p.email
  const adesso = new Date().toISOString()
  const prossima = agendaSua.find((a) => a.at > adesso && !NON_CALL.has(a.tipo ?? ''))
  const inAttesa = preventivi.filter((q) => q.stato === 'inviato')
  const punto = (p.enriched as Record<string, unknown> | null)?.punto as { testo?: string; passo?: string } | undefined
  const fase = cliente ? null : p.fuori && p.pipeline_stage ? PIPELINE_LABEL[p.pipeline_stage as PipelineStage] : null
  const sito = p.website ? (p.website.startsWith('http') ? p.website : `https://${p.website}`) : null
  const tutti = principale ? [principale, ...referenti] : referenti
  const daMostrare = tappe.slice(0, 8)

  // IL FASCICOLO IN PDF (Dre, 6/10): lo stesso Vault, su un foglio pulito da mandare
  function pdf() {
    if (!p) return
    const cifra = (q: Prev) => `${q.importo ? `${Number(q.importo).toLocaleString('it-IT')} €` : ''}${q.mensile ? `${q.importo ? ' + ' : ''}${Number(q.mensile).toLocaleString('it-IT')} €/mese` : ''}`
    const ok = apriFascicolo({
      nome: nome ?? '', codice: sgid(p.sg_id), stato: cliente ? 'Cliente' : perso ? 'Perso' : 'Prospect', fase,
      chiSono: p.descrizione ? p.descrizione.split(/(?<=\.)\s/)[0].replace(/\.$/, '') : (p.sector?.replace(/_/g, ' ') ?? null),
      citta: p.city, sito: p.website ? p.website.replace(/^https?:\/\//, '').replace(/\/$/, '') : null,
      punto: punto?.testo ?? p.next_action ?? null,
      prossima: prossima ? `${prossima.titolo}, ${new Date(prossima.at).toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long' })} alle ${fmtOra(prossima.at)}` : null,
      referenti: tutti.map((r) => ({ nome: r.nome, ruolo: r.ruolo, email: r.email, telefono: r.telefono, decide: decideDi(r), nota: r.nota })),
      preventivi: preventivi.map((q) => ({ numero: q.numero, titolo: q.titolo, cifra: cifra(q),
        stato: q.pagato_il ? 'pagato' : q.stato === 'inviato' ? `in attesa${q.inviato_il ? ` dal ${fmtDateShort(q.inviato_il)}` : ''}` : q.stato })),
      documenti: [...(p.analysis_pdf ? ["Analisi Google Ads"] : []), ...documenti.map((d) => d.nome)],
      filo: tappe.map((t) => ({ at: t.at, titolo: t.titolo, testo: t.aperto ?? t.testo ?? null })),
      logo: new URL(`${import.meta.env.BASE_URL}brand/SG_logo_blu.png`, location.href).href,
    })
    if (!ok) di(5, 'Il browser ha bloccato la finestra: consenti i popup per il Workspace e riprova')
  }

  return (
    <div className="fixed inset-0 z-50">
      <div onClick={onClose} className="absolute inset-0 bg-inchiostro/15" />
      <aside className="scivola absolute inset-y-0 right-0 flex w-full max-w-[920px] flex-col border-l border-bordo bg-fondo">
        {/* la barra: torna, il link del vault, la scheda completa per il lavoro fine */}
        <div className="flex items-center gap-3 border-b border-bordo bg-white px-4 py-2.5">
          <button onClick={onClose} className="shrink-0 text-sm font-semibold text-blu hover:underline">‹ Torna</button>
          <Micro>Vault</Micro>
          <span className="min-w-0 flex-1" />
          <button onClick={pdf} data-tip="Il fascicolo su un foglio: lo salvi in PDF e lo mandi" className="shrink-0 text-[12px] font-semibold text-blu hover:underline">PDF</button>
          <Copia testo={linkDi({ tab: 'prospect', id: p.id, sezione: null })} cosa="il link di questo Vault, da mandare a qualcuno">
            <span className="shrink-0 text-[12px] font-semibold text-blu">Link</span>
          </Copia>
          <button onClick={() => setCompleta(true)} className="shrink-0 rounded-full border border-bordo px-3 py-1 text-xs font-bold text-navy hover:border-navy">
            Scheda completa
          </button>
        </div>

        <ZonaFile onFile={accogli} messaggio={`Lascia qui: nei Documenti, agganciato a ${nome}`} className="flex-1 overflow-y-auto">

          {/* ── la testata: chi e', a che punto, e il referente gia' contattabile ── */}
          <header className="border-b border-bordo bg-white px-4 pb-4 pt-4 sm:px-6">
            <div className="flex flex-wrap items-center gap-2">
              {sgid(p.sg_id) && (
                <Copia testo={sgid(p.sg_id)!} cosa="il codice">
                  <span className="text-[12px] font-bold tracking-wide text-blu">{sgid(p.sg_id)}</span>
                </Copia>
              )}
              <button onClick={() => setStatoAperto(!statoAperto)} title="Lo stato: clicca per cambiarlo"
                      className={`rounded-full px-2.5 py-0.5 text-[12px] font-bold ${cliente ? 'bg-green-50 text-green-800' : perso ? 'bg-velo text-tenue' : 'bg-amber-50 text-amber-800'}`}>
                {cliente ? 'Cliente' : perso ? 'Perso' : 'Prospect'} {statoAperto ? '▴' : '▾'}
              </button>
              {statoAperto && (['prospect', 'cliente'] as const)
                .filter((s) => (s === 'cliente') !== cliente || perso)
                .map((s) => (
                  <button key={s} onClick={() => void cambiaStato(s)}
                          className="rounded-full border border-bordo bg-white px-2.5 py-0.5 text-[12px] font-semibold text-tenue hover:border-blu hover:text-blu">
                    {s === 'cliente' ? 'Cliente' : 'Prospect'}
                  </button>
                ))}
              {fase && <span className="text-[12px] font-semibold text-tenue">{fase}</span>}
            </div>
            <div className="mt-2 flex items-start gap-3">
              <Faccia p={p} size={44} />
              <div className="min-w-0 flex-1">
                <h2 className="text-[22px] font-extrabold leading-tight text-navy">{nome}</h2>
                <p className="mt-0.5 text-[14px] text-tenue">
                  {[p.descrizione ? p.descrizione.split(/(?<=\.)\s/)[0].replace(/\.$/, '') : p.sector?.replace(/_/g, ' '), p.city].filter(Boolean).join(', ')}
                  {sito && <> {' '}<a href={sito} target="_blank" rel="noreferrer" className="font-semibold text-blu hover:underline">{p.website!.replace(/^https?:\/\//, '').replace(/\/$/, '')}</a></>}
                </p>
              </div>
            </div>
            {principale && (principale.nome || principale.email) && (
              <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[14px]">
                <span className="font-semibold">{principale.nome || 'Referente'}{principale.ruolo ? <span className="font-normal text-tenue">, {principale.ruolo}</span> : null}</span>
                {principale.email && <Copia testo={principale.email} cosa="l'indirizzo"><span className="text-blu">{principale.email}</span></Copia>}
                {principale.telefono && <a href={`tel:${principale.telefono}`} className="text-blu hover:underline">{principale.telefono}</a>}
                {decideDi(principale) && <span className="rounded-full bg-velo px-2.5 py-0.5 text-[12px] font-semibold text-navy">{decideDi(principale)}</span>}
              </div>
            )}
          </header>

          <div className="grid gap-4 px-4 py-4 pb-16 sm:px-6 lg:grid-cols-[272px_minmax(0,1fr)] lg:grid-rows-[auto_1fr]">

            {/* ── Adesso: cosa aspetta, la prossima call ── */}
            <Card className="order-1 p-4 lg:order-none lg:col-start-2 lg:row-start-1 lg:self-start">
              <Titolo>Adesso</Titolo>
              {punto?.testo && <p className="text-[15px] leading-snug">{punto.testo}</p>}
              {!punto?.testo && p.next_action && <p className="text-[15px] leading-snug">{p.next_action}{p.next_action_date ? `, ${fmtDateShort(p.next_action_date)}` : ''}</p>}
              {!punto?.testo && !p.next_action && !prossima && !inAttesa.length && !p.awaiting_us && (
                <p className="text-[14px] text-tenue">Niente in sospeso.</p>
              )}
              {p.awaiting_us && (
                <p className="mt-2 flex items-center gap-2 text-[14px] font-semibold text-amber-900">
                  <span className="h-2 w-2 shrink-0 rounded-full bg-amber-400" />Ha scritto: c'è da rispondere
                </p>
              )}
              {prossima && (
                <div className="mt-3 flex items-center gap-3 rounded-xl bg-velo/70 px-3 py-2.5">
                  <span className="flex w-11 shrink-0 flex-col items-center rounded-lg bg-white py-1 leading-none">
                    <span className="text-[10px] font-bold uppercase text-tenue">{new Date(prossima.at).toLocaleDateString('it-IT', { weekday: 'short' })}</span>
                    <span className="text-[18px] font-extrabold text-navy">{new Date(prossima.at).getDate()}</span>
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[14px] font-bold">{prossima.titolo}</span>
                    <span className="block text-[13px] text-tenue">{new Date(prossima.at).toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'short' })} alle {fmtOra(prossima.at)}</span>
                  </span>
                  {prossima.link && (
                    <a href={prossima.link} target="_blank" rel="noreferrer" className="shrink-0 rounded-full bg-blu px-3.5 py-1.5 text-[12px] font-bold text-white hover:bg-navy">Apri Meet</a>
                  )}
                </div>
              )}
              {inAttesa.map((q) => (
                <p key={q.id} className="mt-2 flex items-center gap-2 text-[14px]">
                  <Triangolo size={14} />
                  <span><b>{q.numero ?? q.titolo}</b> aspetta risposta{q.inviato_il ? ` dal ${fmtDateShort(q.inviato_il)}` : ''}</span>
                </p>
              ))}
            </Card>

            {/* ── le cose ferme: referenti, preventivi, documenti ── */}
            <div className="order-3 space-y-4 lg:order-none lg:col-start-1 lg:row-span-2 lg:row-start-1 lg:self-start">
              <Card className="p-4">
                <Titolo azione={<Link_ su={() => setApertoRef(apertoRef === 'nuovo' ? null : 'nuovo')}>+ Aggiungi</Link_>}>Referenti</Titolo>
                <ul className="space-y-1">
                  {tutti.map((r) => (
                    <li key={r.id}>
                      <button onClick={() => setApertoRef(apertoRef === r.id ? null : r.id)}
                              className="flex w-full items-center gap-2.5 rounded-lg py-1.5 text-left hover:bg-velo/50">
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-velo text-[12px] font-bold text-navy">
                          {(r.nome || '?').split(/\s+/).map((x) => x[0]).slice(0, 2).join('').toUpperCase()}
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-[14px] font-semibold">{r.nome || 'Senza nome'}</span>
                          <span className="block truncate text-[12px] text-tenue">{[r.ruolo, decideDi(r)].filter(Boolean).join(', ') || (r.id === 0 ? 'il contatto principale' : '')}</span>
                        </span>
                        <span className="shrink-0 text-[12px] text-spento">{apertoRef === r.id ? '▴' : '›'}</span>
                      </button>
                      {apertoRef !== r.id && r.id !== 0 && (r.email || r.telefono) && (
                        <p className="ml-[42px] flex flex-wrap gap-x-3 text-[13px]">
                          {r.email && <Copia testo={r.email} cosa="l'indirizzo"><span className="text-blu">{r.email}</span></Copia>}
                          {r.telefono && <a href={`tel:${r.telefono}`} className="text-blu">{r.telefono}</a>}
                        </p>
                      )}
                      {apertoRef !== r.id && r.nota && <p className="ml-[42px] line-clamp-2 text-[12.5px] text-tenue">{r.nota}</p>}
                      {apertoRef === r.id && (
                        <SchedaReferente r={r} principale={r.id === 0} onSalva={salvaReferente} onChiudi={() => setApertoRef(null)} />
                      )}
                    </li>
                  ))}
                </ul>
                {apertoRef === 'nuovo' && (
                  <SchedaReferente r={{ id: -1, nome: '', ruolo: null, email: null, telefono: null, linkedin: null, decide: null, nota: null }}
                                   principale={false} onSalva={salvaReferente} onChiudi={() => setApertoRef(null)} />
                )}
              </Card>

              {ceo && <Card className="p-4">
                <Titolo azione={<Link_ su={() => { try { sessionStorage.setItem('preventivo:nuovo', id) } catch { /* niente */ } window.dispatchEvent(new CustomEvent('preventivo:nuovo', { detail: id })) }}>+ Nuovo</Link_>}>Preventivi</Titolo>
                {preventivi.length === 0 ? <p className="text-[13px] text-tenue">Nessuno ancora.</p> : (
                  <ul className="space-y-2.5">
                    {preventivi.map((q) => (
                      <li key={q.id}>
                        <button onClick={() => q.pdf_path && void apriFile(q.pdf_path)} disabled={!q.pdf_path} className="block w-full text-left disabled:cursor-default">
                          <span className={`flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-[0.04em] ${
                            q.stato === 'inviato' ? 'text-amber-800' : q.stato === 'accettato' || q.pagato_il ? 'text-green-800' : q.stato === 'rifiutato' ? 'text-red-700' : 'text-tenue'}`}>
                            {q.stato === 'inviato' && <Triangolo size={11} />}
                            {q.pagato_il ? 'Pagato' : q.stato === 'inviato' ? `In attesa${q.inviato_il ? ` dal ${fmtDateShort(q.inviato_il)}` : ''}` : q.stato}
                          </span>
                          <span className="block text-[14px] font-semibold leading-snug">{q.titolo || 'Preventivo'}</span>
                          <span className="flex justify-between gap-2 text-[12.5px] text-tenue">
                            <span className="truncate">{q.numero}</span>
                            <span className="shrink-0 font-semibold tabular-nums text-inchiostro">
                              {q.importo ? `${Number(q.importo).toLocaleString('it-IT')} €` : ''}{q.mensile ? `${q.importo ? ' + ' : ''}${Number(q.mensile).toLocaleString('it-IT')} €/mese` : ''}
                            </span>
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>}

              <Card className="p-4">
                <Titolo azione={<span className="text-[12px] font-semibold text-tenue">{documenti.length + (p.analysis_pdf ? 1 : 0) || ''}</span>}>Documenti</Titolo>
                <ul className="space-y-1.5">
                  {p.analysis_pdf && (
                    <li className="flex items-center gap-2">
                      <a href={p.analysis_pdf} target="_blank" rel="noreferrer" className="min-w-0 flex-1 truncate text-[14px] font-semibold text-blu hover:underline">Analisi Google Ads</a>
                      <Link_ su={() => void inChat(`L'analisi di ${nome}: ${p.analysis_pdf}`)} tip="Il link nella chat della squadra">In chat</Link_>
                    </li>
                  )}
                  {documenti.map((d) => (
                    <li key={d.id} className="flex items-center gap-2">
                      <button onClick={() => void apriFile(d.path)} className="min-w-0 flex-1 truncate text-left text-[14px] text-blu hover:underline">{d.nome}</button>
                      <span className="shrink-0 text-[12px] tabular-nums text-tenue">{fmtDateShort(d.at)}</span>
                      <Link_ su={() => void inChat(`«${d.nome}»`, d.id)} tip="Il documento nella chat della squadra">In chat</Link_>
                    </li>
                  ))}
                </ul>
                <label className="mt-3 flex cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-bordo py-2.5 text-[13px] font-semibold text-tenue hover:border-navy hover:text-navy">
                  <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><path d="M12 16V4m0 0-4 4m4-4 4 4M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" /></svg>
                  Trascina un file, o sceglilo
                  <input type="file" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) void accogli(f); e.target.value = '' }} />
                </label>
              </Card>
            </div>

            {/* ── il filo del rapporto, dalla tappa piu' recente ── */}
            <section className="order-2 lg:order-none lg:col-start-2 lg:row-start-2">
              <Micro className="mb-3 block">Il filo</Micro>
              {daMostrare.length === 0
                ? <p className="text-[14px] text-tenue">Ancora nessuna tappa: le mail, le call e i preventivi arrivano qui da soli.</p>
                : <Filo tappe={daMostrare} totale={timeline.filter((t) => t.kind !== 'postit' && t.kind !== 'prep').length + agendaSua.length} onTutto={() => setStoriaAperta(true)}
                        extra={<>
                          <Link_ su={() => scarica(`storico-${(nome ?? 'azienda').toLowerCase().replace(/[^a-z0-9]+/g, '-')}.txt`, storicoTesto())} tip="Tutto il rapporto in un file">Scarica</Link_>
                          <Link_ su={() => void inChat(`Il fascicolo di ${nome}: ${linkDi({ tab: 'prospect', id: p.id, sezione: null })}`)} tip="Il link del Vault nella chat della squadra">In chat</Link_>
                        </>} />}
            </section>
          </div>
        </ZonaFile>

        {esito && (
          <p className="pointer-events-none absolute bottom-4 left-1/2 z-20 -translate-x-1/2 rounded-full bg-navy px-4 py-2 text-xs font-bold text-white shadow-lg">
            {esito}
          </p>
        )}

        {storiaAperta && (
          <StoriaCompleta
            prospectId={p.id} nome={nome ?? ''} timeline={timeline} agenda={agendaSua}
            prossimoPasso={{ cosa: p.next_action, quando: p.next_action_date }}
            onChiudi={() => setStoriaAperta(false)}
          />
        )}
      </aside>
    </div>
  )
}
