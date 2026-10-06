import { useEffect, useMemo, useState } from 'react'
import { supabase } from '../lib/supabase'
import {
  PIPELINE_LABEL,
  type Prospect, type Interaction, type AgendaItem, type PipelineStage,
} from '../lib/types'
import { eCliente, ePerso } from '../lib/regole'
import { apriFile, caricaFile } from '../lib/file'
import { linkDi } from '../lib/indirizzo'
import Copia from './Copia'
import Scheda from './Scheda'
import { StoriaCompleta } from './Storia'
import { Card, Micro, Spinner, ZonaFile, Faccia, fmtDateShort, fmtOra, sgid } from './ui'

// IL VAULT DEL CLIENTE (Dre, a voce, 6/10): «quando si entra c'è il nome
// dell'azienda, con accanto lo stato selezionabile: cliente oppure prospect.
// Subito sotto i referenti, poi i preventivi (quelli in attesa col triangolo
// giallo), poi le chiamate col riassunto di Gemini, poi i documenti, e in
// fondo visualizza storico completo. La prima facciata è pulita: posso
// cliccare sulla parte che mi interessa e approfondire».
//
// Quindi: una colonna di sezioni chiuse, ognuna con la sua riga di sintesi.
// Un clic apre, un altro chiude. Il lavoro fine (bozze, pipeline, prezzo)
// resta nella Scheda completa, a un bottone da qui.

interface Props {
  id: string
  sezione?: string | null
  onSezione?: (s: string | null) => void
  onClose: () => void
  onApri?: (id: string) => void
}

interface Referente { id: number; nome: string; ruolo: string | null; email: string | null; telefono: string | null; nota: string | null }
interface Prev { id: number; numero: string | null; titolo: string | null; importo: number | null; mensile: number | null; stato: string; pagato_il: string | null; inviato_il: string | null; pdf_path: string | null }
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

// il triangolo giallo, stile nostro: pieno, netto, col numero accanto
function Triangolo({ n }: { n: number }) {
  return (
    <span data-tip={`${n} in attesa di risposta`} className="inline-flex shrink-0 items-center gap-1 text-[11px] font-bold text-amber-800">
      <svg viewBox="0 0 24 24" className="h-[13px] w-[13px] fill-amber-400"><path d="M12 3 22 20H2z" /></svg>
      {n} in attesa
    </span>
  )
}

// una sezione del Vault: chiusa e' una riga di sintesi, aperta mostra tutto
function Sez({ titolo, sommario, extra, aperta, su, children }: {
  titolo: string
  sommario: string
  extra?: React.ReactNode
  aperta: boolean
  su: () => void
  children: React.ReactNode
}) {
  return (
    <Card>
      <button onClick={su} className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-velo/40">
        <Micro className="w-[88px]">{titolo}</Micro>
        <span className="min-w-0 flex-1 truncate text-sm text-tenue">{sommario}</span>
        {extra}
        <span className="shrink-0 text-xs text-spento">{aperta ? '▴' : '▾'}</span>
      </button>
      {aperta && <div className="border-t border-velo px-4 py-3">{children}</div>}
    </Card>
  )
}

const scarica = (nome: string, testo: string) => {
  const url = URL.createObjectURL(new Blob([testo], { type: 'text/plain;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url; a.download = nome; a.click()
  setTimeout(() => URL.revokeObjectURL(url), 5000)
}

const Azione = ({ su, children, tip }: { su: () => void; children: React.ReactNode; tip?: string }) => (
  <button onClick={su} data-tip={tip} className="shrink-0 rounded-full border border-bordo px-2.5 py-0.5 text-[11px] font-semibold text-navy hover:border-navy">
    {children}
  </button>
)

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
  const [aperta, setAperta] = useState<string | null>(null)
  const [statoAperto, setStatoAperto] = useState(false)
  const [storiaAperta, setStoriaAperta] = useState(false)
  const [vedo, setVedo] = useState<string | null>(null)        // la chiamata col riassunto spiegato
  const [esito, setEsito] = useState<string | null>(null)
  const [nuovoRef, setNuovoRef] = useState(false)
  const [refDraft, setRefDraft] = useState({ nome: '', ruolo: '', email: '', telefono: '' })

  useEffect(() => {
    let vivo = true
    setP(null); setNonCe(false); setAperta(null); setVedo(null); setEsito(null)
    supabase.auth.getSession().then(({ data }) => { if (vivo) setUtenteId(data.session?.user?.id ?? null) })
    supabase.from('prospects').select('*').eq('id', id).maybeSingle()
      .then(({ data }) => { if (vivo) { setP(data as Prospect | null); if (!data) setNonCe(true) } })
    supabase.from('interactions').select('*').eq('prospect_id', id)
      .order('at', { ascending: false }).limit(200)
      .then(({ data }) => { if (vivo) setTimeline([...((data as Interaction[]) ?? [])].reverse()) })
    supabase.from('agenda').select('*').eq('prospect_id', id)
      .order('at', { ascending: true }).limit(100)
      .then(({ data }) => { if (vivo) setAgendaSua((data as AgendaItem[]) ?? []) })
    supabase.from('referenti').select('id,nome,ruolo,email,telefono,nota').eq('prospect_id', id)
      .order('at', { ascending: true }).limit(30)
      .then(({ data, error }) => {
        if (!vivo) return
        // 7/10: un errore non e' «nessun referente» (la tabella v75 puo' non essere ancora attiva)
        if (error) setEsito(`I referenti in piu' non si leggono: ${error.message}`)
        setReferenti((data as Referente[]) ?? [])
      })
    supabase.from('preventivi').select('id,numero,titolo,importo,mensile,stato,pagato_il,inviato_il,pdf_path')
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
  const inAttesa = preventivi.filter((q) => q.stato === 'inviato')

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

  // la pillola di stato: Prospect o Cliente, lo decide Dre con un clic.
  // «Cliente» usa la stessa scrittura del Foglio (TuttiFoglio.cambiaStato);
  // «Prospect» lo rimette in pipeline, in Conoscitiva.
  async function cambiaStato(s: 'prospect' | 'cliente') {
    if (!p) return
    setStatoAperto(false)
    const adesso = new Date().toISOString()
    const patch = s === 'cliente'
      ? { fuori: true, fuori_at: p.fuori_at ?? adesso, pipeline_stage: 'cliente', contratto: p.contratto ?? 'stable', awaiting_us: false, no_followup: true }
      : { fuori: true, fuori_at: p.fuori_at ?? adesso, pipeline_stage: 'conoscitiva' }
    if (!(await aggiorna(patch as Partial<Prospect>))) return
    const body = s === 'cliente' ? 'DIVENTA CLIENTE.' : 'Torna prospect, in Conoscitiva.'
    const { data } = await supabase.from('interactions')
      .insert({ prospect_id: id, at: adesso, kind: 'nota', body }).select().single()
    if (data) setTimeline((t) => [...t, data as Interaction])   // lo storico la vede subito
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
    await supabase.from('interactions').insert({ prospect_id: id, at: new Date().toISOString(), kind: 'nota', body: `${f.name}, nei Documenti` })
    di(3, `«${file.nome}» nei Documenti`)
  }

  async function salvaReferente() {
    if (!refDraft.nome.trim()) return
    const riga = { prospect_id: id, nome: refDraft.nome.trim(), ruolo: refDraft.ruolo.trim() || null, email: refDraft.email.trim() || null, telefono: refDraft.telefono.trim() || null }
    const { data, error } = await supabase.from('referenti').insert(riga).select('id,nome,ruolo,email,telefono,nota').single()
    if (error || !data) { di(5, 'Il referente non si salva: ' + (error?.message ?? '')); return }
    setReferenti((v) => [...v, data as Referente])
    setRefDraft({ nome: '', ruolo: '', email: '', telefono: '' })
    setNuovoRef(false)
  }

  // lo storico in un testo solo, da scaricare: le stesse tappe della Storia
  function storicoTesto(): string {
    const righe = [
      `${p?.company || p?.name || p?.email} — storico completo, ${fmtDateShort(new Date().toISOString())}`,
      '',
      ...[...timeline.filter((t) => t.kind !== 'postit' && t.kind !== 'prep').map((t) => ({ at: t.at, r: `[${fmtDateShort(t.at)} ${fmtOra(t.at)}] ${t.kind}: ${(t.body ?? '').trim()}` })),
        ...agendaSua.map((a) => ({ at: a.at, r: `[${fmtDateShort(a.at)} ${fmtOra(a.at)}] in calendario: ${a.titolo}` }))]
        .sort((x, y) => x.at.localeCompare(y.at)).map((x) => x.r),
    ]
    return righe.join('\n\n')
  }

  if (completa) return <Scheda key={id} id={id} sezione={sezione} onSezione={onSezione} onClose={onClose} onApri={onApri} />

  if (!p) return (
    <div className="fixed inset-0 z-50">
      <div onClick={onClose} className="absolute inset-0 bg-inchiostro/15" />
      <aside className="scivola absolute inset-y-0 right-0 w-full max-w-[720px] overflow-y-auto border-l border-bordo bg-fondo">
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
  const ultimaChiamata = chiamate[0]

  return (
    <div className="fixed inset-0 z-50">
      <div onClick={onClose} className="absolute inset-0 bg-inchiostro/15" />
      <aside className="scivola absolute inset-y-0 right-0 flex w-full max-w-[720px] flex-col border-l border-bordo bg-fondo">
        <div className="flex items-center gap-3 border-b border-bordo bg-white px-4 py-2.5">
          <button onClick={onClose} className="shrink-0 text-sm font-semibold text-blu hover:underline">‹ Torna</button>
          <Micro>Vault</Micro>
          <span className="min-w-0 flex-1" />
          <Copia testo={linkDi({ tab: 'prospect', id: p.id, sezione: null })} cosa="il link di questo Vault, da mandare a qualcuno">
            <span className="shrink-0 text-[11px] font-semibold text-blu">Link</span>
          </Copia>
          <button onClick={() => setCompleta(true)} className="shrink-0 rounded-full border border-bordo px-3 py-1 text-xs font-bold text-navy hover:border-navy">
            Scheda completa
          </button>
        </div>

        <ZonaFile onFile={accogli} messaggio={`Lascia qui: nei Documenti, agganciato a ${nome}`} className="flex-1 space-y-3 overflow-y-auto px-4 py-4 pb-16 sm:px-5">

          {/* ── la testata: il nome, e lo stato che si clicca ─────── */}
          <div className="flex items-start gap-3 px-1">
            <Faccia p={p} size={44} />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="min-w-0 truncate text-lg font-extrabold">{nome}</h2>
                <button
                  onClick={() => setStatoAperto(!statoAperto)}
                  title="Lo stato: clicca per cambiarlo"
                  className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                    cliente ? 'bg-green-50 text-green-800' : perso ? 'bg-velo text-tenue' : 'bg-amber-50 text-amber-800'}`}
                >
                  {cliente ? 'Cliente' : perso ? 'Perso' : 'Prospect'} {statoAperto ? '▴' : '▾'}
                </button>
                {statoAperto && (['prospect', 'cliente'] as const)
                  .filter((s) => (s === 'cliente') !== cliente || perso)
                  .map((s) => (
                    <button key={s} onClick={() => void cambiaStato(s)}
                            className="rounded-full border border-bordo bg-white px-2.5 py-0.5 text-[11px] font-semibold text-tenue hover:border-blu hover:text-blu">
                      {s === 'cliente' ? 'Cliente' : 'Prospect'}
                    </button>
                  ))}
              </div>
              <p className="mt-0.5 text-[13px] text-tenue">
                {sgid(p.sg_id)}{p.city ? `, ${p.city}` : ''}
                {!cliente && !perso && p.fuori && p.pipeline_stage ? `, in ${PIPELINE_LABEL[p.pipeline_stage as PipelineStage]}` : ''}
              </p>
            </div>
          </div>

          {/* ── Referenti ─────────────────────────────────────────── */}
          <Sez
            titolo="Referenti"
            sommario={p.name ? `${p.name}${p.role ? `, ${p.role}` : ''}${referenti.length ? ` e altri ${referenti.length}` : ''}` : referenti[0]?.nome ?? 'Ancora nessun nome'}
            aperta={aperta === 'referenti'} su={() => setAperta(aperta === 'referenti' ? null : 'referenti')}
          >
            <ul className="divide-y divide-velo">
              {[{ id: 0, nome: p.name ?? '(senza nome)', ruolo: p.role, email: p.email, telefono: p.phone, nota: null } as Referente, ...referenti].map((r) => (
                <li key={r.id} className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 py-2 text-sm">
                  <span className="font-semibold">{r.nome}{r.ruolo ? <span className="font-normal text-tenue">, {r.ruolo}</span> : null}</span>
                  {r.email && <Copia testo={r.email} cosa="l'indirizzo"><span className="text-blu">{r.email}</span></Copia>}
                  {r.telefono && <a href={`tel:${r.telefono}`} className="text-blu hover:underline">{r.telefono}</a>}
                  {r.nota && <span className="text-xs text-spento">{r.nota}</span>}
                </li>
              ))}
            </ul>
            {nuovoRef ? (
              <div className="mt-2 flex flex-wrap gap-2">
                {(['nome', 'ruolo', 'email', 'telefono'] as const).map((k) => (
                  <input key={k} value={refDraft[k]} placeholder={k[0].toUpperCase() + k.slice(1)}
                         onChange={(e) => setRefDraft((d) => ({ ...d, [k]: e.target.value }))}
                         onKeyDown={(e) => { if (e.key === 'Enter') void salvaReferente() }}
                         className="w-[calc(50%-4px)] rounded-lg border border-bordo px-2 py-1.5 text-sm outline-none focus:border-blu sm:w-[150px]" />
                ))}
                <button onClick={() => void salvaReferente()} className="rounded-full bg-blu px-3 py-1.5 text-xs font-bold text-white">Salva</button>
                <button onClick={() => setNuovoRef(false)} className="rounded-full px-2 py-1.5 text-xs font-semibold text-tenue">Annulla</button>
              </div>
            ) : (
              <button onClick={() => setNuovoRef(true)} className="mt-1 text-xs font-bold text-blu hover:underline">+ Referente</button>
            )}
          </Sez>

          {/* ── Preventivi ────────────────────────────────────────── */}
          <Sez
            titolo="Preventivi"
            sommario={preventivi.length === 0 ? 'Nessuno ancora' : `${preventivi.length} in tutto`}
            extra={inAttesa.length > 0 ? <Triangolo n={inAttesa.length} /> : undefined}
            aperta={aperta === 'preventivi'} su={() => setAperta(aperta === 'preventivi' ? null : 'preventivi')}
          >
            {preventivi.length === 0 ? <p className="text-sm text-spento">Nessun preventivo ancora.</p> : (
              <ul className="divide-y divide-velo">
                {preventivi.map((q) => (
                  <li key={q.id} className="flex flex-wrap items-center gap-x-3 gap-y-0.5 py-2 text-sm">
                    {q.stato === 'inviato' && <svg viewBox="0 0 24 24" className="h-[13px] w-[13px] shrink-0 fill-amber-400"><path d="M12 3 22 20H2z" /></svg>}
                    <span className="min-w-0 flex-1 truncate font-semibold">{q.titolo || 'Preventivo'} <span className="font-normal text-spento">{q.numero}</span></span>
                    <span className="font-bold tabular-nums">{q.importo ? `${Number(q.importo).toLocaleString('it-IT')} €` : ''}{q.mensile ? `${q.importo ? ' + ' : ''}${Number(q.mensile).toLocaleString('it-IT')} €/mese` : ''}</span>
                    <span className={`text-[11px] font-semibold ${q.pagato_il ? 'text-green-800' : q.stato === 'accettato' ? 'text-green-800' : q.stato === 'rifiutato' ? 'text-red-700' : q.stato === 'inviato' ? 'text-amber-800' : 'text-tenue'}`}>
                      {q.pagato_il ? `pagato il ${fmtDateShort(q.pagato_il)}` : q.stato === 'inviato' && q.inviato_il ? `aspetta dal ${fmtDateShort(q.inviato_il)}` : q.stato}
                    </span>
                    {q.pdf_path && <Azione su={() => void apriFile(q.pdf_path!)}>PDF</Azione>}
                  </li>
                ))}
              </ul>
            )}
            <button onClick={() => { try { sessionStorage.setItem('preventivo:nuovo', id) } catch { /* niente */ } window.dispatchEvent(new CustomEvent('preventivo:nuovo', { detail: id })) }}
                    className="mt-1 text-xs font-bold text-blu hover:underline">+ Nuovo preventivo</button>
          </Sez>

          {/* ── Chiamate ──────────────────────────────────────────── */}
          <Sez
            titolo="Chiamate"
            sommario={chiamate.length === 0 ? 'Nessuna ancora' : `${chiamate.length}, ultima il ${fmtDateShort(ultimaChiamata.at)}`}
            aperta={aperta === 'chiamate'} su={() => setAperta(aperta === 'chiamate' ? null : 'chiamate')}
          >
            {chiamate.length === 0 ? <p className="text-sm text-spento">Le call con il loro riassunto compaiono qui da sole.</p> : (
              <ul className="divide-y divide-velo">
                {chiamate.map((c) => (
                  <li key={c.chiave} className="py-2">
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                      <span className="w-14 shrink-0 text-xs tabular-nums text-tenue">{fmtDateShort(c.at)}</span>
                      <span className="min-w-0 flex-1 truncate font-semibold">{c.titolo}</span>
                      {c.riassunto && <Azione su={() => setVedo(vedo === c.chiave ? null : c.chiave)}>{vedo === c.chiave ? 'Chiudi' : 'Vedi'}</Azione>}
                      {c.link && <a href={c.link} target="_blank" rel="noreferrer" className="shrink-0 rounded-full border border-bordo px-2.5 py-0.5 text-[11px] font-semibold text-navy hover:border-navy">Appunti</a>}
                      {c.riassunto && <Azione su={() => scarica(`call-${fmtDateShort(c.at).replace(/\//g, '-')}.txt`, `${c.titolo}, ${fmtDateShort(c.at)}\n\n${c.riassunto}`)} tip="Scarica il riassunto">Scarica</Azione>}
                      {c.riassunto && <Azione su={() => void inChat(`Call «${c.titolo}» del ${fmtDateShort(c.at)}, il riassunto:\n${c.riassunto}`)} tip="Manda il riassunto nella chat della squadra">In chat</Azione>}
                    </div>
                    {!c.riassunto && <p className="mt-0.5 pl-[68px] text-xs text-spento">{Date.now() - new Date(c.at).getTime() > 3 * 86400e3 ? 'Senza appunti.' : 'Gli appunti non sono ancora arrivati.'}</p>}
                    {vedo === c.chiave && c.riassunto && (
                      <p className="mt-1.5 whitespace-pre-wrap rounded-lg bg-velo/60 px-3 py-2 text-[13px] leading-snug">{c.riassunto}</p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </Sez>

          {/* ── Documenti ─────────────────────────────────────────── */}
          <Sez
            titolo="Documenti"
            sommario={documenti.length + (p.analysis_pdf ? 1 : 0) === 0 ? 'Niente ancora: trascina qui un file' : `${documenti.length + (p.analysis_pdf ? 1 : 0)} ${documenti.length + (p.analysis_pdf ? 1 : 0) === 1 ? 'documento' : 'documenti'}`}
            aperta={aperta === 'documenti'} su={() => setAperta(aperta === 'documenti' ? null : 'documenti')}
          >
            <ul className="divide-y divide-velo">
              {p.analysis_pdf && (
                <li className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2 text-sm">
                  <span className="min-w-0 flex-1 truncate font-semibold">L'analisi Google Ads</span>
                  <a href={p.analysis_pdf} target="_blank" rel="noreferrer" className="shrink-0 rounded-full border border-bordo px-2.5 py-0.5 text-[11px] font-semibold text-navy hover:border-navy">Apri</a>
                  <Copia testo={p.analysis_pdf} cosa="il link dell'analisi, da mandare al cliente">
                    <span className="shrink-0 rounded-full border border-bordo px-2.5 py-0.5 text-[11px] font-semibold text-tenue">Link</span>
                  </Copia>
                  <Azione su={() => void inChat(`L'analisi di ${nome}: ${p.analysis_pdf}`)} tip="Manda il link nella chat della squadra">In chat</Azione>
                </li>
              )}
              {documenti.map((d) => (
                <li key={d.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2 text-sm">
                  <button onClick={() => void apriFile(d.path)} className="min-w-0 flex-1 truncate text-left text-blu hover:underline">{d.nome}</button>
                  <span className="shrink-0 text-xs text-spento">{fmtDateShort(d.at)}</span>
                  <Azione su={() => void inChat(`«${d.nome}»`, d.id)} tip="Passa il documento nella chat della squadra">In chat</Azione>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-spento">Trascina un file qui dentro: entra nei Documenti col suo titolo, agganciato a {nome}.</p>
          </Sez>

          {/* ── lo storico completo, in fondo ─────────────────────── */}
          <div className="flex flex-wrap items-center gap-2 px-1 pt-1">
            <button onClick={() => setStoriaAperta(true)}
                    className="flex-1 rounded-full border border-bordo py-2 text-xs font-bold text-navy hover:border-navy">
              Visualizza storico completo
            </button>
            <Azione su={() => scarica(`storico-${(nome ?? 'azienda').toLowerCase().replace(/[^a-z0-9]+/g, '-')}.txt`, storicoTesto())} tip="Tutto il rapporto, in un file di testo">Scarica</Azione>
            <Azione su={() => void inChat(`Il fascicolo di ${nome}: ${linkDi({ tab: 'prospect', id: p.id, sezione: null })}`)} tip="Manda il link del Vault nella chat della squadra">In chat</Azione>
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
