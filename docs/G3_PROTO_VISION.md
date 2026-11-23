# G3_PROTO_VISION — premiers yeux du moteur

Étape **G3**, phase de construction. Prototype de **perception seule**.
Aucune couture, aucune rangée, aucun ordre, aucun export.

Références : `docs/ARCHITECTURE_FONDATRICE.md`,
`docs/BRODEUR_VISION_MODEL.md`, `docs/G2_CARTE_CONCEPTUELLE.md`.
Contraintes : ne touche ni `fill.py`, ni `planning.py`, ni `engine.py`.

Version : plan expérimental du 2026-11-19. À valider avant écriture du code.

---

## Objectif

Donner au logiciel les **premiers yeux** du brodeur : savoir, avant toute
décision de couture, ce que la forme contient comme salles, passages et
impasses.

Le prototype répond à une seule question : **« qu'est-ce que je vois ? »**
Il ne répond jamais à « comment je couds ? ».

Trois propriétés non négociables :

1. **Aucune sortie de couture** : pas un point, pas une rangée, pas un ordre.
2. **Dépendance zéro** : le prototype n'importe rien de `fill.py`,
   `planning.py`, `engine.py` ni `objects.py` au-delà du contour brut.
3. **Explicable** : chaque zone, chaque passage et chaque impasse doit pouvoir
   être justifié par une mesure géométrique nommée.

---

## Entrées

| Entrée | Forme | Obligatoire | Remarque |
|---|---|---|---|
| `contour` | polyligne fermée de points (x, y) | oui | sens quelconque ; fermeture implicite |
| `trous` | liste de polylignes fermées | non (défaut : vide) | toute polyligne incluse dans le contour |
| `unite` | mm | implicite | convention du projet |

Ce que le prototype **ne prend pas** en entrée, volontairement : écart de
remplissage, longueur de point, angle, couleur, machine, départ, arrivée.
La perception ne doit pas dépendre des paramètres de couture — à une exception
près, explicitement consignée : la **largeur utile d'un couloir**, qui dépendra
plus tard de l'écart de couture. Le prototype mesure la largeur **géométrique**
et laisse ce rapprochement à une étape ultérieure.

---

## Sorties

| Sortie | Contenu |
|---|---|
| `vides` | les trous reconnus, avec leur surface et leur position |
| `zones` | chaque zone : numéro, surface, largeur caractéristique, point de plus grand dégagement, appartenance éventuelle à un vide |
| `passages` | chaque passage : les deux zones reliées, le segment de col (ses deux extrémités sur le bord), sa largeur minimale, sa position |
| `zones_terminales` | zones à un seul passage (ou aucune) |
| `zones_de_transition` | zones traversées, à deux passages ou plus, de forme allongée |
| `culs_de_sac` | zones terminales **dont la largeur décroît** vers le fond |
| `adjacences` | le graphe zone ↔ passage ↔ zone |
| `depart_candidats` | points d'entrée possibles, situés dans les zones terminales, avec leur dégagement |
| `sortie_candidats` | points de sortie possibles, même règle |
| `structures` | lectures remarquables : `Anneau` (une zone autour d'un vide) ou `Pont` (deux zones terminales + une zone de transition) |
| `journal` | la trace lisible de chaque décision géométrique (quelle mesure a créé quelle zone) |

Aucune sortie ne contient de point de broderie.

---

## Concepts détectés

Correspondance directe avec le vocabulaire fondateur :

| Concept fondateur | Ce que le prototype produit |
|---|---|
| Vide | un trou fermé, jamais franchi |
| Zone | une région connexe de matière, séparée des autres par des cols |
| Passage | un col : segment intérieur minimal entre deux points du bord |
| Couloir | la largeur du col et son axe (largeur géométrique seulement) |
| Zone terminale | zone de degré 1 dans le graphe d'adjacence |
| Cul-de-sac | zone terminale dont le profil de largeur décroît vers le fond |
| Zone de transition | zone de degré ≥ 2 et allongée (longueur / largeur élevé) |
| Coin | zone de forte épaisseur à la jonction de deux passages |
| Anneau | zone unique à un vide, sans passage |
| Pont | deux zones terminales reliées par une zone de transition |
| Départ / Sortie candidats | points de dégagement maximal dans les zones terminales |

---

## Architecture minimale

Quatre responsabilités séparées, aucune ne connaissant la couture :

1. **Géométrie pure** — polylignes, appartenance d'un point, distance d'un
   point au bord, aire. Aucune notion de broderie.
2. **Carte de dégagement** — pour chaque point intérieur, la distance au bord
   le plus proche. C'est la mesure fondamentale : elle dit « où il y a de la
   place » et « où la matière s'étrangle ».
3. **Perception** — lit la carte de dégagement, en extrait les cols, coupe la
   matière le long des cols, et nomme les zones obtenues. C'est le seul module
   qui produit le vocabulaire métier.
4. **Rapport** — rend le résultat lisible (texte, et plus tard un aperçu
   graphique). Aucune décision, uniquement de la restitution.

Le prototype vit **hors du moteur** : `prototypes/g3_vision/`, avec ses tests
séparés. Il ne sera branché nulle part tant qu'il n'est pas validé.

---

## Jeux de test

| Forme | Zones attendues | Passages | Terminales | Culs-de-sac | Structures |
|---|---|---|---|---|---|
| Rectangle 20 × 20 | **1** | **0** | 1 (le bloc entier) | 0 | — |
| U 20 × 20 (jambes 6 mm) | **3** (jambe G, traverse, jambe D) | **2** | **2** (les jambes) | 0 — largeur constante | — |
| Trou 40 × 40, trou 16 × 16 | **1** (anneau) | **0** | 0 | 0 | **Anneau** |
| Concave 30 × 10 | **2** (ailes) | **1** (col de base, ~5 mm) | **2** | **2** (les ailes s'affinent) | — |
| Arche 429,5 × 141,1 | **3** (culée G, voûte, culée D) | **2** (les épaules) | **2** (les culées) | **2** si la largeur décroît ; sinon 0 | **Pont** |

Point de vigilance consigné : G0 appelait « culs-de-sac » les deux jambes du U.
La définition fondatrice a été resserrée : cul-de-sac = zone terminale **qui
s'affine**. Les jambes du U, de largeur constante, sont donc **terminales sans
être des culs-de-sac**. Le prototype appliquera la définition fondatrice — c'est
elle qui fait foi — et le tableau ci-dessus l'assume explicitement.

---

## Critères de réussite

Le prototype est accepté si, sur les cinq formes :

1. le **nombre de zones** est exact pour les cinq formes ;
2. le **nombre de passages** est exact, et chaque passage relie les bonnes
   zones dans le graphe d'adjacence ;
3. les **zones terminales** et les **culs-de-sac** sont distingués selon la
   définition fondatrice (le U doit produire 2 terminales et 0 cul-de-sac) ;
4. l'**Anneau** et le **Pont** sont reconnus ;
5. les **candidats départ/sortie** tombent dans les zones terminales, à une
   distance du bord supérieure à la demi-largeur locale ;
6. **aucune sortie de couture** n'existe dans le résultat (vérifiable : aucune
   structure produite n'a de coordonnées de point de couture, aucun ordre) ;
7. le prototype **n'importe rien** du moteur (vérifiable par les imports) ;
8. le temps de perception de l'arche reste **inférieur à 100 ms** ;
9. le résultat est **stable** : une même forme tournée de 90° ou translatée
   donne les mêmes nombres de zones, passages et terminales ;
10. chaque décision du journal est **justifiée par une mesure** (largeur, aire,
    distance), jamais par un seuil magique non documenté.

## Critères d'échec

1. Un seul point de couture apparaît dans la sortie.
2. Le prototype importe `fill`, `planning`, `engine` ou un exporteur.
3. Un nombre de zones ou de passages est faux sur une des cinq formes.
4. Les seuils de détection (col, affinement) ne sont pas explicites et
   paramétrables.
5. Le prototype produit un ordre de visite.
6. Le temps dépasse 100 ms sur l'arche.

---

## Risques

| Risque | Gravité | Réduction |
|---|---|---|
| L'axe médian est instable : une micro-oscillation du bord crée une zone fantôme | **élevée** | élaguer les branches sous une échelle minimale explicite (par exemple 2 mm) et le documenter |
| Seuil de col arbitraire : « étroit » n'est pas absolu | **élevée** | exprimer le seuil en **ratio** largeur / largeur locale du voisinage, et le tester sur les cinq formes |
| Sur-apprentissage des cinq formes | moyenne | ajouter deux formes de contrôle (croissant, L) dont le résultat est prévisible |
| Confusion terminale / cul-de-sac | moyenne | test explicite sur le U (2 terminales, 0 cul-de-sac) |
| Mélange perception / couture | moyenne | interdiction d'import du moteur, vérifiée par test |
| Le prototype devient un second planificateur | **élevée** | aucune notion de rangée, d'ordre ou de point ; revue de code dédiée |
| Coût de la carte de dégagement sur l'arche | faible | mesure explicite, plafond 100 ms |

---

## Prototype V1

Périmètre strict, volontairement minimal :

- **entrée** : contour + trous, aucune autre donnée ;
- **sortie** : les objets du § Sorties, sans un seul point de couture ;
- **méthode** : carte de dégagement, cols détectés comme minima locaux de
  largeur, découpe de la matière le long des cols, nommage des zones d'après
  le graphe d'adjacence, profils de largeur pour distinguer terminale et
  cul-de-sac ;
- **livrables** : un module de géométrie, un module de perception, un rapport,
  et un fichier de tests couvrant les cinq formes plus deux formes de contrôle ;
- **hors périmètre** : couture, rangées, ordre, export, interface, réglages
  utilisateur.

**Ce que V1 ne fera jamais** : proposer un parcours, choisir un ordre, générer
une trajectoire, remplacer `planning.py`. Il regarde la forme, il la décrit, et
il s'arrête là.
