// LE NOVITA' (Dre, 17/9): «quando ci sono modifiche, quando rientrano
// appare un banner tipo quelli delle nuove feature, con le stelle e
// "lascia un feedback": un voto onesto sull'utilita' della feature».
//
// Una riga per ogni cosa nuova che vale la pena dire. La piu' recente sta
// in cima. La chiave e' fissa: e' quella che finisce nel voto (feedback.
// novita) e nella preferenza «novita-viste», quindi non si cambia dopo.
// Si scrive per chi legge, non per noi: cosa ci fa, non come e' fatto.

export interface Novita {
  chiave: string
  data: string          // AAAA-MM-GG
  titolo: string
  testo: string
}

export const NOVITA: Novita[] = [
  {
    chiave: 'piano-2026-09-17',
    data: '2026-09-17',
    titolo: 'Clara fa il piano',
    testo: 'Dopo una call, o quando riprendi in mano un cliente, sulla sua scheda c\'è «Fammi il piano»: Clara mette in fila le cose da fare giorno per giorno, tu togli quello che non serve e con un clic diventano task. Funziona anche scrivendole «fammi un piano per Klavzar». E il logo SG in alto riporta sempre a Oggi.',
  },
]

// la piu' recente che questa persona non ha ancora visto
export function daMostrare(viste: string[]): Novita | null {
  return NOVITA.find((n) => !viste.includes(n.chiave)) ?? null
}
