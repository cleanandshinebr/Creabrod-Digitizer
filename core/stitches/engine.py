import math

from core.stitches.running import running_stitch
from core.stitches.running import resample
from core.stitches.satin import satin_stitch
from core.stitches.underlays import underlay_points
from core.stitches.fill import fill_stitch_paths


UNDERLAY_CONNECTION_STEP_MM = 2.5

# Cache des trajectoires.
#
# `_build_paths` est une fonction pure : un même contour (mêmes points, mêmes
# paramètres) donne toujours les mêmes points. Or le canvas rappelle le moteur
# à chaque rafraîchissement (dessin, compteur de points, survol, sélection) :
# sans cache, un grand remplissage était recalculé plusieurs fois par seconde.
#
# La clé contient tout ce qui influence la géométrie des points. Le résultat
# mis en cache ne doit pas être modifié : `stitch_paths` renvoie une nouvelle
# liste à chaque appel (les trajectoires internes, elles, sont partagées).
CACHE_MAX = 128
_cache = {}


def _point_signature(point):
    return (round(float(point[0]), 3), round(float(point[1]), 3))


def contour_signature(contour):
    """Clé de cache : tout ce qui influe sur les points générés.

    La couleur du fil et le mode de connexion n'y figurent pas : ils changent
    l'export, pas la géométrie cousue."""
    return (
        bool(contour.closed),
        contour.stitch_type,
        round(float(contour.stitch_length), 3),
        round(float(contour.satin_width), 3),
        round(float(contour.satin_spacing), 3),
        round(float(contour.fill_angle), 3),
        round(float(contour.fill_spacing), 3),
        contour.satin_corner_mode,
        tuple(contour.underlays),
        None if contour.start_point is None else _point_signature(contour.start_point),
        None if contour.end_point is None else _point_signature(contour.end_point),
        tuple((round(x, 3), round(y, 3), kind) for x, y, kind in contour.points),
        tuple(
            tuple((round(x, 3), round(y, 3), kind) for x, y, kind in hole.points)
            for hole in contour.holes
        ),
    )


def _connection_path(contour):
    path = []
    for point in contour.flatten():
        if not path or math.hypot(point[0] - path[-1][0], point[1] - path[-1][1]) > 1e-9:
            path.append(point)
    return resample(path, UNDERLAY_CONNECTION_STEP_MM) if len(path) >= 2 else path


def _append_points(result, points):
    if not points:
        return
    if not result:
        result.extend(points)
        return
    _append_segment(result, result[-1], points[0])
    result.extend(points[1:])


def _append_segment(result, start, end):
    distance = math.hypot(end[0] - start[0], end[1] - start[1])
    if distance <= 1e-9:
        return
    intervals = max(1, math.ceil(distance / UNDERLAY_CONNECTION_STEP_MM))
    for index in range(1, intervals + 1):
        fraction = index / intervals
        result.append(
            (
                start[0] + (end[0] - start[0]) * fraction,
                start[1] + (end[1] - start[1]) * fraction,
            )
        )


def _build_paths(contour):
    """Calcul réel des trajectoires (sans cache)."""
    result = []
    underlay_count = 0
    for underlay_type in contour.underlays:
        points = underlay_points(contour, underlay_type)
        if not points:
            continue
        if underlay_count % 2:
            points = list(reversed(points))
        _append_points(result, points)
        underlay_count += 1

    if underlay_count % 2:
        path = _connection_path(contour)
        if len(path) >= 2:
            _append_points(result, list(reversed(path)))

    if contour.stitch_type == "running":
        main_points = running_stitch(contour, contour.stitch_length)
    elif contour.stitch_type == "satin":
        main_points = satin_stitch(contour, contour.satin_width, contour.satin_spacing)
    elif contour.stitch_type == "fill":
        # Fill tatami : rangées découpées en points puis reliées par des
        # sous-points cousus. Un seul trajet par bloc : aucun saut interne.
        fill_paths = fill_stitch_paths(
            contour, contour.fill_angle, contour.fill_spacing, contour.stitch_length
        )
        if not fill_paths:
            return [result] if result else []
        if result:
            # `fill_paths` est recopié : le moteur Fill ne doit pas voir sa
            # liste modifiée (elle peut provenir d'un cache).
            _append_points(result, list(fill_paths[0]))
            paths = [result] + list(fill_paths[1:])
        else:
            paths = list(fill_paths)
        return [path for path in paths if path]
    else:
        raise ValueError(f"Type de point non géré : {contour.stitch_type}")
    _append_points(result, main_points)
    return [result] if result else []


def stitch_paths(contour):
    """Trajectoires cousues distinctes, sans relier les sauts.

    Le résultat est mis en cache : ne pas modifier les listes de points
    renvoyées (les recalculer depuis le contour à la place)."""
    cle = contour_signature(contour)
    en_cache = _cache.get(cle)
    if en_cache is not None:
        return list(en_cache)
    resultat = _build_paths(contour)
    if len(_cache) >= CACHE_MAX:
        _cache.clear()
    _cache[cle] = resultat
    return list(resultat)


def stitch_points(contour):
    """Retourne à plat les points cousus, sans inclure les déplacements."""
    return [point for path in stitch_paths(contour) for point in path]


def safe_stitch_points(contour):
    """Retourne [] plutôt qu'une exception pour un contour non supporté."""
    try:
        return stitch_points(contour)
    except ValueError:
        return []
