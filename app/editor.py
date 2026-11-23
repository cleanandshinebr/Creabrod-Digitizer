import math

from core.ordering import move_item
from core.objects import (
    CONNECTION_MODES,
    FILL_SPACING_MAX,
    FILL_SPACING_MIN,
    SATIN_CORNER_MODES,
    SATIN_SPACING_MAX,
    SATIN_SPACING_MIN,
    SATIN_WIDTH_MAX,
    SATIN_WIDTH_MIN,
    STITCH_TYPES,
    UNDERLAY_TYPES,
)


class Editor:
    """Actions de modification des dessins (utilisées par le panneau de droite)."""

    def __init__(self, canvas):
        self.canvas = canvas

    def set_stitch_length(self, contour, valeur):
        """Change la longueur du point d'un dessin."""
        if abs(contour.stitch_length - valeur) < 1e-9:
            return
        contour.stitch_length = float(valeur)
        self.canvas.refresh_overlay()
        if contour is not self.canvas.current:
            self.canvas.changed.emit()

    def set_connection_mode(self, contour, mode):
        """Change la connexion vers le dessin suivant."""
        if mode not in CONNECTION_MODES or contour.connection_mode == mode:
            return
        contour.connection_mode = mode
        self.canvas.refresh_overlay()
        if contour is not self.canvas.current:
            self.canvas.changed.emit()
        self.canvas.status_message.emit(f"Connexion vers le dessin suivant : {mode}.")

    def set_stitch_type(self, contour, stitch_type):
        """Change le type de point d'un dessin existant."""
        if stitch_type not in STITCH_TYPES or contour.stitch_type == stitch_type:
            return
        contour.stitch_type = stitch_type
        if stitch_type == "fill":
            contour.closed = True
        self.canvas.refresh_overlay()
        if contour is not self.canvas.current:
            self.canvas.changed.emit()
        self.canvas.status_message.emit(f"Type de point : {stitch_type}.")

    def set_satin_width(self, contour, valeur):
        """Change la largeur d'une colonne satin."""
        valeur = float(valeur)
        if not SATIN_WIDTH_MIN <= valeur <= SATIN_WIDTH_MAX:
            return
        if abs(contour.satin_width - valeur) < 1e-9:
            return
        contour.satin_width = valeur
        self.canvas.refresh_overlay()
        if contour is not self.canvas.current:
            self.canvas.changed.emit()

    def set_satin_spacing(self, contour, valeur):
        """Change l'écart entre les points d'une colonne satin."""
        valeur = float(valeur)
        if not SATIN_SPACING_MIN <= valeur <= SATIN_SPACING_MAX:
            return
        if abs(contour.satin_spacing - valeur) < 1e-9:
            return
        contour.satin_spacing = valeur
        self.canvas.refresh_overlay()
        if contour is not self.canvas.current:
            self.canvas.changed.emit()
        self.canvas.status_message.emit(f"Écart du satin : {valeur:.2f} mm.")

    def set_fill_angle(self, contour, valeur):
        """Change l'angle d'un rembourrage simple."""
        valeur = float(valeur)
        if not math.isfinite(valeur):
            return
        if abs(contour.fill_angle - valeur) < 1e-9:
            return
        contour.fill_angle = valeur
        self.canvas.refresh_overlay()
        if contour is not self.canvas.current:
            self.canvas.changed.emit()
        self.canvas.status_message.emit(f"Angle de remplissage : {valeur:.1f}°.")

    def set_fill_spacing(self, contour, valeur):
        """Change l'écart entre les rangées d'un rembourrage simple."""
        valeur = float(valeur)
        if not FILL_SPACING_MIN <= valeur <= FILL_SPACING_MAX:
            return
        if abs(contour.fill_spacing - valeur) < 1e-9:
            return
        contour.fill_spacing = valeur
        self.canvas.refresh_overlay()
        if contour is not self.canvas.current:
            self.canvas.changed.emit()
        self.canvas.status_message.emit(f"Écart du remplissage : {valeur:.2f} mm.")

    def set_thread_color(self, contour, color):
        if not isinstance(color, str) or contour.thread_color.lower() == color.lower():
            return
        contour.thread_color = color.lower()
        self.canvas.refresh_overlay()
        if contour is not self.canvas.current:
            self.canvas.changed.emit()
        self.canvas.status_message.emit(f"Couleur de fil modifiée : {contour.thread_color}.")

    def set_satin_corner_mode(self, contour, mode):
        """Change la façon dont une colonne satin traite ses coins."""
        if mode not in SATIN_CORNER_MODES or contour.satin_corner_mode == mode:
            return
        contour.satin_corner_mode = mode
        self.canvas.refresh_overlay()
        if contour is not self.canvas.current:
            self.canvas.changed.emit()
        self.canvas.status_message.emit(f"Mode de coin satin : {mode}.")

    def set_underlays(self, contour, underlays):
        """Change les sous-couches sélectionnées, dans l'ordre affiché."""
        valeurs = [mode for mode in underlays if mode in UNDERLAY_TYPES]
        if contour.underlays == valeurs:
            return
        contour.underlays = valeurs
        self.canvas.refresh_overlay()
        if contour is not self.canvas.current:
            self.canvas.changed.emit()
        self.canvas.status_message.emit("Sous-couches mises à jour.")

    def move(self, contour, delta):
        """Monte (-1) ou descend (+1) un dessin dans l'ordre de broderie."""
        if move_item(self.canvas.contours, contour, delta):
            self.canvas.refresh_overlay()
            self.canvas.changed.emit()
            self.canvas.status_message.emit("Ordre de broderie modifié.")
