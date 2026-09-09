import { useState } from 'react'
import { leggi as leggiPref, scrivi as scriviPref } from '../lib/preferenze'
import Lista from './Lista'
import TuttiFoglio from './TuttiFoglio'
import Preventivi from './Preventivi'

// AZIENDE (intervista a Dre, 9/9): una pagina sola per prospect e clienti.
// Tre modi di guardare le stesse aziende: la bacheca a colonne (le fasi, si
// trascina), il foglio di Giacomo (stato, chi segue, canone, preventivi) e
// tutti i preventivi in fila. Pipeline e Tutti erano due pagine: ora sono
// due tab, e non ci si perde piu'.

type Modo = 'bacheca' | 'foglio' | 'preventivi'
const MODI: Array<[Modo, string]> = [['bacheca', 'Bacheca'], ['foglio', 'Foglio'], ['preventivi', 'Preventivi']]

interface Props { onOpen: (id: string) => void; q: string }

export default function Aziende({ onOpen, q }: Props) {
  const [modo, setModo] = useState<Modo>(() => (leggiPref('tutti-modo') as Modo) || 'bacheca')
  function cambia(m: Modo) { setModo(m); scriviPref('tutti-modo', m) }
  return (
    <div className="space-y-4">
      <div className="flex gap-6 border-b border-bordo">
        {MODI.map(([m, etichetta]) => (
          <button key={m} onClick={() => cambia(m)}
            className={`-mb-px border-b-2 pb-2.5 text-[15px] font-semibold transition-colors ${
              modo === m ? 'border-navy text-navy' : 'border-transparent text-tenue hover:text-inchiostro'}`}>
            {etichetta}
          </button>
        ))}
      </div>
      {modo === 'bacheca' ? <Lista onOpen={onOpen} q={q} /> : modo === 'foglio' ? <TuttiFoglio onOpen={onOpen} /> : <Preventivi onOpen={onOpen} />}
    </div>
  )
}
