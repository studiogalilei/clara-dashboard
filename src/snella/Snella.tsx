// LA VERSIONE SNELLA DEL WORKSPACE (15/10/2026), fino a «Clara nuova» (dicembre).
// Dre: il Workspace e' pesante e confuso per quello che fa ogni giorno con le campagne.
// Tre schermate e basta: Oggi (chi chiamare, le call, cosa decidere), Lead (chi ha risposto,
// con la scheda e le note), Campagne (come vanno). Sul telefono le tre voci stanno in basso,
// sul computer a sinistra. Il Workspace completo resta a un tocco, in alto.
//
// Gli indirizzi: #/s/oggi, #/s/lead, #/s/lead/<id>, #/s/campagne. Un ceo che apre il Workspace
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
import { Icona, type NomeIcona } from './pezzi'
import { linkCompleto } from './uso'

type Voce = 'oggi' | 'lead' | 'campagne'
interface Dove { voce: Voce; id: string | null }

const VOCI: Array<{ voce: Voce; nome: string; icona: NomeIcona }> = [
  { voce: 'oggi', nome: 'Oggi', icona: 'oggi' },
  { voce: 'lead', nome: 'Lead', icona: 'lead' },
  { voce: 'campagne', nome: 'Campagne', icona: 'campagne' },
]

function leggi(): Dove {
  const [, , voce, id] = window.location.hash.replace(/^#/, '').split('/')
  const v: Voce = voce === 'lead' || voce === 'campagne' ? voce : 'oggi'
  return { voce: v, id: v === 'lead' && id ? decodeURIComponent(id) : null }
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
  useEffect(() => {
    if (!session) return
    chiSono().then(setIo).catch(() => setErroreIo(true))
  }, [session])
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
    else { window.location.replace(indirizzo({ voce: 'lead', id: null })) }
  }
  const apri = (id: string) => vai({ voce: 'lead', id })

  if (!pronta) return <div className="min-h-dvh bg-white" />
  if (!session) return <Login />
  if (erroreIo) {
    return (
      <Pagina>
        <p role="alert" className="text-[16px] text-inchiostro">Non riesco a capire chi sei: controlla la connessione e ricarica la pagina.</p>
      </Pagina>
    )
  }
  if (!io) return <div className="min-h-dvh bg-white" />
  if (io.ruolo !== 'ceo' && !io.vista) {
    return (
      <Pagina>
        <p className="text-[16px] text-inchiostro">Questa pagina è per chi segue le campagne.</p>
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
        <a href={linkCompleto('pipeline')} className="mt-auto flex min-h-11 items-center gap-2 rounded-full px-4 text-[14px] text-tenue hover:bg-velo hover:text-inchiostro">
          Workspace completo <Icona nome="esterno" className="h-4 w-4" />
        </a>
      </nav>

      <div className="min-w-0 flex-1">
        {io.vista && <Vista io={io} />}
        <main id="contenuto" className="mx-auto w-full max-w-[760px] px-4 pb-[calc(96px+env(safe-area-inset-bottom))] pt-[calc(12px+env(safe-area-inset-top))] lg:px-8 lg:pb-16 lg:pt-8">
          {titolo && (
            <header className="mb-5 flex items-start justify-between gap-3">
              <div>
                <h1 className="text-[28px] font-bold leading-tight text-inchiostro">{titolo}</h1>
                {dove.voce === 'oggi' && <p className="text-[15px] text-tenue first-letter:uppercase">{GIORNO.format(new Date())}</p>}
              </div>
              <a href={linkCompleto('pipeline')} className="mt-1.5 inline-flex min-h-10 shrink-0 items-center gap-1 rounded-full px-2 text-[13px] text-tenue hover:bg-velo hover:text-inchiostro lg:hidden">
                Workspace completo <Icona nome="esterno" className="h-3.5 w-3.5" />
              </a>
            </header>
          )}
          {dove.id ? <SchedaLead key={dove.id} id={dove.id} indietro={indietro} />
            : dove.voce === 'lead' ? <Lead apri={apri} />
              : dove.voce === 'campagne' ? <Campagne />
                : <Oggi apri={apri} />}
        </main>
      </div>

      {/* il menu sul telefono: tre voci in basso, a portata di pollice */}
      <nav aria-label="Sezioni" className="fixed inset-x-0 bottom-0 z-30 border-t border-velo bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden">
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
    <div role="alert" className="border-b border-amber-200 bg-amber-50 px-4 py-2.5 text-[14px] text-amber-900">
      Stai guardando il Workspace come {io.vista?.nome ?? 'un\'altra persona'}: qui alcune cose potrebbero non vedersi.{' '}
      <button disabled={lavoro} onClick={() => { setLavoro(true); void vediCome(null).then(() => window.location.reload()) }}
              className="min-h-9 font-bold underline underline-offset-2">
        Torna a te
      </button>
    </div>
  )
}
