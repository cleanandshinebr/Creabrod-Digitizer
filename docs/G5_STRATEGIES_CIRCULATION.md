# G5_STRATEGIES_CIRCULATION — Stratégies de Circulation du Brodeur

Document d'analyse métier officielle — Étape G5.
Fait autorité sur les règles de parcours et l'ordonnancement des structures reconnues en G4.

Références obligatoires :
- `docs/ARCHITECTURE_FONDATRICE.md`
- `docs/BRODEUR_VISION_MODEL.md`
- `docs/G2_CARTE_CONCEPTUELLE.md`
- `docs/G3_PROTO_VISION.md`
- `docs/G4_STRUCTURES_CIRCULATION.md`

Règle absolue : **Ne parler ni de points de couture, ni de rangées.**
Décrire exclusivement le comportement et les intentions d'un maître brodeur qui planifie son cheminement dans la matière.

---

## Chambre unitaire

Une chambre unitaire est un espace d'un seul tenant, convexe ou quasi-convexe, dépourvu de tout étranglement ou col intérieur (ex. rectangle, disque, écusson plein).

1. **Entrées naturelles** :
   Un coin saillant ou une extrémité d'un axe directeur (ex. coin supérieur gauche, pôle amont). L'entrée ne se place jamais au centre de la pièce.
2. **Sorties naturelles** :
   Le coin ou l'extrémité diamétralement opposée à l'entrée, orientée vers le motif suivant ou vers la zone de raccordement finale.
3. **Ordre de visite** :
   Balayage continu, monotone et régulier, de l'entrée vers la sortie. Aucun retour en arrière, aucun rebroussement.
4. **Zones à terminer en premier** :
   Le pôle d'entrée et les bordures périphériques amont : le travail s'en éloigne progressivement sans jamais y revenir.
5. **Zones à garder ouvertes** :
   Le secteur d'évacuation entourant la sortie : c'est le dernier espace touché avant de quitter la chambre.
6. **Reprises éventuellement autorisées** :
   **Aucune reprise tolérée**. Dans une chambre unitaire, tout trajet rapide de liaison resterait visible en surface, car aucune matière future n'existe pour le recouvrir.

---

## Corridor

Un corridor est un tube de matière allongé reliant deux pôles ou reliant deux chambres (ex. traverse d'un U, bande de contour, bras droit).

1. **Entrées naturelles** :
   L'une des deux extrémités ouvertes du couloir.
2. **Sorties naturelles** :
   L'extrémité opposée à l'entrée.
3. **Ordre de visite** :
   Traversée intégrale et d'un seul jet le long de l'axe directeur du corridor. Le brodeur refuse formellement de coudre un corridor en deux passes longitudinales séparées.
4. **Zones à terminer en premier** :
   Si le corridor est précédé d'une zone terminale (cas d'une branche de U), cette zone terminale doit être **totalement achevée** avant d'engager le corridor.
5. **Zones à garder ouvertes** :
   Le couloir lui-même et son débouché vers la sortie : le corridor doit rester entièrement vierge tant que l'amont n'est pas soldé.
6. **Reprises éventuellement autorisées** :
   Au maximum **une reprise rectiligne sous-jacente**, orientée strictement dans l'axe du couloir et vers l'avant (vers la matière encore vierge), jamais vers l'arrière sur du travail déjà accompli.

---

## Pont

Le pont est une structure composite associant deux culées d'ancrage massives réunies par une voûte courbe suspendue (ex. l'Arche 429,5 × 141,1 mm).

1. **Entrées naturelles** :
   La base d'assise de l'une des deux culées (le pied d'ancrage au sol). Il est interdit d'entrer par le sommet de la voûte.
2. **Sorties naturelles** :
   La base d'assise de la culée opposée.
3. **Ordre de visite** :
   Parcours de transfert séquentiel strict en trois actes :
   - *Acte 1* : Remplissage complet de la culée d'entrée, de sa base vers son épaule.
   - *Acte 2* : Franchissement de la voûte d'un seul tenant, d'une épaule à l'autre, avec pivotement continu de l'orientation (en éventail) pour épouser la courbure sans marquer le zénith.
   - *Acte 3* : Remplissage de la culée de sortie, de son épaule vers sa base.
4. **Zones à terminer en premier** :
   La culée d'entrée : elle doit être close et parfaite au moment précis où le travail atteint la première épaule.
5. **Zones à garder ouvertes** :
   La voûte et la culée de sortie. La voûte ne doit recevoir aucune marque avant que la première culée ne soit terminée.
6. **Reprises éventuellement autorisées** :
   **Strictement interdites dans la voûte** : un trajet de reprise sous une voûte courbe forme une corde rectiligne qui coupe le cintre et transparaît sous la trame. Reprise tolérée uniquement au sein de l'épaisseur d'une épaule en cas de calage d'alignement.

---

## Anneau

L'anneau est un circuit fermé de matière entourant un vide central, sans aucune extrémité libre (topologie circulaire à 1 cycle, ex. cadre, œillet, lettre O).

1. **Entrées naturelles** :
   Un coin extérieur épais ou une zone plane discrète, idéalement orientée vers l'amont du dessin global.
2. **Sorties naturelles** :
   Le point immédiatement contigu à l'entrée (bouclage sur lui-même).
3. **Ordre de visite** :
   Rotation continue unidirectionnelle (sens horaire ou anti-horaire au choix) le long du périmètre, sans jamais faire demi-tour en cours de boucle.
4. **Zones à terminer en premier** :
   Le secteur d'amorçage initial : on s'en éloigne dans le sens de rotation choisi.
5. **Zones à garder ouvertes** :
   Le secteur de jonction terminal : la dernière portion du cycle doit rester libre pour permettre la soudure invisible entre la tête et la queue du remplissage.
6. **Reprises éventuellement autorisées** :
   Une reprise de raccordement est admise dans un coin épais lors du bouclage final pour absorber la déformation textile accumulée au cours de la rotation.

---

## Fourche

La fourche est une bifurcation ($1 \rightarrow 2$) où un corridor principal se sépare en deux branches divergentes (ex. lettre Y, ramure).

1. **Entrées naturelles** :
   - *Option nominale* : La base du tronc commun.
   - *Option secondaire* : L'extrémité de l'une des deux branches.
2. **Sorties naturelles** :
   L'extrémité de la branche restante.
3. **Ordre de visite** :
   Le brodeur résout le dilemme de la bifurcation par la stratégie de l'impasse traitée :
   - Le tronc est avancé jusqu'au cœur de la bifurcation.
   - La première branche est traitée en **aller-retour préparé** : le brodeur avance rapidement en sous-couche jusqu'au bout de la branche 1, puis remplit la branche 1 en revenant vers le cœur.
   - Le cœur est franchi, puis la seconde branche est remplie vers l'extérieur jusqu'à son terminus définitif.
4. **Zones à terminer en premier** :
   La première branche explorée doit être totalement close avant de basculer définitivement dans la seconde.
5. **Zones à garder ouvertes** :
   Le nœud central de la fourche (qui sert de pivot de distribution) et la seconde branche d'évacuation.
6. **Reprises éventuellement autorisées** :
   Une reprise sous-jacente au cœur de la fourche (zone triangulaire épaisse) est expressément prévue pour relier la fin de la branche 1 à l'amorce de la branche 2 sans traverser le vide intermédiaire.

---

## Carrefour

Le carrefour est un croisement multi-voies (en T, en X ou en croix) où 3 ou 4 corridors convergent vers une zone centrale élargie.

1. **Entrées naturelles** :
   L'extrémité libre de l'un des bras périphériques.
2. **Sorties naturelles** :
   L'extrémité libre du bras opposé ou désigné pour la suite de l'ouvrage.
3. **Ordre de visite** :
   Stratégie de l'épuisement des impasses latérales :
   - Entrée par le bras 1 vers le carrefour.
   - Traitement des bras latéraux (bras 2 et bras 3) considérés comme des culs-de-sac : aller rapide au fond sous matière, remplissage de retour vers le centre.
   - Remplissage du centre du carrefour (qui coiffe et recouvre tous les départs de branches).
   - Remplissage final du bras 4 vers la sortie définitive.
4. **Zones à terminer en premier** :
   Tous les bras latéraux secondaires doivent être intégralement terminés avant de poser la matière sur le centre du carrefour.
5. **Zones à garder ouvertes** :
   Le centre du carrefour et le bras de sortie. Le centre est le dernier élément nodale à être consolidé.
6. **Reprises éventuellement autorisées** :
   Le carrefour étant une zone de forte épaisseur, des reprises croisées y sont pleinement autorisées sous réserve qu'elles se croisent au centre et soient ultérieurement recouvertes par la finition du carrefour.

---

## Arborescence

L'arborescence est une dorsale principale distribuant une hiérarchie de ramifications multiples (ex. peigne, râteau, motif floral ramifié).

1. **Entrées naturelles** :
   L'extrémité de la ramification la plus profonde et la plus éloignée de la sortie, ou la base de la dorsale.
2. **Sorties naturelles** :
   L'extrémité finale de la dorsale ou le dernier rameau situé vers le motif suivant.
3. **Ordre de visite** :
   Stratégie du « balai de fond » (parcours en profondeur avec éradication des impasses) :
   - On progresse le long de la dorsale.
   - Dès qu'un embranchement secondaire se présente, on le traite et on le liquide immédiatement avant de continuer.
   - On ne dépasse **jamais** un rameau sans l'avoir terminé, sous peine de le laisser dans son dos et de ne plus pouvoir y revenir.
4. **Zones à terminer en premier** :
   Les rameaux secondaires les plus en amont : ils meurent les uns après les autres au fur et à mesure de l'avancée de la dorsale.
5. **Zones à garder ouvertes** :
   Le tronçon aval de la dorsale et le pôle de sortie final.
6. **Reprises éventuellement autorisées** :
   Reprises d'accès le long de la dorsale principale encore vierge pour aller chercher la tête d'un rameau latéral.

---

## Règles communes

Quel que soit le motif ou l'agencement des structures, quatre maximes fondatrices guident l'art du brodeur :

1. **La règle de l'impasse fatale** :
   Un cul-de-sac ne pardonne pas. Il doit être brodé en tout premier (si l'on part de lui), ou en tout dernier (si l'on y finit). Laisser un cul-de-sac derrière soi sans y être entré condamne le remplissage à une traversée disgracieuse ou à une rupture de séquence.
2. **La règle de non-rebroussement en corridor** :
   Un couloir étroit est une voie à sens unique. On le franchit d'un seul jet continu. Le broder à moitié, rebrousser chemin et espérer le recoller plus tard produit immanquablement une cicatrice textile visible.
3. **La règle de la couverture future obligatoire** :
   Une reprise rapide de fil n'est jamais tolérée pour elle-même. Elle n'est légitime que si la matière qui doit être brodée après elle la recouvre entièrement et la noie dans la masse.
4. **La règle de la ligne de fuite permanente** :
   À chaque instant de son travail, le brodeur surveille qu'il existe un chemin continu de matière vierge le reliant à son point de sortie final. S'il coupe sa propre retraite, il est piégé.

---

## Cas ambigus

Dans certaines configurations, la forme pure ne suffit pas à dicter un ordre unique et exige un arbitrage métier :

1. **La symétrie parfaite bilatérale (U régulier, Arche symétrique)** :
   Géométriquement, la culée gauche et la culée droite sont indiscernables. L'entrée et la sortie ne peuvent être choisies que par le contexte global : d'où arrive le fil venant du bloc précédent, et vers où doit-il repartir après ?
2. **Le corridor frontière (hésitation entre salle et couloir)** :
   Lorsque le rapport longueur / largeur d'une bande oscille autour de 2 ou 3, la zone hésite entre une chambre où l'on peut zigzaguer et un couloir à traversée unique. L'arbitrage dépend de l'épaisseur du fil et de la densité choisie.
3. **La fourche équilibrée sans priorité fonctionnelle** :
   Lorsque deux branches d'égale importance s'ouvrent devant l'aiguille, le choix de la branche à visiter en aller-retour dépend de la présence ultérieure d'une bordure satin : le brodeur choisira de sortir par la branche qui sera ultérieurement bordée pour masquer l'ultime point d'arrêt sous la bordure.
