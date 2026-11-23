from PySide6.QtCore import QObject, QEvent, Qt
from PySide6.QtWidgets import QLabel

class FrameWarning(QObject):
    """Ancien bandeau de cadre, conservé sans affichage dans l'espace libre."""

    def __init__(self, canvas):
        super().__init__(canvas)
        self.canvas = canvas
        # Conserver la zone observée : pendant l'arrêt de Qt, le Canvas peut
        # être déjà détruit lorsque l'event filter reçoit encore un événement.
        self._viewport = canvas.viewport()

        self.label = QLabel("⚠ MOTIF TROP GRAND POUR LE CADRE", canvas.viewport())
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet(
            "background-color: #b42318; color: white; font-weight: bold;"
            "font-size: 14px; padding: 6px 14px; border-radius: 4px;"
        )
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents)  # les clics passent au travers
        self.label.hide()

        self._viewport.installEventFilter(self)
        # Ce signal est émis après chaque mise à jour de la zone de travail.
        canvas.stitch_count_changed.connect(lambda nombre: self.update_state())
        self.update_state()

    def update_state(self):
        self.label.hide()

    def _place(self):
        self.label.adjustSize()
        x = (self._viewport.width() - self.label.width()) // 2
        self.label.move(max(x, 0), 10)

    def eventFilter(self, objet, evenement):
        # Quand la zone de travail change de taille, on recentre le bandeau.
        if (
            objet is self._viewport
            and evenement.type() == QEvent.Type.Resize
            and self.label.isVisible()
        ):
            self._place()
        return False
