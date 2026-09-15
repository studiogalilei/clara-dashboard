import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { Card, TitoloCard } from './ui'

// LA SQUADRA (Dre, 15/9): «dammi il potere di controllare gli accessi di
// tutti». Il ruolo ceo era gia' il grado massimo, ma dentro l'app non si
// vedeva chi entra, chi ha collegato Google, e non c'era modo di chiudere
// la porta a qualcuno: il ruolo si cambiava nel database, l'accesso lo
// toglieva chi sapeva farlo. Adesso si fa da qui, in due secondi.
//
// Il lavoro vero lo fa la funzione in cloud `squadra`, che controlla da sola
// che a chiamarla sia un ceo: bloccare una persona vuol dire che il suo
// accesso smette di valere ovunque, app e database, non nascondere bottoni.

interface Riga {
  id: string
  nome: string | null
  ruolo: string
  email: string | null
  entrato: string | null
  creato: string | null
  google: string | null
  bloccato: boolean
  io: boolean
}

const RUOLI: Array<[string, string]> = [
  ['ceo', 'CEO'],
  ['manager', 'Marketing manager'],
  ['specialist', 'Ad specialist'],
  ['frontend', 'Frontend'],
  ['coordinamento', 'Coordinamento'],
]

const GG = 86400e3
function daQuando(iso: string | null): string {
  if (!iso) return 'mai entrato'
  const n = Math.floor((Date.now() - new Date(iso).getTime()) / GG)
  if (n <= 0) return 'entrato oggi'
  if (n === 1) return 'entrato ieri'
  if (n < 30) return `entrato ${n} giorni fa`
  return `entrato il ${new Date(iso).toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })}`
}

export default function Squadra() {
  const [righe, setRighe] = useState<Riga[] | null>(null)
  const [errore, setErrore] = useState<string | null>(null)
  const [chiedo, setChiedo] = useState<string | null>(null)   // id di chi sto per bloccare
  const [lavoro, setLavoro] = useState<string | null>(null)

  async function chiama(corpo: Record<string, unknown>): Promise<{ righe?: Riga[]; errore?: string }> {
    const { data, error } = await supabase.functions.invoke('squadra', { body: corpo })
    if (error) return { errore: error.message }
    return (data ?? {}) as { righe?: Riga[]; errore?: string }
  }

  async function carica() {
    const r = await chiama({ azione: 'elenco' })
    if (r.errore) { setErrore(r.errore); setRighe([]); return }
    setRighe(r.righe ?? [])
  }
  useEffect(() => { void carica() }, [])

  async function agisci(id: string, corpo: Record<string, unknown>) {
    setLavoro(id)
    const r = await chiama({ ...corpo, id })
    setLavoro(null)
    setChiedo(null)
    if (r.errore) { setErrore(r.errore); return }
    setErrore(null)
    await carica()
  }

  if (righe === null) return (
    <Card className="p-5"><TitoloCard>Le persone</TitoloCard>
      <p className="mt-2 text-sm text-spento">Guardo chi c'è…</p></Card>
  )
  if (righe.length === 0 && errore) return (
    <Card className="p-5"><TitoloCard>Le persone</TitoloCard>
      <p className="mt-2 text-sm text-tenue">{errore}</p></Card>
  )

  return (
    <Card>
      <header className="border-b border-velo px-4 py-3">
        <TitoloCard>Le persone</TitoloCard>
        <p className="mt-1 text-xs text-tenue">
          Chi entra nel Workspace, con che ruolo e con quali Google. Bloccare qui chiude tutto, anche il database.
        </p>
      </header>

      {errore && (
        <p className="border-b border-red-100 bg-red-50 px-4 py-2 text-sm font-semibold text-red-800">{errore}</p>
      )}

      <ul>
        {righe.map((p) => (
          <li key={p.id} className="flex flex-wrap items-center gap-x-3 gap-y-2 border-t border-velo px-4 py-3 first:border-t-0">
            <div className="min-w-[160px] flex-1">
              <p className="text-sm font-bold">
                {p.nome ?? p.email ?? p.id.slice(0, 8)}
                {p.io && <span className="ml-2 text-[11px] font-semibold text-spento">sei tu</span>}
              </p>
              <p className="text-xs text-tenue">{p.email ?? 'senza email'}</p>
            </div>

            <div className="flex min-w-[150px] flex-col gap-0.5 text-xs">
              <span className={p.bloccato ? 'font-semibold text-red-800' : 'text-tenue'}>
                {p.bloccato ? 'Accesso bloccato' : daQuando(p.entrato)}
              </span>
              <span className={p.google ? 'text-green-800' : 'text-spento'}>
                {p.google ? 'Google collegato' : 'Google non collegato'}
              </span>
            </div>

            <select
              value={p.ruolo}
              disabled={p.io || lavoro === p.id}
              onChange={(e) => void agisci(p.id, { azione: 'ruolo', ruolo: e.target.value })}
              className="rounded-lg border border-bordo bg-white px-2.5 py-1.5 text-xs font-semibold text-inchiostro outline-none focus:border-blu disabled:text-spento"
            >
              {RUOLI.map(([r, n]) => <option key={r} value={r}>{n}</option>)}
            </select>

            {/* la domanda sta qui dentro, sulla riga di chi tocca: bloccare
                una persona non si chiede in un popup del browser */}
            {p.io ? null : chiedo === p.id ? (
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold">Blocco {p.nome ?? 'questa persona'}?</span>
                <button onClick={() => void agisci(p.id, { azione: 'blocca' })}
                        className="rounded-full bg-red-700 px-3 py-1.5 text-xs font-bold text-white hover:bg-red-800">
                  Conferma
                </button>
                <button onClick={() => setChiedo(null)}
                        className="rounded-full border border-bordo px-3 py-1.5 text-xs font-bold text-tenue hover:border-spento">
                  Annulla
                </button>
              </div>
            ) : lavoro === p.id ? (
              <span className="text-xs font-semibold text-spento">Ci sto…</span>
            ) : p.bloccato ? (
              <button onClick={() => void agisci(p.id, { azione: 'sblocca' })}
                      className="rounded-full border border-bordo px-3 py-1.5 text-xs font-bold text-navy hover:border-navy">
                Riapri l'accesso
              </button>
            ) : (
              <div className="flex items-center gap-2">
                {p.google && (
                  <button onClick={() => void agisci(p.id, { azione: 'scollega' })}
                          className="rounded-full border border-bordo px-3 py-1.5 text-xs font-bold text-tenue hover:border-spento">
                    Stacca Google
                  </button>
                )}
                <button onClick={() => setChiedo(p.id)}
                        className="rounded-full border border-bordo px-3 py-1.5 text-xs font-bold text-red-800 hover:border-red-300">
                  Blocca l'accesso
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>

      <p className="border-t border-velo px-4 py-2.5 text-[11px] text-spento">
        Bloccare toglie l'accesso al Workspace e stacca Clara dai suoi Google. La mail e i file di Google
        restano suoi: quelli si tolgono dalla console di Google, sospendendo l'account.
      </p>
    </Card>
  )
}
