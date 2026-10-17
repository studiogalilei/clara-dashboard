// Le notifiche sul telefono (7/9/2026).
//
// Dre: «una webapp che mi aggiungo in Home sull'iPhone, deve inviare
// notifiche». Web Push: il browser da' un indirizzo a cui il cloud manda
// il messaggio; noi lo salviamo nelle preferenze (chiave push-iscrizioni,
// una lista: telefono e computer insieme) e scripts/avvisa.py lo usa.
// Su iPhone funziona solo dopo «Aggiungi alla schermata Home».
import { supabase } from './supabase'

export type StatoNotifiche = 'attive' | 'spente' | 'negate' | 'non-supportate' | 'da-installare'

const CHIAVE_PUBBLICA = import.meta.env.VITE_VAPID_PUBLIC as string | undefined

/** Aperta come app (dalla Home dell'iPhone, o installata dal computer), non in una scheda del browser. */
export function installata(): boolean {
  return window.matchMedia('(display-mode: standalone)').matches
    || (navigator as Navigator & { standalone?: boolean }).standalone === true
}

/** iPhone o iPad (l'iPad nuovo si presenta come un Mac, ma ha il tocco). */
export function iphone(): boolean {
  return /iPhone|iPad|iPod/.test(navigator.userAgent) || (/Macintosh/.test(navigator.userAgent) && navigator.maxTouchPoints > 1)
}

function daInstallare(): boolean {
  // iPhone: Safari fuori dalla Home non ha le notifiche
  return iphone() && !installata()
}

export function supportate(): boolean {
  return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window && Boolean(CHIAVE_PUBBLICA)
}

export async function stato(): Promise<StatoNotifiche> {
  // l'iPhone fuori dalla Home prima di tutto: anche se Safari mostrasse le API, li' non arrivano
  if (daInstallare()) return 'da-installare'
  if (!supportate()) return 'non-supportate'
  if (Notification.permission === 'denied') return 'negate'
  const reg = await navigator.serviceWorker.getRegistration()
  const sub = await reg?.pushManager.getSubscription()
  return sub ? 'attive' : 'spente'
}

function base64aBytes(s: string): Uint8Array<ArrayBuffer> {
  const pad = '='.repeat((4 - (s.length % 4)) % 4)
  const b = atob((s + pad).replace(/-/g, '+').replace(/_/g, '/'))
  const out = new Uint8Array(new ArrayBuffer(b.length))
  for (let i = 0; i < b.length; i++) out[i] = b.charCodeAt(i)
  return out
}

// chiede il permesso, si iscrive, salva. Torna cosa e' successo, a parole.
export async function attiva(): Promise<{ stato: StatoNotifiche; problema?: string }> {
  if (daInstallare()) return { stato: 'da-installare' }
  if (!supportate()) return { stato: 'non-supportate' }
  const permesso = await Notification.requestPermission()
  if (permesso !== 'granted') return { stato: 'negate' }
  try {
    const reg = await Promise.race([navigator.serviceWorker.ready,
      new Promise<never>((_, no) => setTimeout(() => no(new Error('l\'app non ha finito di installarsi: chiudila e riaprila')), 15_000))])
    const sub = await reg.pushManager.getSubscription()
      ?? await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: base64aBytes(CHIAVE_PUBBLICA!) })
    const problema = await salva(sub.toJSON(), true)
    return problema ? { stato: 'spente', problema } : { stato: 'attive' }
  } catch (e) {
    return { stato: 'spente', problema: e instanceof Error ? e.message : String(e) }
  }
}

/** All'apertura: se questo dispositivo e' iscritto ma la sua iscrizione non e' salvata (tolta dal
 *  cloud come morta, o cambiata dal telefono), la si rimette. Silenziosa: non chiede niente. */
export async function riallinea(): Promise<void> {
  try {
    if (!supportate() || Notification.permission !== 'granted') return
    const reg = await navigator.serviceWorker.getRegistration()
    const sub = await reg?.pushManager.getSubscription()
    if (!sub) return
    const { data } = await supabase.auth.getSession()
    const owner = data.session?.user?.id
    if (!owner) return
    if (!(await elenco(owner)).some((i) => i.endpoint === sub.endpoint)) await salva(sub.toJSON())
  } catch { /* al prossimo giro */ }
}

/** Il tocco su una notifica con l'app gia' aperta: il service worker (public/push.js) manda
 *  l'indirizzo e la pagina ci va, senza ricaricare. */
export function ascoltaNotifiche(): () => void {
  if (!('serviceWorker' in navigator)) return () => {}
  const su = (e: MessageEvent) => {
    const url = (e.data as { apri?: string } | null)?.apri
    if (!url) return
    try {
      const dove = new URL(url, window.location.href)
      if (dove.origin !== window.location.origin) return
      if (dove.pathname === window.location.pathname) window.location.hash = dove.hash
      else window.location.href = dove.href
    } catch { /* indirizzo strano: si resta dove si e' */ }
  }
  navigator.serviceWorker.addEventListener('message', su)
  return () => navigator.serviceWorker.removeEventListener('message', su)
}

export async function spegni(): Promise<StatoNotifiche> {
  const reg = await navigator.serviceWorker.getRegistration()
  const sub = await reg?.pushManager.getSubscription()
  if (sub) {
    await togli(sub.endpoint)
    await sub.unsubscribe()
  }
  return 'spente'
}

type Iscrizione = PushSubscriptionJSON & { dispositivo?: string; dal?: string; benvenuto?: string }

async function elenco(owner: string): Promise<Iscrizione[]> {
  const { data } = await supabase.from('preferenze').select('valore')
    .eq('owner', owner).eq('chiave', 'push-iscrizioni').maybeSingle()
  const v = (data as { valore: unknown } | null)?.valore
  return Array.isArray(v) ? (v as Iscrizione[]) : []
}

// `prova`: il cloud (scripts/avvisa.py, benvenuti) manda a questo dispositivo una notifica di prova
// entro qualche minuto: la prova vera che la strada fino al telefono funziona.
async function salva(sub: PushSubscriptionJSON, prova = false): Promise<string | undefined> {
  const { data } = await supabase.auth.getSession()
  const owner = data.session?.user?.id
  if (!owner) return 'non sei collegato'
  const altre = (await elenco(owner)).filter((i) => i.endpoint !== sub.endpoint)
  const nuova: Iscrizione = { ...sub, dispositivo: navigator.userAgent.slice(0, 80), dal: new Date().toISOString(),
                              ...(prova ? { benvenuto: 'da-mandare' } : {}) }
  const { error } = await supabase.from('preferenze')
    .upsert({ owner, chiave: 'push-iscrizioni', valore: [...altre, nuova] }, { onConflict: 'owner,chiave' })
  return error?.message
}

async function togli(endpoint: string) {
  const { data } = await supabase.auth.getSession()
  const owner = data.session?.user?.id
  if (!owner) return
  const resto = (await elenco(owner)).filter((i) => i.endpoint !== endpoint)
  await supabase.from('preferenze')
    .upsert({ owner, chiave: 'push-iscrizioni', valore: resto }, { onConflict: 'owner,chiave' })
}
