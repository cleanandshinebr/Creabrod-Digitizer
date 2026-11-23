"""Forme concave : deux ailes separees par le col du creux."""

from prototypes.g3_vision import perception

CONCAVE = [(0, 0), (30, 0), (30, 10), (15, 5), (0, 10)]


def test_concave_deux_ailes():
    resultat = perception.perceive(CONCAVE)

    assert len(resultat.zones) == 2


def test_concave_un_seul_passage():
    resultat = perception.perceive(CONCAVE)

    assert len(resultat.passages) == 1


def test_concave_le_col_mesure_le_creux():
    resultat = perception.perceive(CONCAVE)

    # la pointe du V est a 5 mm du bord bas
    assert abs(resultat.passages[0].largeur - 5.0) < 0.8


def test_concave_les_deux_ailes_sont_terminales():
    resultat = perception.perceive(CONCAVE)

    assert len(resultat.zones_terminales) == 2
