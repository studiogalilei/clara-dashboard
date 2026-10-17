// CAMPAGNE: come vanno le campagne attive, ultimi 7 o 30 giorni.
// Mail mandate, aziende scritte e risposte le dice Smartlead (solo lettura, una volta all'ora);
// si', call e no vengono dalle risposte che il sistema ha letto. Un numero che non c'e' non si
// inventa: si scrive «non disponibile».
import { useState } from 'react'
import { leggiNumeri, type Finestra } from './dati'
import { numero, quando, tasso, type Tono } from './regole'
import { Carico, Errore, Vuoto } from './pezzi'
import { TONO } from './toni'
import { useDati } from './uso'

type Periodo = '7' | '30'

function ricordaPeriodo(v?: Periodo): Periodo {
  try {
    if (v) localStorage.setItem('snella-periodo', v)
    return (localStorage.getItem('snella-periodo') as Periodo) || '7'
  } catch { return v ?? '7' }
}

export default function Campagne() {
  const { dati, errore, caricando, rifai } = useDati(leggiNumeri)
  const [periodo, setPeriodo] = useState<Periodo>(() => ricordaPeriodo())

  if (caricando) return <Carico righe={4} etichetta="Carico le campagne" />
  if (errore && !dati) return <Errore testo={errore} riprova={() => void rifai()} />
  const c = dati?.campagne
  if (!c) return <Vuoto>I numeri delle campagne non sono ancora pronti: arrivano entro un'ora.</Vuoto>

  return (
    <div>
      <div role="radiogroup" aria-label="Periodo" className="inline-flex rounded-full border border-bordo bg-white p-1">
        {(['7', '30'] as const).map((p) => (
          <button key={p} role="radio" aria-checked={periodo === p} onClick={() => setPeriodo(ricordaPeriodo(p))}
                  className={`min-h-11 rounded-full px-4 text-[14px] font-semibold ${periodo === p ? 'bg-blu-scuro text-white' : 'text-inchiostro hover:bg-velo'}`}>
            Ultimi {p} giorni
          </button>
        ))}
      </div>

      {c.dati.errore && (
        <p role="alert" className="mt-3 text-[14px] font-semibold text-attesa-testo">
          Smartlead non ha dato tutti i numeri ({c.dati.errore}): dove manca c'è scritto «non disponibile».
        </p>
      )}

      {!c.dati.campagne.length ? (
        <div className="mt-4"><Vuoto>Nessuna campagna attiva su Smartlead.</Vuoto></div>
      ) : (
        <>
          <Riquadro titolo="Tutte le campagne attive" f={c.dati.totale[periodo]} forte />
          <h2 className="mb-2 mt-7 text-[17px] font-bold text-inchiostro">Per campagna <span className="font-semibold text-tenue">{c.dati.campagne.length}</span></h2>
          <ul className="space-y-3">
            {[...c.dati.campagne]
              .sort((a, b) => (b.finestre[periodo].risposte ?? b.finestre[periodo].risposte_lette) - (a.finestre[periodo].risposte ?? a.finestre[periodo].risposte_lette))
              .map((x) => <li key={x.id}><Riquadro titolo={x.nome} f={x.finestre[periodo]} /></li>)}
          </ul>
        </>
      )}

      <p className="mt-6 text-[13px] leading-relaxed text-tenue">
        Mail mandate, aziende scritte e risposte: i numeri di Smartlead. Il tasso è risposte ogni 100 aziende scritte nel periodo (sotto le 30 aziende non si calcola).
        Sì, call prenotate e no: dalle risposte lette dal sistema, per chi ha risposto nel periodo.
        Aggiornati {quando(c.il)}.
      </p>
    </div>
  )
}

const POCHE_AZIENDE = 30

function Riquadro({ titolo, f, forte = false }: { titolo: string; f: Finestra | undefined; forte?: boolean }) {
  // 17/10: 4 risposte su 9 aziende faceva «44,4%»: sotto le 30 aziende scritte un tasso non dice niente
  const pochi = f?.aziende != null && f.aziende < POCHE_AZIENDE
  const t = pochi ? null : tasso(f?.risposte, f?.aziende)
  // 17/10: i numeri buoni in verde (si', call), i no in rosso, il resto neutro. Il colore sta sul
  // numero e su un pallino accanto alla parola: la parola resta, il colore aiuta l'occhio.
  const voci: Array<[string, string | null, string | undefined, string | undefined, Tono]> = [
    ['Mail mandate', numero(f?.mandate), f?.aziende != null ? `a ${numero(f.aziende)} aziende` : undefined, undefined, 'neutro'],
    ['Risposte', numero(f?.risposte), undefined, undefined, 'neutro'],
    ['Tasso di risposta', t, undefined, pochi ? 'troppe poche aziende scritte' : undefined, 'neutro'],
    ['Sì', numero(f?.si), undefined, undefined, 'ok'],
    ['Call prenotate', numero(f?.call), undefined, undefined, 'ok'],
    ['No', numero(f?.no), undefined, undefined, 'no'],
  ]
  return (
    <section className={`mt-4 rounded-2xl border bg-white p-4 ${forte ? 'border-blu-scuro/40' : 'border-bordo'}`}>
      <h3 className={`${forte ? 'text-[17px]' : 'text-[15px]'} font-bold leading-snug text-inchiostro`}>{titolo}</h3>
      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
        {voci.map(([nome, v, sotto, vuoto, tono]) => (
          <div key={nome}>
            <dt className="flex items-center gap-1.5 text-[13px] text-tenue">
              {tono !== 'neutro' && <span aria-hidden="true" className={`h-2 w-2 rounded-full ${TONO[tono].segno}`} />}
              {nome}
            </dt>
            <dd className={v == null ? 'text-[14px] font-semibold text-tenue'
              : `${forte ? 'text-[26px]' : 'text-[22px]'} font-bold leading-tight ${tono === 'neutro' || v === '0' ? 'text-inchiostro' : TONO[tono].testo}`}>
              {v ?? vuoto ?? 'non disponibile'}
            </dd>
            {sotto && v != null && <dd className="text-[13px] text-tenue">{sotto}</dd>}
          </div>
        ))}
      </dl>
    </section>
  )
}
