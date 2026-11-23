import math
import os

import pyembroidery

from core.stitches.engine import stitch_paths
from core.simulation import build_sequence

UNITS_PER_MM = 10        # pyembroidery compte en dixièmes de millimètre
MAX_STITCH_MM = 12.1     # limite d'une commande du format DST
JUMP_STEP_UNITS = 100    # nos sauts sont découpés en morceaux de 10 mm
FLIP_Y = False           # si le dessin sort à l'envers sur la machine : mettre True


def validate(objects, frame_size=None):
    """Vérifie que les points sont sûrs. Lève ValueError sinon."""
    for points in objects:
        for x, y in points:
            if not (math.isfinite(x) and math.isfinite(y)):
                raise ValueError("Une coordonnée invalide a été trouvée dans le motif.")
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            if math.hypot(x2 - x1, y2 - y1) > MAX_STITCH_MM:
                raise ValueError(
                    "Un point est trop long pour le format DST (plus de 12,1 mm). "
                    "Réduisez la longueur du point ou la largeur du satin."
                )

    if frame_size is not None:
        demi_largeur = frame_size[0] / 2
        demi_hauteur = frame_size[1] / 2
        for points in objects:
            for x, y in points:
                if abs(x) > demi_largeur or abs(y) > demi_hauteur:
                    raise ValueError(
                        "⚠ MOTIF TROP GRAND POUR LE CADRE "
                        f"({frame_size[0]:g} × {frame_size[1]:g} mm)."
                    )


def _to_units(x, y):
    if FLIP_Y:
        y = -y
    return round(x * UNITS_PER_MM), round(y * UNITS_PER_MM)


def _jump_to(pattern, position, x, y):
    """Saute (sans broder) vers (x, y), en petits sauts. Retourne la nouvelle position."""
    cx, cy = position
    distance = math.hypot(x - cx, y - cy)
    if distance == 0:
        return position
    n = max(1, math.ceil(distance / JUMP_STEP_UNITS))
    for i in range(1, n + 1):
        t = i / n
        pattern.add_stitch_absolute(
            pyembroidery.JUMP, round(cx + (x - cx) * t), round(cy + (y - cy) * t)
        )
    return (x, y)


def build_pattern(objects, steps=None):
    """Construit le motif de broderie à partir des points (liste de listes de (x, y) en mm)."""
    pattern = pyembroidery.EmbPattern()

    if steps is not None:
        position = (0, 0)
        for step in steps:
            if step.kind == "trim":
                pattern.add_stitch_absolute(pyembroidery.TRIM, *position)
            elif step.kind == "color_change":
                pattern.add_stitch_absolute(pyembroidery.COLOR_CHANGE, *position)
            elif step.kind == "jump":
                position = _jump_to(pattern, position, *_to_units(step.x, step.y))
            elif step.kind == "stitch":
                position = _to_units(step.x, step.y)
                pattern.add_stitch_absolute(pyembroidery.STITCH, *position)
        pattern.add_stitch_absolute(pyembroidery.END, *position)
        return pattern

    position = (0, 0)
    first = True

    for points in objects:
        units = [_to_units(x, y) for x, y in points]
        if not first:
            pattern.add_stitch_absolute(pyembroidery.TRIM, *position)  # coupe du fil
        position = _jump_to(pattern, position, *units[0])
        for ux, uy in units:
            pattern.add_stitch_absolute(pyembroidery.STITCH, ux, uy)
        position = units[-1]
        first = False

    pattern.add_stitch_absolute(pyembroidery.END, *position)
    return pattern


def _size_mm(objects):
    xs = [x for points in objects for x, _ in points]
    ys = [y for points in objects for _, y in points]
    return max(xs) - min(xs), max(ys) - min(ys)


def read_dst(path):
    """Relit un fichier DST et retourne un résumé de son contenu."""
    path = os.fspath(path)
    pattern = pyembroidery.read(path)
    if pattern is None:
        raise ValueError("Le fichier DST n'a pas pu être relu.")

    stitches = jumps = color_changes = 0
    xs, ys = [], []
    for x, y, command in pattern.stitches:
        code = command & 0xFF
        if code == pyembroidery.STITCH:
            stitches += 1
            xs.append(x)
            ys.append(y)
        elif code == pyembroidery.JUMP:
            jumps += 1
        elif code == pyembroidery.COLOR_CHANGE:
            color_changes += 1

    width = (max(xs) - min(xs)) / UNITS_PER_MM if xs else 0.0
    height = (max(ys) - min(ys)) / UNITS_PER_MM if ys else 0.0
    return {
        "stitches": stitches,
        "jumps": jumps,
        "color_changes": color_changes,
        "width_mm": width,
        "height_mm": height,
    }


def export_dst(contours, path, frame_size=None):
    """Exporte les dessins en DST, relit le fichier et vérifie le résultat.

    Retourne un résumé (points, dimensions...). Lève ValueError ou RuntimeError
    si quelque chose ne va pas.
    """
    paths_by_object = [stitch_paths(c) for c in contours]
    objects = [
        [point for stitch_path in paths for point in stitch_path]
        for paths in paths_by_object
    ]
    objects = [points for points in objects if len(points) >= 2]
    if not objects:
        raise ValueError("Il n'y a rien à exporter : dessinez d'abord au moins un contour.")

    stitch_runs = [
        stitch_path
        for paths in paths_by_object
        for stitch_path in paths
        if len(stitch_path) >= 2
    ]
    validate(stitch_runs, frame_size)
    steps = build_sequence(contours)
    pattern = build_pattern(objects, steps=steps)

    # On écrit d'abord un fichier temporaire, puis on le remplace.
    base, extension = os.path.splitext(path)
    chemin_temporaire = base + ".tmp" + extension
    pyembroidery.write(pattern, chemin_temporaire)
    os.replace(chemin_temporaire, path)

    # Relecture et vérification.
    attendu_points = sum(1 for step in steps if step.kind == "stitch")
    attendu_couleurs = sum(1 for step in steps if step.kind == "color_change")
    attendu_largeur, attendu_hauteur = _size_mm(objects)
    relu = read_dst(path)

    problemes = []
    if relu["stitches"] != attendu_points:
        problemes.append(f"nombre de points : {relu['stitches']} relus au lieu de {attendu_points}")
    if relu["color_changes"] != attendu_couleurs:
        problemes.append(
            f"changements de couleur : {relu['color_changes']} relus au lieu de {attendu_couleurs}"
        )
    if abs(relu["width_mm"] - attendu_largeur) > 0.15:
        problemes.append("largeur différente")
    if abs(relu["height_mm"] - attendu_hauteur) > 0.15:
        problemes.append("hauteur différente")
    if problemes:
        raise RuntimeError("La vérification après relecture a échoué : " + " ; ".join(problemes))

    return {
        "stitches": attendu_points,
        "objects": len(objects),
        "jumps": relu["jumps"],
        "color_changes": relu["color_changes"],
        "width_mm": relu["width_mm"],
        "height_mm": relu["height_mm"],
    }
