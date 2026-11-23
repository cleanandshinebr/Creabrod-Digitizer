from PySide6.QtWidgets import (
    QToolBar,
    QLabel,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QSizePolicy,
    QWidget,
)
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QStyle
from PySide6.QtCore import Qt

from core.objects import (
    FILL_SPACING_MIN,
    FILL_SPACING_MAX,
    SATIN_WIDTH_MIN,
    SATIN_WIDTH_MAX,
    SATIN_SPACING_MIN,
    SATIN_SPACING_MAX,
)

NOMS_OUTILS = {
    "select": "Sélection",
    "move": "Déplacer la vue",
    "resize": "Redimensionner",
    "contour": "Contour",
}


def cadre_info(texte, largeur_min):
    """Petite case en relief pour afficher une information (position, compteur...)."""
    etiquette = QLabel(texte)
    etiquette.setFrameShape(QFrame.StyledPanel)
    etiquette.setFrameShadow(QFrame.Sunken)
    etiquette.setMinimumWidth(largeur_min)
    etiquette.setAlignment(Qt.AlignCenter)
    return etiquette


class ContextToolbar(QToolBar):
    """Barre du haut. Son contenu change selon l'outil actif et le type de point choisi."""

    def __init__(self, canvas, parent=None):
        super().__init__("Barre contextuelle", parent)
        self.setMovable(False)
        self.outil = "move"
        # Éléments propres à chaque situation
        self.groupes = {"move": [], "contour": [], "running": [], "satin": [], "fill": []}

        # ----- Toujours visibles : position et nom de l'outil -----
        self.label_position = cadre_info("0.0 , 0.0 mm", 150)
        self.addWidget(self.label_position)
        self.addSeparator()

        self.label_outil = QLabel("")
        police = self.label_outil.font()
        police.setBold(True)
        self.label_outil.setFont(police)
        self.addWidget(self.label_outil)
        self.addSeparator()

        # ----- Outil Contour : type de point -----
        self._ajouter("contour", self.addWidget(QLabel(" Type : ")))

        self.combo_type = QComboBox()
        self.combo_type.addItem("Running stitch", "running")
        self.combo_type.addItem("Satin", "satin")
        self.combo_type.addItem("Fill", "fill")
        self.combo_type.setToolTip("Type de point des nouveaux dessins")
        self._ajouter("contour", self.addWidget(self.combo_type))

        # ----- Running stitch -----
        self._ajouter("running", self.addWidget(QLabel("  Longueur : ")))
        self.spin_longueur = QDoubleSpinBox()
        self.spin_longueur.setRange(1.0, 7.0)
        self.spin_longueur.setSingleStep(0.1)
        self.spin_longueur.setDecimals(1)
        self.spin_longueur.setSuffix(" mm")
        self.spin_longueur.setValue(2.5)
        self.spin_longueur.setToolTip(
            "Longueur du point pour les nouveaux dessins. "
            "Pour un dessin existant : clic droit > Changer les paramètres."
        )
        self._ajouter("running", self.addWidget(self.spin_longueur))

        # ----- Satin -----
        self._ajouter("satin", self.addWidget(QLabel("  Largeur : ")))
        self.spin_largeur = QDoubleSpinBox()
        self.spin_largeur.setRange(SATIN_WIDTH_MIN, SATIN_WIDTH_MAX)
        self.spin_largeur.setSingleStep(0.1)
        self.spin_largeur.setDecimals(1)
        self.spin_largeur.setSuffix(" mm")
        self.spin_largeur.setValue(3.0)
        self.spin_largeur.setToolTip(
            "Largeur de la colonne satin pour les nouveaux dessins. "
            "Pour un dessin existant : clic droit > Changer les paramètres."
        )
        self._ajouter("satin", self.addWidget(self.spin_largeur))

        self._ajouter("satin", self.addWidget(QLabel("  Écart : ")))
        self.spin_ecart = QDoubleSpinBox()
        self.spin_ecart.setRange(SATIN_SPACING_MIN, SATIN_SPACING_MAX)
        self.spin_ecart.setSingleStep(0.05)
        self.spin_ecart.setDecimals(2)
        self.spin_ecart.setSuffix(" mm")
        self.spin_ecart.setValue(0.4)
        self.spin_ecart.setToolTip(
            "Écart entre deux piqûres du même côté : plus il est petit, plus la colonne est "
            "serrée. Réglage pour les nouveaux dessins."
        )
        self._ajouter("satin", self.addWidget(self.spin_ecart))

        # ----- Fill -----
        self._ajouter("fill", self.addWidget(QLabel("  Angle : ")))
        self.spin_angle_fill = QDoubleSpinBox()
        self.spin_angle_fill.setRange(0.0, 180.0)
        self.spin_angle_fill.setSingleStep(1.0)
        self.spin_angle_fill.setDecimals(0)
        self.spin_angle_fill.setSuffix("°")
        self.spin_angle_fill.setValue(0.0)
        self.spin_angle_fill.setToolTip("Angle de la direction du rembourrage pour les nouveaux dessins.")
        self._ajouter("fill", self.addWidget(self.spin_angle_fill))

        self._ajouter("fill", self.addWidget(QLabel("  Écart : ")))
        self.spin_ecart_fill = QDoubleSpinBox()
        self.spin_ecart_fill.setRange(FILL_SPACING_MIN, FILL_SPACING_MAX)
        self.spin_ecart_fill.setSingleStep(0.05)
        self.spin_ecart_fill.setDecimals(2)
        self.spin_ecart_fill.setSuffix(" mm")
        self.spin_ecart_fill.setValue(2.0)
        self.spin_ecart_fill.setToolTip("Écart entre deux rangées de remplissage pour les nouveaux dessins.")
        self._ajouter("fill", self.addWidget(self.spin_ecart_fill))

        # ----- Outil Contour : actions -----
        self._ajouter("contour", self.addSeparator())

        self.act_finish = QAction("Finir le dessin", self)
        self.act_finish.triggered.connect(lambda checked=False: canvas.finish_contour())
        self.addAction(self.act_finish)
        self._ajouter("contour", self.act_finish)

        self.act_undo = QAction("Annuler le dernier point", self)
        self.act_undo.triggered.connect(lambda checked=False: canvas.undo_last_point())
        self.addAction(self.act_undo)
        self._ajouter("contour", self.act_undo)

        # ----- Outil Déplacer la vue -----
        self.act_fit = QAction("Ajuster au cadre", self)
        self.act_fit.setIcon(self.style().standardIcon(QStyle.SP_DesktopIcon))
        self.act_fit.setToolTip("Ajuster la vue au cadre")
        self.act_fit.triggered.connect(lambda checked=False: canvas.fit_to_frame())
        self.addAction(self.act_fit)
        self._ajouter("move", self.act_fit)

        # ----- Toujours visibles : affichage -----
        self.addSeparator()

        self.act_points = QAction("Afficher les points", self)
        self.act_points.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.act_points.setCheckable(True)
        self.act_points.setChecked(True)
        self.act_points.toggled.connect(canvas.set_show_stitches)
        self.addAction(self.act_points)

        self.act_axes = QAction("Axes", self)
        self.act_axes.setIcon(self.style().standardIcon(QStyle.SP_ArrowRight))
        self.act_axes.setCheckable(True)
        self.act_axes.setChecked(True)
        self.act_axes.setToolTip("Afficher les axes X et Y qui suivent la souris")
        self.act_axes.toggled.connect(canvas.set_show_crosshair)
        self.addAction(self.act_axes)

        # ----- Compteur de points (à droite) -----
        espace = QWidget()
        espace.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.addWidget(espace)

        self.label_points = cadre_info("0 points", 110)
        self.addWidget(self.label_points)

        # ----- Connexions : les réglages de la barre sont envoyés à la zone de travail -----
        self.combo_type.currentIndexChanged.connect(
            lambda index: self._on_type_changed(canvas)
        )
        self.spin_longueur.valueChanged.connect(canvas.set_stitch_length)
        self.spin_largeur.valueChanged.connect(canvas.set_default_satin_width)
        self.spin_ecart.valueChanged.connect(canvas.set_default_satin_spacing)
        self.spin_angle_fill.valueChanged.connect(canvas.set_default_fill_angle)
        self.spin_ecart_fill.valueChanged.connect(canvas.set_default_fill_spacing)

        self.show_tool("move")

    def _ajouter(self, groupe, action):
        self.groupes[groupe].append(action)
        return action

    def _on_type_changed(self, canvas):
        canvas.set_default_stitch_type(self.combo_type.currentData())
        self._update_visibility()

    def _update_visibility(self):
        type_choisi = self.combo_type.currentData()
        contour = self.outil == "contour"
        visibles = {
            "move": self.outil == "move",
            "contour": contour,
            "running": contour and type_choisi == "running",
            "satin": contour and type_choisi == "satin",
            "fill": contour and type_choisi == "fill",
        }
        for nom, actions in self.groupes.items():
            for action in actions:
                action.setVisible(visibles[nom])

    def show_tool(self, outil):
        """Affiche uniquement les éléments de l'outil choisi."""
        self.outil = outil
        self.label_outil.setText(f"Outil : {NOMS_OUTILS.get(outil, outil)}")
        self._update_visibility()

    def set_position(self, x, y):
        # Affichage : Y positif vers le haut, comme sur une machine à broder.
        self.label_position.setText(f"{x:.1f} , {-y:.1f} mm")

    def set_stitch_count(self, nombre):
        texte = f"{nombre:,}".replace(",", " ")
        self.label_points.setText(f"{texte} points")
