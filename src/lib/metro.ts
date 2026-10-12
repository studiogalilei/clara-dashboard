// LE SCELTE DEL METRO (29/9), in un posto solo (12/10). Le usano la pagina Metro e la domanda
// «non sono sicura di cosa ha risposto» in Posta: la scelta di Dre sul dubbio scrive la lettura
// (RPC decidi_lettura, schema_v81) e diventa un'etichetta del Metro. Sono le stesse di
// scripts/lettura.py (SCELTE_DRE): se cambiano li', cambiano qui.
export const SCELTE_RISPOSTE: Array<[string, string]> = [
  ['si', 'Sì, vuole'], ['no', 'No'], ['non_scrivere', 'Non scrivetemi più'],
  ['fuori_ufficio', 'Fuori ufficio'], ['rinvio', 'Più avanti'], ['altro', 'Altro'],
]
