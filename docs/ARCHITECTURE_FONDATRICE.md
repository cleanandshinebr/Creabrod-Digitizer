# ARCHITECTURE FONDATRICE — CRÉABROD DIGITIZER

Document fondateur officiel. Il consolide `G0_RAPPORT`,
`docs/BRODEUR_VISION_MODEL.md` et `docs/G2_CARTE_CONCEPTUELLE.md` en un seul
texte de référence métier.

**Règle de suprématie.** Ce document et les trois textes qu'il consolide
décrivent le raisonnement métier de référence. Le code doit s'y adapter. Aucun
de ces documents ne doit être modifié pour justifier le comportement actuel du
code : un écart entre le code et le document est un défaut du code, jamais un
défaut du document.

Version : 1 — 2026-11-17.

---

# Vision du Brodeur

Le brodeur ne voit pas des rangées. Il voit un **territoire** : des salles de
matière, des couloirs qui les relient, des culs-de-sac qui ne pardonnent pas, et
un fil qui doit pouvoir ressortir de partout.

Quatre principes résument sa vision :

1. **Il choisit ses extrémités avant de coudre.** Le départ et l'arrivée sont des
   décisions de composition, prises sur les zones terminales, jamais des
   accidents de parcours.
2. **Il protège les accès, pas les rangées.** Ce qu'il surveille est la
   possibilité d'entrer encore dans une partie de la forme, pas la propreté
   d'une ligne déjà posée.
3. **Il répare au lieu de s'arrêter.** Si une zone se ferme, il coud une ligne
   simple sous le remplissage jusqu'à un point de reprise, et il continue. Le
   geste est prévu, borné, et jugé sur ce qui le recouvrira.
4. **Il termine toujours la forme.** Une impasse géométrique peut exister ; une
   impasse de parcours, non.

Conséquence directe : le brodeur ne cherche pas le parcours parfait, il cherche
un parcours **réparable**. Toute architecture qui interdit la réparation puis
déclare l'impasse définitive est étrangère à ce raisonnement.

---

# Concepts Métier Officiels

Liste consolidée, validée, et **close** : un concept absent de cette liste n'a
pas de statut officiel. Les ajouts passent par une révision de ce document.

## A. Géométrie — ce qui est donné

| Concept | Définition officielle |
|---|---|
| **Forme** | La figure complète à broder : matière et vides. |
| **Silhouette** | La limite extérieure de la matière. |
| **Vides** | Trous intérieurs et échancrures ouvertes : jamais franchis par une couture. |
| **Matière** | Ce qui reste quand les vides sont retirés. |
| **Dimensions / Orientation** | Encombrement, axe long, inclinaison ; servent à choisir l'angle par zone. |

## B. Topologie perçue — ce qui est déduit du dessin

| Concept | Définition officielle |
|---|---|
| **Zone** | Partie continue de matière que l'on peut remplir sans franchir un vide ni une couture. Unité de décision du remplissage. |
| **Sous-zone** | Subdivision d'une grande zone qui se comporte comme une salle autonome. |
| **Adjacence** | Relation « ces deux zones se touchent par ce passage ». |
| **Passage** | Étranglement de matière reliant deux zones. N'existe que par ce qu'il relie. |
| **Couloir** | Chemin concret d'un passage ou d'une zone de transition, avec sa **largeur utile** (elle dépend de l'écart de couture, pas seulement du dessin). |
| **Coin** | Jonction de deux bandes, où la matière est épaisse : lieu privilégié du changement d'angle et de la reprise. |
| **Zone terminale** | Zone à un seul accès. Cas général. |
| **Cul-de-sac** | **Zone terminale qui s'affine** en s'éloignant de son unique passage. Cas particulier de zone terminale, pas une catégorie séparée. |
| **Zone de transition** | Zone que l'on traverse sans y demeurer, reliant deux zones terminales. |
| **Voûte** | **Zone de transition courbe et épaisse**, à coudre en continuité, sans demi-tour au sommet. Cas particulier de zone de transition. |
| **Culée** | Zone terminale massive d'un pont (l'équivalent d'une « jambe » de pont). |
| **Structure remarquable** | Assemblage reconnaissable de zones : **Anneau** (une zone autour d'un vide) ou **Pont** (deux culées + une voûte). Une structure remarquable n'est pas un contenant : c'est une **lecture** de zones existantes. |

## C. Intention — ce qui est choisi avant de coudre

| Concept | Définition officielle |
|---|---|
| **Départ** | Zone terminale ou coin où le bloc commence. |
| **Sortie** | Zone terminale ou coin où il s'achève. |
| **Ordre de visite** | Intention de parcours des zones, choisie sur le graphe des adjacences. |
| **Budget d'imperfection** | Nombre, longueur et localisation des reprises tolérées pour un bloc, fixés **avant** la première rangée. |
| **Angle par zone** | Orientation de remplissage propre à chaque zone. Une voûte et une culée n'ont pas le même axe. |

## D. Exécution — ce qui vit pendant la couture

| Concept | Définition officielle |
|---|---|
| **Position** | Lieu courant de l'aiguille. |
| **Zone courante** | Zone où se trouve l'aiguille. |
| **État d'accès** | Pour chaque zone : **ouvert**, **temporairement fermé** ou **définitivement fermé**. Trois valeurs d'un seul concept. |
| **Couverture future** | Ce qui reste à coudre et recouvrirait un trajet donné. Objet de plein droit : sans lui, aucune reprise n'est légitime. |
| **Point de reprise** | Point où l'aiguille ressort et reprend le remplissage, choisi soutenu et couvert. |
| **Couture de reprise** | Couture simple et droite rejoignant un point de reprise, jugée sur sa couverture future. |
| **Reprises effectuées** | Compteur du budget consommé. |

## E. Ce que la consolidation a corrigé

| Point | Constat dans les documents sources | Décision officielle |
|---|---|---|
| Doublon | « Zone temporairement inaccessible » et « Zone définitivement inaccessible » étaient deux concepts distincts | Ce sont **deux valeurs** de l'État d'accès |
| Doublon | « Voûte » et « Zone de transition » présentés côte à côte | La Voûte est un **cas particulier** de zone de transition |
| Doublon | « Cul-de-sac » et « Zone terminale » se recouvraient | Le Cul-de-sac est un **cas particulier** (zone terminale qui s'affine) |
| Contradiction | G2 plaçait « Ponts » comme frères des Zones dans la hiérarchie de la matière | Le Pont est une **structure remarquable**, lecture de plusieurs zones, pas un contenant |
| Manque | « Culée » employé dans G0 sans définition | Ajouté aux concepts officiels |
| Manque | « Couverture future » utilisée par G1 sans figurer dans sa liste | Ajoutée aux concepts officiels |
| Manque | « Sous-zone », « Adjacence », « Silhouette », « Vides », « Matière » présents seulement dans G2 | Ajoutés à la liste consolidée |
| Ambiguïté | « Accès » défini depuis la position courante seulement | L'accès s'évalue depuis la position courante **ou** depuis tout point de reprise disponible |
| Ambiguïté | « Couloir » présenté comme un objet autonome | Le Couloir est la **dimension utile** d'un passage ou d'une transition, pas une zone |
| Ambiguïté | G0 admettait d'entrer par la base d'une aile | La règle est de ne jamais **laisser derrière soi** un cul-de-sac, pas d'y entrer nécessairement |

---

# Règles Fondamentales

1. **Les culs-de-sac se traitent en premier** — ou, à défaut, on y entre en
   dernier pour y finir. Ce qui est étroit et terminal ne se reprend pas.
2. **Les couloirs se traversent une seule fois**, en continuité, avec l'angle
   qui convient.
3. **Une reprise doit être recouverte par une couverture future.** Une reprise
   sur une zone déjà cousue n'est pas une reprise, c'est un défaut.
4. **Un vide ne se traverse jamais** par une couture.
5. **On lit une forme en zones avant de la lire en rangées.** L'ordre des zones
   décide ; l'ordre des rangées ne fait que servir.
6. **L'accessibilité est un état surveillé, pas un invariant absolu.** On cherche
   à la conserver ; on ne s'arrête pas parce qu'on l'a perdue.
7. **Temporairement fermé n'arrête pas le travail ; définitivement fermé le
   justifie.** C'est toute la différence entre un brodeur et un logiciel bloqué.
8. **Le budget d'imperfection se fixe avant le premier point.** Décider au
   moment du problème revient à décider dans la panique.
9. **Départ et sortie se choisissent parmi les zones terminales ou les coins,
   avant tout calcul.**
10. **L'angle appartient à la zone.** Un bloc n'a pas d'angle unique.
11. **Un coin est le meilleur endroit pour réparer**, parce qu'il est épais et
    qu'il sera cousu après.
12. **La perception ne se recalcule pas pendant la couture.** Coudre ne change
    pas la forme ; cela ne change que l'état d'accès.

---

# Hiérarchie de Perception

```
Forme            « quelles sont la silhouette et les vides ? »
  ↓
Zones            « quelles salles de matière, et comment se touchent-elles ? »
  ↓
Passages         « où la matière s'étrangle-t-elle ? quelle largeur utile ? »
  ↓
Départ / Sortie  « quelles zones terminales, quels coins ? »
  ↓
Stratégie        « quel ordre de visite, quel budget d'imperfection ? »
  ↓
Remplissage      « quelles rangées, dans quelle zone, avec quel angle ? »
  ↓
Points           « quels points exacts, et quelles reprises bornées ? »
```

Cette descente est **unidirectionnelle**. Aucune décision de point, de rangée ou
de reprise ne remonte redéfinir une zone, un passage ou une zone terminale.
La remontée existe, mais elle est locale et volatile : elle ne transporte que
position, état d'accès et couverture future.

---

# Invariants de CREABROD

Principes que le futur moteur ne devra **jamais** violer.

| # | Invariant |
|---|---|
| I1 | Un vide n'est jamais franchi par une couture. |
| I2 | Une zone n'est déclarée définitivement inaccessible qu'après avoir vérifié qu'aucun passage et aucun point de reprise couvert ne la rejoint. |
| I3 | Une couture de reprise n'existe que si sa couverture future est identifiée et suffisante. |
| I4 | Un couloir n'est jamais cousu en deux passes séparées. |
| I5 | Un cul-de-sac n'est jamais laissé derrière soi sans y avoir fini. |
| I6 | L'état d'accès ne se déduit que du travail déjà fait, jamais de la géométrie seule, et ne se confond jamais avec la topologie. |
| I7 | La perception est calculée une fois par dessin ; l'exécution ne la modifie jamais. |
| I8 | Le budget d'imperfection est fixé avant la première rangée et n'est jamais dépassé silencieusement. |
| I9 | L'angle de remplissage est une propriété de la zone, jamais du bloc entier. |
| I10 | Aucune rangée n'est calculée avant que la perception n'ait répondu aux neuf questions du § Hiérarchie de Perception. |
| I11 | Toute décision de couture doit pouvoir nommer : la zone concernée, l'accès utilisé, et ce qui recouvrira le trajet. |
| I12 | Aucun document fondateur n'est modifié pour justifier le comportement du code. |

---

# Décisions Architecturales

Considérées comme **acquis** à compter de cette version.

1. **Le moteur raisonne en zones, pas en rangées.** Les rangées sont une
   conséquence de l'exécution, jamais l'unité de décision.
2. **Trois couches séparées** : perception (stable), intention (choisie),
   exécution (vivante). Aucune ne remplace l'autre.
3. **La perception est stable ; l'exécution est volatile.** Recalculer la
   perception à chaque rangée est proscrit : c'est la cause des lenteurs
   mesurées (161,6 s) et des faux « définitivement inaccessible ».
4. **La reprise fait partie du modèle.** Elle n'est ni une exception, ni un
   échec : c'est un geste prévu, borné et couvert.
5. **Les liaisons visibles bornées sont une politique métier**, pas un défaut
   (conclusions B2E) : liaisons de bord, longueur plafonnée, une par zone, et
   seulement si elles débloquent réellement des rangées. Les liaisons
   traversantes restent interdites.
6. **Le planificateur actuel (`planning.py`) est reconnu comme couche de
   vérification géométrique**, pas comme stratégie de parcours. Ses primitives
   sont conservées ; sa stratégie de sélection de rangée n'est pas la stratégie
   cible (conclusions B2F).
7. **Les paramètres de tolérance ne remplacent pas la stratégie.** Le corridor
   (`SEAM_RADIUS_FACTOR`) n'est pas un levier de stratégie : mesuré sans effet
   dominant (B2D).
8. **Les documents fondateurs prévalent sur le code.** Un écart se corrige dans
   le code, jamais dans le document.

---

# Annexe — cohérence des trois textes fondateurs

Vérification réalisée le 2026-11-17 entre `G0_RAPPORT`,
`BRODEUR_VISION_MODEL` et `G2_CARTE_CONCEPTUELLE`.

- **Documents lus et comparés** : les trois, intégralement.
- **Doublons relevés** : 3 (état d'accès, voûte/transition, cul-de-sac/terminal).
- **Contradictions relevées** : 1 (rang du Pont dans la hiérarchie).
- **Concepts manquants relevés** : 5 (Culée, Couverture future, Sous-zone,
  Adjacence, Silhouette/Vides/Matière).
- **Définitions ambiguës relevées** : 3 (Accès, Couloir, entrée par la base).
- **Résolutions** : toutes consignées au § E des Concepts Métier Officiels.

Aucun de ces écarts ne remettait en cause les conclusions des audits B2C à B2G ;
ils concernaient le vocabulaire et la hiérarchie, pas le raisonnement.
