"""Tests G6 pour la Fourche (Bifurcation en Y)."""

from prototypes.g6_intention import intention, report


def test_fourche_intention():
    # Topologie : Tronc (T) relié à un pivot central (P) qui distribue Branche 1 (B1) et Branche 2 (B2)
    graphe_fourche = {
        "zones": {
            "tronc": {"id": "tronc", "classe": "terminale"},
            "coeur": {"id": "coeur", "classe": "transition", "degre": 3},
            "branche_gauche": {"id": "branche_gauche", "classe": "terminale"},
            "branche_droite": {"id": "branche_droite", "classe": "terminale"},
        },
        "adjacences": {
            "tronc": ["coeur"],
            "coeur": ["tronc", "branche_gauche", "branche_droite"],
            "branche_gauche": ["coeur"],
            "branche_droite": ["coeur"],
        },
        "structures": ["Fourche"],
    }

    plan = intention.plan_intention(graphe_fourche, entry_pref="tronc")

    assert plan.structure == "fourche"
    assert plan.entry_zone == "tronc"
    # L'une des deux branches doit être soldée d'abord, et l'autre sert de sortie finale
    assert plan.exit_zone in ("branche_gauche", "branche_droite")
    assert plan.zones_a_terminer_en_premier[0] in ("branche_gauche", "branche_droite")
    assert "coeur" in plan.zones_a_garder_ouvertes

    txt = report.format_intention(plan, "Fourche Y")
    assert "FOURCHE" in txt
    assert "impasse" in txt.lower()
