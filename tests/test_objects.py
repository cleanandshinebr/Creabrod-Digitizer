import math

from core.objects import Contour, CORNER, CURVE


def ligne():
    c = Contour()
    c.add_point(0, 0, CORNER)
    c.add_point(10, 0, CORNER)
    return c


def test_inverser_le_sens():
    c = Contour()
    c.add_point(0, 0, CORNER)
    c.add_point(5, 5, CURVE)
    c.add_point(10, 0, CORNER)
    longueur = c.length_mm()

    c.reverse()
    assert c.points[0] == (10, 0, CORNER)
    assert c.points[-1] == (0, 0, CORNER)
    assert math.isclose(c.length_mm(), longueur, abs_tol=1e-6)

    c.reverse()
    assert c.points[0] == (0, 0, CORNER)


def test_distance_au_dessin():
    c = ligne()
    assert math.isclose(c.distance_to(5, 3), 3.0)
    assert math.isclose(c.distance_to(-4, 0), 4.0)


def test_dimensions():
    assert ligne().bounds() == (0, 0, 10, 0)