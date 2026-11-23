"""Tests G6 pour le Corridor (Forme en U)."""

from prototypes.g3_vision import perception
from prototypes.g6_intention import intention, report

U_SHAPE = [(0, 0), (20, 0), (20, 20), (14, 20), (14, 8),
           (6, 8), (6, 20), (0, 20)]


def test_u_intention_circulation():
    perc = perception.perceive(U_SHAPE)
    plan = intention.plan_intention(perc)

    assert plan.structure == "corridor"
    # Dans le U de G3, les zones 2 et 3 sont les jambes terminales, la zone 1 est la traverse de transit
    assert set([plan.entry_zone, plan.exit_zone]) == {2, 3}
    assert plan.visit_order in ([2, 1, 3], [3, 1, 2])
    assert plan.zones_a_terminer_en_premier == [plan.entry_zone]
    assert plan.zones_a_garder_ouvertes == [1, plan.exit_zone] or plan.zones_a_garder_ouvertes == [plan.visit_order[1], plan.exit_zone]


def test_u_report():
    perc = perception.perceive(U_SHAPE)
    plan = intention.plan_intention(perc)
    txt = report.format_intention(plan, "U")

    assert "CORRIDOR" in txt
    assert "zones à terminer d'abord" in txt.lower()
    assert "Reprise axiale sous-jacente" in txt
