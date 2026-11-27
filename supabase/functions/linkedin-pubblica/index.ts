// PUBBLICA SU LINKEDIN (27/11/2026). Ogni 5 minuti (pg_cron, v127): i post «programmato» arrivati alla loro ora escono
// sul profilo di chi li firma, con la foto se c'e'. Dre: «colleghiamo i post automatici».
// Esce solo cio' che la persona ha in calendario: niente si pubblica senza un'ora scelta o accettata nel Desk.
// Un post piu' vecchio di 6 ore non esce piu' da solo (se il giro si e' fermato non escono tutti insieme dopo).
// IN CLOUD: supabase functions deploy linkedin-pubblica --no-verify-jwt   (segreto: PUBBLICA_SEGRETO, uguale al vault)
import { createClient } from "jsr:@supabase/supabase-js@2";

const SEGRETO = Deno.env.get("PUBBLICA_SEGRETO") ?? "";
const VERSIONE = "202606";

// LinkedIn legge il testo come «little text»: questi caratteri vanno protetti, se no tagliano il post
const pulisci = (s: string) => s.replace(/[\\|{}@\[\]()<>#*_~]/g, (c) => "\\" + c);

async function li(percorso: string, token: string, init: RequestInit = {}) {
  return await fetch(`https://api.linkedin.com${percorso}`, {
    ...init,
    headers: { Authorization: `Bearer ${token}`, "LinkedIn-Version": VERSIONE, "X-Restli-Protocol-Version": "2.0.0", "Content-Type": "application/json", ...(init.headers ?? {}) },
  });
}

Deno.serve(async (req) => {
  if (!SEGRETO || req.headers.get("x-segreto") !== SEGRETO) return new Response("no", { status: 401 });
  const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const ora = new Date();
  const { data: posts } = await db.from("linkedin_post").select("id,autore,testo,versioni,scelta,foto,uscita_il")
    .eq("stato", "programmato").lte("uscita_il", ora.toISOString()).gte("uscita_il", new Date(ora.getTime() - 6 * 3600000).toISOString()).limit(10);
  const esiti: unknown[] = [];
  for (const p of posts ?? []) {
    const { data: c } = await db.from("linkedin_collegamento").select("sub,token,scade_il").eq("utente", p.autore).maybeSingle();
    if (!c || new Date(c.scade_il) < ora) { esiti.push({ id: p.id, saltato: "profilo non collegato" }); continue; }
    const testo = (p.testo ?? (p.versioni ?? [])[p.scelta ?? 0]?.testo ?? "").trim();
    if (!testo) { await db.from("linkedin_post").update({ stato: "errore", errore: "Il post non ha testo." }).eq("id", p.id); continue; }
    // prima lo segno, cosi' un secondo giro non lo pubblica due volte
    const { data: preso } = await db.from("linkedin_post").update({ stato: "pubblicato", pubblicato_il: ora.toISOString() }).eq("id", p.id).eq("stato", "programmato").select("id");
    if (!preso?.length) continue;
    try {
      const autore = `urn:li:person:${c.sub}`;
      let media: string | null = null;
      if (p.foto) {
        const { data: file } = await db.storage.from("linkedin").download(p.foto);
        if (file) {
          const ini = await (await li("/rest/images?action=initializeUpload", c.token, { method: "POST", body: JSON.stringify({ initializeUploadRequest: { owner: autore } }) })).json();
          const su = await fetch(ini.value.uploadUrl, { method: "PUT", headers: { Authorization: `Bearer ${c.token}` }, body: await file.arrayBuffer() });
          if (su.ok) media = ini.value.image;
        }
      }
      const corpo: Record<string, unknown> = {
        author: autore, commentary: pulisci(testo), visibility: "PUBLIC",
        distribution: { feedDistribution: "MAIN_FEED", targetEntities: [], thirdPartyDistributionChannels: [] },
        lifecycleState: "PUBLISHED", isReshareDisabledByAuthor: false,
        ...(media ? { content: { media: { id: media } } } : {}),
      };
      const r = await li("/rest/posts", c.token, { method: "POST", body: JSON.stringify(corpo) });
      if (!r.ok) throw new Error(`LinkedIn ${r.status}: ${(await r.text()).slice(0, 200)}`);
      const urn = r.headers.get("x-restli-id") ?? "";
      await db.from("linkedin_post").update({ linkedin_urn: urn, errore: null }).eq("id", p.id);
      esiti.push({ id: p.id, urn });
    } catch (e) {
      await db.from("linkedin_post").update({ stato: "errore", pubblicato_il: null, errore: `Non sono riuscito a pubblicarlo: ${String(e).slice(0, 220)}` }).eq("id", p.id);
      esiti.push({ id: p.id, errore: String(e) });
    }
  }
  return Response.json({ esiti });
});
