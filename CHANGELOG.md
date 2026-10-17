# Muutosloki

## 0.1.0

Ensimmainen versio. Rakennettu agentti-pohja 0.1.0:n paalle (ensimmainen oikea agentti pohjasta).

- Uusi agentti `ideapankki`: priorisoi ideatiedoston ideat ja tekee jokaiselle esitutkimuksen
  (GitHub- ja npm-haku, malli arvioi vain loydetyt).
- Prioriteettikaava ja jonon jarjestys koodissa (`jono.py`); malli antaa vain koko- ja hyoty-arviot 1-5 tai ei mitaan.
- Riippuvuudet ideatiedoston `riippuu=`-kentasta; omat pisteet (`koko`, `hyoty`) ohittavat mallin.
- `ehdotusputki.py`: yksi ehdotus per ajo (paras vapaa idea) PENDING-tiedostona ehdotuskansioon; tiedostomuoto on oletus ja tarkistetaan kayttoonotossa.
- Pohjaan: ajoketjuun `--verkko`-lippu, agentin valinnaiset koukut `tarvitsee_llm` ja `loppu`, `Konteksti`;
  haun tulos tallennetaan, vaikka mallikutsu epaonnistuisi.
- 163 testia, 42 mutaatiota kaatuu testeihin.
