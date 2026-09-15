import { useState } from 'react'
import { supabase } from '../lib/supabase'
import { Card, TitoloCard } from './ui'
import { giorno } from '../lib/regole'

// AGGIUNGERE UN'AZIENDA A MANO (Dre, 15/9).
//
// Fino a ieri le aziende entravano solo dall'outbound o da Clara: chi ne
// trova una da un'altra parte non la poteva mettere dentro. Lorenzo lavora
// su LinkedIn con piu' profili e la sua pipeline nasce tutta a mano, e
// anche a Dre capita di conoscere qualcuno a un evento.
//
// Chi la mette dentro ci scrive il suo nome: cosi' la rivede (e' la regola
// del perimetro) e si sa di chi e'.

interface Props {
  nome: string                  // chi sta scrivendo: finisce in «chi segue»
  onFatto: (id: string) => void // si apre la scheda appena nata
  onChiudi: () => void
}

const CAMPI: Array<[string, string, string]> = [
  ['company', 'Azienda', 'Il nome, o incolla il link di LinkedIn'],
  ['name', 'Persona', 'Con chi parli'],
  ['email', 'Email', 'nome@azienda.it'],
  ['linkedin', 'LinkedIn', 'Il link al profilo'],
  ['website', 'Sito', 'azienda.it'],
  ['city', 'Città', 'Dove sono'],
  ['sector', 'Settore', 'Cosa fanno'],
  ['campaign', 'Da dove arriva', 'LinkedIn profilo 2, referral, evento…'],
]

// INCOLLA E BASTA (Dre, 15/9: «come fa Google, sa gia' cosa vuoi fare»).
// Lorenzo lavora su LinkedIn: copia il link del profilo o dell'azienda e lo
// incolla. Da li' si capisce quasi tutto: il campo giusto dove metterlo, il
// nome dell'azienda, il sito. Vale anche per una mail o per un sito.
const GENERICI = /(gmail|libero|hotmail|outlook|yahoo|icloud|tiscali|alice|virgilio|pec\.it)/i
const aTitolo = (t: string) => t
  .replace(/[-_]+/g, ' ')
  .replace(/\b(srl|spa|sas|snc|srls)\b/gi, (x) => x.toUpperCase())
  .replace(/\b[a-zà-ù]/g, (c) => c.toUpperCase())
  .trim()
const nomeDaDominio = (d: string) => aTitolo(d.replace(/^www\./i, '').split('.')[0])

export default function NuovaAzienda({ nome, onFatto, onChiudi }: Props) {
  const [v, setV] = useState<Record<string, string>>({})
  const [capito, setCapito] = useState<string | null>(null)

  // quello che si capisce da un pezzo di testo incollato
  function incolla(grezzo: string): boolean {
    const t = grezzo.trim()
    if (!t || /\s/.test(t)) return false
    const mail = /^[\w.+-]+@[\w-]+\.[\w.-]+$/.test(t)
    const link = /^(https?:\/\/|www\.)/i.test(t)
    if (!mail && !link) return false
    const n = { ...v }
    if (mail) {
      n.email = t
      const dominio = t.split('@')[1] ?? ''
      if (dominio && !GENERICI.test(dominio)) {
        if (!n.website) n.website = dominio
        if (!n.company) n.company = nomeDaDominio(dominio)
      }
      setCapito('dalla mail')
    } else if (/linkedin\./i.test(t)) {
      n.linkedin = t
      const slug = /\/(company|in)\/([^/?#]+)/.exec(t)?.[2]
      if (slug && !n.company) n.company = aTitolo(decodeURIComponent(slug).replace(/-[a-z0-9]{6,}$/i, ''))
      setCapito('dal link di LinkedIn')
    } else {
      const pulito = t.replace(/^https?:\/\//i, '').replace(/\/.*$/, '')
      n.website = pulito
      if (!n.company) n.company = nomeDaDominio(pulito)
      setCapito('dal sito')
    }
    setV(n)
    return true
  }
  // da dove entra: Dre (15/9) «se arriva qualcuno da fuori che vuole i
  // nostri servizi lo aggiungono nella sezione prospect: ci conosce gia',
  // c'e' solo da fare la call tecnica»
  const [come, setCome] = useState<'parlo' | 'trovata' | 'conosce'>('parlo')
  const [salvo, setSalvo] = useState(false)
  const [problema, setProblema] = useState<string | null>(null)

  async function salva() {
    const company = (v.company ?? '').trim()
    const email = (v.email ?? '').trim()
    if (!company && !email) { setProblema('Serve almeno il nome dell\'azienda.'); return }
    setSalvo(true)
    setProblema(null)
    const dentro = come === 'conosce'
    const riga: Record<string, unknown> = {
      company: company || null,
      name: (v.name ?? '').trim() || null,
      email: email || `senza-mail-${Date.now()}@studiogalilei.com`,
      linkedin: (v.linkedin ?? '').trim() || null,
      website: (v.website ?? '').trim() || null,
      city: (v.city ?? '').trim() || null,
      sector: (v.sector ?? '').trim() || null,
      campaign: (v.campaign ?? '').trim() || null,
      chi_segue: nome,
      // «ci sto parlando» = ha risposto, il prossimo passo è l'analisi;
      // «l'ho solo trovata» resta fuori dalla bacheca finché non risponde;
      // «ci conosce già» entra dritto in Call Tecnica, cioè è un prospect
      stage: dentro ? 'call_fissata' : come === 'parlo' ? 'risposto' : 'nuovo',
      last_reply_at: come === 'trovata' ? null : new Date().toISOString(),
      first_reply_at: come === 'trovata' ? null : new Date().toISOString(),
      awaiting_us: false,
      analysis_sent: dentro,
      analysis_sent_at: dentro ? new Date().toISOString() : null,
      fuori: dentro,
      fuori_at: dentro ? new Date().toISOString() : null,
      pipeline_stage: dentro ? 'tecnica' : null,
    }
    const { data, error } = await supabase.from('prospects').insert(riga).select('id').single()
    setSalvo(false)
    if (error || !data) {
      setProblema(error?.message.includes('row-level security')
        ? 'Non hai il permesso di aggiungere aziende: chiedilo a Dre.'
        : `Non si è salvata: ${error?.message ?? 'riprova'}`)
      return
    }
    await supabase.from('interactions').insert({
      prospect_id: (data as { id: string }).id, at: new Date().toISOString(), kind: 'nota',
      body: `${dentro ? 'Arrivata da fuori, entra in Call Tecnica' : 'Aggiunta a mano'} da ${nome}${riga.campaign ? `, da ${riga.campaign}` : ''}, il ${giorno()}.`,
    })
    onFatto((data as { id: string }).id)
  }

  return (
    <Card className="salta-su space-y-4 border-blu/40 p-5">
      <div className="flex items-baseline justify-between gap-3">
        <TitoloCard>Aggiungi un'azienda</TitoloCard>
        <button onClick={onChiudi} className="text-xs font-semibold text-spento hover:text-inchiostro">Annulla</button>
      </div>

      {problema && (
        <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{problema}</p>
      )}

      <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
        {CAMPI.map(([k, etichetta, esempio]) => (
          <label key={k} className={k === 'company' ? 'sm:col-span-2' : ''}>
            <span className="text-[10px] font-bold uppercase tracking-wide text-spento">{etichetta}</span>
            <input
              autoFocus={k === 'company'}
              value={v[k] ?? ''}
              onPaste={(e) => {
                // un link o una mail vanno nel campo giusto, non dove capita
                const t = e.clipboardData.getData('text')
                if (incolla(t)) e.preventDefault()
              }}
              onChange={(e) => { setV({ ...v, [k]: e.target.value }); setCapito(null) }}
              onKeyDown={(e) => { if (e.key === 'Enter') void salva() }}
              placeholder={esempio}
              className="mt-0.5 w-full rounded-lg border border-bordo bg-white px-2.5 py-1.5 text-sm outline-none focus:border-blu"
            />
          </label>
        ))}
      </div>

      {capito && (
        <p className="-mt-1 text-[11px] text-spento">Ho riempito quello che ho capito {capito}, correggi pure</p>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex overflow-hidden rounded-full border border-bordo text-xs font-semibold">
          {([['parlo', 'Ci sto già parlando'], ['trovata', 'L\'ho solo trovata'], ['conosce', 'Ci conosce già']] as const).map(([val, testo]) => (
            <button key={val} onClick={() => setCome(val)}
                    className={`px-3.5 py-1.5 ${come === val ? 'bg-blu text-white' : 'bg-white text-tenue hover:bg-velo'}`}>
              {testo}
            </button>
          ))}
        </div>
        {come === 'conosce' && (
          <span className="text-xs text-spento">Entra in Call Tecnica, da lì è un prospect</span>
        )}
        <span className="text-xs text-spento">La segui tu, {nome.split(' ')[0] || 'tu'}</span>
        <button onClick={() => void salva()} disabled={salvo}
                className="ml-auto rounded-full bg-blu px-5 py-2 text-sm font-bold text-white hover:bg-blu-scuro disabled:opacity-40">
          {salvo ? 'Salvo…' : 'Aggiungi'}
        </button>
      </div>
    </Card>
  )
}
