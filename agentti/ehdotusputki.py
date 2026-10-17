"""Ehdotusputken liitin: kirjoittaa yhden ehdotuksen PENDING-tiedostona ehdotuskansioon.

HUOM: tiedostomuoto on OLETUS paivakatsauksen putkesta (PENDING-PVM-N.md: otsikko, teksti max 140
merkkia, luotu, tila). Ennen kayttoonottoa se tarkistetaan oikeaa proposals.py:ta vastaan ja
tama on ainoa tiedosto, jota silloin muutetaan. Kansiota ei luoda (omistajuus ratkaistaan
asennuksessa), tiedosto luodaan atomisesti ('x'), olemassa olevaa ei koskaan ylikirjoiteta.
Ehdotus ei suorita mitaan: /hyvaksy vain merkitsee sen.
"""
import os
import re

from . import config

TEKSTI_MAX = 140
NUMERO_RE = re.compile(r"-(\d{1,4})\.md$")


class EhdotusVirhe(Exception):
    def __init__(self, koodi):
        super().__init__(koodi)
        self.koodi = koodi


def _siisti(teksti, pituus):
    return " ".join(str(teksti).split())[:pituus]


def seuraava_numero(kansio):
    suurin = 0
    for nimi in os.listdir(kansio):
        m = NUMERO_RE.search(nimi)
        if m:
            suurin = max(suurin, int(m.group(1)))
    return suurin + 1


def kirjoita(kansio, otsikko, teksti, kello=None):
    """Palauttaa kirjoitetun tiedoston nimen. Nostaa EhdotusVirhe."""
    if not kansio or not os.path.isdir(kansio):
        raise EhdotusVirhe("ehdotukset_kansio")
    pvm = config.paiva(kello() if kello else None)
    sisalto = "# %s\n\n%s\n\nluotu: %s\ntila: PENDING\nlahde: ideapankki\n" % (
        _siisti(otsikko, 80), _siisti(teksti, TEKSTI_MAX), pvm)
    try:
        for _ in range(20):
            nimi = "PENDING-%s-%d.md" % (pvm, seuraava_numero(kansio))
            try:
                with open(os.path.join(kansio, nimi), "x", encoding="utf-8") as f:
                    f.write(sisalto)
                return nimi
            except FileExistsError:
                continue  # kilpaileva kirjoittaja otti numeron
    except OSError:
        raise EhdotusVirhe("ehdotukset_kirjoitus")
    raise EhdotusVirhe("ehdotukset_numero")
