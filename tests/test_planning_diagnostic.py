"""Tests de diagnostic du planificateur B1.

Ces tests documentent le comportement observe actuel. Ils ne constituent pas
des criteres d'acceptation du produit : un resultat partiel y est consigne
comme partiel, jamais comme un remplissage complet.

Ils sont volontairement separes de ``test_planning_objectives.py``. Les formes
en U et en arche sont examinees ici pour leur comportement actuel, mais aucune
couverture complete n'y est exigee.
"""

import math

import pytest

from core.objects import Contour, CORNER
from core.stitches.fill import fill_stitch_paths, fill_stitch_segments
from core.stitches.planning import (
    Workspace,
    classify_link,
    plan_fill_path,
    route_transition,
)


SPACING = 2.0
CELL = 0.667

RECT_POINTS = [(0.0, 0.0), (20.0, 0.0), (20.0, 20.0), (0.0, 20.0)]
U_POINTS = [
    (0.0, 0.0), (20.0, 0.0), (20.0, 20.0), (14.0, 20.0),
    (14.0, 8.0), (6.0, 8.0), (6.0, 20.0), (0.0, 20.0),
]
ARCH_POINTS = [
    (0, 0), (0, 55), (30, 95), (90, 125), (170, 138), (214, 141),
    (258, 138), (338, 125), (398, 95), (429, 55), (429, 0),
    (368, 0), (365, 38), (340, 70), (300, 88), (214, 95), (127, 88),
    (89, 70), (64, 38), (61, 0),
]
HOLE_POINTS = [(8.0, 8.0), (12.0, 8.0), (12.0, 12.0), (8.0, 12.0)]


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


def _samples(points, step=0.2):
    """Echantillonne une polyligne, extremites comprises.

    L'echantillonnage est une observation, pas une preuve d'absence totale
    d'intersection. La limite est documentee dans les tests qui l'utilisent.
    """
    samples = []
    for a, b in zip(points, points[1:]):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        if length <= 1e-9:
            continue
        count = max(1, int(math.ceil(length / step)))
        for index in range(count + 1):
            t = index / count
            samples.append((
                a[0] + (b[0] - a[0]) * t,
                a[1] + (b[1] - a[1]) * t,
            ))
    return samples


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


def _assert_plan_invariants(plan):
    """Invariants reels de FillPlan, sans figer un nombre de rangees."""
    assert plan.rows_sewn == len(plan.steps)
    assert plan.total_length == pytest.approx(
        plan.row_length + plan.link_length + plan.arrival_length,
        abs=1e-6,
    )
    if plan.completed:
        assert plan.rows_sewn == plan.rows_total
        assert plan.arrival_move is not None
        assert plan.failure == ""
    else:
        assert plan.arrival_move is None
        assert plan.failure


def _print_plan(label, plan):
    """Trace lisible pour une execution de diagnostic avec ``pytest -s``."""
    print(f"\n[DIAG] {label}")
    print(
        f"  rows={plan.rows_sewn}/{plan.rows_total} "
        f"completed={plan.completed} failure={plan.failure!r}"
    )
    if plan.steps:
        last = plan.steps[-1]
        print(f"  last_step={last.index + 1} row={last.row} end={last.end}")
    if plan.arrival_move is None:
        print("  arrival_move=None")
    else:
        move = plan.arrival_move
        print(
            f"  arrival_move={move.length:.3f} mm visible={move.visible} "
            f"flags=({move.crosses_void},{move.rides_border},{move.rides_seam})"
        )
    visible = ", ".join(
        f"etape {step.index + 1} ({step.route.length:.2f} mm)"
        for step in plan.visible_steps
    )
    print(f"  visible_steps={visible or 'aucune'}")
    refused = sorted(
        round(refusal.route.length, 2)
        for refusal in plan.refused_visible
        if refusal.route is not None
    )
    print(f"  refused_visible={refused}")


def test_diag_rectangle_rows_are_structural():
    """Le rectangle de reference produit dix rangees horizontales."""
    rows = _rows(_contour(RECT_POINTS))

    assert len(rows) == 10
    ys = sorted({round(row[0][1], 9) for row in rows})
    assert ys == pytest.approx(
        [1.0, 3.0, 5.0, 7.0, 9.0, 11.0, 13.0, 15.0, 17.0, 19.0],
        abs=1e-9,
    )
    for row in rows:
        assert row[0][1] == pytest.approx(row[1][1], abs=1e-9)
        xs = sorted([round(row[0][0], 9), round(row[1][0], 9)])
        assert xs == pytest.approx([0.0, 20.0], abs=1e-9)


@pytest.mark.parametrize(
    ("start", "end", "preserve_arrival"),
    [
        ((1.0, 1.0), (19.0, 19.0), True),
        ((1.0, 1.0), (19.0, 1.0), True),
        ((1.0, 1.0), (1.0, 19.0), True),
        ((1.0, 3.0), (19.0, 1.0), True),
        ((1.0, 1.0), (19.0, 19.0), False),
        ((1.0, 1.0), (19.0, 1.0), False),
        ((1.0, 1.0), (1.0, 19.0), False),
        ((1.0, 3.0), (19.0, 1.0), False),
    ],
)
def test_diag_rectangle_plan_observation(start, end, preserve_arrival):
    """Consigne le resultat courant sans figer un nombre de rangees cousues.

    Les valeurs exactes de ce cas ne sont pas affirmees avant une execution
    autorisee ; les tests ne doivent pas transformer un arret en succes.
    """
    workspace = _workspace(RECT_POINTS)
    rows = _rows(_contour(RECT_POINTS))
    plan = plan_fill_path(
        workspace, rows, start, end,
        preserve_arrival=preserve_arrival,
    )

    _assert_plan_invariants(plan)
    assert plan.start == pytest.approx(start, abs=1e-9)
    assert plan.end == pytest.approx(end, abs=1e-9)
    _print_plan(
        f"rectangle {start}->{end} preserve={preserve_arrival}",
        plan,
    )


def test_diag_arrival_move_is_reported_separately():
    """Le trajet final est un objet separe des etapes de rangees."""
    workspace = _workspace(RECT_POINTS)
    rows = _rows(_contour(RECT_POINTS))
    plan = plan_fill_path(workspace, rows, (1.0, 1.0), (19.0, 19.0))

    if plan.arrival_move is None:
        pytest.skip("le plan courant est incomplet : aucun trajet final")
    assert plan.steps
    assert all(step.route is not plan.arrival_move for step in plan.steps)
    expected = math.hypot(
        plan.end[0] - plan.steps[-1].end[0],
        plan.end[1] - plan.steps[-1].end[1],
    )
    assert plan.arrival_move.length == pytest.approx(expected, abs=1e-6)
    _print_plan("trajet final rectangle", plan)


def test_diag_u_shape_observation():
    """Documente l'etat courant du U sans exiger 16/16."""
    workspace = _workspace(U_POINTS)
    rows = _rows(_contour(U_POINTS))
    assert len(rows) == 16

    for allow_visible in (False, True):
        plan = plan_fill_path(
            workspace, rows, (2.0, 19.0), (18.0, 19.0),
            allow_visible=allow_visible,
        )
        _assert_plan_invariants(plan)
        assert plan.rows_total == 16
        _print_plan(f"U allow_visible={allow_visible}", plan)


def test_diag_arch_shape_observation():
    """Documente l'etat courant de l'arche sans exiger 119/119."""
    workspace = _workspace(ARCH_POINTS)
    rows = _rows(_contour(ARCH_POINTS))
    assert len(rows) == 119

    for allow_visible in (False, True):
        plan = plan_fill_path(
            workspace, rows, (30.0, 5.0), (395.0, 5.0),
            allow_visible=allow_visible,
        )
        _assert_plan_invariants(plan)
        assert plan.rows_total == 119
        _print_plan(f"arche allow_visible={allow_visible}", plan)


def test_diag_hole_rows_are_structural():
    """Le trou central coupe deux rangees en deux segments chacune."""
    rows = _rows(_contour(RECT_POINTS, [HOLE_POINTS]))

    assert len(rows) == 12
    counts_by_y = {}
    for row in rows:
        y = round(row[0][1], 9)
        counts_by_y[y] = counts_by_y.get(y, 0) + 1
    assert counts_by_y[9.0] == 2
    assert counts_by_y[11.0] == 2
    assert sum(counts_by_y.values()) == 12


def test_diag_hole_plan_observation():
    """Consigne le plan avec trou, sans presenter un plan partiel comme complet."""
    holes = [HOLE_POINTS]
    workspace = _workspace(RECT_POINTS, holes)
    rows = _rows(_contour(RECT_POINTS, holes))

    for start, end in (((1.0, 1.0), (19.0, 19.0)),
                       ((1.0, 1.0), (1.0, 19.0))):
        plan = plan_fill_path(workspace, rows, start, end)
        _assert_plan_invariants(plan)
        _print_plan(f"trou {start}->{end}", plan)


def test_diag_hole_no_sampled_stitch_inside_hole():
    """Verification par echantillonnage ; elle ne prouve pas l'absence totale.

    Les points sont pris strictement a l'interieur des segments : les
    extremites sont exclues et un point dont la distance exacte a une
    frontiere vaut 0,0 n'est pas traite comme une traversee interieure.
    Aucune tolerance geometrique arbitraire n'est ajoutee.
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


@pytest.mark.parametrize(
    ("start", "end", "holes"),
    [
        ((30.0, 10.0), (10.0, 10.0), ()),
        ((10.0, 10.0), (1.0, 10.0), (HOLE_POINTS,)),
    ],
)
def test_diag_plan_invalid_points_are_refused(start, end, holes):
    """Constat apres validation : plan_fill_path refuse les points invalides."""
    workspace = _workspace(RECT_POINTS, holes)
    rows = _rows(_contour(RECT_POINTS, holes))

    with pytest.raises(ValueError):
        plan_fill_path(workspace, rows, start, end)


@pytest.mark.parametrize(
    ("start", "holes"),
    [
        ((30.0, 10.0), ()),
        ((10.0, 10.0), (HOLE_POINTS,)),
    ],
)
def test_diag_engine_accepts_invalid_start(start, holes):
    """Constat actuel du moteur historique : le premier point est le point choisi."""
    contour = _contour(RECT_POINTS, holes)
    contour.start_point = start
    contour.end_point = (10.0, 10.0)

    path = fill_stitch_paths(contour, 0.0, SPACING, 2.5)[0]

    assert path[0] == pytest.approx(start, abs=1e-9)


def test_diag_route_from_hole_center():
    """Constat actuel : une liaison depuis le trou est acceptee si visible autorisee."""
    holes = [HOLE_POINTS]
    workspace = _workspace(RECT_POINTS, holes)

    route = route_transition(
        workspace, [], (10.0, 10.0), (1.0, 10.0),
        allow_visible=True,
    )

    if route is None:
        print(
            "\n[DIAG] route depuis le centre du trou : "
            "aucune route A* trouvee (absence de route, pas une assertion)"
        )
        pytest.skip("diagnostic : aucune route A* depuis le centre du trou")

    assert route.accepted
    assert any(workspace.in_hole((x, y))
               for x, y in _samples(route.points, 0.2))


def test_diag_classification_border_and_void():
    """Compare une traversee du creux du U et une liaison le long d'un bord.

    La classification exacte du bord reste a decider : ``crosses_void`` est
    seulement consigne, pas transforme ici en exigence.
    """
    u_workspace = _workspace(U_POINTS)
    void_flags = classify_link(u_workspace, [(3.0, 15.0), (17.0, 15.0)])
    assert void_flags[0] is True
    assert void_flags[3] is True

    rect_workspace = _workspace(RECT_POINTS)
    border_flags = classify_link(
        rect_workspace,
        [(1.0, 0.5), (19.0, 0.5)],
    )
    assert len(border_flags) == 4
    assert border_flags[1] is True
    assert border_flags[3] is True

    print(f"\n[DIAG] U void flags={void_flags}")
    print(f"[DIAG] border flags={border_flags}")
