import { useState } from 'react'
import { Card, Micro } from './ui'

// QUANTO CHIEDERE (Dre, 16/9): «chiediamo una parte del valore che
// generiamo, in modo coerente: sarebbe fico avere un calcolo».
//
// Due conti, tenuti volutamente semplici, perche' un prezzo lo devi saper
// spiegare al cliente in una riga mentre sei in call. Non decidono al posto
// tuo: dicono da dove partire e quando stai regalando lavoro.

const euro = (n: number) => `${Math.round(n).toLocaleString('it-IT')} €`

// ── il continuativo ─────────────────────────────────────────────────────
const BASE = 1400          // il lavoro fisso: gestione, report, call
const SOGLIA = 5000        // sotto questa spesa il lavoro e' sempre quello
const QUOTA = 0.10         // sopra, cresce con quanto si gestisce
const SUCCESSO = 0.06      // sul margine lordo in piu', dove si misura davvero

// ── i progetti ──────────────────────────────────────────────────────────
const GIORNATA = 600
const RISCHIO: Array<[string, number, string]> = [
  ['Già fatto', 1, 'l\'abbiamo già costruito almeno una volta'],
  ['Nuovo per noi', 1.3, 'sappiamo farlo ma non l\'abbiamo mai fatto'],
  ['Dipende da altri', 1.6, 'tocca sistemi di terzi che non controlliamo'],
]
const COSTO_ORA = 25       // quanto costa un'ora del loro tempo, prudente
const MINIMO = 1500

export default function Prezzo() {
  const [modo, setModo] = useState<'canone' | 'progetto'>('canone')

  // continuativo
  const [spesa, setSpesa] = useState('')
  const [margine, setMargine] = useState('')
  const sp = Number(spesa.replace(',', '.')) || 0
  const canone = BASE + Math.max(0, sp - SOGLIA) * QUOTA
  const mg = Number(margine.replace(',', '.')) || 0
  const successo = Math.min(mg * SUCCESSO, BASE * 2)

  // progetto
  const [giorni, setGiorni] = useState('')
  const [rischio, setRischio] = useState(1)
  const [ore, setOre] = useState('')
  const gg = Number(giorni.replace(',', '.')) || 0
  const lavoro = gg * GIORNATA * rischio
  const valoreAnno = (Number(ore.replace(',', '.')) || 0) * COSTO_ORA * 12
  const minimoValore = valoreAnno * 0.2
  const massimoValore = valoreAnno * 0.3
  const consiglio = Math.max(MINIMO, lavoro, valoreAnno ? minimoValore : 0)
  const troppo = valoreAnno > 0 && consiglio > massimoValore

  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-center gap-3">
        <Micro className="text-inchiostro">Quanto chiedere</Micro>
        <div className="flex overflow-hidden rounded-[6px] border border-bordo text-[11px] font-bold uppercase tracking-[0.06em]">
          {([['canone', 'Continuativo'], ['progetto', 'Progetto']] as const).map(([v, n]) => (
            <button key={v} onClick={() => setModo(v)}
                    className={`px-3 py-1.5 ${modo === v ? 'bg-navy text-white' : 'bg-white text-tenue hover:bg-velo'}`}>
              {n}
            </button>
          ))}
        </div>
      </div>

      {modo === 'canone' ? (
        <div className="mt-3 space-y-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-2 rounded-[6px] border border-bordo px-2.5 py-1.5 text-sm">
              <span className="text-[11px] font-bold uppercase tracking-[0.06em] text-spento">Spende al mese</span>
              <input value={spesa} onChange={(e) => setSpesa(e.target.value.replace(/[^0-9.,]/g, ''))}
                     placeholder="0" className="w-24 bg-transparent text-right font-bold tabular-nums outline-none" />
              <span className="text-tenue">€</span>
            </label>
            <label className="flex items-center gap-2 rounded-[6px] border border-bordo px-2.5 py-1.5 text-sm">
              <span className="text-[11px] font-bold uppercase tracking-[0.06em] text-spento">Margine in più, al mese</span>
              <input value={margine} onChange={(e) => setMargine(e.target.value.replace(/[^0-9.,]/g, ''))}
                     placeholder="0" className="w-24 bg-transparent text-right font-bold tabular-nums outline-none" />
              <span className="text-tenue">€</span>
            </label>
          </div>

          <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1 border-t border-velo pt-2.5">
            <span className="flex items-baseline gap-2">
              <span className="text-[26px] font-extrabold leading-none tabular-nums">{euro(canone)}</span>
              <span className="text-[11px] font-bold uppercase tracking-[0.06em] text-spento">al mese</span>
            </span>
            {successo > 0 && (
              <span className="text-sm text-tenue">
                più <b className="font-bold tabular-nums text-inchiostro">{euro(successo)}</b> di quota sul risultato
              </span>
            )}
          </div>

          <p className="text-[12px] leading-relaxed text-tenue">
            {euro(BASE)} è il lavoro fisso: gestione, ottimizzazione, report, call. Sopra i {euro(SOGLIA)} di spesa
            si aggiunge il 10%, perché da lì in poi cresce il lavoro vero.
            {successo > 0 && ` La quota sul risultato è il 6% del margine lordo in più rispetto a prima che entrassimo, con un tetto a ${euro(BASE * 2)}.`}
          </p>
        </div>
      ) : (
        <div className="mt-3 space-y-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-2 rounded-[6px] border border-bordo px-2.5 py-1.5 text-sm">
              <span className="text-[11px] font-bold uppercase tracking-[0.06em] text-spento">Giornate</span>
              <input value={giorni} onChange={(e) => setGiorni(e.target.value.replace(/[^0-9.,]/g, ''))}
                     placeholder="0" className="w-16 bg-transparent text-right font-bold tabular-nums outline-none" />
            </label>
            <div className="flex overflow-hidden rounded-[6px] border border-bordo text-[11px] font-semibold">
              {RISCHIO.map(([n, v, perche]) => (
                <button key={n} title={perche} onClick={() => setRischio(v)}
                        className={`px-2.5 py-1.5 ${rischio === v ? 'bg-blu text-white' : 'bg-white text-tenue hover:bg-velo'}`}>
                  {n}
                </button>
              ))}
            </div>
            <label className="flex items-center gap-2 rounded-[6px] border border-bordo px-2.5 py-1.5 text-sm">
              <span className="text-[11px] font-bold uppercase tracking-[0.06em] text-spento">Ore che gli fa risparmiare, al mese</span>
              <input value={ore} onChange={(e) => setOre(e.target.value.replace(/[^0-9.,]/g, ''))}
                     placeholder="0" className="w-16 bg-transparent text-right font-bold tabular-nums outline-none" />
            </label>
          </div>

          <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1 border-t border-velo pt-2.5">
            <span className="flex items-baseline gap-2">
              <span className="text-[26px] font-extrabold leading-none tabular-nums">{euro(consiglio)}</span>
              <span className="text-[11px] font-bold uppercase tracking-[0.06em] text-spento">a progetto</span>
            </span>
            {valoreAnno > 0 && (
              <span className="text-sm text-tenue">
                gli vale <b className="font-bold tabular-nums text-inchiostro">{euro(valoreAnno)}</b> l'anno,
                forchetta {euro(minimoValore)} , {euro(massimoValore)}
              </span>
            )}
          </div>

          {troppo && (
            <p className="rounded-[6px] border border-amber-300 bg-amber-50 px-3 py-2 text-[12px] font-semibold text-amber-900">
              Il lavoro costa più di quanto vale per lui: o si riduce il perimetro, o si lascia perdere.
            </p>
          )}
          <p className="text-[12px] leading-relaxed text-tenue">
            Giornate per {euro(GIORNATA)}, moltiplicate per il rischio. Il valore serve da controllo: il prezzo giusto
            sta fra il 20% e il 30% di quello che il sistema gli fa risparmiare in un anno, e sotto {euro(MINIMO)} non si parte.
          </p>
        </div>
      )}
    </Card>
  )
}
