import unittest

from agentti import rajat


class RajatTesti(unittest.TestCase):
    def test_rajat_ovat_jarkevia(self):
        self.assertGreater(rajat.KULU_PAIVA_USD, 0)
        self.assertGreaterEqual(rajat.KULU_KUUKAUSI_USD, rajat.KULU_PAIVA_USD)
        self.assertGreater(rajat.KUTSU_ARVIO_USD, 0)
        # kaikki sallitut paivan kutsut mahtuvat paivan katon alle
        self.assertLessEqual(rajat.KUTSUT_PAIVA * rajat.KUTSU_ARVIO_USD, rajat.KULU_PAIVA_USD)
        self.assertLessEqual(rajat.MAX_TOKENS, 4096)

    def test_kuukausikatto_on_oikeasti_voimassa(self):
        # jos kuukausikatto olisi >= 31 x paivakatto, se ei koskaan rajoittaisi mitaan
        self.assertLess(rajat.KULU_KUUKAUSI_USD, 31 * rajat.KULU_PAIVA_USD)

    def test_ideapankin_rajat_ovat_jarkevia(self):
        self.assertGreater(rajat.ERA_KOKO, 0)
        # yksi ajo ei saa ylittaa hakupyyntojen kattoa (kaksi lahdetta per idea)
        self.assertLessEqual(2 * rajat.ERA_KOKO, rajat.HAKU_PYYNTOJA_AJOSSA)
        self.assertGreater(rajat.HAKU_TAUKO_SEK, 0)
        self.assertLess(rajat.PISTE_MIN, rajat.PISTE_MAX)
        self.assertGreater(rajat.PISTE_SAMANKALTAINEN_RANGAISTUS, 0)
        self.assertGreater(rajat.ESITUTKIMUS_VOIMASSA_PAIVAA, 0)
        self.assertLessEqual(rajat.JONO_NAYTA, 10)

    def test_hinnat_muoto(self):
        for malli, hinta in rajat.HINNAT_USD_PER_MILJOONA.items():
            self.assertEqual(len(hinta), 2)
            self.assertTrue(all(x >= 0 for x in hinta), malli)


if __name__ == "__main__":
    unittest.main()
