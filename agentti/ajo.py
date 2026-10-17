"""Ajon kulku: kerays -> (LLM -> skeematarkistus) -> render -> (Telegram, kerran paivassa).

Oletus on kuiva-ajo: ei verkkoa. Verkkohaku, LLM ja lahetys kytketaan erikseen paalle
(--verkko, --llm, --send). Virhetilanteessa lahetetaan varaviesti raakadatasta ja
virhekoodista, ja paluukoodi on 1, jolloin systemd ja sydamenlyonti nayttavat vian.

Agentin valinnaiset koukut (esimerkki.py ei tarvitse niita):
  tarvitsee_llm(data) -> bool      jos False, mallia ei kutsuta (ei turhaa kulua)
  loppu(ctx, data, sisalto) -> str tallentaa tilan ja rakentaa tekstin; sisalto on None,
                                   kun mallia ei kutsuttu
"""
import os
from dataclasses import dataclass, field
from typing import Callable, Optional

from . import config, kulu as kulu_mod, llm as llm_mod, sydan, telegram, tulos as tulos_mod
from .lukko import kirjoita_atomisesti, lukittu


@dataclass
class Konteksti:
    """Se, mita agentin kerays() ja loppu() saavat tietaa ajosta."""
    tila: str
    env: dict
    verkko: bool = False
    laheta: bool = False
    kello: Optional[Callable] = None
    hae_haku: Optional[Callable] = None   # testeissa: korvaa verkkohaun
    odota: Optional[Callable] = None      # testeissa: ei oikeaa nukkumista
    lisatiedot: dict = field(default_factory=dict)


def _laheta_kerran(teksti, env, tila, kello, hae_tg):
    """'lahetetty' | 'jo_lahetetty' | 'epaonnistui'. Merkki kirjoitetaan vasta onnistumisen jalkeen."""
    paiva = config.paiva(kello() if kello else None)
    merkki = os.path.join(tila, "lahetetty-%s.txt" % paiva)
    with lukittu(os.path.join(tila, "laheta.lock")):
        if os.path.exists(merkki):
            return "jo_lahetetty"
        if not telegram.laheta(teksti, env, hae=hae_tg):
            return "epaonnistui"
        kirjoita_atomisesti(merkki, "ok\n")
    return "lahetetty"


def suorita(agentti, env, tila, *, llm=False, laheta=False, verkko=False, kello=None,
            hae_llm=None, hae_tg=None, hae_sydan=None, hae_haku=None, odota=None):
    """Palauttaa dictin: teksti, koodi (0/1), virhe (str|None), lahetys (str|None)."""
    os.makedirs(tila, mode=0o700, exist_ok=True)
    kulu = kulu_mod.Kulu(tila, kello)
    ctx = Konteksti(tila=tila, env=env, verkko=verkko, laheta=laheta, kello=kello,
                    hae_haku=hae_haku, odota=odota)
    virhe = None
    try:
        data = agentti.kerays(ctx)
    except Exception as e:
        # kerays ei saa kaataa ajoa ilman varaviestia; poikkeuksen sisaltoa ei tulosteta
        data = {}
        virhe = "kerays_" + (getattr(e, "koodi", None) or type(e).__name__)
    loppu = getattr(agentti, "loppu", None)
    tarvitsee = getattr(agentti, "tarvitsee_llm", None)
    teksti = None
    if virhe:
        pass
    elif not llm or (tarvitsee is not None and not tarvitsee(data)):
        try:
            if loppu and (verkko or llm):
                teksti = "[kuiva-ajo, LLM ei kaytossa]\n" + loppu(ctx, data, None)
            else:
                teksti = "[kuiva-ajo, LLM ei kaytossa]\n" + agentti.render_kuiva(data)
        except Exception as e:
            virhe = "loppu_" + type(e).__name__
    else:
        try:
            vastaus, _ = llm_mod.kysy(agentti.viestit(data), agentti.MALLI, env, kulu, hae=hae_llm)
            tulos = tulos_mod.lue(vastaus, agentti.SKEEMA)
            if tulos.tila == "ok":
                teksti = loppu(ctx, data, tulos.sisalto) if loppu else agentti.render(tulos.sisalto)
            else:
                teksti = "%s: en tieda. Syy: %s" % (agentti.NIMI, tulos.syy)
                if loppu:
                    # ei_tietoa on normaali tulos: tallenna silti haut ja nayta jono
                    teksti += "\n" + loppu(ctx, data, None)
        except kulu_mod.KulukattoYlittyi as e:
            virhe = "kulukatto_" + e.syy
        except kulu_mod.KirjanpitoVirhe:
            virhe = "kirjanpito_virhe"
        except llm_mod.LLMVirhe as e:
            virhe = e.koodi
        except tulos_mod.TulosVirhe as e:
            virhe = e.koodi
        except Exception as e:
            virhe = "loppu_" + type(e).__name__
        if virhe and not virhe.startswith("loppu_") and loppu and verkko:
            try:  # haku maksoi aikaa ja pyyntoja: tallenna se, vaikka malli epaonnistui
                loppu(ctx, data, None)
            except Exception:
                pass
    if virhe:
        try:
            raaka = agentti.render_kuiva(data) if data else "(ei dataa)"
        except Exception:
            raaka = "(ei dataa)"
        teksti = "%s: tiivistys ei onnistunut (%s).\n%s" % (agentti.NIMI, virhe, raaka)
    lahetys = _laheta_kerran(teksti, env, tila, kello, hae_tg) if laheta else None
    koodi = 1 if (virhe or lahetys == "epaonnistui") else 0
    if koodi == 0 and laheta:
        sydan.ping(env, hae=hae_sydan)
    return {"teksti": teksti, "koodi": koodi, "virhe": virhe, "lahetys": lahetys}
