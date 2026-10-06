import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { dataDiRipresa, nonDaRiprendere, soloSuo } from '../lib/posta'
import { giorno } from '../lib/regole'

// IL «NON ORA» DIVENTA UNA DATA (gold, 6/10, idea 3 della ricerca sui ruoli).
// Chi ha detto «piu' avanti» senza dire quando restava un rinvio senza data: nessun giro lo
// riprendeva mai, e spariva. Qui c'e' la sua frase, il giorno proposto letto dalle sue parole,
// e un tocco. La data diventa il prossimo passo, e il calendario dei follow-up la riprende da
// solo (followup.py, «RINVIO SCADUTO»). Chi e' stato girato a un altro indirizzo non sta qui:
// quello e' un altro lavoro.

interface Voce { id: string; nome: string; frase: string; scritta: string; il: Date; perche: string }

export default function NonOra({ conBozza }: { conBozza: Set<string> }) {
  const [voci, setVoci] = useState<Voce[] | null>(null)
  const [fatto, setFatto] = useState<string | null>(null)
  const [guaio, setGuaio] = useState<string | null>(null)

  useEffect(() => {
    let vivo = true
    ;(async () => {
      const { data } = await supabase.from('prospects').select('id,company,name,email,next_action')
        .eq('classificazione', 'rinvio').eq('fuori', false).eq('no_followup', false).eq('awaiting_us', false)
        .is('next_action_date', null).is('ooo_until', null).not('stage', 'in', '(nuovo,perso,cliente)').limit(200)
      const ps = ((data ?? []) as Array<{ id: string; company: string | null; name: string | null; email: string; next_action: string | null }>)
        .filter((p) => !conBozza.has(p.id) && !/^(riscrivere|parcheggiato)/i.test(p.next_action ?? ''))
      if (!ps.length) { if (vivo) setVoci([]); return }
      // a blocchi di 60: con tutti gli id in una richiesta sola l'indirizzo diventa troppo lungo
      const mail: Array<{ prospect_id: string; at: string; body: string | null }> = []
      for (let i = 0; i < ps.length; i += 60) {
        const { data: pezzo } = await supabase.from('interactions').select('prospect_id,at,body')
          .eq('kind', 'email_in').in('prospect_id', ps.slice(i, i + 60).map((p) => p.id)).order('at', { ascending: false }).limit(1000)
        mail.push(...((pezzo ?? []) as typeof mail))
      }
      mail.sort((a, b) => b.at.localeCompare(a.at))
      const ultima = new Map<string, { at: string; body: string | null }>()
      for (const m of mail) {
        if (!ultima.has(m.prospect_id) && soloSuo(m.body)) ultima.set(m.prospect_id, m)
      }
      const lista: Voce[] = []
      for (const p of ps) {
        const m = ultima.get(p.id)
        if (!m) continue                       // senza una sua frase non si indovina niente
        const frase = soloSuo(m.body).replace(/\s+/g, ' ')
        if (nonDaRiprendere(frase)) continue
        const r = dataDiRipresa(frase, new Date(m.at))
        lista.push({ id: p.id, nome: p.company || p.name || p.email, frase, scritta: m.at, il: r.il, perche: r.perche })
      }
      lista.sort((a, b) => a.il.getTime() - b.il.getTime())
      if (vivo) setVoci(lista)
    })()
    return () => { vivo = false }
  }, [conBozza])

  async function riprendi(v: Voce) {
    setGuaio(null)
    const { error } = await supabase.from('prospects')
      .update({ next_action_date: giorno(v.il), next_action: `Ripresa: ${v.perche}` }).eq('id', v.id)
    if (error) { setGuaio(`${v.nome}: non sono riuscito a salvare la data`); return }
    setVoci((l) => (l ?? []).filter((x) => x.id !== v.id))
    setFatto(`${v.nome}: lo riprendo il ${v.il.toLocaleDateString('it-IT', { day: 'numeric', month: 'long' })}`)
  }

  if (!voci || voci.length === 0) return fatto ? <p className="px-5 py-2 text-[12px] font-semibold text-emerald-700">{fatto}</p> : null

  return (
    <>
      <div className="flex items-center gap-2 bg-fondo px-5 pb-1.5 pt-4">
        <span className="text-[10px] font-bold uppercase tracking-[0.05em] text-navy/70">Non ora, senza una data</span>
        <span className="text-[10px] font-bold tabular-nums text-tenue">{voci.length}</span>
      </div>
      {fatto && <p className="px-5 pb-1 text-[12px] font-semibold text-emerald-700">{fatto}</p>}
      {guaio && <p className="px-5 pb-1 text-[12px] font-semibold text-red-700">{guaio}</p>}
      {voci.map((v) => (
        <div key={v.id} className="border-b border-velo px-5 py-2.5">
          <div className="flex items-baseline justify-between gap-2">
            <span className="truncate text-[13px] font-semibold text-inchiostro">{v.nome}</span>
            <span className="shrink-0 text-[11px] tabular-nums text-tenue">{new Date(v.scritta).toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })}</span>
          </div>
          <p className="mt-0.5 line-clamp-2 text-[12px] italic text-tenue">«{v.frase.slice(0, 180)}»</p>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1">
            <button onClick={() => void riprendi(v)}
                    className="min-h-[36px] rounded-full border border-blu px-3 py-1 text-[12px] font-bold text-blu hover:bg-blu/5">
              Riprendi il {v.il.toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'long' })}
            </button>
            <span className="text-[11px] text-tenue">{v.perche}</span>
          </div>
        </div>
      ))}
    </>
  )
}
