from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QComboBox,
    QDoubleSpinBox,
    QDialogButtonBox,
    QLabel,
    QCheckBox,
    QVBoxLayout,
    QWidget,
)

from core.objects import (
    FILL_SPACING_MIN,
    FILL_SPACING_MAX,
    SATIN_WIDTH_MIN,
    SATIN_WIDTH_MAX,
    SATIN_SPACING_MIN,
    SATIN_SPACING_MAX,
    SATIN_CORNER_MODES,
    UNDERLAY_TYPES,
)

NOMS_COINS_SATIN = {
    "continuous": "Coin continu",
    "insertion": "Coin par insertion",
    "square_miter": "Coin carré biseauté",
}
NOMS_SOUS_COUCHES = {
    "centerline": "Centrale",
    "walking": "Marche à suivre",
    "zigzag": "Zigzag",
}


class StitchSettingsDialog(QDialog):
    """Fenêtre « Paramètres du dessin » : type de point et réglages."""

    def __init__(self, contour, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Paramètres du dessin")
        self.formulaire = QFormLayout(self)

        # ----- Type de point -----
        self.combo_type = QComboBox()
        self.combo_type.addItem("Running stitch", "running")
        self.combo_type.addItem("Satin", "satin")
        self.combo_type.addItem("Fill", "fill")
        self.combo_type.setCurrentIndex(max(0, self.combo_type.findData(contour.stitch_type)))
        self.formulaire.addRow("Type de point :", self.combo_type)

        # ----- Running stitch -----
        self.spin_longueur = QDoubleSpinBox()
        self.spin_longueur.setRange(1.0, 7.0)
        self.spin_longueur.setSingleStep(0.1)
        self.spin_longueur.setDecimals(1)
        self.spin_longueur.setSuffix(" mm")
        self.spin_longueur.setValue(contour.stitch_length)
        self.formulaire.addRow("Longueur du point :", self.spin_longueur)

        # ----- Satin -----
        self.spin_largeur = QDoubleSpinBox()
        self.spin_largeur.setRange(SATIN_WIDTH_MIN, SATIN_WIDTH_MAX)
        self.spin_largeur.setSingleStep(0.1)
        self.spin_largeur.setDecimals(1)
        self.spin_largeur.setSuffix(" mm")
        self.spin_largeur.setValue(contour.satin_width)
        self.formulaire.addRow("Largeur de la colonne :", self.spin_largeur)

        self.spin_ecart = QDoubleSpinBox()
        self.spin_ecart.setRange(SATIN_SPACING_MIN, SATIN_SPACING_MAX)
        self.spin_ecart.setSingleStep(0.05)
        self.spin_ecart.setDecimals(2)
        self.spin_ecart.setSuffix(" mm")
        self.spin_ecart.setValue(contour.satin_spacing)
        self.spin_ecart.setToolTip("Plus l'écart est petit, plus la colonne est serrée.")
        self.formulaire.addRow("Écart entre les points :", self.spin_ecart)

        self.spin_angle_remplissage = QDoubleSpinBox()
        self.spin_angle_remplissage.setRange(0.0, 180.0)
        self.spin_angle_remplissage.setSingleStep(1.0)
        self.spin_angle_remplissage.setDecimals(0)
        self.spin_angle_remplissage.setSuffix("°")
        self.spin_angle_remplissage.setValue(contour.fill_angle)
        self.formulaire.addRow("Angle de remplissage :", self.spin_angle_remplissage)

        self.spin_ecart_remplissage = QDoubleSpinBox()
        self.spin_ecart_remplissage.setRange(FILL_SPACING_MIN, FILL_SPACING_MAX)
        self.spin_ecart_remplissage.setSingleStep(0.05)
        self.spin_ecart_remplissage.setDecimals(2)
        self.spin_ecart_remplissage.setSuffix(" mm")
        self.spin_ecart_remplissage.setValue(contour.fill_spacing)
        self.formulaire.addRow("Écart de remplissage :", self.spin_ecart_remplissage)

        self.combo_coin_satin = QComboBox()
        for mode in SATIN_CORNER_MODES:
            self.combo_coin_satin.addItem(NOMS_COINS_SATIN[mode], mode)
        self.combo_coin_satin.setCurrentIndex(
            max(0, self.combo_coin_satin.findData(contour.satin_corner_mode))
        )
        self.formulaire.addRow("Coins du satin :", self.combo_coin_satin)

        self.sous_couches = {}
        sous_couches_widget = QWidget()
        sous_couches_layout = QVBoxLayout(sous_couches_widget)
        for mode in UNDERLAY_TYPES:
            case = QCheckBox(NOMS_SOUS_COUCHES[mode])
            case.setChecked(mode in contour.underlays)
            self.sous_couches[mode] = case
            sous_couches_layout.addWidget(case)
        self.formulaire.addRow("Sous-couches :", sous_couches_widget)
        self.sous_couches_widget = sous_couches_widget

        self.note = QLabel(
            "Valeurs de départ : à ajuster selon votre tissu, votre fil et votre machine."
        )
        self.note.setWordWrap(True)
        self.formulaire.addRow(self.note)

        # ----- Boutons -----
        boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        boutons.button(QDialogButtonBox.Ok).setText("OK")
        boutons.button(QDialogButtonBox.Cancel).setText("Annuler")
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        self.formulaire.addRow(boutons)

        self.combo_type.currentIndexChanged.connect(self._on_type)
        self._on_type()

    def _on_type(self):
        """Montre uniquement les réglages qui concernent le type choisi."""
        type_dessin = self.combo_type.currentData()
        satin = type_dessin == "satin"
        fill = type_dessin == "fill"
        self.formulaire.setRowVisible(self.spin_longueur, not satin and not fill)
        self.formulaire.setRowVisible(self.spin_largeur, satin)
        self.formulaire.setRowVisible(self.spin_ecart, satin)
        self.formulaire.setRowVisible(self.spin_angle_remplissage, fill)
        self.formulaire.setRowVisible(self.spin_ecart_remplissage, fill)
        self.formulaire.setRowVisible(self.combo_coin_satin, satin)
        self.formulaire.setRowVisible(self.sous_couches_widget, satin)
        self.formulaire.setRowVisible(self.note, satin)

    def apply_to(self, contour):
        """Applique les réglages choisis au dessin."""
        contour.stitch_type = self.combo_type.currentData()
        contour.stitch_length = self.spin_longueur.value()
        contour.satin_width = self.spin_largeur.value()
        contour.satin_spacing = self.spin_ecart.value()
        contour.fill_angle = self.spin_angle_remplissage.value()
        contour.fill_spacing = self.spin_ecart_remplissage.value()
        contour.satin_corner_mode = self.combo_coin_satin.currentData()
        contour.underlays = [mode for mode in UNDERLAY_TYPES if self.sous_couches[mode].isChecked()]
