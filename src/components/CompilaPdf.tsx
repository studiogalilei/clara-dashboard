import { useEffect, useRef, useState } from 'react'
import * as pdfjs from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import { PDFDocument, StandardFonts, rgb } from 'pdf-lib'
import { supabase } from '../lib/supabase'
import { urlFile } from '../lib/file'
import { leggiFirma, leggiTimbro, bytePng } from '../lib/firma'

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl

// COMPILA PDF (Dre e Giacomo, 11/9): «inserire queste due date» senza che il
// documento si smerdi. Il PDF non si riscrive: ci si scrive SOPRA. Clicchi
// dove va una cosa (un testo, la data di oggi, la tua firma, il timbro) e
// ci finisce li'; la trascini se serve; salvi e nasce un PDF nuovo, con lo
// stesso impaginato di prima, nella stessa cartella.

export interface FilePdf { id: number; nome: string; path: string; prospect_id: string | null }
interface Props { file: FilePdf; onClose: () => void; onSalvato?: (nuovo: { id: number; nome: string; path: string; at: string; mime: string | null; dimensione: number | null; prospect_id: string | null }) => void }

type Tipo = 'testo' | 'firma' | 'timbro'
interface Pezzo { id: number; pagina: number; x: number; y: number; w: number; h: number; tipo: Tipo; testo: string; src?: string; bordo?: boolean }
interface Pagina { n: number; w: number; h: number }

const LARGHEZZA = 720          // px della pagina a schermo: la scala viene da qui
const NAVY = rgb(0.11, 0.18, 0.43)

function oggiIt() { return new Date().toLocaleDateString('it-IT') }

export default function CompilaPdf({ file, onClose, onSalvato }: Props) {
  const [pagine, setPagine] = useState<Pagina[]>([])
  const [byte, setByte] = useState<Uint8Array | null>(null)
  const [pezzi, setPezzi] = useState<Pezzo[]>([])
  const [strumento, setStrumento] = useState<Tipo | 'data' | null>(null)
  const [scelto, setScelto] = useState<number | null>(null)
  const [firma, setFirma] = useState<{ src: string; w: number; h: number } | null>(null)
  const [timbro, setTimbro] = useState<{ src: string; w: number; h: number } | null>(null)
  const [stato, setStato] = useState<string | null>(null)
  const [salvo, setSalvo] = useState(false)
  const tele = useRef<Record<number, HTMLCanvasElement | null>>({})
  const trascino = useRef<{ id: number; dx: number; dy: number } | null>(null)
  const prossimoId = useRef(1)

  const [url, setUrl] = useState<string | null>(null)
  useEffect(() => { void urlFile(file.path).then(setUrl) }, [file.path])

  // il PDF e le pagine
  useEffect(() => {
    if (!url) return
    let vivo = true
    ;(async () => {
      try {
        const r = await fetch(url)
        const b = new Uint8Array(await r.arrayBuffer())
        if (!vivo) return
        setByte(b)
        const doc = await pdfjs.getDocument({ data: b.slice() }).promise
        const lista: Pagina[] = []
        for (let n = 1; n <= doc.numPages; n++) {
          const p = await doc.getPage(n)
          const v = p.getViewport({ scale: 1 })
          lista.push({ n, w: v.width, h: v.height })
        }
        if (!vivo) return
        setPagine(lista)
        // disegno dopo che i canvas esistono
        setTimeout(async () => {
          for (const pg of lista) {
            const c = tele.current[pg.n]
            if (!c) continue
            const p = await doc.getPage(pg.n)
            const s = LARGHEZZA / pg.w
            const dpr = Math.min(window.devicePixelRatio || 1, 2)
            const v = p.getViewport({ scale: s * dpr })
            c.width = v.width; c.height = v.height
            c.style.width = `${LARGHEZZA}px`; c.style.height = `${pg.h * s}px`
            await p.render({ canvas: c, canvasContext: c.getContext('2d')!, viewport: v }).promise
          }
        }, 0)
      } catch (e) {
        setStato('Non riesco ad aprire questo PDF: ' + (e as Error).message)
      }
    })()
    return () => { vivo = false }
  }, [url])

  // la firma e il timbro, con le loro proporzioni
  useEffect(() => {
    const misura = (src: string) => new Promise<{ src: string; w: number; h: number }>((ok) => {
      const i = new Image(); i.onload = () => ok({ src, w: i.naturalWidth, h: i.naturalHeight }); i.onerror = () => ok({ src, w: 3, h: 1 }); i.src = src
    })
    void leggiFirma().then((f) => { if (f) void misura(f).then(setFirma) })
    void leggiTimbro().then((t) => { if (t) void misura(t).then(setTimbro) })
  }, [])

  const scala = (pg: Pagina) => LARGHEZZA / pg.w

  function clicPagina(e: React.MouseEvent<HTMLDivElement>, pg: Pagina) {
    if (!strumento) { setScelto(null); return }
    const r = e.currentTarget.getBoundingClientRect()
    const s = scala(pg)
    const x = (e.clientX - r.left) / s, y = (e.clientY - r.top) / s
    const id = prossimoId.current++
    if (strumento === 'testo' || strumento === 'data') {
      const testo = strumento === 'data' ? oggiIt() : ''
      setPezzi((v) => [...v, { id, pagina: pg.n, x, y: y - 6, w: 160, h: 14, tipo: 'testo', testo }])
      setScelto(id)
    } else {
      const img = strumento === 'firma' ? firma : timbro
      if (!img) { setStato(strumento === 'firma' ? 'Non hai ancora una firma: la fai in Impostazioni.' : 'Non c\'e\' ancora il timbro: si carica in Impostazioni.'); return }
      const w = strumento === 'firma' ? 150 : 80
      const h = w * img.h / img.w
      setPezzi((v) => [...v, { id, pagina: pg.n, x: x - w / 2, y: y - h / 2, w, h, tipo: strumento, testo: '', src: img.src }])
      setScelto(id)
    }
    if (strumento !== 'testo') setStrumento(null)
  }

  function iniziaTrascino(e: React.PointerEvent, p: Pezzo, pg: Pagina) {
    e.stopPropagation()
    const s = scala(pg)
    trascino.current = { id: p.id, dx: e.clientX / s - p.x, dy: e.clientY / s - p.y }
    setScelto(p.id)
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  }
  function muovi(e: React.PointerEvent, pg: Pagina) {
    const t = trascino.current
    if (!t) return
    const s = scala(pg)
    setPezzi((v) => v.map((p) => (p.id === t.id ? { ...p, x: e.clientX / s - t.dx, y: e.clientY / s - t.dy } : p)))
  }
  function fineTrascino() { trascino.current = null }

  function togli(id: number) { setPezzi((v) => v.filter((p) => p.id !== id)); setScelto(null) }

  async function salva() {
    if (!byte) return
    setSalvo(true); setStato(null)
    try {
      const doc = await PDFDocument.load(byte)
      const font = await doc.embedFont(StandardFonts.Helvetica)
      const immagini = new Map<string, Awaited<ReturnType<typeof doc.embedPng>>>()
      for (const p of pezzi) {
        const pagina = doc.getPage(p.pagina - 1)
        const ph = pagina.getHeight()
        if (p.tipo === 'testo') {
          if (!p.testo.trim()) continue
          pagina.drawText(p.testo, { x: p.x, y: ph - p.y - 11, size: 11, font, color: NAVY })
        } else if (p.src) {
          let img = immagini.get(p.src)
          if (!img) { img = await doc.embedPng(await bytePng(p.src)); immagini.set(p.src, img) }
          pagina.drawImage(img, { x: p.x, y: ph - p.y - p.h, width: p.w, height: p.h })
        }
      }
      const fuori = await doc.save()
      const nome = `${file.nome} (compilato)`
      const path = `${Date.now()}-${nome.replace(/[^a-zA-Z0-9._-]/g, '_')}.pdf`
      const blob = new Blob([fuori as BlobPart], { type: 'application/pdf' })
      const { error } = await supabase.storage.from('vault').upload(path, blob, { contentType: 'application/pdf' })
      if (error) throw new Error(error.message)
      const { data, error: e2 } = await supabase.from('vault_file')
        .insert({ nome, path, mime: 'application/pdf', dimensione: blob.size, prospect_id: file.prospect_id }).select().single()
      if (e2 || !data) { await supabase.storage.from('vault').remove([path]); throw new Error(e2?.message ?? 'riga non scritta') }
      onSalvato?.(data as Parameters<NonNullable<Props['onSalvato']>>[0])
      setStato(`Salvato: «${nome}», nella stessa cartella ✓`)
      setTimeout(onClose, 1200)
    } catch (e) {
      setStato('Non salvato: ' + (e as Error).message)
      setSalvo(false)
    }
  }

  const attrezzo = (t: Tipo | 'data', etichetta: string, spento = false) => (
    <button onClick={() => setStrumento(strumento === t ? null : t)} disabled={spento}
            className={`rounded-full px-3.5 py-1.5 text-xs font-bold transition-colors ${strumento === t ? 'bg-blu text-white' : 'border border-bordo bg-white text-tenue hover:border-navy'} disabled:opacity-30`}>
      {etichetta}
    </button>
  )

  return (
    <div className="fixed inset-0 z-[60] flex flex-col bg-inchiostro/40" onClick={onClose}>
      <div className="mx-auto mt-4 flex w-full max-w-[800px] flex-1 flex-col overflow-hidden rounded-t-2xl bg-fondo shadow-[0_-8px_40px_rgba(16,24,40,0.3)]" onClick={(e) => e.stopPropagation()}>
        <div className="flex flex-wrap items-center gap-2 border-b border-bordo bg-white px-4 py-3">
          <p className="mr-2 truncate text-sm font-bold">{file.nome}</p>
          {attrezzo('testo', 'Testo')}
          {attrezzo('data', `Data di oggi`)}
          {attrezzo('firma', 'Firma', !firma)}
          {attrezzo('timbro', 'Timbro', !timbro)}
          <span className="text-[11px] text-spento">{strumento ? 'clicca sulla pagina dove va' : 'scegli cosa mettere, poi clicca dove va'}</span>
          <div className="ml-auto flex items-center gap-2">
            <button onClick={onClose} className="text-xs font-semibold text-tenue hover:text-inchiostro">annulla</button>
            <button onClick={() => void salva()} disabled={salvo || pezzi.length === 0}
                    className="rounded-full bg-blu px-4 py-1.5 text-sm font-bold text-white hover:bg-blu-scuro disabled:opacity-30">
              {salvo ? 'Salvo…' : 'Salva come nuovo PDF'}
            </button>
          </div>
        </div>
        {stato && <p className="border-b border-bordo bg-velo px-4 py-2 text-xs font-semibold text-inchiostro">{stato}</p>}

        <div className="flex-1 overflow-auto px-4 py-4">
          {pagine.length === 0 && !stato && <p className="py-10 text-center text-sm text-spento">Apro il documento…</p>}
          {pagine.map((pg) => {
            const s = scala(pg)
            return (
              <div key={pg.n} className="relative mx-auto mb-4 bg-white shadow-[0_2px_12px_rgba(16,24,40,0.15)]" style={{ width: LARGHEZZA, height: pg.h * s }}
                   onClick={(e) => clicPagina(e, pg)} onPointerMove={(e) => muovi(e, pg)} onPointerUp={fineTrascino}>
                <canvas ref={(el) => { tele.current[pg.n] = el }} className="block" />
                <div className={`absolute inset-0 ${strumento ? 'cursor-crosshair' : ''}`}>
                  {pezzi.filter((p) => p.pagina === pg.n).map((p) => (
                    <div key={p.id} onPointerDown={(e) => iniziaTrascino(e, p, pg)} onClick={(e) => e.stopPropagation()}
                         className={`absolute cursor-move select-none ${scelto === p.id ? 'ring-2 ring-blu' : 'ring-1 ring-transparent hover:ring-blu/40'}`}
                         style={{ left: p.x * s, top: p.y * s, width: p.w * s, height: p.h * s }}>
                      {p.tipo === 'testo' ? (
                        <input autoFocus={scelto === p.id && !p.testo} value={p.testo}
                               onChange={(e) => setPezzi((v) => v.map((x) => (x.id === p.id ? { ...x, testo: e.target.value } : x)))}
                               onPointerDown={(e) => e.stopPropagation()}
                               placeholder="scrivi qui"
                               className="h-full w-full bg-transparent font-sans text-navy outline-none"
                               style={{ fontSize: 11 * s, lineHeight: 1 }} />
                      ) : (
                        <img src={p.src} alt="" className="pointer-events-none h-full w-full object-contain" draggable={false} />
                      )}
                      {scelto === p.id && (
                        <button onClick={(e) => { e.stopPropagation(); togli(p.id) }} onPointerDown={(e) => e.stopPropagation()}
                                className="absolute -right-2.5 -top-2.5 flex h-5 w-5 items-center justify-center rounded-full bg-inchiostro text-[11px] font-bold text-white">×</button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
