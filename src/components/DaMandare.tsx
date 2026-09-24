import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { useVivo } from '../lib/vivo'
import type { Prospect } from '../lib/types'
import { Card, Spinner } from './ui'

// DA MANDARE (Dre, 24/9): «quando sono nella scheda del cliente non vedo la
// bozza, c'è solo un pulsante per scaricare l'analisi. Se entro e non è
// ancora pronta ci deve essere qualcosa che si carica, così aspetto, prendo
// bozza e analisi e invio in chill». Questo blocco sta in cima alla scheda e
// risponde a una domanda sola: cosa mando a questa persona, adesso.
// Tre stati: Clara ci sta lavorando (con cosa è già pronto), la bozza è qui
// (leggi, correggi, copia, «l'ho mandata»), niente da mandare.

type Proposta = {
  id: number
  tipo: string
  titolo: string
  perche: string | null
  azione: { bozza?: string; intento?: string; template?: string } | null
  at: string
}

export default function DaMandare({ p }: { p: Prospect }) {
  const [pr, setPr] = useState<Proposta | null | undefined>(undefined)   // undefined = non ancora letto
  const [testo, setTesto] = useState('')
  const [copiata, setCopiata] = useState(false)
  const [lavoro, setLavoro] = useState(false)
  const [esito, setEsito] = useState<string | null>(null)
  const [allego, setAllego] = useState(true)
  const [giro, setGiro] = useState(0)

  useVivo(['proposte', 'prospects'], () => setGiro((n) => n + 1))

  useEffect(() => {
    let vivo = true
    supabase.from('proposte')
      .select('id,tipo,titolo,perche,azione,at')
      .eq('prospect_id', p.id).eq('stato', 'aperta').in('tipo', ['risposta', 'umano'])
      .order('at', { ascending: false }).limit(1)
      .then(({ data }) => {
        if (!vivo) return
        const x = (data?.[0] as Proposta | undefined) ?? null
        setPr(x)
        if (x?.azione?.bozza !== undefined) setTesto((t) => t || x.azione!.bozza!)
      })
    return () => { vivo = false }
  }, [p.id, giro])

  const fit = (p.enriched as Record<string, unknown> | null)?.google_fit as { verdetto?: string } | undefined
  const destinatario = ((p as unknown as { email_alt?: string[] | null }).email_alt)?.[0] ?? p.email

  // niente da mandare: la persona non aspetta noi e non c'è una bozza
  if (!p.awaiting_us && !pr) return null
  if (pr === undefined) return null

  async function mandata() {
    if (!pr || lavoro) return
    setLavoro(true); setEsito(null)
    const corpo = testo.trim()
    // la stessa sequenza della Posta (ClaraVolante.rispondi): la mail nostra
    // entra nella storia, lei smette di aspettare, la proposta si chiude
    const { error } = await supabase.from('interactions')
      .insert({ prospect_id: p.id, at: new Date().toISOString(), kind: 'email_out', body: corpo })
    if (error) { setEsito(`Non sono riuscita a segnarla: ${error.message}`); setLavoro(false); return }
    const agg: Record<string, unknown> = { awaiting_us: false }
    if (allego && p.analysis_pdf) { agg.analysis_sent = true; agg.analysis_sent_at = new Date().toISOString() }
    if (pr.azione?.intento === 'INT-GB') { agg.analysis_sent = true; agg.analysis_sent_at = new Date().toISOString(); agg.no_followup = true }
    await supabase.from('prospects').update(agg).eq('id', p.id)
    await supabase.from('proposte').update({ stato: 'fatta', risposta_il: new Date().toISOString() }).eq('id', pr.id)
    setEsito('Segnata come mandata.'); setLavoro(false); setPr(null)
  }

  async function nonCosi() {
    if (!pr || lavoro) return
    const motivo = window.prompt('Cosa non va nella bozza? Una riga: Clara la usa per la prossima.') ?? ''
    if (!motivo.trim()) return
    setLavoro(true)
    await supabase.from('proposte').update({ stato: 'no', risposta: `NO: ${motivo.trim()}`, risposta_il: new Date().toISOString() }).eq('id', pr.id)
    setEsito('Scartata. Clara ne scrive un\'altra al prossimo giro, tenendo conto della nota.'); setLavoro(false); setPr(null)
  }

  const Voce = ({ ok, testo, inCorso }: { ok: boolean; testo: string; inCorso?: boolean }) => (
    <li className="flex items-center gap-2 text-sm">
      {ok ? <span className="text-ok">✓</span> : inCorso ? <span className="inline-block h-3 w-3 animate-pulse rounded-full bg-blu" /> : <span className="text-spento">○</span>}
      <span className={ok ? '' : 'text-tenue'}>{testo}</span>
    </li>
  )

  return (
    <Card className="border-blu/40">
      <header className="flex items-center justify-between gap-2 border-b border-velo px-4 py-2.5">
        <span className="text-[11px] font-bold uppercase tracking-[0.06em] text-blu">Da mandare</span>
        {pr?.azione?.template && <span className="text-[11px] text-tenue">{pr.azione.template}</span>}
      </header>

      {!pr ? (
        // CLARA CI STA LAVORANDO: si vede cosa è già pronto, e ci si può aspettare
        <div className="flex items-start gap-4 px-4 py-4">
          <Spinner />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold">Clara sta preparando bozza e analisi</p>
            <p className="mt-0.5 text-xs text-tenue">Di solito ci vuole qualche minuto dalla risposta. Questa pagina si aggiorna da sola.</p>
            <ul className="mt-3 space-y-1">
              <Voce ok={Boolean(fit?.verdetto)} testo={fit?.verdetto ? `Sito letto, fit ${fit.verdetto}` : 'Legge il sito'} inCorso={!fit?.verdetto} />
              <Voce ok={Boolean(p.analysis_pdf)} testo={p.analysis_pdf ? 'Analisi pronta' : 'Scrive l\'analisi'} inCorso={Boolean(fit?.verdetto) && !p.analysis_pdf} />
              <Voce ok={false} testo="Scrive la bozza" inCorso={Boolean(p.analysis_pdf)} />
            </ul>
            {p.analysis_pdf && (
              <a href={p.analysis_pdf} target="_blank" rel="noreferrer" className="mt-3 inline-block rounded-full border border-navy px-3 py-1 text-xs font-bold text-navy hover:bg-velo">
                Apri l'analisi (PDF)
              </a>
            )}
          </div>
        </div>
      ) : (
        // LA BOZZA È QUI: leggi, correggi, copia, manda, torna e conferma
        <div className="px-4 py-3">
          {pr.tipo === 'umano' && (
            <p className="mb-2 rounded-md bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">Clara si è fermata: {pr.perche}</p>
          )}
          {pr.tipo === 'risposta' && pr.perche && <p className="mb-2 text-xs text-tenue">Clara: {pr.perche}</p>}
          <textarea
            value={testo}
            onChange={(e) => setTesto(e.target.value)}
            rows={11}
            className="w-full rounded-lg border border-bordo bg-white px-3 py-2 text-[13px] leading-snug outline-none focus:border-blu"
          />
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <button
              onClick={async () => { try { await navigator.clipboard.writeText(testo) } catch { /* niente */ } setCopiata(true); setTimeout(() => setCopiata(false), 1800) }}
              className="rounded-full border border-bordo px-3 py-1.5 text-xs font-bold text-navy hover:border-navy">
              {copiata ? 'copiata' : 'Copia la bozza'}
            </button>
            {p.analysis_pdf ? (
              <a href={p.analysis_pdf} target="_blank" rel="noreferrer" className="rounded-full border border-bordo px-3 py-1.5 text-xs font-bold text-navy hover:border-navy">
                Apri l'analisi (PDF)
              </a>
            ) : (
              <span className="flex items-center gap-2 rounded-full border border-bordo px-3 py-1.5 text-xs text-tenue"><span className="inline-block h-2.5 w-2.5 animate-pulse rounded-full bg-blu" /> analisi in preparazione</span>
            )}
            <a href={`mailto:${encodeURIComponent(destinatario)}?subject=${encodeURIComponent('Re: ' + pr.titolo.replace(/^Bozza per /, ''))}&body=${encodeURIComponent(testo)}`}
               className="rounded-full border border-navy px-3 py-1.5 text-xs font-bold text-navy hover:bg-velo">
              Aprila già scritta
            </a>
            <span className="ml-auto flex items-center gap-2">
              {p.analysis_pdf && (
                <label className="flex items-center gap-1 text-[11px] text-tenue">
                  <input type="checkbox" checked={allego} onChange={(e) => setAllego(e.target.checked)} /> ho allegato l'analisi
                </label>
              )}
              <button onClick={mandata} disabled={lavoro} className="rounded-full bg-blu px-4 py-1.5 text-xs font-bold text-white disabled:opacity-40">L'ho mandata</button>
              <button onClick={nonCosi} disabled={lavoro} className="rounded-full border border-bordo px-3 py-1.5 text-xs font-semibold text-tenue hover:border-spento disabled:opacity-40">Non così</button>
            </span>
          </div>
          {destinatario !== p.email && <p className="mt-2 text-[11px] text-tenue">Va mandata a {destinatario} (ci ha dato questo indirizzo).</p>}
        </div>
      )}
      {esito && <p className="border-t border-velo px-4 py-2 text-xs text-navy">{esito}</p>}
    </Card>
  )
}
