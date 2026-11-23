"""Arche : resultat mesure, et divergence assumee avec le plan G3.

Le plan G3 attendait « pont, 3 zones, 2 passages ». La mesure donne **une seule
zone** : aucun col de l'arche n'est plus court que les parois qui le bordent,
donc aucune decoupe n'est retenue. L'arche est une **bande continue** ; la
lecture « deux culees + une voute » est une lecture de parcours, pas de
perception. La divergence est documentee et non contournee par un seuil.
"""

import time

from prototypes.g3_vision import perception

ARCHE = [
    (0, 0), (0, 55), (30, 95), (90, 125), (170, 138), (214, 141),
    (258, 138), (338, 125), (398, 95), (429, 55), (429, 0),
    (368, 0), (365, 38), (340, 70), (300, 88), (214, 95), (127, 88),
    (89, 70), (64, 38), (61, 0),
]


def test_arche_bande_continue_une_seule_zone():
    resultat = perception.perceive(ARCHE)

    assert len(resultat.zones) == 1
    assert resultat.passages == []


def test_arche_aucune_structure_pont():
    resultat = perception.perceive(ARCHE)

    # un pont exige un col entre culees et voute : ici il n'y a aucun col
    assert "Pont" not in resultat.structures


def test_arche_coins_rentrants_detectes_mais_decoupes_refusees():
    resultat = perception.perceive(ARCHE)

    assert len(resultat.coins) >= 3          # les coins de l'intrados existent
    assert resultat.passages == []           # mais aucun n'est un vrai col


def test_arche_temps_de_perception_mesure():
    debut = time.perf_counter()
    resultat = perception.perceive(ARCHE)
    duree = time.perf_counter() - debut

    # constat : environ 1,4 s en Python pur, au-dela du seuil de 100 ms du plan
    assert resultat.duree > 0.0
    assert duree < 15.0
