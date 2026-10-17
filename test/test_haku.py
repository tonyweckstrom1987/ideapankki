import unittest

from agentti import haku, rajat

GH = {"items": [
    {"full_name": "acme/pr-bot", "description": "Review PRs <b>fast</b> https://evil.example/x\x00 now", "stargazers_count": 120},
    {"full_name": "../etc/passwd", "description": "huono nimi", "stargazers_count": 1},
    {"full_name": "acme/other", "description": None, "stargazers_count": True},
]}
NPM = {"objects": [
    {"package": {"name": "@acme/review", "description": "Review", "version": "1.2.3"}},
    {"package": {"name": "Bad Name!", "description": "x", "version": "1"}},
    {"package": {"name": "plain", "description": "y", "version": "0.1.0<script>"}},
    {"foo": "bar"},
]}


class PuhdistaTesti(unittest.TestCase):
    def test_poistaa_linkit_tagit_ja_ohjausmerkit(self):
        self.assertEqual(haku.puhdista("a <b>b</b> https://x.y/z c\x00d\n e", 100), "a b c d e")

    def test_pituusraja_ja_ei_merkkijono(self):
        self.assertEqual(haku.puhdista("x" * 500, 160), "x" * 160)
        self.assertEqual(haku.puhdista(None, 10), "")
        self.assertEqual(haku.puhdista(5, 10), "")


class HakuTesti(unittest.TestCase):
    def test_github_jasennys_ja_url_koodista(self):
        ulos = haku.github("pr review", lambda url: GH)
        self.assertEqual([h["nimi"] for h in ulos], ["acme/pr-bot", "acme/other"])
        self.assertEqual(ulos[0]["url"], "https://github.com/acme/pr-bot")
        self.assertNotIn("evil", ulos[0]["kuvaus"])
        self.assertNotIn("<", ulos[0]["kuvaus"])
        self.assertEqual(ulos[1]["mitta"], "0 tahtea")  # True ei ole kelvollinen tahtiluku

    def test_npm_jasennys_ja_url_koodista(self):
        ulos = haku.npm("pr review", lambda url: NPM)
        self.assertEqual([h["nimi"] for h in ulos], ["@acme/review", "plain"])
        self.assertEqual(ulos[0]["url"], "https://www.npmjs.com/package/@acme/review")
        self.assertNotIn("<", ulos[1]["mitta"])

    def test_osoitteet_ovat_sallituilla_isannoilla(self):
        osoitteet = []
        haku.github("a b", lambda u: osoitteet.append(u) or GH)
        haku.npm("a b", lambda u: osoitteet.append(u) or NPM)
        self.assertTrue(osoitteet[0].startswith("https://api.github.com/search/repositories?"))
        self.assertTrue(osoitteet[1].startswith("https://registry.npmjs.org/-/v1/search?"))

    def test_kysely_validoidaan(self):
        for huono in ("", "a", "a;b", "x" * 101, None, "a\nb"):
            with self.assertRaises(haku.HakuVirhe):
                haku.github(huono, lambda u: GH)

    def test_vaara_vastausmuoto(self):
        for data in ({}, {"items": "ei lista"}, None, []):
            with self.assertRaises(haku.HakuVirhe) as e:
                haku.github("ab", lambda u, d=data: d)
            self.assertEqual(e.exception.koodi, "haku_vastaus")

    def test_oikea_haku_hylkaa_vieraan_isannan_ja_http(self):
        for url in ("https://evil.example/", "http://api.github.com/x", "file:///etc/passwd"):
            with self.assertRaises(haku.HakuVirhe) as e:
                haku._hae_http(url)
            self.assertEqual(e.exception.koodi, "haku_asetus")


class EtsiTesti(unittest.TestCase):
    def test_molemmat_lahteet(self):
        tauot = []
        def hae(url):
            return GH if "github" in url else NPM
        t = haku.etsi("pr review", hae, tauot.append)
        self.assertTrue(t["ok"])
        self.assertEqual(len(t["ehdokkaat"]), 4)
        self.assertEqual(tauot, [rajat.HAKU_TAUKO_SEK])  # tauko lahteiden valissa

    def test_tauko_ennen_ensimmaista_pyyntoa_kun_edellinen_haku_on_tuore(self):
        tauot = []
        haku.etsi("pr review", lambda u: GH if "github" in u else NPM, tauot.append, ensimmainen=False)
        self.assertEqual(tauot, [rajat.HAKU_TAUKO_SEK, rajat.HAKU_TAUKO_SEK])

    def test_yksi_lahde_kaatuu_ok_silti(self):
        def hae(url):
            if "github" in url:
                raise haku.HakuVirhe("haku_http_403")
            return NPM
        t = haku.etsi("pr review", hae, lambda s: None)
        self.assertTrue(t["ok"])
        self.assertEqual(t["virheet"], ["haku_http_403"])

    def test_kumpikaan_ei_vastaa_on_ei_ok_eika_tyhja_loydos(self):
        def hae(url):
            raise haku.HakuVirhe("haku_yhteys")
        t = haku.etsi("pr review", hae, lambda s: None)
        self.assertFalse(t["ok"])
        self.assertEqual(t["ehdokkaat"], [])


if __name__ == "__main__":
    unittest.main()
