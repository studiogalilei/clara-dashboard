import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase, configured, demo } from './lib/supabase'
import { scarica as scaricaPreferenze, leggi as leggiPref, scrivi as scriviPref } from './lib/preferenze'
import { useVivo } from './lib/vivo'
import Login from './components/Login'
import Oggi from './components/Oggi'
import SalaControllo from './components/SalaControllo'
import Radar from './components/Radar'
import Rete from './components/Rete'
import Aziende from './components/Aziende'
import ClaraVolante from './components/ClaraVolante'
import SeguitiInArrivo from './components/SeguitiInArrivo'
import ClaraLogo from './components/ClaraLogo'
import Aiuto from './components/Aiuto'
import Vault from './components/Vault'
import Plugin from './components/Plugin'
import Feedback from './components/Feedback'
import Aggiornato from './components/Aggiornato'
import Novita from './components/Novita'
import Giro from './components/Giro'
import Calendario from './components/Calendario'
import CalendarioClara from './components/CalendarioClara'
import Impostazioni from './components/Impostazioni'
import Clienti from './components/Clienti'
import Chat from './components/Chat'
// dopo un aggiornamento il pezzo vecchio non esiste piu': si ricarica una volta
// sola invece di lasciare lo schermo bianco (QA backend, 14/9)
// Il segno restava scritto per sempre: dopo il primo aggiornamento della
// giornata, il secondo lasciava la pagina inceppata (QA browser, 15/9).
// Adesso vale un minuto: una ricarica sola per volta, e se il pezzo manca
// davvero se ne accorge la rete e lo dice.
function pezzo<T>(carica: () => Promise<T>) {
  return () => carica().catch((e) => {
    const ultima = Number(sessionStorage.getItem('ricaricato') ?? 0)
    if (Date.now() - ultima > 60_000) {
      sessionStorage.setItem('ricaricato', String(Date.now()))
      location.reload()
    }
    throw e
  }) as Promise<T>
}
const Preventivi = lazy(pezzo(() => import('./components/Preventivi')))
import { menuDi, mioRuolo, widgetDi, type Chiave, type Ruolo } from './lib/widget'
import Suggerimento from './components/Suggerimento'
import Apertura from './components/Apertura'
import Comandi, { type Comando } from './components/Comandi'
import { leggiIndirizzo, scriviIndirizzo, linkDi } from './lib/indirizzo'
import { ricordaReparto, repartoRicordato } from './lib/reparto'
import { chiSono, vediCome, type ChiSono, type Persona } from './lib/accessi'
import { avviaUtilizzo } from './lib/utilizzo'
import { nomeDa, iniziali } from './lib/profilo'
import Analytics from './components/Analytics'
import Scheda from './components/Scheda'
import { useSchermoLargo } from './lib/schermo'
import Metro from './components/Metro'
import BachecaAziende from './components/aziende/Aziende'
import Trattativa from './components/Trattativa'

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
    return <span aria-hidden className={`inline-block ${className}`} style={{ backgroundColor: 'currentColor', WebkitMaskImage: url, maskImage: url, WebkitMaskSize: 'contain', maskSize: 'contain', WebkitMaskRepeat: 'no-repeat', maskRepeat: 'no-repeat', WebkitMaskPosition: 'center', maskPosition: 'center' }} />
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
  // 26/9: l'indirizzo comanda dal primo disegno. Se il link dice #/preventivi
  // si apre lì, senza lampeggiare prima sulla Pipeline.
  const dIniziale = leggiIndirizzo()
  // 29/9: l'indirizzo con cui si e' entrati, letto UNA volta. Al primo disegno
  // l'app scrive #/pipeline, e da li' in poi «c'e' gia' un indirizzo» era sempre
  // vero: Carlo, Alex e Salvatore non arrivavano mai su Oggi (studio d'uso di Alex).
  const entrataSenzaIndirizzo = useRef(dIniziale === null)
  const largo = useSchermoLargo()
  const [tab, setTab] = useState<Tab>(dIniziale?.tab ?? 'pipeline')   // 7/10 (Dre): senza indirizzo si entra sulla sala di controllo
  const [openId, setOpenId] = useState<string | null>(dIniziale?.id ?? null)
  const [sezione, setSezione] = useState<string | null>(dIniziale?.sezione ?? null)
  // GLI INDIRIZZI (Dre, 26/9): quello che guardi ha un indirizzo suo, lo copi e
  // lo mandi. All'avvio si legge, poi si scrive a ogni passo, e Indietro torna.
  // Valgono ancora i vecchi link di Clara in calendario (?scheda=<id>).
  useEffect(() => {
    function dallUrl() {
      const d = leggiIndirizzo()
      if (!d) return
      setTab(d.tab); setOpenId(d.id); setSezione(d.sezione)
    }
    window.addEventListener('popstate', dallUrl)
    return () => window.removeEventListener('popstate', dallUrl)
  }, [])
  // L'UTILIZZO (Dre, 7/10): un minuto contato per ogni minuto di lavoro vero, per persona e
  // per schermata. Invisibile; lo legge solo Dre in Impostazioni (schema_v77)
  const doveSono = useRef<string>('')
  doveSono.current = openId ? 'scheda' : tab
  useEffect(() => avviaUtilizzo(() => doveSono.current, demo), [])
  const primoGiro = useRef(true)
  useEffect(() => {
    scriviIndirizzo({ tab, id: openId, sezione }, primoGiro.current)
    primoGiro.current = false
  }, [tab, openId, sezione])
  const [q, setQ] = useState('')
  const [cercaAperta, setCercaAperta] = useState(false)
  // il puntino sul menu Task: quante task ti hanno mandato e aspettano che
  // tu le accetti. Ogni minuto, e quando cambi pagina. Niente rumore in piu'.
  const [inArrivo, setInArrivo] = useState(0)
  // IL BATTITO (Dre, 16/9): quando una riga cambia nel database, i numeri
  // sul menu si rifanno subito. Prima ci mettevano fino a un minuto
  const [battito, setBattito] = useState(0)
  useVivo(['proposte', 'chat', 'task'], () => setBattito((n) => n + 1))
  // schermo intero (Dre, 14/9): via menu, testata e Clara fissa, resta solo la pagina. Esc per uscire
  const [pieno, setPieno] = useState(false)
  useEffect(() => {
    if (!pieno) return
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape' && !document.body.dataset.sopra) setPieno(false) }
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [pieno])
  // IL GIRO GUIDATO (Dre, 16/9): la prima volta parte da solo, dopo si
  // rifa' da Impostazioni. Che l'hai fatto e' una preferenza vera: ti segue
  // anche sul telefono, e non ti ricapita addosso
  const [giro, setGiro] = useState(false)
  // si decide solo dopo che le preferenze sono scese dal database: se no
  // a chi entra da un telefono nuovo il giro ricapita addosso
  const [prefPronte, setPrefPronte] = useState(false)
  useEffect(() => {
    const rifai = () => setGiro(true)
    window.addEventListener('giro:rifai', rifai)
    return () => window.removeEventListener('giro:rifai', rifai)
  }, [])
  useEffect(() => {
    if (!prefPronte) return
    const t = setTimeout(() => { if (!leggiPref('giro-fatto')) setGiro(true) }, 900)
    return () => clearTimeout(t)
  }, [prefPronte])

  // IL RIPOSO (Dre, 15/9): «quando sono nella stessa tab da un po', si
  // allarga lo schermo, sparisce la parte a lato e il logo di Clara; poi
  // passo il mouse dove stavano e riappaiono». Non e' lo schermo intero, che
  // e' una decisione: questo succede da solo mentre lavori, e si disfa da
  // solo appena ti serve qualcosa. Solo su desktop, e mai mentre scrivi.
  const [riposo, setRiposo] = useState(false)
  const [sbircio, setSbircio] = useState(false)
  useEffect(() => {
    setRiposo(false)
    // durante il giro guidato niente si muove: le cose che illumina devono
    // restare dove sono
    if (pieno || giro) return
    if (typeof window === 'undefined' || !window.matchMedia('(min-width: 1024px)').matches) return
    let t = 0
    const riparti = () => {
      window.clearTimeout(t)
      setRiposo(false)
      t = window.setTimeout(() => {
        // se stai scrivendo, non ti si muove niente sotto le mani
        const dentro = document.activeElement?.tagName
        if (dentro === 'INPUT' || dentro === 'TEXTAREA') { riparti(); return }
        setRiposo(true)
      }, 75000)
    }
    riparti()
    // 5/10: anche il mouse, lo scroll e il tocco svegliano lo schermo (prima solo la tastiera:
    // chi lavorava col mouse si vedeva attenuare il menu mentre lo usava)
    const eventi = ['keydown', 'pointerdown', 'pointermove', 'wheel', 'touchstart'] as const
    let ultimo = 0
    const sveglia = () => { const ora = Date.now(); if (ora - ultimo > 1000) { ultimo = ora; riparti() } }
    eventi.forEach((e) => window.addEventListener(e, sveglia, { passive: true }))
    return () => { window.clearTimeout(t); eventi.forEach((e) => window.removeEventListener(e, sveglia)) }
  }, [tab, pieno, giro])

  const [daDecidere, setDaDecidere] = useState(0)     // le proposte aperte: il badge della Posta di Clara
  const [daLeggere, setDaLeggere] = useState(0)       // i messaggi della squadra non letti
  useEffect(() => {
    if (demo) return
    const conta = () => {
      void supabase.from('proposte').select('id', { count: 'exact', head: true }).eq('stato', 'aperta').then(({ count }) => setDaDecidere(count ?? 0))
      // i messaggi che ti hanno mandato e non hai ancora aperto
      void supabase.auth.getSession().then(({ data }) => {
        const io = data.session?.user?.id
        if (!io) return
        void supabase.from('chat').select('id', { count: 'exact', head: true })
          .eq('a', io).eq('letto', false)
          .then(({ count }) => setDaLeggere(count ?? 0))
      })
    }
    conta()
    const t = setInterval(conta, 60_000)
    return () => clearInterval(t)
  }, [battito])
  // gli avvisi dalle altre schermate: si attaccano una volta, non a ogni battito
  useEffect(() => {
    const vai = () => { setTab('clara'); setOpenId(null) }
    window.addEventListener('clara:vai-posta', vai)
    // «+ Nuovo preventivo» dalla scheda: si va al widget, che apre il pannello con l'azienda scelta
    const nuovoPrev = () => { setTab('preventivi'); setOpenId(null) }
    window.addEventListener('preventivo:nuovo', nuovoPrev)
    window.addEventListener('clara:apri-posta', vai)
    return () => { window.removeEventListener('clara:vai-posta', vai); window.removeEventListener('clara:apri-posta', vai); window.removeEventListener('preventivo:nuovo', nuovoPrev) }
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
  }, [tab, battito])
  // alla chiusura della scheda le viste si ricaricano: la bacheca non deve
  // mai mentire su una fase appena cambiata
  const [versione, setVersione] = useState(0)
  const [ruoloDb, setRuoloDb] = useState<Ruolo>('coordinamento')     // il ruolo vero, dal database (profili)
  const [rep, setRep] = useState(repartoRicordato())                 // il reparto: il colore di tutto (schema_v60)
  const [concessi, setConcessi] = useState<Set<Chiave>>(new Set())      // i widget a richiesta che ho
  const [vista, setVista] = useState<ChiSono['vista']>(null)           // un ceo nei panni di qualcun altro
  const [pod, setPod] = useState<Persona[]>([])
  const [ruoloVero, setRuoloVero] = useState('coordinamento')                           // le persone del mio pod, se sono manager
  // il menu si allarga e si stringe trascinando il filo, come su Claude
  // (Dre, 4/9). La larghezza e' una preferenza: ti segue sul telefono
  const [menuLargo, setMenuLargo] = useState(() => Number(leggiPref('menu-larghezza')) || 224)
  const tiroMenu = useRef(false)
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
      setPrefPronte(true)
      return
    }
    supabase.auth.getSession().then(async ({ data }) => {
      setSession(data.session)
      // quello che hai scelto da un altro dispositivo vince su questo
      // browser: le preferenze seguono te, non la macchina (revisione 4/9)
      if (data.session && await scaricaPreferenze()) setVersione((v) => v + 1)
      setReady(true)
      setPrefPronte(true)
    })
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s))
    return () => sub?.subscription.unsubscribe()
  }, [])

  // gold (6/10): il saluto del mattino non si legge piu': la frase di Clara e' quella dal vivo in Adesso

  // LE SCORCIATOIE (Dre, 26/9: «il feel di un software professionale»).
  // ⌘K apre la palette; «/» fa lo stesso, per chi la conosce da prima.
  // G e poi una lettera salta a una sezione: o=Oggi, p=Pipeline, c=Clienti,
  // k=Calendario, m=posta (Clara), v=preventivi. «?» mostra l'elenco.
  const [comandi, setComandi] = useState(false)
  // l'esito di un comando, in una pillola che sparisce da sola (5/10: prima i comandi non dicevano niente)
  const [esito, setEsito] = useState<{ testo: string; male: boolean } | null>(null)
  useEffect(() => { if (!esito) return; const t = window.setTimeout(() => setEsito(null), 3500); return () => window.clearTimeout(t) }, [esito])
  const [scorciatoie, setScorciatoie] = useState(false)
  useEffect(() => {
    let g = false
    let quando = 0
    const SALTI: Record<string, Chiave> = { o: 'pipeline', p: 'prospect', c: 'progetti', k: 'calendario', m: 'clara', v: 'preventivi', d: 'vault' }
    function giu(e: KeyboardEvent) {
      const dentroUnCampo = ['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement)?.tagName)
        || (e.target as HTMLElement)?.isContentEditable
      if (((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') || (e.key === '/' && !dentroUnCampo)) {
        e.preventDefault(); setComandi(true); return
      }
      if (dentroUnCampo || e.metaKey || e.ctrlKey || e.altKey) return
      if (e.key === 'Escape') { setScorciatoie(false); return }
      if (e.key === '?') { e.preventDefault(); setScorciatoie((s) => !s); return }
      if (document.body.dataset.sopra) return   // con un pannello aperto i salti non sparano
      if (e.key.toLowerCase() === 'g') { g = true; quando = Date.now(); return }
      if (g && Date.now() - quando < 1200) {
        const t = SALTI[e.key.toLowerCase()]
        g = false
        if (t) { e.preventDefault(); setTab(t); setOpenId(null); setScorciatoie(false) }
      } else g = false
    }
    window.addEventListener('keydown', giu)
    return () => window.removeEventListener('keydown', giu)
  }, [])

  useEffect(() => {
    if (!session || demo) return
    void chiSono().then((c) => {
      setRuoloDb(c.ruolo); setRuoloVero(c.ruoloVero); setConcessi(new Set(c.concessi)); setVista(c.vista); setPod(c.pod)
      // il reparto veste l'app: icona in home, barra di stato, e l'apertura del prossimo ingresso (Dre, 26/9)
      ricordaReparto(c.reparto); setRep(repartoRicordato())
      // LA PRIMA PAGINA DI CHI CONSEGNA (Dre, 24/9): «fai cominciare dalle cose
      // actionable, non da una home generica». Il ceo entra sulla Pipeline;
      // gli altri su Oggi: le task da accettare, le proprie, la prossima call.
      // Se si arriva con ?scheda= si va dritti alla scheda, per tutti.
      // 26/9: se l'indirizzo dice gia' dove andare (link condiviso, ricarica,
      // tasto indietro) comanda lui. La pagina d'ingresso vale solo quando si
      // entra senza indirizzo: se no un link mandato a Carlo lo porta altrove.
      // 5/10: una volta sola. L'effetto riparte a ogni «versione» (chiusura della scheda,
      // preferenze), e senza spegnere il segnale riportava gli altri su Oggi ogni volta.
      if (c.ruolo !== 'ceo' && entrataSenzaIndirizzo.current) setTab('pipeline')
      entrataSenzaIndirizzo.current = false
    })
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
  // LA BARRA DEL TELEFONO (gold, 6/10): Oggi e la Posta per prime, perche' sono le due cose
  // che si fanno col pollice; poi le prime voci del menu di ognuno. Quello che non ci sta sale
  // fra le icone in alto, dove prima stava la Posta: nessuna pagina diventa irraggiungibile.
  const oggiW = widgetDi('pipeline')
  const postaW = vociSistema.find((w) => w.chiave === 'clara')
  const sotto = [
    // Oggi col sole (come nella V1): l'icona della bacheca era la stessa di Aziende
    ...(oggiW && !voci.some((w) => w.chiave === 'pipeline') ? [{ ...oggiW, immagine: undefined, icona: 'M12 3v1.5M12 19.5V21M4.6 4.6l1.1 1.1M18.3 18.3l1.1 1.1M3 12h1.5M19.5 12H21M4.6 19.4l1.1-1.1M18.3 5.7l1.1-1.1M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z' }] : []),
    ...(postaW ? [{ ...postaW, nome: 'Posta' }] : []),
    ...voci,
  ].slice(0, 5)
  const sopra = [
    ...voci.filter((w) => !sotto.some((x) => x.chiave === w.chiave)),
    ...vociSistema.filter((w) => w.chiave !== 'analytics' && w.chiave !== 'clara'),
  ]

  return (
    <div className="min-h-dvh bg-fondo lg:flex">
      <Apertura reparto={rep} />
      {/* L'ELENCO DELLE SCORCIATOIE, con «?» (Dre, 26/9) */}
      {scorciatoie && (
        <div className="fixed inset-0 z-[130] flex items-center justify-center px-4" onMouseDown={() => setScorciatoie(false)}>
          <div className="absolute inset-0 bg-inchiostro/25" />
          <div onMouseDown={(e) => e.stopPropagation()} className="carta carta-alta relative w-full max-w-[420px] p-5">
            <h2 className="mb-3 text-[15px] font-bold text-navy">Le scorciatoie</h2>
            <ul className="space-y-1.5 text-[13px]">
              {[['⌘K', 'Cerca e comanda: aziende, sezioni, azioni'], ['G poi O', 'Oggi'], ['G poi P', 'Pipeline'],
                ['G poi C', 'Clienti'], ['G poi K', 'Calendario'], ['G poi M', 'Posta di Clara'],
                ['G poi V', 'Preventivi'], ['G poi D', 'Documenti'], ['Esc', 'Chiude quello che è aperto'], ['?', 'Questo elenco']].map(([k, n]) => (
                <li key={k} className="flex items-baseline gap-3">
                  <kbd className="shrink-0 rounded border border-bordo bg-velo px-1.5 py-0.5 font-mono text-[11px] font-semibold text-tenue">{k}</kbd>
                  <span className="text-tenue">{n}</span>
                </li>
              ))}
            </ul>
            <button onClick={() => setScorciatoie(false)} className="mt-4 w-full rounded-full border border-bordo py-1.5 text-xs font-bold text-tenue hover:border-navy hover:text-navy">Chiudi</button>
          </div>
        </div>
      )}
      <Comandi
        aperto={comandi} chiudi={() => setComandi(false)} ruolo={ruolo} concessi={concessi}
        vaiA={(t) => { setTab(t); setOpenId(null) }}
        apriScheda={(id) => { setOpenId(id); setSezione(null); setTab('prospect') }}
        azioni={[
          { id: 'do:azienda', titolo: "Aggiungi un'azienda", sotto: 'una scheda nuova nella Pipeline', gruppo: 'Azioni',
            fai: () => { setTab('prospect'); setOpenId(null); window.dispatchEvent(new CustomEvent('azienda:nuova')) } },
          { id: 'do:preventivo', titolo: 'Nuovo preventivo', sotto: 'parte dal listino', gruppo: 'Azioni',
            fai: () => setTab('preventivi') },
          { id: 'do:sync', titolo: 'Sincronizza adesso', sotto: 'rilegge Smartlead, il calendario e la posta', gruppo: 'Azioni',
            fai: () => {
              setEsito({ testo: 'Sincronizzo Smartlead, calendario e posta…', male: false })
              void supabase.rpc('chiama_direttore', { forza: 'sync_smartlead' }).then(({ error }) =>
                setEsito(error ? { testo: `La sincronizzazione non è partita: ${error.message}`, male: true } : { testo: 'Sincronizzazione partita: fra un paio di minuti è tutto aggiornato.', male: false }))
            } },
          { id: 'do:link', titolo: 'Copia il link di questa pagina', sotto: 'da mandare a qualcuno', gruppo: 'Azioni',
            fai: () => { void navigator.clipboard.writeText(linkDi({ tab, id: openId, sezione })).catch(() => {}) } },
        ] as Comando[]}
      />
      <Suggerimento />
      {vista && (
        <div className="fixed inset-x-0 top-0 z-[70] flex items-center justify-center gap-3 bg-amber-100 px-4 py-1.5 text-xs font-semibold text-amber-900">
          Stai vedendo il Workspace come {vista.nome ?? 'un\'altra persona'}: menu, aziende e chat sono i suoi.
          <button onClick={() => { void vediCome(null).then(() => window.location.reload()) }} className="rounded-full bg-amber-900 px-3 py-0.5 text-white">Torna a te</button>
        </div>
      )}

      {/* ── sidebar (solo desktop) ─────────────────────────────── */}
      {/* il bordo da sfiorare per farlo riapparire: invisibile, largo un dito */}
      {riposo && !pieno && (
        <div onMouseEnter={() => setSbircio(true)}
             className="fixed inset-y-0 left-0 z-30 hidden w-4 lg:block" aria-hidden />
      )}
      <aside
        style={{ width: riposo && !sbircio ? 0 : menuLargo }}
        onMouseEnter={() => setSbircio(true)}
        onMouseLeave={() => setSbircio(false)}
        className={`sticky top-0 z-20 hidden h-dvh shrink-0 flex-col overflow-hidden border-r bg-white py-5 shadow-[var(--shadow-carta)] transition-[width,opacity,padding] duration-300 ease-out ${
          riposo && !sbircio ? 'border-transparent px-0 opacity-0' : 'border-bordo px-4 opacity-100'
        } ${pieno ? '' : 'lg:flex'}`}
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
        {/* IL MARCHIO (Dre, 16/9): il posto e' dello Studio, l'assistente e'
            Clara. Quindi qui sopra sta SG, e Clara resta la pallina */}
        {/* il marchio riporta a casa (Dre, 17/9): da qualunque schermata, Oggi */}
        <button onClick={() => { setTab('pipeline'); setOpenId(null); window.scrollTo(0, 0) }}
                title="Torna a Oggi" aria-label="Torna a Oggi"
                className="mb-8 flex items-center gap-2.5 rounded-xl px-2 text-left hover:bg-velo/60">
          <img src={`${import.meta.env.BASE_URL}sg-simbolo.svg`} alt="Studio Galilei" className="h-9 w-9 shrink-0 object-contain" />
          <span className="leading-tight tracking-tight text-navy">
            <span className="block text-[17px]">
              <span className="font-black">SG</span>
              <span className="ml-1.5 font-bold">Workspace</span>
            </span>
            {/* beta: e' in mano alla squadra da oggi, e si vede (Dre, 16/9) */}
            <span className="block text-[11px] font-bold uppercase tracking-[0.14em] text-navy/70">Beta</span>
          </span>
        </button>

        <p className="mb-2 px-2 text-[11px] font-bold uppercase tracking-[0.08em] text-navy/70">
          Menu
        </p>
        <nav className="space-y-1">
          {voci.map(({ chiave: t, nome: label, icona, immagine, cosa }) => {
            const attivo = tab === t
            return (
              <button
                key={t}
                data-giro={t}
                data-tip={cosa}
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

        <p className="mb-2 mt-7 px-2 text-[11px] font-bold uppercase tracking-[0.08em] text-navy/70">
          Sistema
        </p>
        <nav className="space-y-1">
          {vociSistema.map(({ chiave: t, nome: label, icona, immagine, cosa }) => {
            const attivo = tab === t
            return (
              <button
                key={t}
                data-giro={t}
                data-tip={cosa}
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
                {t === 'chat' && daLeggere > 0 && (
                  <span className="ml-auto rounded-full bg-blu px-1.5 py-px text-[10px] font-bold text-white" title="Messaggi da leggere">{daLeggere}</span>
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
            {/* qui sotto ci sei tu, non il marchio: le tue iniziali */}
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-navy text-[12px] font-bold text-white">
              {iniziali(utente)}
            </span>
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
          {/* sul telefono in alto a sinistra sta il marchio, come sul Mac */}
          <button onClick={() => { setTab('pipeline'); setOpenId(null); window.scrollTo(0, 0) }} aria-label="Torna a Oggi" className="shrink-0">
            <img src={`${import.meta.env.BASE_URL}sg-simbolo.svg`} alt="Studio Galilei" className="h-7 w-7 object-contain" />
          </button>
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
          {sopra.map(({ chiave: t, nome, icona, immagine }) => (
            <button key={t} onClick={() => { setTab(t); setOpenId(null) }} aria-label={nome} title={nome}
                    className={`relative shrink-0 rounded-full p-1.5 ${tab === t ? 'bg-velo text-navy' : 'text-tenue'}`}>
              <Icona icona={icona} immagine={immagine} className="h-5 w-5" />
              {t === 'clara' && daDecidere > 0 && (
                <span className="absolute -right-0.5 -top-0.5 min-w-[16px] rounded-full bg-red-600 px-1 text-[9px] font-bold leading-4 text-white">{daDecidere}</span>
              )}
              {t === 'chat' && daLeggere > 0 && (
                <span className="absolute -right-0.5 -top-0.5 min-w-[16px] rounded-full bg-blu px-1 text-[9px] font-bold leading-4 text-white">{daLeggere}</span>
              )}
            </button>
          ))}
          <button onClick={() => { setTab('impostazioni'); setOpenId(null) }} aria-label="Impostazioni" title="Impostazioni"
                  className={`shrink-0 rounded-full p-1.5 ${tab === 'impostazioni' ? 'bg-velo text-navy' : 'text-tenue'}`}>
            <Icona icona="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1.08-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6h.09A1.65 1.65 0 0 0 10 3.09V3a2 2 0 1 1 4 0v.09A1.65 1.65 0 0 0 15 4.6a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9v.09a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" className="h-5 w-5" />
          </button>
        </header>

        {/* pb-36 sul telefono: l'ultima riga non finisce sotto la barra e i bottoni che galleggiano (29/9) */}
        <main className={`${pieno ? 'px-4 py-4' : 'px-4 pb-36 pt-5 lg:px-8 lg:py-7'} ${tab === 'impostazioni' ? 'mx-auto max-w-4xl' : ''}`}>
          {!pieno && (<>
          {/* le novita', una volta, a chi rientra (Dre, 17/9) */}
          {/* le novita' solo sulla prima pagina (Dre, 25/9): su ogni pagina erano la prima cosa che vedevi, sempre */}
          {/* gold (6/10): sulla prima pagina le novita' stanno sotto Adesso, dentro Oggi: prima erano la prima cosa che vedeva l'occhio */}
          {/* gold: sulla Pipeline (prima pagina, 24/9) le novita' stanno sotto le colonne */}
          {tab === 'prospect' && !giro && leggiPref('pipeline-vista', 'trattativa') === 'classica' && <Novita />}
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
                {/* il come-si-usa della schermata (Dre 5/10: «tutorial su TUTTE le funzioni») */}
                {(tab === 'oggi' && <Aiuto di="oggi" />) || (tab === 'preventivi' && <Aiuto di="preventivi" />)
                  || (tab === 'calendario' && <Aiuto di="calendario" />) || (tab === 'analytics' && <Aiuto di="numeri" />)
                  || (tab === 'metro' && <Aiuto di="metro" />) || (tab === 'prospect' && <Aiuto di="trattativa" />) || ((tab === 'tutti' || tab === 'aziende') && <Aiuto di="aziende" />)}
              </h1>
              {/* gold (6/10): sotto il saluto non c'e' piu' la frase del mattino: la frase di Clara
                  sta in cima ad Adesso ed e' calcolata dal vivo (quella del mattino invecchiava) */}
              {/* quanto e' fresco quello che stai guardando (Dre, 15/9) */}
              {(tab === 'pipeline' || tab === 'prospect') && <Aggiornato />}
            </div>
            {tab === 'pipeline' && largo && ruolo !== 'ceo' && (
              <div className="w-[440px] shrink-0">
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
                    className="fixed left-4 top-3 z-[80] flex items-center gap-1.5 rounded-full border border-bordo bg-white px-3 py-1.5 text-xs font-bold text-tenue shadow-[0_4px_14px_rgba(16,24,40,0.12)] hover:border-navy hover:text-navy">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5"><path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5" /></svg>
              {titolo}: esci
            </button>
          )}
          {/* in schermo intero la testata non c'e': la prossima call resta
              comunque, e' l'unica cosa che non si puo' perdere (QA Dre, 14/9) */}
          {pieno && tab === 'pipeline' && largo && ruolo !== 'ceo' && (
            <div className="mb-4">
              <Radar onOpen={setOpenId} onCalendario={() => setTab('calendario')} parte="call" />
            </div>
          )}
          <div key={versione}>
            <Rete dove={tab}>
            {tab === 'oggi' || tab === 'pipeline' ? (
              ruolo === 'ceo' ? <SalaControllo onOpen={setOpenId} /> : <Oggi onOpen={setOpenId} onCalendario={() => setTab('calendario')} />
            ) : tab === 'calendario' ? (
              ruolo === 'ceo' ? <CalendarioClara onOpen={setOpenId} /> : <Calendario onOpen={setOpenId} pod={pod} />
            ) : tab === 'analytics' ? (
              <Analytics onOpen={setOpenId} />
            ) : tab === 'vault' ? (
              <Vault onOpen={setOpenId} />
            ) : tab === 'plugin' ? (
              <Plugin />
            ) : tab === 'feedback' ? (
              <Feedback />
            ) : tab === 'metro' ? (
              <Metro />
            ) : tab === 'aziende' ? (
              <BachecaAziende onScheda={setOpenId} />
            ) : tab === 'progetti' ? (
              <Clienti onOpen={setOpenId} />
            ) : tab === 'preventivi' ? (
              <Suspense fallback={null}><Preventivi onOpen={setOpenId} /></Suspense>
            ) : tab === 'chat' ? (
              <Chat onOpen={setOpenId} />
            ) : tab === 'clara' ? (
              <>
                {/* i follow-up in arrivo, giorno per giorno (Dre, 29/9) */}
                <SeguitiInArrivo onOpen={setOpenId} />
                <ClaraVolante modo="posta" onOpen={setOpenId} />
              </>
            ) : tab === 'impostazioni' ? (
              <Impostazioni nome={utente} email={mail} demo={demo} ruolo={ruolo} ruoloVero={ruoloVero} onCambio={() => setVersione((v) => v + 1)}
                            onNumeri={() => setTab('analytics')} onWidget={() => setTab('plugin')} />
            ) : tab === 'prospect' && leggiPref('pipeline-vista', 'trattativa') !== 'classica' ? (
              <>
                {/* 5/10, Dre: tre colonne, solo i si'. La vista classica resta a un click. */}
                <Trattativa onOpen={setOpenId} q={q} onTutte={() => { scriviPref('pipeline-vista', 'classica'); setVersione((v) => v + 1) }} />
                <button onClick={() => { scriviPref('pipeline-vista', 'classica'); setVersione((v) => v + 1) }}
                        className="mt-4 text-[11px] font-semibold text-tenue hover:text-navy">Vista classica</button>
                {!giro && <div className="mt-6"><Novita /></div>}
              </>
            ) : tab === 'prospect' ? (
              <>
                <Aziende onOpen={setOpenId} q={q} />
                <button onClick={() => { scriviPref('pipeline-vista', 'trattativa'); setVersione((v) => v + 1) }}
                        className="mt-4 text-[11px] font-semibold text-tenue hover:text-navy">Vista nuova, in trattativa</button>
              </>
            ) : (
              <Aziende onOpen={setOpenId} q={q} />
            )}
            </Rete>
          </div>
        </main>
      </div>

      {/* navigazione mobile */}
      <nav className={`fixed inset-x-0 bottom-0 border-t border-bordo bg-white pb-[env(safe-area-inset-bottom)] lg:hidden ${pieno ? 'hidden' : ''}`}>
        <div className="flex">
          {sotto.map(({ chiave: t, nome: label, icona, immagine }) => (
            <button
              key={t}
              onClick={() => { setTab(t); setOpenId(null); if (t === 'pipeline') window.scrollTo(0, 0) }}
              className={`relative flex min-h-[48px] flex-1 flex-col items-center gap-0.5 py-2 text-[11px] font-semibold ${
                tab === t || (t === 'pipeline' && tab === 'oggi') ? 'text-navy' : 'text-spento'
              }`}
            >
              <Icona icona={icona} immagine={immagine} className="h-5 w-5" />
              {label}
              {t === 'clara' && daDecidere > 0 && (
                <span className="absolute left-1/2 top-1 ml-1.5 min-w-[16px] rounded-full bg-red-600 px-1 text-[9px] font-bold leading-4 text-white">{daDecidere}</span>
              )}
            </button>
          ))}
        </div>
      </nav>

      {openId && <Rete dove={openId}><Scheda key={openId} id={openId} sezione={sezione} onSezione={setSezione} onClose={chiudiScheda} onApri={(id) => { setOpenId(id); setSezione(null) }} /></Rete>}

      {/* Clara: colonna fissa a destra sul desktop, pannello sul telefono */}
      {/* 5/10: dentro la rete (un suo errore non spegne tutta l'app) e non due volte con la Posta aperta */}
      {tab !== 'clara' && (
        <Rete dove="clara">
          <ClaraVolante onOpen={(id) => setOpenId(id)} compatta={pieno} attenuata={riposo} nascostaSuTelefono={tab === 'pipeline' || tab === 'oggi'} />
        </Rete>
      )}

      {esito && (
        <div role="status" className={`fixed bottom-24 left-1/2 z-[130] -translate-x-1/2 rounded-full px-4 py-2 text-[13px] font-semibold shadow-lg sm:bottom-6 ${esito.male ? 'bg-red-600 text-white' : 'bg-navy text-white'}`}>
          {esito.testo}
        </div>
      )}
      {giro && <Giro nome={utente} ruoloVero={ruoloVero} onFine={() => { setGiro(false); scriviPref('giro-fatto', 'si') }} />}
    </div>
  )
}
