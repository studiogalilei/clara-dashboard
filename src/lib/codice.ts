// I CODICI (Dre, 26/9/2026: «il codice identificativo dei documenti, come lo
// ritrovo? Dopo devo ricordarmi il codice? Dobbiamo dargli delle regole»).
//
// IL PRINCIPIO: un codice non serve a ricordarlo a memoria, serve a essere
// INCOLLATO. Lo vedi su un PDF che il cliente ti rimanda, lo incolli in ⌘K e
// atterri sulla cosa giusta. Quindi deve dire da solo di chi è e cosa è.
//
// LA FORMA, la stessa che i preventivi avevano già dal 14/9:
//
//     SG-MK-2026-003        un preventivo: linea, anno, progressivo nell'anno
//     SG-201                un'azienda: il numero permanente, dal 31/8
//     SG-201-AN-02          una cosa che appartiene a quell'azienda
//
// Le cose che escono dallo Studio con una loro vita commerciale (i preventivi)
// tengono il numero di linea: è quello che finisce in fattura e nei contratti.
// Tutto il resto eredita il numero dell'azienda e aggiunge il tipo, così
// leggendo il codice sai già di chi è senza aprire niente.
//
// LE TRE REGOLE
//   1. lo genera il sistema quando la cosa nasce, e non cambia mai più;
//   2. è cercabile in ⌘K, intero o solo il pezzo dell'azienda;
//   3. sta scritto sulla cosa: in alto a destra sul PDF, come dicono le regole
//      documenti («RIFERIMENTO, codice, mese e anno»).
//
// I codici già usciti (preventivi mandati, PDF nelle mani dei clienti) restano
// come sono: rigenerarli vorrebbe dire avere in giro documenti con un
// riferimento che non esiste più.

export type TipoCodice = 'AN' | 'PR' | 'PG' | 'DOC' | 'CN'

export const TIPO_NOME: Record<TipoCodice, string> = {
  AN: 'Analisi', PR: 'Preventivo', PG: 'Progetto', DOC: 'Documento', CN: 'Contratto',
}

/** SG-201: il numero permanente dell'azienda. Null finché non ha risposto. */
export function codiceAzienda(sg_id: number | null | undefined): string | null {
  return sg_id == null ? null : `SG-${String(sg_id).padStart(3, '0')}`
}

/** SG-201-AN-02: una cosa che appartiene a quell'azienda. */
export function codiceDi(sg_id: number | null | undefined, tipo: TipoCodice, n: number): string | null {
  const a = codiceAzienda(sg_id)
  return a && `${a}-${tipo}-${String(n).padStart(2, '0')}`
}

export interface Letto { azienda: number | null; tipo: TipoCodice | null; n: number | null; linea: string | null; anno: number | null }

/** Legge un codice incollato, in qualunque delle forme che usiamo. */
export function leggiCodice(testo: string): Letto | null {
  const t = testo.trim().toUpperCase().replace(/\s+/g, '')
  // SG-MK-2026-003 (preventivo)
  let m = /^SG-(MK|AI|SW|AZ)-(\d{4})-(\d{1,4})$/.exec(t)
  if (m) return { azienda: null, tipo: 'PR', n: Number(m[3]), linea: m[1], anno: Number(m[2]) }
  // SG-201-AN-02
  m = /^SG-0*(\d{1,7})-(AN|PR|PG|DOC|CN)-(\d{1,4})$/.exec(t)
  if (m) return { azienda: Number(m[1]), tipo: m[2] as TipoCodice, n: Number(m[3]), linea: null, anno: null }
  // SG-201, o anche solo 201 quando è chiaro che è un codice
  m = /^(?:SG-?)?0*(\d{1,7})$/.exec(t)
  if (m) return { azienda: Number(m[1]), tipo: null, n: null, linea: null, anno: null }
  return null
}

/** Sembra un codice? Serve alla ricerca per decidere dove cercare. */
export function paiUnCodice(testo: string): boolean {
  return leggiCodice(testo) !== null && /\d/.test(testo)
}
