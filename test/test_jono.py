import unittest

from agentti import ideat, jono, rajat


def idea(id_, tila="avoin", riippuu=(), koko=None, hyoty=None, otsikko="o"):
    return ideat.Idea(id_, otsikko, "lause", "", tuple(riippuu), tila, koko, hyoty)


def arvio(koko=None, hyoty=None, esi=None, syy=""):
    m = {"tiiviste": None, "pisteet": {"syy": syy}}
    if koko is not None:
        m["pisteet"]["koko"] = koko
    if hyoty is not None:
        m["pisteet"]["hyoty"] = hyoty
    if esi:
        m["esitutkimus"] = {"tulos": esi}
    return m


def valimuisti(*pareja):
    """pareja: (idea, merkinta); tiiviste asetetaan ideaan sopivaksi."""
    ulos = {}
    for i, m in pareja:
        m = dict(m)
        m["tiiviste"] = i.tiiviste
        ulos[i.id] = m
    return ulos


class PisteTesti(unittest.TestCase):
    def test_kaava(self):
        # hyoty 5, koko 1: 2*5 + (6-1) = 15 = maksimi
        self.assertEqual(jono.piste(1, 5, False), jono.piste_max())
        self.assertEqual(jono.piste_max(), 15)
        # hyoty 1, koko 5: 2*1 + 1 = 3
        self.assertEqual(jono.piste(5, 1, False), 3)

    def test_samankaltaisuus_vahentaa_rangaistuksen(self):
        self.assertEqual(jono.piste(2, 4, True), jono.piste(2, 4, False) - rajat.PISTE_SAMANKALTAINEN_RANGAISTUS)

    def test_puuttuva_arvio_ei_pisteyta(self):
        self.assertIsNone(jono.piste(None, 3, False))
        self.assertIsNone(jono.piste(3, None, False))

    def test_kaavan_vakiot_ovat_jarkevia(self):
        self.assertGreater(rajat.PISTE_HYOTY_KERROIN, 0)
        self.assertGreater(rajat.PISTE_MAX, rajat.PISTE_MIN)
        # paras mahdollinen piste miinus rangaistus on yha suurempi kuin huonoin mahdollinen
        self.assertGreater(jono.piste_max() - rajat.PISTE_SAMANKALTAINEN_RANGAISTUS, jono.piste(rajat.PISTE_MAX, rajat.PISTE_MIN, False))


class JonoTesti(unittest.TestCase):
    def test_jarjestys_pisteen_mukaan_ja_tasapeli_idlla(self):
        a, b, c = idea("a-id"), idea("b-id"), idea("c-id")
        v = valimuisti((a, arvio(3, 3)), (b, arvio(1, 5)), (c, arvio(3, 3)))
        self.assertEqual([r["id"] for r in jono.jono([a, b, c], v)], ["b-id", "a-id", "c-id"])

    def test_omistajan_arvio_ohittaa_mallin(self):
        a = idea("a-id", koko=1, hyoty=5)
        v = valimuisti((a, arvio(5, 1)))
        r = jono.jono([a], v)[0]
        self.assertEqual((r["koko"], r["hyoty"], r["pisteiden_lahde"], r["piste"]), (1, 5, "oma", 15))

    def test_osittainen_oma_arvio_yhdistyy_mallin_kanssa(self):
        a = idea("a-id", koko=2)
        v = valimuisti((a, arvio(koko=5, hyoty=4)))
        r = jono.jono([a], v)[0]
        self.assertEqual((r["koko"], r["hyoty"], r["pisteiden_lahde"]), (2, 4, "oma+malli"))

    def test_pisteyttamaton_on_pisteytettyjen_jalkeen(self):
        a, b = idea("a-id"), idea("b-id")
        v = valimuisti((b, arvio(5, 1)))
        self.assertEqual([r["id"] for r in jono.jono([a, b], v)], ["b-id", "a-id"])

    def test_valmis_ja_hylatty_eivat_ole_jonossa(self):
        a, b, c = idea("a-id", "valmis"), idea("b-id", "hylatty"), idea("c-id", "kesken")
        self.assertEqual([r["id"] for r in jono.jono([a, b, c], {})], ["c-id"])

    def test_riippuvuus_pitaa_idean_jumissa_ja_viimeisena(self):
        a = idea("a-id", riippuu=["b-id"])
        b = idea("b-id")
        v = valimuisti((a, arvio(1, 5)), (b, arvio(5, 1)))
        tulos = jono.jono([a, b], v)
        self.assertEqual([r["id"] for r in tulos], ["b-id", "a-id"])
        self.assertEqual(tulos[1]["jumissa"], ["b-id"])

    def test_riippuvuus_vapautuu_kun_toinen_on_valmis(self):
        a = idea("a-id", riippuu=["b-id"])
        b = idea("b-id", "valmis")
        self.assertEqual(jono.jono([a, b], {})[0]["jumissa"], [])

    def test_tuntematon_riippuvuus_ei_vapauta(self):
        a = idea("a-id", riippuu=["ei-ole"])
        self.assertEqual(jono.jono([a], {})[0]["jumissa"], ["ei-ole"])

    def test_samankaltainen_laskee_jarjestyksessa(self):
        a, b = idea("a-id"), idea("b-id")
        v = valimuisti((a, arvio(2, 4, esi="samankaltainen_loytyy")), (b, arvio(2, 4, esi="ei_samankaltaista")))
        self.assertEqual([r["id"] for r in jono.jono([a, b], v)], ["b-id", "a-id"])

    def test_muuttunut_idea_hylkaa_vanhan_arvion(self):
        a = idea("a-id")
        v = {"a-id": {"tiiviste": "vanha", "pisteet": {"koko": 1, "hyoty": 5, "syy": "x"}}}
        r = jono.jono([a], v)[0]
        self.assertIsNone(r["piste"])


if __name__ == "__main__":
    unittest.main()
