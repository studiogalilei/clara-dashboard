// I SEI TONI del Workspace (src/index.css, 17/10) come classi Tailwind, scritte per intero
// perche' Tailwind le trova solo cosi'. Il significato di ogni tono sta in index.css.
import type { Tono } from './regole'

export const TONO: Record<Tono, { testo: string; segno: string; morbido: string }> = {
  ok: { testo: 'text-ok-testo', segno: 'bg-ok-segno', morbido: 'border-ok-bordo bg-ok-fondo text-ok-testo' },
  no: { testo: 'text-no-testo', segno: 'bg-no-segno', morbido: 'border-no-bordo bg-no-fondo text-no-testo' },
  attesa: { testo: 'text-attesa-testo', segno: 'bg-attesa-segno', morbido: 'border-attesa-bordo bg-attesa-fondo text-attesa-testo' },
  noi: { testo: 'text-noi-testo', segno: 'bg-noi-segno', morbido: 'border-noi-bordo bg-noi-fondo text-noi-testo' },
  loro: { testo: 'text-loro-testo', segno: 'bg-loro-segno', morbido: 'border-loro-bordo bg-loro-fondo text-loro-testo' },
  neutro: { testo: 'text-tenue', segno: 'bg-bordo', morbido: 'border-bordo bg-white text-tenue' },
}
