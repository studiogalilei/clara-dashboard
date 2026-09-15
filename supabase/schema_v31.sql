-- ODYN CRM schema v31 (15 set 2026) — la chat di Clara non e' piu' aperta a Internet
--
-- QA (backend): clara-risponde sta su --no-verify-jwt e non controllava niente:
-- chiunque conoscesse l'indirizzo poteva bruciare crediti OpenAI, scrivere come
-- Clara nella chat di chiunque e nel diario a nome di un altro. Ora il trigger
-- manda un segreto nell'intestazione, e la funzione senza quello risponde 401.

create or replace function sveglia_clara()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.tipo = 'dre' then
    perform net.http_post(
      url := 'https://tqssfcuzezlczfceqsmk.supabase.co/functions/v1/clara-risponde',
      headers := jsonb_build_object('Content-Type', 'application/json', 'x-clara-segreto', '<CLARA_SEGRETO, nei secret delle funzioni e in .env.local>'),
      body := jsonb_build_object('type', 'INSERT', 'table', 'clara_messaggi', 'record', to_jsonb(new))
    );
  end if;
  return new;
end $$;

select 'schema v31 applicato: la chat parla solo col segreto' as esito;
