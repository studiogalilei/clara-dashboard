import { useEffect, useState } from 'react'

// IL GIRO GUIDATO (Dre, 16/9): «al primo accesso appare il coso che ti
// presenta e ti guida su come puoi fare le cose, tipo onboarding guidato,
// con le frecce». Serve a una cosa sola: che nessuno resti fermo davanti a
// una schermata nuova chiedendosi da dove si comincia.
//
// Regole: dura poco, si salta sempre, e non spiega quello che si capisce da
// solo. Ogni passo illumina una cosa vera sullo schermo, e se quella cosa
// non c'e' (un widget che non hai) il passo si salta da solo.

export interface Passo {
  chiave: string
  titolo: string
  testo: string
  dove?: string          // il selettore della cosa da illuminare
}

const PASSI: Passo[] = [
  {
    chiave: 'ciao',
    titolo: 'Benvenuto nel Workspace',
    testo: 'Qui dentro c\'è il lavoro di tutti i giorni: chi stiamo seguendo, a che punto è, cosa manca. Quasi tutto si scrive da solo leggendo il calendario, le mail e gli appunti delle call: a te resta da decidere. Due minuti e sai dov\'è cosa.',
  },
  {
    chiave: 'oggi',
    titolo: 'Oggi',
    testo: 'La tua giornata: chi aspetta una risposta da te, le tue task, la prossima call. La mattina si parte da qui.',
    dove: '[data-giro="pipeline"]',
  },
  {
    chiave: 'pipeline',
    titolo: 'Pipeline',
    testo: 'Le aziende, dalla prima risposta alla firma. Le carte si trascinano da una colonna all\'altra: quando ne porti avanti una ti chiede il riassunto della call, e se gli appunti ci sono già te li propone con un clic.',
    dove: '[data-giro="prospect"]',
  },
  {
    chiave: 'clienti',
    titolo: 'Clienti',
    testo: 'Chi è già dentro, con i progetti: a che punto sono, chi li segue, cosa manca. Si scrive come un foglio, cella per cella.',
    dove: '[data-giro="progetti"]',
  },
  {
    chiave: 'preventivi',
    titolo: 'Preventivi e documenti',
    testo: 'Il "+" apre un documento col modello già dentro. Colleghi l\'azienda e i dati si riempiono; quello che resta in giallo è da scrivere. C\'è anche il bottone per farlo scrivere a Clara.',
    dove: '[data-giro="preventivi"]',
  },
  {
    chiave: 'condividi',
    titolo: 'Condividi',
    testo: 'Qui ci passiamo i documenti. Trascini il file, dici di che cliente è, e lo ritrovi per sempre: nel thread e nella cartella di quel cliente. Su WhatsApp si parla, i documenti passano da qui.',
    dove: '[data-giro="chat"]',
  },
  {
    chiave: 'clara',
    titolo: 'Clara',
    testo: 'Legge quello che succede, tiene aggiornate le schede, prepara le bozze. Non manda niente e non decide niente da sola: propone, e tu dici sì o no dalla sua Posta. Quando rimbalza, ha qualcosa per te.',
    dove: '[aria-label="Clara"]',
  },
  {
    chiave: 'feedback',
    titolo: 'Cosa cambieresti',
    testo: 'Questa è una beta. Se un bottone sta nel posto sbagliato, se un giro è troppo lungo, o se manca qualcosa che ti servirebbe, scrivilo qui: si legge tutto e si cambia.',
    dove: '[data-giro="feedback"]',
  },
  {
    chiave: 'fine',
    titolo: 'Ultima cosa',
    testo: 'In Impostazioni, sotto «Il tuo Workspace», c\'è la tua guida da scaricare: le sezioni che hai tu e le parole che usiamo qui dentro. Il giro puoi rifarlo da lì quando vuoi.',
  },
]

interface Riquadro { top: number; left: number; width: number; height: number }

export default function Giro({ onFine }: { onFine: () => void }) {
  const [i, setI] = useState(0)
  const [buco, setBuco] = useState<Riquadro | null>(null)

  // i passi che hanno senso per chi sta guardando: se il widget non ce l'ha,
  // il suo passo non esiste
  const passi = PASSI.filter((p) => !p.dove || document.querySelector(p.dove))
  const passo = passi[Math.min(i, passi.length - 1)]

  useEffect(() => {
    const misura = () => {
      if (!passo?.dove) { setBuco(null); return }
      const e = document.querySelector(passo.dove)
      if (!e) { setBuco(null); return }
      const r = e.getBoundingClientRect()
      setBuco({ top: r.top - 6, left: r.left - 6, width: r.width + 12, height: r.height + 12 })
    }
    misura()
    window.addEventListener('resize', misura)
    window.addEventListener('scroll', misura, true)
    return () => { window.removeEventListener('resize', misura); window.removeEventListener('scroll', misura, true) }
  }, [passo])

  useEffect(() => {
    const tasti = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onFine()
      if (e.key === 'Enter' || e.key === 'ArrowRight') avanti()
    }
    window.addEventListener('keydown', tasti)
    return () => window.removeEventListener('keydown', tasti)
  })

  function avanti() {
    if (i >= passi.length - 1) onFine()
    else setI(i + 1)
  }

  if (!passo) return null

  // la scheda: sotto la cosa illuminata se c'e' spazio, se no sopra; senza
  // bersaglio sta in mezzo allo schermo
  const alto = typeof window !== 'undefined' ? window.innerHeight : 800
  const largo = typeof window !== 'undefined' ? window.innerWidth : 1200
  // di fianco se c'e' spazio (le voci del menu stanno a sinistra), se no
  // sotto, se no sopra: la scheda non deve mai coprire quello che illumina
  const diLato = buco ? buco.left + buco.width + 384 < largo : false
  const sotto = buco ? buco.top + buco.height + 12 : 0
  const inBasso = buco ? sotto + 240 > alto : false
  const stile: React.CSSProperties = buco
    ? diLato
      ? {
          top: Math.min(Math.max(12, buco.top - 16), Math.max(12, alto - 250)),
          left: buco.left + buco.width + 14,
        }
      : {
          top: inBasso ? Math.max(12, buco.top - 228) : sotto,
          left: Math.min(Math.max(12, buco.left), Math.max(12, largo - 372)),
        }
    : { top: Math.max(24, alto / 2 - 140), left: Math.max(12, largo / 2 - 180) }

  return (
    <div className="fixed inset-0 z-[120]">
      {/* il velo con il buco: quello che conta resta acceso, il resto si spegne */}
      {buco ? (
        <div
          className="pointer-events-none absolute rounded-2xl ring-2 ring-blu transition-all duration-200"
          style={{ ...buco, boxShadow: '0 0 0 9999px rgba(6, 23, 115, 0.55)' }}
        />
      ) : (
        <div className="absolute inset-0 bg-navy/55" />
      )}

      {/* il velo prende i clic: durante il giro non si tocca altro */}
      <div className="absolute inset-0" onClick={avanti} />

      <div className="salta-su absolute w-[360px] max-w-[calc(100vw-24px)] rounded-2xl bg-white p-5 shadow-[0_18px_50px_rgba(6,23,115,0.3)]"
           style={stile}>
        <p className="text-[11px] font-bold uppercase tracking-[0.1em] text-blu">
          {i + 1} di {passi.length}
        </p>
        <p className="mt-1 text-[17px] font-extrabold text-navy">{passo.titolo}</p>
        <p className="mt-1.5 text-[14px] leading-relaxed text-inchiostro">{passo.testo}</p>
        <div className="mt-4 flex items-center gap-3">
          <button onClick={avanti}
                  className="rounded-full bg-blu px-5 py-2 text-sm font-bold text-white hover:bg-blu-scuro">
            {i >= passi.length - 1 ? 'Ho capito' : 'Avanti'}
          </button>
          {i < passi.length - 1 && (
            <button onClick={onFine} className="text-xs font-semibold text-tenue hover:text-inchiostro">
              Salta il giro
            </button>
          )}
          <span className="ml-auto flex gap-1">
            {passi.map((p, k) => (
              <span key={p.chiave} className={`h-1.5 w-1.5 rounded-full ${k === i ? 'bg-blu' : 'bg-bordo'}`} />
            ))}
          </span>
        </div>
      </div>
    </div>
  )
}
