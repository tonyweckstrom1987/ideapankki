# Käyttöönotto (CT115, oma käyttäjä, ei sudoa)

Tämä ohje on tarkoituksella luettelo, jota ajetaan käsin kohta kerrallaan. Mitään ei asenneta automaattisesti.

## 0. Ennen kuin mitään asennetaan

1. Ehdotusputki toimii postilaatikon kautta, ei päiväkatsauksen omaan kansioon kirjoittaen. Päiväkatsauksen ehdotukset (`PENDING-PVM-N.md`) kulkevat sen omasta `proposals.py`:stä: oma numerolaskuri, lukko ja tarkka tiedostomuoto, joita toisen agentin ei pidä arvata. Ideapankki jättää vain yhden rivin tekstitiedoston (`ideapankki-PVM-TIIVISTE.txt`, max 140 merkkiä) postilaatikkoon, ja päiväkatsaus luo varsinaisen ehdotuksen omalla `luo_ehdotukset`-funktiollaan.
2. Päiväkatsauksen puolelle tarvitaan pieni muutos (postilaatikon lukija: vain viimeiset 3 päivää, vain tavalliset tiedostot, siivous `render.kentta`:lla, sitten `luo_ehdotukset`). Se tehdään päiväkatsauksen omassa repossa omalla promptillaan, ei tässä. Ennen sitä ideapankin Telegram-jono toimii sellaisenaan ja postilaatikkoon kertyvät tiedostot odottavat.
3. Oikeudet: kansio `/var/lib/agentti/ehdotus-posti`, omistaja `ideapankki`, ryhmä `ehdotusposti`, `chmod 2750`; `paivakatsaus`-käyttäjä ryhmään `ehdotusposti` (vain luku). Päiväkatsaus ei kirjoita eikä poista postilaatikosta.
4. Ota snapshot kontista.

## 1. Käyttäjä ja kansiot

```bash
useradd --system --home-dir /nonexistent --shell /usr/sbin/nologin ideapankki
install -d -o root -g root -m 755 /opt/agentit/ideapankki
install -d -o ideapankki -g ideapankki -m 700 /var/lib/agentti/ideapankki
install -d -m 755 /etc/agentti
groupadd --system ehdotusposti
usermod -aG ehdotusposti paivakatsaus     # vain luku
usermod -aG ehdotusposti ideapankki
install -d -o ideapankki -g ehdotusposti -m 2750 /var/lib/agentti/ehdotus-posti
```

Kopioi repon sisältö kohtaan `/opt/agentit/ideapankki` (omistaja root, ei kirjoitusoikeutta ideapankille).

## 2. Ideatiedosto ja salaisuudet (Tony kirjoittaa itse)

- `/etc/agentti/ideapankki-ideat.txt` (omistaja root, ryhmä ideapankki, `chmod 640`): ideat, muoto `esimerkit/ideat.esimerkki.txt`.
- `/etc/agentti/ideapankki.env` (`chmod 640`, ryhmä ideapankki):

```
IDEAT_TIEDOSTO=/etc/agentti/ideapankki-ideat.txt
EHDOTUS_POSTILAATIKKO=/var/lib/agentti/ehdotus-posti
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
- Telegramissa jono; postilaatikossa (`ls -l /var/lib/agentti/ehdotus-posti`) yksi ideapankki-*.txt; kun päiväkatsauksen lukija on asennettu, siitä syntyy PENDING-ehdotus; `/hyvaksy n` vain merkitsee.
- Rikkinäinen välimuisti (`/var/lib/agentti/ideapankki/ideapankki.json`): ajo pysähtyy virhekoodiin `kerays_valimuisti_rikki`; tarkista tiedosto, älä poista sitä sokkona (tuloksia on voinut kulua rahaa ja hakurajoja).
