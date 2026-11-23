from core.frame_check import fits_in_frame
from core.objects import Contour, CORNER
from exporters.dst_io import export_dst, read_dst


def colonne(x1, x2, largeur=4.0):
    c = Contour(stitch_type="satin", satin_width=largeur, satin_spacing=0.5)
    c.add_point(x1, 0, CORNER)
    c.add_point(x2, 0, CORNER)
    return c


def test_export_dst_du_satin(tmp_path):
    chemin = str(tmp_path / "satin.dst")
    resume = export_dst([colonne(-20, 20)], chemin, frame_size=(130, 180))
    # Un point tous les 0,25 mm sur 40 mm : 160 intervalles, donc 161 points
    assert resume["stitches"] == 161

    relu = read_dst(chemin)
    assert relu["stitches"] == 161
    assert abs(relu["height_mm"] - 4.0) < 0.15   # la largeur de la colonne
    assert abs(relu["width_mm"] - 40.0) < 0.15


def test_le_cadre_tient_compte_de_la_largeur_du_satin():
    ligne = colonne(-20, 20, largeur=7.0)
    assert fits_in_frame([ligne], (100, 5)) is False   # 7 mm de large dans un cadre de 5 mm
    ligne.stitch_type = "running"
    assert fits_in_frame([ligne], (100, 5)) is True    # la simple ligne, elle, tient