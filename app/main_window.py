import os

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QLabel, QStyle
from PySide6.QtGui import QAction
from PySide6.QtCore import QTimer, Qt, QSize
from app.canvas import Canvas
from app.context_toolbar import ContextToolbar
from app.editor import Editor
from app.file_manager import FileManager, CADRE_PAR_DEFAUT
from app.frame_warning import FrameWarning
from app.properties_panel import PropertiesPanel
from app.simulation_panel import SimulationPanel
from app.simulator import Simulator
from app.tools_panel import ToolsPanel


class MainWindow(QMainWindow):
    """Fenêtre principale : assemble les morceaux (menus, outils, zone de travail)."""

    def __init__(self):
        super().__init__()
        self._appliquer_style_interface()
        # Ne pas placer le panneau inférieur sous la barre des tâches sur les
        # écrans dont la zone disponible est plus petite que 1300 x 800.
        ecran = self.screen() or QApplication.primaryScreen()
        zone_disponible = ecran.availableGeometry()
        largeur = min(1300, max(800, zone_disponible.width() - 20))
        hauteur = min(800, max(600, zone_disponible.height() - 20))
        self.resize(largeur, hauteur)

        self.canvas = Canvas()
        self.setCentralWidget(self.canvas)

        self.files = FileManager(self, self.canvas)
        self.editor = Editor(self.canvas)
        self.alerte_cadre = FrameWarning(self.canvas)
        self.simulator = Simulator(self.canvas)

        # Panneaux latéraux : outils à gauche, propriétés à droite.
        # Cette disposition évite que les propriétés soient repoussées sous
        # le panneau d'outils ou hors de la zone visible.
        self.panneau_outils = ToolsPanel(self)
        self.panneau_proprietes = PropertiesPanel(self.canvas, self.editor, self)
        self.panneau_outils.setMinimumWidth(150)
        self.panneau_outils.setMaximumWidth(190)
        self.panneau_proprietes.setMinimumWidth(270)
        self.panneau_proprietes.setMaximumWidth(360)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.panneau_outils)
        self.addDockWidget(Qt.RightDockWidgetArea, self.panneau_proprietes)

        # Panneau du bas : simulation (caché au départ)
        self.panneau_simulation = SimulationPanel(self.simulator, self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.panneau_simulation)
        self.panneau_simulation.hide()
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)

        self.barre = ContextToolbar(self.canvas, self)
        self.addToolBar(self.barre)

        self.label_zoom = QLabel("Zoom : 100 %")
        self.statusBar().addPermanentWidget(self.label_zoom)

        self.creer_menus()

        # ----- Connexions -----
        self.canvas.status_message.connect(self.statusBar().showMessage)
        self.canvas.mouse_moved.connect(self.barre.set_position)
        self.canvas.stitch_count_changed.connect(self.barre.set_stitch_count)
        self.canvas.zoom_changed.connect(self.on_zoom_changed)
        self.panneau_outils.tool_selected.connect(self.on_tool_selected)
        self.panneau_outils.clear_requested.connect(self.canvas.clear_contours)
        self.files.state_changed.connect(self.update_title)

        self.update_title()

        # Au démarrage : une page vide
        QTimer.singleShot(0, lambda: self.canvas.new_workspace(*CADRE_PAR_DEFAUT))

    # ---------- Menus ----------
    def _action(self, menu, texte, fonction=None, raccourci=None):
        """Ajoute une action au menu. Sans fonction : grisée avec « (bientôt) »."""
        if fonction is None:
            action = QAction(f"{texte} (bientôt)", self)
            action.setEnabled(False)
        else:
            action = QAction(texte, self)
            action.triggered.connect(lambda checked=False: fonction())
        if raccourci:
            action.setShortcut(raccourci)
        menu.addAction(action)
        return action

    def creer_menus(self):
        barre_menus = self.menuBar()

        # Projet
        menu = barre_menus.addMenu("Projet")
        self._action(menu, "Nouveau...", self.files.new_project, "Ctrl+N")
        self._action(menu, "Ouvrir un projet...", self.files.open_project, "Ctrl+O")
        self._action(menu, "Importer une image...", self.files.import_image, "Ctrl+I")
        self._action(menu, "Importer un motif machine...", self.files.import_machine_pattern, "Ctrl+M")
        menu.addSeparator()
        self._action(menu, "Enregistrer", self.files.save, "Ctrl+S")
        self._action(menu, "Enregistrer sous...", self.files.save_as, "Ctrl+Shift+S")
        self._action(menu, "Exporter en DST...", self.files.export_dst_dialog, "Ctrl+E")
        menu.addSeparator()
        self._action(menu, "Fermer le projet", self.files.close_project, "Ctrl+W")
        self._action(menu, "Quitter", self.close, "Ctrl+Q")

        # Édition
        menu = barre_menus.addMenu("Édition")
        self._action(menu, "Annuler", None, "Ctrl+Z")
        self._action(menu, "Rétablir", None, "Ctrl+Y")
        menu.addSeparator()
        self._action(menu, "Copier", None)
        self._action(menu, "Coller", None)
        menu.addSeparator()
        self._action(menu, "Supprimer le dessin sélectionné", self.supprimer_selection)
        self._action(menu, "Effacer tous les contours", self.canvas.clear_contours)

        # Affichage
        menu = barre_menus.addMenu("Affichage")
        menu.addAction(self.barre.act_fit)
        self._action(menu, "Zoom avant", lambda: self.zoom(1.25), "Ctrl++")
        self._action(menu, "Zoom arrière", lambda: self.zoom(1 / 1.25), "Ctrl+-")
        menu.addSeparator()
        menu.addAction(self.barre.act_points)
        menu.addAction(self.barre.act_axes)
        self._action(menu, "Grille", None)
        menu.addSeparator()

        action_simulation = self.panneau_simulation.toggleViewAction()
        action_simulation.setText("Simulation")
        action_simulation.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        action_simulation.setShortcut("F5")
        action_simulation.toggled.connect(self.on_simulation_toggled)
        menu.addAction(action_simulation)
        self.barre.insertAction(self.barre.act_points, action_simulation)

        # Création
        menu = barre_menus.addMenu("Création")
        self._action(
            menu, "Contour (running stitch)",
            lambda: self.panneau_outils.select_tool("contour"),
        )
        self._action(menu, "Remplissages", None)
        self._action(menu, "Colonnes Satin", None)
        self._action(menu, "Texte", None)
        self._action(menu, "Effets", None)

        # Fenêtres
        menu = barre_menus.addMenu("Fenêtres")
        action_outils = self.panneau_outils.toggleViewAction()
        action_outils.setText("Panneau d'outils")
        menu.addAction(action_outils)
        action_proprietes = self.panneau_proprietes.toggleViewAction()
        action_proprietes.setText("Panneau de propriétés")
        menu.addAction(action_proprietes)
        self._action(menu, "Réinitialiser l'interface", self.reinitialiser_interface)

        # Aide
        menu = barre_menus.addMenu("Aide")
        self._action(menu, "Guide", None)
        self._action(menu, "Tutoriels", None)
        menu.addSeparator()
        self._action(menu, "À propos", self.a_propos)

    # ---------- Actions de la fenêtre ----------
    def _appliquer_style_interface(self):
        """Conserver le rendu natif Windows et seulement compacter la barre."""
        self.setStyleSheet("")
        self.setIconSize(QSize(16, 16))

    def on_tool_selected(self, outil):
        self.canvas.set_tool(outil)
        self.barre.show_tool(outil)

    def on_simulation_toggled(self, visible):
        if visible:
            self.panneau_outils.select_tool("move")  # pas de dessin pendant la simulation
            self.simulator.enter()
        else:
            self.simulator.leave()

    def on_zoom_changed(self, pourcentage):
        self.label_zoom.setText(f"Zoom : {pourcentage:.0f} %")

    def zoom(self, facteur):
        self.canvas.scale(facteur, facteur)
        self.canvas._emit_zoom()

    def supprimer_selection(self):
        if self.canvas.selected is None:
            self.statusBar().showMessage(
                "Aucun dessin sélectionné : faites un clic droit sur un dessin pour le sélectionner."
            )
            return
        self.canvas.delete_contour(self.canvas.selected)

    def reinitialiser_interface(self):
        self.panneau_outils.setFloating(False)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.panneau_outils)
        self.panneau_outils.show()

        self.panneau_proprietes.setFloating(False)
        self.addDockWidget(Qt.RightDockWidgetArea, self.panneau_proprietes)
        self.panneau_proprietes.show()

        self.panneau_simulation.setFloating(False)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.panneau_simulation)

    def a_propos(self):
        QMessageBox.about(
            self,
            "À propos",
            "CRÉABROD DIGITIZER V0.1\n\n"
            "Logiciel de numérisation de broderie en cours de développement.\n"
            "Gratuit, fonctionne en local.",
        )

    # ---------- Titre et fermeture ----------
    def update_title(self):
        chemin = self.files.project_path
        nom = os.path.basename(chemin) if chemin else "Sans titre"
        etoile = "*" if self.files.modified else ""
        self.setWindowTitle(f"{etoile}{nom} - CRÉABROD DIGITIZER V0.1")

    def closeEvent(self, event):
        if self.files.confirm_abandon():
            event.accept()
        else:
            event.ignore()
