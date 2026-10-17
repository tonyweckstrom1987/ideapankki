import os
import tempfile
import unittest

from agentti import ideat, rajat

HYVA = "# kommentti\nidea-yksi | Otsikko yksi | Yksi lause. | haku=mcp server test | koko=2 | hyoty=4\n"


class IdeatTesti(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.polku = os.path.join(self.tmp.name, "ideat.txt")

    def kirjoita(self, teksti):
        with open(self.polku, "w", encoding="utf-8") as f:
            f.write(teksti)
        return ideat.lue(self.polku)

    def test_hyva_rivi(self):
        lista, virheet = self.kirjoita(HYVA)
        self.assertEqual(virheet, [])
        self.assertEqual(len(lista), 1)
        i = lista[0]
        self.assertEqual((i.id, i.otsikko, i.haku, i.koko, i.hyoty, i.tila), (
            "idea-yksi", "Otsikko yksi", "mcp server test", 2, 4, "avoin"))

    def test_puuttuva_tiedosto(self):
        with self.assertRaises(ideat.IdeatVirhe) as e:
            ideat.lue(os.path.join(self.tmp.name, "ei-ole.txt"))
        self.assertEqual(e.exception.koodi, "ideat_puuttuu")

    def test_liian_iso_tiedosto(self):
        with open(self.polku, "w") as f:
            f.write("#" * (rajat.IDEAT_TIEDOSTO_MAX_TAVUA + 1))
        with self.assertRaises(ideat.IdeatVirhe) as e:
            ideat.lue(self.polku)
        self.assertEqual(e.exception.koodi, "ideat_liian_iso")

    def test_virheelliset_rivit_ohitetaan_ja_raportoidaan(self):
        teksti = "\n".join([
            "Iso-Id | otsikko | lause",                       # 1 virheellinen id
            "a | otsikko | lause",                           # 2 liian lyhyt id
            "ok-id | otsikko | lause | tuntematon=1",         # 3 tuntematon avain
            "ok-id | otsikko | lause | koko=9",               # 4 piste yli rajan
            "ok-id | otsikko | lause | koko=x",               # 5 piste ei luku
            "ok-id | otsikko | lause | haku=a;rm -rf",        # 6 haussa kielletyt merkit
            "ok-id | otsikko | lause | tila=outo",            # 7 virheellinen tila
            "ok-id | otsikko | lause | riippuu=ok-id",        # 8 riippuu itsestaan
            "ok-id | otsikko | lause | koko=1 | koko=2",      # 9 avain kahdesti
            "ok-id | otsikko | lause | hyoty",                # 10 ilman '='
            "ok-id | vain kaksi",                             # 11 liian vahan kenttia
            "ok-id | otsikko | lause",                        # 12 kelpaa
            "ok-id | toinen | lause",                         # 13 kaksoisid
            "ok-id2 | otsikko\x07 | lause",                   # 14 ohjausmerkki
        ])
        lista, virheet = self.kirjoita(teksti)
        self.assertEqual([i.id for i in lista], ["ok-id"])
        self.assertEqual(len(virheet), 13)
        self.assertTrue(virheet[0].startswith("rivi 1:"))
        self.assertTrue(virheet[-1].startswith("rivi 14:"))
        self.assertNotIn("rm -rf", " ".join(virheet))  # sisaltoa ei toisteta

    def test_jokainen_virheellinen_rivi_hylataan_yksinaan(self):
        huonot = [
            "Iso-Id | otsikko | lause", "a | otsikko | lause", "ok-id | otsikko | lause | tuntematon=1",
            "ok-id | otsikko | lause | koko=9", "ok-id | otsikko | lause | koko=0", "ok-id | otsikko | lause | hyoty=6",
            "ok-id | otsikko | lause | koko=x", "ok-id | otsikko | lause | haku=a;rm",
            "ok-id | otsikko | lause | tila=outo", "ok-id | otsikko | lause | riippuu=ok-id",
            "ok-id | otsikko | lause | riippuu=Huono Id", "ok-id | otsikko | lause | koko=1 | koko=2",
            "ok-id | otsikko | lause | hyoty", "ok-id | vain kaksi", "ok-id | %s | lause" % ("x" * 81),
            "ok-id | otsikko | %s" % ("x" * 201), "ok-id | otsikko\x07 | lause",
        ]
        for rivi in huonot:
            lista, virheet = self.kirjoita(rivi)
            self.assertEqual(lista, [], rivi)
            self.assertEqual(len(virheet), 1, rivi)

    def test_rajat_hyvaksytaan(self):
        lista, virheet = self.kirjoita("a-id | o | l | koko=1 | hyoty=5\nb-id | %s | %s" % ("x" * 80, "y" * 200))
        self.assertEqual((len(lista), virheet), (2, []))

    def test_ideoita_enintaan_rajan_verran(self):
        rivit = ["id-%03d | otsikko | lause" % i for i in range(rajat.IDEAT_MAX + 3)]
        lista, virheet = self.kirjoita("\n".join(rivit))
        self.assertEqual(len(lista), rajat.IDEAT_MAX)
        self.assertTrue(any("loput ohitettu" in v for v in virheet))

    def test_tiiviste_muuttuu_sisallosta_ei_omista_pisteista(self):
        a, _ = self.kirjoita("x-id | otsikko | lause | haku=aa bb")
        b, _ = self.kirjoita("x-id | otsikko | lause | haku=aa bb | koko=3")
        c, _ = self.kirjoita("x-id | otsikko | lause muuttui | haku=aa bb")
        self.assertEqual(a[0].tiiviste, b[0].tiiviste)
        self.assertNotEqual(a[0].tiiviste, c[0].tiiviste)

    def test_riippuvuudet_ja_tila(self):
        lista, virheet = self.kirjoita("a-id | o | l | riippuu=b-id, c-id | tila=kesken")
        self.assertEqual(virheet, [])
        self.assertEqual((lista[0].riippuu, lista[0].tila), (("b-id", "c-id"), "kesken"))


if __name__ == "__main__":
    unittest.main()
