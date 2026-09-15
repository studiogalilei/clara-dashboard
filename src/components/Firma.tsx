import { useEffect, useRef, useState } from 'react'
import { leggiFirma, scriviFirma, leggiTimbro, scriviTimbro } from '../lib/firma'
import { Card, TitoloCard, Micro } from './ui'

// LA TUA FIRMA (Impostazioni): la disegni col trackpad o col dito, oppure
// carichi un PNG. Da li' in poi «Compila PDF» te la mette dove clicchi.
// Sotto, il timbro di Studio Galilei: uno per tutti.

function FoglioFirma({ onPronta }: { onPronta: (dataUrl: string) => void }) {
  const ref = useRef<HTMLCanvasElement>(null)
  const [vuoto, setVuoto] = useState(true)
  const giu = useRef(false)

  useEffect(() => {
    const c = ref.current!
    const ctx = c.getContext('2d')!
    ctx.lineWidth = 2.4; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.strokeStyle = '#1C2E6E'
  }, [])

  function punto(e: React.PointerEvent<HTMLCanvasElement>) {
    const c = ref.current!, r = c.getBoundingClientRect()
    return [(e.clientX - r.left) * (c.width / r.width), (e.clientY - r.top) * (c.height / r.height)] as const
  }
  function inizia(e: React.PointerEvent<HTMLCanvasElement>) {
    giu.current = true; ref.current!.setPointerCapture(e.pointerId)
    const ctx = ref.current!.getContext('2d')!; const [x, y] = punto(e); ctx.beginPath(); ctx.moveTo(x, y)
  }
  function traccia(e: React.PointerEvent<HTMLCanvasElement>) {
    if (!giu.current) return
    const ctx = ref.current!.getContext('2d')!; const [x, y] = punto(e); ctx.lineTo(x, y); ctx.stroke(); setVuoto(false)
  }
  function fine() { giu.current = false }
  function pulisci() { const c = ref.current!; c.getContext('2d')!.clearRect(0, 0, c.width, c.height); setVuoto(true) }

  // ritaglia il bianco intorno, cosi' la firma nel PDF non porta aria
  function ritaglia(): string {
    const c = ref.current!, ctx = c.getContext('2d')!
    const img = ctx.getImageData(0, 0, c.width, c.height).data
    let x0 = c.width, y0 = c.height, x1 = 0, y1 = 0
    for (let y = 0; y < c.height; y++) for (let x = 0; x < c.width; x++) {
      if (img[(y * c.width + x) * 4 + 3] > 10) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y }
    }
    if (x1 <= x0) return c.toDataURL('image/png')
    const m = 8, out = document.createElement('canvas')
    out.width = x1 - x0 + m * 2; out.height = y1 - y0 + m * 2
    out.getContext('2d')!.drawImage(c, x0 - m, y0 - m, out.width, out.height, 0, 0, out.width, out.height)
    return out.toDataURL('image/png')
  }

  return (
    <div>
      <canvas ref={ref} width={720} height={240}
              onPointerDown={inizia} onPointerMove={traccia} onPointerUp={fine} onPointerLeave={fine}
              className="w-full touch-none rounded-lg border border-bordo bg-white" style={{ aspectRatio: '3 / 1' }} />
      <div className="mt-2 flex gap-2">
        <button onClick={() => onPronta(ritaglia())} disabled={vuoto}
                className="rounded-full bg-blu px-4 py-1.5 text-sm font-bold text-white hover:bg-blu-scuro disabled:opacity-30">Salva questa firma</button>
        <button onClick={pulisci} className="rounded-full border border-bordo px-4 py-1.5 text-sm font-semibold text-tenue hover:border-spento">Ricomincia</button>
      </div>
    </div>
  )
}

export default function Firma({ ceo }: { ceo: boolean }) {
  const [firma, setFirma] = useState<string | null | undefined>(undefined)
  const [disegno, setDisegno] = useState(false)
  const [timbro, setTimbro] = useState<string | null>(null)
  const [esito, setEsito] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const timbroRef = useRef<HTMLInputElement>(null)

  useEffect(() => { void leggiFirma().then(setFirma); void leggiTimbro().then(setTimbro) }, [])

  async function salva(dataUrl: string | null) {
    const err = await scriviFirma(dataUrl)
    setEsito(err ? 'Non salvata: ' + err : dataUrl ? 'Firma salvata' : 'Firma tolta')
    if (!err) { setFirma(dataUrl); setDisegno(false) }
    setTimeout(() => setEsito(null), 2500)
  }
  function daFile(f: File) {
    const r = new FileReader(); r.onload = () => void salva(String(r.result)); r.readAsDataURL(f)
  }
  async function caricaTimbro(f: File) {
    const err = await scriviTimbro(f)
    setEsito(err ? 'Timbro non salvato: ' + err : 'Timbro salvato')
    if (!err) setTimbro(await leggiTimbro())
    setTimeout(() => setEsito(null), 2500)
  }

  return (
    <Card className="p-5">
      <TitoloCard>Firma</TitoloCard>
      <p className="mt-1 text-xs text-tenue">Una volta sola. Poi in «Compila PDF» clicchi dove va e ci finisce lei, con la data accanto.</p>
      {firma === undefined ? null : firma && !disegno ? (
        <div className="mt-3 flex flex-wrap items-center gap-4">
          <img src={firma} alt="la tua firma" className="h-16 max-w-[260px] rounded-lg border border-bordo bg-white object-contain px-3 py-1" />
          <div className="flex gap-2">
            <button onClick={() => setDisegno(true)} className="rounded-full border border-bordo px-3.5 py-1.5 text-xs font-bold text-navy hover:border-navy">Rifalla</button>
            <button onClick={() => void salva(null)} className="rounded-full px-3.5 py-1.5 text-xs font-semibold text-spento hover:text-red-700">Togli</button>
          </div>
        </div>
      ) : (
        <div className="mt-3">
          <Micro>Firma qui dentro, col trackpad o col dito</Micro>
          <div className="mt-1"><FoglioFirma onPronta={(d) => void salva(d)} /></div>
          <p className="mt-2 text-xs text-spento">
            Oppure <button onClick={() => fileRef.current?.click()} className="font-semibold text-blu hover:underline">carica un PNG</button> con lo sfondo trasparente.
            {firma && <> <button onClick={() => setDisegno(false)} className="ml-2 text-spento hover:text-inchiostro">annulla</button></>}
          </p>
          <input ref={fileRef} type="file" accept="image/png" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) daFile(f); e.target.value = '' }} />
        </div>
      )}

      <div className="mt-4 border-t border-velo pt-3">
        <Micro>Il timbro di Studio Galilei</Micro>
        <div className="mt-1.5 flex flex-wrap items-center gap-4">
          {timbro ? <img src={timbro} alt="timbro" className="h-16 max-w-[200px] rounded-lg border border-bordo bg-white object-contain p-1" />
                  : <span className="text-sm text-spento">Nessun timbro ancora.</span>}
          {ceo && (
            <>
              <button onClick={() => timbroRef.current?.click()} className="rounded-full border border-bordo px-3.5 py-1.5 text-xs font-bold text-navy hover:border-navy">
                {timbro ? 'Cambia' : 'Carica il timbro (PNG)'}
              </button>
              <input ref={timbroRef} type="file" accept="image/png" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) void caricaTimbro(f); e.target.value = '' }} />
            </>
          )}
        </div>
      </div>
      {esito && <p className="mt-2 text-xs font-semibold text-green-700">{esito}</p>}
    </Card>
  )
}
