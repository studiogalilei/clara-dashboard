// IL LINKEDIN DESK: bussa alla routine che scrive i post (27/11/2026).
//
// Dre registra dal telefono, la riga entra in linkedin_post, l'app chiama qui. Qui si controlla che sia il ceo e si
// fa partire subito la routine di Claude Code «LinkedIn Desk: scrivi i post» (abbonamento di Dre, niente API a
// consumo). Se il token della routine non c'e' o la routine non risponde, il post aspetta il giro di riserva orario.
//
// IN CLOUD: supabase functions deploy linkedin-scrivi  (con il controllo del JWT)
//   segreti: LINKEDIN_ROUTINE_ID, LINKEDIN_ROUTINE_TOKEN (il token API della routine, da claude.ai/code/routines)
import { createClient } from "jsr:@supabase/supabase-js@2";

const ROUTINE = Deno.env.get("LINKEDIN_ROUTINE_ID") ?? "";
const TOKEN = Deno.env.get("LINKEDIN_ROUTINE_TOKEN") ?? "";
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  const auth = req.headers.get("Authorization") ?? "";
  const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_ANON_KEY")!, { global: { headers: { Authorization: auth } } });
  const { data: ceo } = await sb.rpc("sono_ceo");
  if (ceo !== true) return new Response(JSON.stringify({ ok: false, perche: "solo il ceo" }), { status: 403, headers: CORS });
  if (!ROUTINE || !TOKEN) return new Response(JSON.stringify({ ok: true, subito: false, perche: "manca il token: giro di riserva" }), { headers: CORS });

  const r = await fetch(`https://api.anthropic.com/v1/claude_code/routines/${ROUTINE}/fire`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${TOKEN}`,
      "anthropic-version": "2023-06-01",
      "anthropic-beta": "experimental-cc-routine-2026-04-01",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ text: "Ci sono post nuovi da scrivere nel LinkedIn Desk." }),
  });
  return new Response(JSON.stringify({ ok: r.ok, subito: r.ok, stato: r.status }), { headers: CORS });
});
