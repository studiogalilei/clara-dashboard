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
{CHI}. Italiano informale e diretto, frasi corte, niente fuffa,
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

async function chiParla(owner: string | null): Promise<{ nome: string; ceo: boolean }> {
  if (!owner) return { nome: "Dre, il fondatore", ceo: true };
  const { data } = await sb.from("profili").select("nome,ruolo").eq("id", owner).maybeSingle();
  const nome = (data?.nome ?? "").split(" ")[0];
  const ceo = data?.ruolo === "ceo";
  if (!nome) return { nome: "Dre, il fondatore", ceo: true };
  return { nome: ceo ? `${nome}, uno dei due che guidano lo Studio` : `${nome}, del team di Studio Galilei`, ceo };
}

// IL DIARIO (12/9): se l'ultima cosa che Clara ha detto a questa persona era
// una domanda del diario (comincia con 📔), la risposta va nel diario, non a
// GPT. Un grazie breve, e basta.
async function eRispostaAlDiario(msg: { testo: string; owner: string | null }): Promise<boolean> {
  if (!msg.owner) return false;
  const { data } = await sb.from("clara_messaggi").select("tipo,testo").eq("owner", msg.owner)
    .neq("tipo", "dre").order("at", { ascending: false }).limit(1);
  const ultima = data?.[0];
  if (!ultima || ultima.tipo !== "domanda" || !String(ultima.testo).startsWith("📔")) return false;
  await sb.from("diario").insert({ user_id: msg.owner, domanda: String(ultima.testo).replace(/^📔\s*/, ""), testo: msg.testo });
  const grazie = ["Grazie, me lo segno. Lo leggono solo Dre e Giacomo.", "Preso, grazie. Resta tra noi e la direzione.", "Grazie, lo tengo. Se vuoi aggiungere altro, scrivi pure."];
  await sb.from("clara_messaggi").insert({ tipo: "clara", testo: grazie[Math.floor(Math.random() * grazie.length)], owner: msg.owner, letto: false });
  return true;
}

async function contesto(msg: { testo: string; owner: string | null; prospect_id: string | null }, ceo: boolean) {
  const pezzi: string[] = [];
  // la conversazione: la propria. Quella senza proprietario e' della direzione
  // (brief, promemoria, domande a Dre) e non si mostra agli altri
  const q = sb.from("clara_messaggi").select("tipo,testo");
  const { data: conv } = await (ceo
    ? q.or(msg.owner ? `owner.eq.${msg.owner},owner.is.null` : "owner.is.null")
    : q.eq("owner", msg.owner ?? "")).neq("tipo", "saluto").order("at", { ascending: false }).limit(14);
  pezzi.push("LA CONVERSAZIONE FINORA:\n" + (conv ?? []).reverse()
    .map((m) => `${m.tipo === "dre" ? "Dre" : "Clara"}: ${m.testo.replace(/\s+/g, " ").slice(0, 400)}`).join("\n"));

  let pid = msg.prospect_id ?? await trovaPersona(msg.testo);
  if (pid) {
    const { data: p } = await sb.from("prospects")
      .select("company,name,email,stage,pipeline_stage,classificazione,last_reply_at,next_action,next_action_date,canone,fuori,sg_id")
      .eq("id", pid).maybeSingle();
    const dentro = ceo || (p ? (p.fuori === true && ["tecnica", "avvio", "prova", "cliente"].includes(String(p.pipeline_stage))) : false);
    if (p && dentro) {
      const { canone: _canone, ...senzaSoldi } = p as Record<string, unknown>;
      pezzi.push("LA PERSONA DI CUI SI PARLA:\n" + JSON.stringify(ceo ? p : senzaSoldi));
      const { data: ult } = await sb.from("interactions").select("kind,body,at").eq("prospect_id", pid)
        .order("at", { ascending: false }).limit(4);
      if (ult?.length) pezzi.push("LE SUE ULTIME INTERAZIONI:\n" + ult.map((u) =>
        `- ${u.at.slice(0, 10)} [${u.kind}] ${(u.body ?? "").replace(/\s+/g, " ").slice(0, 300)}`).join("\n"));
    } else pid = null;
  }

  // la coda dei positivi e' lavoro di Dre e Giacomo: agli altri non si racconta
  const { data: caldi } = ceo ? await sb.from("prospects").select("company,name,last_reply_at")
    .eq("awaiting_us", true).eq("fuori", false).eq("classificazione", "positivo")
    .order("last_reply_at", { ascending: true }).limit(10) : { data: null };
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

const SEGRETO = Deno.env.get("CLARA_SEGRETO") ?? "";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

Deno.serve(async (req) => {
  // la funzione sta su --no-verify-jwt (la sveglia un trigger del database):
  // il segreto nell'intestazione e' l'unica porta. Senza, non si entra.
  if (!SEGRETO || req.headers.get("x-clara-segreto") !== SEGRETO) {
    return new Response("no", { status: 401 });
  }
  const corpo = await req.json().catch(() => ({}));
  const rec = corpo.record ?? corpo;             // il webhook manda {type, table, record}
  if (!rec?.testo || rec.tipo !== "dre") return new Response("niente da fare", { status: 200 });

  const owner = typeof rec.owner === "string" && UUID.test(rec.owner) ? rec.owner : null;
  const prospect_id = typeof rec.prospect_id === "string" && UUID.test(rec.prospect_id) ? rec.prospect_id : null;
  const msg = { testo: String(rec.testo).slice(0, 8000), owner, prospect_id };
  try {
    if (await eRispostaAlDiario(msg)) return new Response("diario", { status: 200 });
    const chi = await chiParla(msg.owner);
    const { testo: ctx, pid } = await contesto(msg, chi.ceo);
    const prompt = PERSONA.replace("{CHI}", chi.nome) + await istruzione("chat") + "\n\n" + ctx + "\n\n" + ISTRUZIONI +
      (chi.ceo ? "" : "\n\nChi ti scrive non e' Dre: e' una persona del team. Aiutala sul suo lavoro; le decisioni sulla pipeline restano a Dre e Giacomo.") +
      `\n\nL'ULTIMO MESSAGGIO DI ${chi.nome.split(",")[0].toUpperCase()}:\n` + msg.testo;
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
