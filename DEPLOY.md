# Käyttöönotto (CT115, oma käyttäjä, ei sudoa)

Tämä ohje on tarkoituksella luettelo, jota ajetaan käsin kohta kerrallaan. Mitään ei asenneta automaattisesti.

## 0. Ennen kuin mitään asennetaan

1. Tarkista ehdotusputken oikea muoto: lue päiväkatsauksen `proposals.py` ja `ehdotukset/`-kansion tiedostonimi ja -sisältö. Jos muoto poikkeaa tämän repon `ehdotusputki.py`:stä (`PENDING-PVM-N.md`: otsikko, teksti max 140 merkkiä, luotu, tila), muuta vain sitä tiedostoa ja sen testiä.
2. Ratkaise kirjoitusoikeus: ideapankki-käyttäjän pitää voida luoda tiedostoja ehdotuskansioon, mutta ei lukea päiväkatsauksen salaisuuksia. Suositus: yhteinen ryhmä `ehdotukset`, kansiolle `chmod 2775` (setgid), molemmat käyttäjät ryhmään. Älä anna ideapankille oikeutta päiväkatsauksen kotikansioon.
3. Ota snapshot kontista.

## 1. Käyttäjä ja kansiot

```bash
useradd --system --home-dir /nonexistent --shell /usr/sbin/nologin ideapankki
install -d -o root -g root -m 755 /opt/agentit/ideapankki
install -d -o ideapankki -g ideapankki -m 700 /var/lib/agentti/ideapankki
install -d -m 755 /etc/agentti
```

Kopioi repon sisältö kohtaan `/opt/agentit/ideapankki` (omistaja root, ei kirjoitusoikeutta ideapankille).

## 2. Ideatiedosto ja salaisuudet (Tony kirjoittaa itse)

- `/etc/agentti/ideapankki-ideat.txt` (omistaja root, ryhmä ideapankki, `chmod 640`): ideat, muoto `esimerkit/ideat.esimerkki.txt`.
- `/etc/agentti/ideapankki.env` (`chmod 640`, ryhmä ideapankki):

```
IDEAT_TIEDOSTO=/etc/agentti/ideapankki-ideat.txt
EHDOTUKSET_KANSIO=/var/lib/agentti/ehdotukset
LLM_BASE_URL=http://litellm.example:4000/v1
LLM_API_KEY=            # oma LiteLLM-avain "ideapankki": vain deepseek-flash, budjetti 1 USD / 30 pv
TELEGRAM_BOT_TOKEN=     # päiväkatsauksen botti (ehdotukset ja /hyvaksy kulkevat sen kautta)
TELEGRAM_CHAT_ID=
SYDAN_URL=              # Kuma push -monitori (valinnainen)
```

Avaimet kirjoitetaan käsin, ei chattiin eikä repoon.

## 3. Kokeilu ennen ajastusta

```bash
cd /opt/agentit/ideapankki
runuser -u ideapankki -- env $(cat /etc/agentti/ideapankki.env | xargs) python3 -B -m agentti --agentti ideapankki --tila /var/lib/agentti/ideapankki
```

Kuiva-ajo ei käytä verkkoa. Seuraavaksi `--verkko`, sitten `--verkko --llm` (kuluu rahaa, rajat voimassa), ja vasta lopuksi `--send`. Alussa jonossa voi olla yli 8 ideaa: yksi ajo käsittelee 8, loput seuraavilla kerroilla (päivän kutsuraja 3).

## 4. Ajastus

```bash
cp systemd/ideapankki.service.esimerkki /etc/systemd/system/ideapankki.service
cp systemd/ideapankki.timer.esimerkki /etc/systemd/system/ideapankki.timer
systemd-analyze verify /etc/systemd/system/ideapankki.service
timedatectl                                   # tarkista aikavyöhyke (ajo su 17:30 paikallista aikaa)
systemctl daemon-reload
systemctl enable --now ideapankki.timer
systemctl list-timers ideapankki.timer
```

## 5. Varmistus

- `journalctl -u ideapankki.service --no-pager | tail -30`
- Telegramissa jono; ehdotuskansiossa yksi PENDING-tiedosto; `/hyvaksy n` vain merkitsee.
- Rikkinäinen välimuisti (`/var/lib/agentti/ideapankki/ideapankki.json`): ajo pysähtyy virhekoodiin `kerays_valimuisti_rikki`; tarkista tiedosto, älä poista sitä sokkona (tuloksia on voinut kulua rahaa ja hakurajoja).
