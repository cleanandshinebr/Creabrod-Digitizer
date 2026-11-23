"""Tests G6 pour l'Arborescence (Dorsale et ramifications)."""

from prototypes.g6_intention import intention, report


def test_arborescence_intention():
    # Topologie : Dorsale (D1 -> D2 -> D3) avec rameaux latéraux (R1 sur D1, R2 sur D2)
    graphe_arborescence = {
        "zones": {
            "dorsale_1": {"id": "dorsale_1", "classe": "transition", "degre": 3},
            "rameau_1": {"id": "rameau_1", "classe": "cul-de-sac", "degre": 1},
            "dorsale_2": {"id": "dorsale_2", "classe": "transition", "degre": 3},
            "rameau_2": {"id": "rameau_2", "classe": "cul-de-sac", "degre": 1},
            "dorsale_3": {"id": "dorsale_3", "classe": "terminale", "degre": 1},
        },
        "adjacences": {
            "dorsale_1": ["rameau_1", "dorsale_2"],
            "rameau_1": ["dorsale_1"],
            "dorsale_2": ["dorsale_1", "rameau_2", "dorsale_3"],
            "rameau_2": ["dorsale_2"],
            "dorsale_3": ["dorsale_2"],
        },
        "structures": ["Arborescence"],
    }

    plan = intention.plan_intention(graphe_arborescence, entry_pref="dorsale_1", exit_pref="dorsale_3")

    assert plan.structure == "arborescence"
    assert plan.entry_zone == "dorsale_1"
    assert plan.exit_zone == "dorsale_3"
    # Les rameaux latéraux doivent être éteints
    assert "rameau_1" in plan.visit_order
    assert "rameau_2" in plan.visit_order

    txt = report.format_intention(plan, "Arborescence Peigne")
    assert "ARBORESCENCE" in txt
    assert "balai de fond" in txt.lower() or "rameau" in txt.lower()
