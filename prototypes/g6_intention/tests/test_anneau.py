"""Tests G6 pour l'Anneau (Forme à trou)."""

from prototypes.g3_vision import perception
from prototypes.g6_intention import intention, report

CONTOUR = [(0, 0), (40, 0), (40, 40), (0, 40)]
TROU = [((12, 12), (28, 12), (28, 28), (12, 28))]


def test_anneau_boucle_complete():
    perc = perception.perceive(CONTOUR, TROU)
    plan = intention.plan_intention(perc)

    assert plan.structure == "anneau"
    # L'entrée et la sortie doivent boucler sur la même zone
    assert plan.entry_zone == plan.exit_zone
    # La visite doit parcourir toutes les zones et revenir au point de départ
    assert plan.visit_order[0] == plan.visit_order[-1]
    assert len(set(plan.visit_order)) == len(perc.zones)
    assert len(plan.visit_order) == len(perc.zones) + 1
    assert any("bouclage" in r.lower() for r in plan.reprises_autorisees)


def test_anneau_report():
    perc = perception.perceive(CONTOUR, TROU)
    plan = intention.plan_intention(perc)
    txt = report.format_intention(plan, "Trou")

    assert "ANNEAU" in txt
    assert "Rotation continue unidirectionnelle" in txt
