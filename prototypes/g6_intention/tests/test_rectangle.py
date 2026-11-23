"""Tests G6 pour la Chambre unitaire (Rectangle)."""

import sys
from prototypes.g3_vision import perception
from prototypes.g6_intention import intention, report

RECTANGLE = [(0, 0), (20, 0), (20, 20), (0, 20)]


def test_rectangle_intention():
    perc = perception.perceive(RECTANGLE)
    plan = intention.plan_intention(perc)

    assert plan.structure == "chambre_unitaire"
    assert plan.entry_zone == 1
    assert plan.exit_zone == 1
    assert plan.visit_order == [1]
    assert plan.reprises_autorisees == []
    assert len(plan.etapes) == 1
    assert "chambre" in plan.journal[0].lower()


def test_rectangle_report():
    perc = perception.perceive(RECTANGLE)
    plan = intention.plan_intention(perc)
    txt = report.format_intention(plan, "Rectangle")

    assert "CHAMBRE_UNITAIRE" in txt
    assert "Entrée naturelle   : Zone 1" in txt
    assert "Sortie naturelle   : Zone 1" in txt
    assert "Aucune (interdiction stricte)" in txt


def test_g6_n_importe_aucun_moteur_de_couture():
    import prototypes.g6_intention.intention  # noqa: F401
    import prototypes.g6_intention.report  # noqa: F401

    interdits = [
        "core.stitches.fill",
        "core.stitches.planning",
        "core.stitches.engine",
        "core.stitches.observation",
        "exporters.dst_io",
        "core.simulation",
    ]
    for mod in list(sys.modules):
        for inter in interdits:
            assert inter not in mod, f"Module interdit importé : {mod}"


def test_g6_ne_produit_aucune_couture_ni_rangee():
    perc = perception.perceive(RECTANGLE)
    plan = intention.plan_intention(perc)
    contenu = repr(plan.to_dict()).lower()

    for mot_interdit in ("point", "stitch", "rangee", "rangée", "densite", "densité", "dst", "pes", "aiguille"):
        assert mot_interdit not in contenu, f"Terme de couture interdit trouvé : {mot_interdit}"
