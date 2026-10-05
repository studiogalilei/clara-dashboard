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
