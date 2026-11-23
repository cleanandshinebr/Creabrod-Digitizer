import math
import os

import pytest

from core.objects import Contour, CORNER, CURVE
from exporters.dst_io import export_dst, read_dst


def deux_dessins():
    a = Contour(stitch_length=2.5)
    a.add_point(-30, -10, CORNER)
    a.add_point(30, -10, CORNER)

    b = Contour(stitch_length=3.0)
    b.add_point(-20, 10, CURVE)
    b.add_point(0, 30, CURVE)
    b.add_point(20, 10, CURVE)
    return [a, b]


def test_export_puis_relecture(tmp_path):
    chemin = str(tmp_path / "test.dst")
    resume = export_dst(deux_dessins(), chemin, frame_size=(130, 180))

    assert os.path.getsize(chemin) > 0
    assert resume["objects"] == 2
    assert resume["stitches"] > 25  # la ligne de 60 mm seule fait 25 points

    relu = read_dst(chemin)
    assert relu["stitches"] == resume["stitches"]
    assert relu["color_changes"] == 0
    assert math.isclose(relu["width_mm"], resume["width_mm"], abs_tol=0.15)
    assert math.isclose(relu["height_mm"], resume["height_mm"], abs_tol=0.15)


def test_motif_trop_grand_pour_le_cadre(tmp_path):
    trop_grand = Contour()
    trop_grand.add_point(-100, 0, CORNER)
    trop_grand.add_point(100, 0, CORNER)
    with pytest.raises(ValueError):
        export_dst([trop_grand], str(tmp_path / "x.dst"), frame_size=(130, 180))


def test_rien_a_exporter(tmp_path):
    with pytest.raises(ValueError):
        export_dst([], str(tmp_path / "x.dst"), frame_size=(130, 180))


def test_export_connexion_running_sans_saut_intermediaire(tmp_path):
    contours = deux_dessins()
    contours[0].connection_mode = "running"

    resume = export_dst(contours, str(tmp_path / "running.dst"), frame_size=(130, 180))
    depart = export_dst([contours[0]], str(tmp_path / "depart.dst"), frame_size=(130, 180))

    assert resume["jumps"] == depart["jumps"]


def test_export_dst_contient_un_changement_de_couleur(tmp_path):
    contours = deux_dessins()
    contours[1].thread_color = "#ff0000"

    resume = export_dst(contours, str(tmp_path / "couleurs.dst"), frame_size=(130, 180))

    assert resume["color_changes"] == 1
    assert read_dst(str(tmp_path / "couleurs.dst"))["color_changes"] == 1


def test_export_fill_concave_ne_saute_plus_a_l_interieur_du_bloc(tmp_path):
    """Règle tatami EOS : à l'intérieur d'un bloc de remplissage, la machine
    coud des sous-points, y compris entre les zones concaves. Le seul saut
    restant est l'entrée dans le bloc."""
    contour = Contour(closed=True, stitch_type="fill", fill_spacing=1.0)
    for point in ((0, 0), (10, 0), (10, 10), (7, 10), (7, 3), (3, 3), (3, 10), (0, 10)):
        contour.add_point(*point, CORNER)

    resume = export_dst([contour], str(tmp_path / "concave.dst"))
    relu = read_dst(str(tmp_path / "concave.dst"))

    assert resume["stitches"] > 1
    assert resume["jumps"] <= 1
    assert relu["jumps"] == resume["jumps"]
    assert relu["stitches"] == resume["stitches"]
