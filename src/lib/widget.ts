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

export type Chiave =
  | 'pipeline' | 'prospect' | 'calendario' | 'oggi'
  | 'analytics' | 'vault' | 'plugin' | 'impostazioni'
  | 'tutti'
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
  { chiave: 'pipeline', nome: 'Dashboard', cosa: 'La giornata: fasi, coda, avvisi', zona: 'menu', fisso: true,
    ruoli: ['ceo', 'coordinamento'],
    icona: 'M4 5h4v14H4zM10 5h4v9h-4zM16 5h4v6h-4z' },
  // nota sui nomi: la chiave 'prospect' e' la sezione che Dre chiama Pipeline
  // (rinominata il 3/9); la chiave 'pipeline' e' la home. Le chiavi non si
  // toccano perche' ci sono appese le preferenze salvate.
  { chiave: 'prospect', nome: 'Pipeline', cosa: 'Prospect e clienti, bacheca ed elenco', zona: 'menu', fisso: true,
    ruoli: ['ceo', 'coordinamento'],
    icona: 'M8 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM2 21c0-3.3 2.7-6 6-6s6 2.7 6 6M17 8a3 3 0 1 0 0-6M22 21c0-2.8-1.9-5.1-4.5-5.8' },
  { chiave: 'calendario', nome: 'Calendario', cosa: 'Call, follow-up e scadenze', zona: 'menu', fisso: true,
    ruoli: ['ceo', 'coordinamento'],
    icona: 'M6 5h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2zM8 3v4M16 3v4M4 11h16' },
  { chiave: 'oggi', nome: 'Task', cosa: 'Le tue attività, On go o Week picture', zona: 'menu', fisso: true,
    ruoli: ['ceo', 'coordinamento'],
    icona: 'M4 6h16M4 12h10M4 18h7' },
  { chiave: 'tutti', nome: 'Tutti', cosa: 'Clienti e prospect, con canone e chi li segue', zona: 'menu',
    ruoli: ['ceo', 'coordinamento'],
    icona: 'M20 7h-9M14 17H5M17 14a3 3 0 1 0 0 6 3 3 0 0 0 0-6zM7 4a3 3 0 1 0 0 6 3 3 0 0 0 0-6z' },
  // solo per il coordinamento (Dre, 4/9): i progetti sono il mondo della
  // delivery. Dre li vede comunque nella scheda del suo cliente.
  { chiave: 'progetti', nome: 'Progetti', cosa: 'Il lavoro a scadenza: chi, quando, quanto', zona: 'menu',
    ruoli: ['coordinamento'],
    icona: 'M4 7h16v13H4zM4 7l2-3h12l2 3M9 12h6' },
  { chiave: 'analytics', nome: 'Analytics', cosa: 'I numeri: funnel, ricorrente, canali', zona: 'sistema',
    ruoli: ['ceo', 'coordinamento'],
    icona: 'M5 20v-6M11 20V6M17 20v-9M3 20h18' },
  { chiave: 'vault', nome: 'Documenti', cosa: 'I file, agganciati ai prospect', zona: 'sistema', fisso: true,
    ruoli: ['ceo', 'coordinamento'],
    icona: 'M5 8h14a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1zM8 8V6a4 4 0 0 1 8 0v2M12 13v3' },
  { chiave: 'plugin', nome: 'Agenti e Skills', cosa: 'Cosa sa fare Clara, e i collegamenti', zona: 'sistema',
    ruoli: ['ceo'],
    icona: 'M9 7V3M15 7V3M7 7h10v5a5 5 0 0 1-5 5 5 5 0 0 1-5-5V7zM12 17v4' },
]

export const widgetDi = (c: Chiave) => WIDGET.find((w) => w.chiave === c)

// ── chi sei ───────────────────────────────────────────────────────
// Finche' gli accessi non sono legati ai ruoli sul database, il ruolo e'
// una scelta locale. Serve gia' adesso per provare cosa vede Giacomo.
export function mioRuolo(): Ruolo {
  try { return (localStorage.getItem('mio-ruolo') as Ruolo) || 'ceo' } catch { return 'ceo' }
}
export function scegliRuolo(r: Ruolo) {
  try { localStorage.setItem('mio-ruolo', r) } catch { /* niente */ }
}

// ── chi arriva dove: lo decide Dre ────────────────────────────────
type Accessi = Partial<Record<Chiave, Ruolo[]>>
export function accessi(): Accessi {
  try { return JSON.parse(localStorage.getItem('widget-accessi') ?? '{}') } catch { return {} }
}
export function salvaAccessi(a: Accessi) {
  try { localStorage.setItem('widget-accessi', JSON.stringify(a)) } catch { /* niente */ }
}
export function ruoliDi(w: Widget): Ruolo[] {
  return accessi()[w.chiave] ?? w.ruoli
}

// ── in che ordine li vuoi ─────────────────────────────────────────
export function ordine(): Chiave[] {
  try { return JSON.parse(localStorage.getItem('widget-ordine') ?? '[]') } catch { return [] }
}
export function salvaOrdine(o: Chiave[]) {
  try { localStorage.setItem('widget-ordine', JSON.stringify(o)) } catch { /* niente */ }
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
  try { return JSON.parse(localStorage.getItem('widget-nascosti') ?? '[]') } catch { return [] }
}
export function salvaNascosti(n: Chiave[]) {
  try { localStorage.setItem('widget-nascosti', JSON.stringify(n)) } catch { /* niente */ }
}

// il menu vero: quello a cui arrivi, meno quello che hai spento
export function menuDi(ruolo: Ruolo, zona: 'menu' | 'sistema'): Widget[] {
  const spenti = nascosti()
  return inOrdine(WIDGET.filter((w) =>
    w.zona === zona && ruoliDi(w).includes(ruolo) && (w.fisso || !spenti.includes(w.chiave))))
}
