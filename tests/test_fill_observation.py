"""Tests de l'étape B2A : planificateur branché en observateur.

Règle vérifiée ici : l'observation ne change **jamais** la trajectoire produite.
Contrat des mesures : ``docs/B2A_METRICS.md`` (version 1).
"""

import math

import pytest

from core.objects import CORNER, Contour
from core.stitches.fill import fill_stitch_paths, fill_stitch_segments
from core.stitches.observation import (
    LINK_ALERT_THRESHOLDS_MM,
    OBSERVATION_VERSION,
    FillObservation,
    link_stats,
)


# ---------------------------------------------------------------------------
# Formes de référence
# ---------------------------------------------------------------------------


def _contour(points, holes=()):
    contour = Contour(closed=True, stitch_type="fill")
    for x, y in points:
        contour.add_point(x, y, CORNER)
    for hole_points in holes:
        hole = Contour(closed=True)
        for x, y in hole_points:
            hole.add_point(x, y, CORNER)
        contour.add_hole(hole)
    return contour


RECTANGLE = [(0, 0), (20, 0), (20, 20), (0, 20)]
CONCAVE = [(0, 0), (30, 0), (30, 10), (15, 5), (0, 10)]
HOLE_OUTER = [(0, 0), (40, 0), (40, 40), (0, 40)]
HOLE_INNER = [(12, 12), (28, 12), (28, 28), (12, 28)]

ARCH = [
    (0, 0), (0, 55), (30, 95), (90, 125), (170, 138), (214, 141),
    (258, 138), (338, 125), (398, 95), (429, 55), (429, 0),
    (368, 0), (365, 38), (340, 70), (300, 88), (214, 95), (127, 88),
    (89, 70), (64, 38), (61, 0),
]

U_SHAPE = [(0, 0), (20, 0), (20, 20), (14, 20), (14, 8),
           (6, 8), (6, 20), (0, 20)]


def _shapes():
    return [
        ("rectangle", _contour(RECTANGLE)),
        ("concave", _contour(CONCAVE)),
        ("trou", _contour(HOLE_OUTER, holes=[HOLE_INNER])),
        ("arche", _contour(ARCH)),
        ("u", _contour(U_SHAPE)),
    ]


def _shape(nom):
    """Contour neuf pour une forme de reference (jamais partage entre tests)."""
    return dict(_shapes())[nom]


def _expected_rows(contour):
    segments = fill_stitch_segments(contour, contour.fill_angle, contour.fill_spacing)
    return [
        segment for segment in segments
        if math.hypot(segment[1][0] - segment[0][0],
                      segment[1][1] - segment[0][1]) > 1e-9
    ]


# ---------------------------------------------------------------------------
# 1. La sortie ne change pas
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("nom", ["rectangle", "concave", "trou", "arche", "u"])
def test_observation_ne_change_pas_les_points(nom):
    contour = _shape(nom)
    reference = fill_stitch_paths(contour)
    observation = FillObservation()
    observe = fill_stitch_paths(contour, observation=observation)

    assert observe == reference
    assert observation.error == ""


# ---------------------------------------------------------------------------
# 2. Mesures des rangées
# ---------------------------------------------------------------------------


def test_observation_mesure_les_rangees():
    contour = _contour(RECTANGLE)
    observation = FillObservation()

    fill_stitch_paths(contour, observation=observation)

    assert observation.rows_total == len(_expected_rows(contour))
    assert observation.rows_sewn == observation.rows_total
    assert observation.completed is True
    assert observation.failure == ""
    assert observation.plan_seconds >= 0.0
    assert observation.greedy_seconds >= 0.0
    assert observation.total_seconds >= 0.0


# ---------------------------------------------------------------------------
# 3. Parcours incomplet signalé, sans erreur
# ---------------------------------------------------------------------------


def test_observation_signale_un_parcours_incomplet():
    observation = FillObservation()

    fill_stitch_paths(_contour(ARCH), observation=observation)

    assert observation.error == ""
    assert observation.completed is False
    assert observation.failure != ""
    assert 0 < observation.rows_sewn < observation.rows_total


# ---------------------------------------------------------------------------
# 4. Une panne du planificateur ne casse pas le remplissage
# ---------------------------------------------------------------------------


def test_observation_contient_les_erreurs_du_planificateur(monkeypatch):
    import core.stitches.planning as planning

    def panne(*args, **kwargs):
        raise RuntimeError("panne simulee")

    monkeypatch.setattr(planning, "plan_fill_path", panne)

    contour = _contour(RECTANGLE)
    reference = fill_stitch_paths(contour)
    observation = FillObservation()
    observe = fill_stitch_paths(contour, observation=observation)

    assert observe == reference
    assert "panne simulee" in observation.error
    assert observation.plan_seconds >= 0.0


# ---------------------------------------------------------------------------
# 5. Statistiques de liaison, dont le défaut historique de 46 mm
# ---------------------------------------------------------------------------


def test_stats_de_liaison_sont_coherentes():
    longueurs = [0.0, 3.0, 12.0, 25.0, 46.0]
    stats = link_stats(longueurs)

    assert stats.count == 5
    assert stats.total_length == pytest.approx(86.0)
    assert stats.max_length == pytest.approx(46.0)
    assert stats.over_10mm == 3   # 12, 25, 46
    assert stats.over_20mm == 2   # 25, 46
    assert stats.over_40mm == 1   # 46
    assert stats.over_10mm >= stats.over_20mm >= stats.over_40mm

    vide = link_stats([])
    assert vide.count == 0
    assert vide.total_length == 0.0
    assert vide.max_length == 0.0
    assert vide.over_10mm == vide.over_20mm == vide.over_40mm == 0


# ---------------------------------------------------------------------------
# 6. Contrat des mesures stable et documenté
# ---------------------------------------------------------------------------


CHAMPS_FILL_OBSERVATION = {
    "version", "error", "rows_total", "rows_sewn", "completed", "failure",
    "refused_link_count", "refused_links", "visible_link_count",
    "visible_link_total", "turns", "max_turn_outside", "arrival_length",
    "plan", "greedy", "greedy_arrival_length", "plan_seconds",
    "greedy_seconds", "total_seconds",
}

CHAMPS_LINK_STATS = {
    "count", "total_length", "max_length",
    "over_10mm", "over_20mm", "over_40mm",
}


def test_contrat_de_mesures_est_stable():
    assert OBSERVATION_VERSION == 1
    assert LINK_ALERT_THRESHOLDS_MM == (10.0, 20.0, 40.0)

    donnees = FillObservation().to_dict()
    assert set(donnees) == CHAMPS_FILL_OBSERVATION
    assert set(donnees["plan"]) == CHAMPS_LINK_STATS
    assert set(donnees["greedy"]) == CHAMPS_LINK_STATS
    assert donnees["version"] == 1


# ---------------------------------------------------------------------------
# 7. Les mesures de liaison du parcours réel sont calculées
# ---------------------------------------------------------------------------


def test_les_liaisons_greedy_sont_mesurees():
    observation = FillObservation()

    fill_stitch_paths(_contour(HOLE_OUTER, holes=[HOLE_INNER]), observation=observation)

    assert observation.greedy.count == observation.rows_total - 1
    assert observation.greedy.total_length >= 0.0
    assert observation.greedy.max_length >= 0.0
    assert observation.greedy.over_10mm >= observation.greedy.over_20mm
    assert observation.greedy.over_20mm >= observation.greedy.over_40mm
