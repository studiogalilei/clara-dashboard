// IL LINKEDIN DESK (27/11/2026). Dre: «eliminiamo tutto cio' che riguarda l'outbound, il desk diventa prettamente
// per LinkedIn». Due zone: Post (il compositore e il calendario) e Persone (le aziende del giorno a cui mandare la
// richiesta). Chiunque del team entra con il suo account e vede solo le sue cose (le regole stanno nel database).
// Indirizzi: #/d/post, #/d/persone (e #/d/linkedin, il vecchio indirizzo dei post).
import { useEffect, useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'
import Login from '../Login'
import { Icona, type NomeIcona } from '../ui/pezzi'
import Linkedin from './Linkedin'
import Persone from './Persone'

type Voce = 'post' | 'persone'
const VOCI: Array<{ voce: Voce; nome: string; icona: NomeIcona }> = [
  { voce: 'post', nome: 'Post', icona: 'penna' },
  { voce: 'persone', nome: 'Persone', icona: 'persone' },
]

function leggi(): Voce {
  return /^#\/d\/persone/.test(window.location.hash) ? 'persone' : 'post'
}

export default function Desk() {
  const [session, setSession] = useState<Session | null>(null)
  const [pronta, setPronta] = useState(false)
  const [voce, setVoce] = useState<Voce>(leggi)

  useEffect(() => {
    void supabase.auth.getSession().then(({ data }) => { setSession(data.session); setPronta(true) })
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s))
    return () => sub?.subscription.unsubscribe()
  }, [])
  useEffect(() => {
    const cambia = () => setVoce(leggi())
    window.addEventListener('hashchange', cambia)
    return () => window.removeEventListener('hashchange', cambia)
  }, [])

  if (!pronta) return <div className="min-h-dvh bg-fondo" />
  if (!session) return <Login />

  return (
    <div className="min-h-dvh bg-fondo text-inchiostro lg:flex">
      <nav aria-label="Sezioni" className="hidden w-56 shrink-0 flex-col bg-navy-scuro px-3 py-5 text-white lg:sticky lg:top-0 lg:flex lg:h-dvh">
        <div className="mb-6 flex items-center gap-3 px-3">
          <img src={`${import.meta.env.BASE_URL}sg-simbolo.svg`} alt="Studio Galilei" width={26} height={30} className="shrink-0 brightness-0 invert" />
          <span className="leading-tight"><span className="block text-[11px] font-extrabold tracking-[.14em]">STUDIO GALILEI</span><span className="block text-[10px] tracking-[.12em] text-white/70">LINKEDIN DESK</span></span>
        </div>
        <ul className="space-y-1">
          {VOCI.map((v) => (
            <li key={v.voce}>
              <a href={`#/d/${v.voce}`} aria-current={voce === v.voce ? 'page' : undefined}
                 className={`flex min-h-11 items-center gap-3 rounded-xl px-3.5 text-[14px] font-semibold ${voce === v.voce ? 'bg-white text-navy' : 'text-white/85 hover:bg-white/10'}`}>
                <Icona nome={v.icona} className="h-[18px] w-[18px]" /> {v.nome}
              </a>
            </li>
          ))}
        </ul>
        <button type="button" onClick={() => void supabase.auth.signOut()} className="mt-auto min-h-11 rounded-xl px-3.5 text-left text-[13px] font-semibold text-white/70 hover:text-white">Esci</button>
      </nav>

      <main className="min-w-0 flex-1 px-[max(0.875rem,env(safe-area-inset-left))] pb-[calc(92px+env(safe-area-inset-bottom))] pt-[calc(14px+env(safe-area-inset-top))] lg:px-8 lg:pb-12 lg:pt-8">
        {voce === 'persone' ? <Persone /> : <Linkedin />}
      </main>

      <nav aria-label="Sezioni" className="fixed inset-x-0 bottom-0 z-30 border-t border-bordo bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden">
        <ul className="mx-auto flex max-w-md">
          {VOCI.map((v) => (
            <li key={v.voce} className="flex-1">
              <a href={`#/d/${v.voce}`} aria-current={voce === v.voce ? 'page' : undefined}
                 className={`flex min-h-16 flex-col items-center justify-center gap-0.5 text-[12px] font-semibold ${voce === v.voce ? 'text-navy' : 'text-tenue'}`}>
                <span className={`flex h-8 w-14 items-center justify-center rounded-full ${voce === v.voce ? 'bg-navy/10' : ''}`}><Icona nome={v.icona} className="h-[21px] w-[21px]" /></span>
                {v.nome}
              </a>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  )
}
