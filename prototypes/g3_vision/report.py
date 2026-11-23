"""Restitution lisible d'une perception. Aucune decision, aucun point de couture."""

from __future__ import annotations

try:
    from prototypes.g3_vision.perception import Perception
except ImportError:  # execution depuis le dossier du prototype
    from perception import Perception  # type: ignore


def format_perception(perception: Perception, nom="forme") -> str:
    """Texte stable, utilisable dans les tests et dans le journal."""
    lignes = []
    lignes.append("=== {} ===".format(nom))
    lignes.append("grille : pas {:.2f} mm, {} cellules de matiere".format(
        perception.pas_grille, perception.cellules_matiere))
    lignes.append("zones : {}".format(len(perception.zones)))
    for zone in perception.zones:
        lignes.append(
            "  zone {id} : {classe}, surface {surface:.1f} mm2, "
            "degagement max {degagement:.2f} mm, degre {degre}, centre ({cx:.1f};{cy:.1f})"
            .format(id=zone.identifiant,
                    classe=zone.classe,
                    surface=zone.surface,
                    degagement=zone.degagement_max,
                    degre=zone.degre,
                    cx=zone.centre[0],
                    cy=zone.centre[1]))
    lignes.append("passages : {}".format(len(perception.passages)))
    for passage in perception.passages:
        lignes.append(
            "  zones {a}<->{b} : largeur {largeur:.2f} mm, "
            "col en ({px:.1f};{py:.1f}), {cellules} cellules d'interface"
            .format(a=passage.zone_a, b=passage.zone_b,
                    largeur=passage.largeur,
                    px=passage.position[0], py=passage.position[1],
                    cellules=passage.cellules))
    lignes.append("structures : {}".format(
        ", ".join(perception.structures) if perception.structures else "aucune"))
    lignes.append("candidats depart : {}".format(len(perception.depart_candidats)))
    for identifiant, point, degagement in perception.depart_candidats:
        lignes.append("  zone {} : ({:.1f};{:.1f}) degagement {:.2f} mm".format(
            identifiant, point[0], point[1], degagement))
    lignes.append("journal :")
    for ligne in perception.journal:
        lignes.append("  - " + ligne)
    return "\n".join(lignes)
