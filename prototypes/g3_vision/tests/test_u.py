"""Forme en U : trois salles, deux passages, deux extremites, aucun cul-de-sac."""

from prototypes.g3_vision import perception

U_SHAPE = [(0, 0), (20, 0), (20, 20), (14, 20), (14, 8),
           (6, 8), (6, 20), (0, 20)]


def test_u_trois_salles_et_deux_passages():
    resultat = perception.perceive(U_SHAPE)

    assert len(resultat.zones) == 3
    assert len(resultat.passages) == 2


def test_u_deux_extremites_et_aucun_cul_de_sac():
    resultat = perception.perceive(U_SHAPE)

    # les jambes ont une largeur constante : terminales, pas des culs-de-sac
    assert len(resultat.zones_terminales) == 2
    assert resultat.culs_de_sac == []


def test_u_les_cols_mesurent_la_largeur_des_jambes():
    resultat = perception.perceive(U_SHAPE)

    largeurs = sorted(passage.largeur for passage in resultat.passages)
    assert abs(largeurs[0] - 6.0) < 0.6
    assert abs(largeurs[1] - 6.0) < 0.6


def test_u_format_perception_affiche_passages_et_cellules():
    from prototypes.g3_vision import report
    resultat = perception.perceive(U_SHAPE)
    texte = report.format_perception(resultat, "U")
    assert "=== U ===" in texte
    assert "zones : 3" in texte
    assert "passages : 2" in texte
    assert "cellules d'interface" in texte


def test_u_n_est_pas_un_pont():
    resultat = perception.perceive(U_SHAPE)

    # les deux cols sont dans le prolongement l'un de l'autre : couloir, pas pont
    assert "Pont" not in resultat.structures
