# G2 — CARTE CONCEPTUELLE DU MOTEUR DE VISION BRODEUR

Architecture métier du cerveau du futur moteur CREABROD. Document conceptuel :
aucun code, aucune classe, aucun algorithme, aucune implémentation.

Il répond à une seule question : **de quoi un moteur doit-il être conscient
avant de calculer la première rangée ?**

---

## Vue globale

Le cerveau se lit en trois couches, et une seule doit être stable.

| Couche | Question posée | Nature | Stabilité |
|---|---|---|---|
| **Perception** | « Quelle forme ai-je devant moi ? » | objets géométriques et topologiques | permanente pour une forme donnée |
| **Lecture stratégique** | « Dans quel ordre, avec quelle tolérance ? » | intentions et décisions | stable pendant le bloc |
| **Exécution** | « Où est l'aiguille, et que reste-t-il à couvrir ? » | état vivant | change à chaque rangée |

La règle d'architecture tient en une phrase : **la perception se calcule une
fois, l'exécution se met à jour en continu.** Confondre les deux — recalculer la
perception à chaque rangée — produit à la fois la lenteur (161,6 s mesurées) et
les faux « définitivement inaccessible » relevés en B2C.

---

## Objets fondamentaux

### Famille 1 — Géométrie (ce qui est donné, immuable)

- **Silhouette** : la limite extérieure de la matière.
- **Vides** : trous intérieurs et échancrures ouvertes.
- **Matière** : ce qui reste une fois les vides retirés.
- **Dimensions et orientation** : encombrement, axe long, inclinaison.

Ces objets ne changent jamais pendant un remplissage. Ils ne dépendent de rien.

### Famille 2 — Topologie perçue (ce qui est déduit, stable)

- **Zone** : partie continue de matière.
- **Sous-zone** : subdivision d'une grande zone qui se comporte comme une salle.
- **Passage** : étranglement reliant deux zones.
- **Couloir** : matérialisation d'un passage avec sa largeur utile (voir
  dépendances : il dépend aussi de la densité de couture).
- **Coin** : jonction de deux bandes, candidate à la reprise.
- **Cul-de-sac** : zone terminale à passage unique.
- **Zone terminale** : zone à un seul accès.
- **Zone de transition** : zone traversée sans y demeurer.
- **Anneau** : zones disposées en boucle autour d'un vide.
- **Pont** : deux culées et une voûte, structure composite.
- **Adjacence** : relation « ces deux zones se touchent par ce passage ».

Ces objets sont déduits de la géométrie, mais ils sont **stables** : coudre ne
change pas la topologie de la forme. C'est l'état d'accès qui change, pas elle.

### Famille 3 — Intention stratégique (ce qui est choisi)

- **Départ** : zone terminale ou coin où le bloc commence.
- **Sortie** : zone terminale ou coin où il s'achève.
- **Ordre de visite des zones** : l'intention de parcours.
- **Budget d'imperfection** : combien de reprises, de quelle longueur, où.
- **Angle par zone** : chaque zone a son orientation de remplissage.

Ces objets dépendent de la topologie pour être *possibles*, mais d'une décision
humaine pour être *choisis*. Ils précèdent toute rangée.

### Famille 4 — État d'exécution (ce qui vit)

- **Position de l'aiguille**.
- **Zone courante**.
- **État d'accès par zone** : ouvert, temporairement fermé, définitivement fermé.
- **Couverture future disponible** : ce qui reste à coudre et recouvrirait un
  trajet.
- **Points de reprise disponibles**.
- **Reprises effectuées** (compteur du budget consommé).

Ces objets changent à chaque rangée. Ils ne se déduisent jamais de la forme
seule : ils dépendent du travail déjà accompli.

---

## Relations entre objets

### Ce qui appartient à quoi

```
Forme
├── Silhouette
├── Vides
├── Matière
│   ├── Zones
│   │   ├── Sous-zones
│   │   ├── Zones terminales  (dont Cul-de-sac)
│   │   ├── Zones de transition
│   │   └── Anneaux
│   ├── Passages
│   │   └── Couloirs
│   ├── Coins
│   └── Ponts  (composés de Culées + Voûte)
├── Points remarquables  (Départ, Sortie, Points de reprise candidats)
├── Intentions  (Ordre de visite, Budget d'imperfection, Angles par zone)
└── État d'exécution  (Position, Accès, Couverture future, Reprises)
```

### Ce qui dépend de quoi

| Objet | Dépend de | Pourquoi |
|---|---|---|
| Matière | Silhouette, Vides | la matière est ce qui reste |
| Zones | Matière | une zone est un morceau connexe de matière |
| Passages | Zones | un passage n'existe que par les zones qu'il relie |
| Couloirs | Passage **et** densité de couture | la largeur utile dépend de l'écart de points |
| Coins | Zones, bandes | un coin est une jonction |
| Culs-de-sac | Passage, Zone terminale | un cul-de-sac est défini par son unique passage |
| Anneaux | Vides, Zones | sans vide, pas d'anneau |
| Ponts | Culées, Voûte | structure composite |
| Départ, Sortie | Zones terminales, Coins | on ne part pas du milieu d'un vide |
| Ordre de visite | Zones, Adjacences, Départ, Sortie | l'ordre se choisit sur le graphe des zones |
| Budget d'imperfection | Décision humaine | ce n'est pas une propriété de la forme |
| Angle par zone | Zone, orientation de la bande | une voûte et une jambe n'ont pas le même axe |
| État d'accès | Position, Zones cousues, Couverture future | c'est un état du travail, pas de la forme |
| Point de reprise | Couverture future disponible | un point de reprise sans couverture est un défaut |
| Couture de reprise | Point de reprise, Budget | elle consomme le budget |

### Ce qui peut exister sans quoi

| Peut exister seul | Ne peut pas exister sans |
|---|---|
| Zones (forme jamais cousue) | — |
| Couloir géométrique | Passage |
| Coin | deux bandes de matière |
| Cul-de-sac | un passage unique |
| Anneau | un vide entouré |
| Pont | culées + voûte |
| Budget d'imperfection (défini) | — (mais sans effet sans zone) |
| Départ / Sortie | une zone terminale ou un coin |
| Point de reprise | une couverture future |
| Couture de reprise | un point de reprise et du budget |
| État d'accès | une position et une couverture future |

### Ce qui doit être calculé avant quoi

1. **Silhouette et Vides** — la donnée brute.
2. **Matière** — ce qui reste.
3. **Passages et largeurs** — les étranglements ; ils contraignent tout le reste.
4. **Zones et adjacences** — le graphe des salles.
5. **Structures remarquables** — anneaux, ponts, culs-de-sac, zones terminales,
   zones de transition, coins.
6. **Départ et Sortie** — décision, sur les zones terminales.
7. **Ordre de visite** — intention, sur le graphe.
8. **Budget d'imperfection et angles par zone** — réglages avant couture.
9. **Couverture future initiale** — tout ce qui reste à coudre.
10. **Rangées** — exécution seulement.
11. **État d'accès** — recalculé en continu pendant l'exécution.

Aucune étape 9-11 ne doit jamais remonter modifier les étapes 1-5.

---

## Cycle de perception

```
Silhouette        « une forme ouverte, avec un vide »
    ↓
Zones             « deux culées et une voûte »
    ↓
Passages          « la voûte est le seul lien ; les épaules sont étroites »
    ↓
Culs-de-sac       « le bas de chaque culée est un terminus »
    ↓
Départ / Sortie   « j'entre par le bas d'une culée, je sors par l'autre »
    ↓
Stratégie         « culée gauche, voûte en continuité, culée droite »
    ↓
Remplissage       « rangées, angle par zone, reprises si besoin »
    ↑
    └── état d'accès et couverture future, mis à jour à chaque rangée
        (retour local : ne change jamais la perception)
```

Deux propriétés à retenir :

- **La descente est unidirectionnelle.** Une décision de rangée ne redéfinit
  jamais une zone, un passage ou un cul-de-sac.
- **La remontée est locale et volatile.** Elle ne concerne que la position,
  l'accès et la couverture.

---

## Objets permanents

### Permanents géométriques
Silhouette, Vides, Matière, Dimensions, Orientation.
*Ne changent jamais, sauf modification du dessin par l'utilisateur.*

### Permanents topologiques
Zones, Passages, Couloirs, Coins, Culs-de-sac, Zones terminales, Zones de
transition, Anneaux, Ponts, Adjacences.
*Stables pendant tout le remplissage : coudre ne change pas la forme.*

### Permanents stratégiques (semi-permanents)
Départ, Sortie, Ordre de visite, Budget d'imperfection, Angles par zone.
*Fixés avant le premier point, modifiables seulement par décision humaine.*

---

## Objets temporaires

Position de l'aiguille, Zone courante, État d'accès par zone, Couverture future
disponible, Points de reprise disponibles, Reprises effectuées.
*Changent à chaque rangée ; ne se déduisent jamais de la forme seule.*

---

## Dépendances

Trois dépendances structurent tout le modèle :

1. **Topologie ← Géométrie.** Les zones, passages et coins sont déduits du
   dessin. Si le dessin change, la perception est refaite une fois.
2. **Stratégie ← Topologie + intention humaine.** L'ordre de visite est possible
   grâce au graphe des zones, mais il est choisi : deux brodeurs peuvent
   choisir deux ordres valides pour la même forme.
3. **Exécution ← Stratégie + état du travail.** L'état d'accès dépend de ce qui
   a déjà été cousu, donc du temps, pas du dessin.

Et une dépendance qu'il faut nommer explicitement parce qu'elle est nouvelle :

4. **Reprise ← Couverture future.** Une couture de reprise n'est légitime que
   si une matière encore à coudre la recouvrira. Cette dépendance n'existe dans
   aucun modèle actuel du projet : le planificateur juge une liaison par rapport
   aux coutures passées, jamais par rapport à la couverture future.

---

## Carte conceptuelle complète

```
                          ┌─────────────────┐
                          │      FORME      │
                          └────────┬────────┘
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
   ┌────▼─────┐              ┌─────▼──────┐            ┌──────▼──────┐
   │ GÉOMÉTRIE│              │ TOPOLOGIE  │            │  INTENTION  │
   │ (stable) │──déduit─────▶│  (stable)  │──contraint▶│  (choisie)  │
   └────┬─────┘              └─────┬──────┘            └──────┬──────┘
        │                          │                          │
 Silhouette                 Zones ─┤ Adjacences         Départ / Sortie
 Vides                      Passages                        Ordre de visite
 Matière                    Couloirs                        Budget d'imperfection
 Dimensions                 Coins                           Angles par zone
                            Culs-de-sac
                            Zones terminales
                            Zones de transition
                            Anneaux
                            Ponts (culées + voûte)
                                         │
                                         ▼
                          ┌──────────────────────────┐
                          │   EXÉCUTION (vivante)    │
                          │ Position                 │
                          │ Zone courante            │
                          │ État d'accès par zone    │
                          │ Couverture future        │
                          │ Points de reprise        │
                          │ Reprises effectuées      │
                          └────────────┬─────────────┘
                                       │
                                       ▼
                                 Remplissage
                              (rangées, angles,
                               reprises bornées)
```

---

## Ce qu'un moteur doit comprendre avant de calculer les rangées

Un moteur doit avoir répondu à ces neuf questions, dans cet ordre :

1. **Où est la matière, où est le vide ?** (géométrie)
2. **Où la matière s'étrangle-t-elle ?** (passages)
3. **Quelles salles en résultent, et comment sont-elles reliées ?** (zones et
   adjacences)
4. **Quelles salles n'ont qu'une entrée ?** (culs-de-sac)
5. **Quelle est la structure d'ensemble ?** (anneau, pont, chaîne de salles)
6. **Où sont les coins épais qui pardonneront une reprise ?**
7. **Par où entre-t-on, par où sort-on ?** (zones terminales)
8. **Quel ordre de visite, et quel budget d'imperfection ?** (intention)
9. **Que reste-t-il à coudre à chaque instant pour recouvrir un trajet ?**
   (couverture future, état vivant)

Tant que ces questions n'ont pas de réponse, toute rangée calculée est une
rangée posée au hasard des contraintes locales — ce que B2C, B2D, B2E et B2F ont
mesuré : 42 % de couverture sur les formes réelles, insensible au corridor,
insensible aux liaisons visibles.

**Fin du document conceptuel. Aucun code, aucune classe, aucun algorithme.**
