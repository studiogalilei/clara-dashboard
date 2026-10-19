// LA VERSIONE SNELLA DEL WORKSPACE (15/10/2026), fino a «Clara nuova» (dicembre).
// Dre: il Workspace e' pesante e confuso per quello che fa ogni giorno con le campagne.
// Tre schermate e basta: Oggi (chi chiamare, le call, cosa decidere), Lead (chi ha risposto,
// con la scheda e le note), Campagne (come vanno). Dal 19/10 una quarta, Tutti: il foglio con
// tutti i prospect e il loro stato (Dre: «io non ho un luogo dove vedere tutti quanti»).
// Sul telefono le voci stanno in basso, sul computer a sinistra. Il Workspace completo resta a
// un tocco, in alto.
//
// Gli indirizzi: #/s/oggi, #/s/lead, #/s/lead/<id>, #/s/tutti, #/s/tutti/<id>, #/s/campagne. Un ceo che apre il Workspace
// senza indirizzo (l'icona sul telefono, il link nudo) arriva qui (src/main.tsx).
import { useEffect, useRef, useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'
import { chiSono, vediCome, type ChiSono } from '../lib/accessi'
import Login from '../components/Login'
import Oggi from './Oggi'
import Lead from './Lead'
import SchedaLead from './SchedaLead'
import Campagne from './Campagne'
import Tutti from './Tutti'
import { Icona, type NomeIcona } from './pezzi'
import { linkCompleto } from './uso'
import { AvvisoTelefono, CollegaTelefono } from './Telefono'
import { riallinea } from '../lib/notifiche'

type Voce = 'oggi' | 'lead' | 'tutti' | 'campagne'
interface Dove { voce: Voce; id: string | null }

const VOCI: Array<{ voce: Voce; nome: string; icona: NomeIcona }> = [
  { voce: 'oggi', nome: 'Oggi', icona: 'oggi' },
  { voce: 'lead', nome: 'Lead', icona: 'lead' },
  { voce: 'tutti', nome: 'Tutti', icona: 'tutti' },
  { voce: 'campagne', nome: 'Campagne', icona: 'campagne' },
]

function leggi(): Dove {
  const [, , voce, id] = window.location.hash.replace(/^#/, '').split('/')
  const v: Voce = voce === 'lead' || voce === 'tutti' || voce === 'campagne' ? voce : 'oggi'
  // la scheda si apre sotto Lead o sotto Tutti: la voce accesa in basso resta quella da cui vieni
  return { voce: v, id: (v === 'lead' || v === 'tutti') && id ? decodeURIComponent(id) : null }
}

function indirizzo(d: Dove): string {
  return `#/s/${d.voce}${d.id ? `/${encodeURIComponent(d.id)}` : ''}`
}

const GIORNO = new Intl.DateTimeFormat('it-IT', { timeZone: 'Europe/Rome', weekday: 'long', day: 'numeric', month: 'long' })

export default function Snella() {
  const [session, setSession] = useState<Session | null>(null)
  const [pronta, setPronta] = useState(false)
  const [io, setIo] = useState<ChiSono | null>(null)
  const [erroreIo, setErroreIo] = useState(false)
  const [dove, setDove] = useState<Dove>(leggi)
  const passi = useRef(0)            // quanti passi ho fatto dentro la shell: «Indietro» torna li'

  useEffect(() => {
    void supabase.auth.getSession().then(({ data }) => { setSession(data.session); setPronta(true) })
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s))
    return () => sub?.subscription.unsubscribe()
  }, [])
  const [giroIo, setGiroIo] = useState(0)
  useEffect(() => {
    if (!session) return
    setErroreIo(false)
    chiSono().then(setIo).catch(() => setErroreIo(true))
    void riallinea()                 // l'iscrizione alle notifiche di questo dispositivo, se manca, si rimette
  }, [session, giroIo])
  // aperta senza rete: appena la rete torna si riprova da soli
  useEffect(() => {
    if (!erroreIo) return
    const torna = () => setGiroIo((n) => n + 1)
    window.addEventListener('online', torna)
    return () => window.removeEventListener('online', torna)
  }, [erroreIo])
  // bianca come la pagina: la barra in alto del telefono e la finestra dell'app sul computer
  useEffect(() => {
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', '#ffffff')
  }, [])
  // chi non e' ceo (l'icona sulla Home apre qui per tutti) va dritto al Workspace completo
  const altro = Boolean(io && io.ruolo !== 'ceo' && !io.vista)
  useEffect(() => {
    if (altro) window.location.replace(window.location.pathname + window.location.search + linkCompleto('pipeline'))
  }, [altro])
  useEffect(() => {
    const cambia = () => setDove(leggi())
    window.addEventListener('hashchange', cambia)
    return () => window.removeEventListener('hashchange', cambia)
  }, [])
  useEffect(() => {
    const nome = dove.id ? 'Scheda' : VOCI.find((v) => v.voce === dove.voce)?.nome
    document.title = `${nome} · SG Workspace`
  }, [dove])

  function vai(d: Dove) {
    passi.current += 1
    window.location.hash = indirizzo(d)
  }
  function indietro() {
    if (passi.current > 0) { passi.current -= 1; window.history.back() }
    else { window.location.replace(indirizzo({ voce: dove.voce === 'tutti' ? 'tutti' : 'lead', id: null })) }
  }
  const apri = (id: string) => vai({ voce: 'lead', id })
  const apriDaTutti = (id: string) => vai({ voce: 'tutti', id })

  if (!pronta) return <div className="min-h-dvh bg-white" />
  if (!session) return <Login />
  if (erroreIo) {
    return (
      <Pagina>
        <p role="alert" className="text-[16px] text-inchiostro">Non riesco a raggiungere il Workspace: controlla la connessione. Riprovo da solo appena torna.</p>
        <button onClick={() => setGiroIo((n) => n + 1)} className="mt-3 inline-flex min-h-11 items-center rounded-full bg-blu-scuro px-5 text-[15px] font-semibold text-white">Riprova</button>
      </Pagina>
    )
  }
  if (!io) return <div className="min-h-dvh bg-white" />
  if (altro) {
    return (
      <Pagina>
        <p className="text-[16px] text-inchiostro">Ti porto al Workspace…</p>
        <a href={linkCompleto('pipeline')} className="mt-3 inline-flex min-h-11 items-center rounded-full bg-blu-scuro px-4 text-[15px] font-semibold text-white">Vai al Workspace</a>
      </Pagina>
    )
  }

  const titolo = dove.id ? null : VOCI.find((v) => v.voce === dove.voce)?.nome

  return (
    <div className="snella min-h-dvh bg-white text-inchiostro lg:flex">
      <a href="#contenuto" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-full focus:bg-white focus:px-4 focus:py-2 focus:shadow">
        Vai al contenuto
      </a>

      {/* il menu sul computer: a sinistra */}
      <nav aria-label="Sezioni" className="hidden w-[232px] shrink-0 flex-col border-r border-velo px-3 py-5 lg:sticky lg:top-0 lg:flex lg:h-dvh">
        <p className="mb-6 px-3 text-[15px] text-inchiostro"><span className="font-black">SG</span> <span className="font-semibold">Workspace</span></p>
        <ul className="space-y-1">
          {VOCI.map((v) => {
            const su = dove.voce === v.voce
            return (
              <li key={v.voce}>
                <a href={indirizzo({ voce: v.voce, id: null })} aria-current={su ? 'page' : undefined}
                   onClick={() => { passi.current += 1 }}
                   className={`flex min-h-11 items-center gap-3 rounded-full px-4 text-[15px] font-semibold ${su ? 'bg-blu-scuro/[0.08] text-blu-scuro' : 'text-inchiostro hover:bg-velo'}`}>
                  <Icona nome={v.icona} /> {v.nome}
                </a>
              </li>
            )
          })}
        </ul>
        <div className="mt-auto space-y-1">
          <CollegaTelefono tipo="piatto" className="w-full justify-start px-4 text-[14px] font-normal text-tenue hover:text-inchiostro" />
          <a href={linkCompleto('pipeline')} className="flex min-h-11 items-center gap-2 rounded-full px-4 text-[14px] text-tenue hover:bg-velo hover:text-inchiostro">
            Workspace completo <Icona nome="esterno" className="h-4 w-4" />
          </a>
        </div>
      </nav>

      <div className="min-w-0 flex-1">
        {io.vista && <Vista io={io} />}
        <main id="contenuto" className={`mx-auto w-full ${dove.voce === 'tutti' && !dove.id ? 'max-w-[1400px]' : 'max-w-[760px]'} pl-[max(1rem,env(safe-area-inset-left))] pr-[max(1rem,env(safe-area-inset-right))] pb-[calc(96px+env(safe-area-inset-bottom))] pt-[calc(12px+env(safe-area-inset-top))] lg:px-8 lg:pb-16 lg:pt-8`}>
          {titolo && (
            <header className="mb-5 flex items-start justify-between gap-3">
              <div>
                <h1 className="text-[28px] font-bold leading-tight text-inchiostro">{titolo}</h1>
                {dove.voce === 'oggi' && <p className="text-[15px] text-tenue first-letter:uppercase">{GIORNO.format(new Date())}</p>}
              </div>
              <a href={linkCompleto('pipeline')} className="mt-1.5 inline-flex min-h-11 shrink-0 items-center gap-1 rounded-full px-2 text-[13px] text-tenue hover:bg-velo hover:text-inchiostro lg:hidden">
                Workspace completo <Icona nome="esterno" className="h-3.5 w-3.5" />
              </a>
            </header>
          )}
          {!dove.id && dove.voce === 'oggi' && <AvvisoTelefono />}
          {dove.id ? <SchedaLead key={dove.id} id={dove.id} indietro={indietro} />
            : dove.voce === 'lead' ? <Lead apri={apri} />
              : dove.voce === 'tutti' ? <Tutti apri={apriDaTutti} />
              : dove.voce === 'campagne' ? <Campagne />
                : <Oggi apri={apri} />}
        </main>
      </div>

      {/* il menu sul telefono: quattro voci in basso, a portata di pollice */}
      <nav aria-label="Sezioni" className="fixed inset-x-0 bottom-0 z-30 border-t border-velo bg-white/95 pb-[env(safe-area-inset-bottom)] pl-[env(safe-area-inset-left)] pr-[env(safe-area-inset-right)] backdrop-blur lg:hidden">
        <ul className="mx-auto flex max-w-md">
          {VOCI.map((v) => {
            const su = dove.voce === v.voce
            return (
              <li key={v.voce} className="flex-1">
                <a href={indirizzo({ voce: v.voce, id: null })} aria-current={su ? 'page' : undefined}
                   onClick={() => { passi.current += 1 }}
                   className={`flex min-h-16 flex-col items-center justify-center gap-0.5 text-[12.5px] font-semibold ${su ? 'text-blu-scuro' : 'text-tenue'}`}>
                  <span className={`flex h-8 w-14 items-center justify-center rounded-full ${su ? 'bg-blu-scuro/[0.1]' : ''}`}>
                    <Icona nome={v.icona} className="h-[22px] w-[22px]" />
                  </span>
                  {v.nome}
                </a>
              </li>
            )
          })}
        </ul>
      </nav>
    </div>
  )
}

function Pagina({ children }: { children: React.ReactNode }) {
  return <main className="mx-auto max-w-md px-4 py-16 text-center">{children}</main>
}

/** Un ceo che sta guardando il Workspace nei panni di un altro: qui i dati sono solo dei ceo. */
function Vista({ io }: { io: ChiSono }) {
  const [lavoro, setLavoro] = useState(false)
  return (
    <div role="alert" className="border-b border-attesa-bordo bg-attesa-fondo px-4 py-2.5 text-[14px] text-attesa-testo">
      Stai guardando il Workspace come {io.vista?.nome ?? 'un\'altra persona'}: qui alcune cose potrebbero non vedersi.{' '}
      <button disabled={lavoro} onClick={() => { setLavoro(true); void vediCome(null).then(() => window.location.reload()) }}
              className="min-h-11 font-bold underline underline-offset-2">
        Torna a te
      </button>
    </div>
  )
}
