from PySide6.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSlider,
    QLabel,
    QComboBox,
    QCheckBox,
)
from PySide6.QtCore import Qt

# (texte affiché, étapes par seconde)
VITESSES = [
    ("10 points/s", 10),
    ("25 points/s", 25),
    ("50 points/s", 50),
    ("100 points/s", 100),
    ("250 points/s", 250),
    ("500 points/s", 500),
    ("1 000 points/s", 1000),
    ("2 500 points/s", 2500),
]
VITESSE_PAR_DEFAUT = 3  # 100 points/s


def espaces(nombre):
    """12500 -> '12 500'"""
    return f"{nombre:,}".replace(",", " ")


class SimulationPanel(QDockWidget):
    """Commandes de la simulation : lecture, pause, stop, retour, avance, vitesse."""

    def __init__(self, simulator, parent=None):
        super().__init__("Simulation", parent)
        self.simulator = simulator
        self.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
        self.setFeatures(
            QDockWidget.DockWidgetClosable
            | QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
        )

        self.has_steps = False
        self.position = 0
        self.steps_total = 0
        self.playing = False

        contenu = QWidget()
        disposition = QVBoxLayout(contenu)
        disposition.setContentsMargins(6, 4, 6, 4)
        disposition.setSpacing(3)
        contenu.setMinimumHeight(0)

        # ----- Ligne 1 : boutons, vitesse, numéros -----
        ligne = QHBoxLayout()

        self.bouton_retour = QPushButton("◀ Retour")
        self.bouton_retour.setAutoRepeat(True)
        self.bouton_retour.setAutoRepeatInterval(40)
        self.bouton_retour.setToolTip("Reculer d'un point (maintenir pour reculer vite)")

        self.bouton_play = QPushButton("▶ Lecture")
        self.bouton_pause = QPushButton("|| Pause")
        self.bouton_stop = QPushButton("■ Stop")

        self.bouton_avance = QPushButton("Avance ▶")
        self.bouton_avance.setAutoRepeat(True)
        self.bouton_avance.setAutoRepeatInterval(40)
        self.bouton_avance.setToolTip("Avancer d'un point (maintenir pour avancer vite)")

        for bouton in (
            self.bouton_retour,
            self.bouton_play,
            self.bouton_pause,
            self.bouton_stop,
            self.bouton_avance,
        ):
            ligne.addWidget(bouton)

        ligne.addSpacing(16)
        ligne.addWidget(QLabel("Vitesse :"))
        self.combo_vitesse = QComboBox()
        for texte, _ in VITESSES:
            self.combo_vitesse.addItem(texte)
        self.combo_vitesse.setToolTip(
            "Vitesse de l'animation. Une machine à 600 points/min brode environ 10 points/s."
        )
        self.combo_vitesse.setCurrentIndex(VITESSE_PAR_DEFAUT)
        ligne.addWidget(self.combo_vitesse)

        ligne.addSpacing(16)
        self.case_numeros = QCheckBox("Numéroter les points")
        self.case_numeros.setToolTip("Affiche l'ordre des points sur le dessin")
        ligne.addWidget(self.case_numeros)
        ligne.addStretch(1)
        disposition.addLayout(ligne)

        # ----- Ligne 2 : curseur et compteur -----
        ligne2 = QHBoxLayout()
        self.curseur = QSlider(Qt.Horizontal)
        self.curseur.setRange(0, 0)
        self.label_progression = QLabel("0 / 0 points")
        self.label_progression.setMinimumWidth(170)
        self.label_progression.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        police = self.label_progression.font()
        police.setBold(True)
        self.label_progression.setFont(police)
        ligne2.addWidget(self.curseur, 1)
        ligne2.addWidget(self.label_progression)
        disposition.addLayout(ligne2)

        # ----- Ligne 3 : détail -----
        self.label_detail = QLabel("")
        disposition.addWidget(self.label_detail)

        self.setWidget(contenu)

        # ----- Connexions -----
        self.bouton_play.clicked.connect(lambda checked=False: simulator.play())
        self.bouton_pause.clicked.connect(lambda checked=False: simulator.pause())
        self.bouton_stop.clicked.connect(lambda checked=False: simulator.stop())
        self.bouton_retour.clicked.connect(lambda checked=False: simulator.step(-1))
        self.bouton_avance.clicked.connect(lambda checked=False: simulator.step(1))
        self.curseur.valueChanged.connect(simulator.seek)
        self.combo_vitesse.currentIndexChanged.connect(self._on_vitesse)
        self.case_numeros.toggled.connect(simulator.set_numbers)

        simulator.progress.connect(self.on_progress)
        simulator.playing_changed.connect(self.on_playing)

        simulator.set_speed(VITESSES[VITESSE_PAR_DEFAUT][1])
        self._update_buttons()

    def _on_vitesse(self, index):
        self.simulator.set_speed(VITESSES[index][1])

    def on_playing(self, playing):
        self.playing = playing
        self._update_buttons()

    def on_progress(self, p):
        self.has_steps = p.steps_total > 0
        self.position = p.position
        self.steps_total = p.steps_total

        self.curseur.blockSignals(True)
        self.curseur.setRange(0, p.steps_total)
        self.curseur.setValue(p.position)
        self.curseur.blockSignals(False)

        self.label_progression.setText(
            f"{espaces(p.stitches)} / {espaces(p.stitches_total)} points"
        )
        self.label_detail.setText(
            f"{p.description}    |    Sauts : {p.jumps}/{p.jumps_total}"
            f"  ·  Coupes de fil : {p.trims}/{p.trims_total}"
            f"  ·  Changements de couleur : {p.colors}/{p.colors_total}"
        )
        self._update_buttons()

    def _update_buttons(self):
        self.bouton_play.setEnabled(self.has_steps and not self.playing)
        self.bouton_pause.setEnabled(self.playing)
        self.bouton_stop.setEnabled(self.has_steps and self.position > 0)
        self.bouton_retour.setEnabled(self.has_steps and self.position > 0)
        self.bouton_avance.setEnabled(self.has_steps and self.position < self.steps_total)
        self.curseur.setEnabled(self.has_steps)
