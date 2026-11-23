import math
from dataclasses import dataclass

from core.stitches.engine import safe_stitch_points
from core.simulation import build_sequence, count_table

DEFAULT_SPM = 600  # vitesse supposée de la machine, en points par minute (modifiable)


@dataclass
class Stats:
    objects: int = 0
    stitches: int = 0
    colors: int = 0
    trims: int = 0
    jumps: int = 0
    width_mm: float = 0.0
    height_mm: float = 0.0
    fits_frame: bool = True


def compute_stats(contours, frame_size=None):
    """Statistiques de tout le motif (les dessins terminés)."""
    objects = [safe_stitch_points(c) for c in contours]
    objects = [points for points in objects if len(points) >= 2]
    if not objects:
        return Stats()

    xs = [x for points in objects for x, _ in points]
    ys = [y for points in objects for _, y in points]

    # La machine démarre au centre (0, 0) : chaque déplacement vers un début de dessin est un saut.
    stitches, jumps, trims = count_table(build_sequence(contours))[-1]

    fits = True
    if frame_size is not None:
        demi_largeur = frame_size[0] / 2
        demi_hauteur = frame_size[1] / 2
        fits = all(abs(x) <= demi_largeur for x in xs) and all(
            abs(y) <= demi_hauteur for y in ys
        )

    colors = [
        c.thread_color.lower()
        for c, points in zip(contours, [safe_stitch_points(c) for c in contours])
        if len(points) >= 2
    ]
    return Stats(
        objects=len(objects),
        stitches=stitches,
        colors=len(set(colors)),
        trims=trims,
        jumps=jumps,
        width_mm=max(xs) - min(xs),
        height_mm=max(ys) - min(ys),
        fits_frame=fits,
    )
