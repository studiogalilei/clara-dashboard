import { useState } from 'react'
import { supabase } from '../lib/supabase'
import { entraConGoogle } from '../lib/google'
import { entraConCodice } from '../lib/ponte'
import { installata } from '../lib/notifiche'

// LA PORTA (11/9): si entra con Google, con la mail @studiogalilei.com.
// La password resta sotto, per chi ce l'ha ancora o se Google e' giu'.
// 17/10: e il codice, per l'app sulla Home del telefono (src/lib/ponte.ts): li' la memoria e'
// separata da Safari, e il codice si scrive dentro l'app, senza uscirne.

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [conPassword, setConPassword] = useState(false)
  const [conCodice, setConCodice] = useState(false)
  const [codice, setCodice] = useState('')
  const app = installata()

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setErr(null)
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) setErr('Credenziali sbagliate, riprova.')
    setBusy(false)
  }

  async function codiceOk(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true); setErr(null)
    const no = await entraConCodice(codice)
    if (no) { setErr(no); setBusy(false) }
  }

  async function google() {
    setBusy(true); setErr(null)
    const e = await entraConGoogle()
    if (e) { setErr('Google non ha risposto: ' + e); setBusy(false) }
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-fondo px-6">
      <div className="w-full max-w-sm rounded-2xl border border-bordo bg-white p-6 shadow-[0_4px_16px_rgba(16,24,40,0.05)]">
        <img src={`${import.meta.env.BASE_URL}sg-simbolo.svg`} alt="" className="mb-3 h-10 w-10 object-contain" />
        <h1 className="text-xl text-navy"><span className="font-black">SG</span> <span className="font-bold">Workspace</span></h1>
        <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-navy/70">Beta</p>
        <p className="mb-5 mt-1 text-sm text-tenue">Studio Galilei</p>

        <button
          onClick={() => void google()}
          disabled={busy}
          className="flex min-h-11 w-full items-center justify-center gap-2.5 rounded-full bg-blu py-2.5 text-[15px] font-bold text-white hover:bg-blu-scuro disabled:opacity-50"
        >
          <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden><path fill="#fff" d="M44.5 20H24v8.5h11.8C34.7 33.9 30.1 37 24 37c-7.2 0-13-5.8-13-13s5.8-13 13-13c3.1 0 5.9 1.1 8.1 2.9l6.4-6.4C34.6 4.1 29.6 2 24 2 11.8 2 2 11.8 2 24s9.8 22 22 22c11 0 21-8 21-22 0-1.3-.2-2.7-.5-4z"/></svg>
          {busy ? 'Un attimo…' : 'Entra con Google'}
        </button>
        <p className="mt-2 text-center text-[12px] text-tenue">Con la mail @studiogalilei.com</p>

        {!conCodice ? (
          <button onClick={() => { setConCodice(true); setConPassword(false); setErr(null) }}
                  className="mt-3 flex min-h-11 w-full items-center justify-center rounded-full border border-bordo text-[15px] font-semibold text-navy hover:border-navy">
            Entra con un codice
          </button>
        ) : (
          <form onSubmit={(e) => void codiceOk(e)} className="mt-4 border-t border-velo pt-4">
            <label htmlFor="codice" className="block text-[14px] font-semibold text-inchiostro">Il codice di 6 cifre</label>
            <p className="mb-2 mt-0.5 text-[13px] leading-snug text-tenue">
              Te lo dà il Workspace dove sei già dentro: sul computer «Collega il telefono», in basso a sinistra; sull'iPhone, in Safari, la pagina Oggi.
            </p>
            <input id="codice" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9 ]*" maxLength={7} required autoFocus
                   value={codice} onChange={(e) => setCodice(e.target.value.replace(/[^0-9]/g, '').slice(0, 6))}
                   className="mb-3 w-full rounded-lg border border-bordo px-3 py-2.5 text-center text-[22px] font-bold tracking-[0.3em] outline-none focus:border-blu" />
            <button type="submit" disabled={busy || codice.length !== 6}
                    className="min-h-11 w-full rounded-full bg-navy text-[15px] font-bold text-white disabled:opacity-50">
              {busy ? 'Entro…' : 'Entra'}
            </button>
          </form>
        )}
        {app && !conCodice && (
          <p className="mt-2 text-center text-[12px] leading-snug text-tenue">Nell'app del telefono: se Google non ti riporta qui, usa il codice.</p>
        )}

        {err && <p role="alert" className="mt-3 text-[14px] text-red-700">{err}</p>}

        {!conPassword ? (
          <button onClick={() => { setConPassword(true); setConCodice(false); setErr(null) }}
                  className="mt-3 min-h-11 w-full text-center text-[13px] font-semibold text-tenue hover:text-inchiostro">
            Entra con la password
          </button>
        ) : (
          <form onSubmit={submit} className="mt-5 border-t border-velo pt-4">
            <input type="email" required placeholder="Email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)}
                   className="mb-2.5 w-full rounded-lg border border-bordo px-3 py-2.5 text-[16px] outline-none focus:border-blu" />
            <input type="password" required placeholder="Password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)}
                   className="mb-3.5 w-full rounded-lg border border-bordo px-3 py-2.5 text-[16px] outline-none focus:border-blu" />
            <button type="submit" disabled={busy}
                    className="min-h-11 w-full rounded-full border border-bordo text-[15px] font-bold text-navy hover:border-navy disabled:opacity-50">
              {busy ? 'Accesso…' : 'Entra'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
