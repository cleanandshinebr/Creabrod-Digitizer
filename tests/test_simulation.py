from core.objects import Contour, CORNER
from core.machine_pattern import MachineCommand, MachinePattern
from core.simulation import build_machine_sequence, build_sequence, count_table
from core.stats import compute_stats


def deux_lignes():
    a = Contour(stitch_length=2.5)
    a.add_point(-30, -10, CORNER)
    a.add_point(30, -10, CORNER)
    b = Contour(stitch_length=2.5)
    b.add_point(-30, 10, CORNER)
    b.add_point(30, 10, CORNER)
    return [a, b]


def test_sequence_de_deux_dessins():
    steps = build_sequence(deux_lignes())
    assert len(steps) == 53  # saut + 25 points + coupe + saut + 25 points
    assert [s.kind for s in steps[:3]] == ["jump", "stitch", "stitch"]

    assert steps[26].kind == "trim"
    assert (steps[26].x, steps[26].y) == (30, -10)
    assert steps[27].kind == "jump"
    assert (steps[27].x, steps[27].y) == (-30, 10)
    assert steps[28].kind == "stitch"
    assert steps[1].obj == 0
    assert steps[28].obj == 1

    table = count_table(steps)
    assert table[0] == (0, 0, 0)
    assert table[1] == (0, 1, 0)
    assert table[-1] == (50, 2, 1)


def test_pas_de_saut_si_on_commence_au_centre():
    c = Contour(stitch_length=2.5)
    c.add_point(0, 0, CORNER)
    c.add_point(10, 0, CORNER)
    steps = build_sequence([c])
    assert steps[0].kind == "stitch"
    assert count_table(steps)[-1] == (5, 0, 0)


def test_rien_a_simuler():
    assert build_sequence([]) == []
    assert count_table([]) == [(0, 0, 0)]


def test_coherence_avec_les_statistiques():
    contours = deux_lignes()
    stats = compute_stats(contours, frame_size=(130, 180))
    total = count_table(build_sequence(contours))[-1]
    assert total == (stats.stitches, stats.jumps, stats.trims)


def test_connexion_running_supprime_le_saut_et_la_coupe():
    contours = deux_lignes()
    contours[0].connection_mode = "running"

    steps = build_sequence(contours)

    assert count_table(steps)[-1] == (75, 1, 0)
    assert all(step.kind != "trim" for step in steps)


def test_connexion_jump_conserve_le_saut_sans_coupe():
    contours = deux_lignes()
    contours[0].connection_mode = "jump"

    steps = build_sequence(contours)

    assert count_table(steps)[-1] == (50, 2, 0)
    assert all(step.kind != "trim" for step in steps)


def test_changement_de_couleur_entre_deux_contours():
    contours = deux_lignes()
    contours[1].thread_color = "#ff0000"

    steps = build_sequence(contours)

    changements = [step for step in steps if step.kind == "color_change"]
    assert len(changements) == 1
    assert changements[0].obj == 1


def test_simulation_motif_machine_conserve_lordre_des_commandes():
    motif = MachinePattern(
        "motif.dst",
        "DST",
        [
            MachineCommand("stitch", 0, 0, 0),
            MachineCommand("jump", 5, 0, 0),
            MachineCommand("trim", 5, 0, 0),
            MachineCommand("color_change", 5, 0, 0),
            MachineCommand("stitch", 10, 0, 1),
        ],
    )

    assert [step.kind for step in build_machine_sequence(motif)] == [
        "stitch", "jump", "trim", "color_change", "stitch"
    ]
