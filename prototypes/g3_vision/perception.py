"""Perception de forme du prototype G3.

Ce module regarde et decrit. Il ne coud rien : aucun point, aucune rangee,
aucun ordre, aucun export. Il n'importe aucun module du moteur.

Methode, en clair :
1. on repere les **coins rentrants** du contour et des trous : ce sont les
   seuls endroits ou une salle peut se separer d'une autre ;
2. depuis chaque coin assez marque, on cherche la **plus courte decoupe**
   interieure possible (dans l'une des directions naturelles du coin) ;
3. ces decoupes separent la matiere en **salles** ;
4. chaque decoupe est un **passage**, dont la largeur est la longueur du col ;
5. le graphe d'adjacence donne les salles terminales, les culs-de-sac et les
   transitions ; les cycles donnent les anneaux, les chaines 1-2-1 les ponts.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

try:  # le prototype vit hors du moteur ; il n'importe que sa propre geometrie
    from prototypes.g3_vision import geometry as geo
except ImportError:  # execution directe depuis le dossier du prototype
    import geometry as geo  # type: ignore


@dataclass
class Zone:
    """Une salle de matiere : surface, degagement maximal, degre d'adjacence."""

    identifiant: int
    cellules: int = 0
    surface: float = 0.0
    degagement_max: float = 0.0
    centre: tuple = (0.0, 0.0)
    passages: list = field(default_factory=list)
    degre: int = 0
    classe: str = "zone"

    @property
    def largeur_caracteristique(self):
        return 2.0 * self.degagement_max


@dataclass
class Passage:
    """Un col entre deux salles, avec sa largeur mesuree (longueur du col)."""

    zone_a: int
    zone_b: int
    largeur: float
    position: tuple
    origine: tuple = (0.0, 0.0)
    axe: tuple = (1.0, 0.0)
    cellules: int = 0


@dataclass
class Perception:
    """Tout ce que le prototype voit sur une forme. Aucune sortie de couture."""

    zones: list = field(default_factory=list)
    passages: list = field(default_factory=list)
    structures: list = field(default_factory=list)
    depart_candidats: list = field(default_factory=list)
    sortie_candidats: list = field(default_factory=list)
    journal: list = field(default_factory=list)
    cellules_matiere: int = 0
    pas_grille: float = 0.0
    duree: float = 0.0
    coins: list = field(default_factory=list)

    def zone(self, identifiant):
        for zone in self.zones:
            if zone.identifiant == identifiant:
                return zone
        raise KeyError(identifiant)

    @property
    def zones_terminales(self):
        return [zone for zone in self.zones if zone.classe in ("terminale", "cul-de-sac")]

    @property
    def culs_de_sac(self):
        return [zone for zone in self.zones if zone.classe == "cul-de-sac"]

    @property
    def zones_de_transition(self):
        return [zone for zone in self.zones if zone.classe == "transition"]


def perceive(outer, holes=(), cell=None, angle_min=20.0, coupe_min=1.0):
    """Percoit la forme : zones, passages, structures, candidats. Rien d'autre."""
    depart = __import__("time").perf_counter()
    carte = geo.ClearanceMap(outer, holes, cell=cell)
    journal = [
        "grille : {} x {} cellules de {:.2f} mm".format(
            carte.nx, carte.ny, carte.cell),
        "matiere : {} cellules".format(sum(carte.inside)),
    ]

    coins = _coins_rentrants(outer, holes, angle_min)
    journal.append("coins rentrants retenus (>= {:.0f} deg) : {}".format(
        angle_min, len(coins)))

    coupes = _coupes(carte, coins, coupe_min)
    journal.append("decoupes interieures : {}".format(len(coupes)))
    for coupe in coupes:
        journal.append("  col ({:.1f};{:.1f}) -> ({:.1f};{:.1f}) : {:.2f} mm"
                       .format(coupe["a"][0], coupe["a"][1],
                               coupe["b"][0], coupe["b"][1], coupe["largeur"]))

    etiquettes = _etiqueter(carte, coupes)
    zones = _zones(carte, etiquettes, journal)
    passages = _passages(carte, etiquettes, coupes, zones, journal)
    _classer(zones, passages, journal)
    structures = _structures(zones, passages, holes, journal)
    candidats = _candidats(carte, etiquettes, zones)

    duree = __import__("time").perf_counter() - depart
    journal.append("duree de perception : {:.0f} ms".format(duree * 1000.0))
    return Perception(zones=zones, passages=passages, structures=structures,
                      depart_candidats=candidats,
                      sortie_candidats=list(reversed(candidats)),
                      journal=journal, cellules_matiere=sum(carte.inside),
                      pas_grille=carte.cell, duree=duree, coins=coins)


# ---------------------------------------------------------------------------
# Coins
# ---------------------------------------------------------------------------


def _orientation(polygon):
    total = 0.0
    for (x1, y1), (x2, y2) in zip(polygon, polygon[1:]):
        total += x1 * y2 - x2 * y1
    return 1.0 if total > 0 else -1.0


def _coins_rentrants(outer, holes, angle_min):
    """Coins dont l'angle interieur depasse 180 degres d'au moins ``angle_min``.

    Pour un trou, la matiere est a l'exterieur du polygone : le sens est
    inverse, sinon les coins rentrants du trou ne seraient jamais vus.
    """
    coins = []
    polygones = [(geo.closed(outer), 1.0)]
    polygones.extend((geo.closed(hole), -1.0) for hole in holes)
    for indice, (polygon, sens_matiere) in enumerate(polygones):
        sens = _orientation(polygon) * sens_matiere
        points = polygon[:-1]
        nombre = len(points)
        for position in range(nombre):
            precedent = points[position - 1]
            courant = points[position]
            suivant = points[(position + 1) % nombre]
            vx1, vy1 = courant[0] - precedent[0], courant[1] - precedent[1]
            vx2, vy2 = suivant[0] - courant[0], suivant[1] - courant[1]
            if math.hypot(vx1, vy1) < 1e-9 or math.hypot(vx2, vy2) < 1e-9:
                continue
            cross = vx1 * vy2 - vy1 * vx2
            rentrant = cross * sens < 0
            if not rentrant:
                continue
            angle = math.degrees(math.atan2(abs(cross),
                                            vx1 * vx2 + vy1 * vy2))
            if angle < angle_min:
                continue
            coins.append({
                "point": (float(courant[0]), float(courant[1])),
                "precedent": (float(precedent[0]), float(precedent[1])),
                "suivant": (float(suivant[0]), float(suivant[1])),
                "angle": angle,
                "polygone": indice,
            })
    return coins


def _directions(coin):
    """Directions naturelles d'une decoupe.

    Deux prolongements d'arete (la decoupe continue la ligne du col) et la
    bissectrice de l'angle interieur. La plus courte decoupe valide sera
    retenue : c'est le col le plus franc.
    """
    px, py = coin["point"]
    ax, ay = coin["precedent"]
    bx, by = coin["suivant"]
    directions = []
    for (vx, vy) in ((px - ax, py - ay), (px - bx, py - by)):
        longueur = math.hypot(vx, vy)
        if longueur > 1e-9:
            directions.append((vx / longueur, vy / longueur))
    ux = (px - ax) / max(math.hypot(px - ax, py - ay), 1e-9) + \
         (px - bx) / max(math.hypot(px - bx, py - by), 1e-9)
    uy = (py - ay) / max(math.hypot(px - ax, py - ay), 1e-9) + \
         (py - by) / max(math.hypot(px - bx, py - by), 1e-9)
    norme = math.hypot(ux, uy)
    if norme > 1e-9:
        directions.append((ux / norme, uy / norme))
    return directions


def _coupes(carte, coins, coupe_min):
    """Pour chaque coin, la plus courte decoupe interieure qui atteint le bord.

    Une decoupe n'est retenue que si elle est plus courte que **chacune des
    deux parois** qui la bordent : un col plus long que ses propres murs n'est
    pas un col, c'est une tranche arbitraire. C'est ce critere qui laisse
    l'arche entiere (bande continue) et separe les ailes de la forme concave.
    """
    coupes = []
    pas = max(carte.cell * 0.5, 0.2)
    for coin in coins:
        px, py = coin["point"]
        ax, ay = coin["precedent"]
        bx, by = coin["suivant"]
        paroi = min(math.hypot(px - ax, py - ay), math.hypot(px - bx, py - by))
        meilleure = None
        for direction in _directions(coin):
            longueur = _longueur_jusqu_au_bord(carte, (px, py), direction, pas)
            if longueur is None or longueur < coupe_min:
                continue
            if meilleure is None or longueur < meilleure[0]:
                meilleure = (longueur, direction)
        if meilleure is None:
            continue
        longueur, direction = meilleure
        if longueur > paroi:
            continue
        coupes.append({
            "a": (px, py),
            "b": (px + direction[0] * longueur, py + direction[1] * longueur),
            "largeur": longueur,
            "coin": coin,
        })
    return coupes


def _longueur_jusqu_au_bord(carte, point, direction, pas):
    """Marche dans la matiere jusqu'a en sortir ; rend la longueur parcourue.

    L'appartenance est lue sur la grille (et non sur le polygone) : une decoupe
    qui longe une arete horizontale reste ainsi mesurable, alors qu'un test
    point-dans-polygone exact y devient ambigu.
    """
    x, y = point
    x += direction[0] * pas
    y += direction[1] * pas
    parcouru = pas
    ix, iy = carte.xy_to_cell(x, y)
    if not carte.inside[carte.index(ix, iy)]:
        return None
    limite = 4.0 * max(carte.xmax - carte.xmin, carte.ymax - carte.ymin)
    while parcouru < limite:
        ix, iy = carte.xy_to_cell(x, y)
        if not carte.inside[carte.index(ix, iy)]:
            return parcouru
        x += direction[0] * pas
        y += direction[1] * pas
        parcouru += pas
    return None


# ---------------------------------------------------------------------------
# Zones et passages
# ---------------------------------------------------------------------------


def _cellules_coupees(carte, coupes):
    coupees = set()
    for coupe in coupes:
        ax, ay = coupe["a"]
        bx, by = coupe["b"]
        longueur = math.hypot(bx - ax, by - ay)
        etapes = max(1, int(math.ceil(longueur / (carte.cell * 0.4))))
        for index in range(etapes + 1):
            t = index / etapes
            x = ax + (bx - ax) * t
            y = ay + (by - ay) * t
            ix, iy = carte.xy_to_cell(x, y)
            coupees.add(carte.index(ix, iy))
    return coupees


def _etiqueter(carte, coupes):
    """Etiquette chaque cellule de matiere : 0 = coupee, sinon numero de salle.

    Voisinage a quatre voisins : une decoupe d'une cellule d'epaisseur ne doit
    pas pouvoir etre franchie en diagonale.
    """
    interdites = _cellules_coupees(carte, coupes)
    etiquettes = [0] * (carte.nx * carte.ny)
    numero = 0
    for iy in range(carte.ny):
        for ix in range(carte.nx):
            depart = carte.index(ix, iy)
            if not carte.inside[depart] or etiquettes[depart] or depart in interdites:
                continue
            numero += 1
            etiquettes[depart] = numero
            pile = [(ix, iy)]
            while pile:
                cx, cy = pile.pop()
                for jx, jy in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if not (0 <= jx < carte.nx and 0 <= jy < carte.ny):
                        continue
                    voisin = carte.index(jx, jy)
                    if (not carte.inside[voisin] or etiquettes[voisin]
                            or voisin in interdites):
                        continue
                    etiquettes[voisin] = numero
                    pile.append((jx, jy))
    return etiquettes


def _zones(carte, etiquettes, journal):
    compteurs = {}
    maxima = {}
    sommes = {}
    for iy in range(carte.ny):
        for ix in range(carte.nx):
            position = carte.index(ix, iy)
            etiquette = etiquettes[position]
            if not etiquette:
                continue
            compteurs[etiquette] = compteurs.get(etiquette, 0) + 1
            maxima[etiquette] = max(maxima.get(etiquette, 0.0),
                                    carte.clearance[position])
            x, y = carte.center(ix, iy)
            sx, sy = sommes.get(etiquette, (0.0, 0.0))
            sommes[etiquette] = (sx + x, sy + y)
    zones = []
    for etiquette in sorted(compteurs):
        nombre = compteurs[etiquette]
        sx, sy = sommes[etiquette]
        zones.append(Zone(identifiant=etiquette,
                          cellules=nombre,
                          surface=nombre * carte.cell * carte.cell,
                          degagement_max=maxima[etiquette],
                          centre=(sx / nombre, sy / nombre)))
    journal.append("salles detectees : {}".format(len(zones)))
    return zones


def _passages(carte, etiquettes, coupes, zones, journal):
    indexez = {zone.identifiant: zone for zone in zones}
    passages = []
    for coupe in coupes:
        ax, ay = coupe["a"]
        bx, by = coupe["b"]
        milieu = ((ax + bx) / 2.0, (ay + by) / 2.0)
        voisines = set()
        pas = max(carte.cell * 0.5, 0.2)
        longueur = max(math.hypot(bx - ax, by - ay), 1e-9)
        ux, uy = (bx - ax) / longueur, (by - ay) / longueur
        for index in range(int(longueur / pas) + 1):
            t = min(1.0, index * pas / longueur)
            x = ax + (bx - ax) * t
            y = ay + (by - ay) * t
            for cote in (-1.0, 1.0):
                ox = x - uy * cote * carte.cell * 1.5
                oy = y + ux * cote * carte.cell * 1.5
                ix, iy = carte.xy_to_cell(ox, oy)
                etiquette = etiquettes[carte.index(ix, iy)]
                if etiquette:
                    voisines.add(etiquette)
        voisines = sorted(voisines)
        if len(voisines) < 2:
            continue
        a, b = voisines[0], voisines[1]
        axe = (ux, uy)
        if axe[0] < 0 or (abs(axe[0]) < 1e-9 and axe[1] < 0):
            axe = (-axe[0], -axe[1])
        passage = Passage(zone_a=a, zone_b=b, largeur=longueur,
                          position=milieu, origine=coupe["a"], axe=axe,
                          cellules=int(math.ceil(longueur / carte.cell)))
        passages.append(passage)
        indexez[a].passages.append(passage)
        indexez[b].passages.append(passage)
    for zone in zones:
        zone.degre = len({passage.zone_b if passage.zone_a == zone.identifiant
                          else passage.zone_a
                          for passage in zone.passages})
    journal.append("passages : {}".format(len(passages)))
    return passages


def _classer(zones, passages, journal):
    """Terminale, cul-de-sac, transition : trois lectures, jamais un ordre."""
    for zone in zones:
        if zone.degre == 0:
            zone.classe = "isolee"
            journal.append("zone {} : aucune adjacence -> isolee".format(zone.identifiant))
            continue
        if zone.degre == 1:
            entree = zone.passages[0].largeur / 2.0
            if zone.degagement_max < entree * 0.9:
                zone.classe = "cul-de-sac"
            else:
                zone.classe = "terminale"
        else:
            zone.classe = "transition"
        journal.append("zone {} : degre {} -> {}".format(
            zone.identifiant, zone.degre, zone.classe))


def _structures(zones, passages, holes, journal):
    structures = []
    if not zones:
        return structures
    degres = sorted(zone.degre for zone in zones)
    if len(zones) >= 3 and all(degre == 2 for degre in degres) \
            and len(passages) == len(zones):
        structures.append("Anneau")
        journal.append("structure : Anneau ({} salles en cycle autour d'un vide)"
                       .format(len(zones)))
    if len(zones) == 3 and len(passages) == 2 and degres == [1, 1, 2]:
        milieu = [zone for zone in zones if zone.degre == 2][0]
        if len(milieu.passages) == 2:
            premier, second = milieu.passages
            angle = math.degrees(math.acos(max(-1.0, min(1.0,
                premier.axe[0] * second.axe[0] + premier.axe[1] * second.axe[1]))))
            normale = (-premier.axe[1], premier.axe[0])
            decalage = abs((second.position[0] - premier.position[0]) * normale[0]
                           + (second.position[1] - premier.position[1]) * normale[1])
            reference = 0.5 * max(premier.largeur, second.largeur)
            if angle > 25.0 or decalage > reference:
                structures.append("Pont")
                journal.append(
                    "structure : Pont (deux extremites reliees par une transition ; "
                    "ecart des cols {:.1f} mm, angle {:.0f} deg)"
                    .format(decalage, angle))
            else:
                journal.append(
                    "structure : pas de pont (cols dans le prolongement : "
                    "ecart {:.1f} mm, angle {:.0f} deg)".format(decalage, angle))
    if len(zones) == 1 and holes:
        structures.append("Anneau")
        journal.append("structure : Anneau (une seule salle autour d'un vide)")
    return structures


def _candidats(carte, etiquettes, zones):
    """Points les plus degages des salles terminales : entrees/sorties possibles."""
    meilleurs = {}
    for iy in range(carte.ny):
        for ix in range(carte.nx):
            position = carte.index(ix, iy)
            etiquette = etiquettes[position]
            if not etiquette:
                continue
            valeur = carte.clearance[position]
            if valeur > meilleurs.get(etiquette, (-1.0, (0.0, 0.0)))[0]:
                meilleurs[etiquette] = (valeur, carte.center(ix, iy))
    candidats = []
    for zone in zones:
        if zone.degre > 1:
            continue
        valeur, point = meilleurs.get(zone.identifiant, (0.0, (0.0, 0.0)))
        zone.centre = point
        candidats.append((zone.identifiant, point, valeur))
    candidats.sort(key=lambda item: -item[2])
    return candidats
