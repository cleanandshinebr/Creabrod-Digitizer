import math
import re
from dataclasses import dataclass, field

CORNER = "corner"  # point droit (angle) : la ligne est droite
CURVE = "curve"    # point de courbe : la ligne s'arrondit

STITCH_TYPES = ("running", "satin", "fill")
CONNECTION_MODES = ("trim_then_jump", "jump", "running")

MAX_COORDINATE_MM = 5000.0  # au-delà, on considère que la coordonnée est absurde

# Limites du satin (valeurs prudentes, à valider sur machine)
SATIN_WIDTH_MIN = 1.0       # largeur de la colonne, en mm
SATIN_WIDTH_MAX = 7.0
SATIN_SPACING_MIN = 0.3     # écart entre deux piqûres du même côté, en mm (en dessous : densité excessive)
SATIN_SPACING_MAX = 1.0
FILL_SPACING_MIN = 0.5
FILL_SPACING_MAX = 10.0
THREAD_COLOR_DEFAULT = "#1b3a6b"
THREAD_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
SATIN_CORNER_MODES = ("continuous", "insertion", "square_miter")
SATIN_CORNER_MODE_DEFAULT = "square_miter"
UNDERLAY_TYPES = ("centerline", "walking", "zigzag")


@dataclass
class Contour:
    """Un contour = une suite de points (x, y, type), mesurés en millimètres."""

    points: list = field(default_factory=list)
    closed: bool = False
    stitch_type: str = "running"   # type de point de broderie : "running" ou "satin"
    stitch_length: float = 2.5     # longueur du point (running), en mm
    satin_width: float = 3.0       # largeur de la colonne (satin), en mm
    satin_spacing: float = 0.4     # écart entre deux piqûres du même côté (satin), en mm
    fill_angle: float = 0.0
    fill_spacing: float = 2.0
    satin_corner_mode: str = SATIN_CORNER_MODE_DEFAULT
    underlays: list = field(default_factory=list)
    connection_mode: str = "trim_then_jump"  # connexion vers le bloc suivant
    thread_color: str = THREAD_COLOR_DEFAULT
    holes: list = field(default_factory=list)
    # Départ et arrivée choisis par l'utilisateur pour un Fill
    # (inspiration Ink/Stitch « starting/ending point » et EOS
    # « Point d'Entrée/Sortie »). None = choix automatique.
    start_point: tuple = None
    end_point: tuple = None

    def add_point(self, x, y, kind=CURVE):
        self.points.append((x, y, kind))

    def add_hole(self, hole):
        if hole is None:
            return
        if not isinstance(hole, Contour):
            raise TypeError("Le trou doit être un objet Contour.")
        if not hole.closed:
            hole.closed = True
        self.holes.append(hole)

    # ---------- Sauvegarde ----------
    def to_dict(self):
        dico = {
            "points": [{"x": x, "y": y, "type": kind} for x, y, kind in self.points],
            "closed": self.closed,
            "stitch_type": self.stitch_type,
            "stitch_length": self.stitch_length,
            "satin_width": self.satin_width,
            "satin_spacing": self.satin_spacing,
            "fill_angle": self.fill_angle,
            "fill_spacing": self.fill_spacing,
            "satin_corner_mode": self.satin_corner_mode,
            "underlays": list(self.underlays),
            "connection_mode": self.connection_mode,
            "thread_color": self.thread_color,
            "holes": [hole.to_dict() for hole in self.holes],
        }
        for cle, point in (("start_point", self.start_point), ("end_point", self.end_point)):
            if point is not None:
                dico[cle] = {"x": float(point[0]), "y": float(point[1])}
        return dico

    @classmethod
    def from_dict(cls, data):
        length = float(data.get("stitch_length", 2.5))
        if not math.isfinite(length) or length <= 0:
            raise ValueError("Longueur de point invalide dans le fichier.")

        stitch_type = str(data.get("stitch_type", "running"))
        if stitch_type not in STITCH_TYPES:
            raise ValueError(f"Type de point inconnu dans le fichier : {stitch_type}")

        connection_mode = str(data.get("connection_mode", "trim_then_jump"))
        if connection_mode not in CONNECTION_MODES:
            raise ValueError(f"Mode de connexion inconnu dans le fichier : {connection_mode}")

        satin_corner_mode = str(data.get("satin_corner_mode", SATIN_CORNER_MODE_DEFAULT))
        if satin_corner_mode not in SATIN_CORNER_MODES:
            raise ValueError(f"Mode de coin satin inconnu dans le fichier : {satin_corner_mode}")

        underlays = list(data.get("underlays", []))
        if any(underlay not in UNDERLAY_TYPES for underlay in underlays):
            raise ValueError("Type de sous-couche inconnu dans le fichier.")
        if len(set(underlays)) != len(underlays):
            raise ValueError("Une sous-couche ne peut pas être sélectionnée deux fois.")

        thread_color = str(data.get("thread_color", THREAD_COLOR_DEFAULT))
        if not THREAD_COLOR_RE.fullmatch(thread_color):
            raise ValueError("Couleur de fil invalide dans le fichier.")

        width = float(data.get("satin_width", 3.0))
        if not (SATIN_WIDTH_MIN <= width <= SATIN_WIDTH_MAX):
            raise ValueError("Largeur de satin invalide dans le fichier.")

        spacing = float(data.get("satin_spacing", 0.4))
        if not math.isfinite(spacing) or spacing > SATIN_SPACING_MAX:
            raise ValueError("Densité de satin invalide dans le fichier.")
        # Les anciens projets pouvaient contenir un écart plus petit que le minimum actuel.
        spacing = max(spacing, SATIN_SPACING_MIN)

        fill_angle = float(data.get("fill_angle", 0.0))
        if not math.isfinite(fill_angle):
            raise ValueError("Angle de remplissage invalide dans le fichier.")

        fill_spacing = float(data.get("fill_spacing", 2.0))
        if not math.isfinite(fill_spacing) or not (FILL_SPACING_MIN <= fill_spacing <= FILL_SPACING_MAX):
            raise ValueError("Écart de remplissage invalide dans le fichier.")

        contour = cls(
            closed=bool(data.get("closed", False)),
            stitch_type=stitch_type,
            stitch_length=length,
            satin_width=width,
            satin_spacing=spacing,
            fill_angle=fill_angle,
            fill_spacing=fill_spacing,
            satin_corner_mode=satin_corner_mode,
            underlays=underlays,
            connection_mode=connection_mode,
            thread_color=thread_color.lower(),
        )
        for p in data.get("points", []):
            x = float(p["x"])
            y = float(p["y"])
            if not (math.isfinite(x) and math.isfinite(y)):
                raise ValueError("Coordonnée invalide dans le fichier.")
            if abs(x) > MAX_COORDINATE_MM or abs(y) > MAX_COORDINATE_MM:
                raise ValueError("Coordonnée absurde dans le fichier.")
            kind = p.get("type", CURVE)
            if kind not in (CORNER, CURVE):
                kind = CURVE
            contour.add_point(x, y, kind)
        for raw_hole in data.get("holes", []):
            hole = cls.from_dict(raw_hole)
            hole.closed = True
            contour.add_hole(hole)
        for cle, attribut in (("start_point", "start_point"), ("end_point", "end_point")):
            brut = data.get(cle)
            if brut is None:
                continue
            x = float(brut["x"])
            y = float(brut["y"])
            if not (math.isfinite(x) and math.isfinite(y)):
                raise ValueError("Coordonnée invalide dans le fichier.")
            if abs(x) > MAX_COORDINATE_MM or abs(y) > MAX_COORDINATE_MM:
                raise ValueError("Coordonnée absurde dans le fichier.")
            setattr(contour, attribut, (x, y))
        return contour

    # ---------- Géométrie ----------
    def _tangent(self, i):
        """Direction de la courbe au point i. Un point droit n'a pas de direction."""
        x, y, kind = self.points[i]
        if kind == CORNER:
            return (0.0, 0.0)
        prev_pt = self.points[i - 1] if i > 0 else self.points[i]
        next_pt = self.points[i + 1] if i < len(self.points) - 1 else self.points[i]
        return ((next_pt[0] - prev_pt[0]) / 2, (next_pt[1] - prev_pt[1]) / 2)

    def _build_path(self, steps=24):
        """Calcule le chemin complet. Retourne (chemin, positions_des_points_droits)."""
        n = len(self.points)
        if n == 0:
            return [], []

        x_first, y_first, k_first = self.points[0]
        path = [(x_first, y_first)]
        corners = [0] if k_first == CORNER else []

        for i in range(n - 1):
            x0, y0, k0 = self.points[i]
            x1, y1, k1 = self.points[i + 1]

            if k0 == CORNER and k1 == CORNER:
                path.append((x1, y1))
            else:
                t0 = self._tangent(i)
                t1 = self._tangent(i + 1)
                c1 = (x0 + t0[0] / 3, y0 + t0[1] / 3)
                c2 = (x1 - t1[0] / 3, y1 - t1[1] / 3)
                for s in range(1, steps + 1):
                    t = s / steps
                    u = 1 - t
                    x = u**3 * x0 + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t**3 * x1
                    y = u**3 * y0 + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t**3 * y1
                    path.append((x, y))

            if k1 == CORNER:
                corners.append(len(path) - 1)

        return path, corners

    def flatten(self, steps=24):
        """Transforme le contour (avec ses courbes) en une suite de petits segments."""
        return self._build_path(steps)[0]

    def split_at_corners(self, steps=24):
        """Découpe le chemin en morceaux, à chaque point droit."""
        path, corners = self._build_path(steps)
        if len(path) < 2:
            return []
        cuts = sorted(set([0] + corners + [len(path) - 1]))
        return [path[a : b + 1] for a, b in zip(cuts, cuts[1:]) if b > a]

    def length_mm(self):
        """Longueur réelle du contour (courbes comprises) en millimètres."""
        path = self.flatten()
        if self.closed and path:
            path.append(path[0])
        total = 0.0
        for (x1, y1), (x2, y2) in zip(path, path[1:]):
            total += math.hypot(x2 - x1, y2 - y1)
        return total

    def reverse(self):
        """Inverse le sens : le début devient la fin."""
        self.points.reverse()

    def bounds(self):
        """Rectangle englobant (x min, y min, x max, y max) en mm."""
        path = self.flatten()
        if not path:
            return (0.0, 0.0, 0.0, 0.0)
        xs = [x for x, _ in path]
        ys = [y for _, y in path]
        return (min(xs), min(ys), max(xs), max(ys))

    def distance_to(self, x, y):
        """Distance (mm) entre le point (x, y) et le contour."""
        path = self.flatten()
        if not path:
            return float("inf")
        if len(path) == 1:
            return math.hypot(x - path[0][0], y - path[0][1])
        best = float("inf")
        for (x1, y1), (x2, y2) in zip(path, path[1:]):
            dx, dy = x2 - x1, y2 - y1
            longueur2 = dx * dx + dy * dy
            if longueur2 == 0:
                t = 0.0
            else:
                t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / longueur2))
            best = min(best, math.hypot(x - (x1 + t * dx), y - (y1 + t * dy)))
        return best
