// CLARA SCRIVE DENTRO IL DOCUMENTO (16/9/2026).
//
// Dre: «un pulsante per farmi aiutare da Clara, e lei spacca perche' ha
// accesso a tutto: ha i transcript di tutte le call, capisce com'e' la
// persona, e fa il documento clean, un po' in chill stile Gemini».
//
// Qui dentro: si prende il documento com'e' adesso (blocchi), si mette
// davanti a Clara tutto quello che sappiamo di quell'azienda (scheda, call,
// mail, progetti, preventivi), e torna lo stesso documento riscritto. Non
// inventa numeri e non tocca i blocchi che non c'entrano.
//
// COME SI METTE IN CLOUD (una volta):
//   npx supabase functions deploy documento --project-ref tqssfcuzezlczfceqsmk

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

// le regole della casa, le stesse del motore dei documenti
const TONO = `Scrivi in italiano, informale ma professionale, frasi corte e concrete.
VIETATI: il trattino lungo, il puntino centrale, il punto esclamativo, le parole
«innovativo», «all'avanguardia», «soluzioni concrete», «a 360», «chiavi in mano»,
«sinergia», «valore aggiunto», «eccellenza», «ottimizzare», «implementare».
Niente promesse di risultati numerici che non sono nei dati. Se un dato non c'e',
lascia il buco fra parentesi quadre invece di inventarlo.`;

const ISTRUZIONI = `Ti do un documento in JSON e quello che ci sappiamo sul cliente.
Riscrivi il documento tenendo la stessa struttura di blocchi: stessi tipi, stesso
ordine, puoi aggiungere blocchi solo se servono davvero.
Riempi i buchi fra parentesi quadre con quello che sai dai dati del cliente.
Quello che non sai resta fra parentesi quadre, uguale.
${TONO}

Rispondi SOLO con il JSON del documento, senza spiegazioni e senza blocchi di codice.`;

function pulisci(t: string): string {
  return t
    .replace(/\s*—\s*/g, ": ")
    .replace(/\s*·\s*/g, ", ")
    .replace(/–/g, "-")
    .replace(/\s*!+/g, ".")
    .replace(/\s{2,}/g, " ");
}

// ripulisce ogni stringa del documento: il modello ogni tanto ci prova
function ripulisciDoc(x: unknown): unknown {
  if (typeof x === "string") return pulisci(x);
  if (Array.isArray(x)) return x.map(ripulisciDoc);
  if (x && typeof x === "object") {
    const fuori: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(x)) fuori[k] = ripulisciDoc(v);
    return fuori;
  }
  return x;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  const autorizzazione = req.headers.get("Authorization") ?? "";
  if (!autorizzazione) return risposta({ errore: "Non sei dentro" }, 401);

  const suo = createClient(URL, ANON, { global: { headers: { Authorization: autorizzazione } } });
  const { data: utente } = await suo.auth.getUser();
  if (!utente?.user) return risposta({ errore: "Non sei dentro" }, 401);

  const { doc, prospect_id, richiesta } = (await req.json().catch(() => ({}))) as
    { doc?: Record<string, unknown>; prospect_id?: string | null; richiesta?: string };
  if (!doc || !Array.isArray((doc as { blocchi?: unknown }).blocchi)) {
    return risposta({ errore: "Manca il documento" }, 400);
  }

  // il contesto: quello che sappiamo di quell'azienda, letto a nome del
  // servizio (le call e le mail stanno dietro le regole del database, ma
  // qui serve leggerle per scrivere: non escono mai da questa risposta)
  const admin = createClient(URL, SERVIZIO);
  const pezzi: string[] = [];
  if (prospect_id) {
    const [{ data: p }, { data: storia }, { data: progetti }, { data: quote }] = await Promise.all([
      admin.from("prospects").select("company,name,email,sector,city,website,descrizione,pipeline_stage,stage,canone,contratto,notes,next_action").eq("id", prospect_id).maybeSingle(),
      admin.from("interactions").select("at,kind,body").eq("prospect_id", prospect_id).order("at", { ascending: false }).limit(18),
      admin.from("progetti").select("nome,natura,stato,valore,scadenza,note,imparato").eq("prospect_id", prospect_id).limit(10),
      admin.from("preventivi").select("numero,titolo,importo,mensile,stato,voci").eq("prospect_id", prospect_id).order("creato_il", { ascending: false }).limit(3),
    ]);
    if (p) pezzi.push("IL CLIENTE:\n" + JSON.stringify(p));
    if (storia?.length) {
      pezzi.push("COSA CI SIAMO DETTI (dal piu' recente; i transcript sono le call):\n" +
        storia.map((s) => `- [${(s.at ?? "").slice(0, 10)}, ${s.kind}] ${(s.body ?? "").slice(0, 900)}`).join("\n"));
    }
    if (progetti?.length) pezzi.push("PROGETTI:\n" + JSON.stringify(progetti));
    if (quote?.length) pezzi.push("PREVENTIVI:\n" + JSON.stringify(quote));
  }
  pezzi.push("OGGI: " + new Date().toLocaleDateString("it-IT", { timeZone: "Europe/Rome" }));

  const prompt = [
    ISTRUZIONI,
    richiesta?.trim() ? `QUELLO CHE TI HA CHIESTO:\n${richiesta.trim()}` : "QUELLO CHE TI HA CHIESTO:\nRiempi e sistema il documento con quello che sai.",
    pezzi.join("\n\n"),
    "IL DOCUMENTO ADESSO:\n" + JSON.stringify(doc),
  ].join("\n\n");

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
    let nuovo: unknown;
    try { nuovo = JSON.parse(json); } catch { return risposta({ errore: "Mi e' uscita una cosa storta, riprova" }); }
    const blocchi = (nuovo as { blocchi?: unknown }).blocchi;
    if (!Array.isArray(blocchi) || blocchi.length === 0) return risposta({ errore: "Non ho scritto niente di sensato, riprova a dirmelo diverso" });
    return risposta({ doc: ripulisciDoc(nuovo), detto: "Fatto. Ho scritto con quello che sapevo: guarda e correggi quello che non ti torna." });
  } catch (e) {
    return risposta({ errore: String(e).slice(0, 160) }, 502);
  }
});
