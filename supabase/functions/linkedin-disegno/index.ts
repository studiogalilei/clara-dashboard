// IL DISEGNO A MANO DELLE NOTE (27/11/2026).
//
// Il disegno del «sistema che immaginiamo» nella nota «Gestionale Operativo AI per <azienda>», nello stile scelto da Dre
// (il riferimento sta nello storage: linkedin/_stile/riferimento-stile.png). OpenAI gpt-image-2, qualita' media.
// Tetto: TETTO_MESE dollari al mese, contati nella tabella spesa_immagini. Oltre il tetto non disegna (mai crediti extra).
//   {scena, dre?, stile?} -> {png: base64, spesa_mese}   (dre: protagonista Dre, l'unico con il cappellino)
// stile (Dre, 27/11 notte, per i post di attualita'): "disegno" (il nostro, col riferimento), "foto" (foto realistica da
// giornale, mai persone vere riconoscibili ne' eventi inventati), "meme" (originale, mai template famosi), "scheda"
// (il numero grande con la fonte, nei nostri colori).
// {modello, righe} -> un meme nei formati che esistono gia' (Dre: «meglio i formati di meme che esistono»), fatto da
// memegen.link (open source, gratis, nessuna chiave): modello = id di memegen (drake, fine, gru, buzz...), righe = testi.
// IN CLOUD: supabase functions deploy linkedin-disegno   (segreto: OPENAI_API_KEY)
import { createClient } from "jsr:@supabase/supabase-js@2";

const CHIAVE = Deno.env.get("OPENAI_API_KEY") ?? "";
const TETTO_MESE = 4.0;   // 27/11: un post al giorno con il suo disegno (circa 1,40 $) piu' le note
const DRE =
  "The main character is Dre, drawn in exactly the same naive doodle style as the reference: a round head with dot eyes and a white unfilled face like everyone else (no skin colour fill), very short buzz-cut hair, a thin scribbled mustache joined to a small goatee, a black baseball cap worn backwards (he is the only one with a cap), royal blue #1532A8 sweatshirt, relaxed chill pose. ";
const COSTO = 0.063;
const ALTRI: Record<string, { prompt: string; size: string }> = {
  foto: {
    size: "1536x1024",
    prompt: "Photorealistic editorial photograph for a business news article, as if shot by a newspaper photojournalist on a 35mm camera: natural available light, true-to-life muted colours, slight film grain, shallow depth of field, candid and slightly imperfect composition, real Italian small-business setting. No text, no logos, no brand names, no screens with readable text. No recognizable real people or celebrities: people only from behind, as hands, or out of focus in the background. No AI look: no glossy skin, no perfect symmetry, no surreal or futuristic elements, no glowing lights. Scene: ",
  },
  meme: {
    size: "1024x1024",
    prompt: "An original internet meme image in the classic style: one picture (photographic or simple cartoon) with the caption written in bold white Impact-style capital letters with a thin black outline, at the top and/or bottom. Write the caption text EXACTLY as given, in Italian, with correct spelling and accents, and nothing else written anywhere. Do not use any famous meme template, celebrity, real person or copyrighted character: invent an original scene. Light office humour about work and technology, nothing offensive. Picture and caption: ",
  },
  scheda: {
    size: "1024x1024",
    prompt: "A clean flat data card for a LinkedIn post. Plain white background, generous margins, no illustrations, no icons, no gradients, no shadows. One huge number in a bold geometric sans-serif (like Montserrat Black) in royal blue #1532A8, under it one short line of black text in a clean sans-serif, and at the bottom a small source line in black. A thin warm yellow #FFC400 bar under the number. Write EXACTLY these texts, in Italian, with correct spelling and accents, and nothing else: ",
  },
};
const STILE =
  "Draw a NEW scene in exactly the same drawing style as the reference image: same naive felt-pen doodle, same line weight, round heads with dot eyes, scribbled black hair, dot-pattern clothes, same amount of white space. Do not copy the reference scene or its people. " +
  "Very simple hand-drawn doodle illustration, black ink on plain white background. Few confident lines with a medium-thick felt pen, slightly wobbly like a quick human sketch. Simple cartoon people with big heads, dot eyes and minimal features. Almost no background: only the 2-4 objects the scene needs, floating on white. Very little detail, no hatching on walls or floors, at most a small patch of dot shading on one or two clothes. " +
  "One flat accent of royal blue #1532A8 and at most one tiny flat accent of warm yellow #FFC400, the rest black and white. Nobody wears a cap or a hat. No text, no letters, no logos, no 3D, no gradients, no realism, no engraving style. Lots of empty white space. Scene: ";

// memegen vuole i testi nell'indirizzo: spazi -> _, e alcuni segni con il loro codice
function perMemegen(t: string): string {
  const pezzi = t.trim() || "_";
  return encodeURIComponent(pezzi.replace(/_/g, "__").replace(/-/g, "--").replace(/ /g, "_").replace(/\?/g, "~q")
    .replace(/%/g, "~p").replace(/#/g, "~h").replace(/\//g, "~s").replace(/"/g, "''")).replace(/%7E/g, "~");
}

async function memeDaModello(modello: string, righe: string[]): Promise<Response> {
  if (!/^[a-z0-9-]{2,40}$/.test(modello) || !righe.length || righe.length > 6 || righe.some((r) => r.length > 120))
    return Response.json({ errore: "serve un modello di memegen e da 1 a 6 righe brevi" }, { status: 400 });
  const indirizzo = `https://api.memegen.link/images/${modello}/${righe.map(perMemegen).join("/")}.png?font=impact&width=1200`;
  const r = await fetch(indirizzo);
  if (!r.ok) return Response.json({ errore: `memegen ${r.status}` }, { status: 502 });
  const b = new Uint8Array(await r.arrayBuffer());
  let bin = "";
  for (let i = 0; i < b.length; i += 0x8000) bin += String.fromCharCode(...b.subarray(i, i + 0x8000));
  return Response.json({ png: btoa(bin), spesa_mese: null });
}

Deno.serve(async (req) => {
  if (!CHIAVE) return Response.json({ errore: "manca OPENAI_API_KEY" }, { status: 500 });
  const corpoIn = await req.json().catch(() => ({}));
  if (corpoIn.modello) return await memeDaModello(String(corpoIn.modello), Array.isArray(corpoIn.righe) ? corpoIn.righe.map(String) : []);
  const { scena, dre, stile } = { scena: "", dre: false, stile: "disegno", ...corpoIn };
  const altro = stile && stile !== "disegno" ? ALTRI[stile] : null;
  if (stile && stile !== "disegno" && !altro) return Response.json({ errore: "stile sconosciuto" }, { status: 400 });
  if (!scena || typeof scena !== "string" || scena.length > 900) return Response.json({ errore: "serve scena" }, { status: 400 });
  const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const mese = new Date().toISOString().slice(0, 7);
  const { data: riga } = await db.from("spesa_immagini").select("dollari,immagini").eq("mese", mese).maybeSingle();
  const gia = Number(riga?.dollari ?? 0);
  if (gia + COSTO > TETTO_MESE) return Response.json({ errore: `tetto del mese raggiunto (${gia.toFixed(2)} $ su ${TETTO_MESE} $)` }, { status: 429 });
  let corpo: FormData | string;
  let punto = "https://api.openai.com/v1/images/edits";
  const intestazioni: Record<string, string> = { Authorization: `Bearer ${CHIAVE}` };
  if (altro) {
    punto = "https://api.openai.com/v1/images/generations";
    intestazioni["Content-Type"] = "application/json";
    corpo = JSON.stringify({ model: "gpt-image-2", prompt: altro.prompt + scena, size: altro.size, quality: "medium", n: 1 });
  } else {
    const { data: rif, error } = await db.storage.from("linkedin").download("_stile/riferimento-stile.png");
    if (error || !rif) return Response.json({ errore: "manca il disegno di riferimento nello storage" }, { status: 500 });
    const form = new FormData();
    form.append("model", "gpt-image-2");
    form.append("prompt", STILE.replace("Nobody wears a cap or a hat. ", dre ? "" : "Nobody wears a cap or a hat. ") + (dre ? DRE : "") + scena);
    form.append("size", "1536x1024");
    form.append("quality", "medium");
    form.append("n", "1");
    form.append("image[]", new File([rif], "rif.png", { type: "image/png" }));
    corpo = form;
  }
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), 140000);
  try {
    const r = await fetch(punto, { method: "POST", headers: intestazioni, body: corpo, signal: ctl.signal });
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
