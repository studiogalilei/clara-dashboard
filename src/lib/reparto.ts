// IL REPARTO (Dre, 26/9/2026). I colori sono quelli delle Brand Guidelines
// (capsula del 26/9): blu SG #061773, Marketing #D21205, Software #2F6B33, AI #0689FF.
// IL REPARTO (Dre, 26/9/2026): «in home sia albero bianco con fondo colore di
// colore reparto», e all'ingresso la schermata piena, come fa Smartlead, con il
// nome del reparto sotto. Il reparto sta sul profilo (schema_v60): qui ci sono
// solo i colori e i nomi, in un posto solo, perche' li usano l'apertura,
// l'icona in home e la barra di stato del telefono.

export type Reparto = 'direzione' | 'marketing' | 'software' | 'ai'

export const REPARTI: Record<Reparto, { nome: string; colore: string; scritta: string }> = {
  // Dre, Giacomo, Lorenzo: la scritta e' «StudioGalilei» secco, senza il reparto
  direzione: { nome: 'Direzione', colore: '#061773', scritta: 'StudioGalilei' },
  marketing: { nome: 'Marketing', colore: '#D21205', scritta: 'StudioGalilei Marketing' },
  software:  { nome: 'Software',  colore: '#2F6B33', scritta: 'StudioGalilei Software' },
  ai:        { nome: 'AI',        colore: '#0689FF', scritta: 'StudioGalilei AI' },
}

export const REPARTO_DEFAULT: Reparto = 'direzione'

export function reparto(v: string | null | undefined): Reparto {
  return v && v in REPARTI ? (v as Reparto) : REPARTO_DEFAULT
}

/** Il reparto di chi sta usando l'app, ricordato fra un avvio e l'altro: serve
 *  all'apertura, che parte prima che il profilo arrivi dal database. */
const CHIAVE = 'sg:reparto'

export function repartoRicordato(): Reparto {
  try { return reparto(localStorage.getItem(CHIAVE)) } catch { return REPARTO_DEFAULT }
}

export function ricordaReparto(v: string | null | undefined) {
  try {
    const r = reparto(v)
    localStorage.setItem(CHIAVE, r)
    vestiIlTelefono(r)
  } catch { /* niente */ }
}

/** L'icona in home e il colore della barra di stato seguono il reparto. */
export function vestiIlTelefono(r: Reparto) {
  const base = (import.meta.env.BASE_URL || '/').replace(/\/$/, '')
  const icona = `${base}/reparti/icona-${r}-512.png`
  const link = document.querySelectorAll('link[rel="apple-touch-icon"]')
  if (link.length) link.forEach((l) => l.setAttribute('href', `${base}/reparti/icona-${r}-192.png`))
  else { const l = document.createElement('link'); l.rel = 'apple-touch-icon'; l.href = `${base}/reparti/icona-${r}-192.png`; document.head.appendChild(l) }
  document.querySelectorAll('link[rel="icon"]').forEach((l) => l.setAttribute('href', `${base}/reparti/albero-${r}.svg`))
  let tema = document.querySelector('meta[name="theme-color"]')
  if (!tema) { tema = document.createElement('meta'); tema.setAttribute('name', 'theme-color'); document.head.appendChild(tema) }
  tema.setAttribute('content', REPARTI[r].colore)
  // il manifest si riscrive al volo: cosi' «Aggiungi a Home» prende l'icona giusta
  const vecchio = document.querySelector('link[rel="manifest"]')
  if (vecchio) {
    fetch(vecchio.getAttribute('href') || '').then((x) => x.json()).then((m) => {
      const nuovo = { ...m, theme_color: REPARTI[r].colore, background_color: REPARTI[r].colore,
                      icons: [{ src: `reparti/icona-${r}-192.png`, sizes: '192x192', type: 'image/png' },
                              { src: `reparti/icona-${r}-512.png`, sizes: '512x512', type: 'image/png' }] }
      const url = URL.createObjectURL(new Blob([JSON.stringify(nuovo)], { type: 'application/manifest+json' }))
      vecchio.setAttribute('href', url)
    }).catch(() => { /* niente: resta il manifest di partenza */ })
  }
  return icona
}
