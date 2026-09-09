import { useState } from 'react'
import { supabase } from '../lib/supabase'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setErr(null)
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) setErr('Credenziali sbagliate, riprova.')
    setBusy(false)
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-fondo px-6">
      <form onSubmit={submit} className="w-full max-w-sm rounded-2xl border border-bordo bg-white p-6 shadow-[0_4px_16px_rgba(16,24,40,0.05)]">
        <h1 className="text-xl font-bold">Studio Galilei</h1>
        <p className="mb-5 text-sm text-tenue">Dashboard</p>
        <input
          type="email"
          required
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mb-2.5 w-full rounded-lg border border-bordo px-3 py-2 text-sm outline-none focus:border-blu"
        />
        <input
          type="password"
          required
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mb-3.5 w-full rounded-lg border border-bordo px-3 py-2 text-sm outline-none focus:border-blu"
        />
        {err && <p className="mb-3 text-sm text-red-700">{err}</p>}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-full bg-blu py-2 text-sm font-bold text-white hover:bg-blu-scuro disabled:opacity-50"
        >
          {busy ? 'Accesso…' : 'Entra'}
        </button>
      </form>
    </div>
  )
}
