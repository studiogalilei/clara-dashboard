// LA VERSIONE SNELLA: i ganci che usano le schermate (dati che si rifanno, l'avviso in basso).
import { useCallback, useEffect, useRef, useState } from 'react'

export interface Avviso { testo: string; annulla?: () => void }

/** Una riga in basso che dice cosa e' successo, con «Annulla» per qualche secondo. */
export function useAvviso() {
  const [avviso, setAvviso] = useState<Avviso | null>(null)
  const t = useRef(0)
  const mostra = useCallback((a: Avviso) => {
    window.clearTimeout(t.current)
    setAvviso(a)
    t.current = window.setTimeout(() => setAvviso(null), a.annulla ? 7000 : 3500)
  }, [])
  useEffect(() => () => window.clearTimeout(t.current), [])
  const vista = (
    <div aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-[calc(76px+env(safe-area-inset-bottom))] z-40 flex justify-center px-4 lg:bottom-6">
      {avviso && (
        <div className="pointer-events-auto flex max-w-md items-center gap-3 rounded-xl bg-inchiostro px-4 py-3 text-[14px] text-white shadow-lg">
          <span>{avviso.testo}</span>
          {avviso.annulla && (
            <button onClick={() => { avviso.annulla?.(); setAvviso(null) }}
                    className="min-h-9 shrink-0 rounded-full px-2 font-bold text-blue-200 underline-offset-2 hover:underline focus-visible:outline-white">
              Annulla
            </button>
          )}
        </div>
      )}
    </div>
  )
  return { mostra, vista }
}

/** I dati di una schermata: carica, si rifa' quando torni sull'app e ogni 2 minuti mentre la guardi. */
export function useDati<T>(carica: () => Promise<T>, dipende: unknown[] = []) {
  const [dati, setDati] = useState<T | null>(null)
  const [errore, setErrore] = useState<string | null>(null)
  const [carica_, setCarica] = useState(true)
  const giro = useRef(0)
  const rifai = useCallback(async () => {
    const mio = ++giro.current
    try {
      const d = await carica()
      if (mio === giro.current) { setDati(d); setErrore(null) }
    } catch (e) {
      if (mio === giro.current) setErrore(e instanceof Error ? e.message : String(e))
    } finally {
      if (mio === giro.current) setCarica(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dipende)
  useEffect(() => {
    setCarica(true)
    void rifai()
    const vis = () => { if (document.visibilityState === 'visible') void rifai() }
    document.addEventListener('visibilitychange', vis)
    const t = window.setInterval(() => { if (document.visibilityState === 'visible') void rifai() }, 120_000)
    return () => { document.removeEventListener('visibilitychange', vis); window.clearInterval(t) }
  }, [rifai])
  return { dati, setDati, errore, caricando: carica_ && dati === null, rifai }
}

/** Il link a una pagina del Workspace completo (la shell vecchia). */
export function linkCompleto(dove: string): string {
  return `#/${dove}`
}

/** L'indirizzo e' della versione snella? (#/s, #/s/oggi, #/s/lead/<id>...) */
export function inSnella(hash: string): boolean {
  return /^#\/s(\/|$)/.test(hash)
}
