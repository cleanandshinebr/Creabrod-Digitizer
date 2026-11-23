# État de continuité — CRÉABROD DIGITIZER

Dernière mise à jour : 2026-11-17

## Objectif du projet

Développer progressivement un logiciel local de numérisation de broderie,
inspiré des principes utiles d'EOS3, permettant de créer, modifier, simuler,
sauvegarder et exporter des motifs machine.

## Décisions validées

- Le canvas de travail est libre et ne doit pas être limité par un cadre fixe.
- L'utilisateur contrôle la taille de son motif.
- Les dimensions de la machine, du plateau et du cadre sont des paramètres
  séparés, utilisés lors de la préparation ou de l'export si l'utilisateur les
  choisit.
- EOS3 sert de référence technique pour la géométrie, les points, les angles,
  les sous-couches, la densité et la compensation.
- Le manuel EOS3 ne doit pas être copié aveuglément et ne justifie pas une
  réécriture complète de l'architecture.
- Le projet doit progresser par petites étapes testées et validées.
- Règle tatami (2026-10-20, remplace la règle « transitions entre zones =
  sauts ») : à l'intérieur d'un bloc de remplissage, la machine ne saute
  jamais. Les rangées sont découpées en points de longueur du dessin et les
  transitions entre rangées ou zones sont des sous-points cousus, même à
  travers un creux ou le vide, comme le fait EOS.

## État technique vérifié

- Point d'entrée : `main.py`.
- Interface : `app/` avec PySide6.
- Moteur métier : `core/`.
- Export machine : `exporters/dst_io.py`.
- Environnement vérifié : Python 3.14.3 sous Windows.
- Dépendances documentées dans `requirements.txt` et `pyproject.toml`.
- Branche Git réelle (vérifiée le 2026-11-15) : `wip/fill-concave`, sommet
  `905a947` « Etat stable fill tatami » (2026-11-08). `main` existe mais reste
  en arrière, à `6ab1320`.
- L'étape B1 (validation `start_point` / `end_point` dans `planning.py`) est
  DÉJÀ COMMITÉE dans `905a947` : `git ls-files` liste `core/stitches/planning.py`
  et ses trois fichiers de tests, et `git log -- core/stitches/planning.py`
  les rattache à ce commit. Les hashes cités dans les versions précédentes de
  ce fichier (`910e9d7`, `199c530`, `a00d397`, `1b75df4`, `3b606cc`) n'existent
  pas dans ce dépôt : ne pas les rechercher.

## Fonctionnalités validées

- contours running stitch ;
- colonnes satin ;
- sous-couches centrale, marche à suivre et zigzag ;
- connexions running, jump et trim ;
- sélection, déplacement, rotation et redimensionnement ;
- sauvegarde et relecture JSON ;
- import de motifs machine ;
- export DST et relecture de contrôle ;
- remplissage simple de contours fermés, avec angle et écart configurables ;
- remplissage tatami continu : rangées découpées en points de longueur
  réglable (2,5 mm par défaut), transitions rangée à rangée et zone à zone
  cousues en sous-points, aucun saut à l'intérieur d'un bloc Fill ; ordre de
  couture glouton « plus proche voisin » inspiré du graphe de remplissage
  d'Ink/Stitch (idées prises, code non copié — licence GPL respectée)
  (fonction `fill_stitch_paths` dans `core/stitches/fill.py`) ;
- déplacements entre zones en couture simple droite (modèle EOS), sans
  traversée des rangées déjà cousues quand un autre voisin le permet, et
  sans jamais coudre dans un trou explicite ;
- départ et arrivée d'un bloc Fill choisis par l'utilisateur (`start_point`,
  `end_point`) : le bloc commence et finit à ces places, la zone proche de
  l'arrivée étant gardée pour la fin ;
- cache des trajectoires dans `core/stitches/engine.py` : un contour inchangé
  n'est plus recalculé à chaque rafraîchissement du canvas ;
- affichage du segment de fermeture des contours fermés dans le canvas
  (la référence dessinée correspond désormais au polygone réellement rempli) ;
- remplissage de formes concaves par paires d'intersections, avec les
  intervalles séparés cousus entre eux par des sous-points dans la simulation
  et l'export ;
- prise en charge de trous explicites dans un contour Fill (le trou est retiré du
  balayage de remplissage et sauvegardé dans le modèle) ;
- simulation avec lecture, pause, arrêt, avance et retour.

## Vérifications réalisées

- 120 tests pytest réussis (vérifiés le 2026-10-21, dont : fill tatami continu
  sans saut dans le bloc, déplacement entre zones en couture simple droite,
  fin du bloc près du point d'arrivée sur l'arche de référence, cache des
  trajectoires, absence de couture dans un trou explicite même pendant un
  déplacement, export DST acceptant un remplissage de 40 mm de large) ;
- étape B1 : 22 tests de planification (`tests/test_planning.py`), dont 4
  parcours complets (arche et forme en U) vérifiant la continuité, l'absence
  de traversée de couture, la réserve d'arrivée et l'arrêt explicite ;
- étape B1, validation géométrique de `start_point` / `end_point` (2026-10-23) :
  75/75 tests de planification réussis — 22 dans `tests/test_planning.py`, 21
  dans `tests/test_planning_diagnostic.py` et 32 dans
  `tests/test_planning_objectives.py` ; la suite complète du logiciel n'a pas
  été exécutée ;
- méthode sous-point conforme au manuel EOS3 : « Point de devant voyageant
  sous le design » (connexion cousue en Point de Devant plutôt qu'en saut,
  pages PDF 159, 216 et 221 du manuel) ;
- audit géométrique : pour 4 formes (carré, étoile concave, forme à trou,
  forme courbe) × 3 angles × 2 écarts, tous les points de rangées restent
  dans ou sur le contour (le dépassement historique venait de l'affichage du
  segment de fermeture, corrigé dans `app/canvas.py`) ;
- compilation Python réussie ;
- démarrage de `MainWindow` vérifié en mode Qt hors écran ;
- diagnostics Pylance : aucune erreur signalée ;
- `git diff --check` propre lors du dernier audit.

## Fonctionnalités encore incomplètes

- moteur de remplissage `Fill` ;
- angle de broderie réglable indépendamment pour chaque bloc ;
- points d'entrée et de sortie indépendants ;
- trous et branches ;
- compensation de tirage explicite ;
- points courts ;
- profils de machines et de plateaux ;
- annuler/rétablir, copier/coller et grille ;
- texte et effets ;
- tests fonctionnels complets de l'interface.

## Étape actuelle

Le moteur métier du remplissage simple est implémenté, testé et connecté à
l'interface. Les réglages d'angle et d'écart sont visibles dans les panneaux de
propriétés et la barre contextuelle, et le type `Fill` est désormais actif.

Correction de cohérence ajoutée : un contour passé en `Fill` est automatiquement
marqué comme fermé, et le contour en cours est également fermé lors de sa
finalisation. Cela évite l'erreur `ValueError: Le remplissage nécessite un
contour fermé` qui apparaissait lors de la génération du remplissage dans
l'interface.

Le moteur accepte maintenant les formes concaves : chaque rangée est découpée
en toutes ses zones intérieures. Chaque zone est une trajectoire distincte ;
les transitions entre zones sont des sauts, et non des points cousus qui
traverseraient le creux. L'aperçu, la simulation et l'export DST utilisent ces
trajectoires séparées. Le modèle de contour accepte désormais des trous
explicites (`contour.holes`) et le moteur de Fill les exclut du balayage, ce qui
permet de gérer les motifs avec vide interne sans les remplir.

La sélection d'un contour Fill fermé peut aussi se faire en cliquant dans sa
surface remplie. Le test géométrique respecte les concavités : le creux vide ne
devient pas une zone de sélection.

Principes retenus pour `Fill` :

- partir d'un contour fermé ;
- conserver le contour comme géométrie éditable ;
- ajouter une densité ;
- ajouter un angle de points ;
- prévoir une connexion début/fin cohérente ;
- prévoir ensuite les sous-couches, le passage en bordure et la compensation ;
- vérifier la cohérence géométrie → points → simulation → export.

## Étape actuelle

Le moteur métier du remplissage simple est implémenté, testé et connecté à
l'interface. Les réglages d'angle et d'écart sont visibles dans les panneaux de
propriétés et la barre contextuelle, et le type `Fill` est désormais actif.

Mise à jour du 2026-10-20 — remplissage tatami continu :

Observation : le remplissage générait un saut entre chaque rangée
(368 points / 184 sauts sur un seul bloc), ce qui est inbrodable et que
l'utilisateur a constaté sur machine. En s'appuyant sur les captures EOS
fournies par l'utilisateur, la règle tatami a été implémentée :

- `core/stitches/fill.py` : nouvelle fonction `fill_stitch_paths` qui découpe
  chaque rangée en points de longueur réglable puis relie les rangées et
  zones par des sous-points cousus (fonction `_subdivide`) ;
- `core/stitches/engine.py` : la branche Fill utilise `fill_stitch_paths`,
  un bloc Fill produit une (et une seule) trajectoire continue ;
- sous-points routés : quand les deux extrémités du déplacement sont sur le
  contour (cas général), le sous-point suit la bordure dans la forme
  (`_travel_side_points`, `_boundary_arc`, `_offset_toward_inside` dans
  `core/stitches/fill.py`), à 0,2 mm à l'intérieur — plus de diagonales
  droites qui traversaient le remplissage déjà cousu ;
- cas de repli : si une extrémité n'est pas sur le contour (par exemple sur
  un trou), le sous-point reste en ligne droite (point documenté) ;
- correction d'affichage associée dans `app/canvas.py` : le canvas dessine
  le segment de fermeture des contours fermés (cause racine du dépassement
  apparent des lignes de référence, cherché plusieurs jours) ;
- travaux antérieurs commités sous `199c530` et `a00d397` ; routage des
  sous-points commité dans cette étape ;
- ordre de couture glouton : `fill_stitch_paths` choisit à chaque fin de
  segment le segment restant dont une extrémité est la plus proche de
  l'aiguille (plus proche voisin, inspiration Ink/Stitch). Le départ reste la
  rangée la plus haute à gauche. Un seul trajet par bloc est préservé,
  de même que la validité géométrique et les longueurs de points.

Mise à jour du 2026-10-20 (après validation utilisateur) — sous-points sous
le remplissage et début/fin au choix de l'utilisateur :

- RÈGLE REVUE (choix utilisateur) : la marche des sous-points sur les bords
  n'est pas esthétique. Nouveau routage des sous-points :
  1. trajet direct quand il reste dans la forme (trous exclus) — recouvert
     par les rangées suivantes ;
  2. trajet long (idealement > 6 mm) bloqué par un creux ou un trou : chemin
     intérieur par graphe de déplacement quadrillé (underpath, inspiration
     Ink/Stitch : arêtes près de la bordure plus « chères », le sous-point
     passe au milieu du remplissage), fonctions `_build_travel_graph`,
     `_travel_route_underpath`, `_smooth_route` ;
  3. repli : trajet court (≤ 6 mm) ou sans chemin intérieur : marche en
     bordure à 0,2 mm à l'intérieur (`_boundary_arc`), puis trajet droit.
- DÉBUT/ARRIVÉE AU CHOIX (Ink/Stitch `starting_point`/`ending_point`, EOS
  « Point d'Entrée/Sortie ») : `Contour.start_point` / `Contour.end_point`
  (`core/objects.py`, sauvegardés dans le projet). Dans `fill_stitch_paths` :
  le bloc commence à `start_point` s'il est placé (approche cousue en
  sous-points), et se termine à `end_point` (dernier sous-point) ;
- interface (`app/canvas.py`) : menu contextuel « Définir début et fin » →
  « Placer le point de départ/arrivée du remplissage ici » sur un Fill
  sélectionné, plus « Retirer le départ et l'arrivée du remplissage » ;
  marqueurs en croix + étiquettes « Départ » (vert) / « Arrivée » (rouge) ;
- correction d'un retour (bug) introduit par l'ordre glouton : la première
  rangée du fill n'était plus cousue (test
  `test_premiere_rangee_fill_est_cousue`) ;
- validation : 96/96 tests pytest ; performance OK sur une forme
  360 x 147 mm (0,15 s, sous-points replacés vers l'intérieur) ;
- commits : `1b75df4` (underpath), `3b606cc` (départ/arrivée).

## Étape suivante recommandée

Mise à jour du 2026-10-21 — audit du moteur puis étape A.

Audit en lecture seule (demandé par l'utilisateur) de `core/stitches/fill.py`,
`core/objects.py`, `core/stitches/engine.py` et de leurs dépendances
(`satin.py`, `underlays.py`, `exporters/dst_io.py`, `app/canvas.py`,
`core/simulation.py`), avant toute nouvelle modification.

Défauts démontrés sur l'arche 429,5 × 141,1 mm (119 rangées, 5 630 points) :

- lenteur : 151 ms par génération, recalculée à chaque rafraîchissement du
  canvas (dessin + compteur de points), sans aucun cache ;
- ordre glouton piégé : trajet de 46 mm cousu au-dessus de 22 rangées ;
- approche finale au-dessus du remplissage : 27 mm sur 2 rangées (235 mm
  avant la réserve d'arrivée) ;
- trou non fermé accepté puis fermé silencieusement (`_path_for_contour`) ;
- `start_point` / `end_point` acceptés hors de la forme, sans validation
  (constat historique du moteur ; la validation B1 ajoutée en 2026-10-23
  concerne `plan_fill_path`, pas `fill_stitch_paths`) ;
- `engine.stitch_paths` modifiait la liste renvoyée par le moteur Fill
  (`fill_paths.pop(0)`), ce qui interdisait tout cache ;
- aucune détection des contours auto-intersectants ni des tangences ;
- constante `TRAVEL_UNDERPATH_LIMIT_MM` devenue inutilisée.

Étape A réalisée (une seule étape, autorisée par l'utilisateur) :

- déplacement entre zones = couture simple droite (modèle EOS décrit par
  l'utilisateur), y compris à travers l'espace vide ; seul un trou explicite
  interdit le trajet direct (contournement intérieur conservé) ;
- règle « jamais au-dessus du remplissage » conservée : parmi les 16 voisins
  les plus proches, priorité au trajet qui ne traverse aucune rangée cousue ;
- réserve d'arrivée : les rangées dont le milieu est à moins de
  0,30 × diagonale de `end_point` sont cousues en dernier — le bloc se termine
  juste à côté du point choisi ;
- cache dans `core/stitches/engine.py` : clé = géométrie + paramètres +
  départ/arrivée + trous, 128 entrées, résultat jamais modifié (la première
  trajectoire Fill est recopiée avant d'être rejointe aux sous-couches).
  Mesure sur l'arche : premier calcul 8 ms, rafraîchissements suivants 0,08 ms
  (au lieu de 151 ms à chaque affichage) ;
- `app/canvas.py` : suppression du double `addItem` des marqueurs
  départ/arrivée, qui produisait les avertissements
  `QGraphicsScene::addItem: item has already been added to this scene`.

Tests : 98/98 réussis. Les deux anciens tests décrivant le modèle abandonné
(marche en bordure, underpath systématique) ont été remplacés ; ajouts :
couture simple droite, fin du bloc près de l'arrivée sur l'arche, cache,
absence de couture dans un trou même pendant un déplacement.

Défaut connu restant : sur l'arche, un trajet de 46 mm reste cousu au-dessus
de 22 rangées déjà cousues (poche créée par l'ordre glouton). Traitement prévu
à l'étape B (ordre par zones / arborescence de rangées), sans modifier la
géométrie des rangs ni l'export DST.

Prochaine action : validation visuelle par l'utilisateur du nouveau
comportement (liaisons droites, fin près de l'arrivée, fluidité), puis
autorisation de l'étape B.

À tester ensuite : validation du départ/arrivée dans la forme, politique des
trous ouverts, motifs de test manquants (cercle/ellipse, forme étroite,
intersections ambiguës), puis compensation de tirage.

## Étape B1 — planification du parcours (validation complète, 2026-10-21)

Module isolé `core/stitches/planning.py`, **non branché** dans `fill.py`,
`engine.py` ou `dst_io.py` ; la réserve d'arrivée du moteur n'a pas été
supprimée ; l'étape B2 n'est pas commencée. Le module fournit les primitives
(grille matière/trous, accessibilité, classement des liaisons, demi-tours de
bord) et une simulation gloutonne du parcours complet avec réserve de la
rangée d'arrivée et contrôle global des rangées restantes à chaque étape.

Parcours simulés sur la géométrie réelle (rangées produites par le moteur
actuel, écart 2 mm, maille 0,667 mm) :

- **Arche** 429,5 × 141,1 mm, 119 rangées, départ (30 ; 5), arrivée (395 ; 5) :
  - `allow_visible=False` : 45/119 rangées, 44 demi-tours de bord (sortie de
    matière max 2,44 mm) et une approche initiale de 30,3 mm dans la matière
    vers la rangée du bas ; aucune liaison visible acceptée ; arrêt explicite
    à y = 88,37 mm, où les seules poursuites sont des liaisons visibles de
    25,2 mm et 49,9 mm au bord de l'échancrure ;
  - `allow_visible=True` : 49/119 rangées, 2 liaisons visibles acceptées
    (25,2 mm chacune, étapes 46 et 48), puis arrêt explicite : le couvercle,
    le dôme et la branche droite rendraient des rangées inaccessibles.
    Aucun saut, aucune coupe silencieuse.
- **Forme en U** 20 × 20 mm (branches de 6 mm, creux de 8 mm), 16 rangées,
  départ (2 ; 19), arrivée (18 ; 19) :
  - `allow_visible=False` : 9/16 rangées, 9 demi-tours (2,0 mm), aucune
    liaison visible acceptée ; arrêt explicite à l'étape 10 : la branche
    droite n'est joignable qu'en traversant le creux (liaisons visibles de
    12,1 à 15,4 mm) ;
  - `allow_visible=True` : 9/16 rangées, 9 demi-tours, aucune liaison visible
    retenue ; arrêt explicite : même autorisées, les liaisons visibles
    rendraient les rangées du bas inaccessibles. Le contrôle global refuse
    donc une liaison visible qui abandonne des rangées.

Conclusion mesurée : l'arche (goulot de 16,5 mm, échancrure peu profonde,
dôme en cul-de-sac) et le U (branches en cul-de-sac) **exigent au moins une
liaison visible** ; le planificateur les refuse par défaut et s'arrête
explicitement, sans jamais inventer de saut. Pour obtenir un parcours complet
de l'arche, il manque une politique explicite pour la poche couvercle/dôme et
le retour vers la branche droite (liaison visible acceptée, ou ordre/topologie
différents), ainsi qu'une décision sur les coutures de bord des échancrures
peu profondes (classées visibles par la grille). Le corridor de 2 mm entre
rangées reste un point faible connu du maillage : le planificateur le
contourne par les demi-tours et les seeds latéraux.

Tests : 22/22 dans `tests/test_planning.py`, dont 4 parcours complets
(arche et U) vérifiant la continuité, l'absence de traversée de couture, la
réserve d'arrivée et l'arrêt explicite. Suite complète : 120/120 réussis.

### Validation géométrique de `start_point` / `end_point` (2026-10-23)

La validation ajoutée concerne uniquement `plan_fill_path` dans
`core/stitches/planning.py`, dans le périmètre B1. `fill.py`, `engine.py` et
`dst_io.py` n'ont pas été modifiés ; le moteur `fill_stitch_paths` continue
donc d'accepter un `start_point` invalide, comme le constate toujours
`test_diag_engine_accepts_invalid_start`.

Règle appliquée aux deux points :

- intérieur de la matière : accepté ;
- intérieur d'un trou : refusé ;
- point exactement sur le contour extérieur, hors trous : accepté ;
- point sur le bord d'un trou : refusé ;
- point hors du contour : refusé ;
- coordonnées non finies : refusées par `ValueError` ;
- arête dégénérée : conservée comme point de frontière ;
- aucune tolérance numérique ajoutée : la colinéarité est vérifiée exactement
  avec `Fraction`, y compris pour les segments horizontaux, verticaux et
  obliques.

La validation est insérée après la conversion de `start_point` / `end_point`
et avant leur utilisation dans le routage. Les erreurs existantes « aucune
rangée » et `max_candidates` conservent leur priorité.

Tests exécutés :

- `tests/test_planning_objectives.py` : 32/32, dont 24 nouveaux cas couvrant
  les cinq catégories, les bords horizontaux et verticaux, les sommets, les
  arêtes obliques et les coordonnées non finies ;
- `tests/test_planning_diagnostic.py` : 21/21, avec le test qui documentait
  l'acceptation des points invalides adapté en test de refus ;
- `tests/test_planning.py` : 22/22, sans modification ;
- total du périmètre planification : 75/75 réussis.

Constat au 2026-10-23 : la suite complète du logiciel n'avait pas été exécutée
après cette modification et aucun commit n'avait été créé. Depuis, l'audit du
2026-11-15 a établi que B1 est bien commitée dans `905a947` et a relancé la
suite complète (voir la section correspondante).

Prochaine action : B2 (branchement dans `fill.py`, suppression/remplacement de
la réserve d'arrivée, interface) n'est pas commencée et attend son
autorisation. Le commit de B1 n'est plus à faire : il existe déjà dans
`905a947` (voir la section « Audit de reprise du 2026-11-15 »).

## Audit de reprise du 2026-11-15 (lecture seule, puis documentation)

Audit demandé avant toute modification. Aucun fichier de code n'a été modifié
pendant cet audit.

- Branche réelle : `wip/fill-concave`, sommet `905a947` (2026-11-08).
  `main` existe mais pointe sur `6ab1320`.
- État Git : seule modification de l'arbre de travail, `eos3-fr.pdf` supprimé
  (`git status --porcelain` -> `D eos3-fr.pdf`). Rien d'autre n'est modifié
  ni non suivi.
- Anomalie de données : `git fsck --connectivity-only` signale
  `missing blob 7709d540285883f890d22e1165c523271496498d` ; c'est le blob de
  `eos3-fr.pdf`, absent du disque ET des objets Git. `git cat-file -e
  HEAD:eos3-fr.pdf` échoue et `Test-Path eos3-fr.pdf` répond `False`. Le manuel
  EOS3 doit être replacé dans le dossier par l'utilisateur ; Git ne peut pas le
  restaurer. Les commits « dangling » vus par `git fsck` sont des points de
  contrôle d'anciennes sessions d'assistance, pas du travail perdu.
- Suite de tests réellement exécutée (`pytest 9.1.1`, Python 3.14) :
  **173 tests collectés, 154 réussis, 0 échec, 19 erreurs de mise en place**
  (compte corrigé le 2026-11-16 avec `-o addopts=""`, qui affiche le décompte
  réel ; le chiffre 174/155 annoncé d'abord venait d'un comptage manuel des
  points de la sortie `-q`, faux d'une unité).
  Les 19 erreurs sont des `PermissionError [WinError 5]` sur les dossiers
  temporaires (`fixture tmp_path`) : export DST (`test_dst.py`,
  `test_satin_integration.py`), export large de `test_fill.py`, import machine
  (`test_machine_pattern.py`) et sauvegarde de projet (`test_project.py`).
  Reproduction identique avec quatre réglages de `--basetemp`, donc cause
  environnementale, pas un défaut du code.
- Vérification indépendante de l'utilisateur, le 2026-11-15, dans un terminal
  Windows normal (hors bac à sable) : suite entièrement verte, aucun échec,
  aucune erreur. Le décompte final ne s'affiche pas parce que
  `addopts = "-q"` dans `pyproject.toml` combiné à `-q` en ligne de commande
  produit un double mode silencieux : utiliser `python -m pytest -o addopts=""`
  pour lire le total.
- PDF EOS3 : l'utilisateur a replacé `eos3-fr.pdf` dans le dossier le
  2026-11-15 et le blob manquant `7709d540…` a été réécrit à l'identique
  (`git hash-object -w`) ; `git fsck --connectivity-only` ne signale plus
  aucun objet manquant.
- Diagnostic des droits Windows exécuté (outil d'inspection des permissions,
  sans confinement) : verdict `NOT_THIS_CLASS` — aucun défaut de droit sur la
  chaîne de dossiers temporaires, aucune modification appliquée. Le blocage
  vient du bac à sable de l'assistant, qui interdit à Python de créer et
  supprimer ses dossiers temporaires ; il n'apparaît pas dans un terminal
  Windows normal.
- Variable d'environnement à connaître : `PYTEST_DEBUG_TEMPROOT` vaut
  `C:\Users\CREAG\AppData\Local\Temp\opencode\pytest-root` sur cette machine,
  ce qui déplace la racine temporaire de pytest dans un dossier appartenant à
  un autre outil. La vider (`$env:PYTEST_DEBUG_TEMPROOT=''`) avant de lancer
  les tests évite une confusion de diagnostic.
- Vérification utilisateur recommandée : `python -m pytest -o addopts=""` dans
  le dossier du projet, depuis un terminal Windows normal, pour obtenir le
  décompte complet (173 tests avant B2A, 184 après).
- Fichier d'état précédent : les informations y étaient périmées (branche
  `main`, commit `910e9d7`, « aucun commit de cette étape »). Cette section les
  remplace ; le reste du fichier décrit toujours valablement les étapes A, B1
  et le moteur Fill.

## Étape B2A — planificateur en observateur (2026-11-16)

Implémenté et vérifié, **aucun changement de comportement**. Détail complet des
mesures : `docs/B2A_RESULTS.md` ; contrat des mesures : `docs/B2A_METRICS.md`.

- nouveaux fichiers : `core/stitches/observation.py` (contrat des mesures,
  `OBSERVATION_VERSION = 1`), `tests/test_fill_observation.py` (11 tests),
  `docs/B2A_METRICS.md`, `docs/B2A_RESULTS.md` ;
- `core/stitches/fill.py` : paramètre `observation=None` (désactivé par défaut,
  aucun calcul, import paresseux du planificateur). La trajectoire produite est
  **identique** sur les cinq formes de référence (comparaison stricte) ;
- coût : mesure alternée avant/après, rapport 0,93 (rectangle) et 0,95 (arche),
  donc aucun surcoût mesurable ;
- tests : **184 collectés, 165 réussis, 0 échec, 19 erreurs de bac à sable**
  (les 19 sont les mêmes qu'avant l'étape) ;
- mesures clés sur l'arche (119 rangées) : parcours réel = 7 liaisons > 10 mm,
  6 > 20 mm, **1 > 40 mm (101,8 mm)** ; planificateur = 45/119 rangées,
  aucune liaison > 10 mm (max 4,6 mm), mais **161,6 s** de calcul ;
- forme en U : 9/16 rangées planifiées ; forme à trou : 15/28 ; concave : 3/8 ;
  rectangle : 10/10 ;
- aucune perte de fonctionnalité ni de constante utilisée : le moteur de
  remplissage garde son algorithme actuel ;
- aucun commit créé pour B2A à ce stade (attente de validation utilisateur).

Prochaine action : validation de B2A par l'utilisateur à partir de
`docs/B2A_RESULTS.md`, puis décision sur B2B (repli quand le plan est
incomplet, coût du planificateur, éventuelle optimisation).

## G0-G2 VALIDÉS — architecture fondatrice (2026-11-17)

Étape de consolidation documentaire. **Aucun moteur modifié** : ni `fill.py`,
ni `planning.py`, ni `engine.py`.

Livrables :

- `docs/ARCHITECTURE_FONDATRICE.md` créé : vision du brodeur, concepts métier
  officiels (géométrie, topologie, intention, exécution), 12 règles
  fondamentales, hiérarchie de perception, 12 invariants, 8 décisions
  architecturales, annexe de cohérence ;
- `AGENTS.md` : nouvelle section « Architecture fondatrice » — les documents
  fondateurs font autorité sur le code et ne sont jamais modifiés pour le
  justifier ;
- `PROJECT_STATUS.md` : la présente section.

Conclusions reprises des audits B2C à B2G :

- le corridor (`SEAM_RADIUS_FACTOR`) n'est pas la cause dominante des arrêts
  (+2,3 % de couverture au mieux, aucun effet sur l'arche) ;
- les liaisons visibles ne débloquent que 2,9 % ;
- le choix du départ n'explique rien : aucun des départs essayés ne termine une
  forme ;
- **la cause dominante est l'écart de perception** : le moteur raisonne en
  rangées, le brodeur en zones, passages, accès et couvertures futures ;
- le planificateur actuel est conservé comme **couche de vérification
  géométrique**, pas comme stratégie de parcours ;
- aucune régression fonctionnelle : `planning.py` reste inutilisé par le moteur.

Cohérence des trois textes fondateurs vérifiée : 3 doublons, 1 contradiction,
5 concepts manquants, 3 définitions ambiguës, tous résolus et consignés au § E
de `docs/ARCHITECTURE_FONDATRICE.md`.

État Git au 2026-11-17 : commit `207165a` (B2A), puis le commit de documentation
« Docs: architecture fondatrice G0-G2 et etat du projet » ; arbre de travail
propre et `git fsck` sans objet manquant. Le hash de ce dernier commit ne peut
pas être cité ici : il changerait à chaque correction de cette ligne.

## Références à lire

- `AGENTS.md`
- `README.md`
- `MEGA_PROMPT_MAITRE_DEVELOPPEMENT_LOGICIEL.md`
- `COMPLEMENT_CREADROD_DIGITIZER.md`
- `eos3-fr.pdf`
- `docs/ARCHITECTURE_FONDATRICE.md` (fondateur)
- `docs/BRODEUR_VISION_MODEL.md` (fondateur)
- `docs/G2_CARTE_CONCEPTUELLE.md` (fondateur)

## Actions à ne pas répéter

- ne pas recommencer l'architecture ;
- ne pas réintroduire une limite obligatoire de cadre sur le canvas ;
- ne pas modifier à nouveau les sous-couches déjà validées sans reproduire un
  défaut ;
- ne pas considérer une simulation réussie comme une preuve de résultat textile
  sur machine ;
- ne pas commencer une deuxième fonctionnalité avant validation de l'étape Fill.
