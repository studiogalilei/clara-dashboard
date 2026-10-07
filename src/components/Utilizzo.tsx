import { useEffect, useMemo, useState } from 'react'
import { supabase, demo } from '../lib/supabase'
import { chiSono } from '../lib/accessi'
import { Card, TitoloCard } from './ui'

// L'UTILIZZO, STILE CODEXBAR (Dre, 7/10: «un qualcosa che mi dica l'utilizzo, cosi'
// monitoro l'utilizzo mio e di tutti; in Impostazioni, solo io vedo»). Una riga per
// persona: quanto ha lavorato oggi e negli ultimi 7 giorni, a barre sottili come la
// CodexBar, dove passa il tempo, e quando l'abbiamo visto l'ultima volta. Sotto, i
// crediti delle piattaforme. I numeri li conta il database (schema_v77); il riepilogo
// risponde solo a Dre (utilizzo_squadra), a chiunque altro questo pannello non compare.

const DRE = '43095060-b873-4d29-825b-55522f26af55'

interface Riga { uid: string; nome: string | null; ruolo: string | null; giorno: string; minuti: number; azioni: number; schermate: Record<string, number>; telefono: number; ultimo_at: string }
interface Piattaforma { nome: string; unita: string | null; saldo: number | null; totale: number | null; aggiornato_il: string | null }

const NOMI_SCHERMATA: Record<string, string> = {
  oggi: 'Oggi', prospect: 'Pipeline', pipeline: 'Pipeline', aziende: 'Aziende', clienti: 'Clienti', calendario: 'Calendario',
  posta: 'Posta', clara: 'Posta', scheda: 'Schede', preventivi: 'Preventivi', chat: 'Chat', vault: 'Vault', impostazioni: 'Impostazioni',
}

const durata = (m: number) => (m < 60 ? `${m} min` : `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, '0')}m`)
function fa(iso: string): string {
  const min = Math.round((Date.now() - new Date(iso).getTime()) / 60_000)
  if (min < 2) return 'adesso'
  if (min < 60) return `${min} min fa`
  const ore = Math.round(min / 60)
  if (ore < 24) return `${ore} ${ore === 1 ? 'ora' : 'ore'} fa`
  const g = Math.round(ore / 24)
  return `${g} ${g === 1 ? 'giorno' : 'giorni'} fa`
}
const oggiRoma = () => new Date().toLocaleDateString('sv-SE', { timeZone: 'Europe/Rome' })

// la barra della CodexBar: un binario sottile, il riempimento, il numero a destra
function Barra({ quota, colore = 'bg-navy' }: { quota: number; colore?: string }) {
  return (
    <span className="relative block h-1.5 w-full overflow-hidden rounded-full bg-velo">
      <span className={`absolute inset-y-0 left-0 rounded-full ${colore} transition-[width] duration-300`} style={{ width: `${Math.max(quota > 0 ? 3 : 0, Math.min(100, quota * 100))}%` }} />
    </span>
  )
}

const FINTI: Riga[] = [
  { uid: 'demo', nome: 'Dramane', ruolo: 'ceo', giorno: oggiRoma(), minuti: 74, azioni: 610, schermate: { posta: 31, vault: 22, prospect: 14, oggi: 7 }, telefono: 12, ultimo_at: new Date(Date.now() - 3 * 60_000).toISOString() },
  { uid: 'giacomo', nome: 'Giacomo Facchin', ruolo: 'ceo', giorno: oggiRoma(), minuti: 38, azioni: 240, schermate: { clienti: 20, preventivi: 18 }, telefono: 0, ultimo_at: new Date(Date.now() - 50 * 60_000).toISOString() },
  { uid: 'carlo', nome: 'Carlo Durigon', ruolo: 'manager', giorno: oggiRoma(), minuti: 12, azioni: 60, schermate: { oggi: 8, chat: 4 }, telefono: 12, ultimo_at: new Date(Date.now() - 3 * 3600_000).toISOString() },
]

export default function Utilizzo() {
  const [mio, setMio] = useState<string | null>(demo ? DRE : null)
  const [righe, setRighe] = useState<Riga[] | null>(demo ? FINTI : null)
  const [piatt, setPiatt] = useState<Piattaforma[]>([])
  const [guaio, setGuaio] = useState<string | null>(null)

  useEffect(() => {
    if (demo) return
    void chiSono().then((c) => setMio(c.uid))
  }, [])
  useEffect(() => {
    if (demo || mio !== DRE) return
    void supabase.rpc('utilizzo_squadra', { p_giorni: 7 }).then(({ data, error }) => {
      if (error) { setGuaio(/utilizzo_squadra|function/i.test(error.message) ? 'Il contatore parte appena incolli la v77 in Supabase: da lì in poi ogni minuto di lavoro si conta.' : error.message); setRighe([]); return }
      setRighe((data as Riga[]) ?? [])
    })
    void supabase.from('piattaforme').select('nome,unita,saldo,totale,aggiornato_il').order('nome')
      .then(({ data }) => setPiatt((data as Piattaforma[]) ?? []))
  }, [mio])

  const persone = useMemo(() => {
    const oggi = oggiRoma()
    const m = new Map<string, { nome: string; ruolo: string | null; oggi: number; sette: number; azioni: number; telefono: number; ultimo: string; dove: Record<string, number> }>()
    for (const r of righe ?? []) {
      const x = m.get(r.uid) ?? { nome: r.nome ?? 'Senza profilo', ruolo: r.ruolo, oggi: 0, sette: 0, azioni: 0, telefono: 0, ultimo: r.ultimo_at, dove: {} }
      x.sette += r.minuti; x.azioni += r.azioni; x.telefono += r.telefono
      if (r.giorno === oggi) x.oggi += r.minuti
      if (r.ultimo_at > x.ultimo) x.ultimo = r.ultimo_at
      for (const [k, v] of Object.entries(r.schermate ?? {})) x.dove[k] = (x.dove[k] ?? 0) + Number(v)
      m.set(r.uid, x)
    }
    return [...m.values()].sort((a, b) => b.sette - a.sette)
  }, [righe])

  // le barre si misurano sul piu' attivo della squadra: chi lavora di piu' fa il 100%
  const maxOggi = Math.max(60, ...persone.map((p) => p.oggi))
  const maxSette = Math.max(60, ...persone.map((p) => p.sette))

  if (mio !== DRE) return null

  return (
    <Card className="p-5">
      <div className="flex items-baseline justify-between gap-2">
        <TitoloCard>Utilizzo</TitoloCard>
        <span className="text-[11px] font-semibold text-tenue">solo tu lo vedi</span>
      </div>
      {guaio && <p className="mb-2 rounded-lg bg-velo/70 px-3 py-2 text-[13px] text-tenue">{guaio}</p>}
      {righe === null && <p className="text-[13px] text-tenue">Leggo…</p>}
      {righe !== null && persone.length === 0 && !guaio && (
        <p className="text-[13px] text-tenue">Ancora nessun minuto contato: si riempie man mano che la squadra lavora.</p>
      )}
      <ul className="space-y-4">
        {persone.map((p) => {
          const dove = Object.entries(p.dove).sort((a, b) => b[1] - a[1]).slice(0, 3)
          return (
            <li key={p.nome}>
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-[14px] font-bold text-inchiostro">{p.nome.split(' ')[0]}</span>
                {Date.now() - new Date(p.ultimo).getTime() < 5 * 60_000
                  ? <span className="flex items-center gap-1.5 text-[11px] font-semibold text-green-700"><span className="h-1.5 w-1.5 rounded-full bg-green-600" />sta lavorando</span>
                  : <span className="text-[11px] font-semibold text-tenue">visto {fa(p.ultimo)}</span>}
              </div>
              <div className="mt-1.5 grid grid-cols-[52px_minmax(0,1fr)_64px] items-center gap-x-3 gap-y-1.5 text-[12px]">
                <span className="text-tenue">Oggi</span>
                <Barra quota={p.oggi / maxOggi} />
                <span className="text-right font-semibold tabular-nums">{durata(p.oggi)}</span>
                <span className="text-tenue">7 giorni</span>
                <Barra quota={p.sette / maxSette} colore="bg-blu" />
                <span className="text-right font-semibold tabular-nums">{durata(p.sette)}</span>
              </div>
              {dove.length > 0 && (
                <p className="mt-1 text-[11.5px] text-tenue">
                  {dove.map(([k, v]) => `${NOMI_SCHERMATA[k] ?? k} ${durata(v)}`).join(', ')}
                  {p.telefono > 0 ? `, dal telefono ${durata(p.telefono)}` : ''}
                </p>
              )}
            </li>
          )
        })}
      </ul>
      {piatt.length > 0 && (
        <div className="mt-5 border-t border-velo pt-4">
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.05em] text-navy/70">Crediti delle piattaforme</p>
          <ul className="space-y-2.5">
            {piatt.filter((x) => x.saldo != null).map((x) => {
              const quota = x.totale ? Number(x.saldo) / Number(x.totale) : 1
              return (
                <li key={x.nome} className="grid grid-cols-[88px_minmax(0,1fr)_96px] items-center gap-3 text-[12px]">
                  <span className="truncate font-semibold capitalize">{x.nome}</span>
                  <Barra quota={quota} colore={quota < 0.15 ? 'bg-red-600' : quota < 0.35 ? 'bg-amber-400' : 'bg-green-600'} />
                  <span className="text-right tabular-nums text-tenue">{Number(x.saldo).toLocaleString('it-IT')}{x.totale ? ` su ${Number(x.totale).toLocaleString('it-IT')}` : ''}</span>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </Card>
  )
}
