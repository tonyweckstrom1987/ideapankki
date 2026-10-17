"""Ideapankki: priorisoi ideat ja tekee jokaiselle esitutkimuksen (onko sama jo tehty).

Tyonjako: KOODI hakee (GitHub, npm), laskee pisteet (agentti/jono.py) ja rakentaa linkit.
MALLI arvioi vain: (1) onko jokin loydetyista olennaisesti sama kuin idea, (2) koko ja hyoty 1-5.
Malli ei saa tyokaluja, ei paata jarjestysta eika tuota linkkeja. 'Ei tietoa' kelpaa aina.

Ajot (kaikki kayttavat samaa tilaa, kulukatto voimassa):
  python -m agentti --agentti ideapankki                    kuiva-ajo: jono valimuistista, ei verkkoa
  python -m agentti --agentti ideapankki --verkko --llm      hae + arvioi (korkeintaan ERA_KOKO ideaa)
  python -m agentti --agentti ideapankki --verkko --llm --send   lisaksi Telegram + ehdotus putkeen
"""
import json
import os

from .. import config, data as d, haku, ideat as ideat_mod, jono as jono_mod, rajat
from ..ehdotusputki import EhdotusVirhe, kirjoita as kirjoita_ehdotus
from ..lukko import kirjoita_atomisesti, lukittu

NIMI = "ideapankki"
MALLI = "deepseek-flash"
VALIMUISTI = "ideapankki.json"
ESI_TULOKSET = ("samankaltainen_loytyy", "ei_samankaltaista", "ei_tietoa")

SKEEMA = {
    "type": "object",
    "required": ["arviot"],
    "properties": {
        "arviot": {
            "type": "array", "maxItems": rajat.ERA_KOKO,
            "items": {
                "type": "object", "required": ["id"],
                "properties": {
                    "id": {"type": "string", "maxLength": 40},
                    "esitutkimus": {
                        "type": "object", "required": ["tulos"],
                        "properties": {
                            "tulos": {"type": "string", "enum": list(ESI_TULOKSET)},
                            "samankaltaiset": {"type": "array", "maxItems": 10, "items": {"type": "integer"}},
                            "syy": {"type": "string", "maxLength": 160},
                        },
                    },
                    "pisteet": {
                        "type": "object",
                        "properties": {
                            "koko": {"type": "integer"},
                            "hyoty": {"type": "integer"},
                            "syy": {"type": "string", "maxLength": 160},
                        },
                    },
                },
            },
        },
    },
}

TEHTAVA = (
    "Tehtava: arvioi jokainen <data>-lohkon idea erikseen. Kayta vain ideaan kuuluvia tietoja. "
    "Vastaa JSON-muodossa {\"tila\":\"ok\",\"sisalto\":{\"arviot\":[{\"id\":\"...\","
    "\"esitutkimus\":{\"tulos\":\"samankaltainen_loytyy|ei_samankaltaista|ei_tietoa\","
    "\"samankaltaiset\":[ehdokasnumerot],\"syy\":\"max 160 merkkia\"},"
    "\"pisteet\":{\"koko\":1-5,\"hyoty\":1-5,\"syy\":\"max 160 merkkia\"}}]}}. "
    "esitutkimus: anna vain jos idealla on tarvitsee_esitutkimus=kylla. samankaltainen_loytyy = "
    "jokin numeroiduista ehdokkaista tekee olennaisesti saman asian (nimea ehdokasnumerot); "
    "ei_samankaltaista = ehdokkaat ovat eri asia; ei_tietoa = kuvaukset eivat riita. "
    "pisteet: anna vain jos tarvitsee_pisteet=kylla. koko: 1 = tunti tai paiva, 5 = useita viikkoja. "
    "hyoty: 1-5, kuinka paljon idea auttaa (a) portfolion naekyvyytta AI-infran, MCP-tyokalujen ja "
    "agenttien alueella tai (b) omaa agenttiinfraa; krypto ei kiinnosta. Jata koko tai hyoty pois, "
    "jos et tieda: se on parempi kuin arvaus. Linkkeja ei tarvita."
)


class ValimuistiVirhe(Exception):
    koodi = "valimuisti_rikki"


def _tyhja():
    return {"versio": 1, "ideat": {}, "ehdotettu": {}}


def lue_valimuisti(tila):
    polku = os.path.join(tila, VALIMUISTI)
    try:
        with open(polku, encoding="utf-8") as f:
            v = json.load(f)
    except FileNotFoundError:
        return _tyhja()
    except (OSError, ValueError):
        raise ValimuistiVirhe()
    if not (isinstance(v, dict) and v.get("versio") == 1 and isinstance(v.get("ideat"), dict)
            and isinstance(v.get("ehdotettu"), dict)):
        raise ValimuistiVirhe()
    return v


def _paiva(ctx):
    return config.paiva(ctx.kello() if ctx.kello else None)


def _paivia_vali(alku, loppu):
    import datetime
    try:
        return (datetime.date.fromisoformat(loppu) - datetime.date.fromisoformat(alku)).days
    except (TypeError, ValueError):
        return 10 ** 6


def _voimassa(valimuisti, idea):
    m = valimuisti["ideat"].get(idea.id)
    return m if isinstance(m, dict) and m.get("tiiviste") == idea.tiiviste else None


def _vanhentunut(m, paiva):
    return _paivia_vali(m.get("haettu"), paiva) > rajat.ESITUTKIMUS_VOIMASSA_PAIVAA


def _tarve(idea, m, paiva):
    tarve = set()
    if idea.haku and (m is None or not m.get("haettu") or _vanhentunut(m, paiva)):
        tarve.add("haku")
    if m is None and not idea.haku:
        tarve.add("koodin_esitutkimus")
    if (idea.koko is None or idea.hyoty is None) and (m is None or m.get("pisteet") is None):
        tarve.add("pisteet")
    if m is not None and m.get("haku_ok") and m.get("ehdokkaat") and m.get("esitutkimus") is None \
            and "haku" not in tarve:
        tarve.add("esitutkimus")
    return tarve


def kerays(ctx):
    polku = ctx.env.get("IDEAT_TIEDOSTO") or "ideat.txt"
    ideat, virheet = ideat_mod.lue(polku)
    valimuisti = lue_valimuisti(ctx.tila)
    paiva = _paiva(ctx)
    tyo = []
    for idea in ideat:
        if idea.tila not in ("avoin", "kesken"):
            continue
        m = _voimassa(valimuisti, idea)
        tarve = _tarve(idea, m, paiva)
        if tarve:
            tyo.append((idea, m, tarve))
        if len(tyo) >= rajat.ERA_KOKO:
            break
    uudet, era, odottaa_hakua = {}, [], 0
    for idea, m, tarve in tyo:
        if "haku" in tarve:
            if not ctx.verkko:
                odottaa_hakua += 1
            else:
                uudet[idea.id] = haku.etsi(idea.haku, ctx.hae_haku, ctx.odota, ensimmainen=not uudet)
    for idea, m, tarve in tyo:
        if idea.id in uudet:
            h = uudet[idea.id]
            ehdokkaat, haku_ok, esi_tarve = h["ehdokkaat"], h["ok"], h["ok"] and bool(h["ehdokkaat"])
        elif m is not None:
            ehdokkaat, haku_ok = m.get("ehdokkaat") or [], bool(m.get("haku_ok"))
            esi_tarve = "esitutkimus" in tarve
        else:
            ehdokkaat, haku_ok, esi_tarve = [], False, False
        pis_tarve = "pisteet" in tarve
        if esi_tarve or pis_tarve:
            era.append({"id": idea.id, "otsikko": idea.otsikko, "lause": idea.lause,
                        "ehdokkaat": ehdokkaat if esi_tarve else [],
                        "tarvitsee_esitutkimus": esi_tarve, "tarvitsee_pisteet": pis_tarve})
    return {"paiva": paiva, "ideat": ideat, "ideavirheet": virheet, "valimuisti": valimuisti,
            "tyo": [(i.id, sorted(t)) for i, _, t in tyo], "uudet": uudet, "era": era,
            "odottaa_hakua": odottaa_hakua,
            "jono": jono_mod.jono(ideat, valimuisti["ideat"])}


def tarvitsee_llm(data):
    return bool(data.get("era"))


def viestit(data):
    rivit = []
    for e in data["era"]:
        rivit.append("IDEA %s" % e["id"])
        rivit.append("otsikko: %s" % e["otsikko"])
        rivit.append("lause: %s" % e["lause"])
        rivit.append("tarvitsee_esitutkimus: %s" % ("kylla" if e["tarvitsee_esitutkimus"] else "ei"))
        rivit.append("tarvitsee_pisteet: %s" % ("kylla" if e["tarvitsee_pisteet"] else "ei"))
        for nro, h in enumerate(e["ehdokkaat"]):
            rivit.append("  ehdokas %d: [%s] %s - %s (%s)" % (nro, h["lahde"], h["nimi"], h["kuvaus"], h["mitta"]))
        rivit.append("")
    return [
        {"role": "system", "content": d.SYSTEM_SAANNOT + " " + TEHTAVA},
        {"role": "user", "content": d.data_lohko("\n".join(rivit))},
    ]


def _esi_koodista(tulos, syy):
    return {"tulos": tulos, "samankaltaiset": [], "syy": syy}


def _yhdista(data, sisalto, paiva):
    """Palauttaa uuden valimuistin: haut, koodin tuomiot ja validoidut mallin arviot."""
    uusi = json.loads(json.dumps(data["valimuisti"]))
    ideat = {i.id: i for i in data["ideat"]}
    tyoid = {i for i, _ in data["tyo"]}
    for id_, h in data["uudet"].items():
        idea = ideat[id_]
        m = _voimassa(uusi, idea) or {"tiiviste": idea.tiiviste, "pisteet": None}
        m.update({"tiiviste": idea.tiiviste, "haettu": paiva, "ehdokkaat": h["ehdokkaat"],
                  "haku_ok": h["ok"], "haku_virheet": h["virheet"], "esitutkimus": None})
        if not h["ok"]:
            m["esitutkimus"] = _esi_koodista("ei_tietoa", "haku epaonnistui: " + ",".join(h["virheet"]))
        elif not h["ehdokkaat"]:
            if h["virheet"]:
                m["esitutkimus"] = _esi_koodista("ei_tietoa", "haku puutteellinen: " + ",".join(h["virheet"]))
            else:
                m["esitutkimus"] = _esi_koodista("ei_loytynyt", "haku ei tuottanut osumia")
        uusi["ideat"][id_] = m
    for id_ in sorted(tyoid):
        idea = ideat[id_]
        if not idea.haku and _voimassa(uusi, idea) is None:
            uusi["ideat"][id_] = {"tiiviste": idea.tiiviste, "haettu": None, "ehdokkaat": [],
                                  "haku_ok": False, "pisteet": None,
                                  "esitutkimus": _esi_koodista("ei_tietoa", "ei hakusanaa")}
    nahdyt = set()
    erat = {e["id"]: e for e in data["era"]}
    for a in (sisalto or {}).get("arviot", []):
        e = erat.get(a["id"])
        if e is None or a["id"] in nahdyt:
            continue
        nahdyt.add(a["id"])
        idea = ideat[a["id"]]
        m = _voimassa(uusi, idea) or {"tiiviste": idea.tiiviste, "haettu": None, "ehdokkaat": [],
                                      "haku_ok": False, "esitutkimus": None, "pisteet": None}
        es = a.get("esitutkimus")
        if es and e["tarvitsee_esitutkimus"]:
            n = len(e["ehdokkaat"])
            idx = sorted({i for i in es.get("samankaltaiset", []) if 0 <= i < n})
            tulos, syy = es["tulos"], haku.puhdista(es.get("syy", ""), 160)
            if tulos == "samankaltainen_loytyy" and not idx:
                tulos, syy = "ei_tietoa", "malli ei nimennyt ehdokasta"
            if tulos != "samankaltainen_loytyy":
                idx = []
            if tulos == "ei_samankaltaista" and m.get("haku_virheet"):
                # toinen lahde ei vastannut: 'ei samankaltaista' olisi vaara varmuus
                tulos, syy = "ei_tietoa", "haku puutteellinen: " + ",".join(m["haku_virheet"])
            m["esitutkimus"] = {"tulos": tulos, "samankaltaiset": idx, "syy": syy}
        pi = a.get("pisteet")
        if pi is not None and e["tarvitsee_pisteet"]:
            p = {"syy": haku.puhdista(pi.get("syy", ""), 160)}
            for k in ("koko", "hyoty"):
                v = pi.get(k)
                if isinstance(v, int) and rajat.PISTE_MIN <= v <= rajat.PISTE_MAX:
                    p[k] = v
            m["pisteet"] = p
            m["arvioitu"] = paiva
        uusi["ideat"][a["id"]] = m
    return uusi


def _esi_teksti(r, valimuisti):
    m = valimuisti["ideat"].get(r["id"]) or {}
    es = m.get("esitutkimus") or {}
    t = r["esitutkimus"]
    if t == "samankaltainen_loytyy":
        ehd = m.get("ehdokkaat") or []
        nimet = ["%s (%s)" % (ehd[i]["nimi"], ehd[i]["url"]) for i in es.get("samankaltaiset", [])[:2]
                 if 0 <= i < len(ehd)]
        return "samankaltainen loytyy: " + ", ".join(nimet)
    if t == "ei_samankaltaista":
        return "ei samankaltaista"
    if t == "ei_loytynyt":
        return "haku ei loytanyt mitaan"
    if t == "ei_tietoa":
        return "ei tietoa (%s)" % (es.get("syy") or "?")
    return "esitutkimus tekematta"


def render_jono(jono, valimuisti, paiva, lisarivit=()):
    rivit = ["Ideapankki %s" % paiva]
    nayta = [r for r in jono if not r["jumissa"]][:rajat.JONO_NAYTA]
    if not nayta:
        rivit.append("Ei vapaita ideoita jonossa.")
    for nro, r in enumerate(nayta, 1):
        if r["piste"] is None:
            teho = "ei pisteytetty"
        else:
            teho = "%d/%d (hyoty %d, koko %d, %s)" % (r["piste"], jono_mod.piste_max(), r["hyoty"], r["koko"],
                                                  r["pisteiden_lahde"])
        rivit.append("%d. %s [%s] %s" % (nro, r["otsikko"], r["id"], teho))
        if r["perustelu"]:
            rivit.append("   perustelu: " + r["perustelu"])
        rivit.append("   esitutkimus: " + _esi_teksti(r, valimuisti))
    jumissa = sum(1 for r in jono if r["jumissa"])
    pisteyttamatta = sum(1 for r in jono if not r["jumissa"] and r["piste"] is None)
    rivit.append("Jumissa riippuvuuden takia: %d. Pisteyttamatta: %d." % (jumissa, pisteyttamatta))
    rivit += list(lisarivit)
    return "\n".join(rivit)


def _lisarivit(data):
    ulos = []
    if data["odottaa_hakua"]:
        ulos.append("Odottaa hakua (aja --verkko): %d ideaa." % data["odottaa_hakua"])
    if data["ideavirheet"]:
        ulos.append("Ideatiedoston virheita: %d (%s)." % (len(data["ideavirheet"]), "; ".join(data["ideavirheet"][:3])))
    return ulos


def render_kuiva(data):
    teksti = render_jono(data["jono"], data["valimuisti"], data["paiva"], _lisarivit(data))
    if data["era"]:
        teksti += "\nArvioitavana ajossa: %d ideaa." % len(data["era"])
    return teksti


def _ehdota(ctx, jono, valimuisti, paiva):
    """Yksi ehdotus per ajo: paras vapaa pisteytetty idea, ei samaa uudestaan liian pian."""
    kansio = ctx.env.get("EHDOTUS_POSTILAATIKKO")
    if not (ctx.laheta and kansio):
        return None
    for r in jono:
        if r["jumissa"] or r["piste"] is None:
            continue
        edellinen = valimuisti["ehdotettu"].get(r["id"])
        if edellinen and _paivia_vali(edellinen, paiva) < rajat.EHDOTUS_UUDELLEEN_PAIVAA:
            continue
        teksti = "Aloita seuraavaksi: %s (%d/%d)" % (r["otsikko"], r["piste"], jono_mod.piste_max())
        try:
            kirjoita_ehdotus(kansio, teksti, ctx.kello)
        except EhdotusVirhe as e:
            return "Ehdotus ei mennyt putkeen (%s)." % e.koodi
        valimuisti["ehdotettu"][r["id"]] = paiva
        return "Ehdotus jatetty postilaatikkoon: %s." % r["otsikko"]
    return None


def loppu(ctx, data, sisalto):
    paiva = data["paiva"]
    polku = os.path.join(ctx.tila, VALIMUISTI)
    with lukittu(os.path.join(ctx.tila, "ideapankki.lock")):
        uusi = _yhdista(data, sisalto, paiva)
        jono = jono_mod.jono(data["ideat"], uusi["ideat"])
        lisa = _lisarivit(data)
        ehd = _ehdota(ctx, jono, uusi, paiva)
        kirjoita_atomisesti(polku, json.dumps(uusi, sort_keys=True, indent=1))
    if ehd:
        lisa.append(ehd)
    uusia = len(data["uudet"])
    if uusia:
        lisa.append("Haettu tassa ajossa: %d ideaa." % uusia)
    paattamatta = [e["id"] for e in data["era"] if e["id"] not in {a["id"] for a in (sisalto or {}).get("arviot", [])}]
    if data["era"] and paattamatta:
        if sisalto is None:
            lisa.append("Arvio odottaa mallikutsua (--llm): %d ideaa." % len(paattamatta))
        else:
            lisa.append("Mallin arvio puuttui %d ideasta (yritetaan uudelleen)." % len(paattamatta))
    return render_jono(jono, uusi, paiva, lisa)
