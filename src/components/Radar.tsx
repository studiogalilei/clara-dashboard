import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { PIPELINE_LABEL, type Prospect, type AgendaItem } from '../lib/types'
import { Dot, Card, daysAgo, fmtDateShort, fmtOra } from './ui'
import { VIVI, oggi, giorno, GIORNI_FOLLOWUP } from '../lib/regole'

// Il radar della home: la riga dei 4 numeri (la scura e' «Da fare oggi»,
// e le call di OGGI vivono li' dentro), la card «Prossima» con il primo
// evento futuro, e gli Avvisi. Regole della sintesi 31/8: mai lo stesso
// evento in due punti; zero eventi in settimana = zero interfaccia.

const FERMO_DAYS = 30


interface Avviso {
  peso: number
  tono: 'fermo' | 'attesa'
  testo: string
  id: string | null
}

interface Props {
  onOpen: (id: string) => void
  onOggi?: () => void
  onCalendario?: () => void
  // Dre (9/9): in alto la prossima call, sotto le task, in fondo gli avvisi.
  // Il radar si divide in due: la parte «call» sta sopra la lista, «avvisi» sotto.
  parte?: 'call' | 'avvisi' | 'tutto'
}

interface Voce {
  testo: string
  quando: string
  prospect_id: string | null
}

function fraQuanto(at: string): string {
  const ms = new Date(at).getTime() - Date.now()
  const ore = Math.round(ms / 3600e3)
  if (ore < 24) return `fra ${ore} or${ore === 1 ? 'a' : 'e'}`
  const gg = Math.round(ms / 86400e3)
  if (gg === 1) return 'domani'
  return `fra ${gg} giorni`
}

export default function Radar({ onOpen, onOggi, onCalendario, parte = 'tutto' }: Props) {
  const [avvisi, setAvvisi] = useState<Avviso[]>([])
  const [prossimo, setProssimo] = useState<AgendaItem | null>(null)
  const [settimana, setSettimana] = useState(0)
  const [aggiornato, setAggiornato] = useState<string | null>(null)
  const [pronto, setPronto] = useState(false)
  const [callDiOggi, setCallDiOggi] = useState<Voce[]>([])
  const [bozze, setBozze] = useState(0)
  const [domande, setDomande] = useState(0)
  const [taskOggi, setTaskOggi] = useState<Array<{ id: number; titolo: string; scadenza: string }>>([])
  // le prove che finiscono entro due settimane: e' il momento di riaccordarsi (Dre, 9/9)
  const [proveInScadenza, setProveInScadenza] = useState<Array<{ id: string; nome: string; fine: string }>>([])
  const [tuttiAvvisi, setTuttiAvvisi] = useState(false)

  useEffect(() => {
    const today = oggi()
    const adesso = new Date().toISOString()
    const fraSette = new Date(Date.now() + 7 * 86400e3).toISOString()

    supabase
      .from('sync_runs')
      .select('*')
      .order('finished_at', { ascending: false })
      .limit(1)
      .then(({ data }) => {
        const run = (data as Array<{ finished_at: string | null }> | null)?.[0]
        if (run?.finished_at) setAggiornato(run.finished_at)
      })

    // «cosa devo fare oggi» la decide regole.ts, per tutti. Prima ogni
    // schermata rifaceva le sue query con filtri e tetti diversi, e i due
    // numeri che stanno in testata e qui sotto non tornavano mai (4/9)
    // le cose che aspettano DRE oggi: le bozze da approvare nella posta di
    // Clara, e le sue task in scadenza. La coda delle risposte non sta piu'
    // qui: da oggi la gestisce Clara con le bozze (Dre, 7/9)
    supabase.from('proposte').select('tipo').eq('stato', 'aperta').limit(200)
      .then(({ data }) => {
        const l = (data as Array<{ tipo: string }>) ?? []
        setBozze(l.filter((p) => p.tipo === 'risposta' || p.tipo === 'umano').length)
        setDomande(l.filter((p) => p.tipo !== 'risposta' && p.tipo !== 'umano').length)
      })
    supabase.from('prospects').select('id,company,name,email,prova_fine').eq('fuori', true).eq('pipeline_stage', 'prova')
      .not('prova_fine', 'is', null).lte('prova_fine', new Date(Date.now() + 14 * 86400e3).toISOString().slice(0, 10))
      .order('prova_fine', { ascending: true }).limit(20)
      .then(({ data }) => setProveInScadenza(((data as Array<{ id: string; company: string | null; name: string | null; email: string; prova_fine: string }>) ?? [])
        .map((p) => ({ id: p.id, nome: p.company || p.name || p.email, fine: p.prova_fine }))))
    supabase.auth.getSession().then(({ data: sess }) => {
      const io = sess.session?.user?.id
      const mie = io ? `owner.is.null,owner.eq.${io}` : 'owner.is.null'
      supabase.from('task').select('id,titolo,scadenza').eq('fatta', false).neq('stato', 'proposta')
        .or(mie).not('scadenza', 'is', null).lte('scadenza', today)
        .order('scadenza', { ascending: true }).limit(20)
        .then(({ data }) => { setTaskOggi((data as Array<{ id: number; titolo: string; scadenza: string }>) ?? []); setPronto(true) })
    })

    Promise.all([
      supabase
        .from('agenda')
        .select('*')
        .gte('at', new Date(Date.now() - 14 * 86400e3).toISOString())
        .order('at', { ascending: true })
        .limit(50),
      supabase
        .from('prospects')
        .select('*')
        .in('stage', ['analisi_inviata', 'in_follow_up'])
        .eq('no_followup', false)
        .eq('awaiting_us', false)
        .eq('fuori', false)
        .or(VIVI)
        .order('analysis_sent_at', { ascending: true, nullsFirst: false })
        .limit(1000),
      supabase
        .from('prospects')
        .select('*')
        .eq('fuori', true)
        .in('pipeline_stage', ['conoscitiva', 'tecnica', 'avvio', 'prova']),
      supabase
        .from('prospects')
        .select('*')
        .eq('fuori', false)
        .in('classificazione', ['rinvio', 'ooo'])
        .eq('no_followup', false)
        .order('last_reply_at', { ascending: false, nullsFirst: false })
        .limit(1000),
    ]).then(([ag, fu, pi, ri]) => {
      const eventi = (ag.data as AgendaItem[]) ?? []
      const futuri = eventi.filter((a) => a.at >= adesso)
      const passati = eventi.filter((a) => a.at < adesso)
      const inPipeline = (pi.data as Prospect[]) ?? []

      // oggi vive nel ticker; il primo dei giorni dopo = «Prossima»
      setProssimo(futuri.find((a) => giorno(a.at) > today) ?? null)
      setSettimana(futuri.filter((a) => a.at <= fraSette).length)

      const dovuti = ((fu.data as Prospect[]) ?? []).filter((p) => {
        if (p.followup_due) return p.followup_due.slice(0, 10) <= today
        const d = daysAgo(p.analysis_sent_at)
        return d !== null && d >= GIORNI_FOLLOWUP
      })
      // le call di oggi: quelle stanno nell'agenda, non nella coda
      setCallDiOggi(futuri.filter((a) => a.at.slice(0, 10) === today)
        .map((a) => ({ testo: a.titolo, quando: fmtOra(a.at), prospect_id: a.prospect_id })))

      const nuovi: Avviso[] = []
      for (const a of passati) {
        if (!a.prospect_id) continue
        const p = inPipeline.find((x) => x.id === a.prospect_id)
        if (p && (!p.next_action_date || p.next_action_date < today)) {
          nuovi.push({
            peso: 1, tono: 'fermo',
            testo: `${p.company || p.name || p.email}: la call del ${fmtDateShort(a.at)} è passata e la scheda è ferma`,
            id: p.id,
          })
        }
      }
      for (const p of (ri.data as Prospect[]) ?? []) {
        if (!p.next_action_date && !p.followup_due && !p.ooo_until) {
          nuovi.push({
            peso: 2, tono: 'attesa',
            testo: `${p.company || p.name || p.email}: in attesa senza una data`,
            id: p.id,
          })
        }
      }
      const fermi = dovuti.filter((p) => (daysAgo(p.analysis_sent_at) ?? 0) >= FERMO_DAYS)
      if (fermi.length > 0) {
        nuovi.push({
          peso: 3, tono: 'fermo',
          testo: `${fermi.length} person${fermi.length === 1 ? 'a aspetta' : 'e aspettano'} una risposta da più di un mese`,
          id: null,
        })
      }
      for (const p of inPipeline) {
        const nome = p.company || p.name || p.email
        if (!p.next_action && !p.next_action_date) {
          nuovi.push({
            peso: 4, tono: 'fermo',
            testo: `${nome}: in ${p.pipeline_stage ? PIPELINE_LABEL[p.pipeline_stage] : 'pipeline'} senza un prossimo passo`,
            id: p.id,
          })
        } else if (p.next_action_date && p.next_action_date < today) {
          nuovi.push({
            peso: 5, tono: 'attesa',
            testo: `${nome}: «${p.next_action ?? 'prossimo passo'}» era per il ${fmtDateShort(p.next_action_date)}`,
            id: p.id,
          })
        }
      }

      nuovi.sort((a, b) => a.peso - b.peso)
      const visti = new Set<string>()
      setAvvisi(nuovi.filter((a) => {
        if (!a.id) return true
        if (visti.has(a.id)) return false
        visti.add(a.id)
        return true
      }))
    })
  }, [])

  // la giornata: prima le call di oggi, poi la coda. Due sorgenti, una
  // lista sola, e il numero in alto conta questa
  const daFare = bozze + domande + callDiOggi.length + taskOggi.length + proveInScadenza.length
  const apriPosta = () => window.dispatchEvent(new CustomEvent('clara:apri-posta'))

  const oraControllo = aggiornato ? fmtOra(aggiornato) : fmtOra(new Date().toISOString())
  const visibili = tuttiAvvisi ? avvisi : avvisi.slice(0, 3)
  const urgente = prossimo && new Date(prossimo.at).getTime() - Date.now() < 26 * 3600e3

  return (
    <div className="space-y-4">

      {/* ── la Prossima: un solo evento, grande ───────────────── */}
      {parte !== 'avvisi' && prossimo && (
        <Card className="border-l-4 border-l-navy">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-5 py-3.5">
            <button
              onClick={() => prossimo.prospect_id ? onOpen(prossimo.prospect_id) : onCalendario?.()}
              className="flex min-w-0 flex-1 flex-wrap items-baseline gap-x-3 gap-y-0.5 text-left"
            >
              <span className={`text-[15px] font-extrabold ${urgente ? 'text-amber-700' : ''}`}>
                {fraQuanto(prossimo.at)}
              </span>
              <span className="min-w-0 truncate text-sm font-semibold">{prossimo.titolo}</span>
              <span className="text-xs text-spento">
                {fmtDateShort(prossimo.at)}, {fmtOra(prossimo.at)}
              </span>
            </button>
            {settimana > 1 && onCalendario && (
              <button onClick={onCalendario} className="shrink-0 text-xs font-semibold text-blu hover:underline">
                altri {settimana - 1} in settimana
              </button>
            )}
          </div>
          {/* la riga di oggi: quello che aspetta te, secco, senza riquadro (Dre, 9/9) */}
          {pronto && daFare > 0 && (
            <div className="flex flex-wrap gap-x-4 gap-y-1 border-t border-velo px-5 py-2 text-xs text-tenue">
              {callDiOggi.length > 0 && <button onClick={onCalendario} className="hover:text-navy"><b className="text-inchiostro">{callDiOggi.length}</b> call oggi, {callDiOggi[0].quando} {callDiOggi[0].testo}</button>}
              {bozze > 0 && <button onClick={apriPosta} className="hover:text-navy"><b className="text-inchiostro">{bozze}</b> {bozze === 1 ? 'bozza da approvare' : 'bozze da approvare'}</button>}
              {domande > 0 && <button onClick={apriPosta} className="hover:text-navy"><b className="text-inchiostro">{domande}</b> {domande === 1 ? 'domanda di Clara' : 'domande di Clara'}</button>}
              {proveInScadenza.length > 0 && <button onClick={() => onOpen(proveInScadenza[0].id)} className="hover:text-navy"><b className="text-inchiostro">{proveInScadenza.length}</b> {proveInScadenza.length === 1 ? 'prova che finisce' : 'prove che finiscono'}, {proveInScadenza[0].nome} il {fmtDateShort(proveInScadenza[0].fine)}</button>}
            </div>
          )}
        </Card>
      )}
      {parte !== 'avvisi' && !prossimo && pronto && daFare > 0 && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 px-1 text-xs text-tenue">
          {bozze > 0 && <button onClick={apriPosta} className="hover:text-navy"><b className="text-inchiostro">{bozze}</b> {bozze === 1 ? 'bozza da approvare' : 'bozze da approvare'}</button>}
          {domande > 0 && <button onClick={apriPosta} className="hover:text-navy"><b className="text-inchiostro">{domande}</b> {domande === 1 ? 'domanda di Clara' : 'domande di Clara'}</button>}
          {proveInScadenza.length > 0 && <button onClick={() => onOpen(proveInScadenza[0].id)} className="hover:text-navy"><b className="text-inchiostro">{proveInScadenza.length}</b> {proveInScadenza.length === 1 ? 'prova che finisce' : 'prove che finiscono'}</button>}
        </div>
      )}

      {/* ── avvisi ────────────────────────────────────────────── */}
      {parte !== 'call' && (
      <div id="avvisi" className="scroll-mt-4">
        {avvisi.length === 0 ? (
          <p className="flex items-center gap-2 rounded-2xl border border-green-200 bg-green-50 px-4 py-2.5 text-sm text-green-800">
            <span className="font-bold">fatto</span>
            Clara ha controllato tutto alle {oraControllo}: zero problemi.
          </p>
        ) : (
          <Card>
            <header className="flex flex-wrap items-center gap-2.5 border-b border-velo px-4 py-2.5">
              <span className="text-[13px] font-bold">Avvisi</span>
              <span className="rounded-full bg-red-600 px-2 py-px text-[11px] font-bold text-white">
                {avvisi.length}
              </span>
              <span className="ml-auto text-[11px] text-spento">controllato tutto alle {oraControllo}</span>
            </header>
            {visibili.map((a, i) => {
              const vai = a.id ? () => onOpen(a.id!) : onOggi
              const dentro = (
                <>
                  <span className="mt-[7px]"><Dot tone={a.tono} /></span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-semibold">{a.testo}</span>
                  </span>
                </>
              )
              return vai ? (
                <button
                  key={i}
                  onClick={vai}
                  className="flex w-full items-start gap-3 border-b border-velo px-4 py-2.5 text-left last:border-0 hover:bg-velo/60"
                >
                  {dentro}
                </button>
              ) : (
                <div key={i} className="flex items-start gap-3 border-b border-velo px-4 py-2.5 last:border-0">
                  {dentro}
                </div>
              )
            })}
            {avvisi.length > 3 && (
              <button
                onClick={() => setTuttiAvvisi(!tuttiAvvisi)}
                className="w-full px-4 py-2 text-left text-xs font-semibold text-blu hover:bg-velo/60"
              >
                {tuttiAvvisi ? 'Mostra meno' : `Altri ${avvisi.length - 3} avvisi`}
              </button>
            )}
          </Card>
        )}
      </div>
    )}
    </div>
  )
}
