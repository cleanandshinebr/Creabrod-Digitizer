"""Tests de l'etape B1 : planification du parcours (module isole).

Ces tests n'integrent rien dans le moteur : ils verifient les primitives de
``core/stitches/planning.py``. L'arche est construite avec le generateur de
rangees existant (lecture seule) pour rester proche des motifs reels.
"""

import math

import pytest

from core.objects import Contour, CORNER
from core.stitches.fill import fill_stitch_segments
from core.stitches.planning import (
    FillImpasseError,
    Workspace,
    analyse_rows,
    blocked_rows,
    candidate_blocks_rows,
    classify_link,
    ensure_reachable,
    plan_fill_path,
    route_transition,
)

SEAM_RADIUS = 0.9  # spacing 2.0 * 0.45


# ---------------------------------------------------------------------------
# Outils de test
# ---------------------------------------------------------------------------


def _rectangle(width=20.0, height=20.0, cell=0.667):
    return Workspace(
        outer=[(0, 0), (width, 0), (width, height), (0, height)],
        spacing=2.0,
        cell=cell,
    )


def _horizontal_rows(width=20.0, first=1.0, last=19.0, step=2.0):
    return [((1.0, y), (width - 1.0, y)) for y in
            [first + step * index for index in range(int(round((last - first) / step)) + 1)]]


def _samples(points, step=0.25):
    """Points echantillonnes le long d'une polyligne (x, y, abscisse)."""
    samples = []
    travelled = 0.0
    for a, b in zip(points, points[1:]):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        count = max(1, int(math.ceil(length / step)))
        for index in range(count):
            t = index / count
            samples.append((a[0] + (b[0] - a[0]) * t,
                            a[1] + (b[1] - a[1]) * t,
                            travelled + length * t))
        travelled += length
    samples.append((points[-1][0], points[-1][1], travelled))
    return samples


def _distance_to_segment(point, a, b):
    px, py = point
    ax, ay = a
    bx, by = b
    dx = bx - ax
    dy = by - ay
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-12:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / length_sq
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


ARCH_POINTS = [
    (0, 0), (0, 55), (30, 95), (90, 125), (170, 138), (214, 141),
    (258, 138), (338, 125), (398, 95), (429, 55), (429, 0),
    (368, 0), (365, 38), (340, 70), (300, 88), (214, 95), (127, 88),
    (89, 70), (64, 38), (61, 0),
]

_ARCH_CACHE = {}


def _arch():
    """Arche de reference (429,5 x 141,1 mm) : espace de travail et rangees."""
    if "value" not in _ARCH_CACHE:
        contour = Contour(closed=True, stitch_type="fill")
        for x, y in ARCH_POINTS:
            contour.add_point(x, y, CORNER)
        rows = [tuple(tuple(point) for point in segment)
                for segment in fill_stitch_segments(contour, 0.0, 2.0)]
        rows = [row for row in rows
                if math.hypot(row[1][0] - row[0][0], row[1][1] - row[0][1]) > 1e-9]
        workspace = Workspace(outer=ARCH_POINTS, spacing=2.0, cell=0.667)
        _ARCH_CACHE["value"] = (workspace, rows)
    return _ARCH_CACHE["value"]


def _throat_rows(rows):
    """Rangee du goulot a gauche et a droite (y = 94,33)."""
    gauche = [row for row in rows if abs(row[0][1] - 94.33) < 0.2 and row[0][0] < 210]
    droite = [row for row in rows if abs(row[0][1] - 94.33) < 0.2 and row[0][0] > 210]
    return gauche[0], droite[0]


U_POINTS = [(0, 0), (20, 0), (20, 20), (14, 20), (14, 8),
            (6, 8), (6, 20), (0, 20)]


def _u_shape():
    """Forme en U (20 x 20 mm) : deux branches reliees par le bas."""
    if "u" not in _ARCH_CACHE:
        contour = Contour(closed=True, stitch_type="fill")
        for x, y in U_POINTS:
            contour.add_point(x, y, CORNER)
        rows = [tuple(tuple(point) for point in segment)
                for segment in fill_stitch_segments(contour, 0.0, 2.0)]
        rows = [row for row in rows
                if math.hypot(row[1][0] - row[0][0], row[1][1] - row[0][1]) > 1e-9]
        workspace = Workspace(outer=U_POINTS, spacing=2.0, cell=0.667)
        _ARCH_CACHE["u"] = (workspace, rows)
    return _ARCH_CACHE["u"]


# ---------------------------------------------------------------------------
# Matiere, trous, validation
# ---------------------------------------------------------------------------


def test_matiere_et_trou_sont_distingues():
    workspace = Workspace(
        outer=[(0, 0), (30, 0), (30, 30), (0, 30)],
        holes=[[(10, 10), (20, 10), (20, 20), (10, 20)]],
        spacing=2.0,
        cell=0.667,
    )
    assert workspace.contains((5.0, 15.0))
    assert not workspace.contains((15.0, 15.0))  # dans le trou
    assert workspace.in_hole((15.0, 15.0))
    assert not workspace.contains((35.0, 15.0))  # hors matiere


def test_parametres_invalides_refuses():
    with pytest.raises(ValueError):
        Workspace(outer=[(0, 0), (10, 0), (10, 10)], spacing=0.0)
    with pytest.raises(ValueError):
        Workspace(outer=[(0, 0), (10, 0), (10, 10)], spacing=2.0, max_link=0.0)
    with pytest.raises(ValueError):
        Workspace(outer=[(0, 0), (0, 0)], spacing=2.0)


# ---------------------------------------------------------------------------
# Accessibilite des rangees
# ---------------------------------------------------------------------------


def test_rangees_restent_directes_dans_un_rectangle():
    workspace = _rectangle()
    rows = _horizontal_rows()
    states = analyse_rows(workspace, [], rows, (1.0, 1.0))
    assert [state.status for state in states] == ["direct"] * len(rows)


def test_une_rangee_entouree_est_bloquee():
    """Poche fermee : la rangee ciblee n'est plus joignable."""
    workspace = _rectangle()
    target = ((9.0, 10.0), (11.0, 10.0))
    murs = [
        ((8.0, 8.0), (12.0, 8.0)),
        ((12.0, 8.0), (12.0, 12.0)),
        ((12.0, 12.0), (8.0, 12.0)),
        ((8.0, 12.0), (8.0, 8.0)),
    ]
    ouverte = murs[1:]
    assert analyse_rows(workspace, ouverte, [target], (10.0, 5.0))[0].status == "direct"
    assert analyse_rows(workspace, murs, [target], (10.0, 5.0))[0].status == "blocked"


def test_un_candidat_qui_ferme_la_poche_bloque_la_rangee():
    workspace = _rectangle()
    target = ((9.0, 10.0), (11.0, 10.0))
    murs = [
        ((8.0, 8.0), (12.0, 8.0)),
        ((12.0, 8.0), (12.0, 12.0)),
        ((12.0, 12.0), (8.0, 12.0)),
        ((8.0, 12.0), (8.0, 8.0)),
    ]
    ouverte = murs[1:]
    bloques = candidate_blocks_rows(workspace, ouverte, murs[0], [target], (10.0, 5.0))
    assert target in bloques


def test_une_liaison_courte_dans_le_vide_n_est_pas_bloquee():
    """Forme en U : l'autre branche reste joignable, mais par le vide."""
    workspace = Workspace(
        outer=[(0, 0), (20, 0), (20, 20), (14, 20), (14, 8), (6, 8), (6, 20), (0, 20)],
        spacing=2.0,
        cell=0.667,
    )
    gauche = [((0.5, y), (5.5, y)) for y in range(9, 20, 2)]
    droite = [((14.5, y), (19.5, y)) for y in range(9, 20, 2)]
    states = analyse_rows(workspace, gauche, droite, (5.5, 19.0))
    assert all(state.status == "via_void" for state in states)
    assert all(state.distance <= workspace.max_link for state in states)


# ---------------------------------------------------------------------------
# Liaisons : qualite, securite, continuite
# ---------------------------------------------------------------------------


def test_la_liaison_ne_traverse_pas_une_couture():
    workspace = _rectangle()
    sewn = [((6.0, 10.0), (14.0, 10.0))]
    route = route_transition(workspace, sewn, (10.0, 5.0), (10.0, 15.0))
    assert route is not None
    assert route.length > 10.0  # detour obligatoire autour de la couture
    samples = _samples(route.points)
    total = samples[-1][2]
    for x, y, arc in samples:
        if arc <= 1.5 or arc >= total - 1.5:
            continue
        assert _distance_to_segment((x, y), *sewn[0]) >= SEAM_RADIUS - 1e-3


def test_continuite_et_extremites_de_la_liaison():
    workspace = _rectangle()
    cases = [
        ((1.0, 1.0), (19.0, 19.0)),
        ((10.0, 5.0), (10.0, 15.0)),
    ]
    routes = [
        route_transition(workspace, [], (1.0, 1.0), (19.0, 19.0)),
        route_transition(workspace, [((6.0, 10.0), (14.0, 10.0))],
                         (10.0, 5.0), (10.0, 15.0)),
    ]
    for (start, goal), route in zip(cases, routes):
        assert route is not None
        assert route.points[0] == pytest.approx(start)
        assert route.points[-1] == pytest.approx(goal)
        steps = [math.hypot(b[0] - a[0], b[1] - a[1])
                 for a, b in zip(route.points, route.points[1:])]
        assert steps
        assert max(steps) <= 2.5 + 1e-9
        assert sum(steps) == pytest.approx(route.length, abs=1e-6)


def test_aucune_solution_continue_retourne_none():
    workspace = _rectangle()
    murs = [
        ((8.0, 8.0), (12.0, 8.0)),
        ((12.0, 8.0), (12.0, 12.0)),
        ((12.0, 12.0), (8.0, 12.0)),
        ((8.0, 12.0), (8.0, 8.0)),
    ]
    assert route_transition(workspace, murs, (10.0, 5.0), (10.0, 10.0)) is None


def test_un_trou_n_est_jamais_traverse():
    workspace = Workspace(
        outer=[(0, 0), (30, 0), (30, 30), (0, 30)],
        holes=[[(10, 10), (20, 10), (20, 20), (10, 20)]],
        spacing=2.0,
        cell=0.667,
    )
    route = route_transition(workspace, [], (5.0, 15.0), (25.0, 15.0))
    assert route is not None
    assert not route.crosses_void
    for x, y, _ in _samples(route.points, 0.2):
        assert not workspace.in_hole((x, y))


def test_passage_etroit_est_signale_et_refuse_par_defaut():
    """Bande de 3 mm : tout trajet longe le bord, donc liaison visible."""
    workspace = Workspace(
        outer=[(0, 0), (30, 0), (30, 3), (0, 3)],
        spacing=2.0,
        cell=0.5,
    )
    route = route_transition(workspace, [], (2.0, 1.5), (28.0, 1.5))
    assert route is not None
    assert route.rides_border
    assert route.visible
    assert not route.accepted
    assert route_transition(workspace, [], (2.0, 1.5), (28.0, 1.5),
                            allow_visible=True).accepted


def test_forme_concave_liaison_propre_acceptee():
    workspace = Workspace(
        outer=[(0, 0), (20, 0), (20, 6), (6, 6), (6, 20), (0, 20)],
        spacing=2.0,
        cell=0.667,
    )
    route = route_transition(workspace, [], (3.0, 3.0), (3.0, 15.0))
    assert route is not None
    assert not route.visible
    assert route.accepted


def test_liaison_dans_le_vide_signalee_puis_acceptee_si_autorisee():
    """U : traverser le creux est visible, jamais accepte automatiquement."""
    workspace = Workspace(
        outer=[(0, 0), (20, 0), (20, 20), (14, 20), (14, 8), (6, 8), (6, 20), (0, 20)],
        spacing=2.0,
        cell=0.667,
    )
    crosses_void, _, _, visible = classify_link(workspace, [(3.0, 15.0), (17.0, 15.0)])
    assert crosses_void and visible

    gauche = [((0.5, y), (5.5, y)) for y in range(9, 20, 2)]
    refuse = route_transition(workspace, gauche, (5.5, 19.0), (14.5, 19.0))
    assert refuse is not None and refuse.visible and not refuse.accepted
    accepte = route_transition(workspace, gauche, (5.5, 19.0), (14.5, 19.0),
                               allow_visible=True)
    assert accepte is not None and accepte.accepted


# ---------------------------------------------------------------------------
# Arche : cas mesure
# ---------------------------------------------------------------------------


def test_l_arche_goulot_bloque_dans_l_etat_mesure():
    """Etat mesure avec la reserve d'arrivee (rayon 0,30 x diagonale = 135 mm) :
    a l'aiguille (229,140), la rangee du goulot droit n'est plus joignable.
    C'est l'impasse de 46 mm constatee a l'etape 72."""
    workspace, rows = _arch()
    _, droite = _throat_rows(rows)
    arrivee = (395.0, 5.0)
    rayon = 0.30 * math.hypot(429.0, 141.0)  # reserve actuelle du moteur
    reserve = {row for row in rows
               if math.hypot((row[0][0] + row[1][0]) / 2 - arrivee[0],
                             (row[0][1] + row[1][1]) / 2 - arrivee[1]) <= rayon}
    assert len(reserve) == 48  # valeur mesuree sur l'arche de reference
    sewn = [row for row in rows if row not in reserve and row is not droite]
    states = analyse_rows(workspace, sewn, [droite], (229.0, 140.0))
    assert states[0].status == "blocked"
    assert route_transition(workspace, sewn, (229.0, 140.0), droite[0]) is None


def test_l_arche_dernier_trajet_sans_reserve_est_bloque():
    """Sans reserve, le dernier trajet mesure (429,1) -> (391,98), 104,3 mm a
    travers 48 rangees, n'a aucune liaison acceptable."""
    workspace, rows = _arch()
    cible = min(rows, key=lambda row: min(
        math.hypot(row[0][0] - 391.0, row[0][1] - 98.0),
        math.hypot(row[1][0] - 391.0, row[1][1] - 98.0)))
    sewn = [row for row in rows if row is not cible]
    states = analyse_rows(workspace, sewn, [cible], (429.0, 1.0))
    assert states[0].status == "blocked"
    assert route_transition(workspace, sewn, (429.0, 1.0), cible[0]) is None


def test_l_arche_liaison_du_goulot_est_visible_et_refusee():
    """Le raccord de 16,5 mm entre les deux levres du goulot est une liaison
    visible : refusee par defaut, acceptee seulement si on l'autorise."""
    workspace, rows = _arch()
    gauche, droite = _throat_rows(rows)
    dome = [row for row in rows if row[0][1] > 96.5]
    sewn = dome + [gauche]
    proche = droite[1]  # levre droite la plus proche de la levre gauche

    refuse = route_transition(workspace, sewn, gauche[1], proche)
    assert refuse is not None
    assert refuse.visible
    assert not refuse.accepted

    accepte = route_transition(workspace, sewn, gauche[1], proche, allow_visible=True)
    assert accepte is not None
    assert accepte.accepted
    assert accepte.length < workspace.max_link


# ---------------------------------------------------------------------------
# Erreur explicite
# ---------------------------------------------------------------------------


def test_impasse_reelle_leve_une_erreur_explicite():
    workspace = _rectangle()
    target = ((9.0, 10.0), (11.0, 10.0))
    murs = [
        ((8.0, 8.0), (12.0, 8.0)),
        ((12.0, 8.0), (12.0, 12.0)),
        ((12.0, 12.0), (8.0, 12.0)),
        ((8.0, 12.0), (8.0, 8.0)),
    ]
    with pytest.raises(FillImpasseError) as caught:
        ensure_reachable(workspace, murs, [target], (10.0, 5.0))
    assert target in caught.value.blocked
    assert caught.value.position == (10.0, 5.0)
    assert caught.value.states


def test_l_arrivee_n_est_plus_joignable_proprement_si_cousue_trop_tot():
    """La rangee d'arrivee ne doit pas etre cousue avant la fin : sinon le
    retour se fait par une liaison visible (ou n'existe pas)."""
    workspace = _rectangle()
    rows = _horizontal_rows()
    arrivee = rows[-1]
    sewn = rows[:-1]
    position = (19.0, sewn[-1][0][1])
    route = route_transition(workspace, sewn, position, arrivee[0])
    assert route is None or not route.accepted


# ---------------------------------------------------------------------------
# Parcours complet : arche et forme en U
# ---------------------------------------------------------------------------

_PLAN_CACHE = {}


def _arch_plan(allow_visible):
    key = ("arch", bool(allow_visible))
    if key not in _PLAN_CACHE:
        workspace, rows = _arch()
        _PLAN_CACHE[key] = plan_fill_path(
            workspace, rows, (30.0, 5.0), (395.0, 5.0),
            allow_visible=allow_visible)
    return _PLAN_CACHE[key]


def _u_plan(allow_visible):
    key = ("u", bool(allow_visible))
    if key not in _PLAN_CACHE:
        workspace, rows = _u_shape()
        _PLAN_CACHE[key] = plan_fill_path(
            workspace, rows, (2.0, 19.0), (18.0, 19.0),
            allow_visible=allow_visible)
    return _PLAN_CACHE[key]


def _same_row(a, b):
    return {a[0], a[1]} == {b[0], b[1]}


def _check_continuity(plan):
    """Chaque etape reprend exactement la ou l'aiguille s'est arretee."""
    position = plan.start
    for step in plan.steps:
        start = step.route.points[0]
        assert math.hypot(start[0] - position[0],
                          start[1] - position[1]) <= 1e-9
        assert step.route.length == pytest.approx(sum(step.route.distances()))
        position = step.end
    if plan.steps:
        assert position == plan.steps[-1].end


def _check_no_sewn_crossing(plan):
    """Aucune liaison ne traverse une rangee deja cousue.

    La rangee precedente est exclue : la liaison part de son extremite et la
    longe sur quelques millimetres (demi-tour). Toutes les autres rangees
    cousues sont controlees avec le rayon de couture.
    """
    sewn = []
    for step in plan.steps:
        previous = sewn[-1] if sewn else None
        total = step.route.length
        for x, y, arc in _samples(step.route.points, 0.2):
            if arc <= 1.5 or arc >= total - 1.5:
                continue
            for row in sewn:
                if previous is not None and row is previous:
                    continue
                assert _distance_to_segment((x, y), row[0], row[1]) >= SEAM_RADIUS - 0.05
        sewn.append(step.row)


def _arrival_sewn(plan):
    if plan.arrival_row is None:
        return False
    return any(_same_row(step.row, plan.arrival_row) for step in plan.steps)


def test_parcours_arche_refuse_les_liaisons_visibles_et_s_arrete():
    """Arche : le balayage part du cote court et s'arrete net a l'echancrure,
    ou la seule poursuite est une liaison visible (25,2 mm)."""
    plan = _arch_plan(False)
    assert plan.rows_total == 119
    assert plan.rows_sewn == 45
    assert not plan.completed
    assert plan.failure and "liaison visible" in plan.failure
    assert not plan.visible_steps
    assert plan.refused_visible
    lengths = sorted(round(refusal.route.length, 1)
                     for refusal in plan.refused_visible)
    assert lengths == [25.2, 49.9]
    assert plan.arrival_move is None
    _check_continuity(plan)
    _check_no_sewn_crossing(plan)
    assert not _arrival_sewn(plan)


def test_parcours_arche_avec_visibles_acceptees_reste_bloque_explicitement():
    """Arche : les deux liaisons visibles de l'echancrure sont acceptees, mais
    le couvercle et la branche droite restent inaccessibles : arret explicite,
    jamais de saut silencieux vers l'arrivee."""
    plan = _arch_plan(True)
    assert plan.rows_sewn == 49
    assert not plan.completed
    assert plan.failure and "inaccessibles" in plan.failure
    assert len(plan.visible_steps) == 2
    assert all(round(step.route.length, 1) == 25.2
               for step in plan.visible_steps)
    assert not plan.refused_visible
    assert plan.arrival_move is None
    _check_continuity(plan)
    _check_no_sewn_crossing(plan)
    assert not _arrival_sewn(plan)


def test_parcours_u_refuse_la_liaison_visible_entre_branches():
    """U : le remplissage descend la branche gauche puis le bas ; la branche
    droite n'est joignable qu'en traversant le creux (liaison visible), donc
    le parcours s'arrete explicitement."""
    plan = _u_plan(False)
    assert plan.rows_total == 16
    assert plan.rows_sewn == 9
    assert not plan.completed
    assert plan.failure and "liaison visible" in plan.failure
    assert not plan.visible_steps
    assert plan.refused_visible
    assert plan.arrival_move is None
    _check_continuity(plan)
    _check_no_sewn_crossing(plan)
    assert not _arrival_sewn(plan)


def test_parcours_u_avec_visibles_autorisees_reste_bloque_explicitement():
    """U : meme en autorisant les liaisons visibles, les rangees du bas
    deviendraient inaccessibles : arret explicite, pas de saut silencieux."""
    plan = _u_plan(True)
    assert plan.rows_sewn == 9
    assert not plan.completed
    assert plan.failure and "inaccessibles" in plan.failure
    assert not plan.visible_steps
    assert not plan.refused_visible
    assert plan.arrival_move is None
    _check_continuity(plan)
    _check_no_sewn_crossing(plan)
    assert not _arrival_sewn(plan)
