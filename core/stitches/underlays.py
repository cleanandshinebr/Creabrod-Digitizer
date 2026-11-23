"""Génération des sous-couches choisies pour un contour.

Les sous-couches restent des points cousus : elles ne créent pas de saut ni de
coupe entre elles et la couche principale.
"""

import math

from core.objects import UNDERLAY_TYPES
from core.stitches.running import resample


UNDERLAY_NAMES = {
    "centerline": "Centrale",
    "walking": "Marche à suivre",
    "zigzag": "Zigzag",
}
UNDERLAY_STEP_MM = 2.5
WALKING_STEP_MM = 1.5
ZIGZAG_STEP_MM = 2.0


def _clean_path(path):
    result = []
    for point in path:
        if not result or math.hypot(point[0] - result[-1][0], point[1] - result[-1][1]) > 1e-9:
            result.append(point)
    return result


def _zigzag_points(path, width_mm, step_mm):
    if len(path) < 2:
        return []
    lengths = [
        math.hypot(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(path, path[1:])
    ]
    total = sum(lengths)
    intervals = max(1, round(total / step_mm))
    step = total / intervals
    points = []
    segment = 0
    segment_start = 0.0
    half = width_mm / 2
    for index in range(intervals + 1):
        distance = index * step
        while segment < len(lengths) - 1 and distance > segment_start + lengths[segment] + 1e-12:
            segment_start += lengths[segment]
            segment += 1
        (x1, y1), (x2, y2) = path[segment], path[segment + 1]
        length = lengths[segment]
        t = max(0.0, min(1.0, (distance - segment_start) / length))
        cx = x1 + (x2 - x1) * t
        cy = y1 + (y2 - y1) * t
        dx, dy = (x2 - x1) / length, (y2 - y1) / length
        nx, ny = -dy, dx
        sign = 1.0 if index % 2 == 0 else -1.0
        points.append((cx + sign * nx * half, cy + sign * ny * half))
    return points


def underlay_points(contour, underlay_type):
    """Retourne les points d'une sous-couche donnée, sans saut ni coupe."""
    if underlay_type not in UNDERLAY_TYPES:
        raise ValueError(f"Type de sous-couche inconnu : {underlay_type}")
    path = _clean_path(contour.flatten())
    if len(path) < 2:
        return []
    if underlay_type == "centerline":
        return resample(path, UNDERLAY_STEP_MM)
    if underlay_type == "walking":
        return resample(path, WALKING_STEP_MM)
    width = max(1.0, min(float(contour.satin_width), 4.0))
    return _zigzag_points(path, width, ZIGZAG_STEP_MM)
