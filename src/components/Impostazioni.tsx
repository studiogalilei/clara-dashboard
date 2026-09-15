import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import {
  WIDGET, RUOLI, nascosti, haAccesso, inOrdine, salvaOrdine, type Chiave, type Ruolo,
} from '../lib/widget'
import { mieiAccessi, tuttiAccessi, chiedi, decidi, vediCome, type StatoAccesso, type Accesso } from '../lib/accessi'
import { nomeSalvato, salvaNome, iniziali } from '../lib/profilo'
import { leggi as leggiPref, scrivi as scriviPref, type Chiave as ChiavePref } from '../lib/preferenze'
import { Card, TitoloCard, Micro } from './ui'
import { incassiSenzaAzienda, mensile, type Incasso } from './TuttiFoglio'
import type { VoceListino } from '../lib/preventivo'
import Firma from './Firma'
import { collegato as googleCollegato, entraConGoogle } from '../lib/google'
import { stato as statoNotifiche, attiva as attivaNotifiche, spegni as spegniNotifiche, type StatoNotifiche } from '../lib/notifiche'

// Le Impostazioni sono il tuo angolo, non una voce di menu: ci si entra dal
// proprio nome, in basso a sinistra. Dentro solo cose vere, niente
// interruttori che non cambiano niente (Dre, 3/9).

// i ruoli veri dello Studio (documento «Divisioni e responsabilita'» di Giacomo)
const NOME_RUOLO: Record<string, string> = {
  ceo: 'CEO', coordinamento: 'Coordinamento', manager: 'Marketing manager',
  specialist: 'Ad specialist', frontend: 'Frontend',
}

// SALUTE DEI DATI (Okay, 15/9): le incoerenze fra tabelle che oggi si
// scoprono solo leggendo il database a mano. Una riga per incoerenza, con
// dentro il numero e, dove esiste un posto per sistemarla, il modo di
// arrivarci. Il campo di battaglia e' sempre un'altra schermata: qui si dice
// solo quanto e' grosso il buco.
interface Incoerenza { chiave: string; testo: string; quanti: number; vai?: () => void }
const CAMPI_INCASSO = 'id,genere,importo,valuta,stato,quando,ricorrenza,metodo,prossimo_il,fine_il,cliente_nome,prospect_id'
// «cliente» e' la stessa cosa che legge il Foglio (regole.ts eCliente, piu'
// le prove): un cliente in prova senza canone e' un buco come gli altri
const CLIENTI = 'and(fuori.eq.true,pipeline_stage.in.(cliente,prova)),and(fuori.eq.false,stage.eq.cliente)'

interface Props {
  nome: string
  email: string
  demo: boolean
  ruolo: Ruolo                 // quello vero, dal database (App lo legge da profili)
  ruoloVero?: string           // manager, specialist, frontend: il nome vero del ruolo
  onCambio: () => void
  onNumeri?: () => void
  onWidget?: () => void
}

function Interruttore({ acceso, onClick, etichetta }: { acceso: boolean; onClick: () => void; etichetta: string }) {
  return (
    <button
      onClick={onClick}
      aria-label={etichetta}
      className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${acceso ? 'bg-navy' : 'bg-bordo'}`}
    >
      <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all ${acceso ? 'left-[22px]' : 'left-0.5'}`} />
    </button>
  )
}



export default function Impostazioni({ nome, email, demo, ruolo, ruoloVero = ruolo, onCambio, onNumeri, onWidget }: Props) {
  const [spenti] = useState<Chiave[]>(nascosti)
  // i widget a richiesta (Dre, 11/9): i miei, e per i ceo la mappa di tutti
  const [miei, setMiei] = useState<Partial<Record<Chiave, StatoAccesso>>>({})
  const [mappa, setMappa] = useState<Accesso[]>([])
  const [persone, setPersone] = useState<Array<{ id: string; nome: string | null; ruolo: string }>>([])
  const [accessoEsito, setAccessoEsito] = useState<string | null>(null)
  useEffect(() => {
    if (demo) return
    void mieiAccessi().then(setMiei)
    if (ruolo === 'ceo') {
      void tuttiAccessi().then(setMappa)
      void supabase.from('profili').select('id,nome,ruolo').then(({ data }) => setPersone((data as typeof persone) ?? []))
    }
  }, [demo, ruolo])
  async function chiediAccesso(w: Chiave) {
    const err = await chiedi(w, bozzaNome || nome)
    setAccessoEsito(err ? 'Richiesta non partita: ' + err : 'Richiesta mandata a Dre e Giacomo')
    setMiei(await mieiAccessi())
    setTimeout(() => setAccessoEsito(null), 3000)
  }
  async function concedi(user_id: string, w: Chiave, si: boolean) {
    const err = await decidi(user_id, w, si)
    if (err) { setAccessoEsito('Non salvato: ' + err); return }
    setMappa(await tuttiAccessi())
  }
  // la card la vedono i ceo e chi ha i Numeri: e' lo stesso mestiere, guardare
  // se i dati tornano prima di fidarsi dei totali
  const vedeSalute = ruolo === 'ceo' || miei['analytics'] === 'approvato'

  // IL LISTINO (15/9): i prezzi cambiano, e finche' si cambiavano solo nel
  // database restavano sbagliati. Una voce a zero euro e' finita in un
  // preventivo vero (QA del 14/9): adesso si sistema da qui, in cinque
  // secondi, da chi decide i prezzi.
  const [listino, setListino] = useState<VoceListino[] | null>(null)
  const [salvata, setSalvata] = useState<number | null>(null)
  useEffect(() => {
    if (ruolo !== 'ceo') return
    void supabase.from('listino').select('*').order('ordine').then(({ data }) => setListino((data as VoceListino[]) ?? []))
  }, [ruolo])

  async function scriviVoce(v: VoceListino, patch: Partial<VoceListino>) {
    const { data } = await supabase.from('listino').update(patch).eq('id', v.id).select().single()
    if (!data) return
    setListino((l) => (l ?? []).map((x) => (x.id === v.id ? (data as VoceListino) : x)))
    setSalvata(v.id)
    setTimeout(() => setSalvata((k) => (k === v.id ? null : k)), 1600)
  }

  async function nuovaVoce() {
    const { data } = await supabase.from('listino').insert({
      nome: 'Voce nuova', prezzo: 0, ricorrenza: 'una_tantum', linea: 'marketing',
      ordine: ((listino ?? []).at(-1)?.ordine ?? 0) + 1, attivo: false,
    }).select().single()
    if (data) setListino((l) => [...(l ?? []), data as VoceListino])
  }
  const [salute, setSalute] = useState<Incoerenza[] | null>(null)
  useEffect(() => {
    if (!vedeSalute) return
    let vivo = true
    const apriPosta = () => window.dispatchEvent(new CustomEvent('clara:apri-posta'))
    const apriPreventivi = () => window.dispatchEvent(new CustomEvent('preventivo:nuovo'))
    const treGiorniFa = new Date(Date.now() - 3 * 86400e3).toISOString()
    void Promise.all([
      supabase.from('incassi').select('prospect_id,importo,ricorrenza').eq('genere', 'abbonamento')
        .in('stato', ['active', 'trialing']).not('prospect_id', 'is', null).limit(500),
      supabase.from('prospects').select('id,canone').or(CLIENTI).limit(2000),
      supabase.from('progetti').select('id', { count: 'exact', head: true }).is('prospect_id', null),
      supabase.from('proposte').select('id', { count: 'exact', head: true }).eq('stato', 'aperta').lte('at', treGiorniFa),
      supabase.from('incassi').select(CAMPI_INCASSO).is('prospect_id', null).limit(500),
    ]).then(([abb, cli, prog, prop, inc]) => {
      if (!vivo) return
      const clienti = (cli.data as Array<{ id: string; canone: number | null }>) ?? []
      const canoneDi = new Map(clienti.map((c) => [c.id, c.canone]))
      // il canone nullo ha gia' la sua riga qui sotto: contarlo anche come
      // «diverso da Stripe» sarebbe lo stesso buco contato due volte
      const diversi = ((abb.data as Array<{ prospect_id: string; importo: number; ricorrenza: string | null }>) ?? [])
        .filter((i) => {
          const c = canoneDi.get(i.prospect_id)
          return c != null && Math.round(Number(c)) !== Math.round(mensile(i as Incasso))
        }).length
      setSalute([
        { chiave: 'canone-stripe', testo: 'Clienti col canone diverso da Stripe', quanti: diversi },
        { chiave: 'canone-vuoto', testo: 'Clienti senza canone', quanti: clienti.filter((c) => c.canone == null).length },
        { chiave: 'progetti', testo: 'Progetti senza cliente', quanti: prog.count ?? 0 },
        { chiave: 'proposte', testo: 'Proposte di Clara aperte da più di 3 giorni', quanti: prop.count ?? 0, vai: apriPosta },
        { chiave: 'incassi', testo: 'Incassi senza azienda', quanti: incassiSenzaAzienda((inc.data as Incasso[]) ?? []).length, vai: apriPreventivi },
      ])
    })
    return () => { vivo = false }
  }, [vedeSalute])

  const [bozzaNome, setBozzaNome] = useState(nomeSalvato() || nome)
  const [salvato, setSalvato] = useState(false)
  // il ponte verso Obsidian: qui dentro sta la spina, non il gesto (Dre, 3/9).
  // Se il nome del vault e' vuoto il ponte e' spento in tutta l'app.
  const [vault, setVault] = useState(() => leggiPref('obsidian-vault'))
  const [vaultSalvato, setVaultSalvato] = useState(false)
  // le notifiche sul telefono: il permesso lo da' il browser, noi salviamo l'indirizzo
  const [notifiche, setNotifiche] = useState<StatoNotifiche | null>(null)
  const [google, setGoogle] = useState<boolean | null>(null)
  const [nuovaPassword, setNuovaPassword] = useState('')
  const [passwordEsito, setPasswordEsito] = useState<string | null>(null)
  const [notificheProblema, setNotificheProblema] = useState<string | null>(null)
  useEffect(() => { void statoNotifiche().then(setNotifiche); if (!demo) void googleCollegato().then(setGoogle) }, [demo])
  const [vistaTask, setVistaTask] = useState(() => leggiPref('task-vista', 'ongo'))
  // «Pipeline si apre su…» e' una scelta sola, ma dietro ci sono due
  // preferenze: quale tab (bacheca o foglio) e, dentro la bacheca, quale
  // forma (bacheca o elenco). Prima erano due interruttori scollegati.
  const [vistaTutti, setVistaTutti] = useState(() =>
    leggiPref('tutti-modo', 'bacheca') === 'foglio' ? 'foglio' : leggiPref('tutti-vista', 'board'))
  function apriPipelineCome(v: string) {
    setVistaTutti(v)
    scriviPref('tutti-modo', v === 'foglio' ? 'foglio' : 'bacheca')
    if (v !== 'foglio') scriviPref('tutti-vista', v)
  }
  const [lista, setLista] = useState(() => inOrdine(WIDGET))
  const [presa, setPresa] = useState<Chiave | null>(null)
  const [sopra, setSopra] = useState<Chiave | null>(null)

  // trascina per riordinare: l'ordine vale per il menu, non solo per qui
  function lascia(sopra: Chiave) {
    if (!presa || presa === sopra) return
    const n = [...lista]
    const da = n.findIndex((w) => w.chiave === presa)
    const a = n.findIndex((w) => w.chiave === sopra)
    const [mosso] = n.splice(da, 1)
    n.splice(da < a ? a - 1 : a, 0, mosso)   // come in Oggi: gli indici scalano
    setLista(n)
    salvaOrdine(n.map((w) => w.chiave))
    setPresa(null)
    setSopra(null)
    onCambio()
  }

  // col dito il trascinamento HTML non parte: le frecce fanno la stessa cosa
  // e sono l'unico modo di riordinare da telefono (QA Dre, 15/9)
  function sposta(chiave: Chiave, verso: -1 | 1) {
    const n = [...lista]
    const da = n.findIndex((w) => w.chiave === chiave)
    const a = da + verso
    if (da < 0 || a < 0 || a >= n.length) return
    const [mosso] = n.splice(da, 1)
    n.splice(a, 0, mosso)
    setLista(n)
    salvaOrdine(n.map((w) => w.chiave))
    onCambio()
  }

  function scriviNome() {
    salvaNome(bozzaNome)
    setSalvato(true)
    setTimeout(() => setSalvato(false), 2000)
    onCambio()
  }

  function preferenza(chiave: ChiavePref, valore: string, set: (v: string) => void) {
    scriviPref(chiave, valore)
    set(valore); onCambio()
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4 pb-24 sm:pb-8">

      {/* ── PROFILO ────────────────────────────────────────────── */}
      <Card className="p-5">
        <TitoloCard>Profilo</TitoloCard>
        <div className="mt-2 flex items-center gap-4">
          <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-navy text-lg font-bold text-white">
            {iniziali(bozzaNome || nome)}
          </span>
          <div className="min-w-0 flex-1">
            <label className="block">
              <Micro>Come ti chiami</Micro>
              <input
                value={bozzaNome}
                onChange={(e) => setBozzaNome(e.target.value)}
                onBlur={scriviNome}
                onKeyDown={(e) => e.key === 'Enter' && scriviNome()}
                placeholder="Nome e cognome"
                className="mt-0.5 w-full rounded-lg border border-bordo px-3 py-2 text-sm outline-none focus:border-blu"
              />
            </label>
            <p className="mt-1.5 text-xs text-tenue">
              {demo ? 'Stai guardando la demo, con dati finti' : email}
              {salvato && <span className="ml-2 font-semibold text-green-700">salvato</span>}
            </p>
          </div>
        </div>

        <div className="mt-4 border-t border-velo pt-3">
          <Micro>Ruolo</Micro>
          <p className="mt-1 text-sm font-semibold">{NOME_RUOLO[ruoloVero] ?? RUOLI.find(([r]) => r === ruolo)?.[1] ?? ruolo}</p>
        </div>
      </Card>

      {/* ── GOOGLE (11/9): Drive, Chat e Calendar a nome tuo ─────── */}
      {!demo && (
        <Card className="p-5">
          <TitoloCard>Google</TitoloCard>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            {google === null ? <span className="text-sm text-spento">controllo…</span>
              : google ? <span className="text-sm font-semibold text-green-800">Collegato</span>
              : <span className="text-sm text-tenue">Non ancora collegato.</span>}
            <button onClick={() => void entraConGoogle()} className="rounded-full border border-bordo px-3.5 py-1.5 text-xs font-bold text-navy hover:border-navy">
              {google ? 'Rinnova il collegamento' : 'Collega Google'}
            </button>
          </div>
        </Card>
      )}

      {/* ── LA FIRMA (Dre, 11/9) ───────────────────────────────── */}
      {!demo && <Firma ceo={ruolo === 'ceo'} />}

      {/* ── WIDGET (Dre, 11/9): il catalogo, e la richiesta ───────── */}
      <Card>
        <header className="flex items-baseline justify-between gap-2 border-b border-velo px-4 py-3">
          <TitoloCard>Widget</TitoloCard>
          <Micro>l'ordine è quello del menu</Micro>
        </header>
        {accessoEsito && <p className="border-b border-velo bg-velo px-4 py-2 text-xs font-semibold">{accessoEsito}</p>}

        {lista.map((w) => {
          const acceso = w.fisso || !spenti.includes(w.chiave)
          const stato = miei[w.chiave]
          const mio = haAccesso(w, ruolo, new Set(stato === 'approvato' ? [w.chiave] : []))
          return (
            <div
              key={w.chiave}
              draggable
              onDragStart={(e) => {
                setPresa(w.chiave)
                e.dataTransfer.setData('text/plain', w.chiave)
                e.dataTransfer.effectAllowed = 'move'
              }}
              onDragOver={(e) => { e.preventDefault(); setSopra(w.chiave) }}
              onDrop={(e) => { e.preventDefault(); lascia(w.chiave) }}
              onDragEnd={() => { setPresa(null); setSopra(null) }}
              className={`border-b border-velo px-4 py-3 last:border-0 ${
                presa === w.chiave ? 'bg-velo opacity-60' : ''
              } ${sopra === w.chiave && presa && presa !== w.chiave ? 'border-t-2 border-t-blu' : ''}`}
            >
              <div className="flex items-center gap-3">
                <span className="flex shrink-0 flex-col">
                  <button onClick={() => sposta(w.chiave, -1)} aria-label={`Sposta ${w.nome} in su`}
                          className="text-spento hover:text-navy disabled:opacity-20" disabled={lista[0]?.chiave === w.chiave}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" className="h-3.5 w-3.5"><path d="M6 15l6-6 6 6" /></svg>
                  </button>
                  <button onClick={() => sposta(w.chiave, 1)} aria-label={`Sposta ${w.nome} in giù`}
                          className="text-spento hover:text-navy disabled:opacity-20" disabled={lista[lista.length - 1]?.chiave === w.chiave}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" className="h-3.5 w-3.5"><path d="M6 9l6 6 6-6" /></svg>
                  </button>
                </span>
                {/* la stessa icona del menu: i Documenti qui erano un lucchetto
                    e nel menu il marchio (QA browser, 15/9) */}
                {w.immagine ? (
                  <span aria-hidden
                        className={`inline-block h-4 w-4 shrink-0 ${acceso && mio ? 'text-navy' : 'text-spento'}`}
                        style={{ backgroundColor: 'currentColor', WebkitMaskImage: `url(${import.meta.env.BASE_URL}${w.immagine})`, maskImage: `url(${import.meta.env.BASE_URL}${w.immagine})`, WebkitMaskSize: 'contain', maskSize: 'contain', WebkitMaskRepeat: 'no-repeat', maskRepeat: 'no-repeat', WebkitMaskPosition: 'center', maskPosition: 'center' }} />
                ) : (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
                       className={`h-4 w-4 shrink-0 ${acceso && mio ? 'text-navy' : 'text-spento'}`}>
                    <path d={w.icona} strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold">{w.nome}</p>
                  <p className="truncate text-xs text-tenue">{w.cosa}</p>
                </div>
                {w.base && (w.ruoli.length > 1 || ruolo === 'ceo') ? (
                  <Micro>per tutti</Micro>
                ) : ruolo === 'ceo' ? (
                  <Micro>tuo</Micro>
                ) : stato === 'approvato' ? (
                  <Micro>concesso</Micro>
                ) : stato === 'richiesto' ? (
                  <Micro>richiesta inviata</Micro>
                ) : (
                  <button onClick={() => void chiediAccesso(w.chiave)}
                          className="shrink-0 rounded-full border border-bordo px-3 py-1 text-[11px] font-bold text-navy hover:border-navy">
                    {stato === 'negato' ? 'Chiedi di nuovo' : "Chiedi l'accesso"}
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </Card>

      {/* ── VEDI COME (solo ceo, 12/9): il Workspace nei panni di una persona ── */}
      {ruolo === 'ceo' && !demo && persone.length > 0 && (
        <Card className="p-5">
          <TitoloCard>Vedi come</TitoloCard>
          <p className="mt-1 text-xs text-tenue">Menu, aziende, chat e task diventano i suoi. In alto compare la striscia per tornare a te.</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {persone.filter((p) => p.ruolo !== 'ceo').map((p) => (
              <button key={p.id} onClick={() => { void vediCome(p.id).then(() => window.location.reload()) }}
                      className="rounded-full border border-bordo px-3.5 py-1.5 text-xs font-bold text-navy hover:border-navy">
                {p.nome ?? p.id.slice(0, 8)}
              </button>
            ))}
          </div>
        </Card>
      )}

      {/* ── CHI HA COSA (solo ceo): la mappa, e si da' o si toglie da qui ── */}
      {ruolo === 'ceo' && !demo && persone.some((p) => p.ruolo !== 'ceo') && (
        <Card>
          <header className="border-b border-velo px-4 py-3">
            <TitoloCard>Chi ha cosa</TitoloCard>
          </header>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="text-left text-[11px] font-bold uppercase tracking-wide text-tenue">
                  <th className="px-4 py-2">Persona</th>
                  {WIDGET.filter((w) => !w.base).map((w) => <th key={w.chiave} className="px-3 py-2">{w.nome}</th>)}
                </tr>
              </thead>
              <tbody>
                {persone.filter((p) => p.ruolo !== 'ceo').map((p) => (
                  <tr key={p.id} className="border-t border-velo">
                    <td className="px-4 py-2 font-semibold">{p.nome ?? p.id.slice(0, 8)}</td>
                    {WIDGET.filter((w) => !w.base).map((w) => {
                      const r = mappa.find((a) => a.user_id === p.id && a.widget === w.chiave)
                      const ha = r?.stato === 'approvato'
                      return (
                        <td key={w.chiave} className="px-3 py-2">
                          <div className="flex items-center gap-2">
                            <Interruttore acceso={ha} etichetta={`${ha ? 'Togli' : 'Dai'} ${w.nome} a ${p.nome ?? ''}`}
                                          onClick={() => void concedi(p.id, w.chiave, !ha)} />
                            {r?.stato === 'richiesto' && <span className="text-[11px] font-semibold text-amber-800">chiesto</span>}
                          </div>
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ── COME SI APRE ───────────────────────────────────────── */}
      <Card>
        <header className="border-b border-velo px-4 py-3">
          <TitoloCard>Come si apre</TitoloCard>
        </header>
        <div className="flex items-center gap-3 border-b border-velo px-4 py-3">
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold">Le task in Oggi</p>
          </div>
          <div className="flex shrink-0 overflow-hidden rounded-full border border-bordo">
            {[['ongo', 'On go'], ['big', 'Questa settimana']].map(([v, etichetta]) => (
              <button key={v} onClick={() => preferenza('task-vista', v, setVistaTask)}
                className={`px-3 py-1 text-xs font-bold ${vistaTask === v ? 'bg-blu text-white' : 'bg-white text-tenue'}`}>
                {etichetta}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-3 px-4 py-3">
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold">Pipeline</p>
          </div>
          <div className="flex shrink-0 overflow-hidden rounded-full border border-bordo">
            {[['board', 'Bacheca'], ['elenco', 'Elenco'], ['foglio', 'Foglio']].map(([v, etichetta]) => (
              <button key={v} onClick={() => apriPipelineCome(v)}
                className={`px-3 py-1 text-xs font-bold ${vistaTutti === v ? 'bg-blu text-white' : 'bg-white text-tenue'}`}>
                {etichetta}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* ── OBSIDIAN ───────────────────────────────────────────── */}
      <Card>
        <header className="border-b border-velo px-4 py-3">
          <TitoloCard>Obsidian</TitoloCard>
        </header>
        <div className="px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <input
              value={vault}
              onChange={(e) => { setVault(e.target.value); setVaultSalvato(false) }}
              onBlur={() => { scriviPref('obsidian-vault', vault.trim()); setVaultSalvato(true); onCambio() }}
              onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur() }}
              placeholder="Nome del vault"
              className="min-w-[200px] flex-1 rounded-lg border border-bordo px-3 py-2 text-sm outline-none focus:border-blu"
            />
            <a
              href={vault.trim() ? `obsidian://open?vault=${encodeURIComponent(vault.trim())}` : undefined}
              aria-disabled={!vault.trim()}
              className={`shrink-0 rounded-full border border-bordo px-4 py-2 text-sm font-semibold ${
                vault.trim() ? 'text-tenue hover:border-navy hover:text-navy' : 'pointer-events-none opacity-30'
              }`}
            >
              Aprilo
            </a>
          </div>
          <p className="mt-1.5 text-xs text-spento">
            {vault.trim()
              ? <>Sulle schede compare «cerca in Obsidian», sotto i puntini{vaultSalvato && <span className="ml-2 font-semibold text-green-700">salvato</span>}</>
              : 'Spento: senza il nome del vault i collegamenti non saprebbero dove andare'}
          </p>
        </div>
      </Card>

      {/* la password: al primo accesso ognuno si mette la sua (accessi creati il 9/9) */}
      {!demo && (
        <Card>
          <header className="border-b border-velo px-4 py-3">
            <TitoloCard>Password</TitoloCard>
          </header>
          <div className="flex flex-wrap items-center gap-2 px-4 py-3">
            <input
              type="password"
              value={nuovaPassword}
              onChange={(e) => { setNuovaPassword(e.target.value); setPasswordEsito(null) }}
              placeholder="Nuova password (almeno 8 caratteri)"
              autoComplete="new-password"
              className="min-w-[240px] flex-1 rounded-lg border border-bordo px-3 py-2 text-sm outline-none focus:border-blu"
            />
            <button
              type="button"
              disabled={nuovaPassword.length < 8}
              onClick={async () => {
                const { error } = await supabase.auth.updateUser({ password: nuovaPassword })
                setPasswordEsito(error ? 'Non è cambiata: ' + error.message : 'Password cambiata')
                if (!error) setNuovaPassword('')
              }}
              className="rounded-full bg-blu px-4 py-2 text-sm font-semibold text-white hover:bg-blu-scuro disabled:opacity-40"
            >
              Cambia
            </button>
            {passwordEsito && <p className={`w-full text-xs ${passwordEsito.startsWith('Non') ? 'text-red-700' : 'text-green-700'}`}>{passwordEsito}</p>}
          </div>
        </Card>
      )}

      {/* Numeri e Widget stanno qui dentro (intervista 9/9): non sono lavoro di tutti i giorni */}
      {ruolo === 'ceo' && (
      <Card>
        <header className="border-b border-velo px-4 py-3">
          <TitoloCard>Strumenti</TitoloCard>
        </header>
        <div className="divide-y divide-velo">
          <button onClick={onNumeri} className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-semibold hover:bg-velo/50">
            <span>Numeri<span className="ml-2 font-normal text-tenue">funnel, ricorrente, canali</span></span><span className="text-spento">›</span>
          </button>
          <button onClick={onWidget} className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-semibold hover:bg-velo/50">
            <span>Widget e istruzioni<span className="ml-2 font-normal text-tenue">cosa sa fare Clara, e i collegamenti</span></span><span className="text-spento">›</span>
          </button>
        </div>
      </Card>
      )}

      {/* IL LISTINO: i prezzi che finiscono nei preventivi */}
      {ruolo === 'ceo' && listino && (
        <Card>
          <header className="flex items-baseline justify-between gap-2 border-b border-velo px-4 py-3">
            <TitoloCard>Listino</TitoloCard>
            <button onClick={() => void nuovaVoce()} className="text-xs font-bold text-blu hover:underline">+ Aggiungi una voce</button>
          </header>
          {listino.length === 0 && <p className="px-4 py-4 text-sm text-spento">Nessuna voce.</p>}
          {listino.map((v) => (
            <div key={v.id} className="flex flex-wrap items-center gap-2 border-b border-velo px-4 py-2.5 last:border-0">
              <input
                value={v.nome}
                onChange={(e) => setListino((l) => (l ?? []).map((x) => (x.id === v.id ? { ...x, nome: e.target.value } : x)))}
                onBlur={(e) => { if (e.target.value !== v.nome) void scriviVoce(v, { nome: e.target.value }) }}
                className="min-w-[180px] flex-1 rounded-lg bg-transparent px-2 py-1 text-sm font-semibold outline-none hover:bg-velo focus:bg-velo"
              />
              <label className={`flex items-center gap-1 rounded-lg border px-2 py-1 text-sm ${v.prezzo > 0 ? 'border-bordo' : 'border-amber-300 bg-amber-50'}`}>
                <input
                  type="number" min={0} value={v.prezzo}
                  onChange={(e) => setListino((l) => (l ?? []).map((x) => (x.id === v.id ? { ...x, prezzo: Math.max(0, Number(e.target.value) || 0) } : x)))}
                  onBlur={(e) => { const n = Math.max(0, Number(e.target.value) || 0); if (n !== v.prezzo) void scriviVoce(v, { prezzo: n }) }}
                  className="w-20 bg-transparent text-right font-bold tabular-nums outline-none"
                />
                <span className="text-tenue">€</span>
              </label>
              <div className="flex overflow-hidden rounded-full border border-bordo text-[11px] font-semibold">
                {(['una_tantum', 'mese'] as const).map((r) => (
                  <button key={r} onClick={() => void scriviVoce(v, { ricorrenza: r })}
                          className={`px-2.5 py-1 ${v.ricorrenza === r ? 'bg-blu text-white' : 'bg-white text-tenue hover:bg-velo'}`}>
                    {r === 'mese' ? 'al mese' : 'una tantum'}
                  </button>
                ))}
              </div>
              <button onClick={() => void scriviVoce(v, { attivo: !v.attivo })}
                      className={`rounded-full px-3 py-1 text-[11px] font-bold ${v.attivo ? 'bg-green-100 text-green-900' : 'bg-velo text-spento'}`}>
                {v.attivo ? 'Nel listino' : 'Spenta'}
              </button>
              {salvata === v.id && <span className="text-[11px] font-semibold text-green-700">salvato</span>}
            </div>
          ))}
        </Card>
      )}

      {vedeSalute && salute && (
        <Card>
          <header className="border-b border-velo px-4 py-3">
            <TitoloCard>Salute dei dati</TitoloCard>
          </header>
          <div className="divide-y divide-velo">
            {salute.filter((x) => x.quanti > 0).length === 0 ? (
              <p className="px-4 py-3 text-sm text-spento">Tutto in ordine.</p>
            ) : salute.filter((x) => x.quanti > 0).map((x) => {
              const dentro = (
                <>
                  <span className="min-w-0 flex-1 text-sm font-semibold">{x.testo}</span>
                  <span className="shrink-0 text-sm font-extrabold tabular-nums">{x.quanti}</span>
                </>
              )
              return x.vai ? (
                <button key={x.chiave} onClick={x.vai} className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-velo/50">
                  {dentro}<span className="shrink-0 text-spento">›</span>
                </button>
              ) : (
                <div key={x.chiave} className="flex items-center gap-3 px-4 py-3">
                  {dentro}<span className="w-2 shrink-0" />
                </div>
              )
            })}
          </div>
        </Card>
      )}

      <Card>
        <header className="border-b border-velo px-4 py-3">
          <TitoloCard>Notifiche</TitoloCard>
        </header>
        <div className="px-4 py-3">
          <div className="flex flex-wrap items-center gap-3">
            <p className="min-w-[200px] flex-1 text-sm">
              {notifiche === 'attive' && 'Attive su questo dispositivo: quando ci sono bozze da approvare, Clara ti avvisa qui.'}
              {notifiche === 'spente' && 'Spente. Accendile e Clara ti avvisa quando c\'è qualcosa da approvare.'}
              {notifiche === 'negate' && 'Il browser le ha bloccate: si riaccendono dalle impostazioni del sito.'}
              {notifiche === 'da-installare' && 'Su iPhone prima aggiungi SG Workspace alla schermata Home: condividi, poi «Aggiungi alla schermata Home», e riapri da lì.'}
              {notifiche === 'non-supportate' && 'Questo browser non le supporta.'}
              {notifiche === null && '…'}
            </p>
            {(notifiche === 'spente' || notifiche === 'attive') && (
              <button
                type="button"
                onClick={async () => {
                  setNotificheProblema(null)
                  if (notifiche === 'attive') { setNotifiche(await spegniNotifiche()); return }
                  const r = await attivaNotifiche()
                  setNotifiche(r.stato); setNotificheProblema(r.problema ?? null)
                }}
                className="shrink-0 rounded-full border border-bordo px-4 py-2 text-sm font-semibold text-tenue hover:border-navy hover:text-navy"
              >
                {notifiche === 'attive' ? 'Spegni' : 'Attiva le notifiche'}
              </button>
            )}
          </div>
          {notificheProblema && <p className="mt-1.5 text-xs text-red-700">Non si sono accese: {notificheProblema}</p>}
        </div>
      </Card>

      {!demo && (
        <button
          onClick={() => supabase.auth.signOut()}
          className="w-full rounded-2xl border border-bordo bg-white px-4 py-3 text-sm font-semibold text-tenue transition-colors hover:border-red-300 hover:text-red-700"
        >
          Esci
        </button>
      )}
    </div>
  )
}
