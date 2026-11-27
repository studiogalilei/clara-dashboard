// COLLEGA LINKEDIN (27/11/2026). Dre: «colleghiamo i post automatici».
// POST dal Desk (con il login della persona) -> {url}: l'indirizzo di LinkedIn dove la persona dice «Consenti».
// GET  da LinkedIn (?code&state) -> scambia il codice con il permesso (due mesi), legge chi e' (OpenID), lo salva e
// torna al Desk. Il permesso non esce mai da qui: lo usa solo linkedin-pubblica.
// IN CLOUD: supabase functions deploy linkedin-collega --no-verify-jwt  (segreti: LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET)
import { createClient } from "jsr:@supabase/supabase-js@2";

const ID = Deno.env.get("LINKEDIN_CLIENT_ID") ?? "";
const SEGRETO = Deno.env.get("LINKEDIN_CLIENT_SECRET") ?? "";
const RITORNO = `${Deno.env.get("SUPABASE_URL")}/functions/v1/linkedin-collega`;
const DESK = "https://www.studiogalilei.com/desk#/d/post";
const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type", "Access-Control-Allow-Methods": "GET, POST, OPTIONS" };

const torna = (esito: string) => Response.redirect(`${DESK}?linkedin=${encodeURIComponent(esito)}`, 302);

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

  if (req.method === "POST") {
    const jwt = (req.headers.get("authorization") ?? "").replace(/^Bearer /, "");
    const { data } = await db.auth.getUser(jwt);
    if (!data?.user) return Response.json({ errore: "entra nel Desk prima" }, { status: 401, headers: CORS });
    const stato = crypto.randomUUID();
    await db.from("linkedin_stati").delete().lt("creato_il", new Date(Date.now() - 15 * 60000).toISOString());
    await db.from("linkedin_stati").insert({ stato, utente: data.user.id });
    const q = new URLSearchParams({ response_type: "code", client_id: ID, redirect_uri: RITORNO, state: stato, scope: "openid profile w_member_social" });
    return Response.json({ url: `https://www.linkedin.com/oauth/v2/authorization?${q}` }, { headers: CORS });
  }

  const u = new URL(req.url);
  const codice = u.searchParams.get("code");
  const stato = u.searchParams.get("state") ?? "";
  if (!codice) return torna(u.searchParams.get("error") === "user_cancelled_authorize" ? "annullato" : "errore");
  const { data: biglietto } = await db.from("linkedin_stati").select("utente,creato_il").eq("stato", stato).maybeSingle();
  await db.from("linkedin_stati").delete().eq("stato", stato);
  if (!biglietto || Date.now() - new Date(biglietto.creato_il).getTime() > 15 * 60000) return torna("scaduto");

  const r = await fetch("https://www.linkedin.com/oauth/v2/accessToken", {
    method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ grant_type: "authorization_code", code: codice, redirect_uri: RITORNO, client_id: ID, client_secret: SEGRETO }),
  });
  const t = await r.json();
  if (!t.access_token) return torna("errore");
  const chi = await (await fetch("https://api.linkedin.com/v2/userinfo", { headers: { Authorization: `Bearer ${t.access_token}` } })).json();
  if (!chi.sub) return torna("errore");
  await db.from("linkedin_collegamento").upsert({
    utente: biglietto.utente, sub: chi.sub, nome: chi.name ?? null, token: t.access_token,
    scade_il: new Date(Date.now() + Number(t.expires_in ?? 5184000) * 1000).toISOString(), collegato_il: new Date().toISOString(),
  });
  return torna("collegato");
});
