"""Rectangle : une seule salle, aucun passage.

Ce fichier verifie aussi l'independance du prototype : il ne doit importer
aucun module du moteur.
"""

import sys

from prototypes.g3_vision import perception

RECTANGLE = [(0, 0), (20, 0), (20, 20), (0, 20)]


def test_rectangle_une_seule_zone():
    resultat = perception.perceive(RECTANGLE)

    assert len(resultat.zones) == 1
    assert resultat.passages == []
    assert resultat.structures == []


def test_rectangle_degagement_maximal_est_la_demi_largeur():
    resultat = perception.perceive(RECTANGLE)

    # une salle de 20 mm de cote : le point le plus degage est a 10 mm du bord
    assert abs(resultat.zones[0].degagement_max - 10.0) < 0.6


def test_rectangle_ne_produit_aucune_couture():
    resultat = perception.perceive(RECTANGLE)

    texte = repr(resultat.zones) + repr(resultat.passages) + repr(resultat.journal)
    for interdit in ("rangée", "rangee", "aiguille", "dst", "ordre"):
        assert interdit not in texte.lower()


def test_format_perception_restitue_le_rapport():
    from prototypes.g3_vision import report
    resultat = perception.perceive(RECTANGLE)
    texte = report.format_perception(resultat, "Rectangle")
    assert "=== Rectangle ===" in texte
    assert "zones : 1" in texte
    assert "passages : 0" in texte


def test_le_prototype_n_importe_aucun_module_du_moteur():
    import prototypes.g3_vision.geometry  # noqa: F401
    import prototypes.g3_vision.report  # noqa: F401

    interdits = ("core.stitches.fill", "core.stitches.planning",
                 "core.stitches.engine", "exporters.dst_io", "core.simulation")
    for module in list(sys.modules):
        assert module not in interdits, "module du moteur importe : " + module
