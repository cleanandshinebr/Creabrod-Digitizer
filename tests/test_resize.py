import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.canvas import Canvas
from app.editor import Editor
from app.properties_panel import PropertiesPanel
from core.objects import CORNER, Contour


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _canvas_with(contour):
    canvas = Canvas()
    canvas.contours.append(contour)
    canvas.selected = contour
    return canvas


def test_redimensionnement_du_panneau_conserve_les_proportions(qapp):
    contour = Contour()
    for point in ((0, 0), (10, 0), (10, 5), (0, 5)):
        contour.add_point(*point, CORNER)
    canvas = _canvas_with(contour)
    panel = PropertiesPanel(canvas, Editor(canvas))
    panel.refresh()

    panel.spin_dimension_largeur.setValue(20)

    assert contour.bounds() == pytest.approx((-5, -2.5, 15, 7.5))
    assert panel.spin_dimension_hauteur.value() == pytest.approx(10)


def test_ligne_horizontale_peut_recevoir_une_hauteur(qapp):
    contour = Contour()
    contour.add_point(0, 0, CORNER)
    contour.add_point(10, 0, CORNER)
    canvas = _canvas_with(contour)
    panel = PropertiesPanel(canvas, Editor(canvas))
    panel.refresh()

    assert panel.spin_dimension_hauteur.value() == 0
    assert panel.spin_dimension_hauteur.isEnabled()

    panel.spin_dimension_hauteur.setValue(4)

    assert contour.bounds() == pytest.approx((0, -2, 10, 2))


def test_ligne_verticale_peut_recevoir_une_largeur(qapp):
    contour = Contour()
    contour.add_point(0, 0, CORNER)
    contour.add_point(0, 10, CORNER)
    canvas = _canvas_with(contour)
    panel = PropertiesPanel(canvas, Editor(canvas))
    panel.refresh()

    assert panel.spin_dimension_largeur.value() == 0
    assert panel.spin_dimension_largeur.isEnabled()

    panel.spin_dimension_largeur.setValue(4)

    assert contour.bounds() == pytest.approx((-2, 0, 2, 10))


def test_glisser_une_poignee_choisit_le_coin_le_plus_proche(qapp):
    contour = Contour()
    for point in ((0, 0), (10, 0), (10, 5), (0, 5)):
        contour.add_point(*point, CORNER)
    canvas = _canvas_with(contour)
    canvas.set_tool("resize")
    canvas.resize(800, 600)
    canvas.show()
    qapp.processEvents()

    centre = canvas.mapFromScene(QPointF(5, 2.5))
    QTest.mouseClick(canvas.viewport(), Qt.LeftButton, pos=centre)
    qapp.processEvents()

    poignee = canvas.mapFromScene(QPointF(10, 5))
    arrivee = canvas.mapFromScene(QPointF(15, 10))
    QTest.mousePress(canvas.viewport(), Qt.LeftButton, pos=poignee)
    QTest.mouseMove(canvas.viewport(), arrivee, 20)
    QTest.mouseRelease(canvas.viewport(), Qt.LeftButton, pos=arrivee)

    assert contour.bounds() == pytest.approx((0, 0, 15, 10))
