import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import {
  WIDGET, RUOLI, nascosti, haAccesso, inOrdine, salvaOrdine, type Chiave, type Ruolo,
} from '../lib/widget'
import { mieiAccessi, tuttiAccessi, chiedi, decidi, vediCome, type StatoAccesso, type Accesso } from '../lib/accessi'
import { nomeSalvato, salvaNome, iniziali } from '../lib/profilo'
import { leggi as leggiPref, scrivi as scriviPref, type Chiave as ChiavePref } from '../lib/preferenze'
import { Card, TitoloCard, Micro } from './ui'
import Firma from './Firma'
import { collegato as googleCollegato, entraConGoogle } from '../lib/google'
import { stato as statoNotifiche, attiva as attivaNotifiche, spegni as spegniNotifiche, type StatoNotifiche } from '../lib/notifiche'

// Le Impostazioni sono il tuo angolo, non una voce di menu: ci si entra dal
// proprio nome, in basso a sinistra. Dentro solo cose vere, niente
// interruttori che non cambiano niente (Dre, 3/9).

// i ruoli veri dello Studio (documento «Divisioni e responsabilita'» di Giacomo)
const NOME_RUOLO: Record<string, string> = {
  ceo: 'CEO', coordinamento: 'Coordinamento', manager: 'Marketing manager',
  specialist: 'Ad specialist', frontend: 'Frontend',
}

interface Props {
  nome: string
  email: string
  demo: boolean
  ruolo: Ruolo                 // quello vero, dal database (App lo legge da profili)
  ruoloVero?: string           // manager, specialist, frontend: il nome vero del ruolo
  onCambio: () => void
  onNumeri?: () => void
  onWidget?: () => void
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



export default function Impostazioni({ nome, email, demo, ruolo, ruoloVero = ruolo, onCambio, onNumeri, onWidget }: Props) {
  const [spenti] = useState<Chiave[]>(nascosti)
  // i widget a richiesta (Dre, 11/9): i miei, e per i ceo la mappa di tutti
  const [miei, setMiei] = useState<Partial<Record<Chiave, StatoAccesso>>>({})
  const [mappa, setMappa] = useState<Accesso[]>([])
  const [persone, setPersone] = useState<Array<{ id: string; nome: string | null; ruolo: string }>>([])
  const [accessoEsito, setAccessoEsito] = useState<string | null>(null)
  useEffect(() => {
    if (demo) return
    void mieiAccessi().then(setMiei)
    if (ruolo === 'ceo') {
      void tuttiAccessi().then(setMappa)
      void supabase.from('profili').select('id,nome,ruolo').then(({ data }) => setPersone((data as typeof persone) ?? []))
    }
  }, [demo, ruolo])
  async function chiediAccesso(w: Chiave) {
    const err = await chiedi(w, bozzaNome || nome)
    setAccessoEsito(err ? 'Richiesta non partita: ' + err : 'Richiesta mandata a Dre e Giacomo ✓')
    setMiei(await mieiAccessi())
    setTimeout(() => setAccessoEsito(null), 3000)
  }
  async function concedi(user_id: string, w: Chiave, si: boolean) {
    const err = await decidi(user_id, w, si)
    if (err) { setAccessoEsito('Non salvato: ' + err); return }
    setMappa(await tuttiAccessi())
  }
  const [bozzaNome, setBozzaNome] = useState(nomeSalvato() || nome)
  const [salvato, setSalvato] = useState(false)
  // il ponte verso Obsidian: qui dentro sta la spina, non il gesto (Dre, 3/9).
  // Se il nome del vault e' vuoto il ponte e' spento in tutta l'app.
  const [vault, setVault] = useState(() => leggiPref('obsidian-vault'))
  const [vaultSalvato, setVaultSalvato] = useState(false)
  // le notifiche sul telefono: il permesso lo da' il browser, noi salviamo l'indirizzo
  const [notifiche, setNotifiche] = useState<StatoNotifiche | null>(null)
  const [google, setGoogle] = useState<boolean | null>(null)
  const [nuovaPassword, setNuovaPassword] = useState('')
  const [passwordEsito, setPasswordEsito] = useState<string | null>(null)
  const [notificheProblema, setNotificheProblema] = useState<string | null>(null)
  useEffect(() => { void statoNotifiche().then(setNotifiche); if (!demo) void googleCollegato().then(setGoogle) }, [demo])
  const [vistaTask, setVistaTask] = useState(() => leggiPref('task-vista', 'ongo'))
  const [vistaTutti, setVistaTutti] = useState(() => leggiPref('tutti-vista', 'board'))
  const [lista, setLista] = useState(() => inOrdine(WIDGET))
  const [presa, setPresa] = useState<Chiave | null>(null)
  const [sopra, setSopra] = useState<Chiave | null>(null)

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
          <p className="mt-1 text-sm font-semibold">{NOME_RUOLO[ruoloVero] ?? RUOLI.find(([r]) => r === ruolo)?.[1] ?? ruolo}</p>
        </div>
      </Card>

      {/* ── GOOGLE (11/9): Drive, Chat e Calendar a nome tuo ─────── */}
      {!demo && (
        <Card className="p-5">
          <TitoloCard>Google</TitoloCard>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            {google === null ? <span className="text-sm text-spento">controllo…</span>
              : google ? <span className="text-sm font-semibold text-green-800">Collegato ✓</span>
              : <span className="text-sm text-tenue">Non ancora collegato.</span>}
            <button onClick={() => void entraConGoogle()} className="rounded-full border border-bordo px-3.5 py-1.5 text-xs font-bold text-navy hover:border-navy">
              {google ? 'Rinnova il collegamento' : 'Collega Google'}
            </button>
          </div>
        </Card>
      )}

      {/* ── LA FIRMA (Dre, 11/9) ───────────────────────────────── */}
      {!demo && <Firma ceo={ruolo === 'ceo'} />}

      {/* ── WIDGET (Dre, 11/9): il catalogo, e la richiesta ───────── */}
      <Card>
        <header className="flex items-baseline justify-between gap-2 border-b border-velo px-4 py-3">
          <TitoloCard>Widget</TitoloCard>
          <Micro>trascina per riordinare</Micro>
        </header>
        {accessoEsito && <p className="border-b border-velo bg-velo px-4 py-2 text-xs font-semibold">{accessoEsito}</p>}

        {lista.map((w) => {
          const acceso = w.fisso || !spenti.includes(w.chiave)
          const stato = miei[w.chiave]
          const mio = haAccesso(w, ruolo, new Set(stato === 'approvato' ? [w.chiave] : []))
          return (
            <div
              key={w.chiave}
              draggable
              onDragStart={(e) => {
                setPresa(w.chiave)
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
                     className={`h-4 w-4 shrink-0 ${acceso && mio ? 'text-navy' : 'text-spento'}`}>
                  <path d={w.icona} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold">{w.nome}</p>
                  <p className="truncate text-xs text-tenue">{w.cosa}</p>
                </div>
                {w.base && (w.ruoli.length > 1 || ruolo === 'ceo') ? (
                  <Micro>per tutti</Micro>
                ) : ruolo === 'ceo' ? (
                  <Micro>tuo</Micro>
                ) : stato === 'approvato' ? (
                  <Micro>concesso</Micro>
                ) : stato === 'richiesto' ? (
                  <Micro>richiesta inviata</Micro>
                ) : (
                  <button onClick={() => void chiediAccesso(w.chiave)}
                          className="shrink-0 rounded-full border border-bordo px-3 py-1 text-[11px] font-bold text-navy hover:border-navy">
                    {stato === 'negato' ? 'Chiedi di nuovo' : "Chiedi l'accesso"}
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </Card>

      {/* ── VEDI COME (solo ceo, 12/9): il Workspace nei panni di una persona ── */}
      {ruolo === 'ceo' && !demo && persone.length > 0 && (
        <Card className="p-5">
          <TitoloCard>Vedi come</TitoloCard>
          <p className="mt-1 text-xs text-tenue">Ti metti nei panni di una persona: menu, aziende, chat e task diventano i suoi, davvero (lo decide il database). In alto compare la striscia per tornare a te.</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {persone.filter((p) => p.ruolo !== 'ceo').map((p) => (
              <button key={p.id} onClick={() => { void vediCome(p.id).then(() => window.location.reload()) }}
                      className="rounded-full border border-bordo px-3.5 py-1.5 text-xs font-bold text-navy hover:border-navy">
                {p.nome ?? p.id.slice(0, 8)}
              </button>
            ))}
          </div>
        </Card>
      )}

      {/* ── CHI HA COSA (solo ceo): la mappa, e si da' o si toglie da qui ── */}
      {ruolo === 'ceo' && !demo && persone.some((p) => p.ruolo !== 'ceo') && (
        <Card>
          <header className="border-b border-velo px-4 py-3">
            <TitoloCard>Chi ha cosa</TitoloCard>
            <p className="mt-0.5 text-xs text-tenue">Le voci di base le hanno tutti. Queste si danno una a una.</p>
          </header>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="text-left text-[11px] font-bold uppercase tracking-wide text-tenue">
                  <th className="px-4 py-2">Persona</th>
                  {WIDGET.filter((w) => !w.base).map((w) => <th key={w.chiave} className="px-3 py-2">{w.nome}</th>)}
                </tr>
              </thead>
              <tbody>
                {persone.filter((p) => p.ruolo !== 'ceo').map((p) => (
                  <tr key={p.id} className="border-t border-velo">
                    <td className="px-4 py-2 font-semibold">{p.nome ?? p.id.slice(0, 8)}</td>
                    {WIDGET.filter((w) => !w.base).map((w) => {
                      const r = mappa.find((a) => a.user_id === p.id && a.widget === w.chiave)
                      const ha = r?.stato === 'approvato'
                      return (
                        <td key={w.chiave} className="px-3 py-2">
                          <div className="flex items-center gap-2">
                            <Interruttore acceso={ha} etichetta={`${ha ? 'Togli' : 'Dai'} ${w.nome} a ${p.nome ?? ''}`}
                                          onClick={() => void concedi(p.id, w.chiave, !ha)} />
                            {r?.stato === 'richiesto' && <span className="text-[11px] font-semibold text-amber-800">chiesto</span>}
                          </div>
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

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
            {[['ongo', 'On go'], ['big', 'Questa settimana']].map(([v, etichetta]) => (
              <button key={v} onClick={() => preferenza('task-vista', v, setVistaTask)}
                className={`px-3 py-1 text-xs font-bold ${vistaTask === v ? 'bg-blu text-white' : 'bg-white text-tenue'}`}>
                {etichetta}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-3 px-4 py-3">
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold">Pipeline</p>
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

      {/* la password: al primo accesso ognuno si mette la sua (accessi creati il 9/9) */}
      {!demo && (
        <Card>
          <header className="border-b border-velo px-4 py-3">
            <TitoloCard>Password</TitoloCard>
          </header>
          <div className="flex flex-wrap items-center gap-2 px-4 py-3">
            <input
              type="password"
              value={nuovaPassword}
              onChange={(e) => { setNuovaPassword(e.target.value); setPasswordEsito(null) }}
              placeholder="Nuova password (almeno 8 caratteri)"
              autoComplete="new-password"
              className="min-w-[240px] flex-1 rounded-lg border border-bordo px-3 py-2 text-sm outline-none focus:border-blu"
            />
            <button
              type="button"
              disabled={nuovaPassword.length < 8}
              onClick={async () => {
                const { error } = await supabase.auth.updateUser({ password: nuovaPassword })
                setPasswordEsito(error ? 'Non è cambiata: ' + error.message : 'Password cambiata ✓')
                if (!error) setNuovaPassword('')
              }}
              className="rounded-full bg-blu px-4 py-2 text-sm font-semibold text-white hover:bg-blu-scuro disabled:opacity-40"
            >
              Cambia
            </button>
            {passwordEsito && <p className={`w-full text-xs ${passwordEsito.startsWith('Non') ? 'text-red-700' : 'text-green-700'}`}>{passwordEsito}</p>}
          </div>
        </Card>
      )}

      {/* Numeri e Widget stanno qui dentro (intervista 9/9): non sono lavoro di tutti i giorni */}
      {ruolo === 'ceo' && (
      <Card>
        <header className="border-b border-velo px-4 py-3">
          <TitoloCard>Strumenti</TitoloCard>
        </header>
        <div className="divide-y divide-velo">
          <button onClick={onNumeri} className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-semibold hover:bg-velo/50">
            <span>Numeri<span className="ml-2 font-normal text-tenue">funnel, ricorrente, canali</span></span><span className="text-spento">›</span>
          </button>
          <button onClick={onWidget} className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-semibold hover:bg-velo/50">
            <span>Widget e istruzioni<span className="ml-2 font-normal text-tenue">cosa sa fare Clara, e i collegamenti</span></span><span className="text-spento">›</span>
          </button>
        </div>
      </Card>
      )}

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
