import { useState } from 'react'
import {
  WIDGET, RUOLI, accessi, salvaAccessi, nascosti, salvaNascosti,
  mioRuolo, scegliRuolo, ruoliDi, type Chiave, type Ruolo,
} from '../lib/widget'
import { Card, TitoloCard, Micro } from './ui'

// Impostazioni: per ora una cosa sola, ma vera. I widget si accendono e si
// spengono, e chi comanda decide a chi arrivano. Niente interruttori finti:
// quello che tocchi qui cambia il menu adesso.

export default function Impostazioni({ onCambio }: { onCambio: () => void }) {
  const [ruolo, setRuolo] = useState<Ruolo>(mioRuolo)
  const [spenti, setSpenti] = useState<Chiave[]>(nascosti)
  const [acc, setAcc] = useState(accessi)
  const comando = ruolo === 'ceo'

  function accendi(c: Chiave, acceso: boolean) {
    const n = acceso ? spenti.filter((x) => x !== c) : [...spenti, c]
    setSpenti(n); salvaNascosti(n); onCambio()
  }

  function cambiaAccesso(c: Chiave, r: Ruolo, dentro: boolean) {
    const ora = acc[c] ?? WIDGET.find((w) => w.chiave === c)!.ruoli
    const n = { ...acc, [c]: dentro ? [...new Set([...ora, r])] : ora.filter((x) => x !== r) }
    setAcc(n); salvaAccessi(n); onCambio()
  }

  function cambiaRuolo(r: Ruolo) {
    setRuolo(r); scegliRuolo(r); onCambio()
  }

  return (
    <div className="space-y-4 pb-24 sm:pb-8">
      <Card className="p-4">
        <TitoloCard>Chi sei</TitoloCard>
        <div className="mt-1 flex flex-wrap gap-1.5">
          {RUOLI.map(([r, nome]) => (
            <button
              key={r}
              onClick={() => cambiaRuolo(r)}
              className={`rounded-full px-3.5 py-1.5 text-xs font-bold transition-colors ${
                ruolo === r ? 'bg-navy text-white' : 'border border-bordo bg-white text-tenue hover:border-navy'
              }`}
            >
              {nome}
            </button>
          ))}
        </div>
      </Card>

      <Card>
        <header className="flex items-baseline justify-between gap-2 border-b border-velo px-4 py-3">
          <TitoloCard>Widget</TitoloCard>
          <Micro>{WIDGET.filter((w) => !spenti.includes(w.chiave)).length} accesi</Micro>
        </header>

        {WIDGET.map((w) => {
          const acceso = w.fisso || !spenti.includes(w.chiave)
          const arrivo = ruoliDi(w).includes(ruolo)
          return (
            <div key={w.chiave} className="border-b border-velo px-4 py-3 last:border-0">
              <div className="flex items-center gap-3">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
                     className={`h-4 w-4 shrink-0 ${acceso && arrivo ? 'text-navy' : 'text-spento'}`}>
                  <path d={w.icona} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold">{w.nome}</p>
                  <p className="truncate text-xs text-tenue">{w.cosa}</p>
                </div>

                {w.fisso ? (
                  <span className="shrink-0 text-xs text-spento">sempre acceso</span>
                ) : !arrivo ? (
                  <span className="shrink-0 text-xs text-spento">non ti arriva</span>
                ) : (
                  <button
                    onClick={() => accendi(w.chiave, !acceso)}
                    aria-label={acceso ? `Spegni ${w.nome}` : `Accendi ${w.nome}`}
                    className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${acceso ? 'bg-navy' : 'bg-bordo'}`}
                  >
                    <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all ${acceso ? 'left-[22px]' : 'left-0.5'}`} />
                  </button>
                )}
              </div>

              {/* il controllo degli accessi: solo per chi comanda */}
              {comando && (
                <div className="mt-2 flex flex-wrap items-center gap-1.5 pl-7">
                  <Micro>arriva a</Micro>
                  {RUOLI.map(([r, nome]) => {
                    const dentro = ruoliDi(w).includes(r)
                    return (
                      <button
                        key={r}
                        onClick={() => cambiaAccesso(w.chiave, r, !dentro)}
                        className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold transition-colors ${
                          dentro ? 'bg-blu/10 text-blu' : 'border border-bordo text-spento hover:border-spento'
                        }`}
                      >
                        {nome}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </Card>
    </div>
  )
}
