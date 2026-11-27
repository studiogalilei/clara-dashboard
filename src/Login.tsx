import { useState } from 'react'
import { supabase } from './lib/supabase'

// LA PORTA del LinkedIn Desk (27/11/2026): si entra con Google, con la mail @studiogalilei.com, o con la password.
// Dal Desk di prima: niente permessi in piu' (Gmail, Calendar, Drive servivano all'outbound, che non c'e' piu').

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [conPassword, setConPassword] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true); setErr(null)
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) setErr('Credenziali sbagliate, riprova.')
    setBusy(false)
  }

  async function google() {
    setBusy(true); setErr(null)
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin + window.location.pathname, queryParams: { hd: 'studiogalilei.com' } },
    })
    if (error) { setErr('Google non ha risposto: ' + error.message); setBusy(false) }
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-fondo px-6">
      <div className="w-full max-w-sm rounded-2xl border border-bordo bg-white p-6">
        <img src={`${import.meta.env.BASE_URL}sg-simbolo.svg`} alt="" className="mb-3 h-10 w-10 object-contain" />
        <h1 className="text-[22px] font-black text-navy">Studio Galilei</h1>
        <p className="mb-5 text-[12px] font-bold uppercase tracking-[0.14em] text-navy/70">LinkedIn Desk</p>
        <button onClick={() => void google()} disabled={busy}
                className="flex min-h-12 w-full items-center justify-center gap-2.5 rounded-full bg-blu-scuro text-[15px] font-bold text-white hover:bg-navy disabled:opacity-50">
          <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden><path fill="#fff" d="M44.5 20H24v8.5h11.8C34.7 33.9 30.1 37 24 37c-7.2 0-13-5.8-13-13s5.8-13 13-13c3.1 0 5.9 1.1 8.1 2.9l6.4-6.4C34.6 4.1 29.6 2 24 2 11.8 2 2 11.8 2 24s9.8 22 22 22c11 0 21-8 21-22 0-1.3-.2-2.7-.5-4z"/></svg>
          {busy ? 'Un attimo…' : 'Entra con Google'}
        </button>
        <p className="mt-2 text-center text-[13px] text-tenue">Con la mail @studiogalilei.com</p>
        {err && <p role="alert" className="mt-3 text-[14px] text-no-testo">{err}</p>}
        {!conPassword ? (
          <button onClick={() => { setConPassword(true); setErr(null) }} className="mt-3 min-h-11 w-full text-[14px] font-semibold text-tenue hover:text-inchiostro">
            Entra con la password
          </button>
        ) : (
          <form onSubmit={submit} className="mt-5 border-t border-bordo pt-4">
            <input type="email" required placeholder="Email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)}
                   className="mb-2.5 w-full rounded-xl border border-bordo px-3 py-2.5 text-[16px] outline-none focus:border-blu-scuro" />
            <input type="password" required placeholder="Password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)}
                   className="mb-3.5 w-full rounded-xl border border-bordo px-3 py-2.5 text-[16px] outline-none focus:border-blu-scuro" />
            <button type="submit" disabled={busy} className="min-h-11 w-full rounded-full border border-bordo text-[15px] font-bold text-navy hover:border-navy disabled:opacity-50">
              {busy ? 'Accesso…' : 'Entra'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
