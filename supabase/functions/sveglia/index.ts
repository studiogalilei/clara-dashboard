// LA SVEGLIA: Google bussa, Clara si sveglia (17/9/2026).
//
// Dre: «tutti gli update li voglio in realtime». Il direttore su GitHub
// passa ogni venti minuti; questa funzione lo fa partire SUBITO quando
// arriva una mail. Gmail avvisa Pub/Sub (scripts/orecchio.py tiene acceso
// l'orecchio), Pub/Sub chiama qui, e qui si bussa a GitHub con la catena
// giusta: posta (la mail entra), calendar (gli inviti arrivano per mail).
//
// Non legge la mail e non tocca il database: bussa e basta. Il segreto
// nell'indirizzo (?chiave=...) tiene fuori chi non e' Pub/Sub. Se c'e' gia'
// un direttore in coda, non se ne mette un altro: GitHub ne tiene uno
// solo in attesa e quello leggera' anche questa mail.
//
// IN CLOUD (fatto il 17/9 da Claude):
//   supabase functions deploy sveglia --no-verify-jwt
//   (usa gli stessi segreti di smartlead-webhook: GITHUB_DIRETTORE_TOKEN, WEBHOOK_SEGRETO)

const TOKEN = Deno.env.get("GITHUB_DIRETTORE_TOKEN") ?? "";
const SEGRETO = Deno.env.get("WEBHOOK_SEGRETO") ?? "";
const REPO = Deno.env.get("GITHUB_REPO") ?? "studiogalilei/clara-dashboard";
const GH = {
  "Authorization": `Bearer ${TOKEN}`,
  "Accept": "application/vnd.github+json",
  "User-Agent": "clara-dashboard",
};

async function inCoda(): Promise<boolean> {
  try {
    const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/direttore.yml/runs?status=queued&per_page=1`, { headers: GH });
    if (!r.ok) return false;
    const d = await r.json();
    return (d.total_count ?? 0) > 0;
  } catch {
    return false;
  }
}

async function sveglia(forza: string): Promise<number> {
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/direttore.yml/dispatches`, {
    method: "POST",
    headers: { ...GH, "Content-Type": "application/json" },
    body: JSON.stringify({ ref: "main", inputs: { forza } }),
  });
  return r.status;
}

Deno.serve(async (req) => {
  const url = new URL(req.url);
  if (!SEGRETO || url.searchParams.get("chiave") !== SEGRETO) return new Response("no", { status: 401 });
  if (req.method === "GET") return new Response("clara ascolta", { status: 200 });

  // Pub/Sub manda {message: {data: base64({emailAddress, historyId})}}
  const corpo = await req.json().catch(() => ({}));
  let chi = "";
  try {
    const dati = corpo?.message?.data ? JSON.parse(atob(corpo.message.data)) : {};
    chi = String(dati.emailAddress ?? "");
  } catch { /* non importa chi: si bussa lo stesso */ }
  const fonte = url.searchParams.get("fonte") ?? "gmail";
  const forza = fonte === "calendar" ? "calendar,preparo" : "posta,calendar";

  if (await inCoda()) {
    console.log(`${fonte} ${chi}: un direttore e' gia' in coda, leggera' anche questa`);
    return new Response("in coda", { status: 200 });
  }
  const stato = await sveglia(forza);
  console.log(`${fonte} ${chi} -> direttore ${forza}: github ${stato}`);
  // a Pub/Sub si risponde sempre 2xx: se no riprova all'infinito
  return new Response(JSON.stringify({ fonte, forza, github: stato }), {
    status: 200, headers: { "Content-Type": "application/json" },
  });
});
