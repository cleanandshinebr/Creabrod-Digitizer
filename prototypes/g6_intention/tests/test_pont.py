"""Tests G6 pour le Pont (Arche)."""

from prototypes.g3_vision import perception
from prototypes.g6_intention import intention, report
from prototypes.g3_vision.tests.test_arche import ARCHE


def test_pont_intention_sur_graphe():
    # Graphe canonique d'un pont G4 : 2 culées terminales et 1 voûte de transition
    graphe_pont = {
        "zones": {
            "culee_gauche": {"id": "culee_gauche", "classe": "terminale"},
            "voute": {"id": "voute", "classe": "transition"},
            "culee_droite": {"id": "culee_droite", "classe": "terminale"},
        },
        "adjacences": {
            "culee_gauche": ["voute"],
            "voute": ["culee_gauche", "culee_droite"],
            "culee_droite": ["voute"],
        },
        "structures": ["Pont"],
    }

    plan = intention.plan_intention(graphe_pont)

    assert plan.structure == "pont"
    assert plan.entry_zone == "culee_gauche"
    assert plan.exit_zone == "culee_droite"
    assert plan.visit_order == ["culee_gauche", "voute", "culee_droite"]
    assert plan.zones_a_terminer_en_premier == ["culee_gauche"]
    assert plan.zones_a_garder_ouvertes == ["voute", "culee_droite"]


def test_pont_sur_arche_g3():
    # Avec l'objet Perception direct de l'Arche
    perc = perception.perceive(ARCHE)
    # L'analyse G4 qualifie l'arche de Pont
    perc.structures.append("Pont")
    plan = intention.plan_intention(perc)

    assert plan.structure == "pont"
    assert plan.visit_order == ["culee_gauche", "voute", "culee_droite"]
    txt = report.format_intention(plan, "Arche")
    assert "PONT" in txt
    assert "eventail" in txt.lower() or "éventail" in txt.lower()
