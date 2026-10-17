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

    def lue(self, nimi):
        with open(os.path.join(self.kansio, nimi), encoding="utf-8") as f:
            return f.read()

    def test_kirjoittaa_yhden_rivin_tekstitiedoston(self):
        nimi = ep.kirjoita(self.kansio, "Aloita seuraavaksi: X (12/15)", kello())
        self.assertRegex(nimi, r"^ideapankki-2026-10-16-[0-9a-f]{8}\.txt$")
        self.assertEqual(self.lue(nimi), "Aloita seuraavaksi: X (12/15)\n")

    def test_ei_numeroi_eika_kayta_pending_nimia(self):
        ep.kirjoita(self.kansio, "a", kello())
        ep.kirjoita(self.kansio, "b", kello())
        for nimi in os.listdir(self.kansio):
            self.assertFalse(nimi.startswith("PENDING"))
            self.assertTrue(nimi.endswith(".txt"))

    def test_teksti_rajataan_140_merkkiin_ja_rivinvaihdot_poistetaan(self):
        nimi = ep.kirjoita(self.kansio, "a\n" * 200, kello())
        rivit = self.lue(nimi).splitlines()
        self.assertEqual(len(rivit), 1)
        self.assertLessEqual(len(rivit[0]), ep.TEKSTI_MAX)

    def test_tyhja_teksti_hylataan(self):
        with self.assertRaises(ep.EhdotusVirhe) as e:
            ep.kirjoita(self.kansio, " \n ", kello())
        self.assertEqual(e.exception.koodi, "posti_tyhja")
        self.assertEqual(os.listdir(self.kansio), [])

    def test_puuttuva_kansio_ei_luoda(self):
        polku = os.path.join(self.kansio, "ei-ole")
        with self.assertRaises(ep.EhdotusVirhe) as e:
            ep.kirjoita(polku, "t", kello())
        self.assertEqual(e.exception.koodi, "posti_kansio")
        self.assertFalse(os.path.exists(polku))

    def test_symlink_kansio_hylataan(self):
        oikea = os.path.join(self.kansio, "oikea")
        os.mkdir(oikea)
        linkki = os.path.join(self.kansio, "linkki")
        os.symlink(oikea, linkki)
        with self.assertRaises(ep.EhdotusVirhe) as e:
            ep.kirjoita(linkki, "t", kello())
        self.assertEqual(e.exception.koodi, "posti_kansio")
        self.assertEqual(os.listdir(oikea), [])

    def test_sama_teksti_samana_paivana_ei_ylikirjoita(self):
        nimi = ep.kirjoita(self.kansio, "sama", kello())
        with open(os.path.join(self.kansio, nimi), "a", encoding="utf-8") as f:
            f.write("oma-merkinta\n")
        self.assertEqual(ep.kirjoita(self.kansio, "sama", kello()), nimi)
        self.assertIn("oma-merkinta", self.lue(nimi))

    def test_eri_teksti_eri_tiedosto(self):
        self.assertNotEqual(ep.kirjoita(self.kansio, "yksi", kello()), ep.kirjoita(self.kansio, "kaksi", kello()))


if __name__ == "__main__":
    unittest.main()
