import math

import pytest

from core.objects import CORNER, Contour
from core.simulation import build_sequence, count_table
from core.stitches.engine import stitch_paths, stitch_points
from core.stitches.fill import fill_stitch, fill_stitch_segments


def rectangle(width=20.0, height=10.0):
    contour = Contour(closed=True, stitch_type="fill")
    for point in ((0, 0), (width, 0), (width, height), (0, height)):
        contour.add_point(*point, CORNER)
    return contour


def test_remplissage_rectangle_reste_dans_le_contour():
    points = fill_stitch(rectangle(), spacing_mm=2.0)

    assert len(points) == 10
    assert all(0 <= x <= 20 and 0 <= y <= 10 for x, y in points)
    assert points[0][1] < points[-1][1]


def test_remplissage_plus_serre_produit_plus_de_rangs():
    large = fill_stitch(rectangle(), spacing_mm=2.0)
    serre = fill_stitch(rectangle(), spacing_mm=1.0)

    assert len(serre) > len(large)


def test_remplissage_angle():
    points = fill_stitch(rectangle(), angle_deg=45.0, spacing_mm=2.0)

    assert len(points) >= 2
    assert any(abs(y1 - y2) > 1e-6 for (x1, y1), (x2, y2) in zip(points, points[1:]))


def test_engine_coud_le_fill_en_tatami_continu():
    """Nouvelle règle Fill tatami : rangées découpées en points puis
    sous-points cousus entre rangées et zones."""
    contour = Contour(closed=True, stitch_type="fill")
    for point in ((10, 10), (30, 10), (30, 20), (10, 20)):
        contour.add_point(*point, CORNER)

    paths = stitch_paths(contour)
    assert len(paths) == 1

    plat = [point for point in paths[0]]
    # Couverture : le remplissage occupe toujours la forme.
    assert all(10 - 1e-6 <= x <= 30 + 1e-6 for x, _ in plat)
    assert all(10 - 1e-6 <= y <= 20 + 1e-6 for _, y in plat)
    # Un point cousu ne dépasse jamais la longueur du point.
    ecarts = [
        math.hypot(b[0] - a[0], b[1] - a[1])
        for a, b in zip(plat, plat[1:])
    ]
    assert ecarts
    assert max(ecarts) <= contour.stitch_length + 1e-6
    # Le périmètre est parcouru bien au-delà des simples extrémités de rangées.
    assert len(plat) > 4


def test_remplissage_refuse_un_contour_ouvert():
    contour = rectangle()
    contour.closed = False

    with pytest.raises(ValueError, match="contour fermé"):
        fill_stitch(contour)


def test_remplissage_accepte_une_forme_concave():
    contour = Contour(closed=True, stitch_type="fill")
    for point in ((0, 0), (10, 0), (10, 10), (7, 10), (7, 3), (3, 3), (3, 10), (0, 10)):
        contour.add_point(*point, CORNER)

    points = fill_stitch(contour, spacing_mm=1.0)

    assert len(points) > 0
    assert all(0 <= x <= 10 and 0 <= y <= 10 for x, y in points)


def test_les_segments_de_remplissage_ne_cousent_pas_dans_le_creux_concave():
    contour = Contour(closed=True, stitch_type="fill")
    for point in ((0, 0), (10, 0), (10, 10), (7, 10), (7, 3), (3, 3), (3, 10), (0, 10)):
        contour.add_point(*point, CORNER)

    segments = fill_stitch_segments(contour, spacing_mm=1.0)

    assert len(segments) > 0
    assert all(len(segment) == 2 for segment in segments)
    assert all(
        not (min(x for x, _ in segment) < 7 and max(x for x, _ in segment) > 3)
        for segment in segments
        if segment[0][1] > 3
    )


def test_simulation_n_insere_aucun_saut_dans_un_bloc_fill():
    """Règle tatami EOS : à l'intérieur d'un bloc de remplissage, la machine
    ne saute jamais — les connections sont des sous-points cousus."""
    for points in (
        ((0, 0), (10, 0), (10, 10), (7, 10), (7, 3), (3, 3), (3, 10), (0, 10)),  # concave
        ((0, 0), (40, 0), (40, 30), (0, 30)),  # simple
    ):
        contour = Contour(closed=True, stitch_type="fill")
        contour.fill_spacing = 1.0
        for point in points:
            contour.add_point(*point, CORNER)

        steps = build_sequence([contour])
        premier_point = next(
            index for index, step in enumerate(steps) if step.kind == "stitch"
        )

        # Aucun saut après le premier point cousu : le bloc est continu.
        assert all(step.kind != "jump" for step in steps[premier_point:])
        # Le remplissage couvre les deux dimensions de la forme.
        plat = stitch_points(contour)
        assert all(0 - 1e-6 <= x <= max(40.0, 10.0) + 1e-6 for x, _ in plat)
        assert count_table(steps)[-1][0] == len(plat)


def test_sous_points_rejoignent_le_sommet_dans_une_forme_en_verre():
    """Comme dans EOS : quand le fill doit « recommencer » (zone détachée),
    il y arrive en sous-points cousus, jamais en saut."""
    contour = Contour(closed=True, stitch_type="fill")
    # Forme en verre : corps bas large + pied haut fin.
    for point in (
        (0, 0), (10, 0), (10, 6), (5, 8), (6, 14), (7, 20), (12, 22),
        (13, 15), (13, 7), (14, 2), (12, 0),
    ):
        contour.add_point(*point, CORNER)

    steps = build_sequence([contour])
    premier_point = next(
        index for index, step in enumerate(steps) if step.kind == "stitch"
    )
    assert all(step.kind != "jump" for step in steps[premier_point:])


def test_export_dst_accepte_un_remplissage_large(tmp_path):
    """Avant le découpage en points, une rangée de remplissage de plus de
    12,1 mm faisait échouer l'export DST. Ce n'est plus le cas."""
    from exporters.dst_io import export_dst, read_dst

    contour = Contour(closed=True, stitch_type="fill")
    for point in ((10, 10), (50, 10), (50, 40), (10, 40)):  # largeur 40 mm
        contour.add_point(*point, CORNER)

    chemin = tmp_path / "large.dst"
    resume = export_dst([contour], str(chemin))

    relu = read_dst(str(chemin))
    assert relu["stitches"] == resume["stitches"]
    assert resume["stitches"] > 0


def test_deplacement_d_une_zone_a_l_autre_est_une_couture_droite():
    """Modèle EOS : d'une zone contiguë à la suivante, l'aiguille se déplace
    en couture simple droite. Elle peut traverser l'espace vide du U (ce que
    fait EOS) : aucune rangée du remplissage n'est cousue par ce trajet."""
    from core.stitches.fill import _path_for_contour, _travel_side_points

    contour = Contour(closed=True, stitch_type="fill")
    for point in ((0, 0), (10, 0), (10, 10), (7, 10), (7, 3), (3, 3), (3, 10), (0, 10)):
        contour.add_point(*point, CORNER)
    outer = _path_for_contour(contour)

    a, b = (3.0, 9.5), (7.0, 9.5)
    points = _travel_side_points(a, b, outer, 2.5)

    assert points
    # Tous les points sont sur la droite a→b : couture simple, aucun détour.
    for point in points:
        croisement = (point[0] - a[0]) * (b[1] - a[1]) - (point[1] - a[1]) * (b[0] - a[0])
        assert abs(croisement) < 1e-9
    assert points[-1] == pytest.approx(b)
    # La ligne traverse le creux vide du U : c'est le comportement d'EOS.
    assert any(3.0 < point[0] < 7.0 for point in points)


def _arche():
    """Motif de référence : arche de 429,5 × 141,1 mm (deux jambes et une
    voûte), proche du dessin utilisé pour les mesures de performance."""
    contour = Contour(closed=True, stitch_type="fill")
    for point in (
        (0, 0), (0, 55), (30, 95), (90, 125), (170, 138), (214, 141),
        (258, 138), (338, 125), (398, 95), (429, 55), (429, 0),
        (368, 0), (365, 38), (340, 70), (300, 88), (214, 95), (127, 88),
        (89, 70), (64, 38), (61, 0),
    ):
        contour.add_point(*point, CORNER)
    return contour


def _rangs_cousus(plat, longueur_min=3.0):
    """Découpe une trajectoire en tronçons horizontaux consécutifs (rangées)."""
    rangs = []
    courant = [plat[0]]
    for precedent, point in zip(plat, plat[1:]):
        if abs(precedent[1] - point[1]) <= 1e-9:
            courant.append(point)
            continue
        if len(courant) >= 2:
            rangs.append(courant)
        courant = [point]
    if len(courant) >= 2:
        rangs.append(courant)
    return [
        rang for rang in rangs
        if abs(rang[-1][0] - rang[0][0]) >= longueur_min
    ]


def test_le_bloc_fill_se_termine_pres_du_point_d_arrivee():
    """Modèle EOS : la zone proche de l'arrivée est gardée pour la fin, donc
    le bloc se termine juste à côté du point choisi (plus de grande diagonale
    finale au-dessus du remplissage)."""
    from core.stitches.fill import fill_stitch_paths

    contour = _arche()
    contour.start_point = (30.0, 5.0)
    contour.end_point = (395.0, 5.0)

    plat = fill_stitch_paths(contour, 0.0, 2.0)[0]

    assert plat[0] == pytest.approx((30.0, 5.0))
    assert plat[-1] == pytest.approx((395.0, 5.0))
    rangs = _rangs_cousus(plat)
    assert len(rangs) >= 100
    # Le premier rang cousu est du côté du départ (bas de la jambe gauche)...
    assert abs(rangs[0][0][1] - 5.0) <= 3.0
    # ... et le dernier rang cousu est au bas de la jambe droite, près de
    # l'arrivée : l'approche finale reste courte.
    assert abs(rangs[-1][0][1] - 5.0) <= 8.0
    # Le bloc couvre toujours tout le motif (aucune rangée oubliée).
    assert max(y for _, y in plat) > 130.0
    assert max(x for x, _ in plat) > 420.0
    assert all(
        math.hypot(b[0] - a[0], b[1] - a[1]) <= 2.5 + 1e-6
        for a, b in zip(plat, plat[1:])
    )


def test_sous_points_contournent_un_trou():
    """Le chemin sous le remplissage doit rester hors des trous."""
    from core.stitches.fill import _path_for_contour, _travel_side_points

    contour = Contour(closed=True, stitch_type="fill")
    for point in ((0, 0), (40, 0), (40, 30), (0, 30)):
        contour.add_point(*point, CORNER)
    hole = Contour(closed=True, stitch_type="running")
    for point in ((15, 10), (25, 10), (25, 20), (15, 20)):
        hole.add_point(*point, CORNER)
    contour.add_hole(hole)
    outer = _path_for_contour(contour)
    holes = [_path_for_contour(hole)]

    points = _travel_side_points((5.0, 15.0), (35.0, 15.0), outer, 2.5, holes)

    assert points
    # Aucun point dans le trou.
    assert all(not (15.0 <= p[0] <= 25.0 and 10.0 <= p[1] <= 20.0) for p in points)


def test_premiere_rangee_fill_est_cousue():
    """Non-régression : la toute première rangée du remplissage doit être
    cousue (un bug avait retiré ses points de la trajectoire)."""
    from core.stitches.fill import fill_stitch_paths

    paths = fill_stitch_paths(rectangle(), 0.0, 2.0)
    plat = paths[0]
    # La rangée du haut (y = 1,0 mm pour un rectangle 20x10) va jusqu'a droite.
    assert any(abs(p[1] - 1.0) < 1e-6 and p[0] > 15.0 for p in plat)


def test_sous_point_tout_droit_quand_les_moves_ne_sont_pas_sur_le_bord():
    from core.stitches.fill import _path_for_contour, _travel_side_points

    contour = rectangle()
    outer = _path_for_contour(contour)

    points = _travel_side_points((2.0, 3.0), (8.0, 5.0), outer, 2.5)

    assert points
    # Trajet de repli en ligne droite entre les deux points intérieurs.
    for point in points:
        croisement = (point[0] - 2.0) * (5.0 - 3.0) - (point[1] - 3.0) * (8.0 - 2.0)
        assert abs(croisement) < 1e-9


def test_ordre_glouton_technique_plus_proche_voisin():
    """Ink/Stitch : les rangées sont cousues dans l'ordre du plus proche
    voisin. Départ déterministe : rangée la plus haute, extrémité gauche."""
    from core.stitches.fill import fill_stitch_paths

    contour = rectangle()
    paths = fill_stitch_paths(contour, 0.0, 2.0)

    plat = paths[0]
    # Départ : haut de la forme, côté gauche (hemme le haut du rectangle 20x10).
    assert plat[0][0] == pytest.approx(0.0, abs=1e-6)
    assert plat[0][1] == pytest.approx(1.0, abs=1e-3)
    # Puis la rangée est cousue vers la droite.
    assert plat[1][0] > plat[0][0]


def test_ordre_glouton_est_determine():
    """Deux exécutions donnent exactement la même trajectoire."""
    from core.stitches.fill import fill_stitch_paths

    contour = Contour(closed=True, stitch_type="fill")
    for point in ((0, 0), (10, 0), (10, 10), (7, 10), (7, 3), (3, 3), (3, 10), (0, 10)):
        contour.add_point(*point, CORNER)

    paths_a = fill_stitch_paths(contour, 0.0, 1.0)
    paths_b = fill_stitch_paths(contour, 0.0, 1.0)
    assert paths_a == paths_b


def test_longueur_point_fill_invalide_refusee():
    from core.stitches.fill import fill_stitch_paths

    for mauvais in (0.0, -1.0, 13.0):
        with pytest.raises(ValueError, match="longueur du point"):
            fill_stitch_paths(rectangle(), stitch_length=mauvais)


def test_parametres_fill_sont_sauvegardes():
    contour = rectangle()
    contour.fill_angle = 30.0
    contour.fill_spacing = 1.25

    relu = Contour.from_dict(contour.to_dict())

    assert relu.stitch_type == "fill"
    assert relu.fill_angle == pytest.approx(30.0)
    assert relu.fill_spacing == pytest.approx(1.25)


def test_remplissage_exclut_un_trou_explicite():
    outer = Contour(closed=True, stitch_type="fill")
    for point in ((0, 0), (10, 0), (10, 10), (0, 10)):
        outer.add_point(*point, CORNER)

    hole = Contour(closed=True, stitch_type="fill")
    for point in ((3, 3), (7, 3), (7, 7), (3, 7)):
        hole.add_point(*point, CORNER)
    outer.add_hole(hole)

    points = fill_stitch(outer, spacing_mm=1.0)

    assert all(not (3.0 <= x <= 7.0 and 3.0 <= y <= 7.0) for x, y in points)

    relu = Contour.from_dict(outer.to_dict())
    assert len(relu.holes) == 1
    assert len(relu.holes[0].points) == 4


def test_depart_et_arrivee_fill_sont_sauvegardes():
    """L'utilisateur est maître de son motif : son choix de départ et
    d'arrivée doit survivre à la sauvegarde."""
    contour = rectangle()
    contour.start_point = (3.5, 2.0)
    contour.end_point = (17.5, 8.0)

    relu = Contour.from_dict(contour.to_dict())

    assert relu.start_point == pytest.approx((3.5, 2.0))
    assert relu.end_point == pytest.approx((17.5, 8.0))
    # Sans point placé : reste None.
    assert Contour.from_dict(rectangle().to_dict()).start_point is None


def test_fill_commence_a_la_place_choisie():
    from core.stitches.fill import fill_stitch_paths

    contour = rectangle()
    contour.start_point = (10.0, 5.0)
    contour.end_point = (10.0, 1.0)

    plat = fill_stitch_paths(contour, 0.0, 2.0, 2.0)[0]

    # Le bloc démarre et s'arrête exactement la où l'utilisateur l'a décidé.
    assert plat[0] == pytest.approx((10.0, 5.0))
    assert plat[-1] == pytest.approx((10.0, 1.0))
    # La couverture du motif reste complete.
    assert max(x for x, _ in plat) == pytest.approx(20.0, abs=1e-6)
    # L'approche est cousue par sous-points (pas un bête écart de 10 mm).
    assert all(
        math.hypot(b[0] - a[0], b[1] - a[1]) <= 2.0 + 1e-6
        for a, b in zip(plat, plat[1:])
    )


def test_simulation_respecte_depart_et_arrivee_du_fill():
    """La règle tatami (0 saut dans le bloc) reste valable quand l'utilisateur
    impose son départ et son arrivée."""
    contour = Contour(closed=True, stitch_type="fill")
    for point in ((0, 0), (10, 0), (10, 10), (7, 10), (7, 3), (3, 3), (3, 10), (0, 10)):
        contour.add_point(*point, CORNER)
    contour.fill_spacing = 1.0
    contour.start_point = (1.5, 9.0)
    contour.end_point = (8.5, 1.5)

    steps = build_sequence([contour])
    premier_point = next(
        index for index, step in enumerate(steps) if step.kind == "stitch"
    )
    assert all(step.kind != "jump" for step in steps[premier_point:])
    assert count_table(steps)[-1][0] == len(stitch_points(contour))


def test_les_trajectoires_sont_mises_en_cache(monkeypatch):
    """Le canvas demande les points plusieurs fois par rafraîchissement : le
    moteur ne doit calculer qu'une fois pour un contour inchangé."""
    from core.stitches import engine

    contour = rectangle()
    appels = []
    vrai = engine._build_paths

    def espion(c):
        appels.append(c)
        return vrai(c)

    monkeypatch.setattr(engine, "_build_paths", espion)
    engine._cache.clear()

    premier = engine.stitch_paths(contour)
    second = engine.stitch_paths(contour)

    assert len(appels) == 1
    assert second == premier
    # Une vraie modification du contour invalide le cache.
    contour.fill_spacing = 1.0
    engine.stitch_paths(contour)
    assert len(appels) == 2


def test_le_bloc_fill_ne_coud_jamais_dans_un_trou_meme_en_deplacement():
    """Les déplacements entre zones peuvent traverser l'espace vide, mais
    jamais un trou explicite : le contournement est conservé."""
    from core.stitches.fill import fill_stitch_paths

    contour = Contour(closed=True, stitch_type="fill")
    for point in ((0, 0), (40, 0), (40, 30), (0, 30)):
        contour.add_point(*point, CORNER)
    hole = Contour(closed=True, stitch_type="running")
    for point in ((15, 12), (25, 12), (25, 18), (15, 18)):
        hole.add_point(*point, CORNER)
    contour.add_hole(hole)

    plat = fill_stitch_paths(contour, 0.0, 2.0)[0]

    assert plat
    assert all(
        not (15.0 + 1e-6 < x < 25.0 - 1e-6 and 12.0 + 1e-6 < y < 18.0 - 1e-6)
        for x, y in plat
    )
