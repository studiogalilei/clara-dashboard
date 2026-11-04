// IL DESK (4/11/2026). Dre, 3/11 sera: «buttiamo al cesso l'intero sistema fatto finora e mi crei
// una nuova dashboard per interagire al posto di questo... lascia spazio solo alle call».
// Quattro schermate: la Coda (ogni relazione con la mossa di Clara e il testo pronto: Invia,
// Modifica, No), le Call (prenotate e da richiamare, esiti a un tocco), le Relazioni (cerchi
// un'azienda, vedi tutto il filo), Clara (come sta, cosa ha imparato).
// Indirizzi: #/d/coda, #/d/coda/<id>, #/d/call, #/d/relazioni, #/d/relazioni/<id>, #/d/clara.
import { useEffect, useRef, useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'
import { chiSono, type ChiSono } from '../lib/accessi'
import Login from '../components/Login'
import { Icona, type NomeIcona } from '../snella/pezzi'
import { linkCompleto } from '../snella/uso'
import { AvvisoTelefono, CollegaTelefono } from '../snella/Telefono'
import { riallinea } from '../lib/notifiche'
import Coda from './Coda'
import Call from './Call'
import Relazioni from './Relazioni'
import Filo from './Filo'
import Analytics from './Analytics'

export type Voce = 'relazioni' | 'coda' | 'call' | 'analytics' | 'filo'
export interface Dove { voce: Voce; id: string | null }

// 4/11 pomeriggio, Dre: «Relazioni» e' dove agisce lui (la coda di prima, identica); «Coda» e' la coda di Clara,
// da sbirciare; «Analytics» e' il monitoraggio. «filo» e' la scheda intera di un'azienda, senza voce nel menu.
const VOCI: Array<{ voce: Voce; nome: string; icona: NomeIcona }> = [
  { voce: 'call', nome: 'Call', icona: 'telefono' },
  { voce: 'relazioni', nome: 'Relazioni', icona: 'lead' },
  { voce: 'coda', nome: 'Coda', icona: 'tutti' },
  { voce: 'analytics', nome: 'Analytics', icona: 'campagne' },
]

export function inDesk(hash: string): boolean {
  return /^#\/d(\/|$)/.test(hash)
}

function leggi(): Dove {
  const [, , voce, id] = window.location.hash.replace(/^#/, '').split('/')
  const v: Voce = voce === 'call' || voce === 'coda' || voce === 'analytics' || voce === 'filo' ? voce : voce === 'clara' ? 'analytics' : 'relazioni'
  return { voce: v, id: id ? decodeURIComponent(id) : null }
}

export function indirizzo(d: Dove): string {
  return `#/d/${d.voce}${d.id ? `/${encodeURIComponent(d.id)}` : ''}`
}

export default function Desk() {
  const [larga, setLarga] = useState<boolean>(() => { try { return localStorage.getItem('desk_barra') !== 'stretta' } catch { return true } })
  const cambiaBarra = (v: boolean) => { setLarga(v); try { localStorage.setItem('desk_barra', v ? 'larga' : 'stretta') } catch { /* niente */ } }
  const [session, setSession] = useState<Session | null>(null)
  const [pronta, setPronta] = useState(false)
  const [io, setIo] = useState<ChiSono | null>(null)
  const [erroreIo, setErroreIo] = useState(false)
  const [dove, setDove] = useState<Dove>(leggi)
  const passi = useRef(0)

  useEffect(() => {
    void supabase.auth.getSession().then(({ data }) => { setSession(data.session); setPronta(true) })
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s))
    return () => sub?.subscription.unsubscribe()
  }, [])

  useEffect(() => {
    if (!session) { setIo(null); return }
    let vivo = true
    chiSono().then((c) => { if (vivo) { setIo(c); setErroreIo(false); if (c.ruolo === 'ceo') void riallinea() } })
      .catch(() => { if (vivo) setErroreIo(true) })
    return () => { vivo = false }
  }, [session])

  useEffect(() => {
    const cambia = () => setDove(leggi())
    window.addEventListener('hashchange', cambia)
    return () => window.removeEventListener('hashchange', cambia)
  }, [])

  const vai = (d: Dove) => { passi.current += 1; window.location.hash = indirizzo(d) }
  const indietro = () => { if (passi.current > 0) { passi.current -= 1; window.history.back() } else vai({ voce: dove.voce, id: null }) }

  if (!pronta) return <div className="min-h-dvh bg-white" />
  if (!session) return <Login />
  if (erroreIo) {
    return (
      <div className="mx-auto max-w-md p-6 text-center">
        <p className="text-[16px] text-inchiostro">Non riesco a capire chi sei: la connessione non risponde.</p>
        <button onClick={() => window.location.reload()} className="mt-3 min-h-11 rounded-full bg-blu-scuro px-5 font-semibold text-white">Riprova</button>
      </div>
    )
  }
  if (!io) return <div className="min-h-dvh bg-white" />
  if (io.ruolo !== 'ceo') {
    return (
      <div className="mx-auto max-w-md p-6 text-center">
        <p className="text-[16px] text-inchiostro">Il Desk è la scrivania commerciale. Il tuo Workspace è qui:</p>
        <a href={linkCompleto('pipeline')} className="mt-3 inline-flex min-h-11 items-center rounded-full bg-blu-scuro px-5 font-semibold text-white">Vai al Workspace</a>
      </div>
    )
  }

  return (
    <div className="desk min-h-dvh bg-fondo text-inchiostro lg:flex">

      <a href="#contenuto" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-full focus:bg-white focus:px-4 focus:py-2 focus:shadow">Vai al contenuto</a>

      {/* a sinistra sul computer: scuro, come una scrivania che resta ferma */}
      {/* 4/11, Dre: «allargabile come quella di Claude»: si chiude a sole icone e si riapre, e si ricorda com'era */}
      <nav aria-label="Sezioni" className={`relative hidden shrink-0 flex-col bg-navy-scuro py-5 text-white transition-[width] duration-200 lg:sticky lg:top-0 lg:flex lg:h-dvh ${larga ? 'w-[228px] px-3' : 'w-[72px] px-2.5'}`}>
        <div className={`mb-6 flex items-center ${larga ? 'gap-3 px-3' : 'justify-center'}`}>
          <img src={`${import.meta.env.BASE_URL}sg-simbolo.svg`} alt="Studio Galilei" width={26} height={30} style={{ width: 26, height: 30 }} className="shrink-0 object-contain brightness-0 invert" />
          {larga && <span className="leading-tight"><span className="block text-[11px] font-extrabold tracking-[.14em]">STUDIO GALILEI</span><span className="block text-[10px] tracking-[.12em] text-white/60">OUTBOUND DESK</span></span>}
        </div>
        <button onClick={() => cambiaBarra(!larga)} aria-label={larga ? 'Chiudi la barra' : 'Apri la barra'} aria-expanded={larga} title={larga ? 'Chiudi la barra' : 'Apri la barra'}
                className="absolute -right-3 top-[3.1rem] grid h-6 w-6 place-items-center rounded-full border border-white/20 bg-navy-scuro text-white/70 shadow hover:text-white">
          <Icona nome="indietro" className={`h-3.5 w-3.5 transition-transform ${larga ? '' : 'rotate-180'}`} />
        </button>
        <ul className="space-y-1">
          {VOCI.map((v) => {
            const su = dove.voce === v.voce || (v.voce === 'relazioni' && dove.voce === 'filo')
            return (
              <li key={v.voce}>
                <a href={indirizzo({ voce: v.voce, id: null })} aria-current={su ? 'page' : undefined} onClick={() => { passi.current += 1 }} title={larga ? undefined : v.nome}
                   className={`flex min-h-11 items-center rounded-xl text-[14px] font-semibold ${larga ? 'gap-3 px-3.5' : 'justify-center px-0'} ${su ? 'bg-white text-navy' : 'text-white/80 hover:bg-white/[0.1] hover:text-white'}`}>
                  <Icona nome={v.icona} className="h-[18px] w-[18px] shrink-0" /> {larga && v.nome}
                </a>
              </li>
            )
          })}
        </ul>
        <div className="mt-auto space-y-2">
          {larga ? (
            <div className="rounded-xl border border-white/15 bg-white/[0.06] p-3.5 text-[12px] leading-relaxed text-white/75">
              <p className="flex items-center gap-2 font-bold text-white"><span className="h-2 w-2 rounded-full bg-ok-segno" /> Clara è al lavoro</p>
              <p className="mt-1.5">Legge ogni risposta, decide e manda da sola. A te restano le call e le cose ferme.</p>
            </div>
          ) : (
            <p className="flex justify-center py-2" title="Clara è al lavoro"><span className="h-2.5 w-2.5 rounded-full bg-ok-segno" /></p>
          )}
          {larga && <CollegaTelefono tipo="piatto" className="w-full justify-start px-3 text-[13px] font-normal text-white/60 hover:text-white" />}
          <a href={linkCompleto('pipeline')} title="Workspace completo" className={`flex min-h-10 items-center gap-2 rounded-xl text-[13px] text-white/60 hover:text-white ${larga ? 'px-3' : 'justify-center'}`}>
            {larga && 'Workspace completo'} <Icona nome="esterno" className="h-3.5 w-3.5" />
          </a>
        </div>
      </nav>

      <div className="min-w-0 flex-1">
        <main id="contenuto" className="mx-auto w-full max-w-[1480px] pl-[max(0.875rem,env(safe-area-inset-left))] pr-[max(0.875rem,env(safe-area-inset-right))] pb-[calc(92px+env(safe-area-inset-bottom))] pt-[calc(10px+env(safe-area-inset-top))] lg:px-7 lg:pb-12 lg:pt-6">
          {dove.voce === 'relazioni' && !dove.id && <AvvisoTelefono />}
          {dove.voce === 'relazioni' ? <Relazioni dove={dove} vai={vai} indietro={indietro} />
            : dove.voce === 'coda' ? <Coda vai={vai} />
              : dove.voce === 'call' ? <Call vai={vai} />
                : dove.voce === 'filo' ? <Filo dove={dove} vai={vai} indietro={indietro} />
                  : <Analytics />}
        </main>
      </div>

      {/* in basso sul telefono */}
      <nav aria-label="Sezioni" className="fixed inset-x-0 bottom-0 z-30 border-t border-bordo bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden">
        <ul className="mx-auto flex max-w-md">
          {VOCI.map((v) => {
            const su = dove.voce === v.voce || (v.voce === 'relazioni' && dove.voce === 'filo')
            return (
              <li key={v.voce} className="flex-1">
                <a href={indirizzo({ voce: v.voce, id: null })} aria-current={su ? 'page' : undefined} onClick={() => { passi.current += 1 }}
                   className={`flex min-h-16 flex-col items-center justify-center gap-0.5 text-[12px] font-semibold ${su ? 'text-navy' : 'text-tenue'}`}>
                  <span className={`flex h-8 w-14 items-center justify-center rounded-full ${su ? 'bg-navy/[0.1]' : ''}`}><Icona nome={v.icona} className="h-[21px] w-[21px]" /></span>
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
