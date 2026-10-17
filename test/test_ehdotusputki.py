import os
import tempfile
import unittest

from agentti import ehdotusputki as ep
from test.apu import kello


class EhdotusputkiTesti(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.kansio = self.tmp.name

    def test_kirjoittaa_numeroidun_tiedoston(self):
        n1 = ep.kirjoita(self.kansio, "Otsikko", "Teksti", kello())
        n2 = ep.kirjoita(self.kansio, "Toinen", "Teksti", kello())
        self.assertEqual((n1, n2), ("PENDING-2026-10-16-1.md", "PENDING-2026-10-16-2.md"))
        with open(os.path.join(self.kansio, n1), encoding="utf-8") as f:
            sisalto = f.read()
        self.assertIn("tila: PENDING", sisalto)
        self.assertIn("lahde: ideapankki", sisalto)

    def test_numero_jatkuu_olemassa_olevista(self):
        open(os.path.join(self.kansio, "PENDING-2026-10-15-7.md"), "w").close()
        self.assertEqual(ep.kirjoita(self.kansio, "o", "t", kello()), "PENDING-2026-10-16-8.md")

    def test_teksti_rajataan_140_merkkiin_ja_rivinvaihdot_poistetaan(self):
        n = ep.kirjoita(self.kansio, "o\nx", "a\n" * 200, kello())
        with open(os.path.join(self.kansio, n), encoding="utf-8") as f:
            rivit = f.read().splitlines()
        self.assertEqual(rivit[0], "# o x")
        self.assertLessEqual(len(rivit[2]), ep.TEKSTI_MAX)

    def test_puuttuva_kansio_ei_luoda(self):
        polku = os.path.join(self.kansio, "ei-ole")
        with self.assertRaises(ep.EhdotusVirhe) as e:
            ep.kirjoita(polku, "o", "t", kello())
        self.assertEqual(e.exception.koodi, "ehdotukset_kansio")
        self.assertFalse(os.path.exists(polku))

    def test_numerokilpailu_ei_ylikirjoita_vaan_epaonnistuu(self):
        nimi = ep.kirjoita(self.kansio, "o", "t", kello())
        polku = os.path.join(self.kansio, nimi)
        with open(polku) as f:
            alku = f.read()
        vanha = ep.seuraava_numero
        ep.seuraava_numero = lambda kansio: 1  # kilpaileva kirjoittaja on aina ehtinyt ensin
        self.addCleanup(setattr, ep, "seuraava_numero", vanha)
        with self.assertRaises(ep.EhdotusVirhe) as e:
            ep.kirjoita(self.kansio, "uusi", "uusi teksti", kello())
        self.assertEqual(e.exception.koodi, "ehdotukset_numero")
        with open(polku) as f:
            self.assertEqual(f.read(), alku)

    def test_ei_ylikirjoita_olemassa_olevaa(self):
        nimi = ep.kirjoita(self.kansio, "o", "t", kello())
        polku = os.path.join(self.kansio, nimi)
        with open(polku, "a") as f:
            f.write("oma-merkinta\n")
        ep.kirjoita(self.kansio, "o2", "t2", kello())
        with open(polku) as f:
            self.assertIn("oma-merkinta", f.read())


if __name__ == "__main__":
    unittest.main()
