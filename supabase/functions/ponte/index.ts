// IL PONTE: entrare nell'app sul telefono con un codice (17/10/2026).
//
// Dre, 17/10: «così posso scaricarlo come web app nel mio iPhone». Sull'iPhone l'app aggiunta
// alla Home ha la sua memoria, separata da Safari: chi e' gia' dentro in Safari, nell'app deve
// rientrare. Il link magico arriva per mail e si apre in Safari (non nell'app), e il ritorno da
// Google dentro l'app non lo posso provare io. Il ponte funziona sempre, tutto dentro l'app:
//   1. dove sei gia' dentro (computer, o Safari sul telefono) tocchi «Collega il telefono»:
//      ti da' un codice di 6 cifre che vale 10 minuti, una volta sola;
//   2. nell'app, sulla porta, «Entra con un codice»: lo scrivi e sei dentro.
// Nessuna mail parte: il codice diventa un link magico che si usa qui, dentro l'app.
//
// Sicurezza: il codice si salva solo come impronta (sha256), vale 10 minuti e una volta. Chi
// prova codici a caso si ferma: oltre 20 sbagliati in 10 minuti il ponte chiude per tutti
// finche' non passano (con un milione di codici possibili, 20 tentativi sono 1 su 50.000).
//
// COME SI METTE IN CLOUD (una volta, la tabella e' in supabase/schema_v91.sql):
//   SUPABASE_ACCESS_TOKEN=... npx supabase functions deploy ponte --project-ref tqssfcuzezlczfceqsmk --no-verify-jwt --use-api

import { createClient } from "npm:@supabase/supabase-js@2";

const URL = Deno.env.get("SUPABASE_URL")!;
const SERVIZIO = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const VALE_MINUTI = 10;
const TETTO_SBAGLIATI = 20;

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function risposta(corpo: unknown, stato = 200) {
  return new Response(JSON.stringify(corpo), { status: stato, headers: { ...CORS, "Content-Type": "application/json" } });
}

async function impronta(codice: string): Promise<string> {
  const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode("ponte:" + codice));
  return Array.from(new Uint8Array(b)).map((x) => x.toString(16).padStart(2, "0")).join("");
}

function seiCifre(): string {
  const n = new Uint32Array(1);
  // niente sbilanciamento: si scartano i numeri oltre l'ultimo multiplo di un milione
  do crypto.getRandomValues(n); while (n[0] >= 4_294_000_000);
  return String(n[0] % 1_000_000).padStart(6, "0");
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return risposta({ errore: "Solo POST" }, 405);
  const admin = createClient(URL, SERVIZIO, { auth: { persistSession: false } });
  const { azione, codice } = (await req.json().catch(() => ({}))) as { azione?: string; codice?: string };

  // 1. il codice, per chi e' gia' dentro
  if (azione === "crea") {
    const jwt = (req.headers.get("Authorization") ?? "").replace(/^Bearer\s+/i, "");
    const { data: chi } = jwt ? await admin.auth.getUser(jwt) : { data: { user: null } };
    const io = chi?.user;
    if (!io?.email) return risposta({ errore: "Non sei dentro: entra prima qui" }, 401);
    await admin.from("ponti").delete().eq("user_id", io.id).is("usato_il", null);   // uno valido alla volta
    const nuovo = seiCifre();
    const scade = new Date(Date.now() + VALE_MINUTI * 60_000).toISOString();
    const { error } = await admin.from("ponti").insert({ codice_hash: await impronta(nuovo), user_id: io.id, email: io.email, scade_il: scade });
    if (error) return risposta({ errore: "Non riesco a fare il codice: " + error.message }, 500);
    return risposta({ codice: nuovo, scade_il: scade, minuti: VALE_MINUTI });
  }

  // 2. il codice si usa, dentro l'app che deve entrare
  if (azione === "usa") {
    const pulito = String(codice ?? "").replace(/\D/g, "");
    const da = new Date(Date.now() - VALE_MINUTI * 60_000).toISOString();
    const { count } = await admin.from("ponti_tentativi").select("id", { count: "exact", head: true })
      .eq("riuscito", false).gte("il", da);
    if ((count ?? 0) >= TETTO_SBAGLIATI) return risposta({ errore: "Troppi codici sbagliati: riprova fra 10 minuti" }, 429);
    if (pulito.length !== 6) return risposta({ errore: "Il codice ha 6 cifre" }, 400);
    // si prende e si chiude in un colpo solo: lo stesso codice non entra due volte
    const { data: righe } = await admin.from("ponti").update({ usato_il: new Date().toISOString() })
      .eq("codice_hash", await impronta(pulito)).is("usato_il", null).gt("scade_il", new Date().toISOString())
      .select("email");
    const riga = (righe ?? [])[0] as { email: string } | undefined;
    await admin.from("ponti_tentativi").insert({ riuscito: Boolean(riga) });
    if (!riga) return risposta({ errore: "Codice sbagliato o scaduto: chiedine uno nuovo" }, 400);
    const { data, error } = await admin.auth.admin.generateLink({ type: "magiclink", email: riga.email });
    const token = data?.properties?.hashed_token;
    if (error || !token) return risposta({ errore: "Non riesco ad aprirti la porta: " + (error?.message ?? "riprova") }, 500);
    return risposta({ token_hash: token });
  }

  return risposta({ errore: "Azione sconosciuta" }, 400);
});
