import os

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFileDialog, QMessageBox, QInputDialog

from core.project import Project
from core.machine_pattern import read_machine_pattern
from exporters.dst_io import export_dst, read_dst

# Cadres de broderie proposés (nom affiché, largeur mm, hauteur mm)
CADRES = [
    ("100 × 100 mm", 100, 100),
    ("130 × 180 mm", 130, 180),
    ("140 × 200 mm", 140, 200),
]
CADRE_PERSONNALISE = "Personnalisé..."
CADRE_PAR_DEFAUT = (130, 180)

FILTRE_PROJET = "Projet Créabrod (*.crb)"
FILTRE_DST = "Fichier DST (*.dst)"
FILTRE_MACHINE = "Motifs machine (*.dst *.pes *.jef *.vp3 *.exp *.pec *.hus)"
FILTRE_IMAGES = "Images (*.png *.jpg *.jpeg *.webp)"


class FileManager(QObject):
    """Tout ce qui touche aux fichiers : nouveau, ouvrir, enregistrer, importer, exporter."""

    state_changed = Signal()  # le nom du projet ou l'état « modifié » a changé

    def __init__(self, window, canvas):
        super().__init__(window)
        self.window = window
        self.canvas = canvas
        self.project_path = None   # chemin du fichier .crb ouvert (ou None)
        self.modified = False      # modifications non enregistrées ?
        self.canvas.changed.connect(self._on_canvas_changed)

    # ---------- État ----------
    def _on_canvas_changed(self):
        self.modified = True
        self.state_changed.emit()

    def _mark_saved(self, chemin):
        self.project_path = chemin
        self.modified = False
        self.state_changed.emit()

    def _message(self, texte):
        self.window.statusBar().showMessage(texte)

    # ---------- Protection du travail ----------
    def confirm_abandon(self):
        """Retourne True si on peut continuer (rien à perdre, ou l'utilisateur a choisi)."""
        if not (self.modified or self.canvas.current is not None):
            return True

        boite = QMessageBox(self.window)
        boite.setIcon(QMessageBox.Icon.Warning)
        boite.setWindowTitle("CRÉABROD DIGITIZER")
        boite.setText("Voulez-vous enregistrer votre dessin ?")
        boite.setInformativeText("Si vous ne l'enregistrez pas, vos modifications seront perdues.")
        bouton_enregistrer = boite.addButton("Enregistrer", QMessageBox.ButtonRole.AcceptRole)
        bouton_abandonner = boite.addButton(
            "Ne pas enregistrer", QMessageBox.ButtonRole.DestructiveRole
        )
        boite.addButton("Annuler", QMessageBox.ButtonRole.RejectRole)
        boite.setDefaultButton(bouton_enregistrer)
        boite.exec()

        clique = boite.clickedButton()
        if clique == bouton_enregistrer:
            return self.save()
        if clique == bouton_abandonner:
            return True
        return False

    # ---------- Nouveau / Fermer ----------
    def new_project(self):
        noms = [nom for nom, _, _ in CADRES] + [CADRE_PERSONNALISE]
        choix, ok = QInputDialog.getItem(
            self.window, "Nouveau motif", "Cadre de broderie :", noms, 1, False
        )
        if not ok:
            return

        if choix == CADRE_PERSONNALISE:
            largeur, ok = QInputDialog.getDouble(
                self.window, "Cadre personnalisé", "Largeur (mm) :", 100, 20, 1000, 1
            )
            if not ok:
                return
            hauteur, ok = QInputDialog.getDouble(
                self.window, "Cadre personnalisé", "Hauteur (mm) :", 100, 20, 1000, 1
            )
            if not ok:
                return
        else:
            largeur, hauteur = next((l, h) for nom, l, h in CADRES if nom == choix)

        if not self.confirm_abandon():
            return

        self.canvas.new_workspace(largeur, hauteur)
        self._mark_saved(None)

    def close_project(self):
        if not self.confirm_abandon():
            return
        self.canvas.new_workspace(*CADRE_PAR_DEFAUT)
        self._mark_saved(None)

    # ---------- Enregistrer / Ouvrir ----------
    def save(self):
        if self.project_path is None:
            return self.save_as()
        return self._write(self.project_path)

    def save_as(self):
        if self.project_path:
            depart = self.project_path
        else:
            depart = os.path.join(os.path.expanduser("~"), "Documents", "mon_motif.crb")
        chemin, _ = QFileDialog.getSaveFileName(
            self.window, "Enregistrer le projet", depart, FILTRE_PROJET
        )
        if not chemin:
            return False
        if not chemin.lower().endswith(".crb"):
            chemin += ".crb"
        return self._write(chemin)

    def _write(self, chemin):
        self.canvas.finish_contour()  # termine un dessin éventuellement en cours
        try:
            self.canvas.get_project().save(chemin)
        except OSError as erreur:
            QMessageBox.critical(
                self.window, "Erreur", f"Impossible d'enregistrer le projet :\n{erreur}"
            )
            return False
        self._mark_saved(chemin)
        self._message(f"Projet enregistré : {chemin}")
        return True

    def open_project(self):
        if not self.confirm_abandon():
            return
        chemin, _ = QFileDialog.getOpenFileName(
            self.window, "Ouvrir un projet", "", FILTRE_PROJET
        )
        if not chemin:
            return
        try:
            projet = Project.load(chemin)
        except (ValueError, OSError) as erreur:
            QMessageBox.critical(
                self.window, "Erreur", f"Impossible d'ouvrir ce projet :\n{erreur}"
            )
            return

        avertissement = self.canvas.set_project(projet)
        self._mark_saved(chemin)
        if avertissement:
            QMessageBox.warning(self.window, "Image introuvable", avertissement)

    # ---------- Importer une image ----------
    def import_image(self):
        chemin, _ = QFileDialog.getOpenFileName(
            self.window, "Importer une image", "", FILTRE_IMAGES
        )
        if not chemin:
            return
        if self.canvas.show_image(chemin):
            self._message(chemin)
        else:
            QMessageBox.warning(self.window, "Erreur", "Impossible d'ouvrir cette image.")

    # ---------- Importer un motif machine ----------
    def import_machine_pattern(self):
        if not self.confirm_abandon():
            return
        chemin, _ = QFileDialog.getOpenFileName(
            self.window, "Importer un motif machine", "", FILTRE_MACHINE
        )
        if not chemin:
            return
        try:
            motif = read_machine_pattern(chemin)
            self.canvas.set_machine_pattern(motif)
        except (ValueError, OSError, RuntimeError) as erreur:
            QMessageBox.critical(self.window, "Import impossible", str(erreur))
            return
        self.project_path = None
        self.modified = True
        self.state_changed.emit()
        self._message(
            f"Motif {motif.format_name} importé : {motif.stitches} points, "
            f"{motif.color_changes} changement(s) de couleur."
        )

    # ---------- Export DST ----------
    def export_dst_dialog(self):
        self.canvas.finish_contour()  # termine un dessin éventuellement en cours
        if not self.canvas.contours and self.canvas.machine_pattern is None:
            QMessageBox.information(
                self.window, "Export DST",
                "Il n'y a rien à exporter : dessinez d'abord un contour.",
            )
            return

        if self.project_path:
            depart = os.path.splitext(self.project_path)[0] + ".dst"
        else:
            depart = os.path.join(os.path.expanduser("~"), "Documents", "mon_motif.dst")
        chemin, _ = QFileDialog.getSaveFileName(
            self.window, "Exporter en DST", depart, FILTRE_DST
        )
        if not chemin:
            return
        if not chemin.lower().endswith(".dst"):
            chemin += ".dst"

        try:
            if self.canvas.machine_pattern is not None:
                import pyembroidery
                pyembroidery.write(self.canvas.machine_pattern.to_emb_pattern(), chemin)
                relu = read_dst(chemin)
                resume = {
                    "stitches": relu["stitches"],
                    "objects": 1,
                    "width_mm": relu["width_mm"],
                    "height_mm": relu["height_mm"],
                    "color_changes": relu["color_changes"],
                }
                verifie = True
            else:
                resume = export_dst(
                    self.canvas.contours, chemin, frame_size=None
                )
                verifie = True
        except (ValueError, RuntimeError, OSError) as erreur:
            QMessageBox.critical(self.window, "Export DST impossible", str(erreur))
            return

        QMessageBox.information(
            self.window,
            "Export DST terminé",
            f"Fichier créé{' puis relu et vérifié' if verifie else ''} :\n{chemin}\n\n"
            f"{resume['stitches']} points, {resume['objects']} dessin(s)\n"
            f"{resume['width_mm']:.1f} × {resume['height_mm']:.1f} mm\n"
            f"{resume['color_changes']} changement(s) de couleur\n\n"
            "Cette version n'ajoute pas encore de points d'arrêt au début et à la fin.",
        )
