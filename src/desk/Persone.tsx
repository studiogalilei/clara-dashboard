// LE PERSONE DEL GIORNO (27/11/2026). Dre: «al giorno da' il link di profili suggeriti in target a cui mandare la
// richiesta... te lo suggerisce, tu lo fai, il giorno dopo te ne da' altri; se te lo dimentichi restano quelli».
// Ogni scheda e' un'azienda con un segnale («perche' adesso»): apri LinkedIn, mandi la richiesta, segni Fatto.
// Il sistema non manda niente da solo su LinkedIn: suggerisce e basta.
import { useCallback } from 'react'
import { supabase } from '../lib/supabase'
import { Bottone, Carico, Errore, Icona, Vuoto } from '../ui/pezzi'
import { useAvviso, useDati } from '../ui/uso'

export interface Suggerito {
  id: string
  giorno: string
  stato: 'da_fare' | 'fatto' | 'saltato'
  fatto_il: string | null
  azienda: string
  settore: string | null
  citta: string | null
  persona: string | null
  ruolo: string | null
  profilo: string | null
  cerca: string | null
  perche: string
  fonte: string | null
  segnale: 'annuncio' | 'sito' | 'recensioni' | 'cambiamento' | 'caldo'
}

const SEGNALI: Record<Suggerito['segnale'], string> = {
  annuncio: 'Annuncio di lavoro', sito: 'Dal sito', recensioni: 'Dalle recensioni', cambiamento: 'Cambiamento', caldo: 'Ti ha notato',
}

async function leggi(): Promise<{ daFare: Suggerito[]; fatteOggi: number }> {
  const oggi = new Date(); oggi.setHours(0, 0, 0, 0)
  const [a, b] = await Promise.all([
    supabase.from('linkedin_persone').select('*').eq('stato', 'da_fare').order('giorno', { ascending: true }).limit(60),
    supabase.from('linkedin_persone').select('id').eq('stato', 'fatto').gte('fatto_il', oggi.toISOString()),
  ])
  if (a.error) throw new Error(a.error.message)
  return { daFare: (a.data ?? []) as Suggerito[], fatteOggi: (b.data ?? []).length }
}

async function segna(id: string, stato: 'fatto' | 'saltato' | 'da_fare') {
  const { error } = await supabase.from('linkedin_persone').update({ stato, fatto_il: stato === 'da_fare' ? null : new Date().toISOString() }).eq('id', id)
  if (error) throw new Error(error.message)
}

function Scheda({ s, fatto }: { s: Suggerito; fatto: (stato: 'fatto' | 'saltato') => void }) {
  const link = s.profilo || s.cerca
  const n = new Date()
  const oggi = `${n.getFullYear()}-${String(n.getMonth() + 1).padStart(2, '0')}-${String(n.getDate()).padStart(2, '0')}`
  const vecchia = s.giorno < oggi
  return (
    <li className="rounded-2xl border border-bordo bg-white p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-full px-2.5 py-0.5 text-[12px] font-semibold ${s.segnale === 'caldo' ? 'bg-attesa-fondo text-attesa-testo' : 'bg-noi-fondo text-noi-testo'}`}>{SEGNALI[s.segnale]}</span>
        {vecchia && <span className="text-[13px] text-tenue">da ieri</span>}
      </div>
      <h3 className="mt-2 font-titolo text-[19px] font-bold text-navy">{s.azienda}</h3>
      {(s.settore || s.citta) && <p className="text-[14px] text-tenue">{[s.settore, s.citta].filter(Boolean).join(', ')}</p>}
      <p className="mt-2 text-[15px] font-normal leading-relaxed text-inchiostro/90">{s.perche}</p>
      {s.fonte && <a href={s.fonte} target="_blank" rel="noreferrer" className="mt-1 inline-flex min-h-11 items-center gap-1 text-[14px] font-semibold text-blu-scuro">Vedi il segnale <Icona nome="esterno" className="h-4 w-4" /></a>}
      <p className="mt-1 text-[14px] text-inchiostro"><span className="font-semibold">Chi cercare:</span> {s.persona ? `${s.persona}${s.ruolo ? `, ${s.ruolo}` : ''}` : s.ruolo || 'il titolare'}</p>
      <div className="mt-3 grid grid-cols-[1fr_auto_auto] gap-2">
        {link ? (
          <a href={link} target="_blank" rel="noreferrer" className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-full bg-blu-scuro px-4 text-[14px] font-semibold text-white hover:bg-navy">
            {s.profilo ? 'Apri il profilo' : 'Cerca su LinkedIn'} <Icona nome="esterno" className="h-4 w-4" />
          </a>
        ) : <span />}
        <Bottone onClick={() => fatto('fatto')}><Icona nome="ok" className="h-4 w-4" /> Fatto</Bottone>
        <Bottone tipo="piatto" onClick={() => fatto('saltato')}>Salta</Bottone>
      </div>
    </li>
  )
}

export default function Persone() {
  const { dati, errore, caricando, rifai } = useDati(leggi)
  const ricarica = useCallback(() => { void rifai() }, [rifai])
  const { mostra, vista } = useAvviso()

  const gesto = async (s: Suggerito, stato: 'fatto' | 'saltato') => {
    try {
      await segna(s.id, stato); ricarica()
      mostra({ testo: stato === 'fatto' ? `${s.azienda}: richiesta fatta.` : `${s.azienda}: saltata.`, annulla: () => void segna(s.id, 'da_fare').then(ricarica) })
    } catch (e) { mostra({ testo: e instanceof Error ? e.message : 'Non ho salvato.' }) }
  }

  return (
    <div className="mx-auto max-w-2xl pb-10">
      <div className="mb-4 flex items-baseline justify-between">
        <h1 className="font-titolo text-[28px] font-extrabold text-navy">Persone</h1>
        {dati && <span className="text-[15px] font-semibold text-tenue">{dati.fatteOggi} su 20 oggi</span>}
      </div>
      {errore ? <Errore testo={errore} riprova={ricarica} />
        : caricando && !dati ? <Carico righe={3} />
          : !dati?.daFare.length ? <Vuoto>Per oggi hai fatto tutto. Domattina ne arrivano altre.</Vuoto>
            : <ul className="space-y-3">{dati.daFare.map((s) => <Scheda key={s.id} s={s} fatto={(st) => void gesto(s, st)} />)}</ul>}
      {vista}
    </div>
  )
}
