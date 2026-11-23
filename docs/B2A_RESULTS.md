# B2A_RESULTS — planificateur en mode observateur

Étape : **B2A** — exécution conforme à [B2A_OBJECTIFS](B2A_METRICS.md)
Date des mesures : **2026-11-16**
Environnement : Windows, Python 3.14, pytest 9.1.1, branche `wip/fill-concave`.

> Ce document rapporte des mesures réelles. Aucun changement de comportement
> n'était autorisé : il n'y en a pas. Aucune conclusion sur B2B n'est prise ici,
> seuls les constats mesurés sont présentés.

---

## 1. Résultat principal : la trajectoire ne change pas

Les cinq formes de référence ont été produites deux fois — sans observation,
puis avec. Comparaison **stricte** des listes de points :

| Forme | Comparaison |
|---|---|
| rectangle 20 × 20 mm | **IDENTIQUE** |
| concave 30 × 10 mm | **IDENTIQUE** |
| forme à trou 40 × 40 mm | **IDENTIQUE** |
| arche 429,5 × 141,1 mm | **IDENTIQUE** |
| forme en U 20 × 20 mm | **IDENTIQUE** |

Aucune erreur de planificateur n'est remontée sur ces cinq formes.

## 2. Correction de compte préalable

Le compte de tests indiqué jusqu'ici (174) était faux d'une unité : il avait été
obtenu en comptant les points de la sortie `-q`. Avec `-o addopts=""`, qui
affiche le décompte réel, la mesure donne :

| Moment | Collectés | Réussis | Échecs | Erreurs (bac à sable) |
|---|---|---|---|---|
| avant B2A | **173** | 154 | 0 | 19 |
| après B2A | **184** | **165** | **0** | 19 |

Les 11 tests ajoutés par B2A passent tous. Les 19 erreurs restent les mêmes
avant et après : `PermissionError` sur les dossiers temporaires, dues au bac à
sable de l'assistant, et non au code (documenté dans `PROJECT_STATUS.md`).

## 3. Mesures du parcours (liaisons cousues)

Colonnes `g` = parcours réellement produit (glouton), `p` = planificateur.
Les compteurs `>10`, `>20`, `>40` sont des nombres de liaisons dépassant le
seuil, en mm.

| Forme | rangées | g.n | g>10 | g>20 | g>40 | g max | p.n | p>10 | p>20 | p>40 | p max | plan rangées | terminé | plan (s) | glouton (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rectangle 20 × 20 | 10 | 9 | 0 | 0 | 0 | 0,0 | 10 | 0 | 0 | 0 | 2,0 | 10/10 | oui | 0,828 | 0,001 |
| concave 30 × 10 | 8 | 7 | 1 | 0 | 0 | 18,8 | 3 | 0 | 0 | 0 | 2,0 | 3/8 | non | 0,832 | 0,001 |
| trou 40 × 40 | 28 | 27 | 1 | 0 | 0 | 15,8 | 15 | 0 | 0 | 0 | 2,0 | 15/28 | non | 3,929 | 0,019 |
| **arche** | 119 | 118 | **7** | **6** | **1** | **101,8** | 45 | 0 | 0 | 0 | 4,6 | 45/119 | non | **161,598** | 1,051 |
| U 20 × 20 | 16 | 15 | 1 | 0 | 0 | 11,7 | 9 | 0 | 0 | 0 | 2,0 | 9/16 | non | 2,387 | 0,013 |

### Constats mesurés

1. **Le défaut historique est confirmé et chiffré** : sur l'arche, le parcours
   réel produit une liaison de **101,8 mm**, ainsi que 7 liaisons > 10 mm et
   6 > 20 mm. Le chiffre de 46 mm cité dans les notes antérieures est donc un
   minorant : la mesure actuelle est plus sévère.
2. **Le planificateur ne produit jamais de liaison > 10 mm** sur les portions
   qu'il sait coudre (maximum mesuré 4,6 mm sur l'arche) : la marge
   d'amélioration est réelle.
3. **Mais il est incomplet sur 4 formes sur 5** : 45/119 rangées sur l'arche,
   9/16 sur le U, 15/28 avec un trou, 3/8 sur la forme concave. C'est le
   comportement documenté et testé de B1, pas une régression.
4. **Il est lent** : 161,6 s sur l'arche, 3,9 s pour la forme à trou. Ce coût
   interdit un usage interactif tel quel.
5. Les formes simples (rectangle) sont entièrement cousues par les deux
   parcours, avec des liaisons courtes dans les deux cas : le gain du
   planificateur y est nul.

## 4. Coût de l'observation

Comparaison du moteur d'avant B2A (`git show HEAD:core/stitches/fill.py`) et du
moteur actuel, **mesure alternée** après échauffement (une première mesure
groupée donnait un biais d'ordre : l'arche paraissait 30 % plus rapide).

| Forme | avant (s) | après (s) | rapport |
|---|---|---|---|
| rectangle 20 × 20 | 0,0014 | 0,0013 | **0,929** |
| arche | 0,6554 | 0,6206 | **0,947** |

Aucun surcoût mesurable avec `observation=None` : les rapports sont inférieurs
à 1 (bruit de mesure). Le critère « plus de 5 % de surcoût = échec » est donc
respecté.

Temps du moteur sans observation, mesurés seuls : rectangle 0,002 s ;
concave 0,003 s ; trou 0,029 s ; arche 0,844 s ; U 0,007 s.

## 5. Tests exécutés

| Commande | Résultat réel |
|---|---|
| `python -m pytest tests/test_fill_observation.py -o addopts="" -q` | **11 réussis** en 322,80 s |
| `python -m pytest -o addopts="" -q` (suite complète) | **165 réussis, 19 erreurs de bac à sable, 0 échec** en 1210,42 s |

Les 11 tests couvrent : égalité stricte des points (5 formes), comptage des
rangées, parcours incomplet de l'arche, capture d'une panne du planificateur,
cohérence des statistiques de liaison (dont une liaison de 46 mm), stabilité du
contrat de mesures, comptage des liaisons du parcours réel.

## 6. Limites des mesures — à lire avant toute conclusion

1. Les statistiques `plan` ne portent que sur les rangées que le plan a pu
   coudre : comparer `plan.total_length` au total glouton n'aurait aucun sens.
   Seuls `max_length` et les compteurs de seuils sont comparables, et encore :
   le plan de l'arche ne couvre que 45 rangées sur 119.
2. Asymétrie de comptage assumée : le plan compte une liaison par rangée cousue
   (la première est l'approche depuis le point de départ), le glouton n'en
   compte pas pour la première rangée. Écart de 1 attendu entre `g.n` et
   `rows_total`, visible dans le tableau.
3. `plan_seconds` mesure une planification, `greedy_seconds` une construction
   complète de points : ce ne sont pas les mêmes tâches.
4. Une liaison « visible » ou longue n'est pas nécessairement inbrodable : ces
   mesures signalent, elles ne jugent pas.
5. Aucune mesure ne dit quoi que ce soit du résultat textile réel.

## 7. Fichiers livrés

| Fichier | Nature |
|---|---|
| `core/stitches/observation.py` | créé — `LinkStats`, `FillObservation`, seuils, `link_stats` |
| `core/stitches/fill.py` | modifié — paramètre `observation=None`, comptabilité, `_observe_fill` |
| `tests/test_fill_observation.py` | créé — 11 tests |
| `docs/B2A_METRICS.md` | créé puis ajusté (structures mutables, voir révision) |
| `docs/B2A_RESULTS.md` | ce document |

Inchangés : `planning.py`, `engine.py`, `dst_io.py`, `simulation.py`, `app/*`.

## 8. État

**Implémenté et vérifié** : aucun comportement modifié, aucune régression,
mesures disponibles et conformes au contrat.

**B2B n'est pas commencée.** Les constats du §3 (planificateur incomplet sur
4 formes sur 5, coût de 161,6 s sur l'arche) sont des faits à trancher avec
l'utilisateur avant toute décision, notamment sur le repli et sur la
performance.
