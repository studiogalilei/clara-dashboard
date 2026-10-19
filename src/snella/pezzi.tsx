// LA VERSIONE SNELLA: i pezzi piccoli che usano tutte le schermate.
// Bianco, testo grande, niente fronzoli. Il colore dice un significato e basta (17/10, i sei toni
// di src/index.css): verde va bene, rosso no o in ritardo, ambra da guardare, blu noi e le azioni,
// cotto loro, grigio neutro. Sempre con una parola accanto.
import { tonoStato, type Tono } from './regole'
import { TONO } from './toni'
const ICONE = {
  oggi: 'M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z',
  lead: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75',
  campagne: 'M3 3v18h18M7 15l4-4 3 3 5-6',
  tutti: 'M3 5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5zM3 9h18M3 15h18M9 9v12',
  telefono: 'M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.79 19.79 0 0 1 2.12 4.18 2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z',
  indietro: 'M15 18l-6-6 6-6',
  esterno: 'M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3',
  cerca: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.35-4.35',
  video: 'M23 7l-7 5 7 5V7zM14 5H3a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2z',
  ok: 'M22 11.08V12a10 10 0 1 1-5.93-9.14M22 4L12 14.01l-3-3',
  avviso: 'M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z',
  campana: 'M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0',
  condividi: 'M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8M16 6l-4-4-4 4M12 2v13',
  cellulare: 'M7 2h10a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zM11 18h2',
  divieto: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM4.93 4.93l14.14 14.14',
}

export type NomeIcona = keyof typeof ICONE

export function Icona({ nome, className = 'h-5 w-5' }: { nome: NomeIcona; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"
         className={className} aria-hidden="true">
      <path d={ICONE[nome]} />
    </svg>
  )
}

/** Una sezione: il titolo con il segno del suo tono (una barretta) e quanti sono, nello stesso colore. */
export function Sezione({ titolo, conta, children, id, tono }: {
  titolo: string; conta?: number | null; children: React.ReactNode; id?: string; tono?: Tono
}) {
  const t = tono ? TONO[tono] : null
  return (
    <section aria-labelledby={id} className="mt-8 first:mt-0">
      <h2 id={id} className="mb-3 flex items-center gap-2.5 text-[19px] font-bold text-inchiostro">
        {t && <span aria-hidden="true" className={`h-5 w-1.5 shrink-0 rounded-full ${t.segno}`} />}
        {titolo}
        {conta != null && (
          <span className={`inline-flex min-w-7 items-center justify-center rounded-full border px-2 text-[14px] font-bold leading-6 ${conta > 0 && t ? t.morbido : 'border-bordo text-tenue'}`}>
            {conta}
          </span>
        )}
      </h2>
      {children}
    </section>
  )
}

/** Il caricamento vero: righe grigie della forma di quello che arriva. */
export function Carico({ righe = 3, etichetta = 'Carico i dati' }: { righe?: number; etichetta?: string }) {
  return (
    <div role="status" aria-live="polite" className="space-y-2.5">
      <span className="sr-only">{etichetta}…</span>
      {Array.from({ length: righe }, (_, i) => (
        <div key={i} className="h-[72px] animate-pulse rounded-xl bg-velo motion-reduce:animate-none" />
      ))}
    </div>
  )
}

export function Errore({ testo, riprova }: { testo: string; riprova?: () => void }) {
  return (
    <div role="alert" className="rounded-xl border border-no-bordo bg-no-fondo px-4 py-3 text-[15px] text-no-testo">
      <p className="font-semibold">Non riesco a leggere i dati.</p>
      <p className="mt-0.5 text-[14px]">{testo}</p>
      {riprova && (
        <button onClick={riprova} className="mt-2 min-h-11 rounded-full border border-no-bordo bg-white px-4 text-[14px] font-semibold text-no-testo hover:bg-no-fondo">
          Riprova
        </button>
      )}
    </div>
  )
}

export function Vuoto({ children }: { children: React.ReactNode }) {
  return <p className="rounded-xl border border-dashed border-bordo px-4 py-5 text-center text-[15px] text-tenue">{children}</p>
}

export function Bottone({ children, onClick, tipo = 'secondo', disabled, className = '', etichetta, type = 'button' }: {
  children: React.ReactNode; onClick?: () => void; tipo?: 'primo' | 'secondo' | 'piatto'; disabled?: boolean; className?: string
  etichetta?: string; type?: 'button' | 'submit'
}) {
  const stile = tipo === 'primo'
    ? 'bg-blu-scuro text-white hover:bg-navy border border-blu-scuro'
    : tipo === 'secondo'
      ? 'border border-bordo bg-white text-inchiostro hover:border-tenue'
      : 'text-blu-scuro hover:bg-velo'
  return (
    <button type={type} onClick={onClick} disabled={disabled} aria-label={etichetta}
            className={`inline-flex min-h-11 items-center justify-center gap-1.5 rounded-full px-4 text-[14px] font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${stile} ${className}`}>
      {children}
    </button>
  )
}

/** La pillola dello stato: la parola nel colore del suo tono, su un fondo appena tinto.
 *  «piena» e' per la cosa sola che chiede un gesto adesso (Da chiamare): fondo pieno.
 *  «Non contattare» (tono stop) e' sempre piena, scura, con l'icona del divieto. */
export function Pillola({ testo, tono = 'neutro', piena = false, icona }: { testo: string; tono?: Tono; piena?: boolean; icona?: NomeIcona }) {
  const stile = piena && tono === 'ok' ? 'border-ok-testo bg-ok-testo text-white'
    : piena && tono === 'no' ? 'border-no-testo bg-no-testo text-white'
      : TONO[tono].morbido
  return (
    <span className={`inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-[13px] font-semibold ${stile}`}>
      {icona && <Icona nome={icona} className="h-3.5 w-3.5 shrink-0" />}
      {testo}
    </span>
  )
}


/** Lo stato di un lead, col suo colore: lo stesso in Oggi, in Lead e nella scheda. */
export function PillolaStato({ stato }: { stato: string }) {
  const tono = tonoStato(stato)
  return <Pillola testo={stato} tono={tono} piena={stato === 'Da chiamare'} icona={tono === 'stop' ? 'divieto' : undefined} />
}
