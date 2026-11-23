import json

import pytest

from core.objects import Contour, CORNER, CURVE
from core.project import Project
from core.machine_pattern import MachineCommand, MachinePattern


def exemple():
    c1 = Contour(stitch_length=3.0)
    c1.add_point(0.0, 0.0, CORNER)
    c1.add_point(10.5, 4.25, CURVE)
    c1.add_point(20.0, 0.0, CORNER)
    c2 = Contour()
    c2.add_point(-5.0, -5.0, CURVE)
    c2.add_point(5.0, 5.0, CURVE)
    return Project(
        frame_width=140.0,
        frame_height=200.0,
        image_path="C:/images/fleur.png",
        contours=[c1, c2],
    )


def test_enregistrer_puis_relire(tmp_path):
    chemin = str(tmp_path / "motif.crb")
    original = exemple()
    original.save(chemin)

    relu = Project.load(chemin)
    assert relu.to_dict() == original.to_dict()
    assert relu.contours[0].points[0] == (0.0, 0.0, CORNER)
    assert relu.contours[0].stitch_length == 3.0


def test_fichier_illisible(tmp_path):
    chemin = tmp_path / "casse.crb"
    chemin.write_text("ceci n'est pas du json", encoding="utf-8")
    with pytest.raises(ValueError):
        Project.load(str(chemin))


def test_mauvais_format(tmp_path):
    chemin = tmp_path / "autre.crb"
    chemin.write_text(json.dumps({"format": "autre-chose"}), encoding="utf-8")
    with pytest.raises(ValueError):
        Project.load(str(chemin))


def test_coordonnee_invalide(tmp_path):
    data = exemple().to_dict()
    data["contours"][0]["points"][0]["x"] = float("nan")
    chemin = tmp_path / "nan.crb"
    chemin.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        Project.load(str(chemin))


def test_persistance_du_mode_de_connexion(tmp_path):
    chemin = str(tmp_path / "connexion.crb")
    original = exemple()
    original.contours[0].connection_mode = "running"
    original.save(chemin)

    relu = Project.load(chemin)

    assert relu.contours[0].connection_mode == "running"


def test_persistance_de_la_couleur_de_fil(tmp_path):
    chemin = str(tmp_path / "couleur.crb")
    original = exemple()
    original.contours[0].thread_color = "#ff6600"
    original.save(chemin)

    relu = Project.load(chemin)

    assert relu.contours[0].thread_color == "#ff6600"


def test_persistance_du_motif_machine(tmp_path):
    chemin = str(tmp_path / "machine.crb")
    motif = MachinePattern(
        "motif.dst",
        "DST",
        [
            MachineCommand("stitch", -5.0, 0.0, 0),
            MachineCommand("jump", 0.0, 0.0, 0),
            MachineCommand("color_change", 0.0, 0.0, 0),
            MachineCommand("stitch", 5.0, 0.0, 1),
        ],
    )
    original = Project(machine_pattern=motif)
    original.save(chemin)

    relu = Project.load(chemin)

    assert relu.machine_pattern.to_dict() == motif.to_dict()
