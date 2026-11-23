"""Moteur d'intention de circulation du brodeur (Étape G6).

Ce module décide de l'ordre naturel de parcours d'une forme à partir de
sa topologie perçue (G3/G4) et des règles métier du brodeur (G5).

Aucun point de couture, aucune rangée, aucun export, aucun calcul de densité.
Le moteur choisit, le moteur explique, le moteur s'arrête.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EtapeCirculation:
    """Une étape dans l'intention de circulation."""

    zone_id: Any
    nom: str
    role: str  # 'entree', 'transit', 'cul_de_sac_aller_retour', 'consolidation_noeud', 'sortie'
    action: str  # 'amorcer', 'traverser_continu', 'resorber_impasse', 'consolider_centre', 'terminer'
    reprise_autorisee: bool = False
    motif_reprise: str = ""
    instruction: str = ""


@dataclass
class IntentionCirculation:
    """L'intention complète de circulation sur une structure."""

    structure: str  # 'chambre_unitaire', 'corridor', 'pont', 'anneau', 'fourche', 'carrefour', 'arborescence'
    entry_zone: Any
    exit_zone: Any
    visit_order: list[Any]
    etapes: list[EtapeCirculation] = field(default_factory=list)
    zones_a_terminer_en_premier: list[Any] = field(default_factory=list)
    zones_a_garder_ouvertes: list[Any] = field(default_factory=list)
    reprises_autorisees: list[str] = field(default_factory=list)
    journal: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "structure": self.structure,
            "entry_zone": self.entry_zone,
            "exit_zone": self.exit_zone,
            "visit_order": self.visit_order,
            "zones_a_terminer_en_premier": self.zones_a_terminer_en_premier,
            "zones_a_garder_ouvertes": self.zones_a_garder_ouvertes,
            "reprises_autorisees": self.reprises_autorisees,
            "journal": self.journal,
        }


# ---------------------------------------------------------------------------
# Normalisation des entrées G3 / G4
# ---------------------------------------------------------------------------


def _extraire_graphe(source: Any) -> dict[str, Any]:
    """Convertit un objet Perception G3 ou un dictionnaire en graphe canonique."""
    if isinstance(source, dict):
        return source

    # Si c'est un objet Perception de G3
    zones_dict = {}
    for z in getattr(source, "zones", []):
        zid = getattr(z, "identifiant", z)
        classe = getattr(z, "classe", "zone")
        centre = getattr(z, "centre", (0.0, 0.0))
        surface = getattr(z, "surface", 0.0)
        zones_dict[zid] = {
            "id": zid,
            "classe": classe,
            "centre": centre,
            "surface": surface,
            "degre": getattr(z, "degre", 0),
        }

    adjacences: dict[Any, set[Any]] = {zid: set() for zid in zones_dict}
    passages_list = []
    for p in getattr(source, "passages", []):
        za = getattr(p, "zone_a", None)
        zb = getattr(p, "zone_b", None)
        largeur = getattr(p, "largeur", 0.0)
        pos = getattr(p, "position", (0.0, 0.0))
        if za is not None and zb is not None:
            adjacences.setdefault(za, set()).add(zb)
            adjacences.setdefault(zb, set()).add(za)
            passages_list.append({"a": za, "b": zb, "largeur": largeur, "position": pos})

    structures = list(getattr(source, "structures", []))
    depart_candidats = list(getattr(source, "depart_candidats", []))

    return {
        "zones": zones_dict,
        "adjacences": {k: sorted(v) for k, v in adjacences.items()},
        "passages": passages_list,
        "structures": structures,
        "depart_candidats": depart_candidats,
    }


# ---------------------------------------------------------------------------
# Moteur de décision stratégique
# ---------------------------------------------------------------------------


def plan_intention(source: Any,
                   entry_preference: Any = None,
                   exit_preference: Any = None,
                   entry_pref: Any = None,
                   exit_pref: Any = None,
                   **kwargs: Any) -> IntentionCirculation:
    """Produit l'intention de circulation du brodeur pour la forme donnée."""
    if entry_pref is not None and entry_preference is None:
        entry_preference = entry_pref
    if exit_pref is not None and exit_preference is None:
        exit_preference = exit_pref
    graphe = _extraire_graphe(source)
    zones = graphe.get("zones", {})
    adj = graphe.get("adjacences", {})
    structures = [s.lower() for s in graphe.get("structures", [])]
    passages = graphe.get("passages", [])

    # 1. Détection de la macro-structure
    structure_type = _qualifier_structure(zones, adj, structures, passages)

    # 2. Application de la stratégie G5 appropriée
    if structure_type == "chambre_unitaire":
        return _plan_chambre_unitaire(zones, entry_preference, exit_preference)
    elif structure_type == "pont":
        return _plan_pont(zones, adj, entry_preference, exit_preference)
    elif structure_type == "anneau":
        return _plan_anneau(zones, adj, entry_preference, exit_preference)
    elif structure_type == "corridor":
        return _plan_corridor(zones, adj, entry_preference, exit_preference)
    elif structure_type == "fourche":
        return _plan_fourche(zones, adj, entry_preference, exit_preference)
    elif structure_type == "carrefour":
        return _plan_carrefour(zones, adj, entry_preference, exit_preference)
    elif structure_type == "arborescence":
        return _plan_arborescence(zones, adj, entry_preference, exit_preference)
    else:
        # Repli générique sécurisé sur chaîne / graphe connexe
        return _plan_chaine_generique(zones, adj, entry_preference, exit_preference)


def _qualifier_structure(zones: dict, adj: dict, structures: list[str], passages: list) -> str:
    """Détermine le type de structure parmi les 7 catégories de G4/G5."""
    if "pont" in structures:
        return "pont"
    if "anneau" in structures:
        return "anneau"

    nb_zones = len(zones)
    if nb_zones <= 1:
        return "chambre_unitaire"

    # Degrés des nœuds
    degres = {zid: len(voisins) for zid, voisins in adj.items()}
    degre_max = max(degres.values()) if degres else 0
    terminales = [zid for zid, deg in degres.items() if deg <= 1]

    # Carrefour : nœud central de degré >= 4
    if degre_max >= 4:
        return "carrefour"

    # Fourche : nœud de degré 3 avec exactement 2 ou 3 branches terminales dans un petit graphe
    if degre_max == 3 and nb_zones in (3, 4):
        return "fourche"

    # Arborescence : nœud de degré >= 3 avec plusieurs ramifications
    if degre_max >= 3:
        return "arborescence"

    # Anneau sans étiquette explicite : cycle pur (tous degrés == 2)
    if nb_zones >= 3 and all(deg == 2 for deg in degres.values()):
        return "anneau"

    # Pont géométrique ou fonctionnel : 2 terminales séparées par une transition (degrés 1, 1, 2)
    if sorted(degres.values()) == [1, 1, 2] and "pont" in structures:
        return "pont"

    # Corridor / Chaîne linéaire : 2 terminales et des transitions de degré 2
    if len(terminales) == 2 and all(deg <= 2 for deg in degres.values()):
        return "corridor"

    return "corridor"


# ---------------------------------------------------------------------------
# 1. Chambre unitaire
# ---------------------------------------------------------------------------


def _plan_chambre_unitaire(zones: dict, entry_pref: Any, exit_pref: Any) -> IntentionCirculation:
    zone_id = list(zones.keys())[0] if zones else 1
    journal = [
        "Structure détectée = Chambre unitaire (salle unique sans col ni étranglement)",
        f"Entrée choisie = Zone {zone_id} (pôle amont / coin d'attaque)",
        f"Sortie choisie = Zone {zone_id} (pôle aval / coin opposé)",
        "Raison = Balayage continu et monotone sans retour en arrière",
        "Aucune reprise autorisée (aucune matière future pour la recouvrir)",
    ]
    etapes = [
        EtapeCirculation(
            zone_id=zone_id,
            nom=f"Zone {zone_id}",
            role="chambre_complete",
            action="balayage_monotone",
            reprise_autorisee=False,
            instruction="Balayage continu de l'entrée vers la sortie opposée",
        )
    ]
    return IntentionCirculation(
        structure="chambre_unitaire",
        entry_zone=zone_id,
        exit_zone=zone_id,
        visit_order=[zone_id],
        etapes=etapes,
        zones_a_terminer_en_premier=[zone_id],
        zones_a_garder_ouvertes=[zone_id],
        reprises_autorisees=[],
        journal=journal,
    )


# ---------------------------------------------------------------------------
# 2. Corridor (ex: Forme en U)
# ---------------------------------------------------------------------------


def _plan_corridor(zones: dict, adj: dict, entry_pref: Any, exit_pref: Any) -> IntentionCirculation:
    degres = {zid: len(voisins) for zid, voisins in adj.items()}
    terminales = [zid for zid, deg in degres.items() if deg <= 1]

    # Sélection entrée / sortie
    if entry_pref in terminales:
        entry = entry_pref
        terminales.remove(entry)
        exit_zone = exit_pref if exit_pref in terminales else terminales[0]
    elif exit_pref in terminales:
        exit_zone = exit_pref
        terminales.remove(exit_zone)
        entry = terminales[0]
    else:
        # Ordre naturel : de gauche à droite ou selon identifiants
        entry = terminales[0]
        exit_zone = terminales[1] if len(terminales) > 1 else terminales[0]

    # Reconstruction de la chaîne de l'entrée vers la sortie
    visit_order = [entry]
    courant = entry
    visites = {entry}
    while courant != exit_zone:
        voisins = [v for v in adj.get(courant, []) if v not in visites]
        if not voisins:
            break
        courant = voisins[0]
        visites.add(courant)
        visit_order.append(courant)

    if exit_zone not in visit_order:
        visit_order.append(exit_zone)

    journal = [
        "Structure détectée = Corridor (chaîne linéaire fermée d'extrémités terminales)",
        f"Entrée choisie = Zone {entry} (zone terminale de départ)",
        f"Sortie choisie = Zone {exit_zone} (zone terminale opposée)",
        f"Zone terminale {entry} soldée intégralement avant d'engager le corridor",
        "Traversée du corridor en passe continue dans l'axe directeur",
        f"Couloir de transit et sortie {exit_zone} gardés ouverts jusqu'à la traversée",
    ]

    etapes = [
        EtapeCirculation(
            zone_id=entry,
            nom=f"Zone {entry}",
            role="entree",
            action="amorcer_et_clore_terminale",
            reprise_autorisee=False,
            instruction="Clore entièrement la zone terminale avant de franchir le col",
        )
    ]
    for zid in visit_order[1:-1]:
        etapes.append(
            EtapeCirculation(
                zone_id=zid,
                nom=f"Zone {zid}",
                role="transit",
                action="traverser_continu",
                reprise_autorisee=True,
                motif_reprise="Reprise sous-jacente permise dans l'axe du couloir vers l'avant",
                instruction="Traverser en passe unique sans rebroussement",
            )
        )
    etapes.append(
        EtapeCirculation(
            zone_id=exit_zone,
            nom=f"Zone {exit_zone}",
            role="sortie",
            action="terminer",
            reprise_autorisee=False,
            instruction="Finition définitive sur l'extrémité aval",
        )
    )

    return IntentionCirculation(
        structure="corridor",
        entry_zone=entry,
        exit_zone=exit_zone,
        visit_order=visit_order,
        etapes=etapes,
        zones_a_terminer_en_premier=[entry],
        zones_a_garder_ouvertes=visit_order[1:],
        reprises_autorisees=["Reprise axiale sous-jacente vers l'avant autorisée dans le couloir"],
        journal=journal,
    )


# ---------------------------------------------------------------------------
# 3. Pont (Arche : Culée A -> Voûte -> Culée B)
# ---------------------------------------------------------------------------


def _plan_pont(zones: dict, adj: dict, entry_pref: Any, exit_pref: Any) -> IntentionCirculation:
    degres = {zid: len(voisins) for zid, voisins in adj.items()}
    culees = [zid for zid, deg in degres.items() if deg <= 1]
    voutes = [zid for zid, deg in degres.items() if deg == 2]

    # Si l'arche est représentée comme 1 zone physique continue mais structure Pont
    if len(zones) <= 1:
        entry = "culee_gauche"
        voute = "voute"
        exit_zone = "culee_droite"
        visit_order = ["culee_gauche", "voute", "culee_droite"]
    else:
        entry = entry_pref if entry_pref in culees else (culees[0] if culees else 1)
        exit_zone = exit_pref if exit_pref in culees and exit_pref != entry else (culees[1] if len(culees) > 1 else culees[0])
        voute = voutes[0] if voutes else "voute"
        visit_order = [entry, voute, exit_zone]

    journal = [
        "Structure détectée = Pont (deux culées d'ancrage reliées par une voûte cintrée)",
        f"Entrée choisie = {entry} (pied d'ancrage amont)",
        f"Raison = zone terminale d'appui au sol",
        f"Sortie choisie = {exit_zone} (pied d'ancrage aval)",
        f"Raison = extrémité opposée de transfert",
        f"{entry} terminée intégralement de la base jusqu'à l'épaule",
        f"Voûte franchie d'une épaule à l'autre en éventail sans demi-tour au sommet",
        f"Voûte et {exit_zone} conservées ouvertes jusqu'à la traversée",
        "Reprises interdites sous la voûte (corde visible) ; admise seulement à l'épaule",
    ]

    etapes = [
        EtapeCirculation(
            zone_id=entry,
            nom="Culée d'entrée",
            role="entree",
            action="remplir_base_vers_epaule",
            reprise_autorisee=False,
            instruction="Achever intégralement la culée au moment d'atteindre l'épaule",
        ),
        EtapeCirculation(
            zone_id=voute,
            nom="Voûte cintrée",
            role="transit_courbe",
            action="traverser_continu_eventail",
            reprise_autorisee=False,
            instruction="Franchir la voûte en continuité d'une épaule à l'autre sans demi-tour",
        ),
        EtapeCirculation(
            zone_id=exit_zone,
            nom="Culée de sortie",
            role="sortie",
            action="remplir_epaule_vers_base",
            reprise_autorisee=False,
            instruction="Descendre de l'épaule vers la base pour clore le motif",
        ),
    ]

    return IntentionCirculation(
        structure="pont",
        entry_zone=entry,
        exit_zone=exit_zone,
        visit_order=visit_order,
        etapes=etapes,
        zones_a_terminer_en_premier=[entry],
        zones_a_garder_ouvertes=[voute, exit_zone],
        reprises_autorisees=["Reprise locale admise dans l'épaisseur de l'épaule"],
        journal=journal,
    )


# ---------------------------------------------------------------------------
# 4. Anneau (Circuit fermé)
# ---------------------------------------------------------------------------


def _plan_anneau(zones: dict, adj: dict, entry_pref: Any, exit_pref: Any) -> IntentionCirculation:
    liste_zones = list(zones.keys())
    entry = entry_pref if entry_pref in zones else liste_zones[0]

    # Reconstitution du cycle fermé
    visit_order = [entry]
    courant = entry
    visites = {entry}

    while len(visit_order) < len(zones):
        voisins = [v for v in adj.get(courant, []) if v not in visites]
        if not voisins:
            # repli sur voisins du graphe
            voisins = [v for v in adj.get(courant, []) if v != entry]
            if not voisins:
                break
        suivant = voisins[0]
        visites.add(suivant)
        visit_order.append(suivant)
        courant = suivant

    # Le bouclage revient à la zone d'entrée
    visit_order.append(entry)

    journal = [
        "Structure détectée = Anneau (circuit fermé de corridors entourant un vide)",
        f"Entrée choisie = Zone {entry} (coin amont d'amorçage)",
        "Rotation continue unidirectionnelle le long du cycle sans rebroussement",
        f"Sortie choisie = Zone {entry} (bouclage sur le point d'origine)",
        "Secteur de jonction final préservé ouvert pour accueillir la fermeture du tour",
        "Reprise de raccord autorisée dans le coin épais lors du bouclage final",
    ]

    etapes = []
    for idx, zid in enumerate(visit_order[:-1]):
        etapes.append(
            EtapeCirculation(
                zone_id=zid,
                nom=f"Zone {zid}",
                role="boucle_secteur",
                action="rotation_unidirectionnelle",
                reprise_autorisee=(idx == 0),
                motif_reprise="Reprise d'amorce" if idx == 0 else "",
                instruction=f"Secteur {idx+1}/{len(zones)} de la boucle",
            )
        )
    etapes.append(
        EtapeCirculation(
            zone_id=entry,
            nom=f"Zone {entry} (fermeture)",
            role="sortie",
            action="bouclage_final",
            reprise_autorisee=True,
            motif_reprise="Raccord de fermeture dans l'épaisseur du coin",
            instruction="Soudure finale sans surépaisseur au point d'origine",
        )
    )

    return IntentionCirculation(
        structure="anneau",
        entry_zone=entry,
        exit_zone=entry,
        visit_order=visit_order,
        etapes=etapes,
        zones_a_terminer_en_premier=[entry],
        zones_a_garder_ouvertes=visit_order[1:-1],
        reprises_autorisees=["Reprise de raccordement et bouclage dans le coin épais de fermeture"],
        journal=journal,
    )


# ---------------------------------------------------------------------------
# 5. Fourche (1 tronc -> 2 branches)
# ---------------------------------------------------------------------------


def _plan_fourche(zones: dict, adj: dict, entry_pref: Any, exit_pref: Any) -> IntentionCirculation:
    # Identifier le carrefour/pivot (degré 3)
    pivot = None
    for zid, voisins in adj.items():
        if len(voisins) == 3:
            pivot = zid
            break

    branches = list(adj.get(pivot, [])) if pivot is not None else list(zones.keys())[:3]
    tronc = entry_pref if entry_pref in branches else branches[0]
    branches_restantes = [b for b in branches if b != tronc]
    b1 = branches_restantes[0] if branches_restantes else tronc
    b2 = branches_restantes[1] if len(branches_restantes) > 1 else b1

    # Ordre métier brodeur : Tronc -> Pivot -> Branche 1 (aller-retour résorbé) -> Branche 2 (sortie)
    visit_order = [tronc, pivot, b1, pivot, b2] if pivot else [tronc, b1, b2]

    journal = [
        "Structure détectée = Fourche (bifurcation 1 vers 2 branches)",
        f"Entrée choisie = Zone {tronc} (base du tronc commun)",
        f"Pivot de distribution = Zone {pivot} (cœur épais de la fourche)",
        f"Branche 1 = Zone {b1} traitée en priorité comme une impasse (résorbée en aller-retour)",
        f"Cœur de la fourche {pivot} maintenu ouvert pour basculer vers la branche 2",
        f"Sortie choisie = Zone {b2} (seconde branche d'évacuation terminale)",
        "Reprise autorisée au cœur épais de la fourche pour relier la branche 1 à la branche 2",
    ]

    etapes = [
        EtapeCirculation(
            zone_id=tronc,
            nom=f"Tronc ({tronc})",
            role="entree",
            action="amorcer_vers_noeud",
            reprise_autorisee=False,
            instruction="Avancer sur le tronc jusqu'au cœur de la fourche",
        ),
        EtapeCirculation(
            zone_id=b1,
            nom=f"Branche 1 ({b1})",
            role="cul_de_sac_aller_retour",
            action="resorber_impasse",
            reprise_autorisee=True,
            motif_reprise="Aller sous matière vers le fond puis remplissage de retour vers le cœur",
            instruction="Éteindre complètement la branche 1 avant de franchir la branche 2",
        ),
        EtapeCirculation(
            zone_id=pivot,
            nom=f"Cœur ({pivot})",
            role="consolidation_noeud",
            action="basculer_branche",
            reprise_autorisee=True,
            motif_reprise="Reprise sous le nœud triangulaire épais",
            instruction="Franchir le pivot de distribution vers la branche de sortie",
        ),
        EtapeCirculation(
            zone_id=b2,
            nom=f"Branche 2 ({b2})",
            role="sortie",
            action="terminer",
            reprise_autorisee=False,
            instruction="Remplissage vers l'extrémité terminale pour évacuer définitivement",
        ),
    ]

    return IntentionCirculation(
        structure="fourche",
        entry_zone=tronc,
        exit_zone=b2,
        visit_order=visit_order,
        etapes=etapes,
        zones_a_terminer_en_premier=[b1],
        zones_a_garder_ouvertes=[pivot, b2],
        reprises_autorisees=["Reprise sous-jacente au cœur triangulaire de la fourche"],
        journal=journal,
    )


# ---------------------------------------------------------------------------
# 6. Carrefour (Croisement en T ou en X)
# ---------------------------------------------------------------------------


def _plan_carrefour(zones: dict, adj: dict, entry_pref: Any, exit_pref: Any) -> IntentionCirculation:
    # Trouver le nœud central
    centre = None
    for zid, voisins in adj.items():
        if len(voisins) >= 4 or (len(voisins) == 3 and len(zones) >= 4):
            centre = zid
            break

    voisins = list(adj.get(centre, [])) if centre is not None else list(zones.keys())
    bras_entree = entry_pref if entry_pref in voisins else (voisins[0] if voisins else 1)
    bras_sortie = exit_pref if exit_pref in voisins and exit_pref != bras_entree else (voisins[-1] if len(voisins) > 1 else bras_entree)
    bras_lateraux = [b for b in voisins if b not in (bras_entree, bras_sortie)]

    # Ordre métier brodeur : Bras entrée -> Bras latéraux résorbés en aller-retour -> Centre -> Bras sortie
    visit_order = [bras_entree]
    for bl in bras_lateraux:
        visit_order.extend([centre, bl])
    visit_order.extend([centre, bras_sortie])

    journal = [
        "Structure détectée = Carrefour (croisement multi-voies convergeant vers un centre)",
        f"Entrée choisie = Zone {bras_entree} (bras d'accès)",
        f"Bras latéraux {bras_lateraux} traités comme des culs-de-sac avant la fermeture du centre",
        f"Centre du carrefour {centre} consolidé en dernier pour coiffer tous les départs de branches",
        f"Sortie choisie = Zone {bras_sortie} (bras d'évacuation finale)",
        "Reprises croisées permises au cœur épais du carrefour sous la couche de couverture",
    ]

    etapes = [
        EtapeCirculation(
            zone_id=bras_entree,
            nom=f"Bras entrée ({bras_entree})",
            role="entree",
            action="amorcer_vers_carrefour",
            instruction="Avancer vers le centre du carrefour",
        )
    ]
    for bl in bras_lateraux:
        etapes.append(
            EtapeCirculation(
                zone_id=bl,
                nom=f"Bras latéral ({bl})",
                role="cul_de_sac_aller_retour",
                action="resorber_impasse",
                reprise_autorisee=True,
                motif_reprise="Aller sous matière vers l'extrémité puis retour vers le centre",
                instruction=f"Résorber le bras secondaire {bl} avant la consolidation centrale",
            )
        )
    etapes.append(
        EtapeCirculation(
            zone_id=centre,
            nom=f"Centre ({centre})",
            role="consolidation_noeud",
            action="consolider_centre",
            reprise_autorisee=True,
            motif_reprise="Reprise croisée au centre",
            instruction="Consolider le centre pour recouvrir les jonctions d'arêtes",
        )
    )
    etapes.append(
        EtapeCirculation(
            zone_id=bras_sortie,
            nom=f"Bras sortie ({bras_sortie})",
            role="sortie",
            action="terminer",
            instruction="Évacuation définitive vers l'extrémité du bras de sortie",
        )
    )

    return IntentionCirculation(
        structure="carrefour",
        entry_zone=bras_entree,
        exit_zone=bras_sortie,
        visit_order=visit_order,
        etapes=etapes,
        zones_a_terminer_en_premier=bras_lateraux,
        zones_a_garder_ouvertes=[centre, bras_sortie],
        reprises_autorisees=["Reprises croisées sous-jacentes autorisées au centre du carrefour"],
        journal=journal,
    )


# ---------------------------------------------------------------------------
# 7. Arborescence (Dorsale et ramifications)
# ---------------------------------------------------------------------------


def _plan_arborescence(zones: dict, adj: dict, entry_pref: Any, exit_pref: Any) -> IntentionCirculation:
    degres = {zid: len(voisins) for zid, voisins in adj.items()}
    terminaux = [zid for zid, deg in degres.items() if deg <= 1]

    entry = entry_pref if entry_pref in zones else (terminaux[0] if terminaux else list(zones.keys())[0])
    exit_zone = exit_pref if exit_pref in zones and exit_pref != entry else (terminaux[-1] if len(terminaux) > 1 else entry)

    # Principe du balai de fond : visite en profondeur éteignant systématiquement les rameaux
    visites = set()
    visit_order = []

    def dfs(nœud: Any):
        visites.add(nœud)
        visit_order.append(nœud)
        voisins = [v for v in adj.get(nœud, []) if v not in visites]
        # Traiter d'abord les culs-de-sac (degré 1)
        voisins.sort(key=lambda v: (0 if degres.get(v, 0) <= 1 else 1, v == exit_zone))
        for v in voisins:
            if v not in visites:
                dfs(v)
                if v != exit_zone and nœud not in (visit_order[-1], exit_zone):
                    visit_order.append(nœud)

    dfs(entry)

    rameaux_secondaires = [t for t in terminaux if t not in (entry, exit_zone)]
    journal = [
        "Structure détectée = Arborescence (dorsale distribuant plusieurs rameaux)",
        f"Entrée choisie = Zone {entry} (rameau le plus profond)",
        "Application de la règle du balai de fond : liquidation immédiate de chaque rameau avant d'avancer",
        f"Rameaux secondaires {rameaux_secondaires} éteints au fur et à mesure",
        f"Sortie choisie = Zone {exit_zone} (extrémité aval de la dorsale)",
        "Reprises sous la dorsale principale vierge admises pour aller chercher la tête d'un rameau",
    ]

    etapes = [
        EtapeCirculation(
            zone_id=entry,
            nom=f"Entrée ({entry})",
            role="entree",
            action="amorcer_balai_de_fond",
            instruction="Commencer par l'impasse la plus profonde",
        )
    ]
    for zid in visit_order[1:-1]:
        role = "cul_de_sac_aller_retour" if degres.get(zid, 0) <= 1 else "transit_dorsale"
        etapes.append(
            EtapeCirculation(
                zone_id=zid,
                nom=f"Zone {zid}",
                role=role,
                action="resorber_impasse" if role == "cul_de_sac_aller_retour" else "avancer_dorsale",
                reprise_autorisee=True,
                instruction="Liquider le rameau avant de continuer sur la dorsale",
            )
        )
    etapes.append(
        EtapeCirculation(
            zone_id=exit_zone,
            nom=f"Sortie ({exit_zone})",
            role="sortie",
            action="terminer",
            instruction="Terminer sur l'extrémité aval de la dorsale",
        )
    )

    return IntentionCirculation(
        structure="arborescence",
        entry_zone=entry,
        exit_zone=exit_zone,
        visit_order=visit_order,
        etapes=etapes,
        zones_a_terminer_en_premier=rameaux_secondaires or [entry],
        zones_a_garder_ouvertes=[exit_zone],
        reprises_autorisees=["Reprises de transfert sous la dorsale principale"],
        journal=journal,
    )


# ---------------------------------------------------------------------------
# Repli : chaîne générique
# ---------------------------------------------------------------------------


def _plan_chaine_generique(zones: dict, adj: dict, entry_pref: Any, exit_pref: Any) -> IntentionCirculation:
    liste = list(zones.keys())
    entry = entry_pref if entry_pref in zones else (liste[0] if liste else 1)
    exit_zone = exit_pref if exit_pref in zones else (liste[-1] if liste else entry)
    visit_order = liste or [entry]

    return IntentionCirculation(
        structure="corridor",
        entry_zone=entry,
        exit_zone=exit_zone,
        visit_order=visit_order,
        etapes=[EtapeCirculation(zone_id=z, nom=f"Zone {z}", role="transit", action="traverser") for z in visit_order],
        zones_a_terminer_en_premier=[entry],
        zones_a_garder_ouvertes=[exit_zone],
        reprises_autorisees=["Reprise linéaire sous-jacente vers l'avant"],
        journal=[
            "Structure détectée = Chaîne générique",
            f"Entrée choisie = Zone {entry}",
            f"Sortie choisie = Zone {exit_zone}",
            "Parcours linéaire séquentiel",
        ],
    )
