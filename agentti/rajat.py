"""LAKI: kovakoodatut rajat.

Nama arvot eivat tule ymparistomuuttujista eivatka komentorivilta. Agentti, prompt tai
LLM-vastaus ei voi muuttaa niita. Muutos vaatii omistajan nimenomaisen luvan ja oman
commitin. Testi (test_rajat.py) varmistaa, etta rajat ovat jarkeva kokonaisuus.
"""

KULU_PAIVA_USD = 0.05        # paivan kulukatto
KULU_KUUKAUSI_USD = 1.00     # kuukauden kulukatto (alle 31 x paivakatto, jotta se on oikeasti voimassa)
KUTSUT_PAIVA = 3             # LLM-kutsuja enintaan paivassa
KUTSU_ARVIO_USD = 0.015      # pessimistinen varaus ennen jokaista kutsua

MAX_TOKENS = 2000            # vastauksen katto per kutsu
LLM_AIKAKATKAISU = 120       # sekuntia

TELEGRAM_MAX_MERKKEJA = 3500
TELEGRAM_AIKAKATKAISU = 20
SYDAN_AIKAKATKAISU = 10

# Hinnat USD / miljoona tokenia: malli -> (syote, tuloste). Tyhja = ei tunneta,
# jolloin kirjanpitoon jaa pessimistinen varaus. Hinnaston muutos = lakimuutos.
HINNAT_USD_PER_MILJOONA = {}

# --- ideapankki-agentin rajat (LAKI, sama saanto: muutos vaatii omistajan luvan) ---
IDEAT_MAX = 200                    # ideoita tiedostossa enintaan
IDEAT_TIEDOSTO_MAX_TAVUA = 200_000
ERA_KOKO = 8                       # ideoita per ajo (haku + yksi LLM-kutsu)
ESITUTKIMUS_VOIMASSA_PAIVAA = 30   # vanhempi esitutkimus tehdaan uudelleen
HAKU_EHDOKKAITA = 5                # ehdokasta per lahde
HAKU_AIKAKATKAISU = 15             # sekuntia per pyynto
HAKU_VASTAUS_MAX_TAVUA = 1_000_000
HAKU_TAUKO_SEK = 7                 # GitHubin tunnistamaton hakuraja on noin 10 / min
HAKU_PYYNTOJA_AJOSSA = 2 * ERA_KOKO
PISTE_MIN = 1
PISTE_MAX = 5
PISTE_HYOTY_KERROIN = 2            # prioriteetti = kerroin x hyoty + (6 - koko) - rangaistus
PISTE_SAMANKALTAINEN_RANGAISTUS = 3
JONO_NAYTA = 5                     # kuinka monta ideaa viestissa
EHDOTUS_UUDELLEEN_PAIVAA = 14      # sama idea ehdotetaan uudestaan aikaisintaan taman jalkeen
