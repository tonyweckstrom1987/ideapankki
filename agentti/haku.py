"""Esitutkimuksen haku: GitHub-repot ja npm-paketit hakusanoilla. Vain koodi hakee; malli ei.

- Vain kaksi sallittua isantaa (api.github.com, registry.npmjs.org), vain https.
- Ei avaimia eika kirjautumista (tunnistamaton GitHub-haku riittaa muutamalle ideaa viikossa).
- Ei uudelleenohjauksia, vastauksen koko rajattu, kaikki virheet ovat koodeja.
- Tulokset ovat EPALUOTETTAVAA dataa: kuvaukset siivotaan, URL:t rakennetaan koodissa.
"""
import json
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

from . import rajat

SALLITUT_ISANNAT = ("api.github.com", "registry.npmjs.org")
KYSELY_RE = re.compile(r"^[A-Za-z0-9 .+_-]{2,100}$")
NPM_NIMI_RE = re.compile(r"^(@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*$")
GH_NIMI_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9._-]+$")
_OHJAUS = re.compile(r"[\x00-\x1f\x7f]")
_URL = re.compile(r"https?://\S+", re.IGNORECASE)
_TAGI = re.compile(r"<[^>]*>")


class HakuVirhe(Exception):
    """koodi: haku_asetus | haku_aikakatkaisu | haku_http_<koodi> | haku_yhteys | haku_vastaus"""

    def __init__(self, koodi):
        super().__init__(koodi)
        self.koodi = koodi


class _EiUudelleenohjauksia(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):
        return None


def puhdista(teksti, pituus):
    """Epaluotettava teksti mallille ja viestiin: ei ohjausmerkkeja, tageja eika linkkeja."""
    if not isinstance(teksti, str):
        return ""
    teksti = _TAGI.sub(" ", _URL.sub(" ", _OHJAUS.sub(" ", teksti)))
    return " ".join(teksti.split())[:pituus]


def _hae_http(osoite):
    osat = urllib.parse.urlparse(osoite)
    if osat.scheme != "https" or osat.hostname not in SALLITUT_ISANNAT:
        raise HakuVirhe("haku_asetus")
    pyynto = urllib.request.Request(osoite, headers={
        "User-Agent": "ideapankki-esitutkija", "Accept": "application/json"})
    avaaja = urllib.request.build_opener(_EiUudelleenohjauksia)
    try:
        with avaaja.open(pyynto, timeout=rajat.HAKU_AIKAKATKAISU) as v:
            raaka = v.read(rajat.HAKU_VASTAUS_MAX_TAVUA + 1)
    except urllib.error.HTTPError as e:
        raise HakuVirhe("haku_http_%d" % e.code)
    except urllib.error.URLError as e:
        if isinstance(e.reason, (socket.timeout, TimeoutError)):
            raise HakuVirhe("haku_aikakatkaisu")
        raise HakuVirhe("haku_yhteys")
    except (socket.timeout, TimeoutError):
        raise HakuVirhe("haku_aikakatkaisu")
    except OSError:
        raise HakuVirhe("haku_yhteys")
    if len(raaka) > rajat.HAKU_VASTAUS_MAX_TAVUA:
        raise HakuVirhe("haku_vastaus")
    try:
        return json.loads(raaka.decode("utf-8"))
    except ValueError:
        raise HakuVirhe("haku_vastaus")


def github(kysely, hae=None):
    """Palauttaa listan ehdokkaita. hae(osoite) -> json (testeissa korvattu)."""
    if not KYSELY_RE.match(kysely or ""):
        raise HakuVirhe("haku_asetus")
    osoite = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
        {"q": kysely, "sort": "stars", "order": "desc", "per_page": rajat.HAKU_EHDOKKAITA})
    data = (hae or _hae_http)(osoite)
    try:
        kohteet = data["items"]
    except (KeyError, TypeError):
        raise HakuVirhe("haku_vastaus")
    if not isinstance(kohteet, list):
        raise HakuVirhe("haku_vastaus")
    ulos = []
    for k in kohteet[:rajat.HAKU_EHDOKKAITA]:
        nimi = k.get("full_name") if isinstance(k, dict) else None
        if not isinstance(nimi, str) or not GH_NIMI_RE.match(nimi):
            continue
        tahtia = k.get("stargazers_count")
        tahtia = tahtia if isinstance(tahtia, int) and not isinstance(tahtia, bool) else 0
        ulos.append({"lahde": "github", "nimi": nimi, "url": "https://github.com/" + nimi,
                     "kuvaus": puhdista(k.get("description"), 160), "mitta": "%d tahtea" % tahtia})
    return ulos


def npm(kysely, hae=None):
    if not KYSELY_RE.match(kysely or ""):
        raise HakuVirhe("haku_asetus")
    osoite = "https://registry.npmjs.org/-/v1/search?" + urllib.parse.urlencode(
        {"text": kysely, "size": rajat.HAKU_EHDOKKAITA})
    data = (hae or _hae_http)(osoite)
    try:
        kohteet = data["objects"]
    except (KeyError, TypeError):
        raise HakuVirhe("haku_vastaus")
    if not isinstance(kohteet, list):
        raise HakuVirhe("haku_vastaus")
    ulos = []
    for k in kohteet[:rajat.HAKU_EHDOKKAITA]:
        paketti = k.get("package") if isinstance(k, dict) else None
        nimi = paketti.get("name") if isinstance(paketti, dict) else None
        if not isinstance(nimi, str) or not NPM_NIMI_RE.match(nimi) or len(nimi) > 214:
            continue
        versio = puhdista(paketti.get("version"), 20)
        ulos.append({"lahde": "npm", "nimi": nimi, "url": "https://www.npmjs.com/package/" + nimi,
                     "kuvaus": puhdista(paketti.get("description"), 160), "mitta": "v" + versio})
    return ulos


def etsi(kysely, hae=None, odota=None, ensimmainen=True):
    """GitHub + npm. Palauttaa {'ok': bool, 'ehdokkaat': [...], 'virheet': [koodit]}.

    ensimmainen=False: odota ennen ensimmaista pyyntoa (edellinen haku on juuri tehty).
    ok on True, kun vahintaan yksi lahde vastasi. Jos kumpikaan ei vastannut, ok=False:
    se on 'ei tietoa', ei 'ei loytynyt'."""
    odota = odota or time.sleep
    ehdokkaat, virheet, vastasi = [], [], 0
    for nro, lahde in enumerate((github, npm)):
        if nro or not ensimmainen:
            odota(rajat.HAKU_TAUKO_SEK)  # tunnistamaton GitHub-haku kuristuu (403), jos pyynnot tulevat tiheaan
        try:
            ehdokkaat += lahde(kysely, hae)
            vastasi += 1
        except HakuVirhe as e:
            virheet.append(e.koodi)
    return {"ok": vastasi > 0, "ehdokkaat": ehdokkaat, "virheet": virheet}
