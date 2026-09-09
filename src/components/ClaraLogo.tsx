import { useEffect, useState } from 'react'

// Il simbolo di Clara: la costellazione (logo ufficiale, 31/8), ridisegnata
// in SVG per poterla animare.
//
// Due stati (Dre, 2/9). A RIPOSO respira appena: l'acqua dentro i pallini
// si muove piano e qualcuno pulsa. MENTRE LAVORA la rete si sveglia:
// l'acqua accelera, la costellazione ruota lentissima e un impulso corre
// lungo i fili uno alla volta, come un pensiero che attraversa la rete.
// Il movimento non e' decorazione: dice che sta succedendo qualcosa, e si
// ferma quando ha finito. Con «riduci movimento» resta immobile.

interface Props {
  size?: number
  lavora?: boolean
}

// [x, y, raggio, durata del respiro in s (0 = fermo)]
const PUNTI: Array<[number, number, number, number]> = [
  [50, 10, 6, 3.1], [81, 26, 4, 0], [88, 54, 6.5, 4.2], [73, 84, 5.5, 0],
  [38, 88, 6, 3.6], [14, 68, 6.5, 0], [13, 36, 5.5, 4.8], [30, 14, 5, 0],
  [44, 32, 4.5, 3.9], [62, 38, 5, 0], [52, 52, 6, 3.3], [68, 58, 4, 0],
  [40, 60, 4, 4.5], [55, 72, 4.5, 0], [34, 46, 3.5, 3.7],
]

// i fili in ordine di percorso: l'impulso li accende cosi', uno dopo l'altro
const FILI: Array<[number, number, number, number]> = [
  [50, 10, 62, 38], [62, 38, 81, 26], [62, 38, 52, 52], [52, 52, 44, 32],
  [44, 32, 30, 14], [44, 32, 34, 46], [34, 46, 13, 36], [34, 46, 40, 60],
  [40, 60, 14, 68], [40, 60, 55, 72], [55, 72, 38, 88], [55, 72, 68, 58],
  [68, 58, 88, 54], [52, 52, 68, 58], [68, 58, 73, 84],
]

const GIRO = 2.1        // quanto ci mette l'impulso a fare tutta la rete
const ROTAZIONE = 22    // un giro completo della costellazione, lentissimo

export default function ClaraLogo({ size = 40, lavora = false }: Props) {
  const [ferma, setFerma] = useState(false)

  useEffect(() => {
    try {
      const m = window.matchMedia('(prefers-reduced-motion: reduce)')
      setFerma(m.matches)
      const su = (e: MediaQueryListEvent) => setFerma(e.matches)
      m.addEventListener('change', su)
      return () => m.removeEventListener('change', su)
    } catch { /* niente */ }
  }, [])

  const viva = !ferma
  const attiva = viva && lavora
  // il passo dell'impulso: ogni filo si accende un attimo dopo il precedente
  const passo = GIRO / FILI.length

  return (
    // la chiave rimonta l'SVG al cambio di stato, cosi' le animazioni
    // ripartono insieme invece di trovarsi a meta' strada
    <svg
      key={attiva ? 'lavora' : 'riposa'}
      viewBox="0 0 100 100"
      width={size}
      height={size}
      aria-label={lavora ? 'Clara sta lavorando' : 'Clara'}
    >
      {viva && (
        <defs>
          <filter id="clara-acqua" x="-20%" y="-20%" width="140%" height="140%">
            <feTurbulence
              type="fractalNoise"
              baseFrequency="0.014 0.02"
              numOctaves="2"
              seed="7"
              result="onde"
            >
              <animate
                attributeName="baseFrequency"
                dur={attiva ? '2.4s' : '10s'}
                values="0.014 0.02;0.022 0.013;0.014 0.02"
                repeatCount="indefinite"
              />
            </feTurbulence>
            <feDisplacementMap in="SourceGraphic" in2="onde" scale={attiva ? 4.5 : 3} />
          </filter>
        </defs>
      )}

      <g filter={viva ? 'url(#clara-acqua)' : undefined} stroke="currentColor" fill="none" strokeWidth="3">
        {/* il cerchio non gira mai: e' il contenitore, il pensiero sta dentro */}
        <circle cx="50" cy="50" r="40" />

        <g>
          {attiva && (
            <>
              <animateTransform
                attributeName="transform"
                type="rotate"
                from="0 50 50"
                to="360 50 50"
                dur={`${ROTAZIONE}s`}
                repeatCount="indefinite"
              />
              {/* e cambia forma (Dre, 9/9): la rete si stira e si stringe, fili e punti insieme */}
              <animateTransform
                attributeName="transform"
                type="scale"
                additive="sum"
                values="1 1;1.08 0.93;0.94 1.07;1.04 1.04;1 1"
                keyTimes="0;0.3;0.55;0.8;1"
                dur="3.6s"
                repeatCount="indefinite"
              />
              <animateTransform
                attributeName="transform"
                type="translate"
                additive="sum"
                values="0 0;-3 3;3 -3;-2 -2;0 0"
                keyTimes="0;0.3;0.55;0.8;1"
                dur="3.6s"
                repeatCount="indefinite"
              />
            </>
          )}

          {/* i fili: a riposo pieni, mentre lavora si abbassano e li
              riaccende l'impulso che passa */}
          <g strokeWidth="2.4">
            {FILI.map(([x1, y1, x2, y2], i) => (
              <line
                key={i}
                x1={x1} y1={y1} x2={x2} y2={y2}
                strokeOpacity={attiva ? 0.28 : 1}
                strokeLinecap="round"
              >
                {attiva && (
                  <>
                    <animate
                      attributeName="stroke-opacity"
                      dur={`${GIRO}s`}
                      values="0.28;1;0.28;0.28"
                      keyTimes="0;0.07;0.3;1"
                      begin={`${(i * passo).toFixed(2)}s`}
                      repeatCount="indefinite"
                    />
                    <animate
                      attributeName="stroke-width"
                      dur={`${GIRO}s`}
                      values="2.4;3.8;2.4;2.4"
                      keyTimes="0;0.07;0.3;1"
                      begin={`${(i * passo).toFixed(2)}s`}
                      repeatCount="indefinite"
                    />
                  </>
                )}
              </line>
            ))}
          </g>

          <g fill="currentColor" stroke="none">
            {PUNTI.map(([x, y, r, respiro], i) => {
              // mentre lavora respirano tutti, piu' svelti e sfasati
              const dur = attiva ? (respiro || 4) / 2.4 : respiro
              const cresce = attiva ? 1.32 : 1.18
              return (
                <circle key={i} cx={x} cy={y} r={r}>
                  {viva && dur > 0 && (
                    <animate
                      attributeName="r"
                      dur={`${dur.toFixed(2)}s`}
                      values={`${r};${(r * cresce).toFixed(1)};${r}`}
                      repeatCount="indefinite"
                      begin={`${((i % 5) * (attiva ? 0.16 : 0.6)).toFixed(2)}s`}
                    />
                  )}
                </circle>
              )
            })}
          </g>
        </g>
      </g>
    </svg>
  )
}
