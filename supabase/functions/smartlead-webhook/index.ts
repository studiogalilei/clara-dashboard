// SMARTLEAD BUSSA, Clara si sveglia (10/9/2026).
//
// Dre: «voglio che le mail di Smartlead si vedano subito». Prima il runner
// in cloud guardava Smartlead ogni 15 minuti (e bruciava i minuti gratis di
// GitHub). Adesso e' Smartlead che, a ogni risposta, chiama questa funzione.
//
// 21/10 (Dre: «TUTTE le cose le voglio in realtime»): per una RISPOSTA (EMAIL_REPLY) la funzione
// fa partire risposta.yml con la mail del lead e la campagna: la strada veloce per un lead solo
// (scripts/risposta.py), mai annullata dal cron. Prima lanciava il direttore intero con la catena
// «sync, googlefit, analisi, bozze», e il cron ne annullava 2 su 3. Se nel payload non c'e' la
// mail, si ripiega sul direttore come prima. Gli altri eventi (categoria, rimbalzo, cancellazione)
// restano come prima: il sync, nel direttore.
//
// La funzione non legge la risposta e non tocca il database: bussa e basta.
// Il segreto nell'indirizzo (?chiave=...) tiene fuori chi non e' Smartlead.
//
// IN CLOUD:
//   supabase secrets set GITHUB_DIRETTORE_TOKEN=... WEBHOOK_SEGRETO=...
//   supabase functions deploy smartlead-webhook --no-verify-jwt
//   poi scripts/webhook_smartlead.py registra l'indirizzo su ogni campagna.

const TOKEN = Deno.env.get("GITHUB_DIRETTORE_TOKEN") ?? "";
const SEGRETO = Deno.env.get("WEBHOOK_SEGRETO") ?? "";
const REPO = Deno.env.get("GITHUB_REPO") ?? "studiogalilei/clara-dashboard";

// cosa far partire nel direttore per ogni evento di Smartlead (la rete, non la strada veloce)
const CATENA: Record<string, string> = {
  EMAIL_REPLY: "sync_smartlead,googlefit,analisi,bozze",   // solo se manca la mail del lead (21/10)
  LEAD_CATEGORY_UPDATED: "sync_smartlead",
  EMAIL_BOUNCE: "sync_smartlead",
  LEAD_UNSUBSCRIBED: "sync_smartlead",
};

async function dispatch(workflow: string, inputs: Record<string, string>): Promise<number> {
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${workflow}/dispatches`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${TOKEN}`,
      "Accept": "application/vnd.github+json",
      "User-Agent": "clara-dashboard",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ ref: "main", inputs }),
  });
  return r.status;
}

function sveglia(forza: string): Promise<number> {
  return dispatch("direttore.yml", { forza });
}

// la mail del lead, con i nomi che Smartlead usa nei suoi payload (quelli visti, poi quelli
// documentati): sl_lead_email, lead_email, to_email (nella documentazione dell'EMAIL_REPLY il
// lead e' «to_email»), lead_data.email. Minuscola, senza spazi.
function mailDelLead(corpo: Record<string, unknown>): string {
  const dati = (corpo.lead_data ?? {}) as Record<string, unknown>;
  for (const v of [corpo.sl_lead_email, corpo.lead_email, corpo.to_email, dati.email]) {
    const s = String(v ?? "").trim().toLowerCase();
    if (s.includes("@")) return s;
  }
  return "";
}

Deno.serve(async (req) => {
  const url = new URL(req.url);
  if (!SEGRETO || url.searchParams.get("chiave") !== SEGRETO) {
    return new Response("no", { status: 401 });
  }
  if (req.method === "GET") return new Response("clara ascolta", { status: 200 });

  const corpo = (await req.json().catch(() => ({}))) as Record<string, unknown>;
  const evento = String(corpo.event_type ?? corpo.eventType ?? url.searchParams.get("evento") ?? "EMAIL_REPLY").toUpperCase();
  const forza = CATENA[evento];
  if (!forza) return new Response(`evento ${evento}: niente da fare`, { status: 200 });

  if (evento === "EMAIL_REPLY") {
    const email = mailDelLead(corpo);
    // i nomi dei campi, mai i valori: per sapere cosa manda davvero Smartlead (21/10)
    console.log(`smartlead EMAIL_REPLY campi: ${Object.keys(corpo).sort().join(",")}`);
    if (email) {
      const oppure = String(corpo.from_email ?? "").trim().toLowerCase();
      const inputs = {
        email,
        campagna: String(corpo.campaign_id ?? ""),
        evento,
        oppure: oppure.includes("@") && oppure !== email ? oppure : "",
        bussato: new Date().toISOString(),
        risposta_il: String(corpo.time_replied ?? corpo.event_timestamp ?? ""),
      };
      const stato = await dispatch("risposta.yml", inputs);
      console.log(`smartlead EMAIL_REPLY → risposta.yml (campagna ${inputs.campagna || "?"}): github ${stato}`);
      if (stato === 204) {
        return new Response(JSON.stringify({ evento, strada: "veloce", github: stato }), {
          status: 200, headers: { "Content-Type": "application/json" },
        });
      }
      console.log(`risposta.yml non partita (${stato}): ripiego sul direttore`);
    } else {
      console.log("smartlead EMAIL_REPLY senza la mail del lead: ripiego sul direttore");
    }
  }

  const stato = await sveglia(forza);
  console.log(`smartlead ${evento} → direttore ${forza}: github ${stato}`);
  return new Response(JSON.stringify({ evento, forza, github: stato }), {
    status: stato === 204 ? 200 : 502,
    headers: { "Content-Type": "application/json" },
  });
});
