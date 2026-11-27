// IL LINKEDIN DESK, i dati (27/11/2026). Dre: «un sistema sul telefono dove in modo veloce posso registrare un
// audio, mettere una foto e trasforma la roba in un post». Qui: leggere e scrivere i post, caricare la foto,
// bussare alla routine che li scrive, e la dettatura del telefono (gratis, nel browser).
import { useCallback, useEffect, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'

export type StatoPost = 'da_scrivere' | 'in_scrittura' | 'bozza' | 'programmato' | 'pubblicato' | 'scartato' | 'errore'
export type Richiesta = 'piu_corto' | 'piu_ironico' | 'cambia_framework'

export interface Versione {
  framework: string
  caso?: string
  testo: string
  giudice?: { passa?: boolean; note?: string }
}

export interface Post {
  id: string
  origine: 'auto' | 'mio'
  creato_il: string
  aggiornato_il: string
  stato: StatoPost
  dettato: string
  foto: string | null
  richiesta: Richiesta | null
  versioni: Versione[]
  scelta: number | null
  testo: string | null
  uscita_il: string | null
  pubblicato_il: string | null
  errore: string | null
}

const CAMPI = 'id, origine, creato_il, aggiornato_il, stato, dettato, foto, richiesta, versioni, scelta, testo, uscita_il, pubblicato_il, errore'

/** Il calendario: i post da oggi in poi (e quelli usciti oggi), in ordine di uscita. */
export async function leggiPost(): Promise<Post[]> {
  const da = new Date(); da.setHours(0, 0, 0, 0)
  const { data, error } = await supabase.from('linkedin_post').select(CAMPI)
    .neq('stato', 'scartato').gte('uscita_il', da.toISOString()).order('uscita_il', { ascending: true }).limit(60)
  // (i post ancora senza giorno, quelli che si stanno ottimizzando, li tiene il compositore)
  if (error) throw new Error(error.message)
  return (data ?? []) as Post[]
}

/** Bussa alla routine che scrive: se non risponde, il post aspetta il giro di riserva (ogni ora). */
async function bussa(): Promise<void> {
  try { await supabase.functions.invoke('linkedin-scrivi', { body: {} }) } catch { /* il giro di riserva lo prende */ }
}

export async function caricaFoto(file: File): Promise<string> {
  const est = (file.name.split('.').pop() || 'jpg').toLowerCase().replace(/[^a-z0-9]/g, '') || 'jpg'
  // ognuno ha la sua cartella (v122): la prima parte del percorso e' chi la carica
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) throw new Error('Non sei dentro')
  const percorso = `${user.id}/${new Date().toISOString().slice(0, 10)}/${crypto.randomUUID()}.${est}`
  const { error } = await supabase.storage.from('linkedin').upload(percorso, file, { contentType: file.type || 'image/jpeg' })
  if (error) throw new Error(error.message)
  return percorso
}

export async function urlFoto(percorso: string): Promise<string | null> {
  const { data } = await supabase.storage.from('linkedin').createSignedUrl(percorso, 3600)
  return data?.signedUrl ?? null
}

/** Un post nuovo, ancora senza giorno: con «Ottimizza» lo riscrive la routine, poi si programma. */
export async function nuovoPost(dettato: string, foto: string | null, ottimizza: boolean): Promise<string> {
  const riga: Record<string, string | null> = { dettato: dettato.trim(), foto, origine: 'mio', stato: ottimizza ? 'da_scrivere' : 'bozza', testo: ottimizza ? null : dettato.trim() }
  const { data, error } = await supabase.from('linkedin_post').insert(riga).select('id').single()
  if (error) throw new Error(error.message)
  if (ottimizza) await bussa()
  return (data as { id: string }).id
}

export async function leggiUno(id: string): Promise<Post | null> {
  const { data, error } = await supabase.from('linkedin_post').select(CAMPI).eq('id', id).maybeSingle()
  if (error) throw new Error(error.message)
  return (data as Post | null) ?? null
}

/** «Programma»: giorno e ora li sceglie la persona (v124, linkedin_programma). */
export async function programma(id: string, quando: Date): Promise<void> {
  const { data, error } = await supabase.rpc('linkedin_programma', { post: id, quando: quando.toISOString() })
  if (error) throw new Error(error.message)
  const r = data as { ok?: boolean; perche?: string } | null
  if (r && r.ok === false) throw new Error(r.perche ?? 'Non sono riuscito a programmarlo.')
}

export async function cambiaOra(id: string, uscita: Date): Promise<void> {
  const { error } = await supabase.from('linkedin_post').update({ uscita_il: uscita.toISOString() }).eq('id', id)
  if (error) throw new Error(error.message)
}

export async function cambiaFotoPost(id: string, foto: string | null): Promise<void> {
  const { error } = await supabase.from('linkedin_post').update({ foto }).eq('id', id)
  if (error) throw new Error(error.message)
}

export async function riscrivi(p: Post, richiesta: Richiesta): Promise<void> {
  const { error } = await supabase.from('linkedin_post').update({ richiesta, stato: 'da_scrivere', errore: null }).eq('id', p.id)
  if (error) throw new Error(error.message)
  await bussa()
}

export async function salvaTesto(id: string, scelta: number, testo: string): Promise<void> {
  const { error } = await supabase.from('linkedin_post').update({ scelta, testo }).eq('id', id)
  if (error) throw new Error(error.message)
}

export async function scarta(id: string): Promise<void> {
  const { error } = await supabase.from('linkedin_post').update({ stato: 'scartato' }).eq('id', id)
  if (error) throw new Error(error.message)
}

// IL PROFILO (v122): chi sei e come parli, cosi' la routine scrive con la tua voce.
export interface Profilo { nome: string; ruolo: string; temi: string }

export async function leggiProfilo(): Promise<Profilo | null> {
  const { data, error } = await supabase.from('linkedin_profilo').select('nome, ruolo, temi').maybeSingle()
  if (error) throw new Error(error.message)
  return (data as Profilo | null) ?? null
}

export async function salvaProfilo(p: Profilo): Promise<void> {
  const { error } = await supabase.from('linkedin_profilo').upsert({ ...p, aggiornato_il: new Date().toISOString() })
  if (error) throw new Error(error.message)
}

/** I post cambiano mentre li guardi (la routine scrive): si ascolta la tabella. */
export function useAscoltaPost(rifai: () => void) {
  useEffect(() => {
    const canale = supabase.channel('linkedin_post')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'linkedin_post' }, () => rifai())
      .subscribe()
    return () => { void supabase.removeChannel(canale) }
  }, [rifai])
}

// LA DETTATURA. Il riconoscimento vocale del telefono, in italiano: niente file audio, niente costi.
// Dove non c'e' (alcuni browser), resta il microfono della tastiera.
interface Riconoscimento {
  lang: string; continuous: boolean; interimResults: boolean
  onresult: ((e: { resultIndex: number; results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean }> }) => void) | null
  onend: (() => void) | null
  onerror: ((e: { error: string }) => void) | null
  start(): void; stop(): void
}

function costruttore(): (new () => Riconoscimento) | null {
  const w = window as unknown as Record<string, unknown>
  return (w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null) as (new () => Riconoscimento) | null
}

export function useDettatura(aggiungi: (testo: string) => void) {
  const [ascolto, setAscolto] = useState(false)
  const [provvisorio, setProvvisorio] = useState('')
  const [problema, setProblema] = useState<string | null>(null)
  const r = useRef<Riconoscimento | null>(null)
  const voglio = useRef(false)
  const disponibile = costruttore() !== null

  const ferma = useCallback(() => { voglio.current = false; r.current?.stop(); setAscolto(false); setProvvisorio('') }, [])

  const parti = useCallback(() => {
    const C = costruttore()
    if (!C) { setProblema('Su questo telefono usa il microfono della tastiera.'); return }
    const rec = new C()
    rec.lang = 'it-IT'; rec.continuous = true; rec.interimResults = true
    rec.onresult = (e) => {
      let intanto = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const ris = e.results[i]
        if (ris.isFinal) aggiungi(ris[0].transcript.trim())
        else intanto += ris[0].transcript
      }
      setProvvisorio(intanto)
    }
    rec.onerror = (e) => { if (e.error === 'not-allowed') { voglio.current = false; setProblema('Serve il permesso del microfono.') } }
    // Safari si ferma da solo dopo una pausa: se Dre non ha premuto stop, si riparte
    rec.onend = () => { if (voglio.current) { try { rec.start() } catch { setAscolto(false) } } else setAscolto(false) }
    r.current = rec; voglio.current = true; setProblema(null)
    try { rec.start(); setAscolto(true) } catch { setProblema('Il microfono non parte, riprova.') }
  }, [aggiungi])

  useEffect(() => () => { voglio.current = false; r.current?.stop() }, [])
  return { disponibile, ascolto, provvisorio, problema, parti, ferma }
}
