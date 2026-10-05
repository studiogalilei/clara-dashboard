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

// CHI GALLEGGIA SI FA DA PARTE (gold, 6/10). Sul telefono il «+» di Oggi copriva la lista e
// la pallina di Clara copriva la bozza nella scheda. Come in Google e Apple: mentre scorri
// in giu' stai leggendo, e i bottoni galleggianti scendono fuori dallo schermo; appena
// risali, o torni in cima, tornano (come la barra di Safari: fermarsi non basta, se no
// ricoprono proprio la riga che stai leggendo). Sul computer non cambia niente.
export function useScorroGiu(soglia = 12): boolean {
  const [giu, setGiu] = useState(false)
  useEffect(() => {
    let ultimo = window.scrollY
    const su = () => {
      const y = window.scrollY
      if (y < 80) setGiu(false)
      else if (y - ultimo > soglia) setGiu(true)
      else if (ultimo - y > soglia) setGiu(false)
      ultimo = y
    }
    window.addEventListener('scroll', su, { passive: true })
    return () => window.removeEventListener('scroll', su)
  }, [soglia])
  return giu
}
