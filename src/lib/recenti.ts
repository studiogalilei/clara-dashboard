// VISTI DI RECENTE (Dre, 26/9): su un software vero non ricominci mai da zero.
// Le ultime dieci aziende che hai aperto, sul tuo browser, in ordine di tempo.
const CHIAVE = 'sg:recenti'
const QUANTI = 10

export interface Recente { id: string; nome: string; il: number }

export function recenti(): Recente[] {
  try { return JSON.parse(localStorage.getItem(CHIAVE) || '[]') as Recente[] } catch { return [] }
}

export function segnaRecente(id: string, nome: string) {
  try {
    const lista = recenti().filter((r) => r.id !== id)
    lista.unshift({ id, nome, il: Date.now() })
    localStorage.setItem(CHIAVE, JSON.stringify(lista.slice(0, QUANTI)))
  } catch { /* niente */ }
}
