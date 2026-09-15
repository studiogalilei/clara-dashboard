import { useCallback, useEffect, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'
import { Card, Micro, Spinner, ZonaFile, fmtNum } from './ui'
import { iniziali } from '../lib/profilo'
import { apriFile } from '../lib/file'
import CercaAzienda, { CAMPI_AZIENDA, nomeAzienda } from './CercaAzienda'

// I PASSAGGI (Dre, 15/9).
//
// «Il mood non è conversazionale: è il luogo per mandare documenti. Tanto
// abbiamo WhatsApp e lì ci parliamo, ma i documenti poi si perdono.»
//
// Quindi qui non si chiacchiera: si passa un file a qualcuno, si dice cosa
// deve farci, e si lega al cliente. Il file non vive qui: sale nei Documenti,
// nella cartella di quel cliente, con scritto chi l'ha mandato. Così lo
// ritrovi da due strade, e nessuno deve cercarlo in una conversazione.

interface Riga {
  id: number
  at: string
  da: string
  a: string | null           // null = a tutta la squadra
  testo: string | null       // la descrizione: cosa deve farci chi lo riceve
  prospect_id: string | null
  file_id: number | null
  letto: boolean
}
interface Persona { id: string; nome: string | null; ruolo: string }
interface File_ { id: number; nome: string; path: string; dimensione: number | null; mime: string | null }

interface Props { onOpen: (id: string) => void }

type Filtro = 'tutti' | 'me' | 'miei'
const FILTRI: Array<[Filtro, string]> = [['tutti', 'Tutti'], ['me', 'Per me'], ['miei', 'Mandati da me']]

const quando = (iso: string) => {
  const d = new Date(iso)
  const giorni = Math.round((Date.now() - d.getTime()) / 86400e3)
  const ora = d.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
  if (giorni === 0) return `oggi alle ${ora}`
  if (giorni === 1) return `ieri alle ${ora}`
  return d.toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })
}
const estensione = (path: string) => (path.split('.').pop() ?? '').toUpperCase().slice(0, 4)

export default function Chat({ onOpen }: Props) {
  const [io, setIo] = useState<string | null>(null)
  const [squadra, setSquadra] = useState<Persona[]>([])
  const [righe, setRighe] = useState<Riga[] | null>(null)
  const [file, setFile] = useState<Record<number, File_>>({})
  const [nomi, setNomi] = useState<Record<string, string>>({})
  const [filtro, setFiltro] = useState<Filtro>('tutti')
  const [cerca, setCerca] = useState('')
  const [problema, setProblema] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)

  // quello che sto per mandare
  const [scelto, setScelto] = useState<File | null>(null)
  const [cliente, setCliente] = useState<{ id: string; nome: string } | null>(null)
  const [aChi, setAChi] = useState<string>('tutti')
  const [descrizione, setDescrizione] = useState('')
  const [mando, setMando] = useState(false)
  const input = useRef<HTMLInputElement>(null)

  useEffect(() => {
    void supabase.auth.getSession().then(({ data }) => setIo(data.session?.user?.id ?? null))
    void supabase.from('profili').select('id,nome,ruolo').order('nome')
      .then(({ data }) => setSquadra((data as Persona[]) ?? []))
  }, [])

  const carica = useCallback(() => {
    void supabase.from('chat').select('*').order('at', { ascending: false }).limit(300)
      .then(({ data, error }) => {
        if (error) { setProblema(`I passaggi non si leggono: ${error.message}`); return }
        setRighe((data as Riga[]) ?? [])
      })
  }, [])

  useEffect(() => {
    carica()
    const t = setInterval(carica, 20_000)
    return () => clearInterval(t)
  }, [carica])

  // i file e i nomi delle aziende: una domanda sola, non una per riga
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

  const nomeDi = (id: string | null) => (id ? (squadra.find((p) => p.id === id)?.nome ?? 'qualcuno') : 'tutta la squadra')

  async function manda() {
    if (!scelto) { setProblema('Scegli il file da mandare.'); return }
    if (!cliente) { setProblema('Legalo a un cliente: è il motivo per cui poi lo ritrovi.'); return }
    setMando(true)
    setProblema(null)
    const nomeFile = scelto.name.replace(/[^a-zA-Z0-9._-]+/g, '-')
    const path = `clienti/${cliente.id}/${Date.now()}-${nomeFile}`
    const { error } = await supabase.storage.from('vault').upload(path, scelto)
    if (error) { setProblema(`Non sono riuscito a caricare «${scelto.name}»: ${error.message}`); setMando(false); return }
    const { data: f, error: e2 } = await supabase.from('vault_file').insert({
      nome: scelto.name.replace(/\.[^.]+$/, ''), path, mime: scelto.type || null, dimensione: scelto.size,
      prospect_id: cliente.id, sezione: 'clienti',
      nota: `Passato da ${nomeDi(io)}${descrizione.trim() ? `: ${descrizione.trim()}` : ''}`,
    }).select('id,nome,path,dimensione,mime').single()
    if (e2 || !f) {
      await supabase.storage.from('vault').remove([path])
      setProblema(`Il file è salito ma non l'ho registrato: ${e2?.message ?? ''}`)
      setMando(false); return
    }
    const { data, error: e3 } = await supabase.from('chat').insert({
      da: io,
      a: aChi === 'tutti' ? null : aChi,
      testo: descrizione.trim() || null,
      prospect_id: cliente.id,
      file_id: (f as File_).id,
    }).select().single()
    setMando(false)
    if (e3 || !data) { setProblema(`Non è partito: ${e3?.message ?? 'riprova'}`); return }
    setFile((m) => ({ ...m, [(f as File_).id]: f as File_ }))
    setRighe((v) => [data as Riga, ...(v ?? [])])
    setScelto(null); setDescrizione(''); setCliente(null); setAChi('tutti')
    setToast(`Mandato a ${aChi === 'tutti' ? 'tutta la squadra' : nomeDi(aChi)}, ed è nella cartella di ${cliente.nome}`)
    setTimeout(() => setToast(null), 4000)
  }

  async function apri(r: Riga) {
    const f = r.file_id ? file[r.file_id] : null
    if (!f) return
    if (!(await apriFile(f.path))) setProblema('Il file non si apre: riprova fra un istante')
    if (r.a === io && !r.letto) {
      await supabase.from('chat').update({ letto: true }).eq('id', r.id)
      setRighe((v) => (v ?? []).map((x) => (x.id === r.id ? { ...x, letto: true } : x)))
    }
  }

  if (righe === null) return <Spinner />

  const t = cerca.trim().toLowerCase()
  const visibili = righe.filter((r) => {
    if (filtro === 'me' && r.a !== io) return false
    if (filtro === 'miei' && r.da !== io) return false
    if (!t) return true
    const f = r.file_id ? file[r.file_id] : null
    return [f?.nome, r.testo, r.prospect_id ? nomi[r.prospect_id] : '', nomeDi(r.da)]
      .some((x) => (x ?? '').toLowerCase().includes(t))
  })

  return (
    <ZonaFile onFile={(f) => { setScelto(f); setProblema(null) }} messaggio="Lascia qui il documento da passare" className="space-y-4 pb-24 sm:pb-8">
      {problema && (
        <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <span className="flex-1">{problema}</span>
          <button onClick={() => setProblema(null)} className="shrink-0 text-xs font-bold text-red-600">Chiudi</button>
        </div>
      )}

      {/* IL PASSAGGIO: il file prima di tutto, poi a chi e di chi si parla */}
      <Card className="space-y-3 border-blu/40 p-4">
        {!scelto ? (
          <div className="flex flex-wrap items-center gap-3">
            <button onClick={() => input.current?.click()}
                    className="rounded-full bg-blu px-5 py-2.5 text-sm font-bold text-white shadow-[0_4px_12px_rgba(6,23,115,0.25)] hover:bg-blu-scuro">
              Manda un documento
            </button>
            <span className="text-sm text-spento">o trascinalo qui dentro</span>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="flex items-center gap-2 rounded-lg bg-velo px-3 py-1.5 text-sm font-semibold">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4 text-navy">
                  <path d="M7 3h7l5 5v13H7zM14 3v5h5" />
                </svg>
                {scelto.name}
                <span className="text-[11px] font-normal text-spento">{fmtNum(Math.round(scelto.size / 1024))} KB</span>
              </span>
              <button onClick={() => setScelto(null)} className="text-xs font-semibold text-spento hover:text-inchiostro">Cambia file</button>
            </div>

            <div className="grid gap-3 lg:grid-cols-2">
              <div>
                <Micro>Di quale cliente è</Micro>
                {cliente ? (
                  <div className="mt-1 flex items-center gap-2 rounded-xl border border-bordo bg-white px-3 py-2">
                    <span className="min-w-0 flex-1 truncate text-sm font-semibold">{cliente.nome}</span>
                    <button onClick={() => setCliente(null)} className="text-xs font-semibold text-blu hover:underline">Cambia</button>
                  </div>
                ) : (
                  <div className="mt-1">
                    <CercaAzienda placeholder="Scrivi il nome del cliente…"
                                  onScegli={(a) => setCliente({ id: a.id, nome: nomeAzienda(a) })} />
                  </div>
                )}
              </div>
              <div>
                <Micro>A chi lo mandi</Micro>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {[{ id: 'tutti', nome: 'Tutta la squadra' }, ...squadra.filter((p) => p.id !== io)].map((p) => (
                    <button key={p.id} onClick={() => setAChi(p.id)}
                            className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
                              aChi === p.id ? 'bg-navy text-white' : 'border border-bordo bg-white text-tenue hover:border-navy hover:text-navy'}`}>
                      {p.nome ?? 'senza nome'}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-end gap-2">
              <label className="min-w-[240px] flex-1">
                <Micro>Cosa deve farci</Micro>
                <input value={descrizione} onChange={(e) => setDescrizione(e.target.value)}
                       onKeyDown={(e) => { if (e.key === 'Enter') void manda() }}
                       placeholder="Il contratto firmato, da mandare a Giacomo per la fattura"
                       className="mt-1 w-full rounded-xl border border-bordo bg-white px-3 py-2 text-sm outline-none focus:border-blu" />
              </label>
              <button onClick={() => void manda()} disabled={mando || !cliente}
                      className="rounded-full bg-blu px-5 py-2.5 text-sm font-bold text-white hover:bg-blu-scuro disabled:opacity-40">
                {mando ? 'Mando…' : 'Manda'}
              </button>
            </div>
          </div>
        )}
        <input ref={input} type="file" className="hidden"
               onChange={(e) => { const f = e.target.files?.[0]; if (f) setScelto(f); e.target.value = '' }} />
      </Card>

      {/* LA FILA: l'ultimo passaggio in cima */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap gap-1.5">
          {FILTRI.map(([k, n]) => (
            <button key={k} onClick={() => setFiltro(k)}
                    className={`rounded-full px-3 py-1.5 text-sm font-semibold ${
                      filtro === k ? 'bg-navy text-white' : 'bg-white text-tenue ring-1 ring-bordo hover:text-inchiostro'}`}>
              {n}
              {k === 'me' && righe.some((r) => r.a === io && !r.letto) && (
                <span className="ml-1.5 rounded-full bg-red-600 px-1.5 text-[10px] font-bold text-white">
                  {righe.filter((r) => r.a === io && !r.letto).length}
                </span>
              )}
            </button>
          ))}
        </div>
        <input type="search" value={cerca} onChange={(e) => setCerca(e.target.value)}
               placeholder="Cerca un documento o un cliente…"
               className="ml-auto w-full rounded-full border border-bordo bg-white px-4 py-2 text-sm outline-none focus:border-blu sm:w-72" />
      </div>

      {visibili.length === 0 ? (
        <Card><p className="px-4 py-10 text-center text-sm text-spento">
          {t ? `Niente per «${cerca.trim()}»` : 'Ancora nessun passaggio.'}
        </p></Card>
      ) : (
        <div className="space-y-2">
          {visibili.map((r) => {
            const f = r.file_id ? file[r.file_id] : null
            const nuovo = r.a === io && !r.letto
            return (
              <Card key={r.id} className={`p-3.5 ${nuovo ? 'border-l-4 border-l-blu' : ''}`}>
                <div className="flex flex-wrap items-start gap-3">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-velo text-[10px] font-bold text-navy">
                    {f ? estensione(f.path) : '?'}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="flex flex-wrap items-baseline gap-x-2">
                      <span className="text-[15px] font-bold">{f?.nome ?? 'documento'}</span>
                      {r.prospect_id && (
                        <button onClick={() => onOpen(r.prospect_id!)}
                                className="rounded-full bg-blu/10 px-2 py-0.5 text-[11px] font-bold text-navy hover:bg-blu/20">
                          {nomi[r.prospect_id] ?? 'cliente'}
                        </button>
                      )}
                      {nuovo && <span className="rounded-full bg-blu px-2 py-0.5 text-[10px] font-bold text-white">nuovo</span>}
                    </p>
                    {r.testo && <p className="mt-0.5 text-sm text-tenue">{r.testo}</p>}
                    <p className="mt-0.5 text-[11px] text-spento">
                      <span className="font-semibold">{r.da === io ? 'tu' : nomeDi(r.da)}</span>
                      {' a '}
                      <span className="font-semibold">{r.a === io ? 'te' : nomeDi(r.a)}</span>
                      {`, ${quando(r.at)}`}
                      {f?.dimensione ? `, ${fmtNum(Math.round(f.dimensione / 1024))} KB` : ''}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1.5">
                    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-velo text-[10px] font-bold text-navy" title={nomeDi(r.da)}>
                      {iniziali(nomeDi(r.da))}
                    </span>
                    <button onClick={() => void apri(r)}
                            className="rounded-full border border-bordo bg-white px-3.5 py-1.5 text-xs font-bold text-navy hover:border-navy">
                      Apri
                    </button>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      )}

      {toast && (
        <div className="salta-su fixed bottom-20 left-1/2 z-40 -translate-x-1/2 rounded-full border border-green-200 bg-green-50 px-5 py-2.5 text-sm font-bold text-green-800 shadow-[0_8px_24px_rgba(16,24,40,0.2)] sm:bottom-6">
          {toast}
        </div>
      )}
    </ZonaFile>
  )
}
