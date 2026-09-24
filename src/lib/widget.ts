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
  | 'progetti' | 'preventivi' | 'chat' | 'feedback'

export type Ruolo = 'ceo' | 'coordinamento'

// i ruoli veri dello Studio (documento «Divisioni e responsabilita'» di Giacomo)
export const NOME_RUOLO: Record<string, string> = {
  ceo: 'CEO', coordinamento: 'Coordinamento', manager: 'Marketing manager',
  specialist: 'Ad specialist', frontend: 'Frontend',
}

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
  immagine?: string            // in alternativa: un file in public/, usato come maschera (il marchio)
  ruoli: Ruolo[]               // chi ci arriva, salvo diverso ordine di Dre
  // fisso = l'ossatura della «Dashboard CEO 1» (Dre, 3/9): Dashboard,
  // Pipeline, Task, Calendario e Vault non si spengono, perche' sono il
  // lavoro di tutti i giorni e quattro interruttori che nessuno tocca sono
  // solo roba in mezzo
  fisso?: boolean
  // base = ce l'hanno tutti (Dre, 11/9): Oggi, Aziende, Calendario, Clara,
  // Documenti. Il resto si chiede e lo concede un ceo (lib/accessi.ts).
  base?: boolean
}

export const WIDGET: Widget[] = [
  // Intervista a Dre (9/9): cinque voci, meno pagine, ci si perde meno.
  // Le chiavi non si toccano: ci sono appese le preferenze salvate.
  // 'pipeline' = Oggi (la giornata, con le task sotto); 'prospect' = Aziende
  // (bacheca, foglio, preventivi). Task ('oggi') e Tutti ('tutti') non sono
  // piu' voci: vivono dentro Oggi e Aziende. Numeri e Widget stanno in
  // Impostazioni.
  { chiave: 'pipeline', nome: 'Oggi', cosa: 'Cosa aspetta te, poi le tue task', zona: 'menu', fisso: true, base: true,
    ruoli: ['ceo', 'coordinamento'],
    icona: 'M4 5h4v14H4zM10 5h4v9h-4zM16 5h4v6h-4z' },
  // Dre, 12/9: prima della vendita e dopo la vendita. Le chiavi restano
  // ('prospect', 'progetti'): ci sono appese le preferenze e gli accessi.
  { chiave: 'prospect', nome: 'Pipeline', cosa: 'Chi sta arrivando: dalla risposta alla firma', zona: 'menu', fisso: true, base: true,
    ruoli: ['ceo', 'coordinamento'],
    icona: 'M3 4h18l-7 8v6l-4 2v-8L3 4z' },
  { chiave: 'progetti', nome: 'Clienti', cosa: 'Chi è dentro: prova, retainer, progetti, pagamenti', zona: 'menu', fisso: true,
    ruoli: ['ceo', 'coordinamento'],
    icona: 'M8 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM2 21c0-3.3 2.7-6 6-6s6 2.7 6 6M17 8a3 3 0 1 0 0-6M22 21c0-2.8-1.9-5.1-4.5-5.8' },
  { chiave: 'calendario', nome: 'Calendario', cosa: 'Call, follow-up e scadenze', zona: 'menu', fisso: true, base: true,
    ruoli: ['ceo', 'coordinamento'],
    icona: 'M6 5h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2zM8 3v4M16 3v4M4 11h16' },
  { chiave: 'vault', nome: 'Documenti', cosa: 'La cassaforte: brand, modelli, file dei clienti', immagine: 'sg-intreccio.svg', zona: 'sistema', fisso: true, base: true,
    ruoli: ['ceo', 'coordinamento'],
    icona: 'M5 8h14a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1zM8 8V6a4 4 0 0 1 8 0v2M12 13v3' },
  { chiave: 'clara', nome: 'Posta di Clara', cosa: 'Bozze, richieste e domande da decidere', zona: 'sistema', fisso: true, base: true,
    ruoli: ['ceo', 'coordinamento'],
    icona: 'M3 7.5A2.5 2.5 0 0 1 5.5 5h13A2.5 2.5 0 0 1 21 7.5v9a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 16.5v-9zM3.5 8l8.5 6 8.5-6' },
  { chiave: 'preventivi', nome: 'Preventivi', cosa: 'Crea, manda, segna accettato: e vedi cosa gira', zona: 'menu', ruoli: ['ceo'], fisso: true,
    icona: 'M7 3h7l5 5v13H7zM14 3v5h5M10 12h6M10 16h6' },
  // i passaggi (Dre, 15/9): «il mood non e' conversazionale, e' il luogo
  // per mandare documenti: tanto su WhatsApp ci parliamo, ma i documenti
  // li' si perdono». Ce l'hanno tutti. La chiave resta 'chat'.
  { chiave: 'chat', nome: 'Condividi', cosa: 'Passarsi documenti, legati al cliente', zona: 'sistema', fisso: true, base: true,
    ruoli: ['ceo', 'coordinamento'],
    icona: 'M21 11.5a8.4 8.4 0 0 1-9 8.4 8.6 8.6 0 0 1-3.8-.9L3 20.5l1.5-4.5a8.4 8.4 0 0 1-.9-3.8 8.4 8.4 0 0 1 8.4-8.4h.5a8.4 8.4 0 0 1 8 8z' },
  // LA BETA (Dre, 15/9): gli accessi vanno alla squadra, e quello che non
  // va lo sanno solo loro. Ce l'hanno tutti, ed e' l'ultima voce apposta:
  // si usa dopo, quando una cosa ha dato fastidio.
  { chiave: 'feedback', nome: 'Cosa cambieresti', cosa: 'Quello che non va o che vorresti: lo leggo io', zona: 'sistema', fisso: true, base: true,
    ruoli: ['ceo', 'coordinamento'],
    icona: 'M12 3a9 9 0 0 1 9 9c0 4.5-4 8.2-9 8.2a10 10 0 0 1-2.6-.3L4 21.5l1.2-3.4A8.6 8.6 0 0 1 3 12a9 9 0 0 1 9-9zM12 8v5M12 16h.01' },
  { chiave: 'analytics', nome: 'Numeri', cosa: 'Risposte, conversioni e andamento dell\'outbound', zona: 'sistema', fisso: true,
    ruoli: ['ceo', 'coordinamento'],
    icona: 'M4 19h16M6 16V9M10 16V5M14 16v-6M18 16v-9' },
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

// hai questo widget? di base, o da ceo, o perche' te l'hanno concesso
export function haAccesso(w: Widget, ruolo: Ruolo, concessi: ReadonlySet<Chiave>): boolean {
  return Boolean(w.base) || ruolo === 'ceo' || concessi.has(w.chiave)
}

// il menu vero: quello a cui arrivi, meno quello che hai spento
// IL MENU ESSENZIALE (Dre, 23/9): «non overbuildato, architettura semplice».
// Restano Pipeline, Clienti, Calendario, Posta, Preventivi. Oggi, Documenti,
// Condividi, Cosa cambieresti e Numeri spariscono dal menu (le pagine restano,
// si riaccendono da Impostazioni). Acceso di default.
const FUORI_DAL_MENU_CORTO: Chiave[] = ['pipeline', 'vault', 'chat', 'feedback', 'analytics']
export function menuEssenziale(): boolean {
  return leggiPref('menu-essenziale', 'si') === 'si'
}
export function menuDi(ruolo: Ruolo, zona: 'menu' | 'sistema', concessi: ReadonlySet<Chiave> = new Set()): Widget[] {
  const spenti = nascosti()
  const corto = menuEssenziale()
  return inOrdine(WIDGET.filter((w) =>
    w.zona === zona && haAccesso(w, ruolo, concessi) && ruoliDi(w).includes(ruolo) && (w.fisso || !spenti.includes(w.chiave))
    // Oggi sparisce dal menu corto solo per il ceo: per chi consegna e' la prima pagina (Dre, 24/9)
    && !(corto && FUORI_DAL_MENU_CORTO.includes(w.chiave) && !(w.chiave === 'pipeline' && ruolo !== 'ceo'))))
}
