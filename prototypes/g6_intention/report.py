"""Restitution textuelle lisible de l'intention de circulation (G6).

Aucun point, aucune rangée. Uniquement l'explication des choix du brodeur.
"""

from __future__ import annotations

try:
    from prototypes.g6_intention.intention import IntentionCirculation
except ImportError:
    from intention import IntentionCirculation  # type: ignore


def format_intention(intention: IntentionCirculation, nom: str = "forme") -> str:
    """Formatte l'intention de parcours de manière lisible pour les tests et l'utilisateur."""
    lignes = []
    lignes.append(f"=== INTENTION DE CIRCULATION : {nom.upper()} ===")
    lignes.append(f"Structure reconnue : {intention.structure.upper()}")
    lignes.append(f"Entrée naturelle   : Zone {intention.entry_zone}")
    lignes.append(f"Sortie naturelle   : Zone {intention.exit_zone}")
    lignes.append(f"Ordre de visite    : {' -> '.join(str(z) for z in intention.visit_order)}")
    
    if intention.zones_a_terminer_en_premier:
        lignes.append(f"Zones à terminer d'abord : {', '.join(str(z) for z in intention.zones_a_terminer_en_premier)}")
    if intention.zones_a_garder_ouvertes:
        lignes.append(f"Zones à garder ouvertes  : {', '.join(str(z) for z in intention.zones_a_garder_ouvertes)}")
    
    lignes.append("Reprises autorisées :")
    if intention.reprises_autorisees:
        for r in intention.reprises_autorisees:
            lignes.append(f"  * {r}")
    else:
        lignes.append("  * Aucune (interdiction stricte)")

    lignes.append("Étapes détaillées :")
    for i, etape in enumerate(intention.etapes, 1):
        reprise_str = f" [Reprise admise: {etape.motif_reprise}]" if etape.reprise_autorisee else ""
        lignes.append(f"  {i}. {etape.nom} ({etape.role}) -> {etape.action} : {etape.instruction}{reprise_str}")

    lignes.append("Journal décisionnel :")
    for j in intention.journal:
        lignes.append(f"  - {j}")

    return "\n".join(lignes)
