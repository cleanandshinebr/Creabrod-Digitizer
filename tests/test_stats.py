import math

from core.objects import Contour, CORNER
from core.stats import compute_stats


def deux_lignes():
    a = Contour(stitch_length=2.5)
    a.add_point(-30, -10, CORNER)
    a.add_point(30, -10, CORNER)
    b = Contour(stitch_length=2.5)
    b.add_point(-30, 10, CORNER)
    b.add_point(30, 10, CORNER)
    return [a, b]


def test_statistiques():
    s = compute_stats(deux_lignes(), frame_size=(130, 180))
    assert s.objects == 2
    assert s.stitches == 50  # 25 points par ligne de 60 mm
    assert s.colors == 1
    assert s.trims == 1
    assert s.jumps == 2
    assert math.isclose(s.width_mm, 60)
    assert math.isclose(s.height_mm, 20)
    assert s.fits_frame is True


def test_motif_trop_grand_pour_le_cadre():
    s = compute_stats(deux_lignes(), frame_size=(50, 50))
    assert s.fits_frame is False


def test_motif_vide():
    s = compute_stats([], frame_size=(130, 180))
    assert s.objects == 0
    assert s.stitches == 0