# BRODEUR_VISION_MODEL

Vocabulaire officiel du modèle de perception de forme utilisé par un brodeur.
Document de référence : il décrit ce que voit un brodeur **avant** de piquer,
et non une méthode de calcul.

Règle de lecture : chaque concept est défini par son rôle dans la décision de
parcours. Un concept qui ne change aucune décision n'a pas sa place ici.

---

## Concepts

### 1. Zone

**Définition métier.** Partie continue de matière que le brodeur peut remplir
sans franchir un vide ni une couture déjà posée. Une zone se reconnaît au fait
qu'on peut y circuler librement, à l'intérieur de ses propres limites.

**Exemple réel.** La jambe gauche du U ; l'aile droite de la forme concave ;
la bande basse de la forme à trou.

**Contre-exemple.** Le trou central de la forme à trou n'est pas une zone :
c'est un vide. Le creux du V de la forme concave n'est pas une zone non plus.

**Rôle dans la stratégie.** C'est l'unité de décision. On choisit l'ordre des
zones avant de choisir l'ordre des rangées. Une erreur d'ordre de zone ne se
rattrape pas par une meilleure rangée.

### 2. Passage

**Définition métier.** Partie étroite de matière par laquelle on peut entrer
dans une zone ou en sortir. Un passage n'est défini que par ce qu'il relie :
seul, il n'a pas de sens. Sa largeur décide s'il est franchement franchissable
ou seulement effleurable.

**Exemple réel.** La traverse basse du U, qui relie les deux jambes. La voûte
de l'arche, qui relie les deux culées.

**Contre-exemple.** L'ouverture entre les deux jambes du U, en haut : c'est du
vide, pas un passage. On ne le franchit pas, on le contourne.

**Rôle dans la stratégie.** C'est la ressource rare. Un passage doit rester
ouvert le plus longtemps possible ; c'est lui qu'on protège, pas les zones.

### 3. Cul-de-sac

**Définition métier.** Zone qui n'a qu'un seul passage pour entrer et sortir,
et qui s'affine en s'éloignant de ce passage. Une fois cousue, on ne peut plus
y revenir sans traverser.

**Exemple réel.** La pointe d'une aile de la forme concave ; le haut d'une
jambe du U ; le bas d'une culée de l'arche.

**Contre-exemple.** La traverse du U a deux issues : ce n'est pas un cul-de-sac.
Le cœur d'un rectangle n'en est pas un non plus.

**Rôle dans la stratégie.** À prendre en premier. C'est la zone qui ne pardonne
pas : si on la laisse pour la fin, elle est enfermée.

### 4. Coin

**Définition métier.** Zone de jonction où deux bandes de matière se
rencontrent en changeant de direction. Le coin est épais, soutenu, et c'est là
que le geste de reprise est le plus discret.

**Exemple réel.** Les quatre coins de l'anneau de la forme à trou. Les angles
intérieurs du U.

**Contre-exemple.** Le milieu d'une bande n'est pas un coin, même si la bande
est courbe.

**Rôle dans la stratégie.** Lieu privilégié de changement d'angle et de reprise.
Un coin se termine toujours par son passage, jamais par son milieu.

### 5. Anneau

**Définition métier.** Zone qui entoure complètement un vide. On la parcourt en
boucle et l'on revient près de son point de départ.

**Exemple réel.** La matière autour du trou central 16 × 16 mm.

**Contre-exemple.** Un disque plein n'est pas un anneau ; le U n'en est pas un
non plus, puisqu'il s'ouvre.

**Rôle dans la stratégie.** Impose un tour complet et un retour proche du
départ. Le dernier passage d'un anneau est toujours le plus délicat, parce
qu'il se referme sur lui-même.

### 6. Voûte

**Définition métier.** Partie courbe et épaisse qui relie deux zones et qui se
coud en continuité, sans demi-tour au sommet.

**Exemple réel.** Le sommet de l'arche, épais d'environ 46 mm, entre les deux
culées.

**Contre-exemple.** Une bande droite n'est pas une voûte ; la traverse du U est
droite.

**Rôle dans la stratégie.** C'est le couloir porteur. Un demi-tour dans une
voûte laisse une marque dans la courbe : on la traverse d'un seul geste, en
faisant évoluer l'angle.

### 7. Pont

**Définition métier.** Forme complète composée de deux culées et d'une voûte,
que l'on traverse de part en part. Le pont se lit en entier : entrer par une
culée, sortir par l'autre.

**Exemple réel.** L'arche 429,5 × 141,1 mm.

**Contre-exemple.** Le U n'est pas un pont : ses deux jambes sont reliées par le
bas, pas par le haut.

**Rôle dans la stratégie.** Fixe le sens du parcours et les deux extrémités
naturelles du bloc. Sur un pont, on ne revient jamais en arrière.

### 8. Accès

**Définition métier.** Possibilité effective d'atteindre une zone depuis la
position courante de l'aiguille, dans l'état actuel du travail. L'accès n'est
pas une propriété de la forme : c'est une propriété du moment.

**Exemple réel.** La traverse encore libre du U, avant qu'on la coude.

**Contre-exemple.** Une zone dont toutes les entrées ont été cousues n'est plus
accessible, même si elle est intacte.

**Rôle dans la stratégie.** C'est l'état que le brodeur surveille à chaque
rangée, et non la propreté de la rangée elle-même.

### 9. Zone temporairement inaccessible

**Définition métier.** Zone fermée par ce qui vient d'être cousu, mais
rejoignable par une couture de reprise dont le trajet sera recouvert plus tard.
Elle est fermée **maintenant**, pas définitivement.

**Exemple réel.** La jambe droite du U après avoir cousu la traverse côté
gauche, alors que la traverse n'est pas finie.

**Contre-exemple.** Le trou central : aucune couture de reprise ne peut le
franchir sans rester visible. Il n'est donc pas temporairement inaccessible, il
est hors d'atteinte.

**Rôle dans la stratégie.** C'est la situation qui justifie une réparation et
**jamais** un arrêt. Confondre cette notion avec la suivante est l'erreur qui
bloque un remplissage.

### 10. Zone définitivement inaccessible

**Définition métier.** Zone dont l'accès exigerait de franchir un vide, ou de
traverser une zone qui ne sera jamais recouverte. Aucune couture de reprise ne
peut y mener discrètement.

**Exemple réel.** Le vide central de l'arche ; le vide entre les jambes du U.

**Contre-exemple.** Une zone simplement enfermée par une bande déjà cousue
n'est pas définitivement inaccessible : on peut y aller en passant dessous.

**Rôle dans la stratégie.** Seule situation qui autorise à changer l'ordre
prévu. Elle est rare ; le planificateur actuel la déclare beaucoup trop vite.

### 11. Point de reprise

**Définition métier.** Point précis où l'aiguille ressort de la couture de
reprise et reprend le remplissage. Il est choisi pour être soutenu par la
matière et couvert par les rangées suivantes.

**Exemple réel.** Le milieu de la traverse du U, à mi-hauteur ; un coin épais de
l'anneau.

**Contre-exemple.** L'arête d'un trou n'est jamais un point de reprise : le fil
y resterait visible sur le bord.

**Rôle dans la stratégie.** Rend la réparation invisible. Un point de reprise
mal choisi transforme une imperfection cachée en défaut apparent.

### 12. Couture de reprise

**Définition métier.** Couture simple et droite, exécutée pour rejoindre un
point de reprise. Elle se juge sur sa **couverture future**, pas sur sa
géométrie présente : ce qui compte est ce qui la recouvrira.

**Exemple réel.** La traversée de la traverse du U, perpendiculaire aux rangées
qui restent à coudre.

**Contre-exemple.** Un fil tendu en travers du vide n'est pas une couture de
reprise : c'est un défaut, et il ne sera jamais recouvert.

**Rôle dans la stratégie.** C'est le mécanisme qui rend la stratégie tolérante.
Sans elle, la règle « ne pas fermer l'accès » devient une condamnation.

### 13. Zone terminale

**Définition métier.** Zone qui n'a qu'un accès et où le bloc commence ou
s'achève. Elle est souvent un cul-de-sac, mais pas toujours : une zone large à
une seule entrée est terminale sans être un cul-de-sac.

**Exemple réel.** La pointe d'une aile de la forme concave ; le bas d'une culée.

**Contre-exemple.** La voûte de l'arche n'est pas terminale : elle est traversée.

**Rôle dans la stratégie.** Fournit les points de départ et d'arrivée naturels.
On y entre une fois, on n'y revient pas.

### 14. Zone de transition

**Définition métier.** Zone que l'on traverse sans y demeurer, et qui relie deux
zones terminales.

**Exemple réel.** La traverse du U ; la voûte de l'arche.

**Contre-exemple.** Une jambe du U n'est pas une zone de transition : on y
travaille.

**Rôle dans la stratégie.** Se traverse d'un seul geste, en continuité. C'est
elle qui porte la liaison entre les deux moitiés du bloc.

### 15. Couloir

**Définition métier.** Chemin concret à l'intérieur d'un passage ou d'une zone
de transition, caractérisé par sa largeur utile — la largeur réellement
disponible une fois le remplissage commencé.

**Exemple réel.** La traverse du U, haute de 8 mm ; la bande de 12 mm autour du
trou.

**Contre-exemple.** Le vide entre les jambes du U n'est pas un couloir.

**Rôle dans la stratégie.** Contraint la largeur des rangées et le choix de
l'angle. Un couloir trop étroit ne se traverse qu'en une fois.

### 16. Budget d'imperfection

**Définition métier.** Nombre et longueur de coutures de reprise qu'un bloc
tolère, et les endroits où elles sont acceptables. Il se décide **avant** le
premier point, pas au moment du problème.

**Exemple réel.** « Une reprise de 15 mm maximum, dans une traverse ou un coin,
jamais dans le vide. »

**Contre-exemple.** Autoriser n'importe quelle traversée n'importe où : ce n'est
plus un budget, c'est un abandon.

**Rôle dans la stratégie.** Arbitre entre finir proprement et finir tout court.
C'est la seule notion qui permette de comparer deux imperfections au lieu de
les refuser toutes.

---

## Relations

```
Forme        → contient →     Zones, Vides
Zone         → contient →     Passages, Coins, Couloirs
Zone         → contient →     Sous-zones (une grande zone peut en contenir)
Passage      → relie →        deux Zones (ou une Zone à elle-même dans un Anneau)
Couloir      → matérialise →  un Passage ou une Zone de transition
Cul-de-sac   → est une →      Zone terminale dont le Passage est unique
Zone terminale → porte →      Départ ou Sortie
Zone de transition → contient → Couloir
Coin         → joint →        deux Bandes
Coin         → accueille →    Point de reprise
Anneau       → entoure →      un Vide, et boucle → Zones
Pont         → se compose de → deux Culées et d'une Voûte
Voûte        → est une →      Zone de transition courbe
Accès        → qualifie →     une Zone, à un instant donné
Accès        → vaut →         ouvert | temporairement fermé | définitivement fermé
Zone temporairement inaccessible → exige → Couture de reprise vers un Point de reprise
Couture de reprise → exige →  Couverture future suffisante
Budget d'imperfection → limite → Coutures de reprise par Bloc
Ordre de visite → priorise →  Cul-de-sac, puis Zone terminale, puis Zone de transition
```

Deux dépendances méritent d'être soulignées :

- **Accès → état du travail**, et non → géométrie. Une même zone peut changer
  d'état sans que la forme change d'un millimètre.
- **Couture de reprise → Couverture future**. Une reprise n'est jamais jugée
  sur ce qu'elle est maintenant, mais sur ce qui la recouvrira.

---

## Règles fondamentales

1. **On lit une forme en zones avant de la lire en rangées.** L'ordre des
   zones décide de tout ; l'ordre des rangées ne décide que du confort.
2. **Un cul-de-sac se coud avant le couloir qui y mène.** Sinon il est enfermé.
3. **Un couloir ne se coud jamais en deux fois.** Il se traverse d'un geste,
   avec l'angle qui convient.
4. **Un vide ne se franchit jamais par une couture.** Seul un saut avec coupe
   le traverse, et ce n'est plus une couture.
5. **Une reprise n'est légitime que si sa couverture est future et suffisante.**
   Une reprise sur une zone déjà cousue n'est pas une reprise, c'est un défaut.
6. **L'accessibilité est un état surveillé, pas un invariant absolu.** On
   cherche à la conserver ; on ne s'arrête pas parce qu'on l'a perdue.
7. **Temporairement inaccessible ne justifie pas l'arrêt ; définitivement
   inaccessible le justifie.** C'est la distinction qui fait la différence entre
   un brodeur et un logiciel bloqué.
8. **Le budget d'imperfection se fixe avant le premier point.** Décider au
   moment du problème revient à décider sous contrainte de panique.
9. **Départ et arrivée se choisissent parmi les zones terminales ou les coins,
   avant tout calcul.** Ce sont des décisions de composition.
10. **L'angle de remplissage appartient à la zone, pas au bloc.** Une voûte et
    une jambe n'ont pas le même angle.

---

## Comment un brodeur lit une forme

Dans cet ordre, en quelques secondes :

1. **La silhouette d'abord.** Pleine, évidée, ouverte ? Où est le vide ?
2. **Les étranglements.** Où la matière se resserre-t-elle ? Ce sont les
   passages, et ce sont eux qui vont contraindre tout le reste.
3. **Les zones qui en résultent.** Combien de salles, et comment sont-elles
   reliées ?
4. **Les culs-de-sac.** Qu'est-ce que je ne pourrai plus atteindre si je le
   couds trop tard ?
5. **Les couloirs.** Par où je traverse, et en une seule fois ?
6. **Entrée et sortie.** Lesquelles rendent le parcours le plus naturel ? Les
   plus courtes ne sont pas toujours les meilleures : une sortie sous un
   contour futur est préférable.
7. **Le budget de reprises.** Combien, où, et de quelle longueur, avant même de
   commencer.

Ce n'est qu'après cette lecture que la question « dans quel sens je pique les
rangées ? » se pose.

---

## Ce qu'un logiciel doit voir avant de calculer les rangées

Pour remplir les formes de ce projet, un logiciel devrait percevoir, avant tout
calcul de couture :

- **les zones** de matière, et leur hiérarchie ;
- **les vides** à ne jamais franchir ;
- **les passages** et les couloirs, avec leur largeur utile ;
- **les culs-de-sac** et l'ordre dans lequel ils doivent être pris ;
- **les coins** candidats à une reprise ;
- **la couverture future disponible** à chaque instant, c'est-à-dire ce qui
  reste à coudre et recouvrirait un trajet ;
- **l'état d'accès** de chaque zone : ouvert, temporairement fermé,
  définitivement fermé ;
- **les points de départ et d'arrivée** possibles, dans les zones terminales ;
- **le budget d'imperfection** admis pour le bloc.

Aujourd'hui, le planificateur ne perçoit que des rangées. C'est précisément
l'écart identifié en B2F : il vérifie des contraintes locales sur un objet qui
demande une lecture globale. Aucun réglage de tolérance ne peut compenser une
perception absente.

**Ce document ne contient ni code, ni structure de données, ni méthode de
calcul : uniquement le vocabulaire et les règles de lecture du brodeur.**
