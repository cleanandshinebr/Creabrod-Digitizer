import math
from dataclasses import dataclass

from core.stitches.engine import stitch_paths


CONNECTION_STITCH_LENGTH_MM = 2.5


@dataclass(frozen=True)
class Step:
    """Une étape de la broderie."""

    kind: str   # "stitch" (point), "jump" (saut) ou "trim" (coupe du fil)
    x: float    # position (mm) après cette étape
    y: float
    obj: int    # numéro du dessin (0, 1, 2...)
    color: int = 0


@dataclass
class Progress:
    """Où en est la simulation (envoyé au panneau de simulation)."""

    position: int = 0
    steps_total: int = 0
    stitches: int = 0
    stitches_total: int = 0
    jumps: int = 0
    jumps_total: int = 0
    trims: int = 0
    trims_total: int = 0
    colors: int = 0
    colors_total: int = 0
    description: str = ""


def build_sequence(contours):
    """Liste des étapes de la broderie, dans le même ordre que l'export DST.

    Pour chaque dessin : un saut vers son début (si besoin), puis ses points.
    Entre deux dessins : une coupe du fil.
    """
    objects = [
        (contour, [path for path in stitch_paths(contour) if len(path) >= 2])
        for contour in contours
    ]
    objects = [(contour, paths) for contour, paths in objects if paths]

    steps = []
    position = (0.0, 0.0)  # la machine démarre au centre du cadre
    for index, (contour, paths) in enumerate(objects):
        first_path = paths[0]
        if index > 0:
            mode = objects[index - 1][0].connection_mode
            if mode == "trim_then_jump":
                steps.append(Step("trim", position[0], position[1], index - 1))
            if contour.thread_color.lower() != objects[index - 1][0].thread_color.lower():
                steps.append(Step("color_change", position[0], position[1], index))
            if mode == "running":
                distance = math.hypot(first_path[0][0] - position[0], first_path[0][1] - position[1])
                if distance > 0:
                    intervals = max(1, math.ceil(distance / CONNECTION_STITCH_LENGTH_MM))
                    for step_index in range(1, intervals + 1):
                        fraction = step_index / intervals
                        steps.append(
                            Step(
                                "stitch",
                                position[0] + (first_path[0][0] - position[0]) * fraction,
                                position[1] + (first_path[0][1] - position[1]) * fraction,
                                index,
                            )
                        )
            elif math.hypot(first_path[0][0] - position[0], first_path[0][1] - position[1]) > 0:
                steps.append(Step("jump", first_path[0][0], first_path[0][1], index))
        elif math.hypot(first_path[0][0] - position[0], first_path[0][1] - position[1]) > 0:
            steps.append(Step("jump", first_path[0][0], first_path[0][1], index))
        start_index = 1 if index > 0 and objects[index - 1][0].connection_mode == "running" else 0
        for path_index, path in enumerate(paths):
            if path_index:
                if math.hypot(path[0][0] - position[0], path[0][1] - position[1]) > 0:
                    steps.append(Step("jump", path[0][0], path[0][1], index))
            path_start = start_index if path_index == 0 else 0
            for x, y in path[path_start:]:
                steps.append(Step("stitch", x, y, index))
            position = path[-1]
    return steps


def build_machine_sequence(pattern):
    """Transforme les commandes d'un motif machine en étapes de simulation."""
    return [
        Step(command.kind, command.x, command.y, 0, command.color)
        for command in pattern.commands
        if command.kind in {"stitch", "jump", "trim", "color_change"}
    ]


def count_table(steps):
    """Tableau de comptage : table[i] = (points, sauts, coupes) après i étapes."""
    table = [(0, 0, 0)]
    stitches = jumps = trims = 0
    for step in steps:
        if step.kind == "stitch":
            stitches += 1
        elif step.kind == "jump":
            jumps += 1
        elif step.kind == "trim":
            trims += 1
        table.append((stitches, jumps, trims))
    return table
