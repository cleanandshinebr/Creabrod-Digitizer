"""Geometrie pure du prototype G3.

Aucun import du moteur : ni fill, ni planning, ni engine, ni export.
Ce module ne connait que des points, des segments et des surfaces.
"""

from __future__ import annotations

import math

Point = tuple[float, float]


def closed(points):
    """Ferme une polyligne et verifie qu'elle est exploitable."""
    pts = [(float(x), float(y)) for x, y in points]
    if len(pts) < 3:
        raise ValueError("Un contour doit contenir au moins 3 points.")
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    return pts


def area(points):
    """Aire absolue d'un polygone ferme (formule du lacet)."""
    pts = closed(points)
    total = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def perimeter(points):
    pts = closed(points)
    return sum(math.hypot(b[0] - a[0], b[1] - a[1])
               for a, b in zip(pts, pts[1:]))


def point_segment_distance(point, a, b):
    px, py = point
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-12:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / length_sq
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def resample(points, step=0.5):
    """Echantillonne le bord a pas constant : support de la carte de degagement."""
    pts = closed(points)
    samples = []
    for a, b in zip(pts, pts[1:]):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        count = max(1, int(math.ceil(length / step)))
        for index in range(count):
            t = index / count
            samples.append((a[0] + (b[0] - a[0]) * t,
                            a[1] + (b[1] - a[1]) * t))
    return samples


def boundary_samples(outer, holes, step=0.5):
    samples = list(resample(outer, step))
    for hole in holes:
        samples.extend(resample(hole, step))
    return samples


def inside(x, y, outer, holes=()):
    """Appartenance a la matiere : regle pair-impair sur tous les bords."""
    edges = []
    for polygon in (outer, *holes):
        pts = closed(polygon)
        edges.extend(zip(pts, pts[1:]))
    crossings = 0
    for (ax, ay), (bx, by) in edges:
        if (ay > y) != (by > y):
            x_cross = ax + (y - ay) * (bx - ax) / (by - ay)
            if x_cross > x:
                crossings += 1
    return crossings % 2 == 1


class ClearanceMap:
    """Carte de degagement : distance au bord le plus proche, en chaque point.

    La matiere est identifiee par balayage horizontal (pair-impair), ce qui
    traite les trous sans cas particulier. La distance est obtenue par une
    transformee en chanfrein (poids 1 et racine de 2) : erreur relative de
    quelques pour cent, cout lineaire, et une seule passe sur la grille.
    """

    def __init__(self, outer, holes=(), cell=None):
        self.outer = closed(outer)
        self.holes = [closed(hole) for hole in holes]
        xs = [p[0] for p in self.outer]
        ys = [p[1] for p in self.outer]
        largeur = max(xs) - min(xs)
        hauteur = max(ys) - min(ys)
        if cell is None:
            cell = max(0.5, max(largeur, hauteur) / 320.0)
        self.cell = float(cell)
        # marge de deux cellules : le pourtour doit baigner dans du vide,
        # sinon la transformee de distance mesure la grille, pas le bord.
        marge = 2.0 * self.cell
        self.xmin = min(xs) - marge
        self.ymin = min(ys) - marge
        self.xmax = max(xs) + marge
        self.ymax = max(ys) + marge
        width = self.xmax - self.xmin
        height = self.ymax - self.ymin
        self.nx = max(2, int(math.ceil(width / self.cell)) + 1)
        self.ny = max(2, int(math.ceil(height / self.cell)) + 1)
        self.inside = bytearray(self.nx * self.ny)
        self.clearance = [0.0] * (self.nx * self.ny)
        self._build_inside()
        self._build_clearance()

    # -- indices ---------------------------------------------------------
    def index(self, ix, iy):
        return iy * self.nx + ix

    def center(self, ix, iy):
        return (self.xmin + (ix + 0.5) * self.cell,
                self.ymin + (iy + 0.5) * self.cell)

    def xy_to_cell(self, x, y):
        ix = int((x - self.xmin) / self.cell)
        iy = int((y - self.ymin) / self.cell)
        return max(0, min(self.nx - 1, ix)), max(0, min(self.ny - 1, iy))

    def neighbors8(self, ix, iy):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                jx, jy = ix + dx, iy + dy
                if 0 <= jx < self.nx and 0 <= jy < self.ny:
                    yield jx, jy

    # -- construction ----------------------------------------------------
    def _build_inside(self):
        edges = []
        for polygon in (self.outer, *self.holes):
            edges.extend(zip(polygon, polygon[1:]))
        for iy in range(self.ny):
            y = self.ymin + (iy + 0.5) * self.cell
            crossings = []
            for (ax, ay), (bx, by) in edges:
                if (ay > y) != (by > y):
                    crossings.append(ax + (y - ay) * (bx - ax) / (by - ay))
            crossings.sort()
            for start, end in zip(crossings[0::2], crossings[1::2]):
                first = int(math.ceil((start - self.xmin) / self.cell - 0.5))
                last = int(math.floor((end - self.xmin) / self.cell - 0.5))
                for ix in range(max(0, first), min(self.nx - 1, last) + 1):
                    self.inside[self.index(ix, iy)] = 1

    def _build_clearance(self):
        """Chanfrein : les cellules hors matiere valent 0, le reste s'en eloigne."""
        inf = 1.0e9
        distance = [0.0 if not self.inside[i] else inf
                    for i in range(self.nx * self.ny)]
        diagonal = math.sqrt(2.0)
        nx = self.nx
        for iy in range(self.ny):
            for ix in range(nx):
                position = iy * nx + ix
                valeur = distance[position]
                if valeur == 0.0:
                    continue
                if ix > 0:
                    valeur = min(valeur, distance[position - 1] + 1.0)
                if iy > 0:
                    valeur = min(valeur, distance[position - nx] + 1.0)
                    if ix > 0:
                        valeur = min(valeur, distance[position - nx - 1] + diagonal)
                    if ix + 1 < nx:
                        valeur = min(valeur, distance[position - nx + 1] + diagonal)
                distance[position] = valeur
        for iy in range(self.ny - 1, -1, -1):
            for ix in range(nx - 1, -1, -1):
                position = iy * nx + ix
                valeur = distance[position]
                if valeur == 0.0:
                    continue
                if ix + 1 < nx:
                    valeur = min(valeur, distance[position + 1] + 1.0)
                if iy + 1 < self.ny:
                    valeur = min(valeur, distance[position + nx] + 1.0)
                    if ix + 1 < nx:
                        valeur = min(valeur, distance[position + nx + 1] + diagonal)
                    if ix > 0:
                        valeur = min(valeur, distance[position + nx - 1] + diagonal)
                distance[position] = valeur
        self.clearance = [valeur * self.cell if valeur < inf else 0.0
                          for valeur in distance]
