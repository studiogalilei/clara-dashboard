// IL DISEGNO A MANO DELLE NOTE (27/11/2026).
//
// Il disegno del «sistema che immaginiamo» nella nota «Gestionale Operativo AI per <azienda>», nello stile scelto da Dre
// (il riferimento sta nello storage: linkedin/_stile/riferimento-stile.png). OpenAI gpt-image-2, qualita' media.
// Tetto: TETTO_MESE dollari al mese, contati nella tabella spesa_immagini. Oltre il tetto non disegna (mai crediti extra).
//   {scena, dre?} -> {png: base64, spesa_mese}   (dre: protagonista Dre, l'unico con il cappellino)
// IN CLOUD: supabase functions deploy linkedin-disegno   (segreto: OPENAI_API_KEY)
import { createClient } from "jsr:@supabase/supabase-js@2";

const CHIAVE = Deno.env.get("OPENAI_API_KEY") ?? "";
const TETTO_MESE = 4.0;   // 27/11: un post al giorno con il suo disegno (circa 1,40 $) piu' le note
const DRE =
  "The main character is Dre, drawn in exactly the same naive doodle style as the reference: a round head with dot eyes and a white unfilled face like everyone else (no skin colour fill), very short buzz-cut hair, a thin scribbled mustache joined to a small goatee, a black baseball cap worn backwards (he is the only one with a cap), royal blue #1532A8 sweatshirt, relaxed chill pose. ";
const COSTO = 0.063;
const STILE =
  "Draw a NEW scene in exactly the same drawing style as the reference image: same naive felt-pen doodle, same line weight, round heads with dot eyes, scribbled black hair, dot-pattern clothes, same amount of white space. Do not copy the reference scene or its people. " +
  "Very simple hand-drawn doodle illustration, black ink on plain white background. Few confident lines with a medium-thick felt pen, slightly wobbly like a quick human sketch. Simple cartoon people with big heads, dot eyes and minimal features. Almost no background: only the 2-4 objects the scene needs, floating on white. Very little detail, no hatching on walls or floors, at most a small patch of dot shading on one or two clothes. " +
  "One flat accent of royal blue #1532A8 and at most one tiny flat accent of warm yellow #FFC400, the rest black and white. Nobody wears a cap or a hat. No text, no letters, no logos, no 3D, no gradients, no realism, no engraving style. Lots of empty white space. Scene: ";

Deno.serve(async (req) => {
  if (!CHIAVE) return Response.json({ errore: "manca OPENAI_API_KEY" }, { status: 500 });
  const { scena, dre } = await req.json().catch(() => ({ scena: "", dre: false }));
  if (!scena || typeof scena !== "string" || scena.length > 900) return Response.json({ errore: "serve scena" }, { status: 400 });
  const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const mese = new Date().toISOString().slice(0, 7);
  const { data: riga } = await db.from("spesa_immagini").select("dollari,immagini").eq("mese", mese).maybeSingle();
  const gia = Number(riga?.dollari ?? 0);
  if (gia + COSTO > TETTO_MESE) return Response.json({ errore: `tetto del mese raggiunto (${gia.toFixed(2)} $ su ${TETTO_MESE} $)` }, { status: 429 });
  const { data: rif, error } = await db.storage.from("linkedin").download("_stile/riferimento-stile.png");
  if (error || !rif) return Response.json({ errore: "manca il disegno di riferimento nello storage" }, { status: 500 });
  const form = new FormData();
  form.append("model", "gpt-image-2");
  form.append("prompt", STILE.replace("Nobody wears a cap or a hat. ", dre ? "" : "Nobody wears a cap or a hat. ") + (dre ? DRE : "") + scena);
  form.append("size", "1536x1024");
  form.append("quality", "medium");
  form.append("n", "1");
  form.append("image[]", new File([rif], "rif.png", { type: "image/png" }));
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), 140000);
  try {
    const r = await fetch("https://api.openai.com/v1/images/edits", { method: "POST", headers: { Authorization: `Bearer ${CHIAVE}` }, body: form, signal: ctl.signal });
    const d = await r.json();
    if (!r.ok) return Response.json({ errore: d.error?.message ?? `OpenAI ${r.status}` }, { status: 502 });
    await db.from("spesa_immagini").upsert({ mese, dollari: gia + COSTO, immagini: Number(riga?.immagini ?? 0) + 1 });
    return Response.json({ png: d.data?.[0]?.b64_json, spesa_mese: +(gia + COSTO).toFixed(3) });
  } catch (e) {
    return Response.json({ errore: String(e) }, { status: 502 });
  } finally {
    clearTimeout(t);
  }
});
