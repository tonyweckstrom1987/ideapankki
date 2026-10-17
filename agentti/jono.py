"""Priorisointikaava ja jono. Tama on LAKI: pisteet lasketaan koodissa, malli antaa vain
1-5 arviot (tai ei mitaan). Malli ei paata jarjestysta.

    prioriteetti = PISTE_HYOTY_KERROIN x hyoty + (PISTE_MAX + 1 - koko) - rangaistus

rangaistus = PISTE_SAMANKALTAINEN_RANGAISTUS, jos esitutkimus loysi samankaltaisen.
Jos koko tai hyoty puuttuu (omaa tai mallin arviota ei ole), ideaa EI pisteyteta.
Riippuvuus tulee tiedoston riippuu=-kentasta: idea on jumissa, kunnes kaikki sen riippuvuudet
ovat tilassa valmis. Tuntematon riippuvuus-id pitaa idean jumissa (ei arvata).
"""
from . import rajat


def omat_tai_mallin(idea, merkinta):
    """Palauttaa (koko, hyoty, lahde). Omistajan arvo ohittaa mallin."""
    mallin = (merkinta or {}).get("pisteet") or {}
    koko = idea.koko if idea.koko is not None else mallin.get("koko")
    hyoty = idea.hyoty if idea.hyoty is not None else mallin.get("hyoty")
    if idea.koko is not None and idea.hyoty is not None:
        lahde = "oma"
    elif idea.koko is None and idea.hyoty is None:
        lahde = "malli"
    else:
        lahde = "oma+malli"
    return koko, hyoty, lahde


def piste(koko, hyoty, samankaltainen):
    if koko is None or hyoty is None:
        return None
    p = rajat.PISTE_HYOTY_KERROIN * hyoty + (rajat.PISTE_MAX + 1 - koko)
    if samankaltainen:
        p -= rajat.PISTE_SAMANKALTAINEN_RANGAISTUS
    return p


def piste_max():
    return rajat.PISTE_HYOTY_KERROIN * rajat.PISTE_MAX + rajat.PISTE_MAX


def jumissa(idea, kaikki):
    """Palauttaa listan id:ita, joita idea odottaa (tyhja = ei jumissa)."""
    tilat = {i.id: i.tila for i in kaikki}
    return [r for r in idea.riippuu if tilat.get(r) != "valmis"]


def jono(ideat, valimuisti):
    """Jarjestetty lista dicteja: avoimet ja keskeneraiset ideat, parhaat ensin.

    Jarjestys: pisteytetyt ja vapaat (piste laskeva, id) -> pisteyttamattomat vapaat -> jumissa."""
    ulos = []
    for idea in ideat:
        if idea.tila not in ("avoin", "kesken"):
            continue
        merkinta = valimuisti.get(idea.id)
        if merkinta and merkinta.get("tiiviste") != idea.tiiviste:
            merkinta = None  # idea on muuttunut: vanha arvio ei enaa koske sita
        esi = ((merkinta or {}).get("esitutkimus") or {}).get("tulos")
        koko, hyoty, lahde = omat_tai_mallin(idea, merkinta)
        odottaa = jumissa(idea, ideat)
        ulos.append({
            "id": idea.id, "otsikko": idea.otsikko, "tila": idea.tila,
            "koko": koko, "hyoty": hyoty, "pisteiden_lahde": lahde,
            "piste": piste(koko, hyoty, esi == "samankaltainen_loytyy"),
            "esitutkimus": esi, "jumissa": odottaa,
            "perustelu": ((merkinta or {}).get("pisteet") or {}).get("syy", ""),
        })

    def avain(r):
        if r["jumissa"]:
            ryhma = 2
        elif r["piste"] is None:
            ryhma = 1
        else:
            ryhma = 0
        return (ryhma, -(r["piste"] or 0), r["id"])

    return sorted(ulos, key=avain)
