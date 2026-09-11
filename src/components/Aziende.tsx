import { useState } from 'react'
import { leggi as leggiPref, scrivi as scriviPref } from '../lib/preferenze'
import Lista from './Lista'
import TuttiFoglio from './TuttiFoglio'

// PIPELINE (Dre, 12/9): chi sta arrivando, dalla risposta alla firma. Una
// lista sola in due forme: la bacheca a colonne (le fasi, si trascina) e il
// foglio. I preventivi e i clienti stanno in Clienti: qui c'e' la vendita.

type Modo = 'bacheca' | 'foglio'
const MODI: Array<[Modo, string]> = [['bacheca', 'Bacheca'], ['foglio', 'Foglio']]

interface Props { onOpen: (id: string) => void; q: string }

export default function Aziende({ onOpen, q }: Props) {
  const [modo, setModo] = useState<Modo>(() => ((leggiPref('tutti-modo') as Modo) === 'foglio' ? 'foglio' : 'bacheca'))
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
      {modo === 'bacheca' ? <Lista onOpen={onOpen} q={q} /> : <TuttiFoglio onOpen={onOpen} />}
    </div>
  )
}
