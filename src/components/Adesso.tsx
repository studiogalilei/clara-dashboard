import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { sonoCeo } from '../lib/accessi'
import { apriInPosta, fraseDiClara, percheCosi, quandoProposto, rimandata } from '../lib/posta'
import { useVivo } from '../lib/vivo'

// ADESSO (gold, 6/10): la home non apre su una lista, apre sulla prossima cosa da fare.
// Workflow nel vault: «Il Workspace gold, i workflow prima del software (6-10-2026)».
// 1. Adesso: la conversazione che aspetta da piu' tempo, col perche' di Clara in una riga
//    e un bottone che porta nella Posta gia' aperta su di lei, dentro la fila;
// 2. Poi: i due o tre nomi dopo, nello stesso ordine della Posta;
// 3. il traguardo di oggi (la regola di Dre del 5/10, solo ai ceo): tre spunte che
//    diventano verdi, e quando lo sono tutte la giornata e' chiusa.
// Prende il posto della striscia «N bozze pronte da approvare».

const SEGUITI = ['FOLLOW UP 1', 'MINI FOLLOW UP', 'RINVIO SCADUTO', 'RICONTATTO OOO', 'RIPRESA', 'FOLLOW UP SU MISURA']

interface Voce { id: number; prospect: string; nome: string; perche: string; ore: number | null; seguito: boolean; giorno: string }

function eta(ore: number | null): string {
  if (ore === null) return ''
  if (ore < 1) return 'da meno di un’ora'
  if (ore < 48) return `da ${Math.round(ore)} ore`
  return `da ${Math.round(ore / 24)} giorni`
}

export default function Adesso() {
  const [voci, setVoci] = useState<Voce[] | null>(null)
  const [siSenza, setSiSenza] = useState<number | null>(null)
  const [ceo, setCeo] = useState(false)
  const [giro, setGiro] = useState(0)
  useVivo(['proposte'], () => setGiro((n) => n + 1))

  useEffect(() => { void sonoCeo().then(setCeo) }, [])

  useEffect(() => {
    let vivo = true
    ;(async () => {
      const { data } = await supabase.from('proposte')
        .select('id,tipo,titolo,perche,prospect_id,at,azione')
        .in('tipo', ['risposta', 'umano']).eq('stato', 'aperta').not('azione->>bozza', 'is', null)
        .order('at', { ascending: true }).limit(300)
      const ps = ((data ?? []) as Array<{ id: number; titolo: string; perche: string | null; prospect_id: string | null; azione: Record<string, unknown> | null }>)
        .filter((p) => p.prospect_id && !rimandata(p.azione))
      const ids = [...new Set(ps.map((p) => p.prospect_id as string))]
      const schede = new Map<string, { company: string | null; name: string | null; email: string; last_reply_at: string | null }>()
      for (let i = 0; i < ids.length; i += 100) {
        const { data: d } = await supabase.from('prospects').select('id,company,name,email,last_reply_at').in('id', ids.slice(i, i + 100))
        for (const x of (d ?? []) as Array<{ id: string; company: string | null; name: string | null; email: string; last_reply_at: string | null }>) schede.set(x.id, x)
      }
      const adesso = Date.now()
      const visti = new Set<string>()
      const lista: Voce[] = []
      for (const p of ps) {
        const pid = p.prospect_id as string
        if (visti.has(pid)) continue
        visti.add(pid)
        const s = schede.get(pid)
        const seguito = SEGUITI.includes(String(p.azione?.template ?? ''))
        lista.push({
          id: p.id, prospect: pid, nome: s?.company || s?.name || s?.email || p.titolo,
          perche: percheCosi(p.perche), seguito, giorno: String(p.azione?.giorno_proposto ?? ''),
          ore: !seguito && s?.last_reply_at ? (adesso - new Date(s.last_reply_at).getTime()) / 3600_000 : null,
        })
      }
      // lo stesso ordine della Posta: prima chi aspetta (dal piu' vecchio), poi i follow-up dal giorno di call piu' vicino
      lista.sort((a, b) => Number(a.seguito) - Number(b.seguito)
        || (a.seguito ? (quandoProposto(a.giorno) - quandoProposto(b.giorno)) || a.nome.localeCompare(b.nome) : (b.ore ?? 0) - (a.ore ?? 0)))
      if (vivo) setVoci(lista)
    })()
    return () => { vivo = false }
  }, [giro])

  // la regola del 5/10, contata come la conta il battito (scripts/battito.py, giornata):
  // 1) chi ha detto si' e non ha ancora l'analisi;
  // 2) i follow-up dovuti: in Posta, approvati ma non ancora partiti, o arrivati al loro
  //    giorno nel calendario senza ancora una bozza. Prima contavo solo quelli in Posta, e la
  //    carta poteva dire «giornata chiusa» mentre il battito diceva APERTA.
  const [dovuti, setDovuti] = useState<number | null>(null)
  useEffect(() => {
    if (!ceo) return
    let vivo = true
    const oggi = new Date().toLocaleDateString('sv-SE')     // il giorno di qui, come il battito
    void Promise.all([
      supabase.from('prospects').select('id')
        .eq('fuori', false).eq('analysis_sent', false).in('classificazione', ['positivo', 'tiepido'])
        .eq('no_followup', false).not('stage', 'in', '(perso,cliente)').is('pipeline_stage', null).limit(1000),
      supabase.from('seguiti_calendario').select('prospect_id').lte('il', oggi).limit(1000),
      supabase.from('proposte').select('prospect_id,azione').in('stato', ['aperta', 'approvata', 'in_invio']).eq('tipo', 'risposta').limit(1000),
    ]).then(([si, cal, pr]) => {
      if (!vivo) return
      setSiSenza((si.data ?? []).length)
      const ids = new Set<string>()
      for (const c of (cal.data ?? []) as Array<{ prospect_id: string | null }>) if (c.prospect_id) ids.add(c.prospect_id)
      for (const x of (pr.data ?? []) as Array<{ prospect_id: string | null; azione: Record<string, unknown> | null }>) {
        if (x.prospect_id && SEGUITI.includes(String(x.azione?.template ?? ''))) ids.add(x.prospect_id)
      }
      setDovuti(ids.size)
    })
    return () => { vivo = false }
  }, [ceo, giro])

  if (voci === null) return null
  const risposte = voci.filter((v) => !v.seguito).length
  const seguiti = voci.length - risposte
  const prima = voci[0]
  const poi = voci.slice(1, 4)
  // chi non e' ceo e non ha niente in Posta non vede niente, come prima (la sua giornata sono le task)
  if (!prima && !ceo) return null
  const frase = fraseDiClara({ risposte: voci.filter((v) => !v.seguito).map((v) => v.nome), seguiti, siSenza: ceo ? siSenza : null })

  return (
    <div className="space-y-3">
      {/* LA FRASE DI CLARA (gold, dalla V3): cosa aspetta te, in una frase, dal vivo */}
      <div>
        <p className="flex items-center gap-1.5 text-[12px] font-bold text-blu">
          <span className="h-2 w-2 rounded-full bg-blu ring-4 ring-blu/15" />Clara
        </p>
        <p className="mt-1 text-[19px] font-extrabold leading-snug text-navy">{frase}</p>
      </div>
      {prima ? (
        <div className="rounded-2xl border border-bordo bg-white p-5">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-0.5 text-[11px] font-bold text-amber-800">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
            {prima.seguito ? `Follow-up pronto${prima.giorno ? `, propone ${prima.giorno.replace(/ alle .*/, '')}` : ''}` : `Aspetta te ${eta(prima.ore)}`}
          </span>
          <p className="mt-2 text-[22px] font-extrabold leading-tight text-navy">{prima.nome}</p>
          {prima.perche && (
            <p className="mt-2 rounded-xl bg-blu/[0.06] px-3 py-2 text-[13px] leading-snug text-inchiostro">
              <span className="font-bold text-blu">Clara: </span>{prima.perche}
            </p>
          )}
          <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2">
            <button onClick={() => apriInPosta(prima.id, prima.prospect)}
                    className="min-h-[44px] rounded-full bg-blu px-5 py-2 text-[14px] font-bold text-white hover:bg-blu/90">
              Leggi e approva
            </button>
            {poi.length > 0 && (
              <p className="min-w-0 text-[12px] text-tenue">
                Poi <span className="font-semibold text-inchiostro">{poi.map((v) => v.nome).join(', ')}</span>
                {voci.length > 4 && <span>, e altre {voci.length - 4}</span>}
              </p>
            )}
          </div>
        </div>
      ) : null}

      {ceo && siSenza !== null && (
        <Traguardo righe={[
          { fatto: siSenza === 0, testo: 'Tutti i sì hanno l’analisi', conto: siSenza === 0 ? '' : `${siSenza} senza` },
          { fatto: risposte === 0, testo: 'Le risposte che aspettano te', conto: risposte === 0 ? '' : `${risposte} da decidere` },
          { fatto: (dovuti ?? seguiti) === 0, testo: 'I follow-up partiti', conto: contoSeguiti(dovuti ?? seguiti, seguiti) },
        ]} />
      )}
    </div>
  )
}

function contoSeguiti(dovuti: number, inPosta: number): string {
  if (dovuti === 0) return ''
  if (dovuti === inPosta) return `${inPosta} in Posta`
  return inPosta ? `${dovuti} da mandare, di cui ${inPosta} in Posta` : `${dovuti} da mandare`
}

function Traguardo({ righe }: { righe: Array<{ fatto: boolean; testo: string; conto: string }> }) {
  const fatte = righe.filter((r) => r.fatto).length
  const chiusa = fatte === righe.length
  return (
    <div className="rounded-2xl border border-bordo bg-white px-5 py-4">
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-[11px] font-bold uppercase tracking-[0.06em] text-tenue">Il traguardo di oggi</p>
        <p className={`text-[12px] font-bold ${chiusa ? 'text-emerald-700' : 'text-tenue'}`}>{chiusa ? 'Giornata chiusa' : `${fatte} di ${righe.length}`}</p>
      </div>
      <div className="mt-2 flex gap-1.5" aria-hidden>
        {righe.map((r, i) => <span key={i} className={`h-1.5 flex-1 rounded-full ${r.fatto ? 'bg-emerald-500' : 'bg-velo'}`} />)}
      </div>
      <ul className="mt-3 space-y-2">
        {righe.map((r) => (
          <li key={r.testo} className="flex items-center gap-2.5 text-[13px]">
            <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${r.fatto ? 'bg-emerald-500 text-white' : 'border-2 border-bordo'}`}>
              {r.fatto && <svg viewBox="0 0 24 24" className="h-3 w-3"><path fill="none" stroke="currentColor" strokeWidth="3" d="M5 12l5 5L20 7" /></svg>}
            </span>
            <span className={r.fatto ? 'text-tenue' : 'text-inchiostro'}>{r.testo}</span>
            {r.conto && <span className="ml-auto text-[12px] font-semibold tabular-nums text-tenue">{r.conto}</span>}
          </li>
        ))}
      </ul>
    </div>
  )
}
