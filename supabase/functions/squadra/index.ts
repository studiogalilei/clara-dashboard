// LA SQUADRA, DA IMPOSTAZIONI (15/9/2026).
//
// Dre: «rendimi super admin e dammi il potere di controllare gli accessi di
// tutti». Il ruolo ceo era gia' il grado massimo, ma dentro l'app non c'era
// modo di vedere chi entra e di chiudere la porta a qualcuno: il ruolo si
// cambiava solo scrivendo nel database, e togliere l'accesso voleva dire
// chiamare qualcuno che sapesse farlo.
//
// Perche' sta qui e non nel browser: bloccare davvero una persona si fa con
// la chiave di servizio (auth.admin), che nel browser non puo' stare. La
// funzione controlla da sola chi la chiama: se non e' ceo, non risponde.
// Bloccare qui vuol dire che il suo accesso smette di funzionare ovunque,
// app e database, non solo di nascondere i bottoni.
//
// COME SI METTE IN CLOUD (una volta):
//   npx supabase functions deploy squadra --project-ref tqssfcuzezlczfceqsmk

import { createClient } from "npm:@supabase/supabase-js@2";

const URL = Deno.env.get("SUPABASE_URL")!;
const SERVIZIO = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const ANON = Deno.env.get("SUPABASE_ANON_KEY")!;

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function risposta(corpo: unknown, stato = 200) {
  return new Response(JSON.stringify(corpo), {
    status: stato,
    headers: { ...CORS, "Content-Type": "application/json" },
  });
}

// cent'anni: il blocco non scade da solo, si toglie a mano
const PER_SEMPRE = "876000h";
const RUOLI = ["ceo", "manager", "specialist", "frontend", "coordinamento"];

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });

  const autorizzazione = req.headers.get("Authorization") ?? "";
  if (!autorizzazione) return risposta({ errore: "Non sei dentro" }, 401);

  // chi chiama: il suo stesso token, con le sue stesse regole
  const suo = createClient(URL, ANON, { global: { headers: { Authorization: autorizzazione } } });
  const { data: utente } = await suo.auth.getUser();
  if (!utente?.user) return risposta({ errore: "Non sei dentro" }, 401);
  const { data: ceo } = await suo.rpc("sono_ceo");
  if (!ceo) return risposta({ errore: "Questa parte la vede solo chi guida lo Studio" }, 403);

  const admin = createClient(URL, SERVIZIO);
  const { azione, id, ruolo } = (await req.json().catch(() => ({}))) as
    { azione?: string; id?: string; ruolo?: string };

  // l'elenco: una riga per persona, con quello che serve per decidere
  if (azione === "elenco") {
    const [{ data: profili }, { data: gente }, { data: token }] = await Promise.all([
      admin.from("profili").select("id,nome,ruolo"),
      admin.auth.admin.listUsers({ perPage: 200 }),
      admin.from("google_token").select("user_id,aggiornato_il"),
    ]);
    const perId = new Map((gente?.users ?? []).map((u) => [u.id, u]));
    const conGoogle = new Map(((token ?? []) as Array<{ user_id: string; aggiornato_il: string }>)
      .map((t) => [t.user_id, t.aggiornato_il]));
    const righe = (profili ?? []).map((p: { id: string; nome: string | null; ruolo: string }) => {
      const u = perId.get(p.id);
      const bloccatoFino = (u as { banned_until?: string } | undefined)?.banned_until ?? null;
      return {
        id: p.id,
        nome: p.nome,
        ruolo: p.ruolo,
        email: u?.email ?? null,
        entrato: u?.last_sign_in_at ?? null,
        creato: u?.created_at ?? null,
        google: conGoogle.get(p.id) ?? null,
        bloccato: Boolean(bloccatoFino && new Date(bloccatoFino) > new Date()),
        io: p.id === utente.user.id,
      };
    });
    righe.sort((a, b) => (a.nome ?? "").localeCompare(b.nome ?? ""));
    return risposta({ righe });
  }

  if (!id) return risposta({ errore: "Manca la persona" }, 400);
  if (id === utente.user.id) return risposta({ errore: "Su te stesso no: te lo deve fare l'altro ceo" }, 400);

  if (azione === "ruolo") {
    if (!ruolo || !RUOLI.includes(ruolo)) return risposta({ errore: "Ruolo che non esiste" }, 400);
    // lo Studio resta sempre con almeno un ceo che puo' entrare
    if (ruolo !== "ceo") {
      const { count } = await admin.from("profili").select("id", { count: "exact", head: true }).eq("ruolo", "ceo");
      const { data: era } = await admin.from("profili").select("ruolo").eq("id", id).single();
      if (era?.ruolo === "ceo" && (count ?? 0) <= 1) return risposta({ errore: "È l'ultimo ceo: prima dallo a qualcun altro" }, 400);
    }
    const { error } = await admin.from("profili").update({ ruolo }).eq("id", id);
    return error ? risposta({ errore: error.message }, 500) : risposta({ fatto: true });
  }

  // il blocco vero: il suo token smette di valere, e Clara smette di agire
  // a nome suo (il collegamento Google se ne va con lui)
  if (azione === "blocca") {
    const { error } = await admin.auth.admin.updateUserById(id, { ban_duration: PER_SEMPRE });
    if (error) return risposta({ errore: error.message }, 500);
    await admin.from("google_token").delete().eq("user_id", id);
    return risposta({ fatto: true });
  }

  if (azione === "sblocca") {
    const { error } = await admin.auth.admin.updateUserById(id, { ban_duration: "none" });
    return error ? risposta({ errore: error.message }, 500) : risposta({ fatto: true });
  }

  // staccare solo Google: l'app resta, Clara non tocca piu' la sua roba
  if (azione === "scollega") {
    const { error } = await admin.from("google_token").delete().eq("user_id", id);
    return error ? risposta({ errore: error.message }, 500) : risposta({ fatto: true });
  }

  return risposta({ errore: "Azione che non esiste" }, 400);
});
