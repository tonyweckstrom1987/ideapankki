# Muutosloki

## 0.1.1 (17.10.2026)

- Ensimmainen oikea ajo (deepseek-flash, 8 ideaa) katkesi (`llm_vastaus_katkaistu`) kolme kertaa. Mittaus: mallin oma "ajattelu" kulutti 4950 / 6000 tokenia ja varsinaiselle vastaukselle jai 48 merkkia, joten kattoa nostamalla ei olisi auttanut. Korjaus: pyynnossa `"reasoning": {"enabled": false}` (OpenRouterin parametri; LiteLLM hylkaa `reasoning_effort` ja `thinking` virheella 400). Mittaus korjauksen jalkeen: 907 tokenia ulos, ajattelu 0, JSON kelvollinen, kulu alle 0,005 USD.
- Laatuvertailu ennen korjauksen ottamista kayttoon (sama syote, 8 ideaa): ajattelu paalla (katto 9000) kulutti 5282 tokenia ulos (ajattelu 4422) ja antoi arvion vain 2 ideasta; ajattelu pois antoi 946 tokenilla arviot 7 ideasta, ja kahdessa yhteisessa ideassa tulos oli sama tai lahes sama (context-doctor identtinen, commit-story koko 2 vs 3). Ajattelu pois ei siis heikentanyt laatua, ja tulos oli taydellisempi.
- Lukittu raja `MAX_TOKENS` 2000 -> 3000 (Tonyn lupa), jotta vastauksella on tilaa; paiva- ja kuukausikatto ennallaan.
- Oppi: kun `finish_reason` on `length` mutta `content` on lyhyt, katso `usage.completion_tokens_details.reasoning_tokens`.

## 0.1.0

Ensimmainen versio. Rakennettu agentti-pohja 0.1.0:n paalle (ensimmainen oikea agentti pohjasta).

- Uusi agentti `ideapankki`: priorisoi ideatiedoston ideat ja tekee jokaiselle esitutkimuksen
  (GitHub- ja npm-haku, malli arvioi vain loydetyt).
- Prioriteettikaava ja jonon jarjestys koodissa (`jono.py`); malli antaa vain koko- ja hyoty-arviot 1-5 tai ei mitaan.
- Riippuvuudet ideatiedoston `riippuu=`-kentasta; omat pisteet (`koko`, `hyoty`) ohittavat mallin.
- `ehdotusputki.py`: yksi ehdotus per ajo (paras vapaa idea) yhden rivin tekstitiedostona postilaatikkoon (`EHDOTUS_POSTILAATIKKO`); vastaanottaja numeroi ja validoi omalla koodillaan, tama ei koskaan kirjoita PENDING-tiedostoja.
- Pohjaan: ajoketjuun `--verkko`-lippu, agentin valinnaiset koukut `tarvitsee_llm` ja `loppu`, `Konteksti`;
  haun tulos tallennetaan, vaikka mallikutsu epaonnistuisi.
- 165 testia, 45 mutaatiota kaatuu testeihin.
