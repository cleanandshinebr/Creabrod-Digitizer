"""Primitives de planification du parcours de remplissage (etape B1).

Objectif
--------
Ce module ne remplace pas le moteur de remplissage et n'est branche nulle part.
Il fournit les briques necessaires pour **verifier avant de coudre** qu'une
rangee peut etre ajoutee sans rendre le parcours impossible, et pour qualifier
la liaison (couture de reprise) qui relie deux zones.

Vocabulaire (a ne pas confondre)
--------------------------------
* **Saut** : deplacement machine aiguille levee, hors matiere, qui laisse un
  fil non coupe. Ce module n'en produit jamais : il ne modelise que des
  liaisons *cousues*.
* **Couture de reprise** : liaison cousue entre deux zones. Elle peut etre
  *propre* (dans la matiere, loin des bords) ou *visible* (elle sort de la
  matiere, longe un bord ou rase une zone deja cousue).
* **Sous-couche de stabilisation** : couche volontaire cousue sous le motif
  (contour, colonne...). Ce n'est ni un saut ni une reprise : ce module ne la
  traite pas et ne doit pas servir a la justifier.

Modele geometrique
------------------
* ``material`` = interieur du contour moins les trous explicites.
* ``void`` = espace hors matiere (creux concave, exterieur), traverse
  uniquement par une liaison signalee comme visible.
* Les coutures deja realisees forment une **barriere** : chaque rangee cousue
  est dilatee de ``seam_radius = 0.45 x spacing``. Ce rayon est volontairement
  inferieur a ``spacing / 2`` pour laisser passer la reprise courte entre deux
  rangees voisines ; il reste assez large pour interdire de traverser une
  rangee cousue.
* Une rangee restante est :
  - ``direct`` : joignable dans la matiere sans traverser de couture (la
    longueur du trajet dans la matiere n'est pas bornee : c'est un
    deplacement normal dans la zone libre) ;
  - ``via_void`` : joignable seulement en quittant la matiere (liaison
    visible, longueur totale <= ``max_link``) ;
  - ``blocked`` : ni l'un ni l'autre — aucune liaison dans la matiere et
    aucune liaison visible assez courte.
* Un ``blocked`` n'est pas toujours une impossibilite topologique absolue :
  c'est le refus d'une liaison absente, trop longue ou visible. Cette
  distinction est volontaire et documentee ; le planificateur (etape B2) doit
  la traiter comme une erreur explicite, jamais comme un saut silencieux.

Ce qui est garanti par construction
-----------------------------------
* La grille interdit les cellules des coutures et des trous ; une liaison
  retournee est verifiee par echantillonnage fin (0,25 mm) : aucun point
  echantillonne hors extremites n'approche une couture existante a moins de
  ``seam_radius``, et aucun ne penetre dans un trou.
* Les liaisons retournees sont continues (points consecutifs <= ``max_step``)
  et commencent/terminent exactement aux points demandes.
* Les cas ou aucune liaison n'existe renvoient ``None`` ou le statut
  ``blocked`` ; ils ne fabriquent jamais de trajet artificiel.

Hypotheses et limites (a lire avant d'utiliser le module)
---------------------------------------------------------
* Unites : millimetres, repere du motif.
* Le contour doit etre ferme, simple (non auto-intersectant) et ses trous
  doivent etre inclus dans le contour. Aucune reparation n'est faite.
* La grille est conservative mais *approchee* : une cellule est bloquee des
  qu'elle touche la barriere ou la bande de bord. Deux maillages differents
  peuvent classer differemment une rangee limite. Les seuils par defaut
  (``border_clearance = 1.5``, ``cell ~ spacing / 3``) sont un compromis ; ils
  sont parametrables et doivent etre valides sur les motifs reels.
* ``max_link`` est un **seuil de qualite**, pas une loi geometrique : une
  liaison de 21 mm n'est pas plus impossible qu'une liaison de 19 mm. Le seuil
  par defaut (20 mm) est un choix de conception a ajuster avec l'utilisateur.
* Les coutures de reprise qui sortent de la matiere sont signalees
  (``visible``) et refusees par defaut (``allow_visible = False``). Elles ne
  sont jamais considerees automatiquement comme acceptables.
* Le module ne verifie pas la densite, la compensation, la longueur de point
  machine, ni la lisibilite du motif. Il ne remplace aucun test de rendu.
* Geometries impossibles ou non traitees : contour ouvert, contour
  auto-intersectant, trou deborde, matiere plus etroite que la maille, zone
  totalement entouree de coutures, arrivee deja cousue avant la fin du bloc.
* Aucune garantie universelle de continuite n'est apportee : le module rend le
  defaut *visible et mesurable* (statut, longueur, drapeaux), il ne le supprime
  pas pour toutes les geometries.

Non inclus dans B1
------------------
Aucun branchement dans ``fill.py`` / ``engine.py``, aucune suppression de la
reserve d'arrivee, aucun changement d'algorithme, aucune interface graphique.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Iterable, Sequence

Point = tuple[float, float]
Row = tuple[Point, Point]

EPSILON = 1e-9
INF = math.inf

#: Ecart de remplissage par defaut (mm).
DEFAULT_SPACING_MM = 2.0
#: Marge minimale entre un deplacement et le bord du motif (mm).
DEFAULT_BORDER_CLEARANCE_MM = 1.5
#: Longueur maximale d'une liaison consideree comme acceptable (mm).
DEFAULT_MAX_LINK_MM = 20.0
#: Nombre maximal de cellules de la grille (garde-fou memoire/temps).
DEFAULT_GRID_MAX_CELLS = 200_000
#: Taille minimale d'une cellule (mm).
GRID_CELL_MIN_MM = 0.30
#: Rayon de barriere des coutures, en fraction de l'ecart.
SEAM_RADIUS_FACTOR = 0.45
#: Marge minimale autour du contour pour les trajets exterieurs (mm).
ROUTING_MARGIN_MIN_MM = 12.0
#: Sur-cout des cellules hors matiere et proches du bord dans le routage.
ROUTING_VOID_COST = 12.0
ROUTING_BORDER_COST = 3.0
#: Seuil de longueur de bord rase / de couture rasee pour lever un drapeau.
#: Un demi-tour ou une approche de rangee peut longer le bord sur quelques
#: millimetres sans etre une liaison visible ; au-dela, c'en est une.
RIDE_LENGTH_FACTOR = 4.0  # x spacing
#: Longueur maximale d'un demi-tour de bord entre deux rangees voisines.
TURN_MAX_FACTOR = 3.0  # x spacing


# ---------------------------------------------------------------------------
# Geometrie de base (autonome : aucun import du moteur, pas de cycle en B2)
# ---------------------------------------------------------------------------


def _closed_polygon(points: Iterable[Point]) -> tuple[Point, ...]:
    polygon = [(float(x), float(y)) for x, y in points]
    if len(polygon) < 3:
        raise ValueError("Un polygone doit contenir au moins 3 points.")
    if polygon[0] != polygon[-1]:
        polygon.append(polygon[0])
    return tuple(polygon)


def _edges(polygon: Sequence[Point]) -> list[tuple[Point, Point]]:
    return [(polygon[i], polygon[i + 1]) for i in range(len(polygon) - 1)]


def _bbox(points: Iterable[Point]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _span_intersections(edges: Sequence[tuple[Point, Point]], y: float) -> list[float]:
    xs: list[float] = []
    for (x1, y1), (x2, y2) in edges:
        if (y1 <= y < y2) or (y2 <= y < y1):
            xs.append(x1 + (x2 - x1) * (y - y1) / (y2 - y1))
    xs.sort()
    return xs


def _span_pairs(edges: Sequence[tuple[Point, Point]], y: float) -> list[tuple[float, float]]:
    xs = _span_intersections(edges, y)
    return [(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2) if xs[i + 1] > xs[i]]


def _in_spans(x: float, spans: Sequence[tuple[float, float]]) -> bool:
    for start, end in spans:
        if start <= x < end:
            return True
    return False


def _point_in_polygon(x: float, y: float, edges: Sequence[tuple[Point, Point]]) -> bool:
    inside = False
    for (x1, y1), (x2, y2) in edges:
        if (y1 > y) != (y2 > y):
            if x1 + (x2 - x1) * (y - y1) / (y2 - y1) > x:
                inside = not inside
    return inside


def _point_segment_distance(px: float, py: float, ax: float, ay: float,
                            bx: float, by: float) -> float:
    dx = bx - ax
    dy = by - ay
    length_sq = dx * dx + dy * dy
    if length_sq <= EPSILON:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / length_sq
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _point_on_segment_exact(px: float, py: float,
                            ax: float, ay: float,
                            bx: float, by: float) -> bool:
    """Vrai si (px, py) est exactement sur le segment [a, b], sans tolerance.

    Les bornes inclusives traitent les segments horizontaux et verticaux.
    Pour un segment oblique, la colinearite est calculee en rationnels exacts
    construits sur les flottants fournis : aucun epsilon n'est introduit.
    Une arete degeneree (a == b) est traitee comme un point de frontiere.
    """
    if not (math.isfinite(px) and math.isfinite(py)
            and math.isfinite(ax) and math.isfinite(ay)
            and math.isfinite(bx) and math.isfinite(by)):
        return False
    if ax == bx:
        return px == ax and min(ay, by) <= py <= max(ay, by)
    if ay == by:
        return py == ay and min(ax, bx) <= px <= max(ax, bx)
    if not (min(ax, bx) <= px <= max(ax, bx)
            and min(ay, by) <= py <= max(ay, by)):
        return False
    cross = ((Fraction(bx) - Fraction(ax)) * (Fraction(py) - Fraction(ay))
             - (Fraction(by) - Fraction(ay)) * (Fraction(px) - Fraction(ax)))
    return cross == 0


def _orientation(ax: float, ay: float, bx: float, by: float,
                 cx: float, cy: float) -> int:
    value = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    if abs(value) <= 1e-12:
        return 0
    return 1 if value > 0 else -1


def _on_segment(ax: float, ay: float, bx: float, by: float,
                px: float, py: float) -> bool:
    return (min(ax, bx) - EPSILON <= px <= max(ax, bx) + EPSILON
            and min(ay, by) - EPSILON <= py <= max(ay, by) + EPSILON)


def _segments_intersect(a: Point, b: Point, c: Point, d: Point) -> bool:
    o1 = _orientation(*a, *b, *c)
    o2 = _orientation(*a, *b, *d)
    o3 = _orientation(*c, *d, *a)
    o4 = _orientation(*c, *d, *b)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and _on_segment(*a, *b, *c):
        return True
    if o2 == 0 and _on_segment(*a, *b, *d):
        return True
    if o3 == 0 and _on_segment(*c, *d, *a):
        return True
    if o4 == 0 and _on_segment(*c, *d, *b):
        return True
    return False


def _segments_distance(a: Point, b: Point, c: Point, d: Point) -> float:
    if _segments_intersect(a, b, c, d):
        return 0.0
    return min(
        _point_segment_distance(*a, *c, *d),
        _point_segment_distance(*b, *c, *d),
        _point_segment_distance(*c, *a, *b),
        _point_segment_distance(*d, *a, *b),
    )


def _polyline_length(points: Sequence[Point]) -> float:
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:]))


def _sample_polyline(points: Sequence[Point], step: float) -> list[tuple[float, float, float]]:
    """Echantillonne une polyligne : (x, y, abscisse curviligne)."""
    if len(points) < 2:
        return [(points[0][0], points[0][1], 0.0)] if points else []
    step = max(step, 0.05)
    samples: list[tuple[float, float, float]] = []
    travelled = 0.0
    for a, b in zip(points, points[1:]):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        if length <= EPSILON:
            continue
        count = max(1, int(math.ceil(length / step)))
        for index in range(count):
            t = index / count
            samples.append((a[0] + (b[0] - a[0]) * t,
                            a[1] + (b[1] - a[1]) * t,
                            travelled + length * t))
        travelled += length
    samples.append((points[-1][0], points[-1][1], travelled))
    return samples


def _subdivide(points: Sequence[Point], max_step: float) -> tuple[Point, ...]:
    if max_step <= 0 or len(points) < 2:
        return tuple((float(x), float(y)) for x, y in points)
    result: list[Point] = [(float(points[0][0]), float(points[0][1]))]
    for a, b in zip(points, points[1:]):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        count = max(1, int(math.ceil(length / max_step)))
        for index in range(1, count + 1):
            t = index / count
            result.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return tuple(result)


# ---------------------------------------------------------------------------
# Espace de travail et grille
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Workspace:
    """Matiere, trous et parametres de verification.

    ``outer`` doit etre ferme (ou sera ferme automatiquement). ``holes`` sont
    des polygones fermes inclus dans ``outer``.
    """

    outer: Sequence[Point]
    holes: Sequence[Sequence[Point]] = ()
    spacing: float = DEFAULT_SPACING_MM
    border_clearance: float = DEFAULT_BORDER_CLEARANCE_MM
    max_link: float = DEFAULT_MAX_LINK_MM
    grid_max_cells: int = DEFAULT_GRID_MAX_CELLS
    cell: float = 0.0  # 0 = taille automatique
    seam_radius_factor: float = SEAM_RADIUS_FACTOR
    _cache: dict = field(default_factory=dict, compare=False, repr=False)

    def __post_init__(self) -> None:
        outer = _closed_polygon(self.outer)
        holes = tuple(_closed_polygon(hole) for hole in self.holes)
        spacing = float(self.spacing)
        clearance = float(self.border_clearance)
        max_link = float(self.max_link)
        factor = float(self.seam_radius_factor)
        if not math.isfinite(spacing) or spacing <= 0:
            raise ValueError("L'ecart de remplissage doit etre strictement positif.")
        if not math.isfinite(clearance) or clearance < 0:
            raise ValueError("La marge de bordure doit etre positive ou nulle.")
        if not math.isfinite(max_link) or max_link <= 0:
            raise ValueError("La longueur maximale de liaison doit etre positive.")
        if not math.isfinite(factor) or not 0.0 < factor < 0.5:
            raise ValueError("Le facteur de rayon de couture doit etre dans ]0 ; 0,5[.")
        if int(self.grid_max_cells) < 1_000:
            raise ValueError("La grille doit autoriser au moins 1000 cellules.")
        x0, y0, x1, y1 = _bbox(outer)
        if x1 - x0 <= EPSILON or y1 - y0 <= EPSILON:
            raise ValueError("Le contour doit avoir une surface non nulle.")
        cell = float(self.cell)
        if cell <= 0:
            cell = max(GRID_CELL_MIN_MM, spacing / 3.0)
        cell = max(cell, GRID_CELL_MIN_MM)
        margin = max(max_link, ROUTING_MARGIN_MIN_MM)
        while ((x1 - x0 + 2 * margin) / cell + 2) * ((y1 - y0 + 2 * margin) / cell + 2) > self.grid_max_cells:
            cell *= 1.2
        object.__setattr__(self, "outer", outer)
        object.__setattr__(self, "holes", holes)
        object.__setattr__(self, "spacing", spacing)
        object.__setattr__(self, "border_clearance", clearance)
        object.__setattr__(self, "max_link", max_link)
        object.__setattr__(self, "cell", cell)
        object.__setattr__(self, "seam_radius_factor", factor)

    @property
    def seam_radius(self) -> float:
        """Rayon de barriere autour d'une couture deja realisee."""
        return self.spacing * self.seam_radius_factor

    def grid(self) -> "_Grid":
        grid = self._cache.get("grid")
        if grid is None:
            grid = _Grid(self)
            self._cache["grid"] = grid
        return grid

    def contains(self, point: Point) -> bool:
        """Vrai si le point est dans la matiere (hors trous)."""
        x, y = point
        outer_edges = _edges(self.outer)
        if not _point_in_polygon(x, y, outer_edges):
            return False
        for hole in self.holes:
            if _point_in_polygon(x, y, _edges(hole)):
                return False
        return True

    def in_hole(self, point: Point) -> bool:
        x, y = point
        return any(_point_in_polygon(x, y, _edges(hole)) for hole in self.holes)

    def distance_to_border(self, point: Point) -> float:
        x, y = point
        best = INF
        for polygon in (self.outer, *self.holes):
            for a, b in _edges(polygon):
                best = min(best, _point_segment_distance(x, y, *a, *b))
        return best


def _material_point_status(workspace: Workspace, point: Point) -> str:
    """Classe un point selon la regle de frontiere du planificateur.

    Renvoie "interieur", "contour_exterieur", "trou", "bord_trou",
    "hors_contour" ou "non_fini". La frontiere d'un trou est prioritaire sur
    le contour exterieur : un point sur le bord d'un trou est refuse meme si
    le trou touche le contour. Un point sur le contour exterieur hors trous
    est accepte.
    """
    x, y = point
    if not (math.isfinite(x) and math.isfinite(y)):
        return "non_fini"

    on_hole = any(
        _point_on_segment_exact(x, y, *a, *b)
        for hole in workspace.holes
        for a, b in _edges(hole)
    )
    if on_hole:
        return "bord_trou"
    if workspace.in_hole(point):
        return "trou"

    on_outer = any(
        _point_on_segment_exact(x, y, *a, *b)
        for a, b in _edges(workspace.outer)
    )
    if on_outer:
        return "contour_exterieur"
    if workspace.contains(point):
        return "interieur"
    return "hors_contour"


_DIRECTIONS = (
    (1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
    (1, 1, math.sqrt(2.0)), (1, -1, math.sqrt(2.0)),
    (-1, 1, math.sqrt(2.0)), (-1, -1, math.sqrt(2.0)),
)


class _Grid:
    """Grille conservative : matiere, bande de bord, barrieres, Dijkstra."""

    def __init__(self, workspace: Workspace):
        self.cell: float = workspace.cell
        margin = max(workspace.max_link, ROUTING_MARGIN_MIN_MM)
        x0, y0, x1, y1 = _bbox(workspace.outer)
        self.x0 = x0 - margin
        self.y0 = y0 - margin
        self.nx = int(math.ceil((x1 - x0 + 2 * margin) / self.cell)) + 1
        self.ny = int(math.ceil((y1 - y0 + 2 * margin) / self.cell)) + 1
        self.outer_edges = _edges(workspace.outer)
        self.hole_edges = [_edges(hole) for hole in workspace.holes]
        self.count = self.nx * self.ny
        self.in_material = bytearray(self.count)
        self.in_hole = bytearray(self.count)
        self.near_border = bytearray(self.count)
        self._cost_cache: dict[tuple[float, float], list[float]] = {}
        self._build_material()
        self._build_border_band(workspace.border_clearance + self.cell)

    # -- construction -----------------------------------------------------

    def _build_material(self) -> None:
        nx, ny, cell = self.nx, self.ny, self.cell
        x0, y0 = self.x0, self.y0
        for iy in range(ny):
            y = y0 + (iy + 0.5) * cell
            spans = _span_pairs(self.outer_edges, y)
            if not spans:
                continue
            hole_spans = [span for span in
                          (_span_pairs(edges, y) for edges in self.hole_edges) if span]
            base = iy * nx
            for ix in range(nx):
                x = x0 + (ix + 0.5) * cell
                if not _in_spans(x, spans):
                    continue
                index = base + ix
                if any(_in_spans(x, span) for span in hole_spans):
                    self.in_hole[index] = 1
                    continue
                self.in_material[index] = 1

    def _build_border_band(self, radius: float) -> None:
        for a, b in self.outer_edges:
            self._rasterize_edge(a, b, radius, self.near_border)
        for edges in self.hole_edges:
            for a, b in edges:
                self._rasterize_edge(a, b, radius, self.near_border)

    def _rasterize_edge(self, a: Point, b: Point, radius: float,
                        target: bytearray) -> None:
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        steps = max(1, int(math.ceil(length / (self.cell * 0.5))))
        for index in range(steps + 1):
            t = index / steps
            self._mark_disc(a[0] + (b[0] - a[0]) * t,
                            a[1] + (b[1] - a[1]) * t, radius, target)

    def _mark_disc(self, x: float, y: float, radius: float,
                   target: bytearray) -> None:
        cell = self.cell
        ix0 = max(0, int((x - radius - self.x0) / cell))
        ix1 = min(self.nx - 1, int((x + radius - self.x0) / cell) + 1)
        iy0 = max(0, int((y - radius - self.y0) / cell))
        iy1 = min(self.ny - 1, int((y + radius - self.y0) / cell) + 1)
        radius_sq = radius * radius
        for iy in range(iy0, iy1 + 1):
            dy = self.y0 + (iy + 0.5) * cell - y
            base = iy * self.nx
            for ix in range(ix0, ix1 + 1):
                dx = self.x0 + (ix + 0.5) * cell - x
                if dx * dx + dy * dy <= radius_sq:
                    target[base + ix] = 1

    # -- requetes ---------------------------------------------------------

    def center(self, index: int) -> Point:
        return (self.x0 + (index % self.nx + 0.5) * self.cell,
                self.y0 + (index // self.nx + 0.5) * self.cell)

    def cell_index(self, x: float, y: float) -> int | None:
        ix = int((x - self.x0) / self.cell)
        iy = int((y - self.y0) / self.cell)
        if 0 <= ix < self.nx and 0 <= iy < self.ny:
            return iy * self.nx + ix
        return None

    def sewn_mask(self, sewn: Sequence[Row], radius: float) -> bytearray:
        mask = bytearray(self.count)
        for row in sewn:
            self.add_sewn(mask, row, radius)
        return mask

    def add_sewn(self, mask: bytearray, segment: Row, radius: float) -> list[int]:
        """Ajoute une couture (dilatee) a un masque de barriere existant.

        Renvoie les cellules nouvellement bloquees (aucune duplication), ce
        qui permet de tenir a jour des masques de matiere libre sans les
        reconstruire entierement a chaque etape du plan.
        """
        cell = self.cell
        a, b = segment
        ax, ay = a
        bx, by = b
        added: list[int] = []
        ix0 = max(0, int((min(ax, bx) - radius - self.x0) / cell))
        ix1 = min(self.nx - 1, int((max(ax, bx) + radius - self.x0) / cell) + 1)
        iy0 = max(0, int((min(ay, by) - radius - self.y0) / cell))
        iy1 = min(self.ny - 1, int((max(ay, by) + radius - self.y0) / cell) + 1)
        for iy in range(iy0, iy1 + 1):
            cy = self.y0 + (iy + 0.5) * cell
            base = iy * self.nx
            for ix in range(ix0, ix1 + 1):
                index = base + ix
                if mask[index]:
                    continue
                cx = self.x0 + (ix + 0.5) * cell
                if _point_segment_distance(cx, cy, ax, ay, bx, by) <= radius:
                    mask[index] = 1
                    added.append(index)
        return added

    def material_mask(self, sewn: Sequence[Row], seam_radius: float,
                      barrier: bytearray | None = None) -> bytearray:
        """Matiere libre : ni couture, ni trou.

        La marge de bordure n'est pas retiree ici : une rangee proche du bord
        reste accessible. Le fait de *longer* le bord est signale par les
        drapeaux de :func:`route_transition`, pas par ce masque.
        """
        barrier = (self.sewn_mask(sewn, seam_radius)
                   if barrier is None else barrier)
        mask = bytearray(self.count)
        in_material = self.in_material
        for index in range(self.count):
            if in_material[index] and not barrier[index]:
                mask[index] = 1
        return mask

    def total_mask(self, sewn: Sequence[Row], seam_radius: float,
                   barrier: bytearray | None = None) -> bytearray:
        barrier = (self.sewn_mask(sewn, seam_radius)
                   if barrier is None else barrier)
        mask = bytearray(self.count)
        in_hole = self.in_hole
        for index in range(self.count):
            if not in_hole[index] and not barrier[index]:
                mask[index] = 1
        return mask

    def seed_cells(self, free: bytearray, point: Point,
                   radius: float) -> list[tuple[int, float]]:
        """Cellules libres reliees au point, sans traverser de barriere.

        Un simple disque autour de l'aiguille ne suffit pas : il peut sauter
        un mur fin et ensemencer une poche fermee. On part donc des cellules
        libres les plus proches, puis on propage dans ``free`` jusqu'a
        ``radius``. La matiere est preferee au vide pour l'aiguille posee sur
        une rangee cousue.
        """
        cell = self.cell
        initial_radius = max(2.0 * cell, 1.2)
        initial_radius = min(initial_radius, radius)
        while True:
            closest = self._free_cells_in_disc(free, point, initial_radius)
            if closest or initial_radius >= radius - EPSILON:
                break
            initial_radius = min(radius, initial_radius * 1.5)
        if not closest:
            return []
        x, y = point
        starts = []
        for index in closest:
            cx, cy = self.center(index)
            starts.append((index, math.hypot(cx - x, cy - y)))
        distances = self.dijkstra(free, starts, budget=radius)
        material_seeds: list[tuple[int, float]] = []
        void_seeds: list[tuple[int, float]] = []
        for index, distance in enumerate(distances):
            if not math.isfinite(distance):
                continue
            if self.in_material[index]:
                material_seeds.append((index, distance))
            else:
                void_seeds.append((index, distance))
        return material_seeds or void_seeds

    def _free_cells_in_disc(self, free: bytearray, point: Point,
                            radius: float) -> list[int]:
        x, y = point
        cell = self.cell
        ix0 = max(0, int((x - radius - self.x0) / cell))
        ix1 = min(self.nx - 1, int((x + radius - self.x0) / cell) + 1)
        iy0 = max(0, int((y - radius - self.y0) / cell))
        iy1 = min(self.ny - 1, int((y + radius - self.y0) / cell) + 1)
        found: list[tuple[float, int]] = []
        for iy in range(iy0, iy1 + 1):
            cy = self.y0 + (iy + 0.5) * cell
            base = iy * self.nx
            for ix in range(ix0, ix1 + 1):
                index = base + ix
                if not free[index]:
                    continue
                cx = self.x0 + (ix + 0.5) * cell
                distance = math.hypot(cx - x, cy - y)
                if distance <= radius:
                    found.append((distance, index))
        found.sort()
        return [index for _, index in found]

    def nearest_free(self, free: bytearray, point: Point,
                     max_radius: float) -> int | None:
        seeds = self.seed_cells(free, point, max_radius)
        if not seeds:
            return None
        return min(seeds, key=lambda item: item[1])[0]

    # -- plus courts chemins ---------------------------------------------

    def dijkstra(self, free: bytearray, seeds: Sequence[tuple[int, float]],
                 budget: float = INF) -> list[float]:
        """Distance depuis les graines dans ``free`` ; ``inf`` si inaccessible."""
        count = self.count
        dist = [INF] * count
        heap: list[tuple[float, int]] = []
        for index, distance in seeds:
            if free[index] and distance < dist[index]:
                dist[index] = distance
                heapq.heappush(heap, (distance, index))
        nx, ny, cell = self.nx, self.ny, self.cell
        while heap:
            distance, index = heapq.heappop(heap)
            if distance > dist[index]:
                continue
            if distance > budget:
                break
            ix = index % nx
            iy = index // nx
            for dx, dy, weight in _DIRECTIONS:
                jx = ix + dx
                jy = iy + dy
                if jx < 0 or jx >= nx or jy < 0 or jy >= ny:
                    continue
                neighbour = jy * nx + jx
                if not free[neighbour]:
                    continue
                candidate = distance + weight * cell
                if candidate < dist[neighbour] and candidate <= budget:
                    dist[neighbour] = candidate
                    heapq.heappush(heap, (candidate, neighbour))
        return dist

    def row_distance(self, row: Row, free: bytearray,
                     dist: Sequence[float]) -> float:
        """Distance minimale entre la rangee et les cellules accessibles.

        La rangee est echantillonnee au pas de la maille ; on regarde d'abord
        la cellule elle-meme (elle est libre tant que la rangee n'est pas
        cousue), puis le voisinage seulement si elle ne l'est pas. Cela evite
        un balayage 3x3 systematique sur toutes les rangees a chaque etape.
        """
        (ax, ay), (bx, by) = row
        length = math.hypot(bx - ax, by - ay)
        steps = max(1, int(math.ceil(length / self.cell)))
        best = INF
        nx = self.nx
        for step in range(steps + 1):
            t = step / steps
            index = self.cell_index(ax + (bx - ax) * t, ay + (by - ay) * t)
            if index is None:
                continue
            if free[index]:
                value = dist[index]
                if value < best:
                    best = value
                continue
            ix = index % nx
            iy = index // nx
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    jx = ix + dx
                    jy = iy + dy
                    if 0 <= jx < nx and 0 <= jy < self.ny:
                        neighbour = jy * nx + jx
                        if free[neighbour] and dist[neighbour] < best:
                            best = dist[neighbour]
        return best

    def cost_field(self, void_cost: float, border_cost: float) -> list[float]:
        """Cout par cellule : preferer la matiere et eviter les bords."""
        key = (void_cost, border_cost)
        cached = self._cost_cache.get(key)
        if cached is not None:
            return cached
        costs = [1.0] * self.count
        in_material = self.in_material
        near_border = self.near_border
        for index in range(self.count):
            if not in_material[index]:
                costs[index] = void_cost * (border_cost if near_border[index] else 1.0)
            elif near_border[index]:
                costs[index] = border_cost
        self._cost_cache[key] = costs
        return costs

    def astar(self, free: bytearray, cell_costs: Sequence[float], source: int,
              target: int, max_length: float) -> tuple[list[int], float] | None:
        """A* sur la grille ; renvoie (cellules, longueur) ou None."""
        count = self.count
        g_cost = [INF] * count
        lengths = [INF] * count
        parents = [-1] * count
        tx, ty = self.center(target)
        g_cost[source] = 0.0
        lengths[source] = 0.0
        heap: list[tuple[float, float, int]] = []
        heapq.heappush(heap, (0.0, 0.0, source))
        nx, ny, cell = self.nx, self.ny, self.cell
        while heap:
            _, length, index = heapq.heappop(heap)
            if length > lengths[index] + EPSILON:
                continue
            if index == target:
                path = [index]
                while parents[path[-1]] != -1:
                    path.append(parents[path[-1]])
                path.reverse()
                return path, lengths[index]
            ix = index % nx
            iy = index // nx
            for dx, dy, weight in _DIRECTIONS:
                jx = ix + dx
                jy = iy + dy
                if jx < 0 or jx >= nx or jy < 0 or jy >= ny:
                    continue
                neighbour = jy * nx + jx
                if not free[neighbour]:
                    continue
                step = weight * cell
                new_length = length + step
                if new_length > max_length:
                    continue
                new_cost = (g_cost[index]
                            + step * (cell_costs[index] + cell_costs[neighbour]) * 0.5)
                if new_cost + 1e-12 < g_cost[neighbour]:
                    g_cost[neighbour] = new_cost
                    lengths[neighbour] = new_length
                    parents[neighbour] = index
                    heuristic = math.hypot(self.x0 + (jx + 0.5) * cell - tx,
                                           self.y0 + (jy + 0.5) * cell - ty)
                    heapq.heappush(heap, (new_cost + heuristic, new_length, neighbour))
        return None


# ---------------------------------------------------------------------------
# Analyse d'accessibilite
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RowState:
    """Etat d'une rangee restante apres simulation.

    ``direct``    : joignable dans la matiere sans traverser de couture ;
    ``via_void``  : joignable seulement par une liaison visible (<= max_link) ;
    ``blocked``   : aucune liaison dans la matiere, aucune liaison visible
                    assez courte.
    """

    row: Row
    status: str
    distance: float

    @property
    def blocked(self) -> bool:
        return self.status == "blocked"

    @property
    def visible(self) -> bool:
        return self.status == "via_void"


def _seed_set(grid: _Grid, free: bytearray, position: Point,
              spacing: float) -> list[tuple[int, float]]:
    """Graines autour de l'aiguille (elle est souvent sur une rangee cousue)."""
    radius = 2.0 * spacing + grid.cell
    seeds = grid.seed_cells(free, position, radius)
    if not seeds:
        seeds = grid.seed_cells(free, position, 4.0 * spacing + grid.cell)
    return seeds


def analyse_rows(workspace: Workspace, sewn: Sequence[Row], rows: Sequence[Row],
                 position: Point, *, seam_radius: float | None = None,
                 budget: float | None = None,
                 material: bytearray | None = None,
                 free: bytearray | None = None,
                 barrier: bytearray | None = None,
                 seeds: Sequence[tuple[int, float]] | None = None) -> tuple[RowState, ...]:
    """Classe chaque rangee restante par rapport a l'aiguille.

    Les coutures ``sewn`` forment la barriere. ``position`` est l'aiguille
    (fin de la derniere couture). L'analyse ne modifie rien et ne decide rien :
    elle rend des statuts et des longueurs.

    ``material`` / ``free`` / ``barrier`` permettent au planificateur de
    reutiliser des masques deja calcules (optimisation ; ils doivent
    correspondre a ``sewn``). ``seeds`` permet de fournir explicitement les
    cellules de depart (le planificateur y ajoute les deux cotes de la rangee
    qu'il vient de coudre).
    """
    grid = workspace.grid()
    radius = workspace.seam_radius if seam_radius is None else float(seam_radius)
    limit = workspace.max_link if budget is None else float(budget)
    material = (grid.material_mask(sewn, radius, barrier)
                if material is None else material)
    if seeds is None:
        seeds = _seed_set(grid, material, position, workspace.spacing)
    distances = grid.dijkstra(material, seeds) if seeds else None
    states: dict[int, RowState] = {}
    pending: list[tuple[int, Row]] = []
    for order, row in enumerate(rows):
        distance = grid.row_distance(row, material, distances) if distances else INF
        if math.isfinite(distance):
            states[order] = RowState(row, "direct", distance)
        else:
            pending.append((order, row))
    if pending:
        total = (grid.total_mask(sewn, radius, barrier)
                 if free is None else free)
        total_seeds = (seeds if seeds
                       else _seed_set(grid, total, position, workspace.spacing))
        total_distances = (grid.dijkstra(total, total_seeds, budget=limit)
                           if total_seeds else None)
        for order, row in pending:
            distance = (grid.row_distance(row, total, total_distances)
                        if total_distances else INF)
            if math.isfinite(distance) and distance <= limit + EPSILON:
                states[order] = RowState(row, "via_void", distance)
            else:
                states[order] = RowState(row, "blocked", INF)
    return tuple(states[order] for order in range(len(rows)))


def blocked_rows(states: Sequence[RowState]) -> tuple[Row, ...]:
    return tuple(state.row for state in states if state.status == "blocked")


def visible_rows(states: Sequence[RowState]) -> tuple[RowState, ...]:
    return tuple(state for state in states if state.status == "via_void")


def _approach_segments(position: Point, start: Point) -> tuple[Row, ...]:
    if math.hypot(start[0] - position[0], start[1] - position[1]) <= EPSILON:
        return ()
    return ((position, start),)


def candidate_blocks_rows(workspace: Workspace, sewn: Sequence[Row],
                          candidate: Row, remaining: Sequence[Row],
                          position: Point, *,
                          approach: Sequence[Point] | None = None,
                          seam_radius: float | None = None,
                          budget: float | None = None) -> tuple[Row, ...]:
    """Rangees qui deviendraient ``blocked`` si l'on cousait ``candidate``.

    L'approche est modelisee comme une barriere (droite par defaut, ou
    polyligne ``approach`` allant de ``position`` au debut de la rangee). Cette
    verification est volontairement conservatrice : une approche visible doit
    etre qualifiee separement avec :func:`route_transition`.
    """
    start, end = candidate
    if math.hypot(position[0] - end[0], position[1] - end[1]) < math.hypot(
            position[0] - start[0], position[1] - start[1]):
        start, end = end, start
    if approach is not None:
        points = tuple(approach)
        if not points:
            raise ValueError("L'approche fournie est vide.")
        if math.hypot(points[-1][0] - start[0], points[-1][1] - start[1]) > 1e-6:
            raise ValueError("L'approche doit se terminer au debut de la rangee.")
        segments = tuple(zip(points, points[1:]))
    else:
        segments = _approach_segments(position, start)
    barrier = list(sewn)
    barrier.append((start, end))
    barrier.extend(segments)
    targets = [row for row in remaining
               if not (row == candidate or (row[0] == candidate[1] and row[1] == candidate[0]))]
    states = analyse_rows(workspace, barrier, targets, end,
                          seam_radius=seam_radius, budget=budget)
    return blocked_rows(states)


# ---------------------------------------------------------------------------
# Liaisons (coutures de reprise)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TransitionRoute:
    """Liaison cousue entre deux points, qualifiee et verifiee.

    ``accepted`` est faux des qu'un drapeau est leve, sauf si l'appelant a
    explicitement autorise les liaisons visibles (``allow_visible=True``).
    """

    points: tuple[Point, ...]
    length: float
    crosses_void: bool
    rides_border: bool
    rides_seam: bool
    visible: bool
    accepted: bool
    reason: str
    turn: bool = False
    outside_length: float = 0.0

    def distances(self) -> list[float]:
        return [math.hypot(b[0] - a[0], b[1] - a[1])
                for a, b in zip(self.points, self.points[1:])]


def _classify(workspace: Workspace, points: Sequence[Point],
              sewn: Sequence[Row]) -> tuple[bool, bool, bool, float]:
    grid = workspace.grid()
    total = _polyline_length(points)
    skip = max(1.5, 2.0 * grid.cell)
    step = min(0.35, grid.cell * 0.5)
    samples = _sample_polyline(points, step)
    crosses_void = False
    border_length = 0.0
    seam_length = 0.0
    previous_arc = 0.0
    for x, y, arc in samples:
        index = grid.cell_index(x, y)
        interior = arc > skip and arc < total - skip
        if interior and (index is None or not grid.in_material[index]):
            crosses_void = True
        if not interior:
            previous_arc = arc
            continue
        delta = arc - previous_arc
        previous_arc = arc
        if index is not None and grid.near_border[index]:
            border_length += delta
        if sewn:
            closest = min(_point_segment_distance(x, y, *a, *b) for a, b in sewn)
            if closest < workspace.spacing:
                seam_length += delta
    threshold = workspace.spacing * RIDE_LENGTH_FACTOR
    return (crosses_void, border_length > threshold, seam_length > threshold, total)


def classify_link(workspace: Workspace, points: Sequence[Point],
                  sewn: Sequence[Row] = ()) -> tuple[bool, bool, bool, bool]:
    """Qualifie une polyligne sans la router.

    Renvoie ``(crosses_void, rides_border, rides_seam, visible)``.
    """
    crosses_void, rides_border, rides_seam, _ = _classify(
        workspace, points, sewn)
    return crosses_void, rides_border, rides_seam, (
        crosses_void or rides_border or rides_seam)


def _link_clear(sewn: Sequence[Row], points: Sequence[Point],
                seam_radius: float) -> bool:
    """Verification geometrique exacte : aucune couture traversee."""
    if not sewn:
        return True
    samples = _sample_polyline(points, 0.25)
    total = samples[-1][2] if samples else 0.0
    skip = 1.5
    tolerance = 1e-3
    for x, y, arc in samples:
        if arc <= skip or arc >= total - skip:
            continue
        for a, b in sewn:
            if _point_segment_distance(x, y, *a, *b) < seam_radius - tolerance:
                return False
    return True


def _line_of_sight(grid: _Grid, free: bytearray, a: Point, b: Point) -> bool:
    length = math.hypot(b[0] - a[0], b[1] - a[1])
    steps = max(1, int(math.ceil(length / (grid.cell * 0.5))))
    for index in range(steps + 1):
        t = index / steps
        cell = grid.cell_index(a[0] + (b[0] - a[0]) * t,
                               a[1] + (b[1] - a[1]) * t)
        if cell is None or not free[cell]:
            return False
    return True


def _simplify_cells(grid: _Grid, free: bytearray,
                    cells: Sequence[int]) -> list[Point]:
    """Simplifie un chemin de cellules par visibilite (glouton)."""
    if not cells:
        return []
    points = [grid.center(cell) for cell in cells]
    result = [points[0]]
    index = 0
    last = len(points) - 1
    while index < last:
        best = index + 1
        for candidate in range(last, index, -1):
            if _line_of_sight(grid, free, points[index], points[candidate]):
                best = candidate
                break
        result.append(points[best])
        index = best
    return result


def route_transition(workspace: Workspace, sewn: Sequence[Row], start: Point,
                     goal: Point, *, allow_visible: bool = False,
                     seam_radius: float | None = None,
                     max_step: float = 2.5,
                     max_length: float | None = None,
                     free: bytearray | None = None,
                     barrier: bytearray | None = None) -> TransitionRoute | None:
    """Cherche et qualifie une couture de reprise entre ``start`` et ``goal``.

    La liaison ne traverse aucune couture existante et aucun trou. Si elle
    quitte la matiere, longe un bord ou rase une couture, elle est marquee
    ``visible`` et refusee par defaut (``allow_visible=False``). Renvoie
    ``None`` quand aucune liaison geometriquement valide n'existe.

    ``free`` / ``barrier`` permettent de fournir des masques deja calcules
    (optimisation ; ils doivent correspondre a ``sewn``).
    """
    grid = workspace.grid()
    radius = workspace.seam_radius if seam_radius is None else float(seam_radius)
    free = grid.total_mask(sewn, radius, barrier) if free is None else free
    source = grid.nearest_free(free, start, 4.0 * workspace.spacing + grid.cell)
    target = grid.nearest_free(free, goal, 4.0 * workspace.spacing + grid.cell)
    if source is None or target is None:
        return None
    limit = max_length if max_length is not None else max(3.0 * workspace.max_link, 60.0)
    costs = grid.cost_field(ROUTING_VOID_COST, ROUTING_BORDER_COST)
    result = grid.astar(free, costs, source, target, limit)
    if result is None:
        return None
    cells, _ = result
    middle = _simplify_cells(grid, free, cells)
    points = [tuple(start)] + middle + [tuple(goal)]
    points = list(_subdivide(points, max_step))
    if not _link_clear(sewn, points, radius):
        return None
    crosses_void, rides_border, rides_seam, length = _classify(
        workspace, points, sewn)
    visible = crosses_void or rides_border or rides_seam
    if visible:
        reason = ("liaison visible (hors matiere)" if crosses_void else
                  "liaison le long d'un bord" if rides_border else
                  "liaison le long d'une couture")
    else:
        reason = "liaison dans la matiere"
    return TransitionRoute(
        points=tuple(points),
        length=length,
        crosses_void=crosses_void,
        rides_border=rides_border,
        rides_seam=rides_seam,
        visible=visible,
        accepted=(not visible) or bool(allow_visible),
        reason=reason,
    )


# ---------------------------------------------------------------------------
# Erreur explicite
# ---------------------------------------------------------------------------


class FillImpasseError(RuntimeError):
    """Aucune poursuite acceptable : l'erreur doit remonter, jamais un saut."""

    def __init__(self, message: str, *, row: Row | None = None,
                 position: Point | None = None,
                 blocked: Sequence[Row] = (),
                 states: Sequence[RowState] = ()):
        super().__init__(message)
        self.row = row
        self.position = position
        self.blocked = tuple(blocked)
        self.states = tuple(states)


def ensure_reachable(workspace: Workspace, sewn: Sequence[Row],
                     rows: Sequence[Row], position: Point, **kwargs) -> tuple[RowState, ...]:
    """Analyse les rangees et leve :class:`FillImpasseError` si l'une est bloquee."""
    states = analyse_rows(workspace, sewn, rows, position, **kwargs)
    blocked = blocked_rows(states)
    if blocked:
        count = len(blocked)
        raise FillImpasseError(
            f"{count} rangee(s) ne peuvent plus etre cousues sans traverser "
            "une couture existante ou une liaison visible trop longue.",
            position=position, blocked=blocked, states=states)
    return states

# ---------------------------------------------------------------------------
# Simulation complete du parcours (etape B1, validation avant B2)
# ---------------------------------------------------------------------------


def _row_length(row: Row) -> float:
    (ax, ay), (bx, by) = row
    return math.hypot(bx - ax, by - ay)


def _point_row_distance(point: Point, row: Row) -> float:
    (ax, ay), (bx, by) = row
    return _point_segment_distance(point[0], point[1], ax, ay, bx, by)


def _nearest_row(rows: Sequence[Row], point: Point) -> Row:
    return min(rows, key=lambda row: _point_row_distance(point, row))


def _orient_row(row: Row, position: Point,
                goal: Point | None = None) -> tuple[Point, Point]:
    """Oriente une rangee depuis son extremite la plus proche de l'aiguille.

    Pour la rangee d'arrivee (``goal`` fourni), l'orientation minimise
    ``approche + trajet final`` : le point choisi par l'utilisateur reste la
    reference, sans jamais deplacer la rangee.
    """
    a, b = row
    distance_a = math.hypot(a[0] - position[0], a[1] - position[1])
    distance_b = math.hypot(b[0] - position[0], b[1] - position[1])
    if goal is None:
        return (a, b) if distance_a <= distance_b else (b, a)
    cost_a = distance_a + math.hypot(b[0] - goal[0], b[1] - goal[1])
    cost_b = distance_b + math.hypot(a[0] - goal[0], a[1] - goal[1])
    return (a, b) if cost_a <= cost_b else (b, a)


def _outside_length(workspace: Workspace, points: Sequence[Point],
                    step: float = 0.25) -> float:
    """Longueur de polyligne situee hors de la matiere (mesure sur la grille).

    Le test exact ``contains`` est ambigu pour un point pose sur le contour
    (les extremites de rangee y sont par construction) ; la grille, elle,
    classe la cellule de bord comme matiere. On mesure donc l'ecart reel a la
    matiere maille par maille, pas l'ambiguite du point limite.
    """
    grid = workspace.grid()
    samples = _sample_polyline(points, step)
    total = 0.0
    previous = 0.0
    for x, y, arc in samples:
        index = grid.cell_index(x, y)
        if index is None or not grid.in_material[index]:
            total += arc - previous
        previous = arc
    return total


def _turn_route(workspace: Workspace, position: Point, target: Point,
                sewn: Sequence[Row]) -> TransitionRoute | None:
    """Demi-tour de bord entre deux rangees voisines.

    Le remplissage tatami relie deux rangees voisines par un point court a
    l'extremite : la liaison longe forcement le bord du motif (les extremites
    de rangee sont sur le contour). Ce n'est pas une liaison *visible* au sens
    d'un trajet au-dessus du remplissage : c'est le demi-tour normal. Il n'est
    admis que s'il est court, s'il ne traverse aucune couture et s'il ne
    s'ecarte de la matiere que de facon negligeable (bord arrondi, arrondi de
    cellule). Tout le reste passe par :func:`route_transition` et sa politique.
    """
    length = math.hypot(target[0] - position[0], target[1] - position[1])
    if length > TURN_MAX_FACTOR * workspace.spacing + workspace.grid().cell:
        return None
    if length <= EPSILON:
        return None
    for a, b in sewn:
        if _point_segment_distance(position[0], position[1], *a, *b) <= 1e-6:
            continue
        if _segments_intersect(position, target, a, b):
            return None
    crosses_void, rides_border, rides_seam, _ = classify_link(
        workspace, [position, target], sewn)
    if rides_seam:
        return None
    outside = _outside_length(workspace, [position, target])
    return TransitionRoute(
        points=(position, target),
        length=length,
        crosses_void=crosses_void,
        rides_border=rides_border,
        rides_seam=rides_seam,
        visible=False,
        accepted=True,
        reason=(f"demi-tour de bord ({length:.1f} mm, sortie de matiere "
                f"{outside:.2f} mm)"),
        turn=True,
        outside_length=outside,
    )


@dataclass(frozen=True)
class PlanStep:
    """Une rangee cousue, avec la liaison qui l'a approchee."""

    index: int
    row: Row
    route: TransitionRoute
    start: Point
    end: Point
    remaining_after: int
    rank: int
    rejected_before: int
    length: float

    @property
    def visible(self) -> bool:
        return self.route.visible


@dataclass(frozen=True)
class PlanRefusal:
    """Poursuite ecartee a une etape, avec sa raison mesurable."""

    step: int
    row: Row
    reason: str
    route: TransitionRoute | None = None
    blocked: tuple[Row, ...] = ()


@dataclass(frozen=True)
class FillPlan:
    """Resultat complet d'une simulation de parcours.

    ``completed`` signifie : toutes les rangees ont ete cousues, la rangee
    d'arrivee en dernier. Le ``arrival_move`` est le trajet final vers le
    point choisi par l'utilisateur ; il est toujours signale (il survole
    generalement le remplissage, comme le fait le moteur actuel) et ne doit
    pas etre confondu avec une liaison entre zones.
    """

    start: Point
    end: Point
    steps: tuple[PlanStep, ...]
    refusals: tuple[PlanRefusal, ...]
    arrival_move: TransitionRoute | None
    completed: bool
    failure: str
    rows_total: int
    arrival_row: Row | None

    @property
    def rows_sewn(self) -> int:
        return len(self.steps)

    @property
    def link_length(self) -> float:
        return sum(step.route.length for step in self.steps)

    @property
    def row_length(self) -> float:
        return sum(_row_length(step.row) for step in self.steps)

    @property
    def arrival_length(self) -> float:
        return self.arrival_move.length if self.arrival_move else 0.0

    @property
    def total_length(self) -> float:
        return self.row_length + self.link_length + self.arrival_length

    @property
    def visible_steps(self) -> tuple[PlanStep, ...]:
        return tuple(step for step in self.steps if step.route.visible)

    @property
    def turns(self) -> tuple[PlanStep, ...]:
        return tuple(step for step in self.steps if step.route.turn)

    @property
    def max_turn_outside(self) -> float:
        return max((step.route.outside_length for step in self.turns), default=0.0)

    @property
    def refused_visible(self) -> tuple[PlanRefusal, ...]:
        return tuple(refusal for refusal in self.refusals
                     if refusal.route is not None and refusal.route.visible
                     and not refusal.route.accepted)

    @property
    def max_link(self) -> float:
        return max((step.route.length for step in self.steps), default=0.0)

    def summary(self) -> str:
        lines = [
            f"Rangees : {self.rows_sewn}/{self.rows_total}",
            f"Longueur des rangees : {self.row_length:.1f} mm",
            f"Longueur des liaisons cousues : {self.link_length:.1f} mm"
            f" (max {self.max_link:.1f} mm)",
            f"Trajet d'arrivee : {self.arrival_length:.1f} mm",
            f"Total cousu : {self.total_length:.1f} mm",
        ]
        if self.visible_steps:
            details = ", ".join(
                f"etape {step.index + 1} ({step.route.length:.1f} mm)"
                for step in self.visible_steps)
            lines.append(f"Liaisons visibles acceptees : {len(self.visible_steps)} ({details})")
        else:
            lines.append("Liaisons visibles acceptees : 0")
        lines.append(
            f"Demi-tours de bord : {len(self.turns)}"
            f" (sortie de matiere max {self.max_turn_outside:.2f} mm)")
        if self.refused_visible:
            details = ", ".join(
                f"etape {refusal.step + 1} ({refusal.route.length:.1f} mm)"
                for refusal in self.refused_visible)
            lines.append(f"Liaisons visibles refusees : {len(self.refused_visible)} ({details})")
        if self.completed:
            lines.append("Parcours : complet (depart -> arrivee)")
        else:
            lines.append(f"Parcours interrompu : {self.failure}")
        return "\n".join(lines)


def _plan_seeds(grid: _Grid, material: bytearray, position: Point,
                own_row: Row, spacing: float) -> list[tuple[int, float]]:
    """Graines du planificateur autour de l'aiguille.

    L'aiguille termine une rangee a son extremite : elle peut repartir des
    deux cotes de *cette* rangee (demi-tour), sans traverser les autres. On
    ajoute donc aux graines habituelles les cellules libres voisines de la
    rangee qui vient d'etre cousue. Les autres coutures restent des murs.
    """
    radius = TURN_MAX_FACTOR * spacing + grid.cell
    base = grid.seed_cells(material, position, spacing + grid.cell)
    if not base:
        base = grid.seed_cells(material, position, 2.0 * spacing + grid.cell)
    if not base:
        return []
    limit = spacing + grid.cell + 1e-9
    ax, ay = own_row[0]
    bx, by = own_row[1]
    seen = {index for index, _ in base}
    extra: list[tuple[int, float]] = []
    for index in grid._free_cells_in_disc(material, position, radius):
        if index in seen:
            continue
        cx, cy = grid.center(index)
        if _point_segment_distance(cx, cy, ax, ay, bx, by) <= limit:
            extra.append((index, math.hypot(cx - position[0], cy - position[1])))
    return list(base) + extra


def _endpoint_gap(a: Row, b: Row) -> float:
    """Distance minimale entre les extremites de deux rangees."""
    return min(
        math.hypot(a[0][0] - b[0][0], a[0][1] - b[0][1]),
        math.hypot(a[0][0] - b[1][0], a[0][1] - b[1][1]),
        math.hypot(a[1][0] - b[0][0], a[1][1] - b[0][1]),
        math.hypot(a[1][0] - b[1][0], a[1][1] - b[1][1]),
    )


def _row_normal(row: Row) -> tuple[float, float]:
    (ax, ay), (bx, by) = row
    dx, dy = bx - ax, by - ay
    length = math.hypot(dx, dy)
    if length <= EPSILON:
        return 0.0, 1.0
    return -dy / length, dx / length


def _row_mid_projection(row: Row, normal: tuple[float, float]) -> float:
    return (((row[0][0] + row[1][0]) * 0.5) * normal[0]
            + ((row[0][1] + row[1][1]) * 0.5) * normal[1])


def _first_row(rows: Sequence[Row], nearest: Row, position: Point,
               turn_limit: float, spacing: float) -> Row:
    """Premiere rangee : extreme du cote le plus court du groupe local.

    Commencer par la rangee la plus proche peut laisser des rangees derriere
    l'aiguille (elles ne seront plus joignables sans traverser une couture).
    On choisit donc l'extremite du *petit* cote du groupe de rangees reliees
    par des demi-tours : le remplissage balaie ensuite tout le groupe sans
    revenir en arriere.
    """
    cluster = [nearest]
    seen = {id(nearest)}
    frontier = [nearest]
    while frontier:
        current = frontier.pop()
        for row in rows:
            if id(row) in seen:
                continue
            if _endpoint_gap(current, row) <= turn_limit + EPSILON:
                seen.add(id(row))
                cluster.append(row)
                frontier.append(row)
    normal = _row_normal(nearest)
    start_projection = position[0] * normal[0] + position[1] * normal[1]
    tolerance = spacing * 0.25
    below = [row for row in cluster
             if _row_mid_projection(row, normal) < start_projection - tolerance]
    above = [row for row in cluster
             if _row_mid_projection(row, normal) > start_projection + tolerance]
    if not below or not above:
        # L'aiguille est sur la rangee extreme du groupe : c'est deja le bon
        # depart, inutile de traverser tout le groupe.
        return nearest
    if len(below) <= len(above):
        return min(below, key=lambda row: _row_mid_projection(row, normal))
    return max(above, key=lambda row: _row_mid_projection(row, normal))


def plan_fill_path(workspace: Workspace, rows: Sequence[Row], start: Point,
                   end: Point, *, allow_visible: bool = False,
                   preserve_arrival: bool = True,
                   max_candidates: int = 8) -> FillPlan:
    """Simule le parcours complet de l'aiguille sur ``rows``.

    Regles appliquees, dans cet ordre, a chaque etape :

    1. les rangees sont examinees de la plus proche a la plus lointaine ;
    2. la rangee d'arrivee est reservee : elle ne peut etre cousue que
       lorsqu'elle est la derniere restante ;
    3. une liaison visible (hors matiere, le long d'un bord ou d'une couture)
       est refusee, sauf ``allow_visible=True`` ;
    4. apres chaque candidat, **toutes** les rangees restantes et la rangee
       d'arrivee sont reanalysees depuis la nouvelle position ; si l'une
       devient inaccessible, le candidat est ecarte et la suivante examinee ;
    5. si aucune poursuite n'est valable, le plan s'arrete et explique
       pourquoi (liaison visible refusee / rangees rendues inaccessibles).

    Aucun saut, aucune coupe et aucune liaison traversant une couture ne sont
    introduits : une liaison sans solution geometrique vaut ``None`` et
    interrompt le plan. Le trajet final vers ``end`` est un sous-point cousu
    (comme dans le moteur actuel), rapporte separement.
    """
    grid = workspace.grid()
    radius = workspace.seam_radius
    normalized = [((float(row[0][0]), float(row[0][1])),
                   (float(row[1][0]), float(row[1][1]))) for row in rows]
    if not normalized:
        raise ValueError("Aucune rangee a planifier.")
    if max_candidates < 1:
        raise ValueError("max_candidates doit etre au moins 1.")

    start_point = (float(start[0]), float(start[1]))
    end_point = (float(end[0]), float(end[1]))

    for point, label in ((start_point, "de depart"),
                         (end_point, "d'arrivee")):
        status = _material_point_status(workspace, point)
        if status == "trou":
            raise ValueError(f"Le point {label} est dans un trou.")
        if status == "bord_trou":
            raise ValueError(
                f"Le point {label} est sur le bord d'un trou.")
        if status == "hors_contour":
            raise ValueError(f"Le point {label} est hors du contour.")
        if status == "non_fini":
            raise ValueError(
                f"Le point {label} doit avoir des coordonnees finies.")

    arrival_row = _nearest_row(normalized, end_point) if preserve_arrival else None

    remaining = list(normalized)
    sewn: list[Row] = []
    barrier = bytearray(grid.count)
    material_free = bytearray(grid.in_material)
    total_free = bytearray(0 if hole else 1 for hole in grid.in_hole)
    position = start_point
    steps: list[PlanStep] = []
    refusals: list[PlanRefusal] = []
    index = 0

    while remaining:
        ordered = sorted(remaining, key=lambda row: _point_row_distance(position, row))
        if index == 0 and len(remaining) > 1:
            first = _first_row(
                remaining, ordered[0], position,
                TURN_MAX_FACTOR * workspace.spacing + grid.cell,
                workspace.spacing)
            ordered = [first] + [row for row in ordered if row is not first]
        chosen = None
        attempted: list[PlanRefusal] = []
        for rank, row in enumerate(ordered[:max_candidates]):
            if row is arrival_row and len(remaining) > 1:
                attempted.append(PlanRefusal(
                    index, row, "rangee d'arrivee reservee a la fin"))
                continue
            row_start, row_end = _orient_row(
                row, position, end_point if row is arrival_row else None)
            route = _turn_route(workspace, position, row_start, sewn)
            if route is None:
                route = route_transition(
                    workspace, sewn, position, row_start,
                    allow_visible=allow_visible, free=total_free)
            if route is None:
                attempted.append(PlanRefusal(
                    index, row,
                    "aucune liaison continue sans traverser une couture existante"))
                continue
            if not route.accepted:
                attempted.append(PlanRefusal(
                    index, row,
                    f"liaison visible refusee : {route.reason} "
                    f"({route.length:.1f} mm)", route))
                continue

            candidate_barrier = bytearray(barrier)
            new_cells: list[int] = []
            for segment in ((row_start, row_end), *zip(route.points, route.points[1:])):
                new_cells.extend(grid.add_sewn(candidate_barrier, segment, radius))
            candidate_material = bytearray(material_free)
            candidate_total = bytearray(total_free)
            for cell in new_cells:
                candidate_material[cell] = 0
                candidate_total[cell] = 0

            targets = [other for other in remaining if other is not row]
            if targets:
                states = analyse_rows(
                    workspace, sewn, targets, row_end,
                    material=candidate_material, free=candidate_total,
                    barrier=candidate_barrier,
                    seeds=_plan_seeds(grid, candidate_material, row_end,
                                      (row_start, row_end), workspace.spacing))
                blocked = blocked_rows(states)
                if blocked:
                    attempted.append(PlanRefusal(
                        index, row,
                        f"{len(blocked)} rangee(s) deviendraient inaccessibles "
                        "apres cette couture", route, blocked))
                    continue

            chosen = (row, row_start, row_end, route, candidate_barrier,
                      candidate_material, candidate_total, rank, len(attempted))
            break

        refusals.extend(attempted)
        if chosen is None:
            if any(refusal.route is not None and not refusal.route.accepted
                   for refusal in attempted):
                failure = ("aucune solution valide : la seule poursuite encore "
                           "geometriquement possible est une liaison visible, "
                           "refusee")
            elif attempted:
                failure = ("aucune solution valide : toutes les poursuites "
                           "rendraient des rangees inaccessibles")
            else:
                failure = "aucune rangee candidate dans la limite examinee"
            return FillPlan(start=start_point, end=end_point, steps=tuple(steps),
                            refusals=tuple(refusals), arrival_move=None,
                            completed=False, failure=failure,
                            rows_total=len(normalized), arrival_row=arrival_row)

        (row, row_start, row_end, route, barrier,
         material_free, total_free, rank, rejected) = chosen
        sewn.append((row_start, row_end))
        sewn.extend(zip(route.points, route.points[1:]))
        remaining.remove(row)
        steps.append(PlanStep(
            index=index, row=row, route=route, start=row_start, end=row_end,
            remaining_after=len(remaining), rank=rank, rejected_before=rejected,
            length=_row_length(row) + route.length))
        position = row_end
        index += 1

    # Trajet final vers le point choisi : sous-point cousu au-dessus du
    # remplissage, comme le moteur actuel. Il est signale, jamais masque.
    crosses_void, rides_border, rides_seam, visible = classify_link(
        workspace, [position, end_point], sewn)
    arrival_move = TransitionRoute(
        points=(position, end_point),
        length=math.hypot(end_point[0] - position[0], end_point[1] - position[1]),
        crosses_void=crosses_void, rides_border=rides_border,
        rides_seam=rides_seam, visible=visible, accepted=True,
        reason="trajet d'arrivee vers le point choisi (au-dessus du remplissage)")

    return FillPlan(start=start_point, end=end_point, steps=tuple(steps),
                    refusals=tuple(refusals), arrival_move=arrival_move,
                    completed=True, failure="", rows_total=len(normalized),
                    arrival_row=arrival_row)
