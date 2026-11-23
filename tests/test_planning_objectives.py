"""Tests objectifs du planificateur B1.

Ces tests expriment des exigences attendues, independamment des limites
actuelles. Ils peuvent echouer visiblement lorsqu'une fonctionnalite manque :
ils ne sont pas marques ``xfail`` et ne doivent pas etre masques.

Ils sont separes des tests de diagnostic et ne doivent pas etre lances avec la
suite de reference sans autorisation explicite.

Points en attente, volontairement non transformes en tests arbitraires :

- la couverture complete du U et de l'arche : les regles de deplacement ne
  sont pas encore definies et la faisabilite n'est pas demontree ;
- la tolerance exacte de frontiere pour distinguer un trajet de bord d'une
  traversee reelle du vide ;
- la politique exacte du trajet final visible : sa longueur est deja incluse
  dans ``FillPlan.total_length``, mais son eventuelle visibilite n'a pas de
  statut produit decide dans l'interface actuelle.
"""

import math

import pytest

from core.objects import Contour, CORNER
from core.stitches.fill import fill_stitch_segments
from core.stitches.planning import Workspace, plan_fill_path


SPACING = 2.0
CELL = 0.667
RECT_POINTS = [(0.0, 0.0), (20.0, 0.0), (20.0, 20.0), (0.0, 20.0)]
HOLE_POINTS = [(8.0, 8.0), (12.0, 8.0), (12.0, 12.0), (8.0, 12.0)]
U_POINTS = [
    (0.0, 0.0), (20.0, 0.0), (20.0, 20.0), (14.0, 20.0),
    (14.0, 8.0), (6.0, 8.0), (6.0, 20.0), (0.0, 20.0),
]


def _contour(outer, holes=()):
    contour = Contour(closed=True, stitch_type="fill")
    for x, y in outer:
        contour.add_point(x, y, CORNER)
    for hole_points in holes:
        hole = Contour(closed=True, stitch_type="fill")
        for x, y in hole_points:
            hole.add_point(x, y, CORNER)
        contour.add_hole(hole)
    return contour


def _workspace(outer, holes=()):
    return Workspace(
        outer=outer,
        holes=holes,
        spacing=SPACING,
        cell=CELL,
    )


def _rows(contour):
    rows = [
        tuple(tuple(point) for point in segment)
        for segment in fill_stitch_segments(contour, 0.0, SPACING)
    ]
    return [
        row for row in rows
        if math.hypot(row[1][0] - row[0][0],
                      row[1][1] - row[0][1]) > 1e-9
    ]


def _samples_interior(points, step=0.2):
    """Echantillonne strictement entre les extremites de chaque segment.

    Les extremites sont exclues : une rangee peut legalement commencer ou
    finir sur la frontiere d'un trou. Le pas de 0,2 mm est une resolution
    d'observation, pas une tolerance geometrique de frontiere.
    """
    samples = []
    for a, b in zip(points, points[1:]):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        if length <= 0.0:
            continue
        count = max(2, int(math.ceil(length / step)))
        for index in range(1, count):
            t = index / count
            samples.append((
                a[0] + (b[0] - a[0]) * t,
                a[1] + (b[1] - a[1]) * t,
            ))
    return samples


def _strictly_in_hole(workspace, point):
    """Vrai seulement pour un point interieur au trou, pas sur une frontiere.

    ``Workspace.distance_to_border`` calcule la distance geometrique du module.
    Une valeur nulle signifie que le point est sur une arete ; on ne compare
    pas cette distance a une tolerance arbitraire.
    """
    return (
        workspace.in_hole(point)
        and workspace.distance_to_border(point) > 0.0
    )


def _same_point(a, b):
    return (
        abs(a[0] - b[0]) <= 1e-9
        and abs(a[1] - b[1]) <= 1e-9
    )


def _same_segment(a, b):
    return (
        (_same_point(a[0], b[0]) and _same_point(a[1], b[1]))
        or (_same_point(a[0], b[1]) and _same_point(a[1], b[0]))
    )


def _assert_all_generated_rows_present(rows, plan):
    """Verifie que chaque segment genere est cousu exactement une fois.

    Cette verification porte sur les segments generes par
    ``fill_stitch_segments``. Elle ne pretend pas demontrer a elle seule la
    couverture textile complete de la zone entre les rangees.
    """
    assert plan.rows_sewn == len(plan.steps)
    assert len(plan.steps) == len(rows)

    remaining = list(rows)
    for step in plan.steps:
        match = next(
            (row for row in remaining if _same_segment(row, step.row)),
            None,
        )
        assert match is not None
        remaining.remove(match)
    assert not remaining


# ---------------------------------------------------------------------------
# Validation geometrique
# ---------------------------------------------------------------------------


def test_obj_depart_hors_matiere_refuse():
    """Un depart hors matiere doit produire une erreur explicite."""
    workspace = _workspace(RECT_POINTS)
    rows = _rows(_contour(RECT_POINTS))

    with pytest.raises(ValueError):
        plan_fill_path(workspace, rows, (30.0, 10.0), (10.0, 10.0))


def test_obj_arrivee_hors_matiere_refusee():
    """Une arrivee hors matiere doit produire une erreur explicite."""
    workspace = _workspace(RECT_POINTS)
    rows = _rows(_contour(RECT_POINTS))

    with pytest.raises(ValueError):
        plan_fill_path(workspace, rows, (10.0, 10.0), (30.0, 10.0))


def test_obj_depart_dans_trou_refuse():
    """Un depart dans un trou ne doit pas etre accepte silencieusement."""
    holes = [HOLE_POINTS]
    workspace = _workspace(RECT_POINTS, holes)
    rows = _rows(_contour(RECT_POINTS, holes))

    with pytest.raises(ValueError):
        plan_fill_path(workspace, rows, (10.0, 10.0), (1.0, 10.0))


def test_obj_arrivee_dans_trou_refusee_echec_attendu():
    """Une arrivee dans un trou ne doit pas etre acceptee silencieusement.

    Le nom rappelle que ce comportement est actuellement absent : le test
    doit echouer tant que la validation n'existe pas.
    """
    holes = [HOLE_POINTS]
    workspace = _workspace(RECT_POINTS, holes)
    rows = _rows(_contour(RECT_POINTS, holes))

    with pytest.raises(ValueError):
        plan_fill_path(workspace, rows, (1.0, 10.0), (10.0, 10.0))


# ---------------------------------------------------------------------------
# Regle de frontiere de start / end
# ---------------------------------------------------------------------------


DIAMOND_POINTS = [(10.0, 0.0), (20.0, 10.0), (10.0, 20.0), (0.0, 10.0)]
DIAMOND_HOLE = [(10.0, 8.0), (12.0, 10.0), (10.0, 12.0), (8.0, 10.0)]


def _plan_accepte(start, end, holes=()):
    workspace = _workspace(RECT_POINTS, holes)
    rows = _rows(_contour(RECT_POINTS, holes))
    plan = plan_fill_path(workspace, rows, start, end)
    assert plan.start == pytest.approx(start, abs=1e-9)
    assert plan.end == pytest.approx(end, abs=1e-9)
    return plan


def test_obj_interieur_de_matiere_accepte():
    _plan_accepte((1.0, 1.0), (19.0, 19.0))


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ((0.0, 10.0), (10.0, 10.0)),
        ((10.0, 0.0), (10.0, 10.0)),
        ((20.0, 10.0), (10.0, 10.0)),
        ((10.0, 20.0), (10.0, 10.0)),
        ((10.0, 10.0), (0.0, 10.0)),
        ((10.0, 10.0), (10.0, 20.0)),
    ],
)
def test_obj_contour_exterieur_exact_accepte(start, end):
    _plan_accepte(start, end)


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ((0.0, 0.0), (10.0, 10.0)),
        ((20.0, 20.0), (10.0, 10.0)),
        ((10.0, 10.0), (0.0, 20.0)),
    ],
)
def test_obj_sommets_du_contour_exterieur_acceptes(start, end):
    _plan_accepte(start, end)


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ((8.0, 10.0), (1.0, 10.0)),
        ((12.0, 10.0), (1.0, 10.0)),
        ((10.0, 8.0), (1.0, 10.0)),
        ((10.0, 12.0), (1.0, 10.0)),
        ((1.0, 10.0), (8.0, 10.0)),
        ((1.0, 10.0), (10.0, 8.0)),
        ((8.0, 8.0), (1.0, 10.0)),
        ((1.0, 10.0), (12.0, 12.0)),
    ],
)
def test_obj_bord_de_trou_refuse(start, end):
    workspace = _workspace(RECT_POINTS, [HOLE_POINTS])
    rows = _rows(_contour(RECT_POINTS, [HOLE_POINTS]))
    with pytest.raises(ValueError):
        plan_fill_path(workspace, rows, start, end)


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ((float("nan"), 10.0), (10.0, 10.0)),
        ((10.0, 10.0), (float("nan"), 10.0)),
        ((float("inf"), 10.0), (10.0, 10.0)),
        ((10.0, 10.0), (float("-inf"), 10.0)),
    ],
)
def test_obj_coordonnees_non_finies_refusees(start, end):
    workspace = _workspace(RECT_POINTS)
    rows = _rows(_contour(RECT_POINTS))
    with pytest.raises(ValueError):
        plan_fill_path(workspace, rows, start, end)


def test_obj_contour_oblique_exact_accepte():
    workspace = _workspace(DIAMOND_POINTS)
    rows = _rows(_contour(DIAMOND_POINTS))
    plan = plan_fill_path(workspace, rows, (5.0, 5.0), (10.0, 10.0))
    assert plan.start == pytest.approx((5.0, 5.0), abs=1e-9)


def test_obj_bord_de_trou_oblique_refuse():
    workspace = _workspace(DIAMOND_POINTS, [DIAMOND_HOLE])
    rows = _rows(_contour(DIAMOND_POINTS, [DIAMOND_HOLE]))
    with pytest.raises(ValueError):
        plan_fill_path(workspace, rows, (9.0, 9.0), (10.0, 15.0))


# ---------------------------------------------------------------------------
# Continuite et couverture
# ---------------------------------------------------------------------------


def test_obj_plan_complet_couvre_les_segments_generes():
    """Objectif explicite, non garanti par le code actuel.

    La completude du rectangle n'est pas demontree par la lecture statique.
    Ce test peut donc echouer ; il ne doit pas etre masque par ``xfail`` et le
    planificateur ne doit pas etre modifie pour le faire passer artificiellement.

    Le test verifie aussi que l'interieur des rangees reste dans la matiere.
    Il ne remplace pas une preuve de couverture de toute la zone entre les
    rangees : cette preuve depend de la definition de la couverture textile.
    """
    workspace = _workspace(RECT_POINTS)
    rows = _rows(_contour(RECT_POINTS))
    plan = plan_fill_path(workspace, rows, (1.0, 1.0), (1.0, 19.0))

    assert plan.completed, (
        "Objectif non atteint : la completude du rectangle n'est pas garantie "
        "par le code actuel ; ce test est volontairement susceptible d'echouer."
    )
    _assert_all_generated_rows_present(rows, plan)

    for step in plan.steps:
        (x0, y0), (x1, y1) = step.row
        for fraction in (0.1, 0.25, 0.5, 0.75, 0.9):
            x = x0 + (x1 - x0) * fraction
            y = y0 + (y1 - y0) * fraction
            assert workspace.contains((x, y))


def test_obj_plan_incomplet_non_presente_comme_complet():
    """Un plan incomplet doit rester incomplet et expliquer son arret.

    Aucune exigence de 16/16 n'est posee pour le U. Seule la coherence entre
    ``completed``, le nombre de rangees et le message d'echec est verifiee.
    """
    workspace = _workspace(U_POINTS)
    rows = _rows(_contour(U_POINTS))
    plan = plan_fill_path(workspace, rows, (2.0, 19.0), (18.0, 19.0))

    if plan.completed:
        assert plan.rows_sewn == plan.rows_total
        assert plan.failure == ""
    else:
        assert plan.rows_sewn < plan.rows_total
        assert plan.failure


# ---------------------------------------------------------------------------
# Absence de traversee de trou
# ---------------------------------------------------------------------------


def test_obj_aucune_traversee_de_trou_par_echantillonnage():
    """Necessaire mais non suffisant : aucun echantillon ne doit etre dans le trou.

    Les points sont pris strictement a l'interieur des segments : les
    extremites sont exclues et un point dont la distance exacte a une
    frontiere vaut 0,0 n'est pas traite comme une traversee interieure.
    L'echantillonnage reste necessaire mais non suffisant pour prouver
    l'absence de toute intersection geometrique.
    """
    holes = [HOLE_POINTS]
    workspace = _workspace(RECT_POINTS, holes)
    rows = _rows(_contour(RECT_POINTS, holes))
    plan = plan_fill_path(workspace, rows, (1.0, 1.0), (19.0, 19.0))

    geometries = []
    for step in plan.steps:
        geometries.append(step.row)
        geometries.append(step.route.points)
    if plan.arrival_move is not None:
        geometries.append(plan.arrival_move.points)

    for points in geometries:
        for x, y in _samples_interior(points, 0.2):
            assert not _strictly_in_hole(workspace, (x, y))


# ---------------------------------------------------------------------------
# Distances et trajet final
# ---------------------------------------------------------------------------


def test_obj_total_inclut_trajet_final():
    """La longueur totale doit inclure le trajet final mesure.

    Ce test exige d'abord un plan complet et un trajet final present, afin de
    ne pas valider une formule vide lorsque le plan s'arrete avant l'arrivee.
    La visibilite du trajet final reste une decision en attente : ce test ne
    suppose pas qu'il doit etre invisible, mais il verifie qu'il n'est pas
    oublie dans la distance totale.
    """
    workspace = _workspace(RECT_POINTS)
    rows = _rows(_contour(RECT_POINTS))
    plan = plan_fill_path(workspace, rows, (1.0, 1.0), (1.0, 19.0))

    assert plan.completed
    assert plan.arrival_move is not None
    assert plan.total_length == pytest.approx(
        plan.row_length + plan.link_length + plan.arrival_length,
        abs=1e-6,
    )
    expected = math.hypot(
        plan.end[0] - plan.arrival_move.points[0][0],
        plan.end[1] - plan.arrival_move.points[0][1],
    )
    assert plan.arrival_move.length == pytest.approx(expected, abs=1e-6)
