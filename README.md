# ideapankki

Ideoiden priorisointi ja **esitutkimus** pienenä, turvallisena agenttina: ennen kuin rakennat jotain, se tarkistaa npm:stä ja GitHubista, onko sama jo tehty, ja järjestää ideat jonoon. Vain Pythonin standardikirjasto. Rakennettu [agentti-pohjan](https://github.com/tonyweckstrom1987/agentti-pohja) päälle (ensimmäinen oikea agentti siitä).

Tekijän tarve: rakensin työkalun, jonka vastineet (MCP Inspector, @mcpjam/cli) selvisivät vasta valmiina. Nyt jokainen idea saa esitutkimuksen ennen kuin siihen käytetään aikaa.

## Mitä se tekee

1. Lukee ideatiedoston (yksi idea per rivi).
2. **Koodi** hakee jokaiselle ideaan liittyvät GitHub-repot ja npm-paketit englanninkielisillä hakusanoilla.
3. **Malli** arvioi vain löydetyt: onko jokin niistä olennaisesti sama asia (ja mikä), sekä idean koko ja hyöty asteikolla 1–5. Malli saa myös sanoa "ei tietoa".
4. **Koodi** laskee prioriteetin kaavalla ja järjestää jonon. Linkit rakennetaan koodissa, ei mallin tekstistä.
5. Viikkoajo lähettää jonon kärjen Telegramiin ja kirjaa yhden ehdotuksen ("aloita seuraavaksi X") ehdotusputkeen. Se ei suorita mitään: hyväksyntä on aina ihmisen.

## Vaihtoehtoja ja miksi tämä

Samaa ongelmaa ratkaisee jo kaksi avointa MCP-työkalua. Ne ovat hyviä, jos haluat tarkistuksen suoraan editorissa tai agentin työkaluna:

- **[idea-reality-mcp](https://github.com/mnemox-ai/idea-reality-mcp)** antaa ideasta 0–100 pisteen "onko tämä jo tehty" -arvion (GitHub, Hacker News, npm, PyPI, Stack Overflow). MIT, ei avainta. Se on ylläpitotilassa, hosted-rajapinnassa idean teksti lähtee kolmannelle osapuolelle, eikä se osaa "ei tietoa" -tulosta tai jonota ideoita.
- **[reuse-before-generate](https://www.npmjs.com/package/reuse-before-generate)** hakee 10 rekisteristä ennen koodin generointia ja ohjaa agentin web-hakuun. Hyvä yksittäiseen tarkistukseen, ei priorisoi eikä muista aiempia tuloksia.
- Yleiset RICE-priorisointi-skillit Claudelle ja muille: arvioivat yhden kerran keskustelussa, eivät pidä jonoa eivätkä tarkista rekistereitä.

Tämä on oma pieni agentti, koska tarvitsin kolme asiaa yhdessä: haku (koodi), jono ja riippuvuudet (koodi, ei mallin päätös) sekä tulos olemassa olevaan ehdotusputkeen. Jos tarvitset vain "onko tämä jo tehty", käytä idea-realityä.

## Ideatiedosto

```
id | otsikko | yksi lause | haku=english search words | riippuu=id1,id2 | tila=avoin | koko=3 | hyoty=4
```

Pakolliset ovat kolme ensimmäistä kenttää. Valinnaiset: `haku` (ilman sitä esitutkimus on `ei_tietoa`), `riippuu` (idea on jumissa, kunnes riippuvuudet ovat tilassa `valmis`), `tila` (`avoin`, `kesken`, `valmis`, `hylatty`), `koko` ja `hyoty` (oma arvio 1–5, ohittaa mallin). Virheellinen rivi ohitetaan ja raportoidaan rivinumerolla. Esimerkki: `esimerkit/ideat.esimerkki.txt`.

## Prioriteetti (koodissa, ei mallin päätös)

```
prioriteetti = 2 × hyöty + (6 − koko) − 3, jos samankaltainen löytyi
```

Suurin mahdollinen on 15. Jos koko tai hyöty puuttuu (ei omaa eikä mallin arviota), ideaa ei pisteytetä, ja se jää pisteytettyjen jälkeen. Jumissa oleva idea on aina viimeisenä, eikä sitä koskaan ehdoteta. Tuntematon riippuvuus-id pitää idean jumissa.

## Turvamalli

- Mallilla ei ole työkaluja. Ideat, hakutulokset ja niiden kuvaukset annetaan `<data>`-lohkossa, jota sisältö ei voi sulkea.
- Mallin vastaus hyväksytään vain skeemaa vasten. Sen lisäksi koodi tarkistaa semantiikan: id kuuluu erään, ehdokasnumerot ovat olemassa, pisteet ovat 1–5, kutakin ideaa arvioidaan kerran, arvio annetaan vain asiaan, jota idea tarvitsee. Mallin tekstistä poistetaan linkit ja tagit.
- Haku käyttää vain kahta isäntää (`api.github.com`, `registry.npmjs.org`), vain https, ei uudelleenohjauksia, ei avaimia. Hakusanat validoidaan.
- Haku, joka ei vastannut, on `ei_tietoa`, ei "ei löytynyt". Vain onnistunut tyhjä haku on `ei_loytynyt`, ja sekin tarkoittaa vain, ettei haku tuottanut osumia.
- Kulukatto, päivän kutsuraja ja eräkoko (8 ideaa per ajo) ovat `rajat.py`:ssä. Rikkinäinen välimuisti pysäyttää ajon eikä nollaudu hiljaa.
- Haun tulos tallennetaan, vaikka mallikutsu epäonnistuisi, jotta hakurajat eivät kulu turhaan.

**Rajoitukset.** Esitutkimus ei ole takuu: hakusanat ovat yksi näkökulma, eikä npm- tai GitHub-haku löydä kaikkea (esimerkiksi PyPI:tä, blogeja tai suljettuja tuotteita). "Ei samankaltaista" tarkoittaa "ei viidestä parhaasta hausta". Mallin koko- ja hyötyarviot ovat karkeita; omat arviot (`koko=`, `hyoty=`) ohittavat ne. Ehdotukset eivät mene suoraan päiväkatsauksen kansioon: ideapankki jättää yhden rivin tekstitiedoston postilaatikkoon (`ehdotusputki.py`), ja vastaanottava agentti luo varsinaisen ehdotuksen omalla numeroinnillaan ja lukituksellaan.

## Ajot

```bash
python -m agentti --agentti ideapankki                       # kuiva-ajo: jono välimuistista, ei verkkoa
python -m agentti --agentti ideapankki --verkko --llm        # hae ja arvioi (enintään 8 ideaa)
python -m agentti --agentti ideapankki --verkko --llm --send # lisäksi Telegram ja ehdotus putkeen
```

Ympäristö: `IDEAT_TIEDOSTO` (oletus `ideat.txt`), `EHDOTUS_POSTILAATIKKO`, `LLM_BASE_URL`, `LLM_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. Käyttöönotto: `DEPLOY.md` ja `systemd/ideapankki.*.esimerkki`.

## Testit

```bash
python -m unittest discover -s . -t . -p 'test_*.py'
```

165 testiä, ja 45 tarkoituksella rikottua kohtaa kaatuu testeihin (ensimmäisellä kierroksella osa selvisi, mikä paikkasi testejä: omat ja mallin pisteet, esitutkimuksen vanheneminen, tiedoston ylikirjoitus postilaatikossa).

## Pohja

Kulukatto, LLM-asiakas, "en tiedä" -tulos, `<data>`-lohko, Telegram, sydänääni ja kovennetut systemd-mallit ovat agentti-pohjasta (ks. `agentti/`). Muutokset pohjaan: `--verkko`-lippu, agentin valinnaiset koukut `tarvitsee_llm` ja `loppu` sekä `Konteksti`. Ne kannattaa viedä takaisin pohjaan.

Lisenssi: MIT.
