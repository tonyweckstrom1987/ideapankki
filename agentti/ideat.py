"""Ideatiedoston luku. Tiedosto on Tonyn oma (tai Clauden hanelle kirjoittama) lista:

    # kommentti
    id | otsikko | yksi lause | haku=english search words | riippuu=id1,id2 | tila=avoin | koko=3 | hyoty=4

Pakolliset ovat kolme ensimmaista kenttaa. Valinnaiset (avain=arvo):
  haku    englanninkieliset hakusanat npm/GitHub-hakuun (ilman sita esitutkimus on ei_tietoa)
  riippuu pilkulla erotetut idea-id:t, jotka pitaa olla valmiina ennen tata
  tila    avoin (oletus) | kesken | valmis | hylatty
  koko, hyoty  omistajan oma arvio 1-5; ohittaa mallin arvion

Virheellinen rivi ohitetaan ja raportoidaan (rivinumero), muut rivit luetaan.
"""
import hashlib
import os
import re
from dataclasses import dataclass
from typing import Optional, Tuple

from . import rajat

ID_RE = re.compile(r"^[a-z][a-z0-9-]{1,39}$")
HAKU_RE = re.compile(r"^[A-Za-z0-9 .+_-]{2,100}$")
TILAT = ("avoin", "kesken", "valmis", "hylatty")
AVAIMET = ("haku", "riippuu", "tila", "koko", "hyoty")


class IdeatVirhe(Exception):
    """koodi: ideat_puuttuu | ideat_liian_iso | ideat_luku"""

    def __init__(self, koodi):
        super().__init__(koodi)
        self.koodi = koodi


@dataclass(frozen=True)
class Idea:
    id: str
    otsikko: str
    lause: str
    haku: str = ""
    riippuu: Tuple[str, ...] = ()
    tila: str = "avoin"
    koko: Optional[int] = None
    hyoty: Optional[int] = None

    @property
    def tiiviste(self):
        """Muuttuu vain, kun idean sisalto muuttuu (omat pisteet eivat vaikuta esitutkimukseen)."""
        raaka = "\n".join((self.otsikko, self.lause, self.haku))
        return hashlib.sha256(raaka.encode("utf-8")).hexdigest()[:16]


def _piste(arvo):
    try:
        luku = int(arvo)
    except ValueError:
        raise ValueError("pistearvo ei ole kokonaisluku")
    if not rajat.PISTE_MIN <= luku <= rajat.PISTE_MAX:
        raise ValueError("pistearvo ei ole valilla %d-%d" % (rajat.PISTE_MIN, rajat.PISTE_MAX))
    return luku


def _rivi(teksti):
    osat = [o.strip() for o in teksti.split("|")]
    if len(osat) < 3:
        raise ValueError("liian vahan kenttia")
    id_, otsikko, lause = osat[:3]
    if not ID_RE.match(id_):
        raise ValueError("virheellinen id")
    if not 1 <= len(otsikko) <= 80:
        raise ValueError("otsikon pituus 1-80")
    if not 1 <= len(lause) <= 200:
        raise ValueError("lauseen pituus 1-200")
    kentat = {}
    for osa in osat[3:]:
        if not osa:
            continue
        if "=" not in osa:
            raise ValueError("lisakentta ilman '='")
        avain, arvo = (x.strip() for x in osa.split("=", 1))
        if avain not in AVAIMET:
            raise ValueError("tuntematon avain")
        if avain in kentat:
            raise ValueError("avain kahdesti")
        kentat[avain] = arvo
    haku = kentat.get("haku", "")
    if haku and not HAKU_RE.match(haku):
        raise ValueError("haku: vain kirjaimet, numerot ja . + _ -")
    riippuu = tuple(x.strip() for x in kentat.get("riippuu", "").split(",") if x.strip())
    if any(not ID_RE.match(x) for x in riippuu) or id_ in riippuu:
        raise ValueError("virheellinen riippuvuus")
    tila = kentat.get("tila", "avoin")
    if tila not in TILAT:
        raise ValueError("virheellinen tila")
    koko = _piste(kentat["koko"]) if "koko" in kentat else None
    hyoty = _piste(kentat["hyoty"]) if "hyoty" in kentat else None
    return Idea(id_, otsikko, lause, haku, riippuu, tila, koko, hyoty)


def lue(polku):
    """Palauttaa (ideat, virheet). virheet on lista rivinumeroita ja syita, ei rivin sisaltoa."""
    try:
        if os.path.getsize(polku) > rajat.IDEAT_TIEDOSTO_MAX_TAVUA:
            raise IdeatVirhe("ideat_liian_iso")
        with open(polku, encoding="utf-8") as f:
            rivit = f.read().splitlines()
    except FileNotFoundError:
        raise IdeatVirhe("ideat_puuttuu")
    except IdeatVirhe:
        raise
    except (OSError, UnicodeDecodeError):
        raise IdeatVirhe("ideat_luku")
    ideat, nahdyt, virheet = [], set(), []
    for nro, rivi in enumerate(rivit, 1):
        if not rivi.strip() or rivi.lstrip().startswith("#"):
            continue
        if any(ord(c) < 32 for c in rivi):
            virheet.append("rivi %d: ohjausmerkki" % nro)
            continue
        if len(ideat) >= rajat.IDEAT_MAX:
            virheet.append("rivi %d: ideoita yli %d, loput ohitettu" % (nro, rajat.IDEAT_MAX))
            break
        try:
            idea = _rivi(rivi)
        except ValueError as e:
            virheet.append("rivi %d: %s" % (nro, e))
            continue
        if idea.id in nahdyt:
            virheet.append("rivi %d: id esiintyy jo" % nro)
            continue
        nahdyt.add(idea.id)
        ideat.append(idea)
    return ideat, virheet
