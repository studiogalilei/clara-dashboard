// IL DESK IN DEMO (27/11/2026): ?demo nell'indirizzo, dati finti in memoria, niente login. Serve a vedere la forma
// e ai collaudi a schermo. Testi inventati e dichiarati come esempio.
type Riga = Record<string, unknown>

const giornoLocale = (giorni: number) => { const d = new Date(); d.setDate(d.getDate() + giorni); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` }
const alle = (giorni: number, h: number, m = 30) => { const d = new Date(); d.setDate(d.getDate() + giorni); d.setHours(h, m, 0, 0); return d.toISOString() }
const post = (id: string, giorni: number, origine: string, testo: string, stato = 'programmato'): Riga => ({
  id, origine, stato, dettato: '', foto: null, richiesta: null, scelta: 0, testo: null, errore: null,
  creato_il: alle(-1, 9), aggiornato_il: alle(-1, 9), uscita_il: alle(giorni, 8), pubblicato_il: null,
  versioni: testo ? [{ framework: 'Esempio', caso: 'demo', testo }] : [],
})

const TABELLE: Record<string, Riga[]> = {
  linkedin_post: [
    post('d0', 0, 'auto', 'Immaginate un\'azienda di noleggio con dodici mezzi e un solo foglio Excel.\n\nOgni mattina qualcuno apre il foglio e chiama gli autisti uno per uno.\n\nEsempio della demo.\n\nDa voi chi tiene il calendario dei mezzi?', 'pubblicato'),
    post('d2', 2, 'auto', 'Un\'ora al giorno a ricopiare ordini fa 220 ore l\'anno, se i giorni di lavoro sono 220.\n\nEsempio della demo.'),
    post('d4', 4, 'auto', '', 'da_scrivere'),
  ],
  linkedin_profilo: [{ utente: 'demo', nome: 'Dre', ruolo: 'Fondatore di Studio Galilei', temi: 'gestionali su misura' }],
  linkedin_persone: [
    { id: 'p1', giorno: giornoLocale(0), stato: 'da_fare', azienda: 'Noleggi Esempio Srl', settore: 'Noleggio attrezzature', citta: 'Treviso', persona: null, ruolo: 'Titolare', profilo: 'https://www.linkedin.com/in/esempio', cerca: null, perche: 'Esempio della demo: cerca un addetto all\'inserimento ordini.', fonte: null, segnale: 'annuncio', creato_il: alle(0, 7) },
    { id: 'p2', giorno: giornoLocale(-1), stato: 'da_fare', azienda: 'Consegne Esempio Spa', settore: 'Logistica', citta: 'Padova', persona: null, ruolo: 'Responsabile operativo', profilo: null, cerca: 'https://www.linkedin.com/search/results/people/?keywords=Consegne%20Esempio', perche: 'Esempio della demo: ha commentato un tuo post.', fonte: null, segnale: 'caldo', creato_il: alle(-1, 7) },
  ],
}

function campo(r: Riga, c: string) { return r[c] }

class Query {
  private filtri: Array<(r: Riga) => boolean> = []
  private ordine: { c: string; su: boolean } | null = null
  private max: number | null = null
  private patch: Riga | null = null
  private nuovo: Riga | null = null
  private uno = false
  private tabella: string
  constructor(tabella: string) { this.tabella = tabella }
  select() { return this }
  eq(c: string, v: unknown) { this.filtri.push((r) => campo(r, c) === v); return this }
  neq(c: string, v: unknown) { this.filtri.push((r) => campo(r, c) !== v); return this }
  in(c: string, v: unknown[]) { this.filtri.push((r) => v.includes(campo(r, c))); return this }
  gte(c: string, v: unknown) { this.filtri.push((r) => r[c] != null && String(r[c]) >= String(v)); return this }
  lte(c: string, v: unknown) { this.filtri.push((r) => r[c] != null && String(r[c]) <= String(v)); return this }
  order(c: string, o?: { ascending?: boolean }) { this.ordine = { c, su: o?.ascending !== false }; return this }
  limit(n: number) { this.max = n; return this }
  maybeSingle() { this.uno = true; return this }
  single() { this.uno = true; return this }
  insert(r: Riga) { this.nuovo = r; return this }
  update(r: Riga) { this.patch = r; return this }
  upsert(r: Riga) { this.nuovo = r; return this }
  then(risolvi: (r: { data: unknown; error: null }) => unknown) {
    TABELLE[this.tabella] ??= []
    let righe: Riga[]
    if (this.nuovo) {
      const r = { id: `demo-${Math.random().toString(36).slice(2, 8)}`, creato_il: new Date().toISOString(), versioni: [], ...this.nuovo }
      TABELLE[this.tabella].push(r); righe = [r]
    } else righe = TABELLE[this.tabella].filter((r) => this.filtri.every((f) => f(r)))
    if (this.patch) righe.forEach((r) => Object.assign(r, this.patch))
    if (this.ordine) { const { c, su } = this.ordine; righe = [...righe].sort((a, b) => (String(a[c]) < String(b[c]) ? -1 : 1) * (su ? 1 : -1)) }
    if (this.max != null) righe = righe.slice(0, this.max)
    return Promise.resolve(risolvi({ data: this.uno ? righe[0] ?? null : righe, error: null }))
  }
}

const urlFinti = new Map<string, string>()

export const demoClient = {
  from(tabella: string) { return new Query(tabella) },
  rpc(nome: string, args?: Riga) {
    if (nome === 'linkedin_programma') {
      const q = String(args?.quando ?? '')
      for (const x of TABELLE.linkedin_post) if (x.origine === 'auto' && String(x.uscita_il).slice(0, 10) === q.slice(0, 10)) x.stato = 'scartato'
      const r = TABELLE.linkedin_post.find((x) => x.id === args?.post)
      if (r) { r.uscita_il = q; r.stato = 'programmato'; r.testo = r.testo ?? r.dettato }
      return Promise.resolve({ data: { ok: true, uscita_il: q }, error: null })
    }
    return Promise.resolve({ data: null, error: null })
  },
  functions: { async invoke() { return { data: { ok: true, demo: true }, error: null } } },
  channel() { const c = { on: () => c, subscribe: () => c }; return c },
  async removeChannel() { return 'ok' },
  storage: {
    from() {
      return {
        async upload(path: string, file: File) { try { urlFinti.set(path, URL.createObjectURL(file)) } catch { /* niente */ } return { data: { path }, error: null } },
        async createSignedUrl(path: string) { return { data: { signedUrl: urlFinti.get(path) ?? '#' }, error: null } },
      }
    },
  },
  auth: {
    getSession: async () => ({ data: { session: { user: { id: 'demo', email: 'demo@studiogalilei', user_metadata: { full_name: 'Dre' } } } } }),
    getUser: async () => ({ data: { user: { id: 'demo', email: 'demo@studiogalilei', user_metadata: { full_name: 'Dre' } } }, error: null }),
    onAuthStateChange: () => ({ data: { subscription: { unsubscribe() {} } } }),
    signOut: async () => ({}),
    signInWithPassword: async () => ({ error: null }),
    signInWithOAuth: async () => ({ error: null }),
  },
}
