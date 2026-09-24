import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'

// LA SINCRONIZZAZIONE (Dre, 15/9 e 24/9).
//
// 15/9: «metti la scritta dell'ultimo aggiornamento, così so almeno a quanto
// è datato». 24/9, dopo aver visto la dashboard di Lorenzo: «mi piace il
// pulsante sync». Quindi due cose, sulla stessa riga: QUANDO è stata l'ultima
// sincronizzazione (Smartlead, calendario, posta: tutto quello che Clara
// legge da fuori) e un bottone che la fa partire adesso, senza aspettare i
// cinque minuti dell'orologio.
//
// Il bottone chiama il direttore in cloud con la catena che fa un
// campanello di Smartlead: sync, calendario, Google Fit, analisi, bozze.
// Ci mette circa due minuti (il runner deve partire). La riga resta
// «Sincronizzo…» finché l'ora dell'ultima corsa non avanza; se in quattro
// minuti non è arrivata, lo dice, invece di far finta.
//
// Il verde vuol dire fresco; se il giro si ferma diventa ambra e poi rossa,
// perché a quel punto è il motivo per cui una carta dice una cosa vecchia.

const MIN = 60000
const CATENA = 'sync_smartlead,calendar,googlefit,analisi,bozze'
const ATTESA_MAX = 4 * MIN

function frase(quando: Date): { testo: string; tono: string } {
  const min = Math.floor((Date.now() - quando.getTime()) / MIN)
  const ora = quando.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
  if (min < 2) return { testo: 'Sincronizzato adesso', tono: 'text-green-700' }
  if (min < 60) return { testo: `Sincronizzato ${min} minuti fa, alle ${ora}`, tono: 'text-green-700' }
  const ore = Math.floor(min / 60)
  // fino a 3 ore e' normale (e' lo stesso confine del Radar), poi e' fermo
  if (ore < 3) return { testo: `Sincronizzato ${ore === 1 ? "un'ora" : `${ore} ore`} fa, alle ${ora}`, tono: 'text-green-700' }
  if (ore < 6) return { testo: `Ultima sincronizzazione ${ore} ore fa, alle ${ora}: Clara è ferma`, tono: 'text-amber-700' }
  if (ore < 24) return { testo: `Ultima sincronizzazione stamattina, alle ${ora}`, tono: 'text-amber-700' }
  const giorni = Math.floor(ore / 24)
  return { testo: `Sincronizzazione ferma da ${giorni} ${giorni === 1 ? 'giorno' : 'giorni'}: quello che vedi è vecchio`, tono: 'text-red-700' }
}

export default function Aggiornato() {
  const [quando, setQuando] = useState<Date | null>(null)
  const [richiesta, setRichiesta] = useState<number | null>(null)   // quando ho premuto il bottone
  const [problema, setProblema] = useState<string>('')
  const [, ridisegna] = useState(0)

  useEffect(() => {
    let vivo = true
    const chiedi = async () => {
      const { data } = await supabase.rpc('ultimo_giro')
      if (vivo && data) setQuando(new Date(data as string))
    }
    void chiedi()
    // mentre aspetto la corsa chiedo ogni dieci secondi, altrimenti ogni due minuti
    const q = setInterval(() => void chiedi(), richiesta ? 10000 : 2 * MIN)
    const t = setInterval(() => ridisegna((n) => n + 1), MIN / 2)
    return () => { vivo = false; clearInterval(q); clearInterval(t) }
  }, [richiesta])

  useEffect(() => {
    if (!richiesta) return
    if (quando && quando.getTime() > richiesta) { setRichiesta(null); return }
    if (Date.now() - richiesta > ATTESA_MAX) {
      setRichiesta(null)
      setProblema('La sincronizzazione non è arrivata in quattro minuti: riprova, o guarda le operazioni in Impostazioni.')
    }
  }, [quando, richiesta])

  async function sincronizza() {
    setProblema('')
    setRichiesta(Date.now())
    const { error } = await supabase.rpc('chiama_direttore', { forza: CATENA })
    if (error) {
      setRichiesta(null)
      setProblema(`Non sono riuscita a chiamare il direttore: ${error.message}`)
    }
  }

  if (!quando) return null
  const { testo, tono } = frase(quando)
  return (
    <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] font-semibold">
      <span className={`flex items-center gap-1.5 ${tono}`}>
        <span className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-current" />
        {richiesta ? 'Sincronizzo…' : testo}
      </span>
      <button
        onClick={() => void sincronizza()}
        disabled={Boolean(richiesta)}
        title="Rilegge adesso Smartlead, il calendario e la posta, e prepara analisi e bozze"
        className="rounded-full border border-bordo bg-white px-2.5 py-0.5 text-[11px] font-semibold text-blu hover:border-blu disabled:cursor-wait disabled:opacity-60"
      >
        {richiesta ? 'in corso' : 'Sincronizza'}
      </button>
      {problema && <span className="text-amber-700">{problema}</span>}
    </div>
  )
}
