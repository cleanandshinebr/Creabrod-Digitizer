from PySide6.QtWidgets import (
    QDockWidget,
    QWidget,
    QGridLayout,
    QVBoxLayout,
    QPushButton,
    QButtonGroup,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal

# (identifiant, texte, disponible ?, aide)
OUTILS = [
    ("select", "Sélection", True, "Sélectionner un dessin"),
    ("move", "Déplacer la vue", True, "Glisser = déplacer la vue, molette = zoom"),
    ("rotate", "Rotation", True, "Faire tourner un dessin autour de son centre"),
    ("resize", "Redimensionner", True, "Sélectionner un dessin puis glisser une poignée"),
    ("line", "Ligne", False, "Tracer une ligne"),
    ("contour", "Contour", True, "Dessiner un contour : clic simple = courbe, clic long = point droit"),
    ("running", "Running", False, "Running stitch"),
    ("satin", "Satin", False, "Satin stitch"),
    ("fill", "Fill", False, "Fill stitch"),
    ("text", "Texte", False, "Texte et monogrammes"),
    ("eraser", "Gomme", False, "Effacer une partie d'un dessin"),
]


class ToolsPanel(QDockWidget):
    """Panneau d'outils : boutons sur 2 colonnes. Se place à droite ou à gauche."""

    tool_selected = Signal(str)
    clear_requested = Signal()

    def __init__(self, parent=None):
        super().__init__("Outils", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)

        self.boutons = {}  # identifiant -> bouton

        contenu = QWidget()
        disposition = QVBoxLayout(contenu)
        disposition.setContentsMargins(4, 4, 4, 4)

        grille = QGridLayout()
        grille.setSpacing(2)
        self.groupe = QButtonGroup(self)
        self.groupe.setExclusive(True)

        for index, (identifiant, texte, disponible, aide) in enumerate(OUTILS):
            bouton = QPushButton(texte)
            bouton.setCheckable(True)
            bouton.setMinimumHeight(32)
            bouton.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            bouton.setEnabled(disponible)
            if disponible:
                bouton.setToolTip(aide)
            else:
                bouton.setToolTip(aide + " (pas encore disponible)")
            if identifiant == "move":
                bouton.setChecked(True)
            bouton.clicked.connect(
                lambda checked=False, nom=identifiant: self.tool_selected.emit(nom)
            )
            self.groupe.addButton(bouton)
            self.boutons[identifiant] = bouton
            grille.addWidget(bouton, index, 0)

        disposition.addLayout(grille)
        disposition.addSpacing(6)

        bouton_effacer = QPushButton("Effacer les contours")
        bouton_effacer.clicked.connect(lambda checked=False: self.clear_requested.emit())
        disposition.addWidget(bouton_effacer)

        disposition.addStretch(1)
        self.setWidget(contenu)

    def select_tool(self, identifiant):
        """Choisit un outil par programme (par exemple depuis le menu Création)."""
        bouton = self.boutons.get(identifiant)
        if bouton is None or not bouton.isEnabled():
            return
        bouton.setChecked(True)
        self.tool_selected.emit(identifiant)
