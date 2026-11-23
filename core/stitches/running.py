import math


def resample(polyline, stitch_length):
    """Pose un point tous les 'stitch_length' mm le long de la ligne.

    Le premier et le dernier point de la ligne sont toujours conservés.
    """
    points = [polyline[0]]
    dist_to_next = stitch_length

    for (x1, y1), (x2, y2) in zip(polyline, polyline[1:]):
        seg = math.hypot(x2 - x1, y2 - y1)
        if seg == 0:
            continue
        pos = 0.0
        while seg - pos >= dist_to_next - 1e-9:
            pos += dist_to_next
            t = pos / seg
            points.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t))
            dist_to_next = stitch_length
        dist_to_next -= seg - pos

    # Le dernier point tombe exactement au bout de la ligne.
    end = polyline[-1]
    gap = math.hypot(end[0] - points[-1][0], end[1] - points[-1][1])
    if gap > 1e-9:
        if gap < stitch_length * 0.5 and len(points) > 1:
            points[-1] = end      # reste trop court : on allonge le dernier point
        else:
            points.append(end)
    return points


def running_stitch(contour, stitch_length_mm=2.5):
    """Calcule les points d'aiguille d'un running stitch pour un contour.

    Retourne une liste de (x, y) en millimètres.
    """
    if stitch_length_mm <= 0:
        raise ValueError("La longueur du point doit être supérieure à 0.")

    result = []
    for piece in contour.split_at_corners():
        pts = resample(piece, stitch_length_mm)
        if result:
            pts = pts[1:]  # le point d'angle est déjà dans la liste
        result.extend(pts)
    return result