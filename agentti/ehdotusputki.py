"""Ehdotusputken liitin: jattaa yhden ehdotuksen POSTILAATIKKOON, ei suoraan paivakatsauksen ehdotuskansioon.

Miksi: paivakatsauksen ehdotukset (PENDING-PVM-N.md) kulkevat sen omasta proposals.py:sta: oma
numerolaskuri, lukko, tarkka tiedostomuoto ja vanhentuminen. Toisen agentin ei pida arvata niita eika
kirjoittaa sen kansioon. Ideapankki kirjoittaa vain yhden rivin tekstitiedoston (ideapankki-PVM-TIIVISTE.txt)
yhteiseen postilaatikkokansioon; paivakatsaus lukee sen ja luo varsinaisen ehdotuksen omalla koodillaan
(numero, siivous, kaksoiskappaleiden esto). Tama liitin ei koskaan numeroi, ylikirjoita tai poista mitaan.
Kansiota ei luoda (omistajuus ratkaistaan asennuksessa). Ehdotus ei suorita mitaan: /hyvaksy vain merkitsee sen.
"""
import hashlib
import os

from . import config

TEKSTI_MAX = 140


class EhdotusVirhe(Exception):
    def __init__(self, koodi):
        super().__init__(koodi)
        self.koodi = koodi


def _siisti(teksti, pituus):
    return " ".join(str(teksti).split())[:pituus]


def kirjoita(kansio, teksti, kello=None):
    """Kirjoittaa yhden rivin tekstitiedoston postilaatikkoon. Palauttaa tiedoston nimen.
    Sama teksti samana paivana on jo toimitettu: palautetaan sama nimi koskematta tiedostoon."""
    if not kansio or not os.path.isdir(kansio) or os.path.islink(kansio):
        raise EhdotusVirhe("posti_kansio")
    rivi = _siisti(teksti, TEKSTI_MAX)
    if not rivi:
        raise EhdotusVirhe("posti_tyhja")
    pvm = config.paiva(kello() if kello else None)
    tiiviste = hashlib.sha256(rivi.encode("utf-8")).hexdigest()[:8]
    nimi = "ideapankki-%s-%s.txt" % (pvm, tiiviste)
    try:
        with open(os.path.join(kansio, nimi), "x", encoding="utf-8") as f:
            f.write(rivi + "\n")
    except FileExistsError:
        pass
    except OSError:
        raise EhdotusVirhe("posti_kirjoitus")
    return nimi
