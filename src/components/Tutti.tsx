import { useState } from 'react'
import { leggi as leggiPref, scrivi as scriviPref } from '../lib/preferenze'
import TuttiFoglio from './TuttiFoglio'
import TuttiElenco from './TuttiElenco'
import Preventivi from './Preventivi'

// TUTTI: tre modi di guardare le stesse aziende. Il foglio di Giacomo
// (default), l'elenco a carte con i POD, e tutti i preventivi in fila.

type Modo = 'foglio' | 'elenco' | 'preventivi'
const MODI: Array<[Modo, string]> = [['foglio', 'Foglio'], ['elenco', 'Elenco'], ['preventivi', 'Preventivi']]

interface Props { onOpen: (id: string) => void }

export default function Tutti({ onOpen }: Props) {
  const [modo, setModo] = useState<Modo>(() => (leggiPref('tutti-modo') as Modo) || 'foglio')
  function cambia(m: Modo) { setModo(m); scriviPref('tutti-modo', m) }
  return (
    <div className="space-y-3">
      <div className="flex overflow-hidden rounded-full border border-bordo bg-white self-start w-fit">
        {MODI.map(([m, etichetta]) => (
          <button key={m} onClick={() => cambia(m)}
            className={`px-4 py-1.5 text-xs font-bold transition-colors ${modo === m ? 'bg-blu text-white' : 'text-tenue hover:bg-velo'}`}>
            {etichetta}
          </button>
        ))}
      </div>
      {modo === 'foglio' ? <TuttiFoglio onOpen={onOpen} /> : modo === 'elenco' ? <TuttiElenco onOpen={onOpen} /> : <Preventivi onOpen={onOpen} />}
    </div>
  )
}
