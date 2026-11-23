import os

import pyembroidery

from core.machine_pattern import read_machine_pattern
from core.objects import Contour, CORNER
from exporters.dst_io import export_dst


def motif_machine():
    pattern = pyembroidery.EmbPattern()
    pattern.add_stitch_absolute(pyembroidery.STITCH, 0, 0)
    pattern.add_stitch_absolute(pyembroidery.STITCH, 100, 0)
    pattern.add_stitch_absolute(pyembroidery.JUMP, 150, 50)
    pattern.add_stitch_absolute(pyembroidery.COLOR_CHANGE, 150, 50)
    pattern.add_stitch_absolute(pyembroidery.STITCH, 200, 50)
    pattern.add_stitch_absolute(pyembroidery.END, 200, 50)
    return pattern


def test_import_pes_conserve_points_sauts_et_couleur(tmp_path):
    chemin = str(tmp_path / "motif.pes")
    pyembroidery.write(motif_machine(), chemin)

    motif = read_machine_pattern(chemin)

    assert os.path.getsize(chemin) > 0
    assert motif.format_name == "PES"
    # Le lecteur PES explicite le point de positionnement avant le changement de bloc.
    assert motif.stitches == 4
    assert motif.jumps >= 1
    assert motif.color_changes == 1
    assert len(motif.thread_colors) >= 2
    assert motif.thread_colors[0].startswith("#")
    assert motif.bounds() == (-10.0, -2.5, 10.0, 2.5)


def test_import_refuse_extension_non_supportee(tmp_path):
    chemin = str(tmp_path / "motif.xyz")
    with open(chemin, "wb") as fichier:
        fichier.write(b"test")

    try:
        read_machine_pattern(chemin)
    except ValueError as erreur:
        assert "non pris en charge" in str(erreur)
    else:
        raise AssertionError("Le format xyz aurait dû être refusé")


def test_import_dst_exporte_par_le_logiciel(tmp_path):
    contour = Contour()
    contour.add_point(-10, 0, CORNER)
    contour.add_point(10, 0, CORNER)
    chemin = str(tmp_path / "motif.dst")
    export_dst([contour], chemin, frame_size=(130, 180))

    motif = read_machine_pattern(chemin)

    assert motif.format_name == "DST"
    assert motif.stitches > 1


def test_import_accepte_un_objet_path(tmp_path):
    chemin = tmp_path / "motif.dst"
    contour = Contour()
    contour.add_point(-10, 0, CORNER)
    contour.add_point(10, 0, CORNER)
    export_dst([contour], chemin, frame_size=(130, 180))

    motif = read_machine_pattern(chemin)

    assert motif.format_name == "DST"
    assert motif.stitches > 1
