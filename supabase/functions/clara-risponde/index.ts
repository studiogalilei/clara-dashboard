// CLARA RISPONDE, in cloud (7/9/2026).
//
// Quando Dre scrive nella chat, il database chiama questa funzione (un
// webhook sull'inserimento in clara_messaggi con tipo 'dre'). Lei legge la
// conversazione, la persona di cui si parla, chi aspetta da piu' tempo, le
// istruzioni di Dre, e risponde in pochi secondi. Da qualunque dispositivo,
// col Mac di Dre spento: e' il sostituto di scripts/clara_ascolta.py, che
// girava sul suo Mac come ponte.
//
// Non tocca la pipeline: se dalla conversazione esce una cosa da fare, la
// mette nella stanza come proposta e Dre conferma da li'.
//
// COME SI METTE IN CLOUD (una volta):
//   supabase login                      (serve l'access token di Dre)
//   supabase link --project-ref tqssfcuzezlczfceqsmk
//   supabase secrets set OPENAI_API_KEY=... MODELLO_OPENAI=gpt-5
//   supabase functions deploy clara-risponde --no-verify-jwt
//   poi, nel progetto: Database → Webhooks → nuovo, su clara_messaggi INSERT,
//   che chiama questa funzione.

import { createClient } from "npm:@supabase/supabase-js@2";

const URL = Deno.env.get("SUPABASE_URL")!;
const CHIAVE = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const OPENAI = Deno.env.get("OPENAI_API_KEY")!;
const MODELLO = Deno.env.get("MODELLO_OPENAI") ?? "gpt-5";
const sb = createClient(URL, CHIAVE);

const PERSONA = `Sei Clara, la segretaria di Studio Galilei (agenzia Google Ads). Parli con
Dre, il fondatore. Italiano informale e diretto, frasi corte, niente fuffa,
niente elenchi puntati se non servono, mai il trattino lungo. Dai del tu.
Non inventare dati: se non sai una cosa lo dici. Se Dre ti chiede di fare
qualcosa che cambia la pipeline (spostare, scartare, segnare perso, cambiare
una classificazione) NON dire che l'hai fatto: di' che glielo metti nella tua
stanza come proposta, e lui conferma da li'.`;

const ISTRUZIONI = `Rispondi a Dre. Massimo 4 righe, a meno che non chieda un elenco.
Se nella conversazione c'e' una cosa concreta da fare sulla pipeline, chiudi
la risposta con UNA riga nel formato esatto, da sola:
PROPOSTA | tipo | titolo | perche
dove tipo e' uno fra: classifica, scarta, perso, tornato, richiesta, data, avanza.
Se non c'e' niente da proporre, non scrivere quella riga.`;

const COMUNI = new Set(["Ciao", "Clara", "Dre", "Cosa", "Come", "Quando", "Chi", "Perche", "Allora", "Grazie"]);

function pulisci(t: string): string {
  return t.replace(/\s*—\s*/g, ": ").replace(/–/g, "-");   // la stessa di regole.ts
}

async function istruzione(chiave: string): Promise<string> {
  const { data } = await sb.from("istruzioni").select("testo").eq("chiave", chiave).maybeSingle();
  const t = (data?.testo ?? "").trim();
  return t ? `\n\nISTRUZIONI DI DRE (${chiave}), che vincono su tutto il resto:\n${t}` : "";
}

async function trovaPersona(testo: string): Promise<string | null> {
  const maiuscole = (testo.match(/\b[A-ZÀ-Ý][\w&'.-]{2,}/g) ?? []).filter((w) => !COMUNI.has(w));
  const candidati = [
    ...maiuscole.slice(0, -1).map((a, i) => `${a} ${maiuscole[i + 1]}`),
    ...[...maiuscole].sort((a, b) => b.length - a.length),
  ].slice(0, 10);
  for (const w of candidati) {
    const { data } = await sb.from("prospects").select("id").ilike("company", `%${w}%`)
      .order("last_reply_at", { ascending: false, nullsFirst: false }).limit(1);
    if (data?.[0]) return data[0].id;
  }
  return null;
}

async function contesto(msg: { testo: string; owner: string | null; prospect_id: string | null }) {
  const pezzi: string[] = [];
  const filtro = msg.owner ? `owner.eq.${msg.owner},owner.is.null` : "owner.is.null";
  const { data: conv } = await sb.from("clara_messaggi").select("tipo,testo").or(filtro)
    .neq("tipo", "saluto").order("at", { ascending: false }).limit(14);
  pezzi.push("LA CONVERSAZIONE FINORA:\n" + (conv ?? []).reverse()
    .map((m) => `${m.tipo === "dre" ? "Dre" : "Clara"}: ${m.testo.replace(/\s+/g, " ").slice(0, 400)}`).join("\n"));

  let pid = msg.prospect_id ?? await trovaPersona(msg.testo);
  if (pid) {
    const { data: p } = await sb.from("prospects")
      .select("company,name,email,stage,pipeline_stage,classificazione,last_reply_at,next_action,next_action_date,canone,fuori,sg_id")
      .eq("id", pid).maybeSingle();
    if (p) {
      pezzi.push("LA PERSONA DI CUI SI PARLA:\n" + JSON.stringify(p));
      const { data: ult } = await sb.from("interactions").select("kind,body,at").eq("prospect_id", pid)
        .order("at", { ascending: false }).limit(4);
      if (ult?.length) pezzi.push("LE SUE ULTIME INTERAZIONI:\n" + ult.map((u) =>
        `- ${u.at.slice(0, 10)} [${u.kind}] ${(u.body ?? "").replace(/\s+/g, " ").slice(0, 300)}`).join("\n"));
    } else pid = null;
  }

  const { data: caldi } = await sb.from("prospects").select("company,name,last_reply_at")
    .eq("awaiting_us", true).eq("fuori", false).eq("classificazione", "positivo")
    .order("last_reply_at", { ascending: true }).limit(10);
  if (caldi?.length) pezzi.push("I POSITIVI CHE ASPETTANO UNA RISPOSTA DA PIU' TEMPO (dal piu' vecchio):\n" +
    caldi.map((c) => `- ${c.company ?? c.name}: ultima sua mail ${(c.last_reply_at ?? "").slice(0, 10)}`).join("\n"));
  pezzi.push("OGGI: " + new Date().toLocaleString("it-IT", { timeZone: "Europe/Rome" }));
  return { testo: pezzi.join("\n\n"), pid };
}

async function chiedi(prompt: string): Promise<string> {
  const r = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: { "Authorization": `Bearer ${OPENAI}`, "Content-Type": "application/json" },
    body: JSON.stringify({ model: MODELLO, messages: [{ role: "user", content: prompt }] }),
  });
  if (!r.ok) throw new Error(`OpenAI ${r.status}: ${(await r.text()).slice(0, 200)}`);
  const d = await r.json();
  return d.choices?.[0]?.message?.content ?? "";
}

const RIGA_PROPOSTA = /^\s*PROPOSTA\s*\|\s*(\w+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*$/gm;
const TIPI = new Set(["classifica", "scarta", "perso", "tornato", "richiesta", "data", "avanza"]);

Deno.serve(async (req) => {
  const corpo = await req.json().catch(() => ({}));
  const rec = corpo.record ?? corpo;             // il webhook manda {type, table, record}
  if (!rec?.testo || rec.tipo !== "dre") return new Response("niente da fare", { status: 200 });

  const msg = { testo: rec.testo as string, owner: rec.owner ?? null, prospect_id: rec.prospect_id ?? null };
  try {
    const { testo: ctx, pid } = await contesto(msg);
    const prompt = PERSONA + await istruzione("chat") + "\n\n" + ctx + "\n\n" + ISTRUZIONI +
      "\n\nL'ULTIMO MESSAGGIO DI DRE:\n" + msg.testo;
    const grezzo = (await chiedi(prompt)).trim();

    for (const m of grezzo.matchAll(RIGA_PROPOSTA)) {
      const [, tipo, titolo, perche] = m;
      if (!TIPI.has(tipo)) continue;
      const { data: gia } = await sb.from("proposte").select("id").eq("stato", "aperta").eq("tipo", tipo)
        .eq("prospect_id", pid ?? "00000000-0000-0000-0000-000000000000").limit(1);
      if (!gia?.length) await sb.from("proposte").insert({
        tipo, titolo: titolo.slice(0, 200), perche: perche.slice(0, 300), prospect_id: pid, owner: msg.owner,
      });
    }
    const testo = grezzo.replace(RIGA_PROPOSTA, "").trim() || "Fatto: te l'ho messa nella mia stanza, confermi da li'.";
    await sb.from("clara_messaggi").insert({ tipo: "clara", testo: pulisci(testo), prospect_id: pid, owner: msg.owner, letto: false });
    return new Response("ok", { status: 200 });
  } catch (e) {
    await sb.from("clara_messaggi").insert({
      tipo: "controllo", testo: "Non riesco a pensare adesso: il cervello non risponde. Riprovo fra poco.",
      owner: msg.owner, letto: false,
    });
    return new Response(String(e), { status: 500 });
  }
});
