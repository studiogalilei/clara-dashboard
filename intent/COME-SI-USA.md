---
tipo: convenzione
creato: 2026-09-02
---

# La cartella intent

Qui si posa un'idea **prima** che diventi un cantiere.

Nasce il 2/9 per un motivo preciso: quel giorno una sessione è morta e
un'idea stava per morire con lei. Le idee che vivono nelle chat muoiono con
le chat.

## Chi scrive un intent

Chiunque. Non serve essere tecnici e non serve sapere come si fa. Dre,
Giacomo, Carlo, e un domani un cliente che segnala un problema. Chi lo
scrive si chiama **originatore** e la sua unica responsabilità è dire cosa
fa male e cosa dovrebbe succedere. Il come non è affar suo.

## Come si scrive

Un file per idea, `AAAA-MM-GG-titolo-corto.md`, con dentro quattro cose:

```markdown
---
tipo: intent
chi: <nome>
quando: <data>
stato: proposto
---

# <titolo>

**Cosa fa male oggi**
**Cosa dovrebbe succedere**
**Come si capisce che è risolto**
**Cosa so io che non è scritto da nessuna parte**
```

L'ultima riga è la più preziosa e la salta sempre chi ha fretta: le cose
dette a voce, chi ha già sentito chi, perché una strada è stata scartata.
Sono le informazioni che nessuno può dedurre dai dati.

## Cosa succede dopo

Lo stato cambia a mano: `proposto`, poi `accettato` o `scartato`, poi
`fatto`. Un intent scartato **non si cancella**: resta scritto perché il
motivo per cui si è detto no vale quanto un sì, e fra tre mesi eviterà di
ridiscutere la stessa cosa.

Quando un intent viene accettato e la cosa è grossa, diventa un documento di
progetto in `docs/`. Se è piccola si fa e basta: non tutto merita tre
documenti.
