import { useEffect, useRef, useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase, configured, demo } from './lib/supabase'
import { scarica as scaricaPreferenze, leggi as leggiPref, scrivi as scriviPref } from './lib/preferenze'
import Login from './components/Login'
import Oggi from './components/Oggi'
import Lista from './components/Lista'
import Pipeline from './components/Pipeline'
import ClaraVolante from './components/ClaraVolante'
import ClaraLogo from './components/ClaraLogo'
import Vault from './components/Vault'
import Plugin from './components/Plugin'
import Calendario from './components/Calendario'
import { oggi as giornoOggi } from './lib/regole'
import Impostazioni from './components/Impostazioni'
import TuttiElenco from './components/TuttiElenco'
import Progetti from './components/Progetti'
import { menuDi, mioRuolo, widgetDi, type Chiave } from './lib/widget'
import { nomeDa } from './lib/profilo'
import Analytics from './components/Analytics'
import Scheda from './components/Scheda'

// La struttura sul riferimento scelto da Dre (31/8): sidebar bianca a
// sinistra, testata con titolo grande e ricerca, contenuto in carte morbide.
// Sul telefono la sidebar sparisce e resta la barra in basso.

// il menu si compone dal registro dei widget: aggiungerne uno non si tocca
// piu' qui dentro (Dre, 3/9)
type Tab = Chiave

// il saluto grande: cambia ogni giorno, a volte fa anche ridere.
// Deterministico sul giorno dell'anno: tutta la giornata la stessa frase.
// Frasi BREVI (regola di Dre): il saluto sta su una riga, la coda va a capo.
const SALUTI_MATTINA: Array<[string, string]> = [
  ['Buongiorno, Dre.', ''],
  ['Buongiorno, Dre.', 'Si apre il sipario.'],
  ['Buongiorno, Dre.', 'I lead non si chiudono da soli.'],
  ['Buongiorno, Dre.', 'Oggi si spedisce.'],
  ['Buongiorno, Dre.', 'Prima il caffè, poi la coda.'],
  ['Buongiorno, Dre.', 'Telescopio sui lead.'],
  ['Buongiorno, capitano.', ''],
  ['Buongiorno, Dre.', 'Un lead alla volta.'],
]
const SALUTI_POMERIGGIO: Array<[string, string]> = [
  ['Buon pomeriggio, Dre.', ''],
  ['Buon pomeriggio, Dre.', 'Orario buono per le call.'],
  ['Pomeriggio, Dre.', 'Ancora un paio di carte da muovere.'],
  ['Buon pomeriggio, Dre.', 'Secondo tempo.'],
  ['Buon pomeriggio, Dre.', 'La pipeline non guarda l\'orologio.'],
]
const SALUTI_SERA: Array<[string, string]> = [
  ['Buonasera, Dre.', ''],
  ['Buonasera, Dre.', 'Ultima occhiata e si chiude.'],
  ['Buonasera, Dre.', 'I lead dormono. Tu quasi.'],
  ['Sera, Dre.', 'Domani si rilancia.'],
]

function saluto(): [string, string] {
  const ora = new Date()
  const giorno = Math.floor((ora.getTime() - new Date(ora.getFullYear(), 0, 0).getTime()) / 86400e3)
  const h = ora.getHours()
  const pool = h < 13 ? SALUTI_MATTINA : h < 18 ? SALUTI_POMERIGGIO : SALUTI_SERA
  return pool[giorno % pool.length]
}

export default function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [ready, setReady] = useState(false)
  const [tab, setTab] = useState<Tab>(() =>
    typeof window !== 'undefined' && window.innerWidth < 1024 ? 'oggi' : 'pipeline')
  const [openId, setOpenId] = useState<string | null>(null)
  const [q, setQ] = useState('')
  // alla chiusura della scheda le viste si ricaricano: la bacheca non deve
  // mai mentire su una fase appena cambiata
  const [versione, setVersione] = useState(0)
  // il menu si allarga e si stringe trascinando il filo, come su Claude
  // (Dre, 4/9). La larghezza e' una preferenza: ti segue sul telefono
  const [menuLargo, setMenuLargo] = useState(() => Number(leggiPref('menu-larghezza')) || 224)
  const tiroMenu = useRef(false)
  const [salutoClara, setSalutoClara] = useState<string | null>(null)
  const cercaRef = useRef<HTMLInputElement>(null)

  function chiudiScheda() {
    setOpenId(null)
    setVersione((v) => v + 1)
  }

  useEffect(() => {
    function muovi(e: PointerEvent) {
      if (!tiroMenu.current) return
      e.preventDefault()
      setMenuLargo(Math.min(Math.max(e.clientX, 180), 400))
    }
    function molla() {
      if (!tiroMenu.current) return
      tiroMenu.current = false
      document.body.style.userSelect = ''
      setMenuLargo((w) => { scriviPref('menu-larghezza', String(w)); return w })
    }
    window.addEventListener('pointermove', muovi)
    window.addEventListener('pointerup', molla)
    return () => {
      window.removeEventListener('pointermove', muovi)
      window.removeEventListener('pointerup', molla)
    }
  }, [])

  useEffect(() => {
    if (!configured) {
      setReady(true)
      return
    }
    supabase.auth.getSession().then(async ({ data }) => {
      setSession(data.session)
      // quello che hai scelto da un altro dispositivo vince su questo
      // browser: le preferenze seguono te, non la macchina (revisione 4/9)
      if (data.session && await scaricaPreferenze()) setVersione((v) => v + 1)
      setReady(true)
    })
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s))
    return () => sub?.subscription.unsubscribe()
  }, [])

  // il buongiorno in testata è uno spazio di Clara: se oggi l'ha scritto,
  // si mostra il suo
  useEffect(() => {
    if (!configured) return
    const oggiIso = giornoOggi()
    supabase
      .from('clara_messaggi')
      .select('*')
      .eq('tipo', 'saluto')
      .gte('at', oggiIso + 'T00:00:00')
      .order('at', { ascending: false })
      .limit(1)
      .then(({ data }) => {
        const m = (data as Array<{ testo: string }> | null)?.[0]
        if (m?.testo) setSalutoClara(m.testo)
      })
  }, [])

  // ⌘K (o Ctrl+K) porta sempre alla ricerca
  useEffect(() => {
    function giu(e: KeyboardEvent) {
      const dentroUnCampo = ['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)
      if (((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') || (e.key === '/' && !dentroUnCampo)) {
        e.preventDefault()
        setOpenId(null)
        cercaRef.current?.focus()
      }
    }
    window.addEventListener('keydown', giu)
    return () => window.removeEventListener('keydown', giu)
  }, [])

  if (!configured) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-fondo px-6">
        <div className="max-w-md rounded-2xl border border-bordo bg-white p-6">
          <h1 className="mb-2 text-lg font-bold">Dashboard: manca la configurazione</h1>
          <p className="text-sm text-tenue">
            Compila <code className="rounded bg-velo px-1">.env.local</code> con URL e chiave
            del progetto Supabase, poi riavvia. Le istruzioni sono in SETUP.md.
          </p>
        </div>
      </div>
    )
  }

  if (!ready) return null
  if (!session) return <Login />

  const mail = demo ? '' : (session.user.email ?? '')
  const utente = nomeDa(mail, demo)
  const titolo = widgetDi(tab)?.nome ?? (tab === 'impostazioni' ? 'Impostazioni' : '')
  const ruolo = mioRuolo()
  const voci = menuDi(ruolo, 'menu')
  const vociSistema = menuDi(ruolo, 'sistema')

  return (
    <div className="min-h-dvh bg-fondo lg:flex">

      {/* ── sidebar (solo desktop) ─────────────────────────────── */}
      <aside
        style={{ width: menuLargo }}
        className="sticky top-0 hidden h-dvh shrink-0 flex-col border-r border-bordo bg-white px-4 py-5 lg:flex"
      >
        {/* il filo per allargare: si scurisce quando ci passi sopra */}
        <div
          onPointerDown={(e) => {
            e.preventDefault()
            tiroMenu.current = true
            // se no trascinando si seleziona mezza pagina
            document.body.style.userSelect = 'none'
          }}
          onDoubleClick={() => { setMenuLargo(224); scriviPref('menu-larghezza', '224') }}
          aria-label="Allarga o stringi il menu"
          title="Trascina per allargare, doppio clic per rimetterlo com'era"
          className="group absolute inset-y-0 right-0 z-10 w-3 translate-x-1.5 cursor-col-resize"
        >
          <span className="absolute inset-y-0 left-1.5 w-px bg-transparent transition-colors group-hover:bg-blu" />
          <span className="absolute left-[1px] top-1/2 h-8 w-[5px] -translate-y-1/2 rounded-full bg-transparent transition-colors group-hover:bg-blu/30" />
        </div>
        <div className="mb-8 flex items-center gap-2.5 px-2">
          <span className="text-navy"><ClaraLogo size={36} /></span>
          <span className="text-[15px] leading-tight tracking-tight text-navy">
            <span className="font-extrabold">Clara</span>
            <span className="ml-1 font-medium">dashboard</span>
            <span className="block text-[11px] font-semibold text-inchiostro">SG intelligence</span>
          </span>
        </div>

        <p className="mb-2 px-2 text-[11px] font-bold uppercase tracking-[0.08em] text-spento">
          Menu
        </p>
        <nav className="space-y-1">
          {voci.map(({ chiave: t, nome: label, icona }) => {
            const attivo = tab === t
            return (
              <button
                key={t}
                onClick={() => { setTab(t); setOpenId(null) }}
                className={`relative flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition-colors ${
                  attivo ? 'bg-velo text-inchiostro' : 'text-tenue hover:bg-velo/60 hover:text-inchiostro'
                }`}
              >
                {attivo && <span className="absolute -left-4 h-6 w-1 rounded-r-full bg-navy" />}
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
                     strokeLinecap="round" strokeLinejoin="round"
                     className={`h-[18px] w-[18px] ${attivo ? 'text-navy' : ''}`}>
                  <path d={icona} />
                </svg>
                {label}
              </button>
            )
          })}
        </nav>

        <p className="mb-2 mt-7 px-2 text-[11px] font-bold uppercase tracking-[0.08em] text-spento">
          Sistema
        </p>
        <nav className="space-y-1">
          {vociSistema.map(({ chiave: t, nome: label, icona }) => {
            const attivo = tab === t
            return (
              <button
                key={t}
                onClick={() => { setTab(t); setOpenId(null) }}
                className={`relative flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition-colors ${
                  attivo ? 'bg-velo text-inchiostro' : 'text-tenue hover:bg-velo/60 hover:text-inchiostro'
                }`}
              >
                {attivo && <span className="absolute -left-4 h-6 w-1 rounded-r-full bg-navy" />}
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
                     strokeLinecap="round" strokeLinejoin="round"
                     className={`h-[18px] w-[18px] ${attivo ? 'text-navy' : ''}`}>
                  <path d={icona} />
                </svg>
                {label}
              </button>
            )
          })}
        </nav>

        <div className="mt-auto border-t border-velo pt-3">
          <button
            onClick={() => { setTab('impostazioni'); setOpenId(null) }}
            className={`flex w-full items-center gap-2.5 rounded-xl px-2 py-2 text-left transition-colors ${
              tab === 'impostazioni' ? 'bg-velo' : 'hover:bg-velo/60'
            }`}
          >
            <img src="/sg-simbolo.svg" alt="Studio Galilei" className="h-8 w-8 shrink-0 object-contain" />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-semibold">{utente}</span>
              <span className="block text-[11px] text-spento">Impostazioni</span>
            </span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
                 className={`h-4 w-4 shrink-0 ${tab === 'impostazioni' ? 'text-navy' : 'text-spento'}`}>
              <path d="M9 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      </aside>

      {/* ── contenuto ──────────────────────────────────────────── */}
      <div className="min-w-0 flex-1">

        {/* barra mobile */}
        <header className="sticky top-0 z-10 flex items-center gap-3 border-b border-bordo bg-white px-4 py-2.5 lg:hidden">
          <span className="shrink-0 text-navy"><ClaraLogo size={28} /></span>
          <div className="relative min-w-0 flex-1">
            <input
              type="search"
              placeholder="Cerca…"
              value={q}
              onChange={(e) => {
                setQ(e.target.value)
                if (e.target.value.trim()) { setTab('prospect'); setOpenId(null) }
              }}
              className="w-full rounded-full border border-bordo bg-velo px-4 py-1.5 pr-8 text-sm outline-none focus:border-blu focus:bg-white"
            />
            {q && (
              <button
                onClick={() => setQ('')}
                aria-label="Pulisci la ricerca"
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-sm text-spento"
              >
                ×
              </button>
            )}
          </div>
        </header>

        <main className={`mx-auto px-4 py-5 lg:px-8 lg:py-7 ${tab === 'calendario' ? '' : 'max-w-6xl'}`}>
          {/* testata */}
          <div className="mb-5 flex flex-wrap items-center gap-4">
            <div className="min-w-0 flex-1">
              <h1 className="flex items-center gap-2 text-[19px] font-extrabold tracking-tight lg:text-[21px]">
                {tab === 'pipeline' && <span className="text-navy"><ClaraLogo size={26} /></span>}
                {tab === 'pipeline' ? saluto()[0] : titolo}
              </h1>
              {tab === 'pipeline' && (salutoClara ? (
                <p className="text-sm font-medium">
                  {salutoClara.replace(/^buon\w*[,.]?\s+dre[.,]?\s*/i, '')}
                </p>
              ) : saluto()[1] ? (
                <p className="text-sm font-medium">{saluto()[1]}</p>
              ) : null)}
            </div>
            <div className="relative hidden w-72 lg:block">
              <input
                ref={cercaRef}
                type="search"
                placeholder="Cerca…   ⌘K"
                value={q}
                onChange={(e) => {
                  setQ(e.target.value)
                  if (e.target.value.trim()) { setTab('prospect'); setOpenId(null) }
                }}
                className="w-full rounded-full border border-bordo bg-white px-4 py-2 pr-8 text-sm shadow-[0_1px_2px_rgba(16,24,40,0.04)] outline-none focus:border-blu"
              />
              {q && (
                <button
                  onClick={() => setQ('')}
                  aria-label="Pulisci la ricerca"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-spento hover:text-inchiostro"
                >
                  ×
                </button>
              )}
            </div>
          </div>

          <div key={versione}>
            {tab === 'oggi' ? (
              <Oggi onOpen={setOpenId} />
            ) : tab === 'pipeline' ? (
              <Pipeline onOpen={setOpenId} onOggi={() => setTab('oggi')} onCalendario={() => setTab('calendario')} onTutti={() => setTab('prospect')} />
            ) : tab === 'calendario' ? (
              <Calendario onOpen={setOpenId} />
            ) : tab === 'analytics' ? (
              <Analytics onOpen={setOpenId} />
            ) : tab === 'vault' ? (
              <Vault onOpen={setOpenId} />
            ) : tab === 'plugin' ? (
              <Plugin />
            ) : tab === 'progetti' ? (
              <Progetti onOpen={setOpenId} />
            ) : tab === 'tutti' ? (
              <TuttiElenco onOpen={setOpenId} />
            ) : tab === 'impostazioni' ? (
              <Impostazioni nome={utente} email={mail} demo={demo} onCambio={() => setVersione((v) => v + 1)} />
            ) : (
              <Lista onOpen={setOpenId} q={q} />
            )}
          </div>
        </main>
      </div>

      {/* navigazione mobile */}
      <nav className="fixed inset-x-0 bottom-0 border-t border-bordo bg-white pb-[env(safe-area-inset-bottom)] lg:hidden">
        <div className="flex">
          {voci.map(({ chiave: t, nome: label, icona }) => (
            <button
              key={t}
              onClick={() => { setTab(t); setOpenId(null) }}
              className={`flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px] font-semibold ${
                tab === t ? 'text-navy' : 'text-spento'
              }`}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
                   strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
                <path d={icona} />
              </svg>
              {label}
            </button>
          ))}
        </div>
      </nav>

      {openId && <Scheda key={openId} id={openId} onClose={chiudiScheda} />}

      {/* Clara è dappertutto, anche sopra la scheda */}
      <ClaraVolante onOpen={(id) => setOpenId(id)} />
    </div>
  )
}
