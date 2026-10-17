// IL TELEFONO (17/10/2026): la web app sulla Home e le notifiche.
// Dre, 17/10: «così posso scaricarlo come web app nel mio iPhone 12, e se possibile che mi invii
// anche notifiche». Un riquadro in cima a Oggi, solo finche' serve:
//   - in Safari sull'iPhone: come si mette sulla Home (le notifiche arrivano solo da li');
//   - nell'app, o sul computer, se le notifiche sono spente: «Attiva le notifiche», con cosa arrivera';
//   - se le ha bloccate: dove si riaccendono.
// Quando sono attive il riquadro non c'e'. «Non ora» lo nasconde su quel dispositivo per una settimana.
// E «Collega il telefono»: il codice per entrare nell'app senza rifare il login (src/lib/ponte.ts).
import { useEffect, useState } from 'react'
import { attiva, iphone, stato, type StatoNotifiche } from '../lib/notifiche'
import { creaCodice } from '../lib/ponte'
import { Bottone, Icona } from './pezzi'

const NON_ORA = 'sg:telefono-non-ora'
const SETTIMANA = 7 * 24 * 3600_000

function nascosto(): boolean {
  try { return Date.now() - Number(localStorage.getItem(NON_ORA) ?? 0) < SETTIMANA } catch { return false }
}

const COSA_ARRIVA = 'Ti avviso quando un lead vuole sentirti, quando un sì aspetta risposta, e quando qualcuno prenota, sposta o cancella una call. Un tocco e sei sulla sua scheda.'

export function AvvisoTelefono() {
  const [s, setS] = useState<StatoNotifiche | null>(null)
  const [via, setVia] = useState(nascosto)
  const [lavoro, setLavoro] = useState(false)
  const [problema, setProblema] = useState<string | null>(null)
  const [fatto, setFatto] = useState(false)

  useEffect(() => { void stato().then(setS).catch(() => setS('non-supportate')) }, [])

  function nonOra() {
    try { localStorage.setItem(NON_ORA, String(Date.now())) } catch { /* niente */ }
    setVia(true)
  }

  // il permesso va chiesto dentro il tocco (l'iPhone lo vuole): attiva() lo chiede per primo
  function accendi() {
    setLavoro(true); setProblema(null)
    void attiva().then((r) => {
      setLavoro(false)
      setS(r.stato)
      if (r.problema) setProblema(r.problema)
      if (r.stato === 'attive') setFatto(true)
    })
  }

  if (fatto) {
    return (
      <div role="status" className="mb-4 rounded-2xl border border-ok-bordo bg-ok-fondo px-4 py-3 text-[15px] text-ok-testo">
        <p className="flex items-center gap-2 font-bold"><Icona nome="ok" className="h-5 w-5 shrink-0" /> Notifiche attive su questo dispositivo</p>
        <p className="mt-1 text-[14px] leading-snug">Entro dieci minuti ti arriva una notifica di prova. Se non arriva, scrivimelo.</p>
      </div>
    )
  }
  if (!s || via || s === 'attive' || s === 'non-supportate') return null

  const tel = iphone()
  return (
    <section aria-labelledby="tit-telefono" className="mb-4 rounded-2xl border border-noi-bordo bg-noi-fondo px-4 py-3.5 text-inchiostro">
      {s === 'da-installare' ? (
        <>
          <h2 id="tit-telefono" className="flex items-center gap-2 text-[17px] font-bold text-noi-testo">
            <Icona nome="cellulare" className="h-5 w-5 shrink-0" /> Mettimi sulla schermata Home
          </h2>
          <p className="mt-1 text-[15px] leading-snug">Sull'iPhone le notifiche arrivano solo dall'app sulla Home.</p>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-[15px] leading-snug">
            <li>Tocca <Icona nome="condividi" className="inline h-[18px] w-[18px] align-[-3px] text-noi-testo" /> <b>Condividi</b>, nella barra di Safari.</li>
            <li>Scorri e tocca <b>Aggiungi alla schermata Home</b>, poi <b>Aggiungi</b>.</li>
            <li>Apri <b>SG Oggi</b> dalla Home: entra con Google, o con il codice qui sotto.</li>
          </ol>
          <div className="mt-3 flex flex-wrap gap-2">
            <CollegaTelefono tipo="primo" etichetta="Il codice per entrare nell'app" />
            <Bottone tipo="piatto" onClick={nonOra}>Non ora</Bottone>
          </div>
        </>
      ) : s === 'negate' ? (
        <>
          <h2 id="tit-telefono" className="flex items-center gap-2 text-[17px] font-bold text-noi-testo">
            <Icona nome="campana" className="h-5 w-5 shrink-0" /> Le notifiche sono bloccate
          </h2>
          <p className="mt-1 text-[15px] leading-snug">
            {tel
              ? <>Per riaccenderle: <b>Impostazioni</b> dell'iPhone › <b>Notifiche</b> › <b>SG Oggi</b> › <b>Consenti notifiche</b>. Poi riapri l'app.</>
              : <>Per riaccenderle: tocca l'icona a sinistra dell'indirizzo › <b>Notifiche</b> › <b>Consenti</b>, poi ricarica la pagina.</>}
          </p>
          <div className="mt-3"><Bottone tipo="piatto" onClick={nonOra}>Non ora</Bottone></div>
        </>
      ) : (
        <>
          <h2 id="tit-telefono" className="flex items-center gap-2 text-[17px] font-bold text-noi-testo">
            <Icona nome="campana" className="h-5 w-5 shrink-0" /> Attiva le notifiche
          </h2>
          <p className="mt-1 text-[15px] leading-snug">{COSA_ARRIVA} Le mail continuano ad arrivare.</p>
          {problema && <p role="alert" className="mt-2 text-[14px] text-no-testo">Non si sono attivate: {problema}</p>}
          <div className="mt-3 flex flex-wrap gap-2">
            <Bottone tipo="primo" onClick={accendi} disabled={lavoro}>{lavoro ? 'Un attimo…' : 'Attiva le notifiche'}</Bottone>
            <Bottone tipo="piatto" onClick={nonOra}>Non ora</Bottone>
          </div>
        </>
      )}
    </section>
  )
}

/** Il codice per far entrare il telefono: si chiede con un tocco, si legge grande, vale 10 minuti. */
export function CollegaTelefono({ tipo = 'secondo', etichetta = 'Collega il telefono', className = '' }: {
  tipo?: 'primo' | 'secondo' | 'piatto'; etichetta?: string; className?: string
}) {
  const [codice, setCodice] = useState<{ codice: string; minuti: number } | null>(null)
  const [lavoro, setLavoro] = useState(false)
  const [errore, setErrore] = useState<string | null>(null)

  function chiedi() {
    setLavoro(true); setErrore(null)
    void creaCodice().then(setCodice).catch((e: unknown) => setErrore(e instanceof Error ? e.message : String(e)))
      .finally(() => setLavoro(false))
  }

  if (codice) {
    return (
      <div role="status" className={`w-full rounded-xl border border-bordo bg-white px-4 py-3 ${className}`}>
        <p className="text-[14px] text-tenue">Scrivilo nell'app, su «Entra con un codice»:</p>
        <p className="mt-1 font-mono text-[32px] font-bold tracking-[0.25em] text-inchiostro" aria-label={`Codice ${codice.codice.split('').join(' ')}`}>
          {codice.codice.slice(0, 3)} {codice.codice.slice(3)}
        </p>
        <p className="text-[13px] text-tenue">Vale {codice.minuti} minuti, una volta sola.</p>
      </div>
    )
  }
  return (
    <>
      <Bottone tipo={tipo} onClick={chiedi} disabled={lavoro} className={className}>
        <Icona nome="cellulare" className="h-[18px] w-[18px]" /> {lavoro ? 'Un attimo…' : etichetta}
      </Bottone>
      {errore && <p role="alert" className="w-full text-[14px] text-no-testo">{errore}</p>}
    </>
  )
}
