import math

import pytest

from core.objects import Contour, CORNER, CURVE
from core.stitches.running import running_stitch


def droite(longueur):
    c = Contour()
    c.add_point(0, 0, CORNER)
    c.add_point(longueur, 0, CORNER)
    return c


def test_ligne_droite_10mm():
    pts = running_stitch(droite(10), 2.5)
    assert len(pts) == 5
    assert pts[0] == (0, 0)
    assert pts[-1] == (10, 0)
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        assert math.isclose(math.hypot(x2 - x1, y2 - y1), 2.5, abs_tol=1e-6)


def test_dernier_point_jamais_trop_court():
    pts = running_stitch(droite(10.2), 2.5)
    assert pts[-1] == (10.2, 0)
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        d = math.hypot(x2 - x1, y2 - y1)
        assert 1.25 <= d <= 3.75


def test_les_angles_sont_conserves():
    c = Contour()
    c.add_point(0, 0, CORNER)
    c.add_point(10, 0, CORNER)
    c.add_point(10, 10, CORNER)
    pts = running_stitch(c, 3)
    assert (10, 0) in pts
    assert pts[-1] == (10, 10)
    assert len(pts) == len(set(pts))  # aucun point en double


def test_courbe():
    c = Contour()
    c.add_point(0, 0, CURVE)
    c.add_point(5, 5, CURVE)
    c.add_point(10, 0, CURVE)
    pts = running_stitch(c, 2.5)
    assert len(pts) >= 5
    assert pts[0] == (0, 0)
    assert pts[-1] == (10, 0)


def test_longueur_invalide():
    with pytest.raises(ValueError):
        running_stitch(droite(10), 0)