// CLARA FA IL PIANO (17/9/2026).
//
// Dre: «questo e' top per Clara dopo le call oppure per riprendere cose»,
// su una chat in cui delle idee sparse diventavano una lista di cose da
// fare giorno per giorno. L'idea e' quella: gli appunti di una call, o
// quello che uno si porta in testa da settimane, entrano qui e ne esce un
// piano corto con le date, che con un clic diventa task vere.
//
// Non decide niente: propone. Le task nascono solo quando la persona dice
// «crea», e ognuna la puo' togliere o spostare prima.
//
// COME SI METTE IN CLOUD (una volta):
//   npx supabase functions deploy piano --project-ref tqssfcuzezlczfceqsmk

import { createClient } from "npm:@supabase/supabase-js@2";

const URL = Deno.env.get("SUPABASE_URL")!;
const SERVIZIO = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const ANON = Deno.env.get("SUPABASE_ANON_KEY")!;
const OPENAI = Deno.env.get("OPENAI_API_KEY")!;
const MODELLO = Deno.env.get("MODELLO_OPENAI") ?? "gpt-5";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const risposta = (corpo: unknown, stato = 200) =>
  new Response(JSON.stringify(corpo), { status: stato, headers: { ...CORS, "Content-Type": "application/json" } });

const ISTRUZIONI = `Sei Clara, la segretaria di Studio Galilei (agenzia Google Ads).
Ti do quello che sappiamo di un cliente e degli appunti (una call, o idee sparse).
Tira fuori un piano corto, giorno per giorno, a partire da domani: le cose da fare
per portare avanti quello che si e' detto, nell'ordine giusto (prima quello che
sblocca il resto). Da 3 a 8 passi, non di piu'. Ogni passo e' una cosa sola,
concreta, che una persona fa in una seduta: comincia con un verbo («Mandare a
Zeni la lista degli accessi»), non «Gestire», non «Valutare».
Se una cosa e' gia' una task aperta, non la rimettere.
Le date: giorni lavorativi, al massimo tre settimane da oggi, formato AAAA-MM-GG.
Italiano informale, frasi corte, niente trattino lungo, niente puntino centrale,
niente punto esclamativo. Non inventare dati che non ci sono.

Rispondi SOLO con questo JSON, senza spiegazioni e senza blocchi di codice:
{"titolo": "una riga che dice di cosa e' il piano",
 "passi": [{"giorno": "AAAA-MM-GG", "titolo": "cosa fare", "perche": "una riga, perche' adesso"}]}`;

function pulisci(t: string): string {
  return t.replace(/\s*—\s*/g, ": ").replace(/\s*·\s*/g, ", ").replace(/–/g, "-").replace(/\s*!+/g, ".").replace(/\s{2,}/g, " ").trim();
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  const autorizzazione = req.headers.get("Authorization") ?? "";
  if (!autorizzazione) return risposta({ errore: "Non sei dentro" }, 401);
  const suo = createClient(URL, ANON, { global: { headers: { Authorization: autorizzazione } } });
  const { data: utente } = await suo.auth.getUser();
  if (!utente?.user) return risposta({ errore: "Non sei dentro" }, 401);

  const { prospect_id, testo, indicazione } = (await req.json().catch(() => ({}))) as
    { prospect_id?: string | null; testo?: string | null; indicazione?: string | null };
  if (!prospect_id && !(testo ?? "").trim()) return risposta({ errore: "Dimmi di che cliente, o scrivimi le idee" }, 400);

  const admin = createClient(URL, SERVIZIO);
  const pezzi: string[] = [];
  let azienda = "";
  if (prospect_id) {
    const [{ data: p }, { data: storia }, { data: progetti }, { data: task }] = await Promise.all([
      admin.from("prospects").select("company,name,email,sector,city,website,descrizione,pipeline_stage,stage,canone,contratto,notes,next_action,next_action_date,prova_fine").eq("id", prospect_id).maybeSingle(),
      admin.from("interactions").select("at,kind,body").eq("prospect_id", prospect_id).order("at", { ascending: false }).limit(12),
      admin.from("progetti").select("nome,natura,stato,scadenza,note,accessi_stato").eq("prospect_id", prospect_id).limit(10),
      admin.from("task").select("titolo,scadenza").eq("prospect_id", prospect_id).eq("fatta", false).limit(20),
    ]);
    azienda = p?.company || p?.name || "";
    if (p) pezzi.push("IL CLIENTE:\n" + JSON.stringify(p));
    if (storia?.length) {
      pezzi.push("COSA CI SIAMO DETTI (dal piu' recente; i transcript sono le call):\n" +
        storia.map((s) => `- [${(s.at ?? "").slice(0, 10)}, ${s.kind}] ${(s.body ?? "").slice(0, 1200)}`).join("\n"));
    }
    if (progetti?.length) pezzi.push("PROGETTI:\n" + JSON.stringify(progetti));
    if (task?.length) pezzi.push("TASK GIA' APERTE (non rimetterle):\n" + task.map((t) => `- ${t.titolo} (${t.scadenza ?? "senza data"})`).join("\n"));
  }
  if ((testo ?? "").trim()) pezzi.push("GLI APPUNTI / LE IDEE:\n" + (testo ?? "").trim().slice(0, 6000));
  pezzi.push("OGGI: " + new Date().toLocaleDateString("it-IT", { timeZone: "Europe/Rome", weekday: "long", day: "numeric", month: "long", year: "numeric" })
    + " (" + new Date().toISOString().slice(0, 10) + ")");

  const prompt = [
    ISTRUZIONI,
    indicazione?.trim() ? `COME LO VUOLE: ${indicazione.trim()}` : "",
    pezzi.join("\n\n"),
  ].filter(Boolean).join("\n\n");

  try {
    const r = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: { Authorization: `Bearer ${OPENAI}`, "Content-Type": "application/json" },
      body: JSON.stringify({ model: MODELLO, messages: [{ role: "user", content: prompt }] }),
    });
    if (!r.ok) return risposta({ errore: `Il cervello non risponde (${r.status})` }, 502);
    const d = await r.json();
    const grezzo = (d.choices?.[0]?.message?.content ?? "").trim();
    const json = grezzo.replace(/^```(json)?/i, "").replace(/```$/, "").trim();
    let fuori: { titolo?: string; passi?: Array<{ giorno?: string; titolo?: string; perche?: string }> };
    try { fuori = JSON.parse(json); } catch { return risposta({ errore: "Mi e' uscita una cosa storta, riprova" }); }
    const passi = (fuori.passi ?? [])
      .filter((x) => x && typeof x.titolo === "string" && x.titolo.trim())
      .slice(0, 8)
      .map((x) => ({
        giorno: /^\d{4}-\d{2}-\d{2}$/.test(x.giorno ?? "") ? x.giorno : null,
        titolo: pulisci(x.titolo ?? "").slice(0, 160),
        perche: pulisci(x.perche ?? "").slice(0, 200),
      }));
    if (passi.length === 0) return risposta({ errore: "Non ho trovato niente da mettere in fila, riprova a dirmelo diverso" });
    return risposta({ titolo: pulisci(fuori.titolo ?? (azienda ? `Il piano per ${azienda}` : "Il piano")).slice(0, 120), passi, azienda });
  } catch (e) {
    return risposta({ errore: String(e).slice(0, 160) }, 502);
  }
});
