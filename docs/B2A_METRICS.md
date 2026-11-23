# B2A_METRICS — contrat des mesures d'observation du remplissage

Version du contrat : **1** (constante `OBSERVATION_VERSION = 1`)
Étape : **B2A — planificateur en mode observateur**
Statut : implémenté le 2026-11-16 ; mesures reportées dans
[B2A_RESULTS](B2A_RESULTS.md).

Révision du 2026-11-16 : lors de l'implémentation, `FillObservation` est
devenue **mutable** (et non `frozen`) pour être remplie en place par le moteur.
Les champs, leurs noms et leurs définitions sont **inchangés** : la version du
contrat reste donc 1. `LinkStats` reste une valeur agrégée, remplacée à chaque
observation.


Ce document est la référence unique. Toute mesure collectée en B2A doit y être
décrite. Toute mesure ajoutée, renommée, supprimée ou dont la définition change
impose d'incrémenter `OBSERVATION_VERSION` et de mettre ce document à jour dans
le même commit. Aucun dictionnaire anonyme n'est utilisé : les mesures sont
portées par des `dataclass` gelées, définies dans `core/stitches/observation.py`.

---

## 1. Principe

Le planificateur `plan_fill_path` (`core/stitches/planning.py`) est exécuté
**après** la construction de la trajectoire habituelle. Il ne participe à
aucune décision : la trajectoire renvoyée à l'interface, à la simulation et à
l'export DST reste celle du moteur actuel.

Deux jeux de mesures sont produits, avec **exactement les mêmes définitions**,
afin d'être comparables :

- `greedy` : le parcours réellement produit aujourd'hui par `fill_stitch_paths` ;
- `plan` : le parcours simulé par `plan_fill_path`.

Comparer deux choses définies différemment ne prouverait rien : la symétrie des
définitions ci-dessous est donc une exigence, pas une commodité.

---

## 2. Vocabulaire normatif

**Rangée** : un segment droit de remplissage produit par
`fill_stitch_segments`, avant découpage en points de couture.

**Liaison** : trajet **cousu** reliant la fin d'une rangée au début de la
rangée suivante. Elle est mesurée comme la somme des longueurs de ses segments
(polyligne réellement insérée), en millimètres.

**Trajet d'arrivée** : trajet final entre la dernière rangée et le point
d'arrivée choisi par l'utilisateur. Il **n'est pas** une liaison et n'entre dans
aucune statistique de liaison ; il est mesuré séparément (`arrival_length`).

**Saut** : déplacement aiguille levée. Le moteur Fill n'en produit aucun à
l'intérieur d'un bloc ; B2A n'en mesure aucun.

**Liaison visible** : liaison qui sort de la matière, longe un bord ou rase une
zone déjà cousue, selon la classification de `planning.classify_link`.

**Parcours incomplet** : plan dont toutes les rangées n'ont pas pu être cousues
sans introduire une liaison refusée (`completed == False`).

---

## 3. Contrat de données

Deux `dataclass` dans `core/stitches/observation.py`. Leurs **noms de champs
sont le contrat** : aucune clé hors de ce document n'est produite.
`FillObservation` est remplie en place par le moteur ; `LinkStats` est une
valeur agrégée remplacée à chaque observation.

### 3.1 `LinkStats` — statistiques d'un jeu de liaisons

| Champ | Type | Unité | Définition exacte |
|---|---|---|---|
| `count` | `int` | — | nombre de liaisons du parcours |
| `total_length` | `float` | mm | somme des longueurs de toutes les liaisons |
| `max_length` | `float` | mm | longueur de la liaison la plus longue (`0.0` si aucune) |
| `over_10mm` | `int` | — | nombre de liaisons de longueur **strictement supérieure** à 10,0 mm |
| `over_20mm` | `int` | — | nombre de liaisons de longueur **strictement supérieure** à 20,0 mm |
| `over_40mm` | `int` | — | nombre de liaisons de longueur **strictement supérieure** à 40,0 mm |

### 3.2 `FillObservation` — l'observation complète

| Champ | Type | Unité | Définition exacte |
|---|---|---|---|
| `version` | `int` | — | version du contrat, `1` |
| `error` | `str` | — | vide si le planificateur a abouti ; sinon type et message de l'exception, capturée et **non propagée** |
| `rows_total` | `int` | — | nombre de rangées fournies au planificateur (`len(rows)` après filtrage des segments dégénérés) |
| `rows_sewn` | `int` | — | nombre de rangées que le plan a pu coudre |
| `completed` | `bool` | — | `True` seulement si toutes les rangées sont cousues et la rangée d'arrivée en dernier |
| `failure` | `str` | — | motif d'arrêt du plan, vide si `completed` |
| `refused_link_count` | `int` | — | nombre de poursuites écartées par le planificateur, toutes raisons confondues |
| `refused_links` | `tuple[tuple[int, float, str], ...]` | — | détail informatif : `(index d'étape, longueur en mm, raison)`, dans l'ordre de rejet |
| `visible_link_count` | `int` | — | nombre de liaisons visibles **acceptées** par le plan |
| `visible_link_total` | `float` | mm | longueur cumulée de ces liaisons visibles |
| `turns` | `int` | — | nombre de demi-tours de bord retenus par le plan |
| `max_turn_outside` | `float` | mm | sortie de matière maximale d'un demi-tour de bord (`0.0` si aucun) |
| `arrival_length` | `float` | mm | longueur du trajet final vers le point d'arrivée (`0.0` si aucun) |
| `plan` | `LinkStats` | — | statistiques des liaisons du planificateur |
| `greedy` | `LinkStats` | — | statistiques des liaisons du parcours réellement produit |
| `greedy_arrival_length` | `float` | mm | longueur du trajet d'arrivée du parcours produit |
| `plan_seconds` | `float` | s | durée du seul appel `plan_fill_path` |
| `greedy_seconds` | `float` | s | durée de la construction complète de la trajectoire habituelle (rangées, liaisons, sous-points, arrivée) |
| `total_seconds` | `float` | s | durée de `fill_stitch_paths` hors observation |

### 3.3 Constantes de seuil

`LINK_ALERT_THRESHOLDS_MM = (10.0, 20.0, 40.0)` — utilisées par `LinkStats` et par
les tests, jamais écrites en dur dans le code de mesure.

Justification des seuils : le défaut historique du projet est un **trajet de
46 mm cousu au-dessus de 22 rangées déjà cousues**. 10 mm signale les reprises
déjà suspectes, 20 mm la limite haute admise par le planificateur
(`DEFAULT_MAX_LINK_MM`), 40 mm encadre le défaut mesuré.

### 3.4 Conversions et stabilité

- Aucun arrondi n'est appliqué dans les structures : les valeurs sont des
  `float` pleine précision. L'arrondi est une affaire d'affichage.
- `FillObservation.to_dict()` existe uniquement pour le journal et les rapports
  de mesure ; ses clés sont **identiques** aux noms de champs ci-dessus.
- Import paresseux : `planning` n'est importé que si l'observation est demandée.

---

## 4. Ce que les mesures ne disent pas

- `plan_seconds` et `greedy_seconds` ne mesurent pas la même chose : le premier
  estime une **planification**, le second une **construction complète de
  points**. Ils donnent un ordre de grandeur, pas un rapport rigoureux. La
  comparaison honnête se fait sur `total_seconds` avant/après activation.
- Un parcours incomplet n'est pas une erreur du logiciel : sur l'arche et sur la
  forme en U, l'arrêt est le comportement documenté et testé de B1.
- Une liaison « visible » n'est pas nécessairement un défaut : c'est un signal.
- Aucune mesure ne prouve la qualité textile réelle (tension, tirage, tissu).

---

## 5. Protocole de mesure (hors tests unitaires)

Pour chaque forme de référence (rectangle 20 × 20 mm, étoile concave, forme à
trou, arche 429,5 × 141,1 mm, forme en U) :

1. un appel avec `observation=None` — référence de temps et de points ;
2. un appel avec `observation=FillObservation` vide ;
3. vérification de l'égalité **stricte** des listes de points ;
4. consignation de `greedy.over_10mm`, `greedy.over_20mm`, `greedy.over_40mm`,
   `plan.over_10mm`, `plan.over_20mm`, `plan.over_40mm`, `rows_sewn`,
   `rows_total`, `completed`, `plan_seconds`, `greedy_seconds`.

Le résultat est reporté dans `PROJECT_STATUS.md` à la fin de B2A, avec les
chiffres réellement obtenus et la date.

---

## 6. Critère d'acceptation du contrat

Le contrat est accepté si :

1. chaque champ du tableau §3.2 est produit sur les cinq formes de référence ;
2. aucune clé n'existe hors de ce document ;
3. `over_10mm >= over_20mm >= over_40mm` pour les deux jeux `greedy` et `plan` ;
4. `count == 0` implique `total_length == 0.0` et `max_length == 0.0` ;
5. un échec du planificateur remplit `error` **sans** modifier la trajectoire.
