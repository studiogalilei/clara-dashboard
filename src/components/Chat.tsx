import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'
import { Card, Micro, Spinner, ZonaFile, fmtNum } from './ui'
import { useVivo } from '../lib/vivo'
import { iniziali } from '../lib/profilo'
import { apriFile } from '../lib/file'
import { leggi as leggiPref, scrivi as scriviPref } from '../lib/preferenze'
import CercaAzienda, { CAMPI_AZIENDA, nomeAzienda, indizio } from './CercaAzienda'

// CONDIVIDI (Dre, 15/9).
//
// «Voglio che sia come una chat con i thread, ma il tema è che lì invii
// documenti, non stai a chattare tutto il giorno. Uno fa drag and drop,
// esce da sola la barra di ricerca dei clienti, cerca quello che gli
// interessa, seleziona e invia. Le azioni devono essere come le fa Google:
// l'app sa già quello che vuoi fare e te lo rende stra easy.»
//
// Quindi: i thread ci sono (con tutti, o con una persona), ma il gesto
// principale è lasciare cadere un file. Appena cade, la ricerca del cliente
// si apre da sola, gia' scritta col nome che si legge dentro il file, e con
// Invio parte. Ogni thread ha «Tutte le condivisioni», che è la stessa roba
// senza le chiacchiere in mezzo.
//
// Il documento non vive qui: sale nei Documenti, nella cartella di quel
// cliente, con scritto chi l'ha passato. Questo è il motivo di tutto: su
// WhatsApp i documenti si perdono, qui si ritrovano da due strade.

interface Riga {
  id: number
  at: string
  da: string
  a: string | null
  testo: string | null
  prospect_id: string | null
  file_id: number | null
  letto: boolean
}
interface Persona { id: string; nome: string | null; ruolo: string }
interface File_ { id: number; nome: string; path: string; dimensione: number | null; mime: string | null }

interface Props { onOpen: (id: string) => void }

const TUTTI = 'tutti'
const ora = (iso: string) => new Date(iso).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
const giornoDi = (iso: string) => {
  const d = new Date(iso)
  const g = Math.round((Date.now() - d.getTime()) / 86400e3)
  if (g === 0) return 'oggi'
  if (g === 1) return 'ieri'
  return d.toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long' })
}
const estensione = (path: string) => (path.split('.').pop() ?? '').toUpperCase().slice(0, 4)

export default function Chat({ onOpen }: Props) {
  const [io, setIo] = useState<string | null>(null)
  const [squadra, setSquadra] = useState<Persona[]>([])
  const [righe, setRighe] = useState<Riga[] | null>(null)
  const [file, setFile] = useState<Record<number, File_>>({})
  const [nomi, setNomi] = useState<Record<string, string>>({})
  const [con, setCon] = useState<string>(() => leggiPref('chat-con') || TUTTI)
  const [soloCondivisioni, setSoloCondivisioni] = useState(false)
  const [elencoAperto, setElencoAperto] = useState(false)   // sul telefono
  const [problema, setProblema] = useState<string | null>(null)

  // quello che sta per partire
  const [scelto, setScelto] = useState<File | null>(null)
  const [cliente, setCliente] = useState<{ id: string; nome: string } | null>(null)
  const [testo, setTesto] = useState('')
  const [mando, setMando] = useState(false)
  const [daThread, setDaThread] = useState(false)   // il cliente e' una proposta, non una scelta

  const fondo = useRef<HTMLDivElement | null>(null)
  const input = useRef<HTMLInputElement>(null)
  const scrivi = useRef<HTMLTextAreaElement | null>(null)

  useEffect(() => {
    void supabase.auth.getSession().then(({ data }) => setIo(data.session?.user?.id ?? null))
    void supabase.from('profili').select('id,nome,ruolo').order('nome')
      .then(({ data }) => setSquadra((data as Persona[]) ?? []))
  }, [])

  const carica = useCallback(() => {
    void supabase.from('chat').select('*').order('at', { ascending: true }).limit(500)
      .then(({ data, error }) => {
        if (error) { setProblema(`Le condivisioni non si leggono: ${error.message}`); return }
        setRighe((data as Riga[]) ?? [])
      })
  }, [])

  useEffect(() => {
    carica()
    // la rete di sicurezza: il vivo fa il lavoro, questo copre i buchi
    const t = setInterval(carica, 60_000)
    return () => clearInterval(t)
  }, [carica])
  // i documenti passati arrivano mentre li mandano, senza ricaricare
  useVivo(['chat'], carica)

  useEffect(() => {
    const idFile = [...new Set((righe ?? []).map((r) => r.file_id).filter(Boolean) as number[])].filter((i) => !file[i])
    if (idFile.length) {
      void supabase.from('vault_file').select('id,nome,path,dimensione,mime').in('id', idFile).limit(300)
        .then(({ data }) => setFile((m) => {
          const out = { ...m }
          for (const f of ((data as File_[]) ?? [])) out[f.id] = f
          return out
        }))
    }
    const idAz = [...new Set((righe ?? []).map((r) => r.prospect_id).filter(Boolean) as string[])].filter((i) => !nomi[i])
    if (idAz.length) {
      void supabase.from('prospects').select(CAMPI_AZIENDA).in('id', idAz).limit(300)
        .then(({ data }) => setNomi((m) => {
          const out = { ...m }
          for (const a of ((data as Array<{ id: string }>) ?? [])) out[a.id] = nomeAzienda(a as never)
          return out
        }))
    }
  }, [righe])   // eslint-disable-line react-hooks/exhaustive-deps

  const nomeDi = useCallback((id: string | null) => (
    id ? (squadra.find((p) => p.id === id)?.nome ?? 'qualcuno') : 'tutta la squadra'
  ), [squadra])

  const dentro = useCallback((r: Riga) => (
    con === TUTTI ? r.a === null : (r.da === con && r.a === io) || (r.da === io && r.a === con)
  ), [con, io])

  const conversazione = useMemo(() => (righe ?? []).filter(dentro), [righe, dentro])
  const condivisioni = useMemo(() => conversazione.filter((r) => r.file_id), [conversazione])

  useEffect(() => { fondo.current?.scrollIntoView({ block: 'end' }) }, [conversazione.length, con, soloCondivisioni])

  // quello che leggi si segna letto, senza che tu faccia niente
  useEffect(() => {
    if (!io) return
    const daSegnare = conversazione.filter((r) => r.a === io && !r.letto).map((r) => r.id)
    if (daSegnare.length === 0) return
    void supabase.from('chat').update({ letto: true }).in('id', daSegnare)
      .then(() => setRighe((v) => (v ?? []).map((r) => (daSegnare.includes(r.id) ? { ...r, letto: true } : r))))
  }, [conversazione, io])

  // il cliente di cui si sta parlando in questo thread: se ne hai appena
  // mandato uno, e' quasi sempre lo stesso. Si propone, non si decide.
  const ultimoCliente = useMemo(() => {
    const r = [...conversazione].reverse().find((x) => x.prospect_id)
    return r?.prospect_id ? { id: r.prospect_id, nome: nomi[r.prospect_id] ?? 'cliente' } : null
  }, [conversazione, nomi])

  function prendi(f: File) {
    setScelto(f)
    setProblema(null)
    setSoloCondivisioni(false)
    // quello che si legge nel nome del file vince su tutto: se il file si
    // chiama «contratto-klavzar.pdf» non si propone il cliente di cui si
    // parlava prima, si apre la ricerca gia' scritta su Klavzar. Solo se il
    // nome non dice niente si propone l'ultimo cliente del thread, e lo si
    // dice («come l'ultimo»), cosi' nessuno manda un contratto nella
    // cartella sbagliata senza accorgersene.
    const ind = indizio(f.name)
    if (ind) { setCliente(null); setDaThread(false); return }
    if (!cliente && ultimoCliente) { setCliente(ultimoCliente); setDaThread(true) }
  }

  function apriElenco(chi: string) {
    setCon(chi)
    scriviPref('chat-con', chi)
    setElencoAperto(false)
    setSoloCondivisioni(false)
  }

  const nonLetti = (chi: string) => (righe ?? []).filter((r) => (
    chi === TUTTI ? r.a === null && r.da !== io && !r.letto : r.da === chi && r.a === io && !r.letto
  )).length

  async function manda() {
    const t = testo.trim()
    if (!scelto && !t) return
    if (scelto && !cliente) { setProblema('Di quale prospect o cliente è? Serve per ritrovarlo dopo.'); return }
    setMando(true)
    setProblema(null)
    let file_id: number | null = null

    if (scelto) {
      const nomeFile = scelto.name.replace(/[^a-zA-Z0-9._-]+/g, '-')
      const path = `clienti/${cliente!.id}/${Date.now()}-${nomeFile}`
      const { error } = await supabase.storage.from('vault').upload(path, scelto)
      if (error) { setProblema(`Non sono riuscito a caricare «${scelto.name}»: ${error.message}`); setMando(false); return }
      const { data: f, error: e2 } = await supabase.from('vault_file').insert({
        nome: scelto.name.replace(/\.[^.]+$/, ''), path, mime: scelto.type || null, dimensione: scelto.size,
        prospect_id: cliente!.id, sezione: 'clienti',
        nota: `Condiviso da ${nomeDi(io)}${t ? `: ${t}` : ''}`,
      }).select('id,nome,path,dimensione,mime').single()
      if (e2 || !f) {
        await supabase.storage.from('vault').remove([path])
        setProblema(`Il file è salito ma non l'ho registrato: ${e2?.message ?? ''}`)
        setMando(false); return
      }
      file_id = (f as File_).id
      setFile((m) => ({ ...m, [(f as File_).id]: f as File_ }))
    }

    const { data, error } = await supabase.from('chat').insert({
      da: io,
      a: con === TUTTI ? null : con,
      testo: t || null,
      prospect_id: scelto ? cliente!.id : (cliente?.id ?? null),
      file_id,
    }).select().single()
    setMando(false)
    if (error || !data) { setProblema(`Non è partito: ${error?.message ?? 'riprova'}`); return }
    setRighe((v) => [...(v ?? []), data as Riga])
    setTesto(''); setScelto(null); setDaThread(false)
    // il cliente resta: di solito se ne mandano due di fila dello stesso
  }

  async function apriIl(r: Riga) {
    const f = r.file_id ? file[r.file_id] : null
    if (!f) return
    if (!(await apriFile(f.path))) setProblema('Il file non si apre: riprova fra un istante')
  }

  if (righe === null) return <Spinner />

  const altri = squadra.filter((p) => p.id !== io)
  const conNome = con === TUTTI ? 'Tutta la squadra' : nomeDi(con)

  const elenco = (
    <div className="space-y-0.5">
      {[{ id: TUTTI, nome: 'Tutta la squadra', ruolo: `${squadra.length} persone` }, ...altri].map((p) => {
        const n = nonLetti(p.id)
        const acceso = con === p.id
        const suoi = (righe ?? []).filter((r) => (p.id === TUTTI ? r.a === null : (r.da === p.id && r.a === io) || (r.da === io && r.a === p.id)))
        const ultimo = suoi[suoi.length - 1]
        return (
          <button key={p.id} onClick={() => apriElenco(p.id)}
                  className={`flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-left ${acceso ? 'bg-velo' : 'hover:bg-velo/60'}`}>
            <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${
              p.id === TUTTI ? 'bg-navy text-white' : 'bg-blu/10 text-navy'}`}>
              {p.id === TUTTI ? 'SG' : iniziali(p.nome ?? '?')}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-semibold">{p.nome ?? 'senza nome'}</span>
              <span className="block truncate text-[11px] text-spento">
                {ultimo
                  ? `${ultimo.file_id ? 'documento, ' : ''}${ultimo.prospect_id ? (nomi[ultimo.prospect_id] ?? '') : (ultimo.testo ?? '')}`.slice(0, 34) || 'una condivisione'
                  : p.ruolo}
              </span>
            </span>
            {n > 0 && <span className="shrink-0 rounded-full bg-red-600 px-1.5 py-px text-[10px] font-bold text-white">{n}</span>}
          </button>
        )
      })}
    </div>
  )

  const cartaFile = (r: Riga, mia: boolean) => {
    const f = r.file_id ? file[r.file_id] : null
    if (!f) return null
    return (
      <button onClick={() => void apriIl(r)}
              className={`mt-1 flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-left ${
                mia ? 'bg-white/15 hover:bg-white/25' : 'bg-white hover:bg-velo'}`}>
        <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-[10px] font-bold ${
          mia ? 'bg-white/20 text-white' : 'bg-velo text-navy'}`}>
          {estensione(f.path)}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[13px] font-semibold">{f.nome}</span>
          <span className={`block text-[11px] ${mia ? 'text-white/70' : 'text-spento'}`}>
            {f.dimensione ? `${fmtNum(Math.round(f.dimensione / 1024))} KB, ` : ''}apri
          </span>
          {/* Documenti e Condividi sono lo stesso posto visto da due porte:
              qui si dice dove il file e' finito, se no sembrano due archivi
              diversi e nessuno sa quale guardare (16/9) */}
          {r.prospect_id && (
            <span className={`block text-[11px] ${mia ? 'text-white/60' : 'text-spento'}`}>
              è nella cartella di {nomi[r.prospect_id] ?? 'quel cliente'}, in Documenti
            </span>
          )}
        </span>
      </button>
    )
  }

  let ultimoGiorno = ''

  return (
    <div className="pb-24 sm:pb-8">
      {problema && (
        <div className="mb-3 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <span className="flex-1">{problema}</span>
          <button onClick={() => setProblema(null)} className="shrink-0 text-xs font-bold text-red-600">Chiudi</button>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[250px_minmax(0,1fr)]">
        <Card className={`p-2 ${elencoAperto ? '' : 'hidden lg:block'}`}>{elenco}</Card>

        <Card className={`flex min-h-[64vh] flex-col ${elencoAperto ? 'hidden lg:flex' : ''}`}>
          <header className="flex items-center gap-2 border-b border-velo px-4 py-2.5">
            <button onClick={() => setElencoAperto(true)} className="text-sm font-semibold text-blu lg:hidden">‹</button>
            <span className="text-[15px] font-extrabold">{conNome}</span>
            <button onClick={() => setSoloCondivisioni((v) => !v)}
                    className={`ml-auto rounded-full px-3 py-1 text-xs font-semibold ${
                      soloCondivisioni ? 'bg-navy text-white' : 'text-blu hover:bg-velo'}`}>
              {soloCondivisioni ? 'Torna al thread' : `Tutte le condivisioni, ${condivisioni.length}`}
            </button>
          </header>

          {/* il thread, o solo i documenti: due viste della stessa cosa */}
          <ZonaFile onFile={prendi} messaggio="Lascia andare: ti chiedo solo di chi è"
                    className="min-h-0 flex-1 space-y-2 overflow-y-auto px-4 py-3">
            {soloCondivisioni ? (
              condivisioni.length === 0
                ? <p className="py-12 text-center text-sm text-spento">Nessun documento ancora.</p>
                : [...condivisioni].reverse().map((r) => {
                    const f = r.file_id ? file[r.file_id] : null
                    return (
                      <div key={r.id} className="flex items-center gap-3 rounded-xl border border-bordo px-3 py-2">
                        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-velo text-[10px] font-bold text-navy">
                          {f ? estensione(f.path) : '?'}
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-[13px] font-semibold">{f?.nome ?? 'documento'}</span>
                          <span className="block truncate text-[11px] text-spento">
                            {r.da === io ? 'tu' : nomeDi(r.da)}, {giornoDi(r.at)}
                            {r.testo ? `, ${r.testo}` : ''}
                          </span>
                        </span>
                        {r.prospect_id && (
                          <button onClick={() => onOpen(r.prospect_id!)}
                                  className="shrink-0 rounded-full bg-blu/10 px-2 py-0.5 text-[11px] font-bold text-navy hover:bg-blu/20">
                            {nomi[r.prospect_id] ?? 'cliente'}
                          </button>
                        )}
                        <button onClick={() => void apriIl(r)}
                                className="shrink-0 rounded-full border border-bordo px-3 py-1 text-xs font-bold text-navy hover:border-navy">
                          Apri
                        </button>
                      </div>
                    )
                  })
            ) : conversazione.length === 0 ? (
              <div className="py-12 text-center">
                <p className="text-sm text-spento">Trascina qui un documento per mandarlo a {conNome.toLowerCase()}.</p>
              </div>
            ) : (
              conversazione.map((r) => {
                const mia = r.da === io
                const g = giornoDi(r.at)
                const nuovo = g !== ultimoGiorno
                ultimoGiorno = g
                return (
                  <div key={r.id} className="space-y-2">
                    {nuovo && <p className="py-1 text-center text-[11px] font-semibold text-spento">{g}</p>}
                    <div className={`flex ${mia ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[80%] rounded-2xl px-3.5 py-2 ${mia ? 'bg-blu text-white' : 'bg-velo'}`}>
                        {!mia && con === TUTTI && <p className="mb-0.5 text-[11px] font-bold text-navy">{nomeDi(r.da)}</p>}
                        {r.prospect_id && (
                          <button onClick={() => onOpen(r.prospect_id!)}
                                  className={`mb-1 inline-block rounded-full px-2 py-0.5 text-[11px] font-bold ${
                                    mia ? 'bg-white/20 text-white' : 'bg-white text-navy'}`}>
                            {nomi[r.prospect_id] ?? 'cliente'}
                          </button>
                        )}
                        {r.testo && <p className="whitespace-pre-wrap text-[13px] leading-snug">{r.testo}</p>}
                        {cartaFile(r, mia)}
                        <p className={`mt-0.5 text-right text-[10px] ${mia ? 'text-white/60' : 'text-spento'}`}>{ora(r.at)}</p>
                      </div>
                    </div>
                  </div>
                )
              })
            )}
            <div ref={fondo} />
          </ZonaFile>

          {/* IL GESTO: il file, e subito «di chi è» */}
          <div className="border-t border-velo px-3 py-2.5">
            {scelto && (
              <div className="mb-2 space-y-2 rounded-xl bg-velo/70 p-2.5">
                <div className="flex items-center gap-2">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white text-[10px] font-bold text-navy">
                    {estensione(scelto.name)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[13px] font-semibold">{scelto.name}</span>
                    <span className="block text-[11px] text-spento">{fmtNum(Math.round(scelto.size / 1024))} KB</span>
                  </span>
                  <button onClick={() => setScelto(null)} className="shrink-0 text-xs font-semibold text-spento hover:text-inchiostro">Togli</button>
                </div>
                {cliente ? (
                  <div className="flex items-center gap-2">
                    <Micro>Di</Micro>
                    <span className="rounded-full bg-blu/10 px-2.5 py-1 text-[11px] font-bold text-navy">{cliente.nome}</span>
                    {daThread && <span className="text-[11px] text-spento">come l'ultimo</span>}
                    <button onClick={() => { setCliente(null); setDaThread(false) }} className="text-[11px] font-semibold text-blu hover:underline">Cambia</button>
                  </div>
                ) : (
                  <CercaAzienda
                    sopra
                    dentro
                    iniziale={indizio(scelto.name)}
                    placeholder="Di quale prospect o cliente è?"
                    onScegli={(a) => {
                      setCliente({ id: a.id, nome: nomeAzienda(a) })
                      setDaThread(false)
                      setTimeout(() => scrivi.current?.focus(), 30)
                    }}
                  />
                )}
              </div>
            )}
            <div className="flex items-end gap-2">
              <button onClick={() => input.current?.click()} title="Manda un documento"
                      className="shrink-0 rounded-full border border-bordo px-2.5 py-1.5 text-tenue hover:border-navy hover:text-navy">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4">
                  <path d="M21.4 11.1 12.3 20a5 5 0 0 1-7.1-7.1l9.2-9.2a3.3 3.3 0 1 1 4.7 4.7l-9.2 9.2a1.7 1.7 0 0 1-2.4-2.4l8.5-8.5" />
                </svg>
              </button>
              <input ref={input} type="file" className="hidden"
                     onChange={(e) => { const f = e.target.files?.[0]; if (f) prendi(f); e.target.value = '' }} />
              <textarea
                ref={scrivi}
                value={testo}
                onChange={(e) => setTesto(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void manda() } }}
                rows={1}
                placeholder={scelto ? 'Cosa deve farci, in una riga' : `Scrivi a ${con === TUTTI ? 'tutti' : conNome.split(' ')[0]}, o trascina un documento`}
                className="min-h-[38px] flex-1 resize-none rounded-xl border border-bordo px-3 py-2 text-sm outline-none focus:border-blu"
              />
              <button onClick={() => void manda()} disabled={mando || (!testo.trim() && !scelto)}
                      className="shrink-0 rounded-full bg-blu px-4 py-2 text-sm font-bold text-white hover:bg-blu-scuro disabled:opacity-30">
                {mando ? 'Mando…' : 'Manda'}
              </button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
