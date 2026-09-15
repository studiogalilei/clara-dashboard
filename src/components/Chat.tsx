import { useCallback, useEffect, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'
import { Card, Micro, Spinner, ZonaFile } from './ui'
import { iniziali } from '../lib/profilo'
import { apriFile } from '../lib/file'
import { leggi as leggiPref, scrivi as scriviPref } from '../lib/preferenze'
import CercaAzienda, { CAMPI_AZIENDA, nomeAzienda } from './CercaAzienda'

// LA CHAT DELLA SQUADRA (Dre, 15/9).
//
// «È come un WhatsApp interno: ci si scrive da una dashboard all'altra e ci
// si passano documenti taggando il cliente, così quel documento lo ritrovi
// sempre: nella sezione del cliente, con scritto chi l'ha mandato, e nel
// thread della chat.»
//
// Quindi un messaggio può portarsi dietro due cose: il cliente di cui si
// parla (basta un clic per aprirgli la scheda) e un file, che non vive qui
// ma nei Documenti, nella cartella di quel cliente. La chat è una strada in
// più per arrivare alle stesse cose, non un posto dove si perdono.

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
interface File_ { id: number; nome: string; path: string }

interface Props { onOpen: (id: string) => void }

const TUTTI = 'tutti'
const ora = (iso: string) => new Date(iso).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
const giornoDi = (iso: string) => new Date(iso).toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long' })

export default function Chat({ onOpen }: Props) {
  const [io, setIo] = useState<string | null>(null)
  const [squadra, setSquadra] = useState<Persona[]>([])
  const [righe, setRighe] = useState<Riga[] | null>(null)
  const [con, setCon] = useState<string>(() => leggiPref('chat-con') || TUTTI)
  const [testo, setTesto] = useState('')
  const [cliente, setCliente] = useState<{ id: string; nome: string } | null>(null)
  const [cercoCliente, setCercoCliente] = useState(false)
  const [nomi, setNomi] = useState<Record<string, string>>({})     // aziende taggate
  const [file, setFile] = useState<Record<number, File_>>({})      // documenti condivisi
  const [carico, setCarico] = useState<string | null>(null)
  const [problema, setProblema] = useState<string | null>(null)
  const [apertoElenco, setApertoElenco] = useState(false)          // sul telefono: elenco o thread
  const fondo = useRef<HTMLDivElement | null>(null)
  const scegliFile = useRef<HTMLInputElement>(null)

  useEffect(() => {
    void supabase.auth.getSession().then(({ data }) => setIo(data.session?.user?.id ?? null))
    void supabase.from('profili').select('id,nome,ruolo').order('nome')
      .then(({ data }) => setSquadra((data as Persona[]) ?? []))
  }, [])

  const carica = useCallback(() => {
    void supabase.from('chat').select('*').order('at', { ascending: true }).limit(500)
      .then(({ data, error }) => {
        if (error) { setProblema(`La chat non si legge: ${error.message}`); return }
        setRighe((data as Riga[]) ?? [])
      })
  }, [])

  useEffect(() => {
    carica()
    const t = setInterval(carica, 7000)
    return () => clearInterval(t)
  }, [carica])

  // i nomi delle aziende taggate e i documenti condivisi: una domanda sola
  useEffect(() => {
    const idAziende = [...new Set((righe ?? []).map((r) => r.prospect_id).filter(Boolean) as string[])]
      .filter((id) => !nomi[id])
    if (idAziende.length) {
      void supabase.from('prospects').select(CAMPI_AZIENDA).in('id', idAziende).limit(200)
        .then(({ data }) => setNomi((m) => {
          const out = { ...m }
          for (const a of ((data as Array<{ id: string }>) ?? [])) out[a.id] = nomeAzienda(a as never)
          return out
        }))
    }
    const idFile = [...new Set((righe ?? []).map((r) => r.file_id).filter(Boolean) as number[])]
      .filter((id) => !file[id])
    if (idFile.length) {
      void supabase.from('vault_file').select('id,nome,path').in('id', idFile).limit(200)
        .then(({ data }) => setFile((m) => {
          const out = { ...m }
          for (const f of ((data as File_[]) ?? [])) out[f.id] = f
          return out
        }))
    }
  }, [righe])   // eslint-disable-line react-hooks/exhaustive-deps

  // la conversazione aperta, in ordine
  const dentro = (r: Riga) => (con === TUTTI ? r.a === null : (r.da === con && r.a === io) || (r.da === io && r.a === con))
  const conversazione = (righe ?? []).filter(dentro)

  useEffect(() => { fondo.current?.scrollIntoView({ block: 'end' }) }, [conversazione.length, con])

  // segno letto quello che ho appena guardato
  useEffect(() => {
    if (!io || con === TUTTI) return
    const daSegnare = conversazione.filter((r) => r.a === io && !r.letto).map((r) => r.id)
    if (daSegnare.length === 0) return
    void supabase.from('chat').update({ letto: true }).in('id', daSegnare)
      .then(() => setRighe((v) => (v ?? []).map((r) => (daSegnare.includes(r.id) ? { ...r, letto: true } : r))))
  }, [conversazione, con, io])

  // la stanza comune non ha il letto per ognuno: basta ricordare l'ultima visita
  useEffect(() => {
    if (con !== TUTTI) return
    scriviPref('chat-visto', new Date().toISOString())
  }, [con, conversazione.length])

  function apri(chi: string) {
    setCon(chi)
    scriviPref('chat-con', chi)
    setApertoElenco(false)
  }

  const nonLetti = (chi: string) => {
    if (chi === TUTTI) {
      const visto = leggiPref('chat-visto') || ''
      return (righe ?? []).filter((r) => r.a === null && r.da !== io && r.at > visto).length
    }
    return (righe ?? []).filter((r) => r.da === chi && r.a === io && !r.letto).length
  }

  async function manda(f?: File) {
    const t = testo.trim()
    if (!t && !f) return
    setProblema(null)
    let file_id: number | null = null

    if (f) {
      // il documento va nei Documenti: nella cartella del cliente se c'e' il
      // tag, se no fra i documenti interni. Nella chat resta il riferimento.
      setCarico(f.name)
      const nomeFile = f.name.replace(/[^a-zA-Z0-9._-]+/g, '-')
      const cartella = cliente ? `clienti/${cliente.id}` : 'azienda'
      const path = `${cartella}/${Date.now()}-${nomeFile}`
      const { error } = await supabase.storage.from('vault').upload(path, f)
      if (error) { setProblema(`Non sono riuscito a caricare «${f.name}»: ${error.message}`); setCarico(null); return }
      const { data, error: e2 } = await supabase.from('vault_file').insert({
        nome: f.name.replace(/\.[^.]+$/, ''), path, mime: f.type || null, dimensione: f.size,
        prospect_id: cliente?.id ?? null,
        sezione: cliente ? 'clienti' : 'azienda',
        nota: `Condiviso in chat da ${nomeDi(io)}`,
      }).select('id,nome,path').single()
      setCarico(null)
      if (e2 || !data) { setProblema(`Il file è salito ma non l'ho registrato: ${e2?.message ?? ''}`); return }
      file_id = (data as File_).id
      setFile((m) => ({ ...m, [(data as File_).id]: data as File_ }))
    }

    const riga = {
      // `da` ce l'ha anche il database come valore di partenza, ma scriverlo
      // qui serve a chi guarda subito dopo aver premuto Manda
      da: io,
      a: con === TUTTI ? null : con,
      testo: t || null,
      prospect_id: cliente?.id ?? null,
      file_id,
    }
    const { data, error } = await supabase.from('chat').insert(riga).select().single()
    if (error || !data) { setProblema(`Non è partito: ${error?.message ?? 'riprova'}`); return }
    setRighe((v) => [...(v ?? []), data as Riga])
    setTesto('')
    setCliente(null)
  }

  function nomeDi(id: string | null): string {
    if (!id) return 'qualcuno'
    const p = squadra.find((x) => x.id === id)
    return p?.nome ?? 'qualcuno'
  }

  if (righe === null) return <Spinner />

  const altri = squadra.filter((p) => p.id !== io)
  const conNome = con === TUTTI ? 'Tutta la squadra' : nomeDi(con)

  const elenco = (
    <div className="space-y-1">
      {[{ id: TUTTI, nome: 'Tutta la squadra', ruolo: `${squadra.length} persone` }, ...altri].map((p) => {
        const n = nonLetti(p.id)
        const acceso = con === p.id
        return (
          <button key={p.id} onClick={() => apri(p.id)}
                  className={`flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-left ${acceso ? 'bg-velo' : 'hover:bg-velo/60'}`}>
            <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${
              p.id === TUTTI ? 'bg-navy text-white' : 'bg-blu/10 text-navy'}`}>
              {p.id === TUTTI ? 'SG' : iniziali(p.nome ?? '?')}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-semibold">{p.nome ?? 'senza nome'}</span>
              <span className="block truncate text-[11px] text-spento">{p.ruolo}</span>
            </span>
            {n > 0 && <span className="shrink-0 rounded-full bg-red-600 px-1.5 py-px text-[10px] font-bold text-white">{n}</span>}
          </button>
        )
      })}
    </div>
  )

  const bolla = (r: Riga, mia: boolean) => (
    <div key={r.id} className={`flex ${mia ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[82%] rounded-2xl px-3.5 py-2 ${mia ? 'bg-blu text-white' : 'bg-velo'}`}>
        {!mia && con === TUTTI && (
          <p className="mb-0.5 text-[11px] font-bold text-navy">{nomeDi(r.da)}</p>
        )}
        {r.prospect_id && (
          <button onClick={() => onOpen(r.prospect_id!)}
                  className={`mb-1 inline-block rounded-full px-2 py-0.5 text-[11px] font-bold ${
                    mia ? 'bg-white/20 text-white' : 'bg-white text-navy'}`}>
            {nomi[r.prospect_id] ?? 'azienda'}
          </button>
        )}
        {r.testo && <p className="whitespace-pre-wrap text-[13px] leading-snug">{r.testo}</p>}
        {r.file_id && file[r.file_id] && (
          <button onClick={() => void apriFile(file[r.file_id!].path)}
                  className={`mt-1 flex items-center gap-1.5 rounded-lg px-2 py-1 text-[12px] font-semibold ${
                    mia ? 'bg-white/20 text-white' : 'bg-white text-navy'}`}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-3.5 w-3.5">
              <path d="M7 3h7l5 5v13H7zM14 3v5h5" />
            </svg>
            {file[r.file_id].nome}
          </button>
        )}
        <p className={`mt-0.5 text-right text-[10px] ${mia ? 'text-white/60' : 'text-spento'}`}>{ora(r.at)}</p>
      </div>
    </div>
  )

  let ultimoGiorno = ''

  return (
    <div className="pb-24 sm:pb-8">
      {problema && (
        <div className="mb-3 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <span className="flex-1">{problema}</span>
          <button onClick={() => setProblema(null)} className="shrink-0 text-xs font-bold text-red-600">Chiudi</button>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)]">
        <Card className={`p-2 ${apertoElenco ? '' : 'hidden lg:block'}`}>{elenco}</Card>

        <Card className={`flex min-h-[60vh] flex-col ${apertoElenco ? 'hidden lg:flex' : ''}`}>
          <header className="flex items-center gap-2 border-b border-velo px-4 py-2.5">
            <button onClick={() => setApertoElenco(true)} className="text-sm font-semibold text-blu lg:hidden">‹</button>
            <span className="text-[15px] font-extrabold">{conNome}</span>
            <Micro className="ml-auto">{conversazione.length}</Micro>
          </header>

          <ZonaFile onFile={(f) => void manda(f)} messaggio="Lascia qui: lo mando e finisce nei Documenti"
                    className="min-h-0 flex-1 space-y-2 overflow-y-auto px-4 py-3">
            {conversazione.length === 0 && (
              <p className="py-10 text-center text-sm text-spento">Ancora niente.</p>
            )}
            {conversazione.map((r) => {
              const g = giornoDi(r.at)
              const nuovo = g !== ultimoGiorno
              ultimoGiorno = g
              return (
                <div key={r.id} className="space-y-2">
                  {nuovo && <p className="py-1 text-center text-[11px] font-semibold text-spento">{g}</p>}
                  {bolla(r, r.da === io)}
                </div>
              )
            })}
            <div ref={fondo} />
          </ZonaFile>

          <div className="border-t border-velo px-3 py-2.5">
            {cliente && (
              <div className="mb-1.5 flex items-center gap-2">
                <span className="rounded-full bg-blu/10 px-2.5 py-1 text-[11px] font-bold text-navy">{cliente.nome}</span>
                <button onClick={() => setCliente(null)} className="text-[11px] text-spento hover:text-inchiostro">Togli il tag</button>
              </div>
            )}
            {cercoCliente && (
              <div className="mb-2">
                <CercaAzienda placeholder="Di quale cliente si parla?"
                              onScegli={(a) => { setCliente({ id: a.id, nome: nomeAzienda(a) }); setCercoCliente(false) }} />
              </div>
            )}
            <div className="flex items-end gap-2">
              <button onClick={() => setCercoCliente((v) => !v)} title="Tagga un cliente"
                      className="shrink-0 rounded-full border border-bordo px-2.5 py-1.5 text-xs font-bold text-tenue hover:border-navy hover:text-navy">
                @
              </button>
              <button onClick={() => scegliFile.current?.click()} title="Allega un documento" disabled={!!carico}
                      className="shrink-0 rounded-full border border-bordo px-2.5 py-1.5 text-tenue hover:border-navy hover:text-navy disabled:opacity-40">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4">
                  <path d="M21.4 11.1 12.3 20a5 5 0 0 1-7.1-7.1l9.2-9.2a3.3 3.3 0 1 1 4.7 4.7l-9.2 9.2a1.7 1.7 0 0 1-2.4-2.4l8.5-8.5" />
                </svg>
              </button>
              <input ref={scegliFile} type="file" className="hidden"
                     onChange={(e) => { const f = e.target.files?.[0]; if (f) void manda(f); e.target.value = '' }} />
              <textarea
                value={testo}
                onChange={(e) => setTesto(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void manda() } }}
                rows={1}
                placeholder={carico ? `Carico ${carico}…` : `Scrivi a ${con === TUTTI ? 'tutti' : conNome.split(' ')[0]}…`}
                className="min-h-[38px] flex-1 resize-none rounded-xl border border-bordo px-3 py-2 text-sm outline-none focus:border-blu"
              />
              <button onClick={() => void manda()} disabled={!testo.trim() && !carico}
                      className="shrink-0 rounded-full bg-blu px-4 py-2 text-sm font-bold text-white hover:bg-blu-scuro disabled:opacity-30">
                Manda
              </button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
