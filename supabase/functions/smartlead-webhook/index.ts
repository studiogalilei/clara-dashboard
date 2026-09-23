// SMARTLEAD BUSSA, Clara si sveglia (10/9/2026).
//
// Dre: «voglio che le mail di Smartlead si vedano subito». Prima il runner
// in cloud guardava Smartlead ogni 15 minuti (e bruciava i minuti gratis di
// GitHub). Adesso e' Smartlead che, a ogni risposta, chiama questa funzione;
// lei fa partire subito il direttore su GitHub con la catena giusta:
// sync (la risposta entra), google fit (Clara valuta), bozze (Clara scrive).
// Il cron di GitHub resta ogni ora come rete di sicurezza.
//
// La funzione non legge la risposta e non tocca il database: bussa e basta.
// Il segreto nell'indirizzo (?chiave=...) tiene fuori chi non e' Smartlead.
//
// IN CLOUD (fatto il 10/9 da Claude con l'access token di Dre):
//   supabase secrets set GITHUB_DIRETTORE_TOKEN=... WEBHOOK_SEGRETO=...
//   supabase functions deploy smartlead-webhook --no-verify-jwt
//   poi scripts/webhook_smartlead.py registra l'indirizzo su ogni campagna.

const TOKEN = Deno.env.get("GITHUB_DIRETTORE_TOKEN") ?? "";
const SEGRETO = Deno.env.get("WEBHOOK_SEGRETO") ?? "";
const REPO = Deno.env.get("GITHUB_REPO") ?? "studiogalilei/clara-dashboard";

// cosa far partire per ogni evento di Smartlead
const CATENA: Record<string, string> = {
  EMAIL_REPLY: "sync_smartlead,googlefit,analisi,bozze",   // 23/9: l'analisi prima della bozza
  LEAD_CATEGORY_UPDATED: "sync_smartlead",
  EMAIL_BOUNCE: "sync_smartlead",
  LEAD_UNSUBSCRIBED: "sync_smartlead",
};

async function sveglia(forza: string): Promise<number> {
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/direttore.yml/dispatches`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${TOKEN}`,
      "Accept": "application/vnd.github+json",
      "User-Agent": "clara-dashboard",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ ref: "main", inputs: { forza } }),
  });
  return r.status;
}

Deno.serve(async (req) => {
  const url = new URL(req.url);
  if (!SEGRETO || url.searchParams.get("chiave") !== SEGRETO) {
    return new Response("no", { status: 401 });
  }
  if (req.method === "GET") return new Response("clara ascolta", { status: 200 });

  const corpo = await req.json().catch(() => ({}));
  const evento = String(corpo.event_type ?? corpo.eventType ?? url.searchParams.get("evento") ?? "EMAIL_REPLY").toUpperCase();
  const forza = CATENA[evento];
  if (!forza) return new Response(`evento ${evento}: niente da fare`, { status: 200 });

  const stato = await sveglia(forza);
  console.log(`smartlead ${evento} → direttore ${forza}: github ${stato}`);
  return new Response(JSON.stringify({ evento, forza, github: stato }), {
    status: stato === 204 ? 200 : 502,
    headers: { "Content-Type": "application/json" },
  });
});
