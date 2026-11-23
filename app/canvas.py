import time

import math

from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsEllipseItem,
    QGraphicsRectItem,
    QGraphicsItem,
    QGraphicsSimpleTextItem,
    QMenu,
    QMessageBox,
)
from PySide6.QtGui import (
    QPixmap,
    QPainter,
    QColor,
    QPen,
    QBrush,
    QPainterPath,
    QTransform,
)
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from app.settings_dialog import StitchSettingsDialog
from core.objects import Contour, CORNER, CURVE, THREAD_COLOR_DEFAULT, FILL_SPACING_MIN, FILL_SPACING_MAX
from core.machine_pattern import DEFAULT_THREAD_COLORS
from core.project import Project
from core.stitches.engine import safe_stitch_points, stitch_paths, stitch_points

# L'image est affichée à cette largeur. 1 unité de la scène = 1 millimètre.
IMAGE_WIDTH_MM = 100.0

# Un clic maintenu plus longtemps que cela (en millisecondes) = point droit.
LONG_CLICK_MS = 400

# Couleurs
COULEUR_EN_COURS = "#1d6fe0"
COULEUR_CONTOUR = "#d62828"
COULEUR_SELECTION = "#f28c28"
COULEUR_FIL = "#1b3a6b"
COULEUR_DEBUT = "#1a7f37"
COULEUR_FIN = "#b42318"

NOMS_TYPES = {"running": "Running stitch", "satin": "Satin", "fill": "Fill"}


def describe_parameters(contour):
    """Phrase courte décrivant les réglages d'un dessin."""
    if contour.stitch_type == "satin":
        return (
            f"satin de {contour.satin_width:.1f} mm de large, "
            f"écart {contour.satin_spacing:.2f} mm"
        )
    if contour.stitch_type == "fill":
        return (
            f"remplissage à {contour.fill_angle:.1f}°, "
            f"écart {contour.fill_spacing:.2f} mm"
        )
    return f"point de {contour.stitch_length:.1f} mm"


def _point_in_polygon(point, polygon):
    """Indique si un point est à l'intérieur d'un chemin polygonal fermé."""
    x, y = point
    inside = False
    previous_x, previous_y = polygon[-1]
    for current_x, current_y in polygon:
        if (current_y > y) != (previous_y > y):
            intersection_x = (
                (previous_x - current_x) * (y - current_y)
                / (previous_y - current_y)
                + current_x
            )
            if x < intersection_x:
                inside = not inside
        previous_x, previous_y = current_x, current_y
    return inside


class Canvas(QGraphicsView):
    """Zone de travail : cadre, image, zoom, déplacement, contours et points.

    Le centre du cadre est le point (0, 0), comme sur une machine à broder.
    """

    status_message = Signal(str)
    changed = Signal()                 # le projet a été modifié
    mouse_moved = Signal(float, float) # position de la souris en mm
    zoom_changed = Signal(float)       # zoom en % (100 % = taille réelle à l'écran)
    stitch_count_changed = Signal(int) # nombre total de points de broderie
    selection_changed = Signal()

    def __init__(self):
        super().__init__()
        self.work_scene = QGraphicsScene(self)
        self.setScene(self.work_scene)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setBackgroundBrush(QColor("#d0d0d0"))
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

        self.frame_size = (130.0, 180.0)  # largeur, hauteur du cadre en mm
        self.image_item = None
        self.image_path = ""
        self.contours = []        # contours terminés
        self.machine_pattern = None  # motif machine importé, conservé comme points
        self.current = None       # contour en cours de dessin
        self.current_hole = None  # trou en cours de définition pour un fill
        self.selected = None      # contour terminé sélectionné
        self.overlay_items = []   # éléments graphiques des contours
        self.press_point = None   # position du clic gauche en cours
        self.press_time = 0.0     # moment où le bouton a été enfoncé

        # Réglages des NOUVEAUX dessins (choisis dans la barre du haut)
        self.default_stitch_type = "running"
        self.default_thread_color = THREAD_COLOR_DEFAULT
        self.stitch_length = 2.5         # running stitch : longueur du point (mm)
        self.default_satin_width = 3.0   # satin : largeur de la colonne (mm)
        self.default_satin_spacing = 0.4 # satin : écart entre deux piqûres du même côté (mm)
        self.default_fill_angle = 0.0     # fill : angle de la direction de points (°)
        self.default_fill_spacing = 2.0   # fill : écart entre les lignes (mm)

        self.show_stitches = True # afficher les points d'aiguille
        self.show_crosshair = True# afficher les axes qui suivent la souris
        self.cursor_pos = None    # position de la souris dans la scène
        self.tool = "move"
        self.selection_dragged = False
        self._resize_handle = None
        self._resize_bounds = None
        self._resize_points = None
        self._rotation_center = None
        self._rotation_start_angle = None
        self._rotation_points = None
        self.set_tool("move")

    # ---------- Outils ----------
    def set_tool(self, tool):
        selection_a_conserver = self.selected
        self.tool = tool
        if tool == "contour":
            self.setDragMode(QGraphicsView.NoDrag)
            self.viewport().setCursor(Qt.CrossCursor)
            self.status_message.emit(
                "Contour : clic simple = courbe, clic long = point droit, "
                "clic droit = menu, Entrée = terminer, Retour arrière = annuler le dernier point, "
                "Échap = annuler le contour."
            )
        elif tool == "select":
            self.finish_contour()
            self.setDragMode(QGraphicsView.NoDrag)
            self.viewport().setCursor(Qt.ArrowCursor)
            self.status_message.emit(
                "Sélection : cliquez sur un dessin pour afficher ses propriétés."
            )
        elif tool == "rotate":
            self.finish_contour()
            self.setDragMode(QGraphicsView.NoDrag)
            self.viewport().setCursor(Qt.CrossCursor)
            self.status_message.emit(
                "Rotation : cliquez sur un dessin puis glissez autour de son centre."
            )
        elif tool == "resize":
            self.finish_contour()
            self.setDragMode(QGraphicsView.NoDrag)
            self.viewport().setCursor(Qt.SizeFDiagCursor)
            self.status_message.emit(
                "Redimensionner : sélectionnez un dessin puis glissez une poignée."
            )
        else:
            self.finish_contour()
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.viewport().setCursor(Qt.OpenHandCursor)
            self.status_message.emit(
                "Déplacer : glisser = déplacer, molette = zoom, clic droit sur un dessin = menu."
            )
        # Changer d'outil ne doit jamais désélectionner le motif courant.
        # C'est particulièrement important pour Rotation et Redimensionner :
        # le dessin doit rester visible avec ses poignées après le clic sur le bouton.
        if selection_a_conserver is not None and selection_a_conserver in self.contours:
            self.selected = selection_a_conserver
        self.refresh_overlay()

    # ---------- Réglages des nouveaux dessins ----------
    def new_contour(self):
        """Un nouveau dessin vide, avec les réglages choisis dans la barre du haut."""
        return Contour(
            closed=self.default_stitch_type == "fill",
            stitch_type=self.default_stitch_type,
            thread_color=self.default_thread_color,
            stitch_length=self.stitch_length,
            satin_width=self.default_satin_width,
            satin_spacing=self.default_satin_spacing,
            fill_angle=self.default_fill_angle,
            fill_spacing=self.default_fill_spacing,
        )

    def set_default_stitch_type(self, stitch_type):
        """Type de point des NOUVEAUX dessins (et du dessin en cours)."""
        if stitch_type not in NOMS_TYPES:
            return
        self.default_stitch_type = stitch_type
        if self.current is not None:
            self.current.stitch_type = stitch_type
            if stitch_type == "fill":
                self.current.closed = True
                self.current.fill_angle = self.default_fill_angle
                self.current.fill_spacing = self.default_fill_spacing
        self.status_message.emit(
            f"Type de point des nouveaux dessins : {NOMS_TYPES[stitch_type]}."
        )

    def set_stitch_length(self, value):
        """Longueur du point (running) pour les NOUVEAUX dessins (et le dessin en cours)."""
        self.stitch_length = float(value)
        if self.current is not None:
            self.current.stitch_length = self.stitch_length
            self.refresh_overlay()
        self.status_message.emit(
            f"Longueur du point des nouveaux dessins : {self.stitch_length:.1f} mm."
        )

    def set_default_satin_width(self, value):
        """Largeur du satin pour les NOUVEAUX dessins (et le dessin en cours)."""
        self.default_satin_width = float(value)
        if self.current is not None:
            self.current.satin_width = self.default_satin_width
            self.refresh_overlay()
        self.status_message.emit(
            f"Largeur du satin des nouveaux dessins : {self.default_satin_width:.1f} mm."
        )

    def set_default_satin_spacing(self, value):
        """Écart du satin pour les NOUVEAUX dessins (et le dessin en cours)."""
        self.default_satin_spacing = float(value)
        if self.current is not None:
            self.current.satin_spacing = self.default_satin_spacing
            self.refresh_overlay()
        self.status_message.emit(
            f"Écart du satin des nouveaux dessins : {self.default_satin_spacing:.2f} mm."
        )

    def set_default_fill_angle(self, value):
        """Angle de remplissage pour les NOUVEAUX dessins (et le dessin en cours)."""
        angle = float(value)
        if not (0.0 <= angle <= 180.0):
            return
        self.default_fill_angle = angle
        if self.current is not None:
            self.current.fill_angle = angle
            self.refresh_overlay()
        self.status_message.emit(
            f"Angle de remplissage des nouveaux dessins : {self.default_fill_angle:.1f}°."
        )

    def set_default_fill_spacing(self, value):
        """Écart du remplissage pour les NOUVEAUX dessins (et le dessin en cours)."""
        spacing = float(value)
        if not (FILL_SPACING_MIN <= spacing <= FILL_SPACING_MAX):
            return
        self.default_fill_spacing = spacing
        if self.current is not None:
            self.current.fill_spacing = spacing
            self.refresh_overlay()
        self.status_message.emit(
            f"Écart de remplissage des nouveaux dessins : {self.default_fill_spacing:.2f} mm."
        )

    def set_show_stitches(self, visible):
        self.show_stitches = bool(visible)
        self.refresh_overlay()

    def set_show_crosshair(self, visible):
        self.show_crosshair = bool(visible)
        self.viewport().update()

    def total_stitches(self):
        if self.machine_pattern is not None:
            return self.machine_pattern.stitches
        return sum(len(safe_stitch_points(c)) for c in self.contours)

    # ---------- Projet ----------
    def get_project(self):
        """Rassemble l'état actuel dans un objet Project (pour l'enregistrer)."""
        return Project(
            frame_width=self.frame_size[0],
            frame_height=self.frame_size[1],
            image_path=self.image_path,
            contours=list(self.contours),
            machine_pattern=self.machine_pattern,
        )

    def set_project(self, project):
        """Affiche un projet ouvert. Retourne un message d'avertissement (ou '')."""
        self._reset_scene(project.frame_width, project.frame_height)
        avertissement = ""
        if project.image_path:
            if not self._put_image(project.image_path):
                avertissement = f"Image de fond introuvable : {project.image_path}"
        self.contours = list(project.contours)
        self.machine_pattern = project.machine_pattern
        self.update_scene_rect()
        self.fit_to_frame()
        self.refresh_overlay()
        self.status_message.emit(
            f"Projet ouvert : {len(self.contours)} dessins, "
            f"{self.total_stitches()} points de broderie."
        )
        return avertissement

    # ---------- Page de travail (cadre) ----------
    def has_content(self):
        return bool(self.contours) or self.current is not None or self.machine_pattern is not None

    def set_machine_pattern(self, pattern):
        """Affiche un motif machine sans le convertir en contours éditables."""
        x0, y0, x1, y1 = pattern.bounds()
        self._reset_scene(max(130.0, x1 - x0 + 20.0), max(180.0, y1 - y0 + 20.0))
        self.machine_pattern = pattern
        self.update_scene_rect()
        self.fit_to_frame()
        self.refresh_overlay()
        self.status_message.emit(
            f"Motif {pattern.format_name} ouvert : {pattern.stitches} points, "
            f"{pattern.jumps} sauts, {pattern.color_changes} changement(s) de couleur."
        )

    def _reset_scene(self, width_mm, height_mm):
        self.work_scene.clear()
        self.image_item = None
        self.image_path = ""
        self.overlay_items = []
        self.contours = []
        self.machine_pattern = None
        self.current = None
        self.selected = None
        self.press_point = None
        self.frame_size = (float(width_mm), float(height_mm))
        self.stitch_count_changed.emit(0)

    def new_workspace(self, width_mm, height_mm):
        """Crée une page vide : un cadre blanc de width_mm x height_mm."""
        self._reset_scene(width_mm, height_mm)
        self.update_scene_rect()
        self.fit_to_frame()
        self.status_message.emit(
            "Nouveau motif : espace de travail libre. "
            "Choisissez l'outil Contour pour dessiner."
        )

    def draw_frame(self):
        """Compatibilité avec les anciens projets : aucun cadre n'est affiché."""
        return None

    def update_scene_rect(self):
        rect = self.work_scene.itemsBoundingRect()
        if not rect.isValid() or rect.isNull():
            rect = QRectF(-250, -200, 500, 400)
        self.work_scene.setSceneRect(rect.adjusted(-30, -30, 30, 30))

    def fit_to_frame(self):
        self.fitInView(self.work_scene.sceneRect(), Qt.KeepAspectRatio)
        self._emit_zoom()

    def _emit_zoom(self):
        """100 % = 1 mm du motif correspond à 1 mm à l'écran."""
        pixels_par_mm = self.logicalDpiX() / 25.4
        self.zoom_changed.emit(self.transform().m11() / pixels_par_mm * 100)

    # ---------- Image ----------
    def _put_image(self, path):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return False
        if self.image_item is not None:
            self.work_scene.removeItem(self.image_item)
        item = self.work_scene.addPixmap(pixmap)
        item.setScale(IMAGE_WIDTH_MM / pixmap.width())
        hauteur = pixmap.height() * IMAGE_WIDTH_MM / pixmap.width()
        item.setPos(-IMAGE_WIDTH_MM / 2, -hauteur / 2)  # centrée dans le cadre
        item.setZValue(0)
        self.image_item = item
        self.image_path = path
        return True

    def show_image(self, path):
        if not self._put_image(path):
            return False
        self.update_scene_rect()
        self.fit_to_frame()
        self.changed.emit()
        return True

    # ---------- Dessin des contours ----------
    def clear_contours(self):
        had_content = self.has_content()
        self.contours = []
        self.machine_pattern = None
        self.current = None
        self.selected = None
        self.refresh_overlay()
        if had_content:
            self.changed.emit()
        self.status_message.emit("Contours effacés.")

    def add_point(self, point, kind):
        if self.machine_pattern is not None:
            self.machine_pattern = None
            self.refresh_overlay()
        self.selected = None
        if self.current_hole is not None:
            self.current_hole.add_point(point.x(), point.y(), kind)
            self.refresh_overlay()
            nom = "droit" if kind == CORNER else "de courbe"
            self.status_message.emit(
                f"Point {nom} ajouté au trou : {len(self.current_hole.points)} points, "
                f"{self.current_hole.length_mm():.1f} mm"
            )
            return
        if self.current is None:
            self.current = self.new_contour()
        self.current.add_point(point.x(), point.y(), kind)
        self.refresh_overlay()
        nom = "droit" if kind == CORNER else "de courbe"
        self.status_message.emit(
            f"Point {nom} ajouté. Contour en cours : {len(self.current.points)} points, "
            f"{self.current.length_mm():.1f} mm"
        )

    def undo_last_point(self):
        if self.current_hole is not None:
            if self.current_hole.points:
                self.current_hole.points.pop()
            if not self.current_hole.points:
                self.current_hole = None
            self.refresh_overlay()
            return
        if self.current is None:
            return
        if self.current.points:
            self.current.points.pop()
        if not self.current.points:
            self.current = None
        self.refresh_overlay()

    def cancel_drawing(self):
        if self.current_hole is not None:
            self.current_hole = None
            self.refresh_overlay()
            return
        self.current = None
        self.refresh_overlay()

    def finish_contour(self):
        if self.current_hole is not None:
            if len(self.current_hole.points) >= 2:
                self.current_hole.closed = True
                self.current.holes.append(self.current_hole)
                self.status_message.emit(
                    f"Trou ajouté : {self.current_hole.length_mm():.1f} mm, "
                    f"{len(self.current.holes)} trou(s) dans le remplissage."
                )
            self.current_hole = None
            self.refresh_overlay()
            return
        if self.current is None:
            return
        if self.current.stitch_type == "fill":
            self.current.closed = True
        if len(self.current.points) >= 2:
            self.contours.append(self.current)
            points = safe_stitch_points(self.current)
            nb = len(points)
            self.status_message.emit(
                f"Contour terminé : {self.current.length_mm():.1f} mm, "
                f"{nb} points de broderie ({describe_parameters(self.current)}). "
                f"Total : {self.total_stitches()} points."
            )
            self.changed.emit()
        self.current = None
        self.refresh_overlay()

    # ---------- Sélection et actions sur un dessin ----------
    def select(self, contour):
        self.selected = contour
        self.refresh_overlay()
        self.selection_changed.emit()

    def move_selected(self, dx, dy):
        """Déplace le contour sélectionné de (dx, dy) millimètres."""
        if self.selected is None:
            return False
        self.selected.points = [
            (x + dx, y + dy, kind) for x, y, kind in self.selected.points
        ]
        self.refresh_overlay()
        self.selection_changed.emit()
        return True

    def contour_at(self, point):
        """Le dessin terminé le plus proche du point (ou None s'il n'y en a pas près)."""
        tolerance = 8 / max(self.transform().m11(), 1e-9)  # 8 pixels d'écran
        meilleur = None
        meilleure_distance = tolerance
        for contour in self.contours:
            distance = contour.distance_to(point.x(), point.y())
            if (
                contour.closed
                and contour.stitch_type == "fill"
                and len(contour.points) >= 3
                and _point_in_polygon(
                    (point.x(), point.y()), contour.flatten()
                )
            ):
                distance = 0.0
            if distance <= meilleure_distance:
                meilleur = contour
                meilleure_distance = distance
        return meilleur

    def delete_contour(self, contour):
        self.contours = [c for c in self.contours if c is not contour]
        if self.selected is contour:
            self.selected = None
        self.refresh_overlay()
        self.changed.emit()
        self.status_message.emit("Dessin supprimé.")

    def reverse_contour(self, contour):
        contour.reverse()
        self.refresh_overlay()
        if contour is not self.current:
            self.changed.emit()
        self.status_message.emit("Sens inversé : le début et la fin ont changé de place.")

    def set_stitch_type(self, contour, stitch_type):
        """Change le type de point d'un dessin (running stitch, satin...)."""
        if contour.stitch_type == stitch_type:
            return
        contour.stitch_type = stitch_type
        self.refresh_overlay()
        if contour is not self.current:
            self.changed.emit()
        self.status_message.emit(
            f"Type de point : {NOMS_TYPES[stitch_type]} ({describe_parameters(contour)})."
        )

    def edit_settings(self, contour):
        dialogue = StitchSettingsDialog(contour, self)
        if dialogue.exec():
            dialogue.apply_to(contour)
            self.refresh_overlay()
            if contour is not self.current:
                self.changed.emit()
            self.status_message.emit(
                f"Paramètres modifiés : {NOMS_TYPES[contour.stitch_type]}, "
                f"{describe_parameters(contour)}."
            )

    def show_properties(self, contour):
        points = stitch_points(contour)
        if points:
            xs = [x for x, _ in points]
            ys = [y for _, y in points]
            largeur = max(xs) - min(xs)
            hauteur = max(ys) - min(ys)
        else:
            x0, y0, x1, y1 = contour.bounds()
            largeur, hauteur = x1 - x0, y1 - y0

        debut = contour.points[0]
        fin = contour.points[-1]
        lignes = [
            f"Type de point : {NOMS_TYPES.get(contour.stitch_type, contour.stitch_type)}",
            f"Points de contrôle : {len(contour.points)}",
            f"Longueur de la ligne : {contour.length_mm():.1f} mm",
            f"Dimensions : {largeur:.1f} × {hauteur:.1f} mm",
        ]
        if contour.stitch_type == "satin":
            lignes.append(f"Largeur de la colonne : {contour.satin_width:.1f} mm")
            lignes.append(f"Écart entre les points : {contour.satin_spacing:.2f} mm")
        else:
            lignes.append(f"Longueur du point : {contour.stitch_length:.1f} mm")
        lignes += [
            f"Points de broderie : {len(points)}",
            f"Début : {debut[0]:.1f} , {-debut[1]:.1f} mm",
            f"Fin : {fin[0]:.1f} , {-fin[1]:.1f} mm",
        ]
        QMessageBox.information(self, "Propriétés du dessin", "\n".join(lignes))

    # ---------- Menu du clic droit ----------
    def _add_action(self, menu, texte, fonction, enabled=True):
        action = menu.addAction(texte)
        action.setEnabled(enabled)
        action.triggered.connect(lambda checked=False: fonction())
        return action

    def _place_fill_point(self, contour, cle, point):
        """Place (ou retire) le point de départ/arrivée d'un remplissage."""
        if cle is None:
            contour.start_point = None
            contour.end_point = None
            message = "Départ et arrivée du remplissage retirés (choix automatique)."
        else:
            if not (math.isfinite(point.x()) and math.isfinite(point.y())):
                return
            setattr(contour, cle, (point.x(), point.y()))
            nom = "de départ" if cle == "start_point" else "d'arrivée"
            message = (
                f"Point {nom} du remplissage placé à "
                f"{point.x():.1f} ; {-point.y():.1f} mm."
            )
        self.refresh_overlay()
        self.changed.emit()
        self.status_message.emit(message)

    def start_hole_drawing(self):
        if self.current is None or self.current.stitch_type != "fill" or self.current_hole is not None:
            return
        self.current_hole = Contour(
            closed=True,
            stitch_type="running",
            thread_color=self.current.thread_color,
        )
        self.refresh_overlay()
        self.status_message.emit("Tracez le contour du trou, puis terminez-le pour l'ajouter au remplissage.")

    def show_context_menu(self, event):
        point = self.mapToScene(event.position().toPoint())
        en_dessin = self.current is not None
        if en_dessin:
            cible = self.current
        else:
            cible = self.contour_at(point)
            self.select(cible)  # None = on désélectionne

        menu = QMenu(self)

        if cible is None:
            self._add_action(menu, "Ajuster au cadre", self.fit_to_frame)
            menu.exec(event.globalPosition().toPoint())
            return

        if en_dessin and self.current is not None and self.current.stitch_type == "fill":
            self._add_action(
                menu,
                "Insérer un trou",
                self.start_hole_drawing,
                enabled=self.current_hole is None,
            )
            self._add_action(
                menu,
                "Terminer le trou",
                self.finish_contour,
                enabled=self.current_hole is not None and len(self.current_hole.points) >= 2,
            )
            menu.addSeparator()

        self._add_action(
            menu, "Finir le dessin", self.finish_contour,
            enabled=en_dessin and len(cible.points) >= 2,
        )
        menu.addSeparator()

        sous_menu_type = menu.addMenu("Changer le type de point")
        for cle, nom in (("running", "Running stitch"), ("satin", "Satin"), ("fill", "Fill")):
            action = sous_menu_type.addAction(nom)
            action.setCheckable(True)
            action.setChecked(cible.stitch_type == cle)
            action.triggered.connect(
                lambda checked=False, choisi=cle: self.set_stitch_type(cible, choisi)
            )

        self._add_action(
            menu, "Changer les paramètres...", lambda: self.edit_settings(cible)
        )

        sous_menu_sens = menu.addMenu("Définir début et fin")
        self._add_action(
            sous_menu_sens,
            "Inverser le sens (le début devient la fin)",
            lambda: self.reverse_contour(cible),
            enabled=len(cible.points) >= 2,
        )
        if cible.stitch_type == "fill" and not en_dessin:
            sous_menu_sens.addSeparator()
            self._add_action(
                sous_menu_sens,
                "Placer le point de départ du remplissage ici",
                lambda: self._place_fill_point(cible, "start_point", point),
            )
            self._add_action(
                sous_menu_sens,
                "Placer le point d'arrivée du remplissage ici",
                lambda: self._place_fill_point(cible, "end_point", point),
            )
            if cible.start_point is not None or cible.end_point is not None:
                self._add_action(
                    sous_menu_sens,
                    "Retirer le départ et l'arrivée du remplissage",
                    lambda: self._place_fill_point(cible, None, None),
                )

        menu.addSeparator()
        self._add_action(
            menu, "Propriétés du dessin...", lambda: self.show_properties(cible)
        )

        menu.addSeparator()
        if en_dessin:
            self._add_action(menu, "Annuler le dernier point", self.undo_last_point)
            self._add_action(menu, "Annuler le dessin", self.cancel_drawing)
        else:
            self._add_action(menu, "Supprimer le dessin", lambda: self.delete_contour(cible))

        menu.exec(event.globalPosition().toPoint())

    # ---------- Affichage des contours et des points ----------
    def refresh_overlay(self):
        for item in self.overlay_items:
            self.work_scene.removeItem(item)
        self.overlay_items = []

        if self.machine_pattern is not None:
            self.draw_machine_pattern(self.machine_pattern)
            self.stitch_count_changed.emit(self.total_stitches())
            return

        for contour in self.contours:
            if contour is self.selected:
                self.draw_contour(contour, COULEUR_SELECTION, markers=True, width=3)
                self.draw_start_end(contour, with_fill_points=True)
                self.draw_resize_handles(contour)
                self.draw_rotation_handle(contour)
                if self.show_stitches:
                    self.draw_stitches(contour)
            elif self.show_stitches:
                self.draw_contour(contour, contour.thread_color, markers=False, width=1)
                self.draw_stitches(contour)
            else:
                self.draw_contour(contour, contour.thread_color)

        if self.current is not None:
            self.draw_contour(self.current, COULEUR_EN_COURS)
            self.draw_start_end(self.current, with_end=False)
        if self.current_hole is not None:
            self.draw_contour(self.current_hole, "#7a5ef8", width=1)
            self.draw_start_end(self.current_hole, with_end=False)

        self.stitch_count_changed.emit(self.total_stitches())

    def draw_machine_pattern(self, pattern):
        """Dessine les points, sauts et changements de couleur du motif importé."""
        palette = self._machine_palette(pattern)
        previous = (0.0, 0.0)
        paths = {}
        jump_path = QPainterPath()
        for command in pattern.commands:
            current = (command.x, command.y)
            if command.kind == "jump":
                jump_path.moveTo(QPointF(*previous))
                jump_path.lineTo(QPointF(*current))
            elif command.kind == "stitch":
                path = paths.setdefault(command.color, QPainterPath())
                if path.isEmpty():
                    path.moveTo(QPointF(*previous))
                path.lineTo(QPointF(*current))
            previous = current
        for color, path in paths.items():
            pen = QPen(QColor(palette[color % len(palette)]), 1.6)
            pen.setCosmetic(True)
            item = self.work_scene.addPath(path, pen)
            item.setZValue(12)
            self.overlay_items.append(item)
        if not jump_path.isEmpty():
            pen = QPen(QColor("#8a8f98"), 1, Qt.DashLine)
            pen.setCosmetic(True)
            item = self.work_scene.addPath(jump_path, pen)
            item.setZValue(11)
            self.overlay_items.append(item)

    @staticmethod
    def _machine_palette(pattern):
        colors = list(pattern.thread_colors or [])
        return colors or list(DEFAULT_THREAD_COLORS)

    def draw_contour(self, contour, color, markers=True, width=2):
        if not contour.points:
            return

        # La ligne (avec ses courbes), refermée pour un contour fermé :
        # le moteur de remplissage brode sur le polygone fermé, la référence
        # affichée doit donc montrer le même tronçon de fermeture.
        flat = contour.flatten()
        if (
            contour.closed
            and len(flat) >= 2
            and (abs(flat[0][0] - flat[-1][0]) > 1e-9 or abs(flat[0][1] - flat[-1][1]) > 1e-9)
        ):
            flat = flat + [flat[0]]
        path = QPainterPath(QPointF(*flat[0]))
        for x, y in flat[1:]:
            path.lineTo(x, y)
        pen = QPen(QColor(color), width)
        pen.setCosmetic(True)  # épaisseur constante quelle que soit le zoom
        line = self.work_scene.addPath(path, pen)
        line.setZValue(10)
        self.overlay_items.append(line)

        if not markers:
            return

        # Les points : carré = point droit, rond = point de courbe
        for x, y, kind in contour.points:
            if kind == CORNER:
                dot = QGraphicsRectItem(-3.5, -3.5, 7, 7)
            else:
                dot = QGraphicsEllipseItem(-3.5, -3.5, 7, 7)
            dot.setBrush(QBrush(QColor(color)))
            dot.setPen(QPen(Qt.NoPen))
            dot.setFlag(QGraphicsItem.ItemIgnoresTransformations)
            dot.setPos(x, y)
            dot.setZValue(11)
            self.work_scene.addItem(dot)
            self.overlay_items.append(dot)

    def draw_start_end(self, contour, with_end=True, with_fill_points=False):
        """Étiquettes « Début » (vert) et « Fin » (rouge)."""
        if not contour.points:
            return
        self._draw_label(contour.points[0], "Début", COULEUR_DEBUT)
        if with_end and len(contour.points) >= 2:
            self._draw_label(contour.points[-1], "Fin", COULEUR_FIN)
        if with_fill_points and contour.stitch_type == "fill":
            # Départ et arrivée choisis par l'utilisateur pour le remplissage.
            if contour.start_point is not None:
                self._draw_fill_marker(contour.start_point, COULEUR_DEBUT)
                self._draw_label(contour.start_point, "Départ", COULEUR_DEBUT)
            if contour.end_point is not None:
                self._draw_fill_marker(contour.end_point, COULEUR_FIN)
                self._draw_label(contour.end_point, "Arrivée", COULEUR_FIN)

    def _draw_fill_marker(self, point, couleur):
        """Marqueur en croix pour le départ/l'arrivée d'un remplissage."""
        longueur = 6.0
        for dx, dy in ((1, 0), (0, 1)):
            segment = self.work_scene.addLine(
                point[0] - longueur * dx, point[1] - longueur * dy,
                point[0] + longueur * dx, point[1] + longueur * dy,
            )
            segment.setPen(QPen(QColor(couleur), 2))
            segment.setZValue(15)
            self.overlay_items.append(segment)

    def draw_resize_handles(self, contour):
        """Dessine une boîte et quatre poignées autour du contour sélectionné."""
        x0, y0, x1, y1 = contour.bounds()
        cadre = QGraphicsRectItem(QRectF(x0, y0, x1 - x0, y1 - y0))
        cadre.setPen(QPen(QColor("#e0a600"), 1, Qt.DashLine))
        cadre.setBrush(QBrush(Qt.NoBrush))
        cadre.setZValue(13)
        self.work_scene.addItem(cadre)
        self.overlay_items.append(cadre)

        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            poignee = QGraphicsRectItem(-5, -5, 10, 10)
            poignee.setBrush(QBrush(QColor("white")))
            poignee.setPen(QPen(QColor("#1d6fe0"), 1))
            poignee.setFlag(QGraphicsItem.ItemIgnoresTransformations)
            poignee.setPos(x, y)
            poignee.setZValue(14)
            self.work_scene.addItem(poignee)
            self.overlay_items.append(poignee)

    def resize_handle_at(self, point):
        """Retourne l'index de la poignée proche du point, ou None."""
        if self.selected is None:
            return None
        x0, y0, x1, y1 = self.selected.bounds()
        coins = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
        tolerance = 10 / max(self.transform().m11(), 1e-9)
        distances = [
            (math.hypot(point.x() - x, point.y() - y), index)
            for index, (x, y) in enumerate(coins)
        ]
        distance, index = min(distances)
        return index if distance <= tolerance else None

    def resize_selected(self, handle, point):
        """Redimensionne le contour sélectionné depuis une poignée."""
        if self.selected is None or self._resize_bounds is None or self._resize_points is None:
            return False
        x0, y0, x1, y1 = self._resize_bounds
        fixes = ((x1, y1), (x0, y1), (x0, y0), (x1, y0))
        fixed_x, fixed_y = fixes[handle]
        if handle in (0, 3):
            new_x0, new_x1 = min(point.x(), fixed_x - 0.1), fixed_x
        else:
            new_x0, new_x1 = fixed_x, max(point.x(), fixed_x + 0.1)
        if handle in (0, 1):
            new_y0, new_y1 = min(point.y(), fixed_y - 0.1), fixed_y
        else:
            new_y0, new_y1 = fixed_y, max(point.y(), fixed_y + 0.1)

        old_width = x1 - x0
        old_height = y1 - y0
        scale_x = (new_x1 - new_x0) / old_width if old_width > 1e-9 else 1.0
        scale_y = (new_y1 - new_y0) / old_height if old_height > 1e-9 else 1.0
        self.selected.points = [
            (
                fixed_x + (x - fixed_x) * scale_x,
                fixed_y + (y - fixed_y) * scale_y,
                kind,
            )
            for x, y, kind in self._resize_points
        ]
        self.refresh_overlay()
        self.selection_changed.emit()
        return True

    def resize_selected_dimensions(self, width, height):
        """Applique une largeur et une hauteur précises au dessin sélectionné."""
        if self.selected is None:
            return False
        width = float(width)
        height = float(height)
        if not math.isfinite(width) or not math.isfinite(height) or width < 0 or height < 0:
            return False

        x0, y0, x1, y1 = self.selected.bounds()
        old_width = x1 - x0
        old_height = y1 - y0
        has_width = old_width > 1e-9
        has_height = old_height > 1e-9
        if not has_width and not has_height:
            return False
        if (has_width and width <= 0) or (has_height and height <= 0):
            return False

        centre_x = (x0 + x1) / 2
        centre_y = (y0 + y1) / 2
        scale_x = width / old_width if has_width else 1.0
        scale_y = height / old_height if has_height else 1.0
        points = []
        for x, y, kind in self.selected.points:
            new_x = centre_x + (x - centre_x) * scale_x if has_width else centre_x
            new_y = centre_y + (y - centre_y) * scale_y if has_height else centre_y
            if not has_height and height > 1e-9:
                new_y = centre_y + (new_x - centre_x) * height / width
            if not has_width and width > 1e-9:
                new_x = centre_x + (new_y - centre_y) * width / height
            points.append((new_x, new_y, kind))
        self.selected.points = points
        self.refresh_overlay()
        self.selection_changed.emit()
        self.changed.emit()
        self.status_message.emit(f"Dimensions : {width:.1f} × {height:.1f} mm.")
        return True

    def rotate_selected(self, angle_degrees, center=None, source_points=None):
        """Tourne le dessin sélectionné autour de son centre, en degrés."""
        if self.selected is None:
            return False
        if center is None:
            x0, y0, x1, y1 = self.selected.bounds()
            center = ((x0 + x1) / 2, (y0 + y1) / 2)
        points = self._rotation_points if source_points is None else source_points
        if points is None:
            points = list(self.selected.points)
        radians = math.radians(angle_degrees)
        cosinus = math.cos(radians)
        sinus = math.sin(radians)
        cx, cy = center
        self.selected.points = [
            (
                cx + (x - cx) * cosinus - (y - cy) * sinus,
                cy + (x - cx) * sinus + (y - cy) * cosinus,
                kind,
            )
            for x, y, kind in points
        ]
        self.refresh_overlay()
        self.selection_changed.emit()
        return True

    def rotation_handle_at(self, point):
        """Retourne True si le point est proche de la poignée de rotation."""
        if self.selected is None:
            return False
        x0, y0, x1, _ = self.selected.bounds()
        centre_x = (x0 + x1) / 2
        distance = 12 / max(self.transform().m11(), 1e-9)
        return math.hypot(point.x() - centre_x, point.y() - (y0 - distance)) <= distance

    def draw_rotation_handle(self, contour):
        """Dessine une poignée ronde au-dessus du dessin sélectionné."""
        x0, y0, x1, _ = contour.bounds()
        distance = 12 / max(self.transform().m11(), 1e-9)
        centre_x = (x0 + x1) / 2
        ligne = self.work_scene.addLine(
            centre_x, y0, centre_x, y0 - distance,
            QPen(QColor("#1d6fe0"), 1, Qt.DashLine),
        )
        ligne.setZValue(13)
        self.overlay_items.append(ligne)
        poignee = QGraphicsEllipseItem(-5, -5, 10, 10)
        poignee.setBrush(QBrush(QColor("white")))
        poignee.setPen(QPen(QColor("#1d6fe0"), 1))
        poignee.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        poignee.setPos(centre_x, y0 - distance)
        poignee.setZValue(14)
        self.work_scene.addItem(poignee)
        self.overlay_items.append(poignee)

    def _draw_label(self, point, texte, couleur):
        etiquette = QGraphicsSimpleTextItem(texte)
        etiquette.setBrush(QBrush(QColor(couleur)))
        police = etiquette.font()
        police.setBold(True)
        etiquette.setFont(police)
        etiquette.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        etiquette.setTransform(QTransform.fromTranslate(6, -22))
        etiquette.setPos(point[0], point[1])
        etiquette.setZValue(15)
        self.work_scene.addItem(etiquette)
        self.overlay_items.append(etiquette)

    def draw_stitches(self, contour):
        """Dessine le fil de la broderie (et les points d'aiguille pour le running stitch)."""
        try:
            paths = stitch_paths(contour)
        except ValueError:
            paths = []
        if not paths:
            return

        epaisseur = 1.5 if contour.stitch_type == "running" else 1
        pen = QPen(QColor(contour.thread_color), epaisseur)
        pen.setCosmetic(True)
        for points in paths:
            if len(points) < 2:
                continue
            path = QPainterPath(QPointF(*points[0]))
            for x, y in points[1:]:
                path.lineTo(x, y)
            thread = self.work_scene.addPath(path, pen)
            thread.setZValue(12)
            self.overlay_items.append(thread)

        if contour.stitch_type != "running":
            return  # satin : trop de points pour dessiner un rond sur chacun

        dot_pen = QPen(QColor(contour.thread_color), 1)
        for points in paths:
            for x, y in points:
                dot = QGraphicsEllipseItem(-2, -2, 4, 4)
                dot.setBrush(QBrush(QColor("white")))
                dot.setPen(dot_pen)
                dot.setFlag(QGraphicsItem.ItemIgnoresTransformations)
                dot.setPos(x, y)
                dot.setZValue(13)
                self.work_scene.addItem(dot)
                self.overlay_items.append(dot)

    # ---------- Axes qui suivent la souris ----------
    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        if not self.show_crosshair or self.cursor_pos is None:
            return
        pen = QPen(QColor(230, 120, 0, 170), 1, Qt.DashLine)
        pen.setCosmetic(True)
        painter.setPen(pen)
        x = self.cursor_pos.x()
        y = self.cursor_pos.y()
        painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
        painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))

    def leaveEvent(self, event):
        self.cursor_pos = None
        self.viewport().update()
        super().leaveEvent(event)

    # ---------- Souris et clavier ----------
    def mouseMoveEvent(self, event):
        point = self.mapToScene(event.position().toPoint())
        self.cursor_pos = point
        self.mouse_moved.emit(point.x(), point.y())
        if (
            self.tool == "rotate"
            and self._rotation_center is not None
            and self.press_point is not None
            and self._rotation_start_angle is not None
        ):
            cx, cy = self._rotation_center
            angle = math.degrees(math.atan2(point.y() - cy, point.x() - cx))
            delta = angle - self._rotation_start_angle
            self.rotate_selected(
                delta,
                center=self._rotation_center,
                source_points=self._rotation_points,
            )
            self.selection_dragged = True
            self.viewport().update()
            return
        if self.tool in ("select", "resize") and self._resize_handle is not None:
            self.resize_selected(self._resize_handle, point)
            self.selection_dragged = True
            self.viewport().update()
            return
        if self.tool == "select" and self.press_point is not None and self.selected is not None:
            dx = point.x() - self.press_point.x()
            dy = point.y() - self.press_point.y()
            if dx or dy:
                self.move_selected(dx, dy)
                self.press_point = point
                self.selection_dragged = True
            self.viewport().update()
            return
        self.viewport().update()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.show_context_menu(event)
            return
        if self.tool in ("select", "resize") and event.button() == Qt.LeftButton:
            point = self.mapToScene(event.position().toPoint())
            handle = self.resize_handle_at(point)
            if handle is not None:
                self._resize_handle = handle
                self._resize_bounds = self.selected.bounds()
                self._resize_points = list(self.selected.points)
                self.selection_dragged = False
                return
            self.select(self.contour_at(point))
            self.press_point = (
                point if self.tool == "select" and self.selected is not None else None
            )
            self.selection_dragged = False
            return
        if self.tool == "rotate" and event.button() == Qt.LeftButton:
            point = self.mapToScene(event.position().toPoint())
            cible = self.selected if self.rotation_handle_at(point) else self.contour_at(point)
            if cible is not None and cible is not self.selected:
                self.select(cible)
            if self.selected is None:
                return
            cx0, cy0, cx1, cy1 = self.selected.bounds()
            self._rotation_center = ((cx0 + cx1) / 2, (cy0 + cy1) / 2)
            cx, cy = self._rotation_center
            self._rotation_start_angle = math.degrees(
                math.atan2(point.y() - cy, point.x() - cx)
            )
            self._rotation_points = list(self.selected.points)
            self.press_point = point
            self.selection_dragged = False
            return
        if self.tool != "contour":
            super().mousePressEvent(event)
            return
        if event.button() == Qt.LeftButton:
            # On note où et quand on a appuyé ; le point est ajouté au relâchement.
            self.press_point = self.mapToScene(event.position().toPoint())
            self.press_time = time.monotonic()

    def mouseReleaseEvent(self, event):
        if self.tool in ("select", "resize") and event.button() == Qt.LeftButton:
            if self.selection_dragged:
                self.changed.emit()
                self.status_message.emit(
                    "Dessin redimensionné." if self._resize_handle is not None else "Dessin déplacé."
                )
            self.press_point = None
            self.selection_dragged = False
            self._resize_handle = None
            self._resize_bounds = None
            self._resize_points = None
            return
        if self.tool == "rotate" and event.button() == Qt.LeftButton:
            if self.selection_dragged:
                self.changed.emit()
                self.status_message.emit("Dessin tourné.")
            self.press_point = None
            self.selection_dragged = False
            self._rotation_center = None
            self._rotation_start_angle = None
            self._rotation_points = None
            return
        if (
            self.tool == "contour"
            and event.button() == Qt.LeftButton
            and self.press_point is not None
        ):
            duree_ms = (time.monotonic() - self.press_time) * 1000
            kind = CORNER if duree_ms >= LONG_CLICK_MS else CURVE
            self.add_point(self.press_point, kind)
            self.press_point = None
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        touche = event.key()
        if self.current is not None:
            if touche == Qt.Key_Backspace:
                self.undo_last_point()
                return
            if touche == Qt.Key_Escape:
                self.cancel_drawing()
                return
            if touche in (Qt.Key_Return, Qt.Key_Enter):
                self.finish_contour()
                return
        elif self.selected is not None:
            if touche == Qt.Key_Escape:
                if self._rotation_points is not None and self._rotation_center is not None:
                    self.selected.points = list(self._rotation_points)
                    self.refresh_overlay()
                    self._rotation_points = None
                    self._rotation_center = None
                    self._rotation_start_angle = None
                    self.press_point = None
                self.select(None)
                return
            if touche == Qt.Key_Delete:
                self.delete_contour(self.selected)
                return
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)
        self._emit_zoom()
