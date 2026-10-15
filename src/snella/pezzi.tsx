// LA VERSIONE SNELLA: i pezzi piccoli che usano tutte e tre le schermate.
// Bianco, una tinta sola (il blu scuro SG, contrasto 6:1 sul bianco), testo grande, niente
// fronzoli. Il rosso solo per quello che e' in ritardo.
const ICONE = {
  oggi: 'M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z',
  lead: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75',
  campagne: 'M3 3v18h18M7 15l4-4 3 3 5-6',
  telefono: 'M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.79 19.79 0 0 1 2.12 4.18 2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z',
  indietro: 'M15 18l-6-6 6-6',
  esterno: 'M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3',
  cerca: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.35-4.35',
  video: 'M23 7l-7 5 7 5V7zM14 5H3a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2z',
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

export function Sezione({ titolo, conta, children, id }: { titolo: string; conta?: number | null; children: React.ReactNode; id?: string }) {
  return (
    <section aria-labelledby={id} className="mt-7 first:mt-0">
      <h2 id={id} className="mb-2.5 flex items-baseline gap-2 text-[17px] font-bold text-inchiostro">
        {titolo}
        {conta != null && <span className="text-[15px] font-semibold text-tenue">{conta}</span>}
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
    <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-[15px] text-red-900">
      <p className="font-semibold">Non riesco a leggere i dati.</p>
      <p className="mt-0.5 text-[14px]">{testo}</p>
      {riprova && (
        <button onClick={riprova} className="mt-2 min-h-11 rounded-full border border-red-300 bg-white px-4 text-[14px] font-semibold text-red-900 hover:bg-red-100">
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

/** La pillola dello stato: testo scuro, bordo sottile. Il colore lo prende solo «Vuole sentirti». */
export function Pillola({ testo, forte = false }: { testo: string; forte?: boolean }) {
  return (
    <span className={`inline-flex shrink-0 items-center rounded-full border px-2.5 py-0.5 text-[12.5px] font-semibold ${forte ? 'border-blu-scuro/40 bg-blu-scuro/[0.07] text-blu-scuro' : 'border-bordo text-tenue'}`}>
      {testo}
    </span>
  )
}

