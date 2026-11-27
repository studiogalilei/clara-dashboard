// LE PERSONE DEL GIORNO: gli annunci di lavoro da Google Jobs (27/11/2026).
//
// La routine «LinkedIn Desk: persone del giorno» cerca aziende che stanno assumendo per lavoro che farebbe un
// gestionale (inserimento ordini, ufficio traffico, back office). Qui si chiede a Google Jobs, tramite SearchAPI, e si
// torna una lista corta. La chiave resta nei segreti di Supabase: la routine chiama con la chiave di servizio.
//
// IN CLOUD: supabase functions deploy linkedin-annunci   (segreto: SEARCHAPI_KEY)
const CHIAVE = Deno.env.get("SEARCHAPI_KEY") ?? "";

Deno.serve(async (req) => {
  if (!CHIAVE) return Response.json({ errore: "manca SEARCHAPI_KEY" }, { status: 500 });
  const { q } = await req.json().catch(() => ({ q: "" }));
  if (!q || typeof q !== "string" || q.length > 120) return Response.json({ errore: "serve q" }, { status: 400 });
  const url = `https://www.searchapi.io/api/v1/search?engine=google_jobs&gl=it&hl=it&q=${encodeURIComponent(q)}&api_key=${CHIAVE}`;
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), 25000);
  try {
    const r = await fetch(url, { signal: ctl.signal });
    const d = await r.json();
    const lavori = (d.jobs ?? []).map((j: Record<string, unknown>) => ({
      titolo: j.title, azienda: j.company_name, luogo: j.location, via: j.via,
      quando: (j.detected_extensions as Record<string, unknown> | undefined)?.posted_at ?? null,
      link: j.apply_link ?? (Array.isArray(j.apply_links) ? (j.apply_links[0] as Record<string, unknown>)?.link : null) ?? j.sharing_link ?? null,
      descrizione: String(j.description ?? "").slice(0, 600),
    }));
    return Response.json({ lavori });
  } catch (e) {
    return Response.json({ errore: String(e) }, { status: 502 });
  } finally {
    clearTimeout(t);
  }
});
