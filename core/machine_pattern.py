"""Lecture et représentation minimale des motifs machine importés."""

from dataclasses import dataclass
import math
import os

import pyembroidery


UNIT_MM = 10.0
SUPPORTED_MACHINE_EXTENSIONS = (".dst", ".pes", ".jef", ".vp3", ".exp", ".pec", ".hus")
_NOMS_FORMATS = {".dst": "DST", ".pes": "PES", ".jef": "JEF", ".vp3": "VP3", ".exp": "EXP", ".pec": "PEC", ".hus": "HUS"}
DEFAULT_THREAD_COLORS = ["#1b3a6b", "#9b2226", "#386641", "#6a4c93", "#ca6702"]


@dataclass(frozen=True)
class MachineCommand:
    kind: str
    x: float
    y: float
    color: int


@dataclass
class MachinePattern:
    source_path: str
    format_name: str
    commands: list
    thread_colors: list = None

    def to_dict(self):
        return {
            "source_path": self.source_path,
            "format_name": self.format_name,
            "thread_colors": list(self.thread_colors or []),
            "commands": [
                {"kind": c.kind, "x": c.x, "y": c.y, "color": c.color}
                for c in self.commands
            ],
        }

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise ValueError("Motif machine invalide dans le projet.")
        commandes = []
        types = {"stitch", "jump", "trim", "color_change"}
        for raw in data.get("commands", []):
            kind = str(raw["kind"])
            x = float(raw["x"])
            y = float(raw["y"])
            color = int(raw.get("color", 0))
            if kind not in types or not all(math.isfinite(v) for v in (x, y)) or color < 0:
                raise ValueError("Commande machine invalide dans le projet.")
            commandes.append(MachineCommand(kind, x, y, color))
        if not any(c.kind == "stitch" for c in commandes):
            raise ValueError("Le motif machine du projet ne contient aucun point.")
        colors = [str(color) for color in data.get("thread_colors", [])]
        return cls(str(data.get("source_path", "")), str(data.get("format_name", "")), commandes, colors)

    @property
    def stitches(self):
        return sum(command.kind == "stitch" for command in self.commands)

    @property
    def jumps(self):
        return sum(command.kind == "jump" for command in self.commands)

    @property
    def trims(self):
        return sum(command.kind == "trim" for command in self.commands)

    @property
    def color_changes(self):
        return sum(command.kind == "color_change" for command in self.commands)

    def bounds(self):
        points = [command for command in self.commands if command.kind == "stitch"]
        if not points:
            return (0.0, 0.0, 0.0, 0.0)
        xs = [point.x for point in points]
        ys = [point.y for point in points]
        return min(xs), min(ys), max(xs), max(ys)

    def to_emb_pattern(self):
        pattern = pyembroidery.EmbPattern()
        for command in self.commands:
            code = {"stitch": pyembroidery.STITCH, "jump": pyembroidery.JUMP, "trim": pyembroidery.TRIM, "color_change": pyembroidery.COLOR_CHANGE}[command.kind]
            pattern.add_stitch_absolute(code, round(command.x * UNIT_MM), round(command.y * UNIT_MM))
        pattern.add_stitch_absolute(pyembroidery.END, 0, 0)
        return pattern


def read_machine_pattern(path):
    path = os.fspath(path)
    extension = os.path.splitext(path)[1].lower()
    if extension not in SUPPORTED_MACHINE_EXTENSIONS:
        raise ValueError("Format machine non pris en charge dans cette version.")
    pattern = pyembroidery.read(path)
    if pattern is None or not pattern.stitches:
        raise ValueError("Le fichier de broderie est vide ou illisible.")

    raw = []
    color = 0
    for x, y, command in pattern.stitches:
        code = command & 0xFF
        if code == pyembroidery.END:
            break
        if code == pyembroidery.COLOR_CHANGE:
            raw.append(("color_change", x / UNIT_MM, y / UNIT_MM, color))
            color += 1
        elif code == pyembroidery.JUMP:
            raw.append(("jump", x / UNIT_MM, y / UNIT_MM, color))
        elif code == pyembroidery.TRIM:
            raw.append(("trim", x / UNIT_MM, y / UNIT_MM, color))
        elif code == pyembroidery.STITCH:
            raw.append(("stitch", x / UNIT_MM, y / UNIT_MM, color))

    stitches = [item for item in raw if item[0] == "stitch"]
    if not stitches:
        raise ValueError("Le fichier ne contient aucun point de broderie.")
    centre_x = (min(item[1] for item in stitches) + max(item[1] for item in stitches)) / 2
    centre_y = (min(item[2] for item in stitches) + max(item[2] for item in stitches)) / 2
    commands = [MachineCommand(kind, x - centre_x, y - centre_y, color) for kind, x, y, color in raw]
    thread_colors = []
    for thread in getattr(pattern, "threadlist", []):
        color = getattr(thread, "thread", None)
        if color:
            thread_colors.append(str(color))
    if not thread_colors:
        thread_colors = list(DEFAULT_THREAD_COLORS)
    return MachinePattern(path, _NOMS_FORMATS[extension], commands, thread_colors)
