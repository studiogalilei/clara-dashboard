import { useState } from 'react'
import { supabase } from '../lib/supabase'
import {
  WIDGET, RUOLI, accessi, salvaAccessi, nascosti, salvaNascosti,
  mioRuolo, scegliRuolo, ruoliDi, type Chiave, type Ruolo,
} from '../lib/widget'
import { nomeSalvato, salvaNome, iniziali } from '../lib/profilo'
import { Card, TitoloCard, Micro } from './ui'

// Le Impostazioni sono il tuo angolo, non una voce di menu: ci si entra dal
// proprio nome, in basso a sinistra. Dentro solo cose vere, niente
// interruttori che non cambiano niente (Dre, 3/9).

interface Props {
  nome: string
  email: string
  demo: boolean
  onCambio: () => void
}

function Interruttore({ acceso, onClick, etichetta }: { acceso: boolean; onClick: () => void; etichetta: string }) {
  return (
    <button
      onClick={onClick}
      aria-label={etichetta}
      className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${acceso ? 'bg-navy' : 'bg-bordo'}`}
    >
      <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all ${acceso ? 'left-[22px]' : 'left-0.5'}`} />
    </button>
  )
}

function leggi(chiave: string, difetto: string): string {
  try { return localStorage.getItem(chiave) ?? difetto } catch { return difetto }
}

export default function Impostazioni({ nome, email, demo, onCambio }: Props) {
  const [ruolo, setRuolo] = useState<Ruolo>(mioRuolo)
  const [spenti, setSpenti] = useState<Chiave[]>(nascosti)
  const [acc, setAcc] = useState(accessi)
  const [bozzaNome, setBozzaNome] = useState(nomeSalvato() || nome)
  const [salvato, setSalvato] = useState(false)
  const [vistaTask, setVistaTask] = useState(() => leggi('task-vista', 'ongo'))
  const [vistaTutti, setVistaTutti] = useState(() => leggi('tutti-vista', 'board'))
  const comando = ruolo === 'ceo'

  function scriviNome() {
    salvaNome(bozzaNome)
    setSalvato(true)
    setTimeout(() => setSalvato(false), 2000)
    onCambio()
  }

  function preferenza(chiave: string, valore: string, set: (v: string) => void) {
    try { localStorage.setItem(chiave, valore) } catch { /* niente */ }
    set(valore); onCambio()
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4 pb-24 sm:pb-8">

      {/* ── PROFILO ────────────────────────────────────────────── */}
      <Card className="p-5">
        <TitoloCard>Profilo</TitoloCard>
        <div className="mt-2 flex items-center gap-4">
          <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-navy text-lg font-bold text-white">
            {iniziali(bozzaNome || nome)}
          </span>
          <div className="min-w-0 flex-1">
            <label className="block">
              <Micro>Come ti chiami</Micro>
              <input
                value={bozzaNome}
                onChange={(e) => setBozzaNome(e.target.value)}
                onBlur={scriviNome}
                onKeyDown={(e) => e.key === 'Enter' && scriviNome()}
                placeholder="Nome e cognome"
                className="mt-0.5 w-full rounded-lg border border-bordo px-3 py-2 text-sm outline-none focus:border-blu"
              />
            </label>
            <p className="mt-1.5 text-xs text-tenue">
              {demo ? 'Stai guardando la demo, con dati finti' : email}
              {salvato && <span className="ml-2 font-semibold text-green-700">salvato ✓</span>}
            </p>
          </div>
        </div>

        <div className="mt-4 border-t border-velo pt-3">
          <Micro>Il tuo ruolo</Micro>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {RUOLI.map(([r, etichetta]) => (
              <button
                key={r}
                onClick={() => { setRuolo(r); scegliRuolo(r); onCambio() }}
                className={`rounded-full px-3.5 py-1.5 text-xs font-bold transition-colors ${
                  ruolo === r ? 'bg-navy text-white' : 'border border-bordo bg-white text-tenue hover:border-navy'
                }`}
              >
                {etichetta}
              </button>
            ))}
          </div>
          <p className="mt-1.5 text-xs text-spento">
            Il ruolo decide a quali widget arrivi. Cambialo per vedere la Dashboard con gli occhi di un altro.
          </p>
        </div>
      </Card>

      {/* ── WIDGET ─────────────────────────────────────────────── */}
      <Card>
        <header className="flex items-baseline justify-between gap-2 border-b border-velo px-4 py-3">
          <TitoloCard>Widget</TitoloCard>
          <Micro>{WIDGET.filter((w) => w.fisso || !spenti.includes(w.chiave)).length} su {WIDGET.length} accesi</Micro>
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
                  <Micro>sempre acceso</Micro>
                ) : !arrivo ? (
                  <Micro>non ti arriva</Micro>
                ) : (
                  <Interruttore
                    acceso={acceso}
                    etichetta={acceso ? `Spegni ${w.nome}` : `Accendi ${w.nome}`}
                    onClick={() => {
                      const n = acceso ? [...spenti, w.chiave] : spenti.filter((x) => x !== w.chiave)
                      setSpenti(n); salvaNascosti(n); onCambio()
                    }}
                  />
                )}
              </div>

              {comando && (
                <div className="mt-2 flex flex-wrap items-center gap-1.5 pl-7">
                  <Micro>arriva a</Micro>
                  {RUOLI.map(([r, etichetta]) => {
                    const dentro = ruoliDi(w).includes(r)
                    return (
                      <button
                        key={r}
                        onClick={() => {
                          const ora = acc[w.chiave] ?? w.ruoli
                          const n = { ...acc, [w.chiave]: dentro ? ora.filter((x) => x !== r) : [...new Set([...ora, r])] }
                          setAcc(n); salvaAccessi(n); onCambio()
                        }}
                        className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold transition-colors ${
                          dentro ? 'bg-blu/10 text-blu' : 'border border-bordo text-spento hover:border-spento'
                        }`}
                      >
                        {etichetta}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </Card>

      {/* ── COME SI APRE ───────────────────────────────────────── */}
      <Card>
        <header className="border-b border-velo px-4 py-3">
          <TitoloCard>Come si apre</TitoloCard>
        </header>
        <div className="flex items-center gap-3 border-b border-velo px-4 py-3">
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold">Task</p>
            <p className="text-xs text-tenue">La vista con cui parte</p>
          </div>
          <div className="flex shrink-0 overflow-hidden rounded-full border border-bordo">
            {[['ongo', 'On go'], ['big', 'Week picture']].map(([v, etichetta]) => (
              <button key={v} onClick={() => preferenza('task-vista', v, setVistaTask)}
                className={`px-3 py-1 text-xs font-bold ${vistaTask === v ? 'bg-navy text-white' : 'bg-white text-tenue'}`}>
                {etichetta}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-3 px-4 py-3">
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold">Tutti</p>
            <p className="text-xs text-tenue">La vista con cui parte</p>
          </div>
          <div className="flex shrink-0 overflow-hidden rounded-full border border-bordo">
            {[['board', 'Bacheca'], ['elenco', 'Elenco']].map(([v, etichetta]) => (
              <button key={v} onClick={() => preferenza('tutti-vista', v, setVistaTutti)}
                className={`px-3 py-1 text-xs font-bold ${vistaTutti === v ? 'bg-navy text-white' : 'bg-white text-tenue'}`}>
                {etichetta}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {!demo && (
        <button
          onClick={() => supabase.auth.signOut()}
          className="w-full rounded-2xl border border-bordo bg-white px-4 py-3 text-sm font-semibold text-tenue transition-colors hover:border-red-300 hover:text-red-700"
        >
          Esci
        </button>
      )}
    </div>
  )
}
