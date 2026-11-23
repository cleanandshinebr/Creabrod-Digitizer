"""Contrat des mesures d'observation du remplissage (étape B2A).

Ce module ne contient **aucune logique de couture** : uniquement les structures
de données décrites dans ``docs/B2A_METRICS.md`` (version 1), et les deux
constantes de seuil associées.

Règle de stabilité : les noms de champs forment le contrat d'interface. Toute
mesure ajoutée, renommée ou supprimée impose d'incrémenter
``OBSERVATION_VERSION`` et de mettre ``docs/B2A_METRICS.md`` à jour dans le même
commit.
"""

from dataclasses import asdict, dataclass, field

#: Version du contrat décrit dans docs/B2A_METRICS.md.
OBSERVATION_VERSION = 1

#: Seuils d'alerte des liaisons cousues, en millimètres.
#: 10 mm : reprise déjà suspecte ; 20 mm : limite haute du planificateur ;
#: 40 mm : encadre le défaut historique de 46 mm.
LINK_ALERT_THRESHOLDS_MM = (10.0, 20.0, 40.0)


@dataclass
class LinkStats:
    """Statistiques d'un jeu de liaisons cousues (définitions : §3.1)."""

    count: int = 0
    total_length: float = 0.0
    max_length: float = 0.0
    over_10mm: int = 0
    over_20mm: int = 0
    over_40mm: int = 0


def link_stats(lengths) -> LinkStats:
    """Agrège une suite de longueurs de liaisons (en mm).

    Les seuils sont appliqués en comparaison **stricte** ; une liaison de
    longueur exactement égale à 10, 20 ou 40 mm n'est pas comptée.
    """
    valeurs = [float(longueur) for longueur in lengths]
    seuil_10, seuil_20, seuil_40 = LINK_ALERT_THRESHOLDS_MM
    return LinkStats(
        count=len(valeurs),
        total_length=sum(valeurs),
        max_length=max(valeurs, default=0.0),
        over_10mm=sum(1 for valeur in valeurs if valeur > seuil_10),
        over_20mm=sum(1 for valeur in valeurs if valeur > seuil_20),
        over_40mm=sum(1 for valeur in valeurs if valeur > seuil_40),
    )


@dataclass
class FillObservation:
    """Observation complète d'un appel à ``fill_stitch_paths``.

    La structure est **remplie en place** par le moteur quand l'appelant la
    fournit ::

        observation = FillObservation()
        chemins = fill_stitch_paths(contour, observation=observation)

    Elle ne participe à aucune décision : la trajectoire renvoyée est identique
    avec ou sans observation.
    """

    version: int = OBSERVATION_VERSION
    error: str = ""
    rows_total: int = 0
    rows_sewn: int = 0
    completed: bool = False
    failure: str = ""
    refused_link_count: int = 0
    refused_links: tuple = ()
    visible_link_count: int = 0
    visible_link_total: float = 0.0
    turns: int = 0
    max_turn_outside: float = 0.0
    arrival_length: float = 0.0
    plan: LinkStats = field(default_factory=LinkStats)
    greedy: LinkStats = field(default_factory=LinkStats)
    greedy_arrival_length: float = 0.0
    plan_seconds: float = 0.0
    greedy_seconds: float = 0.0
    total_seconds: float = 0.0

    def to_dict(self) -> dict:
        """Représentation pour les rapports : clés = noms de champs."""
        return asdict(self)
