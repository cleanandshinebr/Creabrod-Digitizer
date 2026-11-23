import math

import pytest

from core.objects import Contour, CORNER, CURVE
from core.stitches.engine import stitch_points
from core.stitches.satin import satin_stitch


def polyligne(*points):
    c = Contour()
    for x, y in points:
        c.add_point(x, y, CORNER)
    return c


def ligne(longueur):
    return polyligne((0, 0), (longueur, 0))


def plus_long_point(points):
    return max(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:]))


def fil_par_mm2(points, cx, cy, rayon):
    """Longueur de fil par mm² dans un petit disque (pour comparer les densités)."""
    total = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        longueur = math.hypot(x2 - x1, y2 - y1)
        n = max(1, int(longueur / 0.02))
        for i in range(n):
            t = (i + 0.5) / n
            x = x1 + (x2 - x1) * t
            y = y1 + (y2 - y1) * t
            if math.hypot(x - cx, y - cy) <= rayon:
                total += longueur / n
    return total / (math.pi * rayon * rayon)


def test_colonne_droite():
    pts = satin_stitch(ligne(20), width_mm=4, spacing_mm=0.5)
    # Un point tous les 0,25 mm (l'écart de 0,5 mm est mesuré sur un même côté)
    assert len(pts) == 81
    assert pts[0] == pytest.approx((0, 2))        # bord gauche
    assert pts[1] == pytest.approx((0.25, -2))    # bord droit, 0,25 mm plus loin
    for k, (x, y) in enumerate(pts):
        assert x == pytest.approx(0.25 * k)
        assert abs(y) == pytest.approx(2)         # la colonne fait bien 4 mm de large


def test_densite_plus_serree_donne_plus_de_points():
    assert len(satin_stitch(ligne(20), spacing_mm=0.4)) == 101
    assert len(satin_stitch(ligne(20), spacing_mm=0.8)) == 51


def test_coin_a_angle_droit_en_onglet():
    c = polyligne((0, 0), (10, 0), (10, 10))
    pts = satin_stitch(c, width_mm=2, spacing_mm=0.5)

    assert plus_long_point(pts) <= 2.05  # aucun point trop long dans le coin (largeur 2 mm)

    # Le long du premier morceau, les points restent bien en travers de la colonne.
    for (x1, _), (x2, _) in zip(pts, pts[1:]):
        if x1 < 8 and x2 < 8:
            assert abs(x2 - x1) <= 0.26

    # Le coin est plein : la pointe extérieure est brodée.
    assert any(x > 10.4 and y < -0.4 for x, y in pts)

    # Aucun point ne dépasse la pointe de l'onglet (1,41 mm de la ligne centrale).
    for x, y in pts:
        assert c.distance_to(x, y) <= 1.42


def test_densite_identique_dans_les_coins():
    droite = satin_stitch(ligne(40), width_mm=3, spacing_mm=0.4)
    reference = fil_par_mm2(droite, 20, 0, 0.6)

    angle_droit = polyligne((0, 0), (20, 0), (20, 20))
    pts = satin_stitch(angle_droit, width_mm=3, spacing_mm=0.4)
    assert 0.85 <= fil_par_mm2(pts, 20, 0, 0.6) / reference <= 1.2

    en_v = polyligne((0, 0), (10, 20), (20, 0))
    pts = satin_stitch(en_v, width_mm=3, spacing_mm=0.4)
    assert 0.85 <= fil_par_mm2(pts, 10, 20, 0.6) / reference <= 1.2


def test_parametres_hors_limites():
    with pytest.raises(ValueError):
        satin_stitch(ligne(10), width_mm=0.5)
    with pytest.raises(ValueError):
        satin_stitch(ligne(10), width_mm=10)
    with pytest.raises(ValueError):
        satin_stitch(ligne(10), spacing_mm=0.2)   # densité excessive
    with pytest.raises(ValueError):
        satin_stitch(ligne(10), spacing_mm=2)


def test_dessins_trop_courts():
    un_point = Contour()
    un_point.add_point(5, 5, CORNER)
    assert satin_stitch(un_point) == []

    deux_points_identiques = polyligne((5, 5), (5, 5))
    assert satin_stitch(deux_points_identiques) == []


def test_aucun_point_trop_long_sur_des_formes_variees():
    rond = Contour()
    for i in range(9):
        angle = 2 * math.pi * i / 8
        rond.add_point(15 * math.cos(angle), 15 * math.sin(angle), CURVE)

    formes = [
        polyligne((0, 0), (20, 0), (20, 20)),
        polyligne((0, 0), (10, 20), (20, 0)),
        polyligne((0, 0), (20, 0), (0, 25), (20, 25)),            # un Z
        polyligne((0, 25), (0, 0), (10, 15), (20, 0), (20, 25)),  # un M
        rond,
    ]
    for forme in formes:
        for largeur in (1.0, 3.0, 7.0):
            for ecart in (0.3, 0.4, 1.0):
                pts = satin_stitch(forme, width_mm=largeur, spacing_mm=ecart)
                assert len(pts) > 2
                assert all(math.isfinite(x) and math.isfinite(y) for x, y in pts)
                assert plus_long_point(pts) <= largeur * 1.5 + 1.0


def test_trace_aberrant_ne_produit_pas_de_point_trop_long():
    # Un tracé tordu (boucles, demi-tour) : la méthode de secours doit prendre le relais.
    c = Contour()
    for x, y in [(-14.1, -14.2), (-15.0, -23.4), (-16.5, -10.2), (-2.9, -14.3),
                 (-14.8, -15.2), (-23.7, -11.5), (-24.3, -6.9)]:
        c.add_point(x, y, CURVE)
    pts = satin_stitch(c, width_mm=6.0, spacing_mm=0.4)
    assert len(pts) > 2
    assert plus_long_point(pts) <= 12.1


def test_contour_avec_coins_du_fichier_aenvoyer_couvre_toute_la_trajectoire():
    c = Contour(stitch_type="satin")
    for x, y, kind in [
        (11.7867, -41.3532, CURVE),
        (21.9751, -31.1647, CURVE),
        (32.1636, -17.5801, CURVE),
        (40.5541, -49.5439, CURVE),
        (15.9819, -61.7301, CURVE),
        (-28.5676, -57.9344, CURVE),
        (-30.7652, -45.5484, CORNER),
        (-13.5846, -40.3543, CORNER),
    ]:
        c.add_point(x, y, kind)

    pts = satin_stitch(c, width_mm=3.0, spacing_mm=0.4)

    assert max(x for x, y in pts) > 40
    assert min(x for x, y in pts) < -32
    assert plus_long_point(pts) <= 12.1


def test_insertion_satin_atteint_les_coins_du_fichier_aenvoyer():
    c = Contour(stitch_type="satin", satin_corner_mode="insertion")
    for x, y, kind in [
        (11.7867, -41.3532, CURVE),
        (21.9751, -31.1647, CURVE),
        (32.1636, -17.5801, CURVE),
        (40.5541, -49.5439, CURVE),
        (15.9819, -61.7301, CURVE),
        (-28.5676, -57.9344, CURVE),
        (-30.7652, -45.5484, CORNER),
        (-13.5846, -40.3543, CORNER),
    ]:
        c.add_point(x, y, kind)

    pts = satin_stitch(c, width_mm=3.0, spacing_mm=0.4)
    for x, y, kind in c.points:
        if kind == CORNER:
            assert min(math.hypot(px - x, py - y) for px, py in pts) < 0.01


def test_le_moteur_choisit_le_satin():
    c = ligne(10)
    c.stitch_type = "satin"
    c.satin_width = 3.0
    c.satin_spacing = 0.5
    assert len(stitch_points(c)) == 41

    c.stitch_type = "running"
    assert len(stitch_points(c)) == 5  # running stitch, point de 2,5 mm


def test_sauvegarde_du_satin():
    c = Contour(stitch_type="satin", satin_width=4.5, satin_spacing=0.35)
    c.add_point(0, 0, CORNER)
    c.add_point(10, 5, CURVE)
    relu = Contour.from_dict(c.to_dict())
    assert relu.stitch_type == "satin"
    assert relu.satin_width == 4.5
    assert relu.satin_spacing == 0.35

    # Un ancien fichier, sans réglages de satin, doit toujours s'ouvrir.
    ancien = Contour.from_dict({"points": [{"x": 0, "y": 0, "type": "corner"}]})
    assert ancien.stitch_type == "running"
    assert ancien.satin_width == 3.0

    # Un ancien écart trop petit est ramené au minimum actuel.
    serre = Contour.from_dict({"satin_spacing": 0.2, "points": []})
    assert serre.satin_spacing == 0.3

    mauvais = c.to_dict()
    mauvais["satin_width"] = 50
    with pytest.raises(ValueError):
        Contour.from_dict(mauvais)
