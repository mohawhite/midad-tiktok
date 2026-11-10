import random
from datetime import date, timedelta

import pytest
import yaml

from midad import legende, suivi
from midad.decoupage import VERSETS, decouper
from midad.layout import _split_arabic, _split_french
from midad.sources import skeleton

CFG = yaml.safe_load(open("config.yaml", encoding="utf-8"))


def faux_decoupage(n):
    """Découpage factice : des parties de 10 versets."""
    total = VERSETS[n - 1]
    return [[a, min(a + 9, total)] for a in range(1, total + 1, 10)]


# --- table de référence -------------------------------------------------

def test_table_des_versets():
    assert len(VERSETS) == 114
    assert sum(VERSETS) == 6236


# --- découpage ----------------------------------------------------------

def test_sourate_courte_en_une_partie():
    assert decouper([5.0] * 7) == [[1, 7]]


@pytest.mark.parametrize("graine", range(20))
def test_decoupage_couvre_tout_sans_couper(graine):
    rng = random.Random(graine)
    durees = [rng.uniform(3, 45) for _ in range(rng.randint(30, 286))]
    parts = decouper(durees)
    assert parts[0][0] == 1 and parts[-1][1] == len(durees)
    for a, b in zip(parts, parts[1:]):
        assert b[0] == a[1] + 1          # ni trou ni chevauchement
    for i, (a, b) in enumerate(parts):
        d = sum(durees[a - 1:b])
        assert d <= 180
        if i < len(parts) - 1:
            assert d >= 60


def test_verset_plus_long_que_la_limite_reste_entier():
    parts = decouper([50, 50, 200, 50, 50, 50])
    assert [3, 3] in parts


# --- basmala et comparaison de texte ------------------------------------

def test_squelette_ignore_les_differences_de_signes():
    assert skeleton("ٱلْعَٰلَمِينَ") == skeleton("ٱلْعَـٰلَمِينَ")
    assert skeleton("قُلْ هُوَ ٱللَّهُ أَحَدٌ") != skeleton("ٱللَّهُ ٱلصَّمَدُ")


# --- découpage d'un verset long à l'écran -------------------------------

def test_decoupe_arabe_conserve_tous_les_mots():
    texte = "ذَٰلِكَ ٱلْكِتَٰبُ لَا رَيْبَ ۛ فِيهِ ۛ هُدًى لِّلْمُتَّقِينَ"
    parts = _split_arabic(texte, 2)
    assert len(parts) == 2
    assert " ".join(parts) == texte
    assert not parts[1].startswith("ۛ")   # une marque de pause ne commence jamais un écran


def test_decoupe_francaise_conserve_tous_les_mots():
    texte = "C'est le Livre au sujet duquel il n'y a aucun doute, c'est un guide pour les pieux."
    parts = _split_french(texte, [0.5, 0.5])
    assert " ".join(parts) == texte


# --- légende ------------------------------------------------------------

def test_legende_sourate_longue():
    p = suivi.Passage("principal", 2, 17, 24, 3, 40)
    lignes = legende.legende("Al-Baqara", p, CFG).split("\n")
    assert lignes[0] == "Al-Baqara, partie 3/40 (versets 17 à 24)"
    assert lignes[1] == "Récitation : Mishary Rashid Alafasy"
    assert lignes[2] == "Traduction : Muhammad Hamidullah"
    tags = lignes[-1].split()
    assert 3 <= len(tags) <= 5 and "#albaqara" in tags


def test_legende_sourate_courte():
    p = suivi.Passage("principal", 1, 1, 7, 1, 1)
    assert legende.legende("Al-Fatiha", p, CFG).startswith("Al-Fatiha (versets 1 à 7)")


# --- suivi et planning --------------------------------------------------

def test_ordre_contient_les_114_sourates():
    seq = suivi.ordre(CFG)
    assert seq[:4] == [1, 112, 113, 114] and seq[4] == 78 and len(seq) == 114


def simuler(jours, debut=date(2026, 11, 11)):
    state = suivi.vide()
    for i in range(jours):
        jour = debut + timedelta(days=i)
        p = suivi.prochain(state, jour, CFG, faux_decoupage)
        if p is None:
            break
        suivi.enregistrer(state, p, jour, "essai")
    return state


def test_ni_repetition_ni_saut_dans_la_progression_principale():
    state = simuler(1200)
    vus = [(p["sourate"], p["debut"], p["fin"]) for p in state["publications"] if p["flux"] == "principal"]
    assert len(vus) == len(set(vus))
    attendu = [(s, a, b) for s in suivi.ordre(CFG) for a, b in faux_decoupage(s)]
    assert vus == attendu[:len(vus)]
    assert len(vus) > 600


def test_vendredi_al_kahf_dans_l_ordre():
    state = simuler(120)
    for p in state["publications"]:
        vendredi = date.fromisoformat(p["date"]).weekday() == 4
        assert (p["flux"] == "vendredi") == vendredi
        if vendredi:
            assert p["sourate"] == 18
    parties = [p["partie"] for p in state["publications"] if p["flux"] == "vendredi"]
    assert parties[:11] == list(range(1, 12))
    assert parties[11] == 1          # après la dernière partie, on reprend au début


def test_ramadan_passe_avant_la_progression():
    # Ramadan 1448 : de février à mars 2027.
    state = simuler(140)
    ramadan = [p for p in state["publications"] if p["flux"] == "ramadan"]
    assert len(ramadan) == len(CFG["ramadan"])
    for p in ramadan:
        assert suivi.hegire(date.fromisoformat(p["date"]))[1] == 9
    assert [(p["sourate"], p["debut"]) for p in ramadan] == [(r["sourate"], r["versets"][0]) for r in CFG["ramadan"]]


def test_echec_reprend_le_meme_passage_et_pas_de_double_publication():
    state = suivi.vide()
    lundi, mardi = date(2026, 11, 16), date(2026, 11, 17)
    p1 = suivi.prochain(state, lundi, CFG, faux_decoupage)
    # Échec le lundi : rien n'est enregistré, le mardi reprend le même passage.
    p2 = suivi.prochain(state, mardi, CFG, faux_decoupage)
    assert p1 == p2
    suivi.enregistrer(state, p2, mardi, "essai")
    assert suivi.prochain(state, mardi, CFG, faux_decoupage) is None
    with pytest.raises(ValueError):
        suivi.enregistrer(state, p2, mardi, "essai")


def test_decoupage_fige():
    state = suivi.vide()
    suivi.decoupage(state, 2, faux_decoupage)
    assert suivi.decoupage(state, 2, lambda n: [[1, 286]]) == faux_decoupage(2)
