import { useEffect, useState } from 'react'

// LO SCHERMO LARGO (29/9). Due copie dello stesso riquadro, una per il telefono
// e una per il computer, nascoste col CSS, caricavano entrambe i loro dati: in
// Oggi il radar faceva le sue letture tre volte. Una copia che non si vede non
// si disegna, cosi' non carica niente.
export function useSchermoLargo(minimo = 1024): boolean {
  const q = `(min-width: ${minimo}px)`
  const [largo, setLargo] = useState(() => {
    try { return window.matchMedia(q).matches } catch { return true }
  })
  useEffect(() => {
    try {
      const m = window.matchMedia(q)
      const su = (e: MediaQueryListEvent) => setLargo(e.matches)
      m.addEventListener('change', su)
      return () => m.removeEventListener('change', su)
    } catch { return undefined }
  }, [q])
  return largo
}
