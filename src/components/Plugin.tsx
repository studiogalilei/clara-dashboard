import { Card, Dot } from './ui'

// Plugin: lo stato dei collegamenti, a colpo d'occhio. Verde = collegato,
// ambra = aspetta qualcosa, grigio = da collegare (mai acceso non e' un guasto).
// Via le descrizioni fisse: erano didascalie, non davano ne' dato ne' feedback.

const RIGHE: Array<[string, 'ok' | 'attesa' | 'no', string]> = [
  ['Supabase', 'ok', 'collegato'],
  ['Smartlead', 'ok', 'collegato · Clara lo sorveglia ogni mattina'],
  ['Porkbun', 'ok', 'collegato · Clara lo sorveglia ogni mattina'],
  ['Google Ads API', 'ok', 'collegato'],
  ['Google Tasks', 'ok', 'collegato'],
  ['Google Calendar', 'attesa', 'aspetta la tua autorizzazione'],
  ['Granola', 'attesa', 'manuale: incolli tu il riassunto'],
  ['Zapmail', 'no', 'da collegare'],
]

export default function Plugin() {
  return (
    <div className="pb-24 sm:pb-8">
      <Card>
        {RIGHE.map(([nome, stato, nota]) => (
          <div key={nome} className="flex items-center gap-3 border-b border-velo px-4 py-3 last:border-0">
            <Dot tone={stato === 'ok' ? 'ok' : stato === 'attesa' ? 'attesa' : 'spento'} />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold">{nome}</p>
            </div>
            <span className={`shrink-0 text-xs ${
              stato === 'ok' ? 'text-green-700' : stato === 'attesa' ? 'font-semibold text-amber-700' : 'text-spento'
            }`}>
              {nota}
            </span>
          </div>
        ))}
      </Card>
    </div>
  )
}
