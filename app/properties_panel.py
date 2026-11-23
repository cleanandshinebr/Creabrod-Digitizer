from PySide6.QtWidgets import (
    QDockWidget,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
    QSlider,
    QListWidget,
    QPushButton,
    QColorDialog,
    QCheckBox,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from core.objects import (
    CONNECTION_MODES,
    FILL_SPACING_MIN,
    FILL_SPACING_MAX,
    SATIN_WIDTH_MIN,
    SATIN_WIDTH_MAX,
    SATIN_SPACING_MIN,
    SATIN_SPACING_MAX,
    SATIN_CORNER_MODES,
    UNDERLAY_TYPES,
)
from core.stats import compute_stats, DEFAULT_SPM
from core.stitches.engine import safe_stitch_points

NOMS_TYPES = {"running": "Running stitch", "satin": "Satin", "fill": "Fill"}
NOMS_CONNEXIONS = {
    "trim_then_jump": "Couper puis sauter",
    "jump": "Sauter sans couper",
    "running": "Coudre jusqu'au suivant",
}
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
STYLE_ALERTE = "color: #b42318; font-weight: bold;"


def format_time(minutes):
    secondes = round(minutes * 60)
    if secondes < 60:
        return f"≈ {secondes} s"
    return f"≈ {secondes // 60} min {secondes % 60:02d} s"


class PropertiesPanel(QDockWidget):
    """Panneau « Propriétés » à onglets : Points, Ordre, Aperçu rapide..."""

    def __init__(self, canvas, editor, parent=None):
        super().__init__("Propriétés", parent)
        self.canvas = canvas
        self.editor = editor
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)

        self.onglets = QTabWidget()
        self.onglets.setMinimumWidth(270)
        # Le panneau doit pouvoir se réduire lorsque le panneau Simulation
        # est affiché en bas, notamment sur les écrans avec barre des tâches.
        self.onglets.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.onglets.addTab(self._creer_onglet_couleur(), "Couleur")
        self.onglets.addTab(self._creer_onglet_points(), "Points")
        self.onglets.addTab(self._creer_onglet_ordre(), "Ordre")
        self.onglets.addTab(QWidget(), "Effets")
        self.onglets.addTab(self._creer_onglet_apercu(), "Aperçu rapide")
        for index in (3,):
            self.onglets.setTabEnabled(index, False)
            self.onglets.setTabToolTip(index, "Pas encore disponible")
        self.onglets.setCurrentIndex(1)
        self.setWidget(self.onglets)

        # Ce signal est émis après chaque mise à jour de la zone de travail.
        canvas.stitch_count_changed.connect(lambda nombre: self.refresh())
        canvas.selection_changed.connect(self.refresh)
        self.refresh()

    # ---------- Création des onglets ----------
    def _creer_onglet_couleur(self):
        page = QWidget()
        disposition = QVBoxLayout(page)
        disposition.addWidget(QLabel("Couleur de l'aiguille / du fil du dessin sélectionné :"))
        self.bouton_couleur = QPushButton("Choisir une couleur")
        self.bouton_couleur.clicked.connect(self._choisir_couleur)
        disposition.addWidget(self.bouton_couleur)
        disposition.addStretch(1)
        return page

    def _creer_reglage(self, slider_min, slider_max, mini, maxi, pas, decimales):
        """Un réglage : un curseur et une case numérique côte à côte."""
        conteneur = QWidget()
        ligne = QHBoxLayout(conteneur)
        ligne.setContentsMargins(0, 0, 0, 0)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(slider_min, slider_max)

        spin = QDoubleSpinBox()
        spin.setRange(mini, maxi)
        spin.setSingleStep(pas)
        spin.setDecimals(decimales)
        spin.setSuffix(" mm")

        ligne.addWidget(slider, 1)
        ligne.addWidget(spin)
        return slider, spin, conteneur

    def _lier(self, slider, spin, echelle, appliquer):
        """Le curseur et la case restent identiques, et appliquent la valeur au dessin."""

        def depuis_curseur(valeur):
            spin.blockSignals(True)
            spin.setValue(valeur / echelle)
            spin.blockSignals(False)
            appliquer(spin.value())

        def depuis_case(valeur):
            slider.blockSignals(True)
            slider.setValue(round(valeur * echelle))
            slider.blockSignals(False)
            appliquer(valeur)

        slider.valueChanged.connect(depuis_curseur)
        spin.valueChanged.connect(depuis_case)

    def _regler(self, slider, spin, echelle, valeur):
        """Affiche une valeur dans le curseur et la case, sans rien appliquer."""
        for widget in (slider, spin):
            widget.blockSignals(True)
        slider.setValue(round(valeur * echelle))
        spin.setValue(valeur)
        for widget in (slider, spin):
            widget.blockSignals(False)

    def _creer_onglet_points(self):
        page = QWidget()
        disposition = QVBoxLayout(page)

        self.titre_points = QLabel("")
        self.titre_points.setWordWrap(True)
        police = self.titre_points.font()
        police.setBold(True)
        self.titre_points.setFont(police)
        disposition.addWidget(self.titre_points)

        self.formulaire_points = QWidget()
        self.formulaire = QFormLayout(self.formulaire_points)
        self._dimensions_en_cours = False

        # ----- Type de point -----
        self.combo_type = QComboBox()
        self.combo_type.addItem("Running stitch", "running")
        self.combo_type.addItem("Satin", "satin")
        self.combo_type.addItem("Fill", "fill")
        self.formulaire.addRow("Type de point :", self.combo_type)

        # ----- Connexion vers le dessin suivant -----
        self.combo_connexion = QComboBox()
        for mode in CONNECTION_MODES:
            self.combo_connexion.addItem(NOMS_CONNEXIONS[mode], mode)
        self.combo_connexion.setToolTip(
            "Connexion entre la fin de ce dessin et le début du dessin suivant."
        )
        self.formulaire.addRow("Connexion suivante :", self.combo_connexion)

        # ----- Running stitch : longueur du point (1,0 à 7,0 mm) -----
        self.slider_longueur, self.spin_longueur, self.ligne_longueur = self._creer_reglage(
            10, 70, 1.0, 7.0, 0.1, 1
        )
        self.formulaire.addRow("Longueur du point :", self.ligne_longueur)

        # ----- Satin : largeur de la colonne -----
        self.slider_largeur, self.spin_largeur, self.ligne_largeur = self._creer_reglage(
            round(SATIN_WIDTH_MIN * 10), round(SATIN_WIDTH_MAX * 10),
            SATIN_WIDTH_MIN, SATIN_WIDTH_MAX, 0.1, 1,
        )
        self.formulaire.addRow("Largeur de la colonne :", self.ligne_largeur)

        # ----- Satin : écart entre les points -----
        self.slider_ecart, self.spin_ecart, self.ligne_ecart = self._creer_reglage(
            round(SATIN_SPACING_MIN * 100), round(SATIN_SPACING_MAX * 100),
            SATIN_SPACING_MIN, SATIN_SPACING_MAX, 0.05, 2,
        )
        self.spin_ecart.setToolTip(
            "Écart entre deux piqûres du même côté de la colonne. "
            "Plus il est petit, plus la colonne est serrée."
        )
        self.formulaire.addRow("Écart entre les points :", self.ligne_ecart)

        self.slider_angle_fill, self.spin_angle_fill, self.ligne_angle_fill = self._creer_reglage(
            0, 1800, 0.0, 180.0, 1.0, 0,
        )
        self.formulaire.addRow("Angle de remplissage :", self.ligne_angle_fill)

        self.slider_ecart_fill, self.spin_ecart_fill, self.ligne_ecart_fill = self._creer_reglage(
            round(FILL_SPACING_MIN * 100), round(FILL_SPACING_MAX * 100),
            FILL_SPACING_MIN, FILL_SPACING_MAX, 0.05, 2,
        )
        self.spin_ecart_fill.setToolTip(
            "Écart entre deux rangées de points du remplissage. "
            "Plus il est petit, plus le remplissage est dense."
        )
        self.formulaire.addRow("Écart de remplissage :", self.ligne_ecart_fill)

        self.combo_coin_satin = QComboBox()
        for mode in SATIN_CORNER_MODES:
            self.combo_coin_satin.addItem(NOMS_COINS_SATIN[mode], mode)
        self.combo_coin_satin.setToolTip(
            "Méthode utilisée par le satin lorsqu'il rencontre un coin."
        )
        self.formulaire.addRow("Coins du satin :", self.combo_coin_satin)
        self.ligne_coin_satin = self.combo_coin_satin

        self.sous_couches = {}
        sous_couches_widget = QWidget()
        sous_couches_layout = QVBoxLayout(sous_couches_widget)
        for mode in UNDERLAY_TYPES:
            case = QCheckBox(NOMS_SOUS_COUCHES[mode])
            case.stateChanged.connect(self._on_underlays_changed)
            self.sous_couches[mode] = case
            sous_couches_layout.addWidget(case)
        self.formulaire.addRow("Sous-couches :", sous_couches_widget)
        self.ligne_sous_couches = sous_couches_widget

        # ----- Redimensionnement numérique -----
        self.spin_dimension_largeur = QDoubleSpinBox()
        self.spin_dimension_largeur.setRange(0.1, 10000.0)
        self.spin_dimension_largeur.setSingleStep(0.5)
        self.spin_dimension_largeur.setDecimals(1)
        self.spin_dimension_largeur.setSuffix(" mm")
        self.spin_dimension_largeur.setToolTip("Largeur exacte du dessin sélectionné.")

        self.spin_dimension_hauteur = QDoubleSpinBox()
        self.spin_dimension_hauteur.setRange(0.1, 10000.0)
        self.spin_dimension_hauteur.setSingleStep(0.5)
        self.spin_dimension_hauteur.setDecimals(1)
        self.spin_dimension_hauteur.setSuffix(" mm")
        self.spin_dimension_hauteur.setToolTip("Hauteur exacte du dessin sélectionné.")

        dimensions = QWidget()
        dimensions_layout = QVBoxLayout(dimensions)
        dimensions_layout.setContentsMargins(0, 0, 0, 0)
        ligne_largeur = QHBoxLayout()
        ligne_largeur.setContentsMargins(0, 0, 0, 0)
        ligne_largeur.addWidget(QLabel("Largeur"))
        ligne_largeur.addWidget(self.spin_dimension_largeur)
        dimensions_layout.addLayout(ligne_largeur)
        ligne_hauteur = QHBoxLayout()
        ligne_hauteur.setContentsMargins(0, 0, 0, 0)
        ligne_hauteur.addWidget(QLabel("Hauteur"))
        ligne_hauteur.addWidget(self.spin_dimension_hauteur)
        dimensions_layout.addLayout(ligne_hauteur)
        self.case_proportions = QCheckBox("Conserver les proportions")
        self.case_proportions.setChecked(True)
        dimensions_layout.addWidget(self.case_proportions)
        self.formulaire.addRow("Redimensionner :", dimensions)
        self.ligne_dimensions = dimensions

        # ----- Informations -----
        self.info_controle = QLabel("—")
        self.info_longueur = QLabel("—")
        self.info_points = QLabel("—")
        self.info_dimensions = QLabel("—")
        self.formulaire.addRow("Points de contrôle :", self.info_controle)
        self.formulaire.addRow("Longueur de la ligne :", self.info_longueur)
        self.formulaire.addRow("Points de broderie :", self.info_points)
        self.formulaire.addRow("Dimensions :", self.info_dimensions)

        disposition.addWidget(self.formulaire_points)
        disposition.addStretch(1)

        # ----- Connexions -----
        self.combo_type.currentIndexChanged.connect(self._on_type_changed)
        self.combo_connexion.currentIndexChanged.connect(self._on_connection_changed)
        self.combo_coin_satin.currentIndexChanged.connect(self._on_satin_corner_changed)
        self._lier(self.slider_longueur, self.spin_longueur, 10, self._appliquer_longueur)
        self._lier(self.slider_largeur, self.spin_largeur, 10, self._appliquer_largeur)
        self._lier(self.slider_ecart, self.spin_ecart, 100, self._appliquer_ecart)
        self._lier(self.slider_angle_fill, self.spin_angle_fill, 10, self._appliquer_angle_fill)
        self._lier(self.slider_ecart_fill, self.spin_ecart_fill, 100, self._appliquer_ecart_fill)
        self.spin_dimension_largeur.valueChanged.connect(
            lambda valeur: self._appliquer_dimension("largeur", valeur)
        )
        self.spin_dimension_hauteur.valueChanged.connect(
            lambda valeur: self._appliquer_dimension("hauteur", valeur)
        )
        return page

    def _creer_onglet_ordre(self):
        page = QWidget()
        disposition = QVBoxLayout(page)
        disposition.addWidget(QLabel("Ordre de broderie (de haut en bas) :"))

        self.liste = QListWidget()
        self.liste.currentRowChanged.connect(self._on_row_changed)
        disposition.addWidget(self.liste, 1)

        boutons = QHBoxLayout()
        self.bouton_monter = QPushButton("▲ Monter")
        self.bouton_descendre = QPushButton("▼ Descendre")
        self.bouton_supprimer = QPushButton("Supprimer")
        self.bouton_monter.clicked.connect(lambda checked=False: self._deplacer(-1))
        self.bouton_descendre.clicked.connect(lambda checked=False: self._deplacer(1))
        self.bouton_supprimer.clicked.connect(lambda checked=False: self._supprimer())
        boutons.addWidget(self.bouton_monter)
        boutons.addWidget(self.bouton_descendre)
        boutons.addWidget(self.bouton_supprimer)
        disposition.addLayout(boutons)
        return page

    def _creer_onglet_apercu(self):
        page = QWidget()
        disposition = QVBoxLayout(page)
        formulaire = QFormLayout()

        self.stat_dessins = QLabel("—")
        self.stat_points = QLabel("—")
        self.stat_couleurs = QLabel("—")
        self.stat_sauts = QLabel("—")
        self.stat_coupes = QLabel("—")
        self.stat_dimensions = QLabel("—")
        self.stat_cadre = QLabel("—")
        self.stat_cadre.setWordWrap(True)
        self.stat_temps = QLabel("—")

        self.spin_vitesse = QSpinBox()
        self.spin_vitesse.setRange(100, 1500)
        self.spin_vitesse.setSingleStep(50)
        self.spin_vitesse.setSuffix(" points/min")
        self.spin_vitesse.setValue(DEFAULT_SPM)
        self.spin_vitesse.valueChanged.connect(lambda valeur: self._rafraichir_apercu())

        formulaire.addRow("Dessins :", self.stat_dessins)
        formulaire.addRow("Points de broderie :", self.stat_points)
        formulaire.addRow("Couleurs :", self.stat_couleurs)
        formulaire.addRow("Sauts (jumps) :", self.stat_sauts)
        formulaire.addRow("Coupes de fil (trims) :", self.stat_coupes)
        formulaire.addRow("Dimensions :", self.stat_dimensions)
        formulaire.addRow("Cadre :", self.stat_cadre)
        formulaire.addRow("Vitesse de la machine :", self.spin_vitesse)
        formulaire.addRow("Temps estimé :", self.stat_temps)
        disposition.addLayout(formulaire)

        note = QLabel(
            "Le temps estimé est approximatif : réglez la vitesse selon votre machine. "
            "Il ne compte pas les changements de fil ni les arrêts."
        )
        note.setWordWrap(True)
        disposition.addWidget(note)
        disposition.addStretch(1)
        return page

    # ---------- Dessin actif ----------
    def _dessin_actif(self):
        """Le dessin en cours de tracé, sinon le dessin sélectionné."""
        if self.canvas.current is not None:
            return self.canvas.current
        return self.canvas.selected

    def _index_selection(self):
        for i, contour in enumerate(self.canvas.contours):
            if contour is self.canvas.selected:
                return i
        return None

    # ---------- Mise à jour ----------
    def refresh(self):
        self._rafraichir_points()
        self._rafraichir_ordre()
        self._rafraichir_apercu()

    def _rafraichir_points(self):
        contour = self._dessin_actif()
        self.formulaire_points.setEnabled(contour is not None)
        self.bouton_couleur.setEnabled(contour is not None)

        if contour is None:
            self.titre_points.setText(
                "Aucun dessin sélectionné.\n"
                "Faites un clic droit sur un dessin, ou choisissez-le dans l'onglet Ordre."
            )
            for etiquette in (
                self.info_controle, self.info_longueur, self.info_points, self.info_dimensions
            ):
                etiquette.setText("—")
            return

        self.bouton_couleur.setText(f"Couleur actuelle : {contour.thread_color}")
        self.bouton_couleur.setStyleSheet(
            f"background-color: {contour.thread_color}; color: white;"
        )

        if contour is self.canvas.current:
            self.titre_points.setText("Dessin en cours")
        else:
            self.titre_points.setText(f"Dessin n° {self._index_selection() + 1:02d}")

        # Le type choisi, et les réglages qui vont avec
        self.combo_type.blockSignals(True)
        self.combo_type.setCurrentIndex(max(0, self.combo_type.findData(contour.stitch_type)))
        self.combo_type.blockSignals(False)

        self.combo_connexion.blockSignals(True)
        self.combo_connexion.setCurrentIndex(
            max(0, self.combo_connexion.findData(contour.connection_mode))
        )
        self.combo_connexion.blockSignals(False)

        satin = contour.stitch_type == "satin"
        fill = contour.stitch_type == "fill"
        self.formulaire.setRowVisible(self.ligne_longueur, not satin and not fill)
        self.formulaire.setRowVisible(self.ligne_largeur, satin)
        self.formulaire.setRowVisible(self.ligne_ecart, satin)
        self.formulaire.setRowVisible(self.ligne_angle_fill, fill)
        self.formulaire.setRowVisible(self.ligne_ecart_fill, fill)
        self.formulaire.setRowVisible(self.ligne_coin_satin, satin)
        self.formulaire.setRowVisible(self.ligne_sous_couches, satin)

        self._regler(self.slider_longueur, self.spin_longueur, 10, contour.stitch_length)
        self._regler(self.slider_largeur, self.spin_largeur, 10, contour.satin_width)
        self._regler(self.slider_ecart, self.spin_ecart, 100, contour.satin_spacing)
        self._regler(self.slider_angle_fill, self.spin_angle_fill, 10, contour.fill_angle)
        self._regler(self.slider_ecart_fill, self.spin_ecart_fill, 100, contour.fill_spacing)
        x0, y0, x1, y1 = contour.bounds()
        largeur, hauteur = x1 - x0, y1 - y0
        a_une_dimension = largeur > 1e-9 or hauteur > 1e-9
        self._dimensions_en_cours = True
        for spin, dimension in (
            (self.spin_dimension_largeur, largeur),
            (self.spin_dimension_hauteur, hauteur),
        ):
            if dimension > 1e-9:
                spin.setRange(0.1, 10000.0)
                spin.setEnabled(True)
                spin.setValue(dimension)
            else:
                spin.setRange(0.0, 10000.0)
                spin.setValue(0.0)
                spin.setEnabled(a_une_dimension)
        self._dimensions_en_cours = False
        self.combo_coin_satin.blockSignals(True)
        self.combo_coin_satin.setCurrentIndex(
            max(0, self.combo_coin_satin.findData(contour.satin_corner_mode))
        )
        self.combo_coin_satin.blockSignals(False)
        for mode, case in self.sous_couches.items():
            case.blockSignals(True)
            case.setChecked(mode in contour.underlays)
            case.blockSignals(False)

        # Informations
        points = safe_stitch_points(contour)
        if points:
            xs = [x for x, _ in points]
            ys = [y for _, y in points]
            largeur = max(xs) - min(xs)
            hauteur = max(ys) - min(ys)
        else:
            x0, y0, x1, y1 = contour.bounds()
            largeur, hauteur = x1 - x0, y1 - y0

        self.info_controle.setText(str(len(contour.points)))
        self.info_longueur.setText(f"{contour.length_mm():.1f} mm")
        self.info_points.setText(f"{len(points):,}".replace(",", " "))
        self.info_dimensions.setText(f"{largeur:.1f} × {hauteur:.1f} mm")

    def _rafraichir_ordre(self):
        contours = self.canvas.contours
        index = self._index_selection()

        self.liste.blockSignals(True)
        self.liste.clear()
        for i, contour in enumerate(contours):
            nom = NOMS_TYPES.get(contour.stitch_type, contour.stitch_type)
            nb = len(safe_stitch_points(contour))
            self.liste.addItem(f"{i + 1:02d}  {nom} · {nb} points · {contour.length_mm():.0f} mm")
        self.liste.setCurrentRow(index if index is not None else -1)
        self.liste.blockSignals(False)

        self.bouton_monter.setEnabled(index is not None and index > 0)
        self.bouton_descendre.setEnabled(index is not None and index < len(contours) - 1)
        self.bouton_supprimer.setEnabled(index is not None)

    def _choisir_couleur(self):
        contour = self._dessin_actif()
        if contour is None:
            return
        couleur = QColorDialog.getColor(
            QColor(contour.thread_color), self, "Couleur du fil"
        )
        if couleur.isValid():
            self.editor.set_thread_color(contour, couleur.name())
            self.refresh()

    def _rafraichir_apercu(self):
        stats = compute_stats(self.canvas.contours)

        self.stat_dessins.setText(str(stats.objects))
        self.stat_points.setText(f"{stats.stitches:,}".replace(",", " "))
        self.stat_couleurs.setText(str(stats.colors))
        self.stat_sauts.setText(str(stats.jumps))
        self.stat_coupes.setText(str(stats.trims))

        if stats.objects == 0:
            self.stat_dimensions.setText("—")
            self.stat_cadre.setText("Espace de travail libre")
            self.stat_cadre.setStyleSheet("")
            self.stat_temps.setText("—")
            return

        self.stat_dimensions.setText(f"{stats.width_mm:.1f} × {stats.height_mm:.1f} mm")
        self.stat_cadre.setText("Espace de travail libre")
        self.stat_cadre.setStyleSheet("")
        self.stat_temps.setText(format_time(stats.stitches / self.spin_vitesse.value()))

    # ---------- Réactions aux changements faits dans le panneau ----------
    def _on_type_changed(self, index):
        contour = self._dessin_actif()
        choisi = self.combo_type.currentData()
        if contour is not None and choisi in NOMS_TYPES:
            self.editor.set_stitch_type(contour, choisi)

    def _on_connection_changed(self, index):
        contour = self._dessin_actif()
        mode = self.combo_connexion.currentData()
        if contour is not None:
            self.editor.set_connection_mode(contour, mode)

    def _on_satin_corner_changed(self, index):
        contour = self._dessin_actif()
        mode = self.combo_coin_satin.currentData()
        if contour is not None:
            self.editor.set_satin_corner_mode(contour, mode)

    def _on_underlays_changed(self, state):
        contour = self._dessin_actif()
        if contour is not None:
            choisis = [mode for mode in UNDERLAY_TYPES if self.sous_couches[mode].isChecked()]
            self.editor.set_underlays(contour, choisis)

    def _appliquer_longueur(self, valeur):
        contour = self._dessin_actif()
        if contour is not None:
            self.editor.set_stitch_length(contour, valeur)

    def _appliquer_largeur(self, valeur):
        contour = self._dessin_actif()
        if contour is not None:
            self.editor.set_satin_width(contour, valeur)

    def _appliquer_ecart(self, valeur):
        contour = self._dessin_actif()
        if contour is not None:
            self.editor.set_satin_spacing(contour, valeur)

    def _appliquer_angle_fill(self, valeur):
        contour = self._dessin_actif()
        if contour is not None:
            self.editor.set_fill_angle(contour, valeur)

    def _appliquer_ecart_fill(self, valeur):
        contour = self._dessin_actif()
        if contour is not None:
            self.editor.set_fill_spacing(contour, valeur)

    def _appliquer_dimension(self, dimension, valeur):
        if self._dimensions_en_cours:
            return
        contour = self._dessin_actif()
        if contour is None:
            return
        x0, y0, x1, y1 = contour.bounds()
        ancienne_largeur = x1 - x0
        ancienne_hauteur = y1 - y0
        if ancienne_largeur <= 1e-9 and ancienne_hauteur <= 1e-9:
            return

        largeur = float(valeur) if dimension == "largeur" else ancienne_largeur
        hauteur = float(valeur) if dimension == "hauteur" else ancienne_hauteur
        if (
            self.case_proportions.isChecked()
            and ancienne_largeur > 1e-9
            and ancienne_hauteur > 1e-9
        ):
            if dimension == "largeur":
                hauteur = largeur * ancienne_hauteur / ancienne_largeur
            else:
                largeur = hauteur * ancienne_largeur / ancienne_hauteur

        self.canvas.resize_selected_dimensions(largeur, hauteur)

    def _on_row_changed(self, ligne):
        if 0 <= ligne < len(self.canvas.contours):
            contour = self.canvas.contours[ligne]
            if contour is not self.canvas.selected:
                self.canvas.select(contour)

    def _deplacer(self, delta):
        if self.canvas.selected is not None:
            self.editor.move(self.canvas.selected, delta)

    def _supprimer(self):
        if self.canvas.selected is not None:
            self.canvas.delete_contour(self.canvas.selected)
