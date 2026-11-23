"""Forme a trou : quatre bandes en cycle, reconnues comme un anneau."""

from prototypes.g3_vision import perception

CONTOUR = [(0, 0), (40, 0), (40, 40), (0, 40)]
TROU = [((12, 12), (28, 12), (28, 28), (12, 28))]


def test_trou_anneau_reconnu():
    resultat = perception.perceive(CONTOUR, TROU)

    assert "Anneau" in resultat.structures


def test_trou_quatre_bandes_en_cycle():
    resultat = perception.perceive(CONTOUR, TROU)

    # quatre bandes, chacune reliee a deux voisines : un cycle, pas une chaine
    assert len(resultat.zones) == 4
    assert len(resultat.passages) == 4
    assert all(zone.degre == 2 for zone in resultat.zones)


def test_trou_chaque_bande_est_une_transition():
    resultat = perception.perceive(CONTOUR, TROU)

    assert resultat.zones_terminales == []
    assert len(resultat.zones_de_transition) == 4


def test_trou_les_cols_mesurent_la_largeur_des_bandes():
    resultat = perception.perceive(CONTOUR, TROU)

    for passage in resultat.passages:
        assert abs(passage.largeur - 12.0) < 1.0
