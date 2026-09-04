import { useEffect, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'
import type { Prospect } from '../lib/types'
import { Card, Spinner, Empty, ZonaFile, fmtNum, fmtDateShort, sgid } from './ui'

// Il Vault: la cassaforte. File con un nome tuo, agganciabili a un
// prospect/cliente, sempre ritrovabili (anche dalla ricerca di Clara).

interface FileVault {
  id: number
  at: string
  nome: string
  path: string
  mime: string | null
  dimensione: number | null
  prospect_id: string | null
}

interface Props {
  onOpen: (id: string) => void
}

// L'anteprima: si intravede gia' il documento, come i PDF su WhatsApp.
// Immagini e PDF veri si mostrano; per il resto, il foglio con l'estensione.
function Anteprima({ f, url }: { f: FileVault; url: string | null }) {
  if (url && f.mime?.startsWith('image/')) {
    return <img src={url} alt="" className="h-full w-full object-cover" />
  }
  if (url && f.mime?.includes('pdf')) {
    return (
      <object
        data={`${url}#toolbar=0&navpanes=0&scrollbar=0&view=FitH`}
        type="application/pdf"
        className="pointer-events-none h-full w-full"
        aria-hidden
      />
    )
  }
  const est = (f.path.match(/\.([a-zA-Z0-9]{1,5})$/)?.[1] ?? '').toUpperCase()
  return (
    <div className="flex h-full items-center justify-center">
      <div className="flex h-[84%] w-[58%] flex-col gap-1.5 rounded-[3px] bg-white p-2.5 shadow-[0_2px_10px_rgba(16,24,40,0.14)]">
        <span className="h-1.5 w-3/4 rounded-full bg-inchiostro/20" />
        <span className="h-1 w-full rounded-full bg-inchiostro/10" />
        <span className="h-1 w-full rounded-full bg-inchiostro/10" />
        <span className="h-1 w-5/6 rounded-full bg-inchiostro/10" />
        <span className="h-1 w-full rounded-full bg-inchiostro/10" />
        {est && <span className="mt-auto self-end text-[10px] font-bold uppercase tracking-wide text-spento">{est}</span>}
      </div>
    </div>
  )
}

export default function Vault({ onOpen }: Props) {
  const [file, setFile] = useState<FileVault[] | null>(null)
  const [prospects, setProspects] = useState<Prospect[]>([])
  const [cerca, setCerca] = useState('')
  const [caricando, setCaricando] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [problema, setProblema] = useState<string | null>(null)

  useEffect(() => {
    supabase.from('vault_file').select('*').order('at', { ascending: false }).limit(200)
      .then(({ data, error }) => {
        // senza questo una connessione rotta si legge «nessun documento»,
        // che e' la bugia peggiore in un archivio (revisione 4/9)
        if (error) setProblema('I documenti non si caricano: ' + error.message)
        setFile((data as FileVault[]) ?? [])
      })
    supabase.from('prospects').select('*').neq('stage', 'nuovo').limit(300)
      .then(({ data }) => setProspects((data as Prospect[]) ?? []))
  }, [])

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 3000)
    return () => clearTimeout(t)
  }, [toast])

  const nomeProspect = (id: string | null) =>
    id ? (prospects.find((p) => p.id === id)?.company ?? prospects.find((p) => p.id === id)?.name ?? null) : null

  // il file resta in mano finche' non si dice a chi appartiene
  const [inAttesa, setInAttesa] = useState<File | null>(null)
  const [aCasaDi, setACasaDi] = useState('')

  async function carica(f: File) {
    setCaricando(true)
    const path = `${Date.now()}-${f.name.replace(/[^a-zA-Z0-9._-]/g, '_')}`
    const { error } = await supabase.storage.from('vault').upload(path, f)
    if (error) {
      setProblema(`«${f.name}» non è salito: ${error.message}`)
      setCaricando(false)
      return
    }
    const nome = f.name.replace(/\.[^.]+$/, '')
    const { data, error: e2 } = await supabase.from('vault_file')
      .insert({ nome, path, mime: f.type || null, dimensione: f.size,
                prospect_id: aCasaDi || null })
      .select().single()
    if (e2 || !data) {
      // il file e' nello storage ma nessuna riga lo nomina: se lo lasciassimo
      // li' sarebbe spazio occupato che non compare in nessuna cartella
      await supabase.storage.from('vault').remove([path])
      setProblema(`«${nome}» è stato caricato ma non registrato, quindi l'ho tolto. ${e2?.message ?? ''}`.trim())
      setCaricando(false)
      return
    }
    setFile((v) => [data as FileVault, ...(v ?? [])])
    setToast(aCasaDi
      ? `«${nome}» nella cartella di ${nomeProspect(aCasaDi)} ✓`
      : `«${nome}» fra i documenti interni ✓`)
    setProblema(null)
    setInAttesa(null)
    setACasaDi('')
    setCaricando(false)
  }

  async function aggiorna(id: number, patch: Partial<FileVault>) {
    const { data, error } = await supabase.from('vault_file').update(patch).eq('id', id).select().single()
    if (error || !data) {
      // prima la riga tornava com'era e sembrava un ripensamento del mouse
      setProblema('La modifica non è stata salvata: ' + (error?.message ?? 'nessuna riga aggiornata'))
      return
    }
    setProblema(null)
    setFile((v) => v!.map((x) => (x.id === id ? (data as FileVault) : x)))
  }

  function urlDi(f: FileVault): string | null {
    const { data } = supabase.storage.from('vault').getPublicUrl(f.path)
    return data?.publicUrl && data.publicUrl !== '#' ? data.publicUrl : null
  }

  function apri(f: FileVault) {
    const url = urlDi(f)
    if (url) window.open(url, '_blank')
  }

  const visibili = (file ?? []).filter((f) => {
    if (!cerca.trim()) return true
    const t = cerca.trim().toLowerCase()
    const p2 = prospects.find((x) => x.id === f.prospect_id)
    return f.nome.toLowerCase().includes(t)
      || (nomeProspect(f.prospect_id) ?? '').toLowerCase().includes(t)
      || (sgid(p2?.sg_id) ?? '').toLowerCase().includes(t)
  })

  return (
    <ZonaFile onFile={(f) => setInAttesa(f)} messaggio="Lascia qui: va nei Documenti" className="space-y-3 pb-24 sm:pb-8">

      {problema && (
        <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <span className="flex-1">{problema}</span>
          <button onClick={() => setProblema(null)} className="shrink-0 text-xs font-bold text-red-600 hover:text-red-900">chiudi</button>
        </div>
      )}

      {/* il pedaggio del documento (Dre, 4/9): un file entra solo se si sa
          di chi e'. Se no la cartella di un cliente e' incompleta e non lo
          sa nessuno */}
      {inAttesa && (
        <Card className="salta-su border-blu/40 p-4">
          <p className="text-sm font-bold">Di chi è «{inAttesa.name.replace(/\.[^.]+$/, '')}»?</p>
          <div className="mt-2.5 flex flex-wrap items-center gap-2">
            <select
              autoFocus
              value={aCasaDi}
              onChange={(e) => setACasaDi(e.target.value)}
              className="min-w-[240px] flex-1 rounded-lg border border-bordo bg-white px-3 py-2 text-sm outline-none focus:border-blu"
            >
              <option value="">Scegli il cliente…</option>
              {prospects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.company || p.name || p.email}{sgid(p.sg_id) ? ` · ${sgid(p.sg_id)}` : ''}
                </option>
              ))}
            </select>
            <button
              onClick={() => carica(inAttesa)}
              disabled={!aCasaDi || caricando}
              className="rounded-full bg-navy px-4 py-2 text-sm font-bold text-white hover:bg-navy-scuro disabled:cursor-not-allowed disabled:opacity-30"
            >
              {caricando ? 'Carico…' : 'Metti nella sua cartella'}
            </button>
            <button
              onClick={() => { setACasaDi(''); carica(inAttesa) }}
              disabled={caricando}
              className="rounded-full border border-bordo px-4 py-2 text-sm font-semibold text-tenue hover:border-spento"
            >
              È un documento interno
            </button>
            <button
              onClick={() => { setInAttesa(null); setACasaDi('') }}
              className="text-xs text-spento hover:text-inchiostro"
            >
              annulla
            </button>
          </div>
        </Card>
      )}
      <div className="flex flex-wrap items-center gap-2.5">
        <button
          onClick={() => inputRef.current?.click()}
          disabled={caricando}
          className="rounded-full bg-navy px-5 py-2.5 text-sm font-bold text-white shadow-[0_4px_12px_rgba(6,23,115,0.25)] hover:bg-navy-scuro disabled:opacity-40"
        >
          {caricando ? 'Carico…' : '+ Aggiungi file'}
        </button>
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) setInAttesa(f); e.target.value = '' }}
        />
        <input
          type="search"
          value={cerca}
          onChange={(e) => setCerca(e.target.value)}
          placeholder="Cerca nei Documenti…"
          className="w-56 rounded-full border border-bordo bg-white px-4 py-2 text-sm outline-none focus:border-blu"
        />
      </div>

      {file === null ? (
        <Card><Spinner /></Card>
      ) : visibili.length === 0 ? (
        <Card><Empty text={cerca ? `Niente per «${cerca}»` : 'Nessun documento'} /></Card>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
          {visibili.map((f) => (
            <div
              key={f.id}
              className="group overflow-hidden rounded-2xl border border-bordo bg-white shadow-[0_1px_2px_rgba(16,24,40,0.03),0_4px_16px_rgba(16,24,40,0.04)] transition-colors hover:border-blu"
            >
              {/* il documento si intravede; clic = si apre */}
              <button
                onClick={() => apri(f)}
                className="block h-36 w-full overflow-hidden border-b border-velo bg-velo text-left"
              >
                <Anteprima f={f} url={urlDi(f)} />
              </button>
              <div className="space-y-1 p-3">
                <input
                  value={f.nome}
                  onChange={(e) => setFile((v) => v!.map((x) => (x.id === f.id ? { ...x, nome: e.target.value } : x)))}
                  onBlur={(e) => aggiorna(f.id, { nome: e.target.value })}
                  className="w-full truncate rounded bg-transparent text-[13px] font-semibold outline-none focus:bg-velo focus:ring-1 focus:ring-blu"
                />
                <p className="truncate text-[11px] text-tenue">
                  {fmtDateShort(f.at)}
                  {f.dimensione ? ` · ${fmtNum(Math.round(f.dimensione / 1024))} KB` : ''}
                  {(() => {
                    const p2 = prospects.find((x) => x.id === f.prospect_id)
                    const c = sgid(p2?.sg_id)
                    return c ? <span className="ml-1.5 font-semibold text-blu/70">{c}</span> : null
                  })()}
                </p>
                <div className="flex items-center gap-1.5 pt-0.5">
                  <select
                    value={f.prospect_id ?? ''}
                    onChange={(e) => aggiorna(f.id, { prospect_id: e.target.value || null })}
                    className="min-w-0 flex-1 truncate rounded-full border border-bordo bg-white px-2.5 py-1 text-[11px] font-semibold text-tenue outline-none focus:border-blu"
                  >
                    <option value="">nessun aggancio</option>
                    {prospects.map((p) => (
                      <option key={p.id} value={p.id}>
                        {sgid(p.sg_id) ? `${sgid(p.sg_id)} · ` : ''}{p.company || p.name || p.email}
                      </option>
                    ))}
                  </select>
                  {f.prospect_id && (
                    <button
                      onClick={() => onOpen(f.prospect_id!)}
                      className="shrink-0 rounded-full border border-bordo px-2.5 py-1 text-[11px] font-bold text-blu hover:border-blu"
                    >
                      scheda
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
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
