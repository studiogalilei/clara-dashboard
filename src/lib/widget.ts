// I WIDGET (Dre, 3/9).
//
// Ogni pezzo della Dashboard e' un widget: dichiara chi e', cosa mostra e a
// chi serve. Le Impostazioni li accendono e li spengono, e Dre decide chi ha
// accesso a cosa. E' la stessa forma della scheda delle skill di Clara e del
// menu componibile: quando lo stesso schema torna tre volte da strade
// diverse, e' quello giusto.
//
// Aggiungere un widget vuol dire aggiungere una riga qui sotto: compare da
// solo nelle Impostazioni e nel menu, senza toccare nient'altro.

import { leggi as leggiPref, scrivi as scriviPref } from './preferenze'

export type Chiave =
  | 'pipeline' | 'prospect' | 'calendario' | 'oggi'
  | 'analytics' | 'vault' | 'plugin' | 'impostazioni'
  | 'tutti' | 'clara'
  | 'progetti'

export type Ruolo = 'ceo' | 'coordinamento'

export const RUOLI: Array<[Ruolo, string]> = [
  ['ceo', 'CEO'],
  ['coordinamento', 'Coordinamento'],
]

export interface Widget {
  chiave: Chiave
  nome: string
  cosa: string                 // una riga: cosa mostra, non cosa e'
  zona: 'menu' | 'sistema'
  icona: string                // path SVG 24x24, tratto
  ruoli: Ruolo[]               // chi ci arriva, salvo diverso ordine di Dre
  // fisso = l'ossatura della «Dashboard CEO 1» (Dre, 3/9): Dashboard,
  // Pipeline, Task, Calendario e Vault non si spengono, perche' sono il
  // lavoro di tutti i giorni e quattro interruttori che nessuno tocca sono
  // solo roba in mezzo
  fisso?: boolean
}

export const WIDGET: Widget[] = [
  // Intervista a Dre (9/9): cinque voci, meno pagine, ci si perde meno.
  // Le chiavi non si toccano: ci sono appese le preferenze salvate.
  // 'pipeline' = Oggi (la giornata, con le task sotto); 'prospect' = Aziende
  // (bacheca, foglio, preventivi). Task ('oggi') e Tutti ('tutti') non sono
  // piu' voci: vivono dentro Oggi e Aziende. Numeri e Widget stanno in
  // Impostazioni.
  { chiave: 'pipeline', nome: 'Oggi', cosa: 'Cosa aspetta te, poi le tue task', zona: 'menu', fisso: true,
    ruoli: ['ceo', 'coordinamento'],
    icona: 'M4 5h4v14H4zM10 5h4v9h-4zM16 5h4v6h-4z' },
  { chiave: 'prospect', nome: 'Aziende', cosa: 'Prospect e clienti: bacheca, foglio, preventivi', zona: 'menu', fisso: true,
    ruoli: ['ceo', 'coordinamento'],
    icona: 'M8 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM2 21c0-3.3 2.7-6 6-6s6 2.7 6 6M17 8a3 3 0 1 0 0-6M22 21c0-2.8-1.9-5.1-4.5-5.8' },
  { chiave: 'progetti', nome: 'Progetti', cosa: 'Il foglio dei progetti e la roadmap', zona: 'menu', fisso: true,
    ruoli: ['ceo', 'coordinamento'],
    icona: 'M4 7h16v13H4zM4 7l2-3h12l2 3M9 12h6' },
  { chiave: 'calendario', nome: 'Calendario', cosa: 'Call, follow-up e scadenze', zona: 'menu', fisso: true,
    ruoli: ['ceo', 'coordinamento'],
    icona: 'M6 5h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2zM8 3v4M16 3v4M4 11h16' },
  { chiave: 'clara', nome: 'Clara', cosa: 'Le cose che chiede, e la chat', zona: 'menu', fisso: true,
    ruoli: ['ceo', 'coordinamento'],
    icona: 'M12 3a9 9 0 1 0 9 9M12 3v6l4 2M12 3l-6 4M12 9l-3 6M12 9l6 3' },
  { chiave: 'vault', nome: 'Documenti', cosa: 'I file, agganciati alle aziende', zona: 'sistema', fisso: true,
    ruoli: ['ceo', 'coordinamento'],
    icona: 'M5 8h14a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1zM8 8V6a4 4 0 0 1 8 0v2M12 13v3' },
]

export const widgetDi = (c: Chiave) => WIDGET.find((w) => w.chiave === c)

// ── chi sei ───────────────────────────────────────────────────────
// Il ruolo, l'ordine e gli accessi sono preferenze: stanno nel browser per
// essere immediati e sul database per seguirti sul telefono (vedi
// preferenze.ts). Prima restavano solo qui e cambiavano da un dispositivo
// all'altro senza dirlo (revisione 4/9).
export function mioRuolo(): Ruolo {
  return (leggiPref('mio-ruolo') as Ruolo) || 'ceo'
}
export function scegliRuolo(r: Ruolo) {
  scriviPref('mio-ruolo', r)
}

// ── chi arriva dove: lo decide Dre ────────────────────────────────
type Accessi = Partial<Record<Chiave, Ruolo[]>>
export function accessi(): Accessi {
  try { return JSON.parse(leggiPref('widget-accessi', '{}')) } catch { return {} }
}
export function salvaAccessi(a: Accessi) {
  scriviPref('widget-accessi', JSON.stringify(a))
}
export function ruoliDi(w: Widget): Ruolo[] {
  return accessi()[w.chiave] ?? w.ruoli
}

// ── in che ordine li vuoi ─────────────────────────────────────────
export function ordine(): Chiave[] {
  try { return JSON.parse(leggiPref('widget-ordine', '[]')) } catch { return [] }
}
export function salvaOrdine(o: Chiave[]) {
  scriviPref('widget-ordine', JSON.stringify(o))
}

// i widget nell'ordine scelto: quelli mai spostati restano dove nascono
export function inOrdine(lista: Widget[]): Widget[] {
  const o = ordine()
  if (o.length === 0) return lista
  return [...lista].sort((a, b) => {
    const ia = o.indexOf(a.chiave), ib = o.indexOf(b.chiave)
    return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib)
  })
}

// ── cosa vuoi vedere tu: lo decide ognuno per se' ─────────────────
export function nascosti(): Chiave[] {
  try { return JSON.parse(leggiPref('widget-nascosti', '[]')) } catch { return [] }
}
export function salvaNascosti(n: Chiave[]) {
  scriviPref('widget-nascosti', JSON.stringify(n))
}

// il menu vero: quello a cui arrivi, meno quello che hai spento
export function menuDi(ruolo: Ruolo, zona: 'menu' | 'sistema'): Widget[] {
  const spenti = nascosti()
  return inOrdine(WIDGET.filter((w) =>
    w.zona === zona && ruoliDi(w).includes(ruolo) && (w.fisso || !spenti.includes(w.chiave))))
}
