import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase, configured, demo } from './lib/supabase'
import { scarica as scaricaPreferenze, leggi as leggiPref, scrivi as scriviPref } from './lib/preferenze'
import Login from './components/Login'
import Oggi from './components/Oggi'
import Radar from './components/Radar'
import Aziende from './components/Aziende'
import ClaraVolante from './components/ClaraVolante'
import ClaraLogo from './components/ClaraLogo'
import Vault from './components/Vault'
import Plugin from './components/Plugin'
import Calendario from './components/Calendario'
import { oggi as giornoOggi } from './lib/regole'
import Impostazioni from './components/Impostazioni'
import Clienti from './components/Clienti'
// dopo un aggiornamento il pezzo vecchio non esiste piu': si ricarica una volta
// sola invece di lasciare lo schermo bianco (QA backend, 14/9)
function pezzo<T>(carica: () => Promise<T>) {
  return () => carica().catch((e) => {
    if (!sessionStorage.getItem('ricaricato')) { sessionStorage.setItem('ricaricato', '1'); location.reload() }
    throw e
  }) as Promise<T>
}
const Preventivi = lazy(pezzo(() => import('./components/Preventivi')))
import { menuDi, mioRuolo, widgetDi, type Chiave, type Ruolo } from './lib/widget'
import { chiSono, vediCome, type ChiSono, type Persona } from './lib/accessi'
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
// la coda la legge solo chi vende (Dre): agli altri il saluto e basta
const SALUTI_MATTINA: Array<[string, string]> = [
  ['Buongiorno, {nome}.', ''],
  ['Buongiorno, {nome}.', 'Si apre il sipario.'],
  ['Buongiorno, {nome}.', 'I lead non si chiudono da soli.'],
  ['Buongiorno, {nome}.', 'Oggi si spedisce.'],
  ['Buongiorno, {nome}.', 'Prima il caffè, poi la coda.'],
  ['Buongiorno, {nome}.', 'Telescopio sui lead.'],
  ['Buongiorno, capitano.', ''],
  ['Buongiorno, {nome}.', 'Un lead alla volta.'],
]
const SALUTI_POMERIGGIO: Array<[string, string]> = [
  ['Buon pomeriggio, {nome}.', ''],
  ['Buon pomeriggio, {nome}.', 'Orario buono per le call.'],
  ['Pomeriggio, {nome}.', 'Ancora un paio di carte da muovere.'],
  ['Buon pomeriggio, {nome}.', 'Secondo tempo.'],
  ['Buon pomeriggio, {nome}.', 'La pipeline non guarda l\'orologio.'],
]
const SALUTI_SERA: Array<[string, string]> = [
  ['Buonasera, {nome}.', ''],
  ['Buonasera, {nome}.', 'Ultima occhiata e si chiude.'],
  ['Buonasera, {nome}.', 'I lead dormono. Tu quasi.'],
  ['Sera, {nome}.', 'Domani si rilancia.'],
]

function saluto(nome: string): [string, string] {
  const ora = new Date()
  const giorno = Math.floor((ora.getTime() - new Date(ora.getFullYear(), 0, 0).getTime()) / 86400e3)
  const h = ora.getHours()
  const pool = h < 13 ? SALUTI_MATTINA : h < 18 ? SALUTI_POMERIGGIO : SALUTI_SERA
  const [apertura, coda] = pool[giorno % pool.length]
  return [apertura.replace('{nome}', nome.split(' ')[0] || 'ciao'), coda]
}

// l'icona di una voce: il tratto SVG, oppure un'immagine di public/ usata come
// maschera cosi' prende il colore del testo (il marchio SG per i Documenti)
function Icona({ icona, immagine, className }: { icona: string; immagine?: string; className: string }) {
  if (immagine) {
    const url = `url(${import.meta.env.BASE_URL}${immagine})`
    return <span aria-hidden className={className} style={{ backgroundColor: 'currentColor', WebkitMaskImage: url, maskImage: url, WebkitMaskSize: 'contain', maskSize: 'contain', WebkitMaskRepeat: 'no-repeat', maskRepeat: 'no-repeat', WebkitMaskPosition: 'center', maskPosition: 'center' }} />
  }
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d={icona} />
    </svg>
  )
}

export default function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [ready, setReady] = useState(false)
  const [tab, setTab] = useState<Tab>('pipeline')
  const [openId, setOpenId] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const [cercaAperta, setCercaAperta] = useState(false)
  // il puntino sul menu Task: quante task ti hanno mandato e aspettano che
  // tu le accetti. Ogni minuto, e quando cambi pagina. Niente rumore in piu'.
  const [inArrivo, setInArrivo] = useState(0)
  // schermo intero (Dre, 14/9): via menu, testata e Clara fissa, resta solo la pagina. Esc per uscire
  const [pieno, setPieno] = useState(false)
  useEffect(() => {
    if (!pieno) return
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setPieno(false) }
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [pieno])
  const [daDecidere, setDaDecidere] = useState(0)     // le proposte aperte: il badge della Posta di Clara
  useEffect(() => {
    if (demo) return
    const conta = () => { void supabase.from('proposte').select('id', { count: 'exact', head: true }).eq('stato', 'aperta').then(({ count }) => setDaDecidere(count ?? 0)) }
    conta()
    const t = setInterval(conta, 60_000)
    const vai = () => { setTab('clara'); setOpenId(null) }
    window.addEventListener('clara:vai-posta', vai)
    // «+ Nuovo preventivo» dalla scheda: si va al widget, che apre il pannello con l'azienda scelta
    const nuovoPrev = () => { setTab('preventivi'); setOpenId(null) }
    window.addEventListener('preventivo:nuovo', nuovoPrev)
    window.addEventListener('clara:apri-posta', vai)
    return () => { clearInterval(t); window.removeEventListener('clara:vai-posta', vai); window.removeEventListener('clara:apri-posta', vai); window.removeEventListener('preventivo:nuovo', nuovoPrev) }
  }, [])
  useEffect(() => {
    let vivo = true
    async function conta() {
      const { data } = await supabase.auth.getSession()
      const io = data.session?.user?.id
      if (!io) return
      const { count } = await supabase.from('task').select('id', { count: 'exact', head: true })
        .eq('owner', io).eq('stato', 'proposta').eq('fatta', false)
      if (vivo) setInArrivo(count ?? 0)
    }
    void conta()
    const t = setInterval(conta, 60_000)
    return () => { vivo = false; clearInterval(t) }
  }, [tab])
  // alla chiusura della scheda le viste si ricaricano: la bacheca non deve
  // mai mentire su una fase appena cambiata
  const [versione, setVersione] = useState(0)
  const [ruoloDb, setRuoloDb] = useState<Ruolo>('coordinamento')     // il ruolo vero, dal database (profili)
  const [concessi, setConcessi] = useState<Set<Chiave>>(new Set())      // i widget a richiesta che ho
  const [vista, setVista] = useState<ChiSono['vista']>(null)           // un ceo nei panni di qualcun altro
  const [pod, setPod] = useState<Persona[]>([])
  const [ruoloVero, setRuoloVero] = useState('coordinamento')                           // le persone del mio pod, se sono manager
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
        { setCercaAperta(true); setTimeout(() => cercaRef.current?.focus(), 30) }
      }
    }
    window.addEventListener('keydown', giu)
    return () => window.removeEventListener('keydown', giu)
  }, [])

  useEffect(() => {
    if (!session || demo) return
    void chiSono().then((c) => { setRuoloDb(c.ruolo); setRuoloVero(c.ruoloVero); setConcessi(new Set(c.concessi)); setVista(c.vista); setPod(c.pod) })
  }, [session, versione])

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
  const titolo = widgetDi(tab)?.nome ?? (tab === 'impostazioni' ? 'Impostazioni' : tab === 'oggi' ? 'Oggi' : tab === 'tutti' ? 'Pipeline' : tab === 'analytics' ? 'Numeri' : tab === 'plugin' ? 'Widget e istruzioni' : '')
  const ruolo: Ruolo = demo ? mioRuolo() : ruoloDb
  const voci = menuDi(ruolo, 'menu', concessi)
  const vociSistema = menuDi(ruolo, 'sistema', concessi)

  return (
    <div className="min-h-dvh bg-fondo lg:flex">
      {vista && (
        <div className="fixed inset-x-0 top-0 z-[70] flex items-center justify-center gap-3 bg-amber-100 px-4 py-1.5 text-xs font-semibold text-amber-900">
          Stai vedendo il Workspace come {vista.nome ?? 'un\'altra persona'}: menu, aziende e chat sono i suoi.
          <button onClick={() => { void vediCome(null).then(() => window.location.reload()) }} className="rounded-full bg-amber-900 px-3 py-0.5 text-white">Torna a te</button>
        </div>
      )}

      {/* ── sidebar (solo desktop) ─────────────────────────────── */}
      <aside
        style={{ width: menuLargo }}
        className={`sticky top-0 hidden h-dvh shrink-0 flex-col border-r border-bordo bg-white px-4 py-5 ${pieno ? '' : 'lg:flex'}`}
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
          <span className="text-[17px] leading-tight tracking-tight text-navy">
            <span className="font-black">SG</span>
            <span className="ml-1.5 font-bold">Workspace</span>
          </span>
        </div>

        <p className="mb-2 px-2 text-[11px] font-bold uppercase tracking-[0.08em] text-spento">
          Menu
        </p>
        <nav className="space-y-1">
          {voci.map(({ chiave: t, nome: label, icona, immagine }) => {
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
                <Icona icona={icona} immagine={immagine} className={`h-[18px] w-[18px] ${attivo ? 'text-navy' : ''}`} />
                {label}
                {t === 'pipeline' && inArrivo > 0 && (
                  <span className="ml-auto rounded-full bg-blu px-1.5 py-px text-[10px] font-bold text-white" title="Task in arrivo da accettare">{inArrivo}</span>
                )}
                {t === 'clara' && daDecidere > 0 && (
                  <span className="ml-auto rounded-full bg-red-600 px-1.5 py-px text-[10px] font-bold text-white" title="Cose da decidere">{daDecidere}</span>
                )}
              </button>
            )
          })}
        </nav>

        <p className="mb-2 mt-7 px-2 text-[11px] font-bold uppercase tracking-[0.08em] text-spento">
          Sistema
        </p>
        <nav className="space-y-1">
          {vociSistema.map(({ chiave: t, nome: label, icona, immagine }) => {
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
                <Icona icona={icona} immagine={immagine} className={`h-[18px] w-[18px] ${attivo ? 'text-navy' : ''}`} />
                {label}
                {t === 'clara' && daDecidere > 0 && (
                  <span className="ml-auto rounded-full bg-red-600 px-1.5 py-px text-[10px] font-bold text-white" title="Cose da decidere">{daDecidere}</span>
                )}
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
            <img src={`${import.meta.env.BASE_URL}sg-simbolo.svg`} alt="Studio Galilei" className="h-8 w-8 shrink-0 object-contain" />
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
          {/* la Posta, i Documenti e le Impostazioni: dal telefono si
              raggiungevano solo dalla pallina, e una volta li' nessuna icona
              era accesa (QA Dre, 14/9) */}
          {vociSistema.filter((w) => w.chiave !== 'analytics').map(({ chiave: t, nome, icona, immagine }) => (
            <button key={t} onClick={() => { setTab(t); setOpenId(null) }} aria-label={nome} title={nome}
                    className={`relative shrink-0 rounded-full p-1.5 ${tab === t ? 'bg-velo text-navy' : 'text-tenue'}`}>
              <Icona icona={icona} immagine={immagine} className="h-5 w-5" />
              {t === 'clara' && daDecidere > 0 && (
                <span className="absolute -right-0.5 -top-0.5 min-w-[16px] rounded-full bg-red-600 px-1 text-[9px] font-bold leading-4 text-white">{daDecidere}</span>
              )}
            </button>
          ))}
          <button onClick={() => { setTab('impostazioni'); setOpenId(null) }} aria-label="Impostazioni" title="Impostazioni"
                  className={`shrink-0 rounded-full p-1.5 ${tab === 'impostazioni' ? 'bg-velo text-navy' : 'text-tenue'}`}>
            <Icona icona="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1.08-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6h.09A1.65 1.65 0 0 0 10 3.09V3a2 2 0 1 1 4 0v.09A1.65 1.65 0 0 0 15 4.6a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9v.09a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" className="h-5 w-5" />
          </button>
        </header>

        <main className={`${pieno ? 'px-4 py-4' : 'px-4 py-5 lg:px-8 lg:py-7'} ${tab === 'impostazioni' ? 'mx-auto max-w-4xl' : ''}`}>
          {!pieno && (<>
          {/* testata */}
          <div className="mb-5 flex flex-wrap items-center gap-4">
            <div className="min-w-0 flex-1">
              {/* briciole (intervista 9/9): da dove vengo e come torno, sempre in alto */}
              {(tab === 'analytics' || tab === 'plugin') && (
                <button onClick={() => setTab('impostazioni')} className="mb-1 text-sm font-semibold text-blu hover:underline">‹ Impostazioni</button>
              )}
              <h1 className="flex items-center gap-2 text-[24px] font-extrabold tracking-tight lg:text-[28px]">
                {tab === 'pipeline' && <span className="text-navy"><ClaraLogo size={26} /></span>}
                {tab === 'vault' && <Icona icona="" immagine="sg-intreccio.svg" className="h-8 w-8 shrink-0 text-navy" />}
                {tab === 'pipeline' ? saluto(utente)[0] : titolo}
              </h1>
              {tab === 'pipeline' && (salutoClara ? (
                <p className="mt-2 max-w-xl text-[15px] leading-relaxed text-tenue">
                  {salutoClara.replace(/^buon\w*[,.]?\s+dre[.,]?\s*/i, '')}
                </p>
              ) : ruolo === 'ceo' && saluto(utente)[1] ? (
                <p className="mt-2 max-w-xl text-[15px] leading-relaxed text-tenue">{saluto(utente)[1]}</p>
              ) : null)}
            </div>
            {tab === 'pipeline' && (
              <div className="hidden w-[440px] shrink-0 lg:block">
                <Radar onOpen={setOpenId} onCalendario={() => setTab('calendario')} parte="call" />
              </div>
            )}
            {/* schermo intero (Dre, 14/9): sparisce tutto intorno e resta la pagina */}
            <button onClick={() => setPieno(true)} aria-label="Schermo intero" title="Schermo intero (Esc per uscire)"
                    className="hidden h-10 w-10 items-center justify-center rounded-full border border-bordo bg-white text-tenue hover:border-navy hover:text-navy lg:flex">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-[18px] w-[18px]"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" /></svg>
            </button>
            {/* la ricerca: una lente, si apre quando serve o con ⌘K (Dre, 9/9) */}
            <div className="relative hidden lg:block">
              {cercaAperta || q ? (
                <input
                  ref={cercaRef}
                  autoFocus
                  type="search"
                  placeholder="Cerca…"
                  value={q}
                  onChange={(e) => {
                    setQ(e.target.value)
                    if (e.target.value.trim()) { setTab('prospect'); setOpenId(null) }
                  }}
                  onBlur={() => { if (!q) setCercaAperta(false) }}
                  onKeyDown={(e) => { if (e.key === 'Escape') { setQ(''); setCercaAperta(false) } }}
                  className="w-64 rounded-full border border-blu bg-white px-4 py-2 text-sm outline-none"
                />
              ) : (
                <button onClick={() => setCercaAperta(true)} aria-label="Cerca (⌘K)" title="Cerca  ⌘K"
                        className="flex h-10 w-10 items-center justify-center rounded-full border border-bordo bg-white text-tenue hover:border-navy hover:text-navy">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="h-[18px] w-[18px]"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
                </button>
              )}
            </div>
          </div>

          </>)}
          {pieno && (
            <button onClick={() => setPieno(false)} title="Esci dallo schermo intero (Esc)"
                    className="fixed right-4 top-3 z-50 flex items-center gap-1.5 rounded-full border border-bordo bg-white px-3 py-1.5 text-xs font-bold text-tenue shadow-[0_4px_14px_rgba(16,24,40,0.12)] hover:border-navy hover:text-navy">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5"><path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5" /></svg>
              {titolo}: esci
            </button>
          )}
          {/* in schermo intero la testata non c'e': la prossima call resta
              comunque, e' l'unica cosa che non si puo' perdere (QA Dre, 14/9) */}
          {pieno && tab === 'pipeline' && (
            <div className="mb-4 hidden lg:block">
              <Radar onOpen={setOpenId} onCalendario={() => setTab('calendario')} parte="call" />
            </div>
          )}
          <div key={versione}>
            {tab === 'oggi' || tab === 'pipeline' ? (
              <Oggi onOpen={setOpenId} onCalendario={() => setTab('calendario')} />
            ) : tab === 'calendario' ? (
              <Calendario onOpen={setOpenId} pod={pod} />
            ) : tab === 'analytics' ? (
              <Analytics onOpen={setOpenId} />
            ) : tab === 'vault' ? (
              <Vault onOpen={setOpenId} />
            ) : tab === 'plugin' ? (
              <Plugin />
            ) : tab === 'progetti' ? (
              <Clienti onOpen={setOpenId} />
            ) : tab === 'preventivi' ? (
              <Suspense fallback={null}><Preventivi onOpen={setOpenId} /></Suspense>
            ) : tab === 'clara' ? (
              <ClaraVolante modo="posta" onOpen={setOpenId} />
            ) : tab === 'impostazioni' ? (
              <Impostazioni nome={utente} email={mail} demo={demo} ruolo={ruolo} ruoloVero={ruoloVero} onCambio={() => setVersione((v) => v + 1)}
                            onNumeri={() => setTab('analytics')} onWidget={() => setTab('plugin')} />
            ) : (
              <Aziende onOpen={setOpenId} q={q} />
            )}
          </div>
        </main>
      </div>

      {/* navigazione mobile */}
      <nav className={`fixed inset-x-0 bottom-0 border-t border-bordo bg-white pb-[env(safe-area-inset-bottom)] lg:hidden ${pieno ? 'hidden' : ''}`}>
        <div className="flex">
          {voci.map(({ chiave: t, nome: label, icona, immagine }) => (
            <button
              key={t}
              onClick={() => { setTab(t); setOpenId(null) }}
              className={`flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px] font-semibold ${
                tab === t ? 'text-navy' : 'text-spento'
              }`}
            >
              <Icona icona={icona} immagine={immagine} className="h-5 w-5" />
              {label}
            </button>
          ))}
        </div>
      </nav>

      {openId && <Scheda key={openId} id={openId} onClose={chiudiScheda} />}

      {/* Clara: colonna fissa a destra sul desktop, pannello sul telefono */}
      <ClaraVolante onOpen={(id) => setOpenId(id)} compatta={pieno} />
    </div>
  )
}
