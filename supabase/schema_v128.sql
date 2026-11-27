-- v128 (27/11, Dre: «metti un pulsante Copy Video che mi crea copy di video usando questo framework»). Dal compositore
-- un testo puo' diventare il copione di un video (metodo delle domande, contenuti/skills/copione-video/riferimenti/
-- copy-video.md): la routine lo scrive come una bozza, come per «Ottimizza».
alter table linkedin_post drop constraint if exists linkedin_post_richiesta_check;
alter table linkedin_post add constraint linkedin_post_richiesta_check
  check (richiesta in ('piu_corto', 'piu_ironico', 'cambia_framework', 'copy_video'));
