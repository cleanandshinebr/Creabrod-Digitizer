import math

from core.objects import (
    SATIN_WIDTH_MIN,
    SATIN_WIDTH_MAX,
    SATIN_SPACING_MIN,
    SATIN_SPACING_MAX,
)

# Dans un angle, la pointe extérieure ne dépasse jamais 1,5 fois la demi-largeur.
MITER_LIMIT = 1.5
MITER_TAN_MAX = math.sqrt(MITER_LIMIT ** 2 - 1)
# Un changement de direction de plus de 25° est un coin : la colonne est coupée en deux
# morceaux qui se rejoignent en onglet. En dessous, c'est une courbe douce.
SHARP_ANGLE_DEG = 25.0
MIN_ROW_LENGTH = 0.4   # mm : on ne garde pas les rangées plus courtes


def _remove_duplicates(path):
    result = [path[0]]
    for point in path[1:]:
        if math.hypot(point[0] - result[-1][0], point[1] - result[-1][1]) > 1e-9:
            result.append(point)
    return result


def _unit(dx, dy):
    longueur = math.hypot(dx, dy)
    return (dx / longueur, dy / longueur)


def _longest_stitch(points):
    return max(
        (math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:])),
        default=0.0,
    )


# ---------------------------------------------------------------------------
# Méthode principale : morceaux de colonne qui se rejoignent en onglet aux coins
# ---------------------------------------------------------------------------
def _make_join(vertex, d_in, d_out, half):
    """Description d'un coin : la ligne de coupe (l'onglet) et la longueur de prolongement."""
    sx, sy = d_in[0] + d_out[0], d_in[1] + d_out[1]
    if math.hypot(sx, sy) < 1e-6:
        return None  # demi-tour complet : pas d'onglet possible
    q = _unit(sx, sy)
    dot = max(-1.0, min(1.0, d_in[0] * d_out[0] + d_in[1] * d_out[1]))
    virage = math.acos(dot)
    prolongement = half * min(math.tan(virage / 2), MITER_TAN_MAX)
    return {"vertex": vertex, "q": q, "ext": prolongement}


def _vertex_offsets(leg_dirs, half):
    """Décalage (vers le bord gauche) à chaque sommet du morceau."""
    normals = [(-d[1], d[0]) for d in leg_dirs]
    m = len(leg_dirs)
    offsets = []
    for j in range(m + 1):
        if j == 0:
            nx, ny = normals[0]
            facteur = 1.0
        elif j == m:
            nx, ny = normals[-1]
            facteur = 1.0
        else:
            bx = normals[j - 1][0] + normals[j][0]
            by = normals[j - 1][1] + normals[j][1]
            b = math.hypot(bx, by)
            if b < 1e-9:
                nx, ny = normals[j]
                facteur = 1.0
            else:
                nx, ny = bx / b, by / b
                cos_demi = max(nx * normals[j][0] + ny * normals[j][1], 1e-6)
                facteur = min(1 / cos_demi, MITER_LIMIT)
        offsets.append((nx * half * facteur, ny * half * facteur))
    return offsets


def _clip(a, b, join, garder):
    """Coupe le segment a-b le long de la ligne de l'onglet.

    garder = "derriere" (fin d'un morceau) ou "devant" (début d'un morceau).
    Retourne (a, b) raccourci, ou None si tout est de l'autre côté.
    """
    vx, vy = join["vertex"]
    qx, qy = join["q"]
    signe = 1.0 if garder == "derriere" else -1.0
    ga = signe * ((a[0] - vx) * qx + (a[1] - vy) * qy)
    gb = signe * ((b[0] - vx) * qx + (b[1] - vy) * qy)
    if ga <= 0 and gb <= 0:
        return a, b
    if ga > 0 and gb > 0:
        return None
    t = ga / (ga - gb)
    p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    if ga > 0:
        return p, b
    return a, p


def _leg_rows(leg_pts, leg_dirs, half, row_step, start_join, end_join):
    """Rangées de points d'un morceau de colonne : liste de (bord gauche, bord droit)."""
    offsets = _vertex_offsets(leg_dirs, half)
    lengths = [
        math.hypot(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(leg_pts, leg_pts[1:])
    ]
    length = sum(lengths)
    ext0 = start_join["ext"] if start_join else 0.0
    ext1 = end_join["ext"] if end_join else 0.0
    total = length + ext0 + ext1
    intervals = max(1, round(total / row_step))
    step = total / intervals

    rows = []
    seg = 0
    seg_start = 0.0
    for k in range(intervals + 1):
        s = -ext0 + k * step  # position le long de la ligne centrale
        if s < -1e-12:  # avant le début : on prolonge la ligne tout droit
            cx = leg_pts[0][0] + leg_dirs[0][0] * s
            cy = leg_pts[0][1] + leg_dirs[0][1] * s
            ox, oy = offsets[0]
        elif s > length + 1e-12:  # après la fin : on prolonge tout droit
            extra = s - length
            cx = leg_pts[-1][0] + leg_dirs[-1][0] * extra
            cy = leg_pts[-1][1] + leg_dirs[-1][1] * extra
            ox, oy = offsets[-1]
        else:
            while seg < len(lengths) - 1 and s > seg_start + lengths[seg] + 1e-12:
                seg_start += lengths[seg]
                seg += 1
            t = max(0.0, min(1.0, (s - seg_start) / lengths[seg]))
            p, q = leg_pts[seg], leg_pts[seg + 1]
            cx = p[0] + (q[0] - p[0]) * t
            cy = p[1] + (q[1] - p[1]) * t
            ox = offsets[seg][0] + (offsets[seg + 1][0] - offsets[seg][0]) * t
            oy = offsets[seg][1] + (offsets[seg + 1][1] - offsets[seg][1]) * t

        a = (cx + ox, cy + oy)
        b = (cx - ox, cy - oy)
        if start_join is not None:
            coupe = _clip(a, b, start_join, "devant")
            if coupe is None:
                continue
            a, b = coupe
        if end_join is not None:
            coupe = _clip(a, b, end_join, "derriere")
            if coupe is None:
                continue
            a, b = coupe
        if math.hypot(a[0] - b[0], a[1] - b[1]) < MIN_ROW_LENGTH:
            continue
        rows.append((a, b))
    return rows


def _points_with_joins(path, half, row_step):
    n = len(path)
    dirs = [_unit(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(path, path[1:])]

    # Position (en mm) de chaque sommet le long de la ligne
    positions = [0.0]
    for (x1, y1), (x2, y2) in zip(path, path[1:]):
        positions.append(positions[-1] + math.hypot(x2 - x1, y2 - y1))
    total_length = positions[-1]

    # Repérer les coins. Deux coins trop rapprochés (moins d'une demi-largeur) ne coupent
    # pas la colonne : le coin est alors traité comme une courbe serrée.
    cuts = [0]
    joins = {}
    for i in range(1, n - 1):
        dot = max(-1.0, min(1.0, dirs[i - 1][0] * dirs[i][0] + dirs[i - 1][1] * dirs[i][1]))
        if math.degrees(math.acos(dot)) <= SHARP_ANGLE_DEG:
            continue
        if positions[i] - positions[cuts[-1]] < half or total_length - positions[i] < half:
            continue
        cuts.append(i)
        joins[i] = _make_join(path[i], dirs[i - 1], dirs[i], half)
    cuts.append(n - 1)

    rows = []
    for a, b in zip(cuts, cuts[1:]):
        start_join = joins.get(a) if a > 0 else None
        end_join = joins.get(b) if b < n - 1 else None
        rows.extend(_leg_rows(path[a : b + 1], dirs[a:b], half, row_step, start_join, end_join))

    # Un point par rangée, en alternance bord gauche / bord droit
    return [(edge_a if k % 2 == 0 else edge_b) for k, (edge_a, edge_b) in enumerate(rows)]


# ---------------------------------------------------------------------------
# Méthode de secours : une seule bande continue, pointes d'angle limitées
# ---------------------------------------------------------------------------
def _points_simple(path, half, row_step):
    n = len(path)
    dirs = [_unit(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(path, path[1:])]
    offsets = _vertex_offsets(dirs, half)
    left = [(path[i][0] + offsets[i][0], path[i][1] + offsets[i][1]) for i in range(n)]
    right = [(path[i][0] - offsets[i][0], path[i][1] - offsets[i][1]) for i in range(n)]

    lengths = [
        math.hypot(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(path, path[1:])
    ]
    total = sum(lengths)
    intervals = max(1, round(total / row_step))
    step = total / intervals

    points = []
    segment = 0
    segment_start = 0.0
    for k in range(intervals + 1):
        s = k * step
        while segment < len(lengths) - 1 and s > segment_start + lengths[segment] + 1e-12:
            segment_start += lengths[segment]
            segment += 1
        t = max(0.0, min(1.0, (s - segment_start) / lengths[segment]))
        edge = left if k % 2 == 0 else right
        a = edge[segment]
        b = edge[segment + 1]
        points.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return points


def _points_continuous(path, half, row_step):
    """Génère une colonne continue avec une normale locale par rangée.

    Contrairement au secours basé sur les sommets, chaque rangée est calculée
    depuis la tangente du segment réellement parcouru. Cela évite que les
    décalages gauche/droit se croisent dans un coin continu.
    """
    lengths = [
        math.hypot(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(path, path[1:])
    ]
    total = sum(lengths)
    intervals = max(1, round(total / row_step))
    step = total / intervals

    points = []
    segment = 0
    segment_start = 0.0
    for k in range(intervals + 1):
        s = k * step
        while segment < len(lengths) - 1 and s > segment_start + lengths[segment] + 1e-12:
            segment_start += lengths[segment]
            segment += 1

        p, q = path[segment], path[segment + 1]
        longueur = lengths[segment]
        t = max(0.0, min(1.0, (s - segment_start) / longueur))
        cx = p[0] + (q[0] - p[0]) * t
        cy = p[1] + (q[1] - p[1]) * t
        dx, dy = (q[0] - p[0]) / longueur, (q[1] - p[1]) / longueur
        nx, ny = -dy, dx
        signe = 1.0 if k % 2 == 0 else -1.0
        points.append((cx + signe * nx * half, cy + signe * ny * half))
    return points


def _covers_centerline(path, points, half):
    """Vérifie que les rangées satin restent proches de tout le trajet central."""
    if not points:
        return False
    pas_controle = max(1, len(path) // 80)
    seuil = half * 2.2
    for centre in path[::pas_controle]:
        if min(math.hypot(centre[0] - x, centre[1] - y) for x, y in points) > seuil:
            return False
    return True


def _corner_reinforcements(points, contour, half):
    """Insère une piqûre au sommet de chaque coin explicite.

    Les deux bords d'une colonne satin peuvent passer de chaque côté d'un
    angle sans jamais traverser sa pointe intérieure. Une piqûre centrale
    locale évite ce vide, tout en laissant les courbes inchangées.
    """
    corners = []
    if len(contour.points) > 2:
        for i in (0, len(contour.points) - 1):
            x, y, kind = contour.points[i]
            if kind == "corner":
                corners.append((x, y))
    for i, (x, y, kind) in enumerate(contour.points[1:-1], start=1):
        if kind != "corner":
            continue
        px, py, _ = contour.points[i - 1]
        nx, ny, _ = contour.points[i + 1]
        incoming = _unit(x - px, y - py)
        outgoing = _unit(nx - x, ny - y)
        angle = math.degrees(
            math.acos(max(-1.0, min(1.0, incoming[0] * outgoing[0] + incoming[1] * outgoing[1])))
        )
        if angle > SHARP_ANGLE_DEG:
            corners.append((x, y))
    if not corners or not points:
        return points

    result = list(points)
    insertions = []
    for x, y in corners:
        index = min(
            range(len(result)),
            key=lambda i: math.hypot(result[i][0] - x, result[i][1] - y),
        )
        if math.hypot(result[index][0] - x, result[index][1] - y) > 1e-9:
            insertions.append((index, (x, y)))

    for index, vertex in sorted(insertions, reverse=True):
        result.insert(index, vertex)
    return result


def satin_stitch(contour, width_mm=3.0, spacing_mm=0.4):
    """Calcule les points d'aiguille d'une colonne satin le long d'un contour.

    La ligne centrale est le contour dessiné. 'spacing_mm' est l'écart entre deux
    piqûres du même côté de la colonne : un point traverse donc la colonne tous les
    spacing_mm / 2 le long de la ligne.
    Aux coins, la colonne est coupée en morceaux qui se rejoignent en onglet, sans
    superposition de points. Si le tracé est trop tordu pour cela (boucles, demi-tours),
    on utilise une méthode de secours qui garantit des points de longueur raisonnable.
    Retourne une liste de (x, y) en millimètres.
    """
    if not (SATIN_WIDTH_MIN <= width_mm <= SATIN_WIDTH_MAX):
        raise ValueError(
            f"La largeur du satin doit être entre {SATIN_WIDTH_MIN:g} et {SATIN_WIDTH_MAX:g} mm."
        )
    if not (SATIN_SPACING_MIN <= spacing_mm <= SATIN_SPACING_MAX):
        raise ValueError(
            f"L'écart entre les points doit être entre {SATIN_SPACING_MIN:g} et "
            f"{SATIN_SPACING_MAX:g} mm (en dessous, la densité est excessive)."
        )

    path = contour.flatten()
    if len(path) < 2:
        return []
    path = _remove_duplicates(path)
    if len(path) < 2:
        return []

    half = width_mm / 2
    row_step = spacing_mm / 2

    mode = getattr(contour, "satin_corner_mode", "square_miter")
    if mode == "continuous":
        # EOS3 conserve la traversée continue du coin, y compris ses
        # transitions longues. Cette voie ne doit donc pas utiliser le
        # garde-fou des onglets biseautés.
        points = _points_simple(path, half, row_step)
    elif mode == "insertion":
        points = _points_simple(path, half, row_step)
        points = _corner_reinforcements(points, contour, half)
    else:
        points = _points_with_joins(path, half, row_step)
        # Garde-fou : un point plus long que cela signalerait un tracé aberrant.
        if (
            len(points) < 2
            or _longest_stitch(points) > width_mm * MITER_LIMIT + 1.0
            or not _covers_centerline(path, points, half)
        ):
            points = _points_simple(path, half, row_step)
    return points if len(points) >= 2 else []
