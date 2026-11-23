from core.stitches.engine import stitch_points


def _extent(contour):
    """Rectangle réellement occupé par le dessin : ligne centrale ET points de broderie
    (pour un satin, la largeur de la colonne compte)."""
    x0, y0, x1, y1 = contour.bounds()
    points = stitch_points(contour)
    if points:
        xs = [x for x, _ in points]
        ys = [y for _, y in points]
        x0, x1 = min(x0, min(xs)), max(x1, max(xs))
        y0, y1 = min(y0, min(ys)), max(y1, max(ys))
    return x0, y0, x1, y1


def fits_in_frame(contours, frame_size):
    """True si tous les dessins restent dans le cadre.

    Le centre du cadre est le point (0, 0). Un dessin d'un seul point compte aussi.
    """
    demi_largeur = frame_size[0] / 2
    demi_hauteur = frame_size[1] / 2
    for contour in contours:
        if not contour.points:
            continue
        x0, y0, x1, y1 = _extent(contour)
        if x0 < -demi_largeur or x1 > demi_largeur:
            return False
        if y0 < -demi_hauteur or y1 > demi_hauteur:
            return False
    return True