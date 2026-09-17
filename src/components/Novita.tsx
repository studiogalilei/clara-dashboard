import { useState } from 'react'
import { supabase } from '../lib/supabase'
import { leggi as leggiPref, scrivi as scriviPref } from '../lib/preferenze'
import { NOVITA, daMostrare } from '../lib/novita'

// LA STRISCIA DELLE NOVITA' (Dre, 17/9): quando qualcosa cambia, chi
// rientra lo trova qui, in alto, una volta. Cinque stelle per dire se serve
// davvero, e «lascia un feedback» per dirlo a parole. La prima volta in
// assoluto si spiega anche che le novita' arriveranno qui. Dopo il voto
// (o la x) sparisce, e quella novita' non torna piu'.

const viste = () => leggiPref('novita-viste').split(',').map((s) => s.trim()).filter(Boolean)

export default function Novita() {
  const [chiuse, setChiuse] = useState<string[]>(viste)
  const nuova = daMostrare(chiuse)
  const [voto, setVoto] = useState(0)
  const [sopra, setSopra] = useState(0)
  const [scrivo, setScrivo] = useState(false)
  const [testo, setTesto] = useState('')
  const [grazie, setGrazie] = useState(false)
  const [guaio, setGuaio] = useState('')

  if (!nuova) return null
  const primaVolta = chiuse.length === 0 && NOVITA.length > 0

  function segnaVista() {
    const tutte = [...new Set([...chiuse, nuova!.chiave])]
    scriviPref('novita-viste', tutte.join(','))
    setChiuse(tutte)
  }

  async function manda(stelle: number, parole?: string) {
    const riga = {
      genere: 'novita', novita: nuova!.chiave, voto: stelle || null,
      testo: parole?.trim() || `${stelle} ${stelle === 1 ? 'stella' : 'stelle'} a «${nuova!.titolo}»`,
      dove: 'novita',
    }
    const { error } = await supabase.from('feedback').insert(riga)
    if (error) { setGuaio(`Non è partito: ${error.message}`); return false }
    return true
  }

  async function vota(n: number) {
    setVoto(n)
    if (scrivo) return                      // lo manda insieme alle parole
    if (await manda(n)) ringraziaEChiudi()
  }

  async function mandaParole() {
    if (!testo.trim() && !voto) return
    if (await manda(voto, testo)) ringraziaEChiudi()
  }

  function ringraziaEChiudi() {
    setGrazie(true)
    window.setTimeout(segnaVista, 1100)
  }

  return (
    <div className="salta-su mb-5 rounded-2xl border border-blu/25 bg-blu/[0.04] px-4 py-3.5 lg:px-5">
      {grazie ? (
        <p className="py-1 text-sm font-semibold text-navy">Grazie. Conta davvero.</p>
      ) : (
        <>
          <div className="flex items-start gap-3">
            <div className="min-w-0 flex-1">
              <p className="text-[11px] font-bold uppercase tracking-[0.1em] text-blu">Novità</p>
              <p className="mt-0.5 text-[15px] font-extrabold text-navy">{nuova.titolo}</p>
              <p className="mt-1 max-w-2xl text-sm leading-relaxed text-inchiostro">{nuova.testo}</p>
              {primaVolta && (
                <p className="mt-1.5 text-xs text-tenue">
                  Le novità arrivano qui: ogni volta che cambia qualcosa lo trovi in questa striscia, una volta sola. Le stelle ci dicono se serve davvero.
                </p>
              )}
            </div>
            <button onClick={segnaVista} aria-label="Chiudi" title="Chiudi"
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-tenue hover:bg-white hover:text-navy">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="h-3.5 w-3.5"><path d="M6 6l12 12M18 6L6 18" /></svg>
            </button>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
            <div className="flex items-center gap-1" onMouseLeave={() => setSopra(0)} role="radiogroup" aria-label="Quanto ti serve, da 1 a 5">
              {[1, 2, 3, 4, 5].map((n) => {
                const piena = n <= (sopra || voto)
                return (
                  <button key={n} onClick={() => void vota(n)} onMouseEnter={() => setSopra(n)}
                          role="radio" aria-checked={voto === n} aria-label={`${n} su 5`}
                          className="p-0.5 transition-transform duration-150 ease-out hover:scale-110">
                    <svg viewBox="0 0 24 24" className={`h-6 w-6 ${piena ? 'fill-blu text-blu' : 'fill-transparent text-bordo'}`}
                         stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round">
                      <path d="M12 3.5l2.6 5.4 5.9.8-4.3 4.1 1.1 5.9L12 16.9l-5.3 2.8 1.1-5.9-4.3-4.1 5.9-.8z" />
                    </svg>
                  </button>
                )
              })}
              <span className="ml-1.5 text-xs text-tenue">{voto ? `${voto} su 5` : 'quanto ti serve?'}</span>
            </div>
            <button onClick={() => setScrivo((v) => !v)} className="text-xs font-semibold text-blu hover:underline">
              {scrivo ? 'Solo le stelle' : 'Lascia un feedback'}
            </button>
          </div>

          {scrivo && (
            <div className="salta-su mt-2.5 flex flex-col gap-2 sm:flex-row sm:items-end">
              <textarea autoFocus rows={2} value={testo} onChange={(e) => setTesto(e.target.value)}
                        placeholder="Cosa ne pensi, cosa cambieresti, cosa manca. Anche due parole."
                        className="min-w-0 flex-1 rounded-xl border border-bordo bg-white px-3 py-2 text-sm outline-none focus:border-blu" />
              <button onClick={() => void mandaParole()} disabled={!testo.trim() && !voto}
                      className="shrink-0 rounded-full bg-blu px-4 py-2 text-xs font-bold text-white hover:bg-blu-scuro disabled:opacity-30">
                Manda
              </button>
            </div>
          )}
          {guaio && <p className="mt-2 text-xs text-red-700">{guaio}</p>}
        </>
      )}
    </div>
  )
}
