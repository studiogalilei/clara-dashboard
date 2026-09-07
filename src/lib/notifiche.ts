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

function daInstallare(): boolean {
  // iPhone: Safari fuori dalla Home non ha le notifiche
  const iphone = /iPhone|iPad/.test(navigator.userAgent)
  const inHome = window.matchMedia('(display-mode: standalone)').matches
    || (navigator as Navigator & { standalone?: boolean }).standalone === true
  return iphone && !inHome
}

export function supportate(): boolean {
  return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window && Boolean(CHIAVE_PUBBLICA)
}

export async function stato(): Promise<StatoNotifiche> {
  if (!supportate()) return daInstallare() ? 'da-installare' : 'non-supportate'
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
  if (!supportate()) return { stato: daInstallare() ? 'da-installare' : 'non-supportate' }
  const permesso = await Notification.requestPermission()
  if (permesso !== 'granted') return { stato: 'negate' }
  try {
    const reg = await navigator.serviceWorker.ready
    const sub = await reg.pushManager.getSubscription()
      ?? await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: base64aBytes(CHIAVE_PUBBLICA!) })
    const problema = await salva(sub.toJSON())
    return problema ? { stato: 'spente', problema } : { stato: 'attive' }
  } catch (e) {
    return { stato: 'spente', problema: e instanceof Error ? e.message : String(e) }
  }
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

type Iscrizione = PushSubscriptionJSON & { dispositivo?: string; dal?: string }

async function elenco(owner: string): Promise<Iscrizione[]> {
  const { data } = await supabase.from('preferenze').select('valore')
    .eq('owner', owner).eq('chiave', 'push-iscrizioni').maybeSingle()
  const v = (data as { valore: unknown } | null)?.valore
  return Array.isArray(v) ? (v as Iscrizione[]) : []
}

async function salva(sub: PushSubscriptionJSON): Promise<string | undefined> {
  const { data } = await supabase.auth.getSession()
  const owner = data.session?.user?.id
  if (!owner) return 'non sei collegato'
  const altre = (await elenco(owner)).filter((i) => i.endpoint !== sub.endpoint)
  const nuova: Iscrizione = { ...sub, dispositivo: navigator.userAgent.slice(0, 80), dal: new Date().toISOString() }
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
