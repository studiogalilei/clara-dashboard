import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import {
  WIDGET, RUOLI, accessi, salvaAccessi, nascosti, salvaNascosti,
  mioRuolo, scegliRuolo, ruoliDi, inOrdine, salvaOrdine, type Chiave, type Ruolo,
} from '../lib/widget'
import { nomeSalvato, salvaNome, iniziali } from '../lib/profilo'
import { leggi as leggiPref, scrivi as scriviPref, type Chiave as ChiavePref } from '../lib/preferenze'
import { Card, TitoloCard, Micro } from './ui'
import { stato as statoNotifiche, attiva as attivaNotifiche, spegni as spegniNotifiche, type StatoNotifiche } from '../lib/notifiche'

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



export default function Impostazioni({ nome, email, demo, onCambio }: Props) {
  const [ruolo, setRuolo] = useState<Ruolo>(mioRuolo)
  const [spenti, setSpenti] = useState<Chiave[]>(nascosti)
  const [acc, setAcc] = useState(accessi)
  const [bozzaNome, setBozzaNome] = useState(nomeSalvato() || nome)
  const [salvato, setSalvato] = useState(false)
  // il ponte verso Obsidian: qui dentro sta la spina, non il gesto (Dre, 3/9).
  // Se il nome del vault e' vuoto il ponte e' spento in tutta l'app.
  const [vault, setVault] = useState(() => leggiPref('obsidian-vault'))
  const [vaultSalvato, setVaultSalvato] = useState(false)
  // le notifiche sul telefono: il permesso lo da' il browser, noi salviamo l'indirizzo
  const [notifiche, setNotifiche] = useState<StatoNotifiche | null>(null)
  const [notificheProblema, setNotificheProblema] = useState<string | null>(null)
  useEffect(() => { void statoNotifiche().then(setNotifiche) }, [])
  const [vistaTask, setVistaTask] = useState(() => leggiPref('task-vista', 'ongo'))
  const [vistaTutti, setVistaTutti] = useState(() => leggiPref('tutti-vista', 'board'))
  const [lista, setLista] = useState(() => inOrdine(WIDGET))
  const [presa, setPresa] = useState<Chiave | null>(null)
  const [sopra, setSopra] = useState<Chiave | null>(null)
  const comando = ruolo === 'ceo'

  // trascina per riordinare: l'ordine vale per il menu, non solo per qui
  function lascia(sopra: Chiave) {
    if (!presa || presa === sopra) return
    const n = [...lista]
    const da = n.findIndex((w) => w.chiave === presa)
    const a = n.findIndex((w) => w.chiave === sopra)
    const [mosso] = n.splice(da, 1)
    n.splice(da < a ? a - 1 : a, 0, mosso)   // come in Oggi: gli indici scalano
    setLista(n)
    salvaOrdine(n.map((w) => w.chiave))
    setPresa(null)
    setSopra(null)
    onCambio()
  }

  function scriviNome() {
    salvaNome(bozzaNome)
    setSalvato(true)
    setTimeout(() => setSalvato(false), 2000)
    onCambio()
  }

  function preferenza(chiave: ChiavePref, valore: string, set: (v: string) => void) {
    scriviPref(chiave, valore)
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
                  ruolo === r ? 'bg-blu text-white' : 'border border-bordo bg-white text-tenue hover:border-navy'
                }`}
              >
                {etichetta}
              </button>
            ))}
          </div>
          <p className="mt-1.5 text-xs text-spento">
            {WIDGET.filter((w) => ruoliDi(w).includes(ruolo)).length} widget su {WIDGET.length}
          </p>
        </div>
      </Card>

      {/* ── WIDGET ─────────────────────────────────────────────── */}
      <Card>
        <header className="flex items-baseline justify-between gap-2 border-b border-velo px-4 py-3">
          <TitoloCard>Widget</TitoloCard>
          <Micro>trascina per riordinare</Micro>
        </header>

        {lista.map((w) => {
          const acceso = w.fisso || !spenti.includes(w.chiave)
          const arrivo = ruoliDi(w).includes(ruolo)
          return (
            <div
              key={w.chiave}
              draggable
              onDragStart={(e) => {
                setPresa(w.chiave)
                // Firefox non avvia il trascinamento senza dati (revisione 4/9)
                e.dataTransfer.setData('text/plain', w.chiave)
                e.dataTransfer.effectAllowed = 'move'
              }}
              onDragOver={(e) => { e.preventDefault(); setSopra(w.chiave) }}
              onDrop={(e) => { e.preventDefault(); lascia(w.chiave) }}
              onDragEnd={() => { setPresa(null); setSopra(null) }}
              className={`border-b border-velo px-4 py-3 last:border-0 ${
                presa === w.chiave ? 'bg-velo opacity-60' : ''
              } ${sopra === w.chiave && presa && presa !== w.chiave ? 'border-t-2 border-t-blu' : ''}`}
            >
              <div className="flex items-center gap-3">
                <span className="cursor-grab text-spento active:cursor-grabbing" aria-hidden>
                  <svg viewBox="0 0 24 24" className="h-4 w-4">
                    <path fill="currentColor" d="M9 5h2v2H9zM13 5h2v2h-2zM9 11h2v2H9zM13 11h2v2h-2zM9 17h2v2H9zM13 17h2v2h-2z" />
                  </svg>
                </span>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
                     className={`h-4 w-4 shrink-0 ${acceso && arrivo ? 'text-navy' : 'text-spento'}`}>
                  <path d={w.icona} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold">{w.nome}</p>
                  <p className="truncate text-xs text-tenue">{w.cosa}</p>
                </div>
                {w.fisso ? (
                  <Micro>sempre</Micro>
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

              {comando && !w.fisso && (
                <div className="mt-2 flex flex-wrap items-center gap-1.5 pl-14">
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
          </div>
          <div className="flex shrink-0 overflow-hidden rounded-full border border-bordo">
            {[['ongo', 'On go'], ['big', 'Week picture']].map(([v, etichetta]) => (
              <button key={v} onClick={() => preferenza('task-vista', v, setVistaTask)}
                className={`px-3 py-1 text-xs font-bold ${vistaTask === v ? 'bg-blu text-white' : 'bg-white text-tenue'}`}>
                {etichetta}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-3 px-4 py-3">
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold">Tutti</p>
          </div>
          <div className="flex shrink-0 overflow-hidden rounded-full border border-bordo">
            {[['board', 'Bacheca'], ['elenco', 'Elenco']].map(([v, etichetta]) => (
              <button key={v} onClick={() => preferenza('tutti-vista', v, setVistaTutti)}
                className={`px-3 py-1 text-xs font-bold ${vistaTutti === v ? 'bg-blu text-white' : 'bg-white text-tenue'}`}>
                {etichetta}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* ── OBSIDIAN ───────────────────────────────────────────── */}
      <Card>
        <header className="border-b border-velo px-4 py-3">
          <TitoloCard>Obsidian</TitoloCard>
        </header>
        <div className="px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <input
              value={vault}
              onChange={(e) => { setVault(e.target.value); setVaultSalvato(false) }}
              onBlur={() => { scriviPref('obsidian-vault', vault.trim()); setVaultSalvato(true); onCambio() }}
              onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur() }}
              placeholder="Nome del vault"
              className="min-w-[200px] flex-1 rounded-lg border border-bordo px-3 py-2 text-sm outline-none focus:border-blu"
            />
            <a
              href={vault.trim() ? `obsidian://open?vault=${encodeURIComponent(vault.trim())}` : undefined}
              aria-disabled={!vault.trim()}
              className={`shrink-0 rounded-full border border-bordo px-4 py-2 text-sm font-semibold ${
                vault.trim() ? 'text-tenue hover:border-navy hover:text-navy' : 'pointer-events-none opacity-30'
              }`}
            >
              Aprilo
            </a>
          </div>
          <p className="mt-1.5 text-xs text-spento">
            {vault.trim()
              ? <>Sulle schede compare «cerca in Obsidian», sotto i puntini{vaultSalvato && <span className="ml-2 font-semibold text-green-700">salvato ✓</span>}</>
              : 'Spento: senza il nome del vault i collegamenti non saprebbero dove andare'}
          </p>
        </div>
      </Card>

      <Card>
        <header className="border-b border-velo px-4 py-3">
          <TitoloCard>Notifiche</TitoloCard>
        </header>
        <div className="px-4 py-3">
          <div className="flex flex-wrap items-center gap-3">
            <p className="min-w-[200px] flex-1 text-sm">
              {notifiche === 'attive' && 'Attive su questo dispositivo: quando ci sono bozze da approvare, Clara ti avvisa qui.'}
              {notifiche === 'spente' && 'Spente. Accendile e Clara ti avvisa quando c\'è qualcosa da approvare.'}
              {notifiche === 'negate' && 'Il browser le ha bloccate: si riaccendono dalle impostazioni del sito.'}
              {notifiche === 'da-installare' && 'Su iPhone prima aggiungi la Dashboard alla schermata Home (condividi → Aggiungi alla schermata Home), poi riapri da lì.'}
              {notifiche === 'non-supportate' && 'Questo browser non le supporta.'}
              {notifiche === null && '…'}
            </p>
            {(notifiche === 'spente' || notifiche === 'attive') && (
              <button
                type="button"
                onClick={async () => {
                  setNotificheProblema(null)
                  if (notifiche === 'attive') { setNotifiche(await spegniNotifiche()); return }
                  const r = await attivaNotifiche()
                  setNotifiche(r.stato); setNotificheProblema(r.problema ?? null)
                }}
                className="shrink-0 rounded-full border border-bordo px-4 py-2 text-sm font-semibold text-tenue hover:border-navy hover:text-navy"
              >
                {notifiche === 'attive' ? 'Spegni' : 'Attiva le notifiche'}
              </button>
            )}
          </div>
          {notificheProblema && <p className="mt-1.5 text-xs text-red-700">Non si sono accese: {notificheProblema}</p>}
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
