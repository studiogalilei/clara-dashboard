import { scrivi } from './preferenze'

// IL PERCHE' COSI' (gold, 6/10): sopra la bozza, il ragionamento di Clara in una riga,
// cosi' Dre giudica prima di leggere. Senza codici (INT-01, «si':»): parole sue.
export function percheCosi(perche: string | null | undefined): string {
  const t = (perche ?? '')
    .replace(/^\s*s[iì]'?\s*:\s*/i, '')
    .replace(/[,;]?\s*\(?\bINT-[A-Z0-9]+\b\)?/g, '')
    .replace(/\s+,/g, ',').replace(/\s{2,}/g, ' ').trim()
  if (!t) return ''
  const frase = t.length > 220 ? t.slice(0, 220).replace(/[,;\s]+\S*$/, '') + '…' : t
  return frase.charAt(0).toUpperCase() + frase.slice(1)
}

// DA OGGI ALLA POSTA, GIA' APERTA (gold, 6/10): «Leggi e approva» nella carta Adesso porta
// nella Posta sulla conversazione giusta, dentro la fila. Si segna qui quale aprire; la Posta
// la apre appena ha caricato e la dimentica.
let daAprire: number | null = null
export function apriInPosta(propostaId: number) {
  daAprire = propostaId
  scrivi('clara-posta', 'conversazioni')
  window.dispatchEvent(new Event('clara:vai-posta'))
}
export function prendiDaAprire(): number | null {
  const id = daAprire
  daAprire = null
  return id
}
