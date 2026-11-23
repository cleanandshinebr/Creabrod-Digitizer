"""Tests G6 pour le Carrefour (Croisement en croix / T / X)."""

from prototypes.g6_intention import intention, report


def test_carrefour_intention():
    # Topologie : 4 bras reliés à un centre commun
    graphe_carrefour = {
        "zones": {
            "centre": {"id": "centre", "classe": "noeud_central", "degre": 4},
            "bras_nord": {"id": "bras_nord", "classe": "terminale"},
            "bras_sud": {"id": "bras_sud", "classe": "terminale"},
            "bras_est": {"id": "bras_est", "classe": "terminale"},
            "bras_ouest": {"id": "bras_ouest", "classe": "terminale"},
        },
        "adjacences": {
            "centre": ["bras_nord", "bras_sud", "bras_est", "bras_ouest"],
            "bras_nord": ["centre"],
            "bras_sud": ["centre"],
            "bras_est": ["centre"],
            "bras_ouest": ["centre"],
        },
        "structures": ["Carrefour"],
    }

    plan = intention.plan_intention(graphe_carrefour, entry_pref="bras_nord", exit_pref="bras_sud")

    assert plan.structure == "carrefour"
    assert plan.entry_zone == "bras_nord"
    assert plan.exit_zone == "bras_sud"
    # Les bras latéraux (est, ouest) doivent être éteints avant la consolidation centrale
    assert set(plan.zones_a_terminer_en_premier) == {"bras_est", "bras_ouest"}
    assert "centre" in plan.zones_a_garder_ouvertes

    txt = report.format_intention(plan, "Carrefour Croix")
    assert "CARREFOUR" in txt
    assert "consolidation" in txt.lower() or "coiffer" in txt.lower()
