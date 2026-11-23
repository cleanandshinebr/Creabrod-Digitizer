from core.frame_check import fits_in_frame
from core.objects import Contour, CORNER


def ligne(x1, y1, x2, y2):
    c = Contour()
    c.add_point(x1, y1, CORNER)
    c.add_point(x2, y2, CORNER)
    return c


def test_dans_le_cadre():
    assert fits_in_frame([ligne(-30, -10, 30, 10)], (130, 180)) is True


def test_hors_du_cadre():
    assert fits_in_frame([ligne(-30, 0, 70, 0)], (130, 180)) is False   # 70 > 65
    assert fits_in_frame([ligne(0, -95, 0, 10)], (130, 180)) is False   # 95 > 90


def test_un_seul_point_hors_cadre_et_liste_vide():
    c = Contour()
    c.add_point(80, 0, CORNER)
    assert fits_in_frame([c], (130, 180)) is False
    assert fits_in_frame([], (130, 180)) is True