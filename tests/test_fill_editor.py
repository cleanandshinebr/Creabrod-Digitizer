from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF
from PySide6.QtGui import QTransform

from app.canvas import Canvas
from app.editor import Editor
from core.objects import Contour
from core.stitches.engine import safe_stitch_points


class DummyCanvas:
    def __init__(self):
        self.current = None
        self.changed = type("Signal", (), {"emit": lambda self, *args, **kwargs: None})()
        self.status_message = type("StatusSignal", (), {"emit": lambda self, *args, **kwargs: None})()

    def refresh_overlay(self):
        pass


def test_edition_fill_met_a_jour_angle_et_ecart():
    canvas = DummyCanvas()
    editor = Editor(canvas)
    contour = Contour(closed=True, stitch_type="fill")

    editor.set_fill_angle(contour, 45.0)
    editor.set_fill_spacing(contour, 1.25)

    assert contour.fill_angle == 45.0
    assert contour.fill_spacing == 1.25


def test_edition_fill_refuse_les_valeurs_invalides():
    canvas = DummyCanvas()
    editor = Editor(canvas)
    contour = Contour(closed=True, stitch_type="fill", fill_angle=30.0, fill_spacing=2.0)

    editor.set_fill_angle(contour, float("nan"))
    editor.set_fill_spacing(contour, 99.0)

    assert contour.fill_angle == 30.0
    assert contour.fill_spacing == 2.0


def test_set_stitch_type_fill_ferme_le_contour():
    app = QApplication.instance() or QApplication([])
    canvas = Canvas()
    editor = Editor(canvas)
    contour = Contour(closed=False, stitch_type="running")

    editor.set_stitch_type(contour, "fill")

    assert contour.stitch_type == "fill"
    assert contour.closed is True
    app.processEvents()


def test_fill_concave_ne_fait_pas_crasher_linterface():
    contour = Contour(closed=True, stitch_type="fill")
    for point in ((0, 0), (10, 0), (10, 10), (7, 10), (7, 3), (3, 3), (3, 10), (0, 10)):
        contour.add_point(*point, "corner")

    points = safe_stitch_points(contour)
    assert len(points) > 0

    app = QApplication.instance() or QApplication([])
    canvas = Canvas()
    canvas.contours = [contour]
    assert canvas.total_stitches() > 0
    app.processEvents()


def test_finish_contour_fill_concave_accepte_le_contour():
    app = QApplication.instance() or QApplication([])
    canvas = Canvas()
    canvas.current = Contour(closed=True, stitch_type="fill")
    for point in ((0, 0), (10, 0), (10, 10), (7, 10), (7, 3), (3, 3), (3, 10), (0, 10)):
        canvas.current.add_point(*point, "corner")

    canvas.finish_contour()

    assert canvas.current is None
    assert len(canvas.contours) == 1
    app.processEvents()


def test_fill_selectionnable_en_cliquant_dans_la_zone_remplie():
    app = QApplication.instance() or QApplication([])
    canvas = Canvas()
    canvas.setTransform(QTransform.fromScale(100.0, 100.0))
    contour = Contour(closed=True, stitch_type="fill", fill_spacing=1.0)
    for point in ((0, 0), (10, 0), (10, 10), (7, 10), (7, 3), (3, 3), (3, 10), (0, 10)):
        contour.add_point(*point, "corner")
    canvas.contours = [contour]

    assert canvas.contour_at(QPointF(1.0, 8.0)) is contour
    assert canvas.contour_at(QPointF(5.0, 8.0)) is None
    app.processEvents()
