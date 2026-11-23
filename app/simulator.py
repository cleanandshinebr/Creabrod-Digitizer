import math
import time

from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainterPath, QPen, QTransform
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsSimpleTextItem,
)

from core.simulation import Progress, build_machine_sequence, build_sequence, count_table
from core.machine_pattern import DEFAULT_THREAD_COLORS

COULEUR_FIL = "#1b3a6b"
COULEUR_SAUT = "#8a8f98"
COULEUR_COUPE = "#d62828"
COULEUR_NUMEROS = "#1a7f37"
MAX_NUMEROS = 150        # on n'affiche pas plus d'environ 150 numéros
RAYON_COUPE_MM = 1.5     # taille de la croix qui marque une coupe de fil

NOMS_ETAPES = {
    "stitch": "Point",
    "jump": "Saut (jump)",
    "trim": "Coupe du fil (trim)",
    "color_change": "Changement de couleur",
}


class Simulator(QObject):
    """Rejoue la broderie point par point sur la zone de travail."""

    progress = Signal(object)        # envoie un objet Progress
    playing_changed = Signal(bool)   # lecture en cours ou non

    def __init__(self, canvas):
        super().__init__(canvas)
        self.canvas = canvas
        self.active = False

        self.steps = []
        self.table = [(0, 0, 0)]
        self.stitch_steps = []   # numéro d'étape de chaque point
        self.position = 0        # nombre d'étapes déjà brodées
        self.drawn = 0           # nombre d'étapes déjà dessinées à l'écran

        self.speed = 100.0       # étapes par seconde
        self.accumulator = 0.0
        self.last_time = 0.0

        self.show_numbers = False
        self.number_every = 1
        self.number_items = []   # liste de (numéro, élément graphique)

        self.thread = QPainterPath()   # le fil brodé
        self.thread_paths = {}
        self.jumps = QPainterPath()    # les sauts
        self.trims = QPainterPath()    # les coupes de fil
        self.thread_item = None
        self.thread_items = {}
        self.jump_item = None
        self.trim_item = None
        self.needle = None

        self.timer = QTimer(self)
        self.timer.setInterval(16)  # environ 60 images par seconde
        self.timer.timeout.connect(self._tick)

        # Ce signal est émis après chaque mise à jour de la zone de travail.
        canvas.stitch_count_changed.connect(self._on_canvas_refreshed)

    # ---------- Entrer / sortir du mode simulation ----------
    def enter(self):
        self.active = True
        self._reload(self._canvas_steps())

    def leave(self):
        self.pause()
        self.active = False
        self._destroy_items()
        self.canvas.refresh_overlay()  # les dessins normaux réapparaissent

    # ---------- Commandes ----------
    def set_speed(self, etapes_par_seconde):
        self.speed = float(etapes_par_seconde)

    def set_numbers(self, visible):
        self.show_numbers = bool(visible)
        if not self.active:
            return
        if self.show_numbers:
            self._update_numbers(self.table[self.drawn][0])
        else:
            self._clear_numbers()

    def play(self):
        if not self.active or not self.steps:
            return
        if self.position >= len(self.steps):
            self.seek(0)  # on relance depuis le début
        self.last_time = time.monotonic()
        self.accumulator = 0.0
        self.timer.start()
        self.playing_changed.emit(True)

    def pause(self):
        self.timer.stop()
        self.playing_changed.emit(False)

    def stop(self):
        self.pause()
        self.seek(0)

    def step(self, delta):
        """Avance (+1) ou recule (-1) d'une étape."""
        self.pause()
        self.seek(self.position + delta)

    def seek(self, index):
        if not self.active or not self._items_alive():
            return
        index = max(0, min(int(index), len(self.steps)))
        self.position = index
        self._render(index)
        self._emit_progress()

    def _tick(self):
        if not self._items_alive():
            self.pause()
            return
        maintenant = time.monotonic()
        self.accumulator += (maintenant - self.last_time) * self.speed
        self.last_time = maintenant
        avance = int(self.accumulator)
        if avance <= 0:
            return
        self.accumulator -= avance
        cible = min(self.position + avance, len(self.steps))
        self.seek(cible)
        if cible >= len(self.steps):
            self.pause()

    # ---------- Quand le motif change pendant la simulation ----------
    def _on_canvas_refreshed(self, nombre=0):
        if not self.active:
            return
        steps = self._canvas_steps()
        if steps != self.steps or not self._items_alive():
            self._reload(steps)
        else:
            self._hide_overlay()

    def _canvas_steps(self):
        if self.canvas.machine_pattern is not None:
            return build_machine_sequence(self.canvas.machine_pattern)
        return build_sequence(self.canvas.contours)

    def _hide_overlay(self):
        """Cache les dessins normaux : on ne voit que ce qui est déjà brodé."""
        for item in self.canvas.overlay_items:
            item.setVisible(False)

    def _reload(self, steps):
        self.timer.stop()
        self.playing_changed.emit(False)
        self._destroy_items()

        self.steps = steps
        self.table = count_table(steps)
        self.stitch_steps = [i for i, s in enumerate(steps) if s.kind == "stitch"]
        total = self.table[-1][0]
        self.number_every = max(1, math.ceil(total / MAX_NUMEROS))
        self.position = 0
        self.drawn = 0
        self.thread = QPainterPath()
        self.thread_paths = {}
        self.jumps = QPainterPath()
        self.trims = QPainterPath()

        self._create_items()
        self._hide_overlay()
        self._render(0)
        self._emit_progress()

    # ---------- Éléments graphiques ----------
    def _create_items(self):
        scene = self.canvas.work_scene

        pen_saut = QPen(QColor(COULEUR_SAUT), 1, Qt.DashLine)
        pen_saut.setCosmetic(True)
        self.jump_item = scene.addPath(QPainterPath(), pen_saut)
        self.jump_item.setZValue(29)

        pen_fil = QPen(QColor(COULEUR_FIL), 2)
        pen_fil.setCosmetic(True)
        self.thread_item = scene.addPath(QPainterPath(), pen_fil)
        self.thread_item.setZValue(30)
        if self.canvas.machine_pattern is not None:
            palette = self.canvas.machine_pattern.thread_colors or DEFAULT_THREAD_COLORS
            self.thread_item.setVisible(False)
            for index, color in enumerate(palette):
                pen_couleur = QPen(QColor(color), 2)
                pen_couleur.setCosmetic(True)
                item = scene.addPath(QPainterPath(), pen_couleur)
                item.setZValue(30)
                self.thread_items[index] = item
        else:
            self.thread_item.setVisible(False)
            for index, contour in enumerate(self.canvas.contours):
                pen_couleur = QPen(QColor(contour.thread_color), 2)
                pen_couleur.setCosmetic(True)
                item = scene.addPath(QPainterPath(), pen_couleur)
                item.setZValue(30)
                self.thread_items[index] = item

        pen_coupe = QPen(QColor(COULEUR_COUPE), 2)
        pen_coupe.setCosmetic(True)
        self.trim_item = scene.addPath(QPainterPath(), pen_coupe)
        self.trim_item.setZValue(31)

        self.needle = QGraphicsEllipseItem(-5, -5, 10, 10)
        self.needle.setBrush(QBrush(QColor(COULEUR_COUPE)))
        self.needle.setPen(QPen(QColor("white"), 1))
        self.needle.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.needle.setZValue(40)
        scene.addItem(self.needle)

    def _safe_remove(self, item):
        try:
            scene = item.scene()
            if scene is not None:
                scene.removeItem(item)
        except RuntimeError:
            pass  # l'élément a déjà été supprimé avec la scène

    def _destroy_items(self):
        for item in (self.thread_item, self.jump_item, self.trim_item, self.needle):
            if item is not None:
                self._safe_remove(item)
        for item in self.thread_items.values():
            self._safe_remove(item)
        self.thread_items = {}
        self.thread_item = None
        self.jump_item = None
        self.trim_item = None
        self.needle = None
        self._clear_numbers()

    def _items_alive(self):
        try:
            return (
                self.thread_item is not None
                and self.thread_item.scene() is self.canvas.work_scene
            )
        except RuntimeError:
            return False

    # ---------- Dessin de la simulation ----------
    def _position_after(self, i):
        if i < 0:
            return (0.0, 0.0)
        return (self.steps[i].x, self.steps[i].y)

    def _apply_step(self, i):
        step = self.steps[i]
        if step.kind == "stitch":
            precedente = self.steps[i - 1] if i > 0 else None
            if self.canvas.machine_pattern is not None:
                path = self.thread_paths.setdefault(step.color, QPainterPath())
                if (
                    precedente is not None
                    and precedente.kind == "stitch"
                    and precedente.obj == step.obj
                    and precedente.color == step.color
                ):
                    path.lineTo(step.x, step.y)
                else:
                    path.moveTo(step.x, step.y)
                self.thread = path
            elif self.canvas.contours:
                path = self.thread_paths.setdefault(step.obj, QPainterPath())
                if precedente is not None and precedente.kind == "stitch" and precedente.obj == step.obj:
                    path.lineTo(step.x, step.y)
                else:
                    path.moveTo(step.x, step.y)
                self.thread = path
            elif precedente is not None and precedente.kind == "stitch" and precedente.obj == step.obj:
                self.thread.lineTo(step.x, step.y)
            else:
                self.thread.moveTo(step.x, step.y)
        elif step.kind == "jump":
            px, py = self._position_after(i - 1)
            self.jumps.moveTo(px, py)
            self.jumps.lineTo(step.x, step.y)
        elif step.kind == "trim":
            r = RAYON_COUPE_MM
            self.trims.moveTo(step.x - r, step.y - r)
            self.trims.lineTo(step.x + r, step.y + r)
            self.trims.moveTo(step.x - r, step.y + r)
            self.trims.lineTo(step.x + r, step.y - r)

    def _render(self, cible):
        if cible < self.drawn:  # on recule : on redessine depuis le début
            self.thread = QPainterPath()
            self.thread_paths = {}
            self.jumps = QPainterPath()
            self.trims = QPainterPath()
            self.drawn = 0
        for i in range(self.drawn, cible):
            self._apply_step(i)
        self.drawn = cible

        if self.thread_items:
            for color, item in self.thread_items.items():
                item.setPath(self.thread_paths.get(color, QPainterPath()))
        else:
            self.thread_item.setPath(self.thread)
        self.jump_item.setPath(self.jumps)
        self.trim_item.setPath(self.trims)

        x, y = self._position_after(cible - 1)
        self.needle.setPos(x, y)
        self.needle.setVisible(bool(self.steps))

        self._update_numbers(self.table[cible][0])

    # ---------- Numéros des points (ordre de broderie) ----------
    def _clear_numbers(self):
        for _, item in self.number_items:
            self._safe_remove(item)
        self.number_items = []

    def _update_numbers(self, faits):
        if not self.show_numbers or not self._items_alive():
            return

        # On retire les numéros des points pas encore brodés (quand on recule).
        while self.number_items and self.number_items[-1][0] > faits:
            _, item = self.number_items.pop()
            self._safe_remove(item)

        # On ajoute les numéros des points qui viennent d'être brodés.
        dernier = self.number_items[-1][0] if self.number_items else 0
        for numero in range(dernier + 1, faits + 1):
            if (numero - 1) % self.number_every != 0:
                continue
            step = self.steps[self.stitch_steps[numero - 1]]
            etiquette = QGraphicsSimpleTextItem(str(numero))
            etiquette.setBrush(QBrush(QColor(COULEUR_NUMEROS)))
            etiquette.setFlag(QGraphicsItem.ItemIgnoresTransformations)
            etiquette.setTransform(QTransform.fromTranslate(4, -14))
            etiquette.setPos(step.x, step.y)
            etiquette.setZValue(34)
            self.canvas.work_scene.addItem(etiquette)
            self.number_items.append((numero, etiquette))

    # ---------- Avancement ----------
    def _describe(self):
        if not self.steps:
            return "Rien à simuler : dessinez d'abord un contour."
        if self.position == 0:
            return "Prêt : appuyez sur Lecture."
        if self.position >= len(self.steps):
            return "Terminé."
        step = self.steps[self.position - 1]
        return f"Dessin n° {step.obj + 1:02d} · {NOMS_ETAPES[step.kind]}"

    def _emit_progress(self):
        faits, sauts, coupes = self.table[self.position]
        total, sauts_total, coupes_total = self.table[-1]
        couleurs = sum(step.kind == "color_change" for step in self.steps[:self.position])
        couleurs_total = sum(step.kind == "color_change" for step in self.steps)
        self.progress.emit(
            Progress(
                position=self.position,
                steps_total=len(self.steps),
                stitches=faits,
                stitches_total=total,
                jumps=sauts,
                jumps_total=sauts_total,
                trims=coupes,
                trims_total=coupes_total,
                colors=couleurs,
                colors_total=couleurs_total,
                description=self._describe(),
            )
        )
