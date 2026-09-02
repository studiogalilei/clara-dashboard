import { useEffect, useState } from 'react'

// Il simbolo di Clara: la costellazione (logo ufficiale, 31/8), ridisegnata
// in SVG per poterla animare. L'«acqua» dentro: una turbolenza continua
// deforma appena i pallini (effetto liquido) e alcuni respirano.
// Con "riduci movimento" attivo resta ferma.

export default function ClaraLogo({ size = 40 }: { size?: number }) {
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

  // rim = sul cerchio, dentro = la rete
  const punti: Array<[number, number, number, number]> = [
    // [x, y, raggio, durata del respiro in s (0 = fermo)]
    [50, 10, 6, 3.1], [81, 26, 4, 0], [88, 54, 6.5, 4.2], [73, 84, 5.5, 0],
    [38, 88, 6, 3.6], [14, 68, 6.5, 0], [13, 36, 5.5, 4.8], [30, 14, 5, 0],
    [44, 32, 4.5, 3.9], [62, 38, 5, 0], [52, 52, 6, 3.3], [68, 58, 4, 0],
    [40, 60, 4, 4.5], [55, 72, 4.5, 0], [34, 46, 3.5, 3.7],
  ]
  const fili: Array<[number, number, number, number]> = [
    [50, 10, 62, 38], [62, 38, 81, 26], [62, 38, 52, 52], [52, 52, 44, 32],
    [44, 32, 30, 14], [44, 32, 34, 46], [34, 46, 13, 36], [34, 46, 40, 60],
    [40, 60, 14, 68], [40, 60, 55, 72], [55, 72, 38, 88], [55, 72, 68, 58],
    [68, 58, 88, 54], [52, 52, 68, 58], [68, 58, 73, 84],
  ]

  return (
    <svg viewBox="0 0 100 100" width={size} height={size} aria-label="Clara">
      {!ferma && (
        <defs>
          <filter id="clara-acqua" x="-20%" y="-20%" width="140%" height="140%">
            <feTurbulence type="fractalNoise" baseFrequency="0.014 0.02" numOctaves="2" seed="7" result="onde">
              <animate
                attributeName="baseFrequency"
                dur="10s"
                values="0.014 0.02;0.022 0.013;0.014 0.02"
                repeatCount="indefinite"
              />
            </feTurbulence>
            <feDisplacementMap in="SourceGraphic" in2="onde" scale="3" />
          </filter>
        </defs>
      )}
      <g
        filter={ferma ? undefined : 'url(#clara-acqua)'}
        stroke="currentColor"
        fill="none"
        strokeWidth="3"
      >
        <circle cx="50" cy="50" r="40" />
        <g strokeWidth="2.4">
          {fili.map(([x1, y1, x2, y2], i) => (
            <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} />
          ))}
        </g>
        <g fill="currentColor" stroke="none">
          {punti.map(([x, y, r, respiro], i) => (
            <circle key={i} cx={x} cy={y} r={r}>
              {!ferma && respiro > 0 && (
                <animate
                  attributeName="r"
                  dur={`${respiro}s`}
                  values={`${r};${(r * 1.18).toFixed(1)};${r}`}
                  repeatCount="indefinite"
                  begin={`${(i % 5) * 0.6}s`}
                />
              )}
            </circle>
          ))}
        </g>
      </g>
    </svg>
  )
}
