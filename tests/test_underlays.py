import math

import pytest

from core.objects import CORNER, Contour, UNDERLAY_TYPES
from core.stitches.engine import stitch_points
from core.stitches.satin import satin_stitch
from core.stitches.underlays import underlay_points


def contour_satin():
    contour = Contour(stitch_type="satin", satin_width=3.0, satin_spacing=0.4)
    contour.add_point(0, 0, CORNER)
    contour.add_point(20, 0, CORNER)
    return contour


def test_les_trois_types_de_sous_couche_produisent_des_points():
    contour = contour_satin()
    for underlay_type in UNDERLAY_TYPES:
        points = underlay_points(contour, underlay_type)
        assert len(points) > 1
        assert all(math.isfinite(x) and math.isfinite(y) for x, y in points)


def test_les_sous_couches_sont_avant_la_couche_principale():
    contour = contour_satin()
    sans_sous_couche = len(stitch_points(contour))

    contour.underlays = ["centerline", "walking", "zigzag"]
    avec_sous_couches = stitch_points(contour)

    assert len(avec_sous_couches) > sans_sous_couche
    assert avec_sous_couches[-1] == pytest.approx(stitch_points(contour)[-1])


def test_la_liaison_entre_couches_revient_par_le_centre_du_satin():
    contour = contour_satin()
    contour.underlays = ["centerline", "walking"]
    centre = underlay_points(contour, "centerline")

    points = stitch_points(contour)

    # La deuxième couche commence en B et revient vers A sur le centre.
    assert points[len(centre)] == pytest.approx((18.0, 0.0))


def test_la_deuxieme_sous_couche_va_de_b_vers_a_et_le_satin_repart_de_a():
    contour = contour_satin()
    contour.underlays = ["centerline", "walking"]
    centre = underlay_points(contour, "centerline")
    marche = underlay_points(contour, "walking")
    satin = satin_stitch(contour, contour.satin_width, contour.satin_spacing)

    points = stitch_points(contour)
    debut_marche = len(centre)
    fin_marche = debut_marche + len(marche) - 2

    assert points[debut_marche] == pytest.approx(marche[-2])
    assert points[fin_marche] == pytest.approx((0.0, 0.0))
    assert points[-len(satin):] == pytest.approx(satin)


def test_la_troisieme_sous_couche_retourne_au_centre_avant_le_satin():
    contour = contour_satin()
    contour.underlays = ["centerline", "walking", "zigzag"]
    centre = underlay_points(contour, "centerline")
    marche = underlay_points(contour, "walking")
    zigzag = underlay_points(contour, "zigzag")
    satin = satin_stitch(contour, contour.satin_width, contour.satin_spacing)

    points = stitch_points(contour)
    debut_troisieme = len(centre) + len(marche) - 1
    debut_retour = debut_troisieme + len(zigzag)
    trajet_retour = list(reversed(centre))

    assert points[debut_troisieme] == pytest.approx(zigzag[0])
    assert points[debut_troisieme + len(zigzag) - 1] == pytest.approx(zigzag[-1])
    for point, attendu in zip(
        points[debut_retour:debut_retour + len(trajet_retour)], trajet_retour
    ):
        assert point == pytest.approx(attendu)
    assert points[-len(satin):] == pytest.approx(satin)


def test_les_sous_couches_sont_sauvegardees_et_facultatives():
    contour = contour_satin()
    contour.underlays = ["walking", "zigzag"]

    relu = Contour.from_dict(contour.to_dict())

    assert relu.underlays == ["walking", "zigzag"]
    assert Contour.from_dict({"points": []}).underlays == []


def test_un_type_de_sous_couche_inconnu_est_refuse():
    contour = contour_satin()
    with pytest.raises(ValueError):
        underlay_points(contour, "inconnu")

    data = contour.to_dict()
    data["underlays"] = ["inconnu"]
    with pytest.raises(ValueError):
        Contour.from_dict(data)
