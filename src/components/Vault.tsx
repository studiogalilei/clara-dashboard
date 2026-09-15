import { useEffect, useMemo, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'
import { lazy, Suspense } from 'react'
const CompilaPdf = lazy(() => import('./CompilaPdf').catch((e) => {
  if (!sessionStorage.getItem('ricaricato')) { sessionStorage.setItem('ricaricato', '1'); location.reload() }
  throw e
}))
import type { Prospect } from '../lib/types'
import { Card, Spinner, Empty, ZonaFile, fmtNum, fmtDateShort, sgid } from './ui'
import { urlFileTanti, apriFile, dimenticaFile } from '../lib/file'

// I DOCUMENTI: la cassaforte dello Studio (Dre, 14/9). «Che ci deve fare
// una persona qui?» Trovare subito un logo, una copertina, il contratto
// tipo, il file di un cliente. Quindi: poche sezioni fisse (come le cartelle
// di Drive, ma nessuno ne inventa di nuove), una ricerca sola, le anteprime.
//   clienti  i file agganciati a un'azienda
//   brand    marchio, loghi, copertine, sfondi, segni, incisioni, regole
//   modelli  i template e gli esempi dei documenti
//   azienda  documenti interni

interface FileVault {
  id: number
  at: string
  nome: string
  path: string
  mime: string | null
  dimensione: number | null
  prospect_id: string | null
  sezione: Sezione
  gruppo: string | null
  nota: string | null
}

type Sezione = 'clienti' | 'brand' | 'modelli' | 'azienda'
type Scelta = 'tutti' | Sezione

const SEZIONI: Array<[Sezione, string, string]> = [
  ['clienti', 'Clienti', 'I file di ogni azienda, nella sua cartella'],
  ['brand', 'Brand', 'Marchio, loghi, copertine, regole'],
  ['modelli', 'Modelli', 'I template e gli esempi dei documenti'],
  ['azienda', 'Azienda', 'Documenti interni dello Studio'],
]
const GRUPPO_NOME: Record<string, string> = {
  marchio: 'Il marchio', loghi: 'Loghi', copertine: 'Copertine', sfondi: 'Sfondi delle copertine',
  segni: 'Segni a pennarello', incisioni: 'Incisioni', regole: 'Regole e Clara Capsule', modelli: 'I modelli dello Studio', esempi: 'Esempi pubblicati',
}
const ORDINE_GRUPPI = ['marchio', 'loghi', 'copertine', 'sfondi', 'segni', 'incisioni', 'regole', 'modelli', 'esempi']
const DRIVE = 'https://drive.google.com/drive/folders/0APZrGzxULiREUk9PVA'

interface Props {
  onOpen: (id: string) => void
}

const estensione = (path: string) => (path.match(/\.([a-zA-Z0-9]{1,5})$/)?.[1] ?? '').toLowerCase()
const eImmagine = (f: FileVault) => f.mime?.startsWith('image/') || ['png', 'svg', 'jpg', 'jpeg', 'webp'].includes(estensione(f.path))
const ePdf = (f: FileVault) => f.mime?.includes('pdf') || estensione(f.path) === 'pdf'

// i loghi bianchi si vedono solo su un fondo colorato: il fondo giusto sta nel nome
function fondoDi(f: FileVault): string {
  const n = f.path.toLowerCase()
  if (n.includes('su_rosso')) return '#D21205'
  if (n.includes('su_verde')) return '#2F6B33'
  if (n.includes('su_azzurro')) return '#0689FF'
  if (n.includes('su_blu') || n.includes('_bianco') || n.includes('intreccio') || n.includes('clara-logo')) return '#061773'
  return '#FFFFFF'
}

// L'anteprima: si intravede gia' il documento. Immagini e PDF veri si
// mostrano; per il resto, il foglio con l'estensione.
function Anteprima({ f, url }: { f: FileVault; url: string | null }) {
  if (url && eImmagine(f)) {
    return (
      <div className="flex h-full w-full items-center justify-center p-4" style={{ backgroundColor: fondoDi(f) }}>
        <img src={url} alt="" className="max-h-full max-w-full object-contain" loading="lazy" />
      </div>
    )
  }
  if (url && ePdf(f)) {
    return (
      <object data={`${url}#toolbar=0&navpanes=0&scrollbar=0&view=FitH`} type="application/pdf"
              className="pointer-events-none h-full w-full" aria-hidden />
    )
  }
  const est = estensione(f.path).toUpperCase()
  return (
    <div className="flex h-full items-center justify-center">
      <div className="flex h-[84%] w-[58%] flex-col gap-1.5 rounded-[3px] bg-white p-2.5 shadow-[0_2px_10px_rgba(16,24,40,0.14)]">
        <span className="h-1.5 w-3/4 rounded-full bg-inchiostro/20" />
        <span className="h-1 w-full rounded-full bg-inchiostro/10" />
        <span className="h-1 w-full rounded-full bg-inchiostro/10" />
        <span className="h-1 w-5/6 rounded-full bg-inchiostro/10" />
        {est && <span className="mt-auto self-end text-[10px] font-bold uppercase tracking-wide text-spento">{est}</span>}
      </div>
    </div>
  )
}

export default function Vault({ onOpen }: Props) {
  const [file, setFile] = useState<FileVault[] | null>(null)
  const [prospects, setProspects] = useState<Prospect[]>([])
  const [scelta, setScelta] = useState<Scelta>('tutti')
  const [cerca, setCerca] = useState('')
  const [caricando, setCaricando] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const [problema, setProblema] = useState<string | null>(null)
  const [compila, setCompila] = useState<FileVault | null>(null)
  const [url, setUrl] = useState<Record<string, string>>({})   // le URL firmate dei file che si vedono
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    supabase.from('vault_file').select('*').order('at', { ascending: false }).limit(1000)
      .then(({ data, error }) => {
        if (error) setProblema(`Non riesco a leggere i Documenti: ${error.message}`)
        setFile((data as FileVault[]) ?? [])
      })
    supabase.from('prospects').select('id,company,name,email,sg_id,stage,pipeline_stage,fuori').order('company').limit(2000)
      .then(({ data }) => setProspects((data as Prospect[]) ?? []))
  }, [])

  // le URL firmate dei file che stanno per comparire: una chiamata sola per schermata
  useEffect(() => {
    const paths = (file ?? []).map((f) => f.path)
    if (paths.length === 0) return
    let vivo = true
    void urlFileTanti(paths).then((m) => { if (vivo) setUrl((v) => ({ ...v, ...m })) })
    return () => { vivo = false }
  }, [file])

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 2600)
    return () => clearTimeout(t)
  }, [toast])

  const nomeProspect = (id: string | null) => {
    const p = prospects.find((x) => x.id === id)
    return p ? (p.company || p.name || p.email) : null
  }

  // il pedaggio del documento (Dre, 4/9): un file entra solo se si sa dove
  // va. Se no la cartella di un cliente e' incompleta e non lo sa nessuno
  const [inAttesa, setInAttesa] = useState<File | null>(null)
  const [dove, setDove] = useState('')     // «cliente:<id>» | «brand:<gruppo>» | «modelli» | «azienda»

  async function carica(f: File) {
    if (!dove) return
    setCaricando(true)
    const [sezione, resto] = dove.split(':') as [string, string | undefined]
    const nomeFile = f.name.replace(/[^a-zA-Z0-9._-]+/g, '-')
    const cartella = sezione === 'cliente' ? `clienti/${resto}` : sezione === 'brand' ? `brand/${resto}` : sezione
    const path = `${cartella}/${Date.now()}-${nomeFile}`
    const { error } = await supabase.storage.from('vault').upload(path, f)
    if (error) {
      setProblema(`Non sono riuscita a caricare «${f.name}»: ${error.message}`)
      setCaricando(false); return
    }
    const riga = {
      nome: f.name.replace(/\.[^.]+$/, ''), path, mime: f.type || null, dimensione: f.size,
      prospect_id: sezione === 'cliente' ? resto : null,
      sezione: sezione === 'cliente' ? 'clienti' : sezione,
      gruppo: sezione === 'brand' ? resto : null,
    }
    const { data, error: e2 } = await supabase.from('vault_file').insert(riga).select().single()
    if (e2 || !data) {
      await supabase.storage.from('vault').remove([path])
      setProblema(`Il file e' salito ma non l'ho potuto registrare: ${e2?.message ?? 'errore'}`)
    } else {
      dimenticaFile(path)
      setFile((v) => [data as FileVault, ...(v ?? [])])
      setToast(sezione === 'cliente' ? `«${riga.nome}» nella cartella di ${nomeProspect(resto!)} ✓` : `«${riga.nome}» in ${SEZIONI.find(([k]) => k === riga.sezione)?.[1]} ✓`)
      setScelta(riga.sezione as Sezione)
    }
    setInAttesa(null); setDove(''); setCaricando(false)
  }

  async function aggiorna(id: number, patch: Partial<FileVault>) {
    const { data, error } = await supabase.from('vault_file').update(patch).eq('id', id).select().single()
    if (error) { setProblema(`Non ho potuto salvare: ${error.message}`); return }
    setFile((v) => v!.map((x) => (x.id === id ? (data as FileVault) : x)))
  }

  const urlDi = (f: FileVault): string | null => url[f.path] ?? null

  async function copiaLink(f: FileVault) {
    // il link firmato dura un'ora: chi lo riceve lo apre subito, non per sempre
    const u = urlDi(f)
    if (!u) { setProblema('Il link non è pronto: riprova fra un istante'); return }
    try { await navigator.clipboard.writeText(u); setToast('Link copiato, vale un\'ora') } catch { setProblema('Non riesco a copiare il link') }
  }

  const t = cerca.trim().toLowerCase()
  const visibili = useMemo(() => (file ?? []).filter((f) => {
    if (!t) return true
    const p2 = prospects.find((x) => x.id === f.prospect_id)
    return f.nome.toLowerCase().includes(t)
      || (f.gruppo ?? '').includes(t) || (f.nota ?? '').toLowerCase().includes(t)
      || (nomeProspect(f.prospect_id) ?? '').toLowerCase().includes(t)
      || (sgid(p2?.sg_id, p2) ?? '').toLowerCase().includes(t)
  }), [file, prospects, t])   // eslint-disable-line react-hooks/exhaustive-deps

  const conta = (s: Sezione) => (file ?? []).filter((f) => f.sezione === s).length

  // i loghi stanno a coppie SVG + PNG con lo stesso nome: una carta sola, due formati
  function accoppia(lista: FileVault[]): Array<{ capo: FileVault; formati: FileVault[] }> {
    const m = new Map<string, FileVault[]>()
    for (const f of lista) {
      const k = f.gruppo === 'loghi' || f.gruppo === 'marchio' ? `${f.gruppo}/${f.nome}` : String(f.id)
      m.set(k, [...(m.get(k) ?? []), f])
    }
    return [...m.values()].map((formati) => ({ capo: formati.find((x) => estensione(x.path) === 'svg') ?? formati[0], formati }))
  }

  const carta = ({ capo: f, formati }: { capo: FileVault; formati: FileVault[] }, piccola = false) => {
    const suo = urlDi(f)
    const p2 = prospects.find((x) => x.id === f.prospect_id)
    const codice = sgid(p2?.sg_id, p2)
    return (
      <div key={f.id} className="group flex flex-col overflow-hidden rounded-2xl border border-bordo bg-white shadow-[0_1px_2px_rgba(16,24,40,0.03),0_4px_16px_rgba(16,24,40,0.04)] transition-colors hover:border-blu">
        <button onClick={() => void apriFile(f.path)} title="Apri"
                className={`block ${piccola ? 'h-28' : 'h-40'} w-full overflow-hidden border-b border-velo bg-velo`}>
          <Anteprima f={f} url={suo} />
        </button>
        <div className="flex flex-1 flex-col gap-1 p-3">
          <input
            value={f.nome}
            onChange={(e) => setFile((v) => v!.map((x) => (x.id === f.id ? { ...x, nome: e.target.value } : x)))}
            onBlur={(e) => { if (e.target.value !== f.nome) void aggiorna(f.id, { nome: e.target.value }) }}
            title="Il nome si cambia qui"
            className="w-full truncate rounded bg-transparent text-[13px] font-semibold outline-none focus:bg-velo focus:ring-1 focus:ring-blu"
          />
          {f.nota && <p className="truncate text-[11px] text-tenue">{f.nota}</p>}
          <p className="truncate text-[11px] text-spento">
            {formati.length > 1 ? formati.map((x) => estensione(x.path).toUpperCase()).join(', ') : estensione(f.path).toUpperCase()}
            {f.dimensione && formati.length === 1 ? `, ${fmtNum(Math.round(f.dimensione / 1024))} KB` : ''}
            {f.sezione === 'clienti' || f.sezione === 'azienda' ? `, ${fmtDateShort(f.at)}` : ''}
            {codice && <span className="ml-1.5 font-semibold text-blu/70">{codice}</span>}
          </p>
          <div className="mt-auto flex flex-wrap items-center gap-1.5 pt-1.5">
            {formati.map((x) => (
              <button key={x.id} onClick={() => void apriFile(x.path)}
                      className="rounded-full border border-bordo px-2.5 py-1 text-[11px] font-bold text-navy hover:border-navy">
                {formati.length > 1 ? estensione(x.path).toUpperCase() : 'apri'}
              </button>
            ))}
            <button onClick={() => copiaLink(f)} className="rounded-full border border-bordo px-2.5 py-1 text-[11px] font-semibold text-tenue hover:border-spento">link</button>
            {ePdf(f) && (
              <button onClick={() => setCompila(f)} title="Scrivi sopra: testo, data, firma, timbro"
                      className="rounded-full border border-bordo px-2.5 py-1 text-[11px] font-bold text-navy hover:border-navy">compila</button>
            )}
            {f.prospect_id && (
              <button onClick={() => onOpen(f.prospect_id!)} className="rounded-full border border-bordo px-2.5 py-1 text-[11px] font-bold text-blu hover:border-blu">scheda</button>
            )}
            {(f.sezione === 'clienti' || f.sezione === 'azienda') && (
              <select value={f.prospect_id ?? ''}
                      onChange={(e) => aggiorna(f.id, { prospect_id: e.target.value || null, sezione: e.target.value ? 'clienti' : 'azienda' })}
                      className="ml-auto max-w-[120px] truncate rounded-full border border-bordo bg-white px-2 py-1 text-[11px] text-tenue outline-none focus:border-blu">
                <option value="">interno</option>
                {prospects.map((p) => <option key={p.id} value={p.id}>{p.company || p.name || p.email}</option>)}
              </select>
            )}
          </div>
        </div>
      </div>
    )
  }

  const griglia = (lista: FileVault[], piccola = false) => (
    <div className={piccola ? 'grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5 2xl:grid-cols-6' : 'grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5'}>
      {accoppia(lista).map((c) => carta(c, piccola))}
    </div>
  )

  // una sezione: i suoi scaffali (gruppi) in ordine, o le cartelle dei clienti
  const sezione = (s: Sezione, lista: FileVault[]) => {
    if (lista.length === 0) return <Card><Empty text={t ? `Niente per «${cerca.trim()}» qui` : 'Ancora vuota'} /></Card>
    if (s === 'clienti') {
      const perCliente = new Map<string, FileVault[]>()
      for (const f of lista) perCliente.set(f.prospect_id ?? '', [...(perCliente.get(f.prospect_id ?? '') ?? []), f])
      return [...perCliente.entries()].sort((a, b) => (nomeProspect(a[0]) ?? '').localeCompare(nomeProspect(b[0]) ?? '')).map(([pid, suoi]) => {
        const p2 = prospects.find((x) => x.id === pid)
        return (
          <section key={pid} className="space-y-2.5">
            <h3 className="flex items-baseline gap-2 text-sm font-bold">
              {nomeProspect(pid) ?? 'Senza azienda'}
              {sgid(p2?.sg_id, p2) && <span className="text-[11px] font-semibold text-blu/70">{sgid(p2?.sg_id, p2)}</span>}
              <span className="text-[11px] font-semibold text-spento">{suoi.length}</span>
              {pid && <button onClick={() => onOpen(pid)} className="ml-1 text-[11px] font-semibold text-blu hover:underline">apri la scheda</button>}
            </h3>
            {griglia(suoi)}
          </section>
        )
      })
    }
    const gruppi = [...new Set(lista.map((f) => f.gruppo ?? ''))].sort((a, b) => (ORDINE_GRUPPI.indexOf(a) + 100) % 100 - (ORDINE_GRUPPI.indexOf(b) + 100) % 100)
    return gruppi.map((g) => {
      const suoi = lista.filter((f) => (f.gruppo ?? '') === g)
      return (
        <section key={g || 'altro'} className="space-y-2.5">
          {g && (
            <h3 className="flex items-baseline gap-2 text-sm font-bold">
              {GRUPPO_NOME[g] ?? g[0].toUpperCase() + g.slice(1)}
              <span className="text-[11px] font-semibold text-spento">{g === 'loghi' || g === 'marchio' ? accoppia(suoi).length : suoi.length}</span>
            </h3>
          )}
          {griglia(suoi, g === 'loghi')}
        </section>
      )
    })
  }

  const recenti = (file ?? []).filter((f) => f.sezione === 'clienti' || f.sezione === 'azienda').slice(0, 5)

  return (
    <ZonaFile onFile={(f) => setInAttesa(f)} messaggio="Lascia qui: va nei Documenti" className="space-y-5 pb-24 sm:pb-8">

      {problema && (
        <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <span className="flex-1">{problema}</span>
          <button onClick={() => setProblema(null)} className="shrink-0 text-xs font-bold text-red-600 hover:text-red-900">chiudi</button>
        </div>
      )}

      {inAttesa && (
        <Card className="salta-su border-blu/40 p-4">
          <p className="text-sm font-bold">Dove va «{inAttesa.name.replace(/\.[^.]+$/, '')}»?</p>
          <div className="mt-2.5 flex flex-wrap items-center gap-2">
            <select autoFocus value={dove} onChange={(e) => setDove(e.target.value)}
                    className="min-w-[260px] flex-1 rounded-lg border border-bordo bg-white px-3 py-2 text-sm outline-none focus:border-blu">
              <option value="">Scegli…</option>
              <optgroup label="Nella cartella di un cliente">
                {prospects.filter((p) => p.fuori || p.stage === 'cliente').map((p) => (
                  <option key={p.id} value={`cliente:${p.id}`}>{p.company || p.name || p.email}{sgid(p.sg_id, p) ? `, ${sgid(p.sg_id, p)}` : ''}</option>
                ))}
              </optgroup>
              <optgroup label="Nella cartella di un'altra azienda">
                {prospects.filter((p) => !(p.fuori || p.stage === 'cliente')).map((p) => (
                  <option key={p.id} value={`cliente:${p.id}`}>{p.company || p.name || p.email}</option>
                ))}
              </optgroup>
              <optgroup label="Brand">
                {ORDINE_GRUPPI.filter((g) => g !== 'esempi' && g !== 'modelli').map((g) => <option key={g} value={`brand:${g}`}>{GRUPPO_NOME[g]}</option>)}
              </optgroup>
              <option value="modelli">Modelli</option>
              <option value="azienda">Azienda (documento interno)</option>
            </select>
            <button onClick={() => carica(inAttesa)} disabled={!dove || caricando}
                    className="rounded-full bg-blu px-4 py-2 text-sm font-bold text-white hover:bg-blu-scuro disabled:cursor-not-allowed disabled:opacity-30">
              {caricando ? 'Carico…' : 'Metti qui'}
            </button>
            <button onClick={() => { setInAttesa(null); setDove('') }} className="text-xs text-spento hover:text-inchiostro">annulla</button>
          </div>
        </Card>
      )}

      {/* la barra: le sezioni a sinistra, la ricerca e l'aggiunta a destra (come Drive) */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap items-center gap-1.5">
          {([['tutti', 'Tutti'], ...SEZIONI.map(([k, n]) => [k, n])] as Array<[Scelta, string]>).map(([k, n]) => (
            <button key={k} onClick={() => setScelta(k)}
                    className={`rounded-full px-3.5 py-1.5 text-sm font-semibold transition-colors ${scelta === k ? 'bg-navy text-white' : 'bg-white text-tenue ring-1 ring-bordo hover:text-inchiostro'}`}>
              {n}{k !== 'tutti' && file ? <span className={`ml-1.5 text-[11px] ${scelta === k ? 'text-white/70' : 'text-spento'}`}>{conta(k as Sezione)}</span> : null}
            </button>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-2">
          <input type="search" value={cerca} onChange={(e) => setCerca(e.target.value)} placeholder="Cerca un documento, un logo, un cliente…"
                 className="w-64 rounded-full border border-bordo bg-white px-4 py-2 text-sm outline-none focus:border-blu lg:w-80" />
          <a href={DRIVE} target="_blank" rel="noreferrer" title="Il Drive condiviso StudioGalilei: l'archivio"
             className="hidden rounded-full border border-bordo bg-white px-3.5 py-2 text-sm font-semibold text-tenue hover:border-navy hover:text-navy sm:block">Drive</a>
          <button onClick={() => inputRef.current?.click()} disabled={caricando}
                  className="rounded-full bg-blu px-4 py-2 text-sm font-bold text-white shadow-[0_4px_12px_rgba(6,23,115,0.25)] hover:bg-blu-scuro disabled:opacity-40">
            {caricando ? 'Carico…' : '+ Aggiungi'}
          </button>
          <input ref={inputRef} type="file" className="hidden"
                 onChange={(e) => { const f = e.target.files?.[0]; if (f) setInAttesa(f); e.target.value = '' }} />
        </div>
      </div>

      {file === null ? (
        <Card><Spinner /></Card>
      ) : t ? (
        // la ricerca guarda dappertutto, qualunque sezione sia scelta
        visibili.length === 0
          ? <Card><Empty text={`Niente per «${cerca.trim()}»`} /></Card>
          : SEZIONI.filter(([k]) => visibili.some((f) => f.sezione === k)).map(([k, n]) => (
            <section key={k} className="space-y-3">
              <h2 className="text-base font-extrabold">{n}</h2>
              {sezione(k, visibili.filter((f) => f.sezione === k))}
            </section>
          ))
      ) : scelta === 'tutti' ? (
        <>
          {/* la porta d'ingresso: quattro stanze con dentro cosa c'e' */}
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {SEZIONI.map(([k, n, cosa]) => (
              <button key={k} onClick={() => setScelta(k)}
                      className="rounded-2xl border border-bordo bg-white p-4 text-left shadow-[0_1px_2px_rgba(16,24,40,0.03)] transition-colors hover:border-blu">
                <span className="flex items-baseline justify-between gap-2">
                  <span className="text-[15px] font-extrabold">{n}</span>
                  <span className="text-sm font-bold tabular-nums text-spento">{conta(k)}</span>
                </span>
                <span className="mt-1 block text-[13px] text-tenue">{cosa}</span>
              </button>
            ))}
          </div>
          {recenti.length > 0 && (
            <section className="space-y-2.5">
              <h3 className="text-sm font-bold">Ultimi arrivati</h3>
              {griglia(recenti)}
            </section>
          )}
        </>
      ) : (
        <div className="space-y-6">{sezione(scelta, visibili.filter((f) => f.sezione === scelta))}</div>
      )}

      {compila && (
        <Suspense fallback={null}>
          <CompilaPdf file={compila} onClose={() => setCompila(null)}
                      onSalvato={(nuovo) => { setFile((v) => [{ ...(nuovo as FileVault), sezione: compila.sezione, gruppo: compila.gruppo, nota: null }, ...(v ?? [])]); setToast(`«${nuovo.nome}» salvato ✓`) }} />
        </Suspense>
      )}

      {toast && (
        <div className="salta-su fixed bottom-20 left-1/2 z-40 -translate-x-1/2 rounded-full border border-green-200 bg-green-50 px-5 py-2.5 text-sm font-bold text-green-800 shadow-[0_8px_24px_rgba(16,24,40,0.2)] sm:bottom-6">
          {toast}
        </div>
      )}
    </ZonaFile>
  )
}
