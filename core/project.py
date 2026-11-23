import json
import math
import os
from dataclasses import dataclass, field

from core.objects import Contour
from core.machine_pattern import MachinePattern

FORMAT_NAME = "creabrod-project"
FORMAT_VERSION = 2


@dataclass
class Project:
    """Un projet Créabrod (fichier .crb) : le cadre, l'image de fond et les dessins."""

    frame_width: float = 130.0
    frame_height: float = 180.0
    image_path: str = ""
    contours: list = field(default_factory=list)
    machine_pattern: MachinePattern | None = None

    def to_dict(self):
        return {
            "format": FORMAT_NAME,
            "version": FORMAT_VERSION,
            "frame": {"width": self.frame_width, "height": self.frame_height},
            "image_path": self.image_path,
            "contours": [c.to_dict() for c in self.contours],
            "machine_pattern": self.machine_pattern.to_dict() if self.machine_pattern else None,
        }

    @classmethod
    def from_dict(cls, data):
        try:
            if not isinstance(data, dict) or data.get("format") != FORMAT_NAME:
                raise ValueError("Ce fichier n'est pas un projet Créabrod.")
            if data.get("version", 1) > FORMAT_VERSION:
                raise ValueError(
                    "Ce projet a été créé avec une version plus récente de Créabrod Digitizer."
                )

            frame = data.get("frame", {})
            width = float(frame.get("width", 130))
            height = float(frame.get("height", 180))
            if not (math.isfinite(width) and math.isfinite(height)):
                raise ValueError("Dimensions du cadre invalides.")
            if not (10 <= width <= 2000 and 10 <= height <= 2000):
                raise ValueError("Dimensions du cadre invalides.")

            contours = [Contour.from_dict(raw) for raw in data.get("contours", [])]
            machine_data = data.get("machine_pattern")
            machine_pattern = MachinePattern.from_dict(machine_data) if machine_data else None
            return cls(
                frame_width=width,
                frame_height=height,
                image_path=str(data.get("image_path", "")),
                contours=contours,
                machine_pattern=machine_pattern,
            )
        except (TypeError, KeyError, AttributeError) as erreur:
            raise ValueError(f"Données du projet invalides ({erreur!r}).") from erreur

    def save(self, path):
        """Enregistre le projet. Écrit d'abord un fichier temporaire, puis le remplace."""
        texte = json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
        chemin_temporaire = path + ".tmp"
        with open(chemin_temporaire, "w", encoding="utf-8") as fichier:
            fichier.write(texte)
        os.replace(chemin_temporaire, path)

    @classmethod
    def load(cls, path):
        """Lit un projet. Lève ValueError si le fichier est abîmé ou invalide."""
        try:
            with open(path, "r", encoding="utf-8") as fichier:
                data = json.load(fichier)
        except (json.JSONDecodeError, UnicodeDecodeError) as erreur:
            raise ValueError(f"Fichier illisible ou corrompu ({erreur}).") from erreur
        return cls.from_dict(data)
