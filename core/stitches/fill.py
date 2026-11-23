"""Génération d'un remplissage simple par lignes parallèles."""

import heapq
import math
import time

from core.objects import FILL_SPACING_MAX, FILL_SPACING_MIN
from core.stitches.observation import FillObservation, link_stats


EPSILON = 1e-9


def _clean_path(path):
    result = []
    for point in path:
        if not result or math.hypot(point[0] - result[-1][0], point[1] - result[-1][1]) > EPSILON:
            result.append(point)
    return result


def _polyline_length(points):
    """Longueur cumulée d'une polyligne (mm). Utilisé par l'observation B2A."""
    return sum(
        math.hypot(b[0] - a[0], b[1] - a[1])
        for a, b in zip(points, points[1:])
    )


def _rotate(point, center, angle):
    x, y = point
    cx, cy = center
    cos_angle = math.cos(angle)
    sin_angle = math.sin(angle)
    dx, dy = x - cx, y - cy
    return (
        cx + dx * cos_angle - dy * sin_angle,
        cy + dx * sin_angle + dy * cos_angle,
    )


def _scanline_intersections(path, y):
    intersections = []
    for (x1, y1), (x2, y2) in zip(path, path[1:]):
        if abs(y2 - y1) <= EPSILON:
            continue
        if not ((y1 <= y < y2) or (y2 <= y < y1)):
            continue
        fraction = (y - y1) / (y2 - y1)
        intersections.append(x1 + (x2 - x1) * fraction)
    return sorted(intersections)


def _subtract_range(intervals, cut_start, cut_end):
    updated = []
    for start_x, end_x in intervals:
        if cut_end <= start_x or cut_start >= end_x:
            updated.append((start_x, end_x))
            continue
        if start_x < cut_start:
            left_end = min(cut_start - EPSILON, end_x)
            if left_end - start_x > EPSILON:
                updated.append((start_x, left_end))
        if cut_end < end_x:
            right_start = max(cut_end + EPSILON, start_x)
            if end_x - right_start > EPSILON:
                updated.append((right_start, end_x))
    return updated


def _fill_segment_pairs_for_row(path, holes, y):
    intersections = _scanline_intersections(path, y)
    if len(intersections) < 2:
        return []

    pairs = []
    outer_ranges = []
    for index in range(0, len(intersections) - 1, 2):
        start_x = intersections[index]
        end_x = intersections[index + 1]
        midpoint = ((start_x + end_x) / 2.0, y)
        if _inside_polygon(midpoint, path):
            outer_ranges.append((start_x, end_x))

    for hole in holes:
        hole_intersections = _scanline_intersections(hole, y)
        for index in range(0, len(hole_intersections) - 1, 2):
            hole_start = hole_intersections[index]
            hole_end = hole_intersections[index + 1]
            if hole_start >= hole_end:
                continue
            outer_ranges = _subtract_range(outer_ranges, hole_start, hole_end)

    for start_x, end_x in outer_ranges:
        if end_x - start_x <= EPSILON:
            continue
        midpoint = ((start_x + end_x) / 2.0, y)
        if _inside_polygon(midpoint, path):
            pairs.append((start_x, end_x))
    return pairs


def _path_for_contour(contour):
    path = _clean_path(contour.flatten())
    if len(path) < 3:
        raise ValueError("Le remplissage nécessite au moins trois points distincts.")
    if math.hypot(path[0][0] - path[-1][0], path[0][1] - path[-1][1]) > EPSILON:
        path.append(path[0])
    return path


def _inside_polygon(point, polygon):
    x, y = point
    inside = False
    previous = polygon[-1]
    for current in polygon:
        if (current[1] > y) != (previous[1] > y):
            intersection_x = (
                (previous[0] - current[0]) * (y - current[1]) / (previous[1] - current[1]) + current[0]
            )
            if x < intersection_x:
                inside = not inside
        previous = current
    return inside


def _inside_region(point, outer, holes):
    """Vrai si le point est dans la forme (extérieur, hors des trous)."""
    if not _inside_polygon(point, outer):
        return False
    return not any(_inside_polygon(point, hole) for hole in holes)


def _segment_inside_region(a, b, outer, holes):
    """Vrai si tout le segment [a, b] reste dans la forme (hors trous).

    Les extrémités sont tolérées sur le bord (ce sont des extrémités de
    rangées) ; seuls les points entre a et b sont échantillonnés."""
    distance = math.hypot(b[0] - a[0], b[1] - a[1])
    if distance <= EPSILON:
        return True
    steps = max(1, math.ceil(distance / 1.0))
    for index in range(1, steps):
        fraction = index / steps
        point = (a[0] + (b[0] - a[0]) * fraction, a[1] + (b[1] - a[1]) * fraction)
        if not _inside_region(point, outer, holes):
            return False
    return True


def _distance_to_boundary(point, polygons):
    """ Distance du point à la bordure la plus proche (contour et trous)."""
    best = float("inf")
    for polygon in polygons:
        info = _project_on_polygon(point, polygon)
        if info is not None:
            best = min(best, info[2])
    return best


def _build_travel_graph(outer, holes):
    """Graphe de déplacement intérieur (façon underpath d'Ink/Stitch).

    Un quadrillage couvre la forme ; seules les mailles à l'intérieur sont
    gardées. Les arêtes relient les mailles voisines et coûtent d'autant
    plus près de la bordure : le trajet préfère passer au milieu du
    remplissage, où les rangées suivantes le recouvriront."""
    polygons = [outer] + list(holes)
    xs = [point[0] for point in outer[:-1]]
    ys = [point[1] for point in outer[:-1]]
    min_x, min_y = min(xs), min(ys)
    max_x, max_y = max(xs), max(ys)

    step = TRAVEL_UNDERPATH_GRID_MM
    while (
        ((max_x - min_x) / step + 2.0) * ((max_y - min_y) / step + 2.0)
        > TRAVEL_UNDERPATH_MAX_NODES
    ):
        step *= 2.0

    points = []
    lignes_par_rang = {}
    rang = 0
    y = min_y + step / 2.0
    while y < max_y:
        ligne = {}
        colonne = 0
        x = min_x + step / 2.0
        while x < max_x:
            if _inside_region((x, y), outer, holes):
                ligne[colonne] = len(points)
                points.append((x, y))
            x += step
            colonne += 1
        if ligne:
            lignes_par_rang[rang] = ligne
        y += step
        rang += 1

    margins = [_distance_to_boundary(point, polygons) for point in points]

    adjacency = {index: {} for index in range(len(points))}
    for rang, ligne in lignes_par_rang.items():
        for colonne, index in ligne.items():
            for de_colonne, de_rang in ((0, 1), (1, 0), (1, 1), (-1, 1)):
                voisin = lignes_par_rang.get(rang + de_rang, {}).get(colonne + de_colonne)
                if voisin is None:
                    continue
                if not _segment_inside_region(points[index], points[voisin], outer, holes):
                    continue
                longueur = math.hypot(
                    points[index][0] - points[voisin][0],
                    points[index][1] - points[voisin][1],
                )
                marge = min(margins[index], margins[voisin])
                poids = longueur / (marge + 0.25)
                adjacency[index][voisin] = poids
                adjacency[voisin][index] = poids
    return points, adjacency


def _travel_route_underpath(a, b, outer, holes, memo):
    """Chemin intérieur le plus court de a vers b (underpath Ink/Stitch).

    Retourne la suite des points intermédiaires (hors a et b), ou None si
    aucun chemin intérieur n'existe."""
    if "graphe" not in memo:
        memo["graphe"] = _build_travel_graph(outer, holes)
    points, adjacency = memo["graphe"]
    if len(points) < 2:
        return None

    step = TRAVEL_UNDERPATH_GRID_MM

    def ancres(point):
        candidates = sorted(
            (math.hypot(point[0] - p[0], point[1] - p[1]), index)
            for index, p in enumerate(points)
            if abs(p[0] - point[0]) < 10 * step and abs(p[1] - point[1]) < 10 * step
        )
        resultats = []
        for distance, index in candidates:
            if len(resultats) >= 8 or distance > 3 * step:
                break
            if _segment_inside_region(point, points[index], outer, holes):
                resultats.append(index)
        return resultats

    departs = ancres(a)
    arrivees = set(ancres(b))
    if not departs or not arrivees:
        return None

    meilleur = {}
    parent = {}
    file = []
    for index in departs:
        cout = math.hypot(a[0] - points[index][0], a[1] - points[index][1])
        meilleur[index] = cout
        parent[index] = None
        heapq.heappush(file, (cout, index))

    final = None
    while file:
        cout, index = heapq.heappop(file)
        if cout > meilleur.get(index, cout):
            continue
        if index in arrivees:
            final = index
            break
        for voisin, poids in adjacency[index].items():
            suivant = cout + poids
            if suivant < meilleur.get(voisin, float("inf")):
                meilleur[voisin] = suivant
                parent[voisin] = index
                heapq.heappush(file, (suivant, voisin))
    if final is None:
        return None

    chemin = []
    index = final
    while index is not None:
        chemin.append(points[index])
        index = parent.get(index)
    chemin.reverse()
    return _smooth_route(chemin, outer, holes)


def _smooth_route(points, outer, holes):
    """Supprime les cols inutiles du chemin de grille, en restant dans la forme."""
    points = _clean_path(points)
    for _ in range(3):
        if len(points) <= 2:
            break
        result = [points[0]]
        index = 0
        while index < len(points) - 1:
            limite = min(index + 14, len(points) - 1)
            choisi = index + 1
            for essai in range(limite, index + 1, -1):
                if _segment_inside_region(points[index], points[essai], outer, holes):
                    choisi = essai
                    break
            result.append(points[choisi])
            index = choisi
        if result == points:
            break
        points = result
    return points


def fill_stitch_segments(contour, angle_deg=0.0, spacing_mm=2.0):
    """Génère une trajectoire indépendante pour chaque segment de remplissage."""
    if not contour.closed:
        raise ValueError("Le remplissage nécessite un contour fermé.")

    angle_deg = float(angle_deg)
    spacing_mm = float(spacing_mm)
    if not math.isfinite(angle_deg):
        raise ValueError("L'angle de remplissage doit être fini.")
    if not math.isfinite(spacing_mm) or not (FILL_SPACING_MIN <= spacing_mm <= FILL_SPACING_MAX):
        raise ValueError("L'écart de remplissage est invalide.")

    outer_path = _path_for_contour(contour)
    holes = [_path_for_contour(hole) for hole in getattr(contour, "holes", [])]

    center = (
        sum(x for x, _ in outer_path[:-1]) / len(outer_path[:-1]),
        sum(y for _, y in outer_path[:-1]) / len(outer_path[:-1]),
    )
    angle = math.radians(angle_deg)
    rotated_outer = [_rotate(point, center, -angle) for point in outer_path]
    rotated_holes = [
        [_rotate(point, center, -angle) for point in hole]
        for hole in holes
    ]
    min_y = min(y for _, y in rotated_outer)
    max_y = max(y for _, y in rotated_outer)
    for hole in rotated_holes:
        min_y = min(min_y, min(y for _, y in hole))
        max_y = max(max_y, max(y for _, y in hole))
    height = max_y - min_y
    if height <= EPSILON:
        raise ValueError("Le contour doit avoir une hauteur pour être rempli.")

    row_count = max(1, math.ceil(height / spacing_mm))
    row_spacing = height / row_count
    segments = []
    for row_index in range(row_count):
        y = min_y + row_spacing * (row_index + 0.5)
        row_segments = []
        for start_x, end_x in _fill_segment_pairs_for_row(rotated_outer, rotated_holes, y):
            start_point = (start_x, y)
            end_point = (end_x, y)
            row_segments.append((start_point, end_point))

        if row_index % 2:
            row_segments.reverse()
        for segment_index, (start, end) in enumerate(row_segments):
            start = _rotate(start, center, angle)
            end = _rotate(end, center, angle)
            if (row_index + segment_index) % 2:
                segments.append((end, start))
            else:
                segments.append((start, end))

    return [list(segment) for segment in segments]


def fill_stitch(contour, angle_deg=0.0, spacing_mm=2.0):
    """Retourne les points de remplissage à plat pour les usages géométriques."""
    return [
        point
        for segment in fill_stitch_segments(contour, angle_deg, spacing_mm)
        for point in segment
    ]


# Limite de sécurité : le format DST refuse un point de plus de 12,1 mm.
FILL_STITCH_LENGTH_MIN = 0.5
FILL_STITCH_LENGTH_MAX = 12.0

# Le sous-point se tient à peine à l'intérieur de la bordure (repli court),
# comme le « passage en bordure » du manuel EOS3 : il suit le contour sans
# rester à cheval dessus.
TRAVEL_INSIDE_OFFSET_MM = 0.2
TRAVEL_ON_EDGE_TOLERANCE_MM = 1e-6

# Contournement d'un trou explicite (inspiration underpath d'Ink/Stitch) :
# le trajet direct étant interdit, on route les sous-points à l'intérieur de
# la forme, en préférant le milieu du remplissage.
TRAVEL_UNDERPATH_GRID_MM = 3.0     # maille du graphe de déplacement
TRAVEL_UNDERPATH_MAX_NODES = 20000


def _subdivide(start, end, max_len):
    """Points intermédiaires entre start (exclu) et end (inclus).

    La distance entre deux points consécutifs ne dépasse jamais max_len.
    """
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    distance = math.hypot(dx, dy)
    if distance <= EPSILON:
        return []
    intervals = max(1, math.ceil(distance / max_len))
    return [
        (start[0] + dx * i / intervals, start[1] + dy * i / intervals)
        for i in range(1, intervals + 1)
    ]


def _subdivide_polyline(points, max_len):
    """Découpe une suite de points en tronçons qui ne dépassent pas max_len."""
    result = []
    for start, end in zip(points, points[1:]):
        result.extend(_subdivide(start, end, max_len))
    return result


def _project_on_polygon(point, polygon):
    """Projette un point sur la ligne fermée `polygon` (polygon[-1] == polygon[0]).

    Retourne (index_de_l'arête, projection, distance, t) ou None."""
    best = None
    for i in range(len(polygon) - 1):
        p1, p2 = polygon[i], polygon[i + 1]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length2 = dx * dx + dy * dy
        if length2 <= EPSILON:
            continue
        t = ((point[0] - p1[0]) * dx + (point[1] - p1[1]) * dy) / length2
        t = max(0.0, min(1.0, t))
        proj = (p1[0] + dx * t, p1[1] + dy * t)
        d = math.hypot(point[0] - proj[0], point[1] - proj[1])
        if best is None or d < best[2]:
            best = (i, proj, d, t)
    return best


def _boundary_arc(a, b, polygon):
    """Arc le plus court du contour entre a et b (points sur le contour).

    Retourne les points du contour entre a (exclu) et b (inclus), ou None
    si l'un des deux points n'est pas sur le contour."""
    info_a = _project_on_polygon(a, polygon)
    info_b = _project_on_polygon(b, polygon)
    if info_a is None or info_b is None:
        return None
    if (
        info_a[2] > TRAVEL_ON_EDGE_TOLERANCE_MM
        or info_b[2] > TRAVEL_ON_EDGE_TOLERANCE_MM
    ):
        return None
    index_a, index_b = info_a[0], info_b[0]
    n = len(polygon) - 1
    if index_a == index_b:
        return [b]

    forward = []
    k = (index_a + 1) % n
    while True:
        forward.append(polygon[k])
        if k == index_b:
            break
        k = (k + 1) % n
    forward.append(b)

    backward = []
    k = index_a
    while True:
        backward.append(polygon[k])
        if k == (index_b + 1) % n:
            break
        k = (k - 1) % n
    backward.append(b)

    def arc_length(points):
        total = 0.0
        previous = a
        for point in points:
            total += math.hypot(point[0] - previous[0], point[1] - previous[1])
            previous = point
        return total

    if arc_length(forward) <= arc_length(backward):
        return forward
    return backward


def _inward_edge_normal(p1, p2, polygon):
    """Normale unitaire de l'arête (p1, p2), tournée vers l'intérieur."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length <= EPSILON:
        return (0.0, 0.0)
    candidate = (dy / length, -dx / length)
    probe = (
        (p1[0] + p2[0]) / 2 + candidate[0] * 0.1,
        (p1[1] + p2[1]) / 2 + candidate[1] * 0.1,
    )
    if not _inside_polygon(probe, polygon):
        candidate = (-candidate[0], -candidate[1])
    return candidate


def _offset_toward_inside(point, polygon, offset):
    """Décale un point du contour vers l'intérieur de la forme."""
    info = _project_on_polygon(point, polygon)
    if info is None:
        return point
    i = info[0]
    normal = _inward_edge_normal(polygon[i], polygon[i + 1], polygon)
    return (point[0] + normal[0] * offset, point[1] + normal[1] * offset)


def _segment_traverse_un_trou(a, b, holes):
    """Vrai si le trajet droit a→b passe dans un trou explicite (interdit)."""
    distance = math.hypot(b[0] - a[0], b[1] - a[1])
    if distance <= EPSILON:
        return False
    steps = max(1, math.ceil(distance / 1.0))
    for hole in holes:
        for index in range(steps + 1):
            fraction = index / steps
            point = (a[0] + (b[0] - a[0]) * fraction, a[1] + (b[1] - a[1]) * fraction)
            if _inside_polygon(point, hole):
                return True
    return False


def _travel_side_points(a, b, outer, max_len, holes=(), memo=None):
    """Sous-points de a vers b, façon EOS : couture simple droite.

    Le déplacement traverse l'espace vide sans problème (c'est la ligne de
    liaison visible dans EOS) et passe dans les zones pas encore cousues —
    les rangées suivantes le recouvrent. L'ordre de couture évite déjà les
    traversées de rangées déjà cousues (règle « jamais au-dessus du
    remplissage »). Seul un trou explicite est interdit : alors on contourne
    par un chemin intérieur (graphe de déplacement, inspiration Ink/Stitch),
    en repli par la bordure, puis tout droit en dernier recours."""
    if not holes:
        return _subdivide(a, b, max_len)

    if not _segment_traverse_un_trou(a, b, holes):
        return _subdivide(a, b, max_len)

    chemin = _travel_route_underpath(a, b, outer, holes, {} if memo is None else memo)
    if chemin:
        return _subdivide_polyline(_clean_path([a] + chemin + [b]), max_len)

    arc = _boundary_arc(a, b, outer)
    if arc is None:
        return _subdivide(a, b, max_len)
    route = [a]
    if math.hypot(b[0] - a[0], b[1] - a[1]) > EPSILON:
        route.append(_offset_toward_inside(a, outer, TRAVEL_INSIDE_OFFSET_MM))
    for point in arc[:-1]:
        route.append(_offset_toward_inside(point, outer, TRAVEL_INSIDE_OFFSET_MM))
    route.append(b)
    return _subdivide_polyline(route, max_len)


def _croise_strictement(p1, p2, p3, p4):
    """Vrai si le segment (p1, p2) coupe l'intérieur du segment (p3, p4).

    Les simples contacts bout à bout (extrémités partagées) ne comptent pas :
    c'est le cas normal du passage d'une rangée à sa voisine."""
    d1 = (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])
    d2 = (p2[0] - p1[0]) * (p4[1] - p1[1]) - (p2[1] - p1[1]) * (p4[0] - p1[0])
    d3 = (p4[0] - p3[0]) * (p1[1] - p3[1]) - (p4[1] - p3[1]) * (p1[0] - p3[0])
    d4 = (p4[0] - p3[0]) * (p2[1] - p3[1]) - (p4[1] - p3[1]) * (p2[0] - p3[0])
    return (
        ((d1 > EPSILON and d2 < -EPSILON) or (d1 < -EPSILON and d2 > EPSILON))
        and ((d3 > EPSILON and d4 < -EPSILON) or (d3 < -EPSILON and d4 > EPSILON))
    )


def _rangées_traversées(a, b, cousues):
    """Nombre de rangées déjà cousues que le trajet droit a→b traverserait.

    Un trajet qui traverse des rangées cousues resterait visible au-dessus
    du remplissage : on préfère les candidats qui n'en traversent aucun."""
    total = 0
    for p3, p4 in cousues:
        if _croise_strictement(a, b, p3, p4):
            total += 1
    return total


def fill_stitch_paths(contour, angle_deg=None, spacing_mm=None, stitch_length=2.5,
                      observation=None):
    """Remplissage « tatami » : une trajectoire continue par bloc.

    Les rangées restent des segments droits découpés en points de longueur
    stitch_length. Les transitions entre rangées ou entre zones sont des
    sous-points cousus (jamais un saut) : une couture simple droite, y
    compris à travers l'espace vide, comme EOS. Seul un trajet qui
    traverserait un trou explicite est détourné (chemin intérieur, puis
    bordure en repli).

    Ordre de couture « intelligence » façon EOS (et graphe de remplissage
    Ink/Stitch) : l'aiguille remplit des zones contiguës, approche la
    suivante par une couture simple droite, et recommence — le tout en
    évitant de traverser des rangées déjà cousues (le sous-point resterait
    visible au-dessus du remplissage). Le départ est la rangée la plus
    haute, extrémité la plus à gauche — sauf si l'utilisateur a placé
    `contour.start_point`, auquel cas le bloc commence là ; les rangées
    proches de `contour.end_point` sont gardées pour la fin afin de
    terminer juste à côté du point choisi.

    Étape B2A — observation seulement : si ``observation`` est une instance de
    ``FillObservation``, la fonction la remplit **après** avoir construit la
    trajectoire, avec le résultat du planificateur ``plan_fill_path`` et les
    statistiques du parcours réellement produit. Aucune décision n'en dépend :
    la trajectoire renvoyée est strictement identique avec ou sans observation.
    ``observation=None`` (défaut, cas du moteur) n'ajoute aucun calcul et
    n'importe même pas le planificateur."""
    started = time.perf_counter()
    if angle_deg is None:
        angle_deg = contour.fill_angle
    if spacing_mm is None:
        spacing_mm = contour.fill_spacing

    stitch_length = float(stitch_length)
    if not math.isfinite(stitch_length) or not (
        FILL_STITCH_LENGTH_MIN <= stitch_length <= FILL_STITCH_LENGTH_MAX
    ):
        raise ValueError("La longueur du point de remplissage est invalide.")

    segments = fill_stitch_segments(contour, angle_deg, spacing_mm)
    outer = _path_for_contour(contour)
    holes = [_path_for_contour(hole) for hole in getattr(contour, "holes", [])]

    reste = [
        (start, end)
        for start, end in segments
        if math.hypot(end[0] - start[0], end[1] - start[1]) > EPSILON
    ]
    if not reste:
        return []

    # Copie destinée au planificateur : `reste` est consommé par la boucle.
    rows_for_plan = list(reste)
    liaison_lengths = [] if observation is not None else None
    greedy_started = time.perf_counter()

    depart = getattr(contour, "start_point", None)
    arrivee = getattr(contour, "end_point", None)

    if depart is not None:
        # Début imposé par l'utilisateur : l'aiguille démarre là.
        path = [depart]
    else:
        # Premier segment automatique : rangée la plus haute, extrémité la
        # plus à gauche.
        premier = min(range(len(reste)), key=lambda i: (reste[i][0][1], reste[i][0][0]))
        start, end = reste.pop(premier)
        path = [start]
        path.extend(_subdivide(start, end, stitch_length))

    memo = {}
    cousues = []  # rangées déjà cousues (paires de points)

    # Réserve « près de l'arrivée » (modèle EOS) : les rangées proches du
    # point d'arrivée sont gardées pour la fin ; le bloc se termine alors
    # juste à côté du point choisi par l'utilisateur, sans grande diagonale
    # finale au-dessus du remplissage.
    reserves = set()
    if arrivee is not None:
        xs = [point[0] for point in outer[:-1]]
        ys = [point[1] for point in outer[:-1]]
        diag = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
        rayon = 0.30 * diag
        reserves = {
            (s, e)
            for s, e in reste
            if math.hypot((s[0] + e[0]) / 2 - arrivee[0], (s[1] + e[1]) / 2 - arrivee[1]) <= rayon
        }

    while reste:
        position = path[-1]
        nb_reserves = sum(1 for segment in reste if segment in reserves)
        candidats = []
        for s, e in reste:
            # La réserve attend : on ne l'approche que lorsqu'il ne reste plus rien.
            if (s, e) in reserves and len(reste) > nb_reserves:
                continue
            distance_s = math.hypot(position[0] - s[0], position[1] - s[1])
            distance_e = math.hypot(position[0] - e[0], position[1] - e[1])
            if distance_s <= distance_e:
                candidats.append((distance_s, (s, e), s, e))
            else:
                candidats.append((distance_e, (s, e), e, s))
        candidats.sort(key=lambda candidat: candidat[0])

        # Règle « jamais au-dessus du remplissage » : parmi les voisins les
        # plus proches, préférer un candidat dont l'approche ne traverse
        # aucune rangée déjà cousue. À défaut (impasse totale), le moins de
        # traversées.
        choisi = None
        moins_de_traversees = None
        for distance, segment, s, e in candidats[:16]:
            traversee = _rangées_traversées(position, s, cousues)
            if traversee == 0:
                choisi = (segment, s, e)
                break
            if moins_de_traversees is None or traversee < moins_de_traversees:
                moins_de_traversees = traversee
                choisi = (segment, s, e)

        segment, start, end = choisi
        reste.remove(segment)
        cousues.append((start, end))

        avant_liaison = len(path) if observation is not None else 0
        path.extend(_travel_side_points(path[-1], start, outer, stitch_length, holes, memo))
        if observation is not None:
            liaison_lengths.append(_polyline_length(path[avant_liaison:]))
        path.extend(_subdivide(start, end, stitch_length))

    arrivee_length = 0.0
    if arrivee is not None:
        # Fin imposée par l'utilisateur : dernier sous-point vers cette place.
        avant_arrivee = len(path)
        path.extend(_travel_side_points(path[-1], arrivee, outer, stitch_length, holes, memo))
        if observation is not None:
            arrivee_length = _polyline_length(path[avant_arrivee:])

    if len(path) < 2:
        return []
    if observation is not None:
        _observe_fill(
            observation,
            rows=rows_for_plan,
            outer=outer,
            holes=holes,
            spacing_mm=spacing_mm,
            path=path,
            depart=depart,
            arrivee=arrivee,
            liaison_lengths=liaison_lengths,
            arrival_length=arrivee_length,
            greedy_seconds=time.perf_counter() - greedy_started,
            total_seconds=time.perf_counter() - started,
        )
    return [path]


def _observe_fill(observation, *, rows, outer, holes, spacing_mm, path, depart,
                  arrivee, liaison_lengths, arrival_length, greedy_seconds,
                  total_seconds):
    """Remplit ``observation`` sans jamais influencer la trajectoire produite.

    Appelée seulement après la construction complète de ``path``. L'import du
    planificateur est paresseux : sans observation, ``planning`` n'est jamais
    chargé. Toute exception du planificateur est capturée dans
    ``observation.error`` — un remplissage ne doit jamais échouer à cause de
    l'observation.
    """
    observation.greedy = link_stats(liaison_lengths)
    observation.greedy_arrival_length = arrival_length
    observation.greedy_seconds = greedy_seconds
    observation.rows_total = len(rows)
    observation.total_seconds = total_seconds

    plan_started = time.perf_counter()
    try:
        from core.stitches.planning import Workspace, plan_fill_path

        workspace = Workspace(outer=outer, holes=holes, spacing=spacing_mm)
        start = depart if depart is not None else path[0]
        end = arrivee if arrivee is not None else path[-1]
        plan = plan_fill_path(workspace, rows, start, end)
    except Exception as erreur:  # observation uniquement : jamais d'échec de couture
        observation.error = f"{type(erreur).__name__}: {erreur}"
        observation.plan_seconds = time.perf_counter() - plan_started
        return

    observation.plan_seconds = time.perf_counter() - plan_started
    observation.rows_sewn = plan.rows_sewn
    observation.completed = plan.completed
    observation.failure = plan.failure
    observation.refused_link_count = len(plan.refusals)
    observation.refused_links = tuple(
        (
            refusal.step,
            refusal.route.length if refusal.route is not None else 0.0,
            refusal.reason,
        )
        for refusal in plan.refusals
    )
    observation.visible_link_count = len(plan.visible_steps)
    observation.visible_link_total = sum(
        step.route.length for step in plan.visible_steps)
    observation.turns = len(plan.turns)
    observation.max_turn_outside = plan.max_turn_outside
    observation.arrival_length = plan.arrival_length
    observation.plan = link_stats(step.route.length for step in plan.steps)
