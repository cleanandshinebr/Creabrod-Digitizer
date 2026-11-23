# COMPLÉMENT SPÉCIALISÉ — CRÉABROD DIGITIZER
## Règles métier, continuité du projet, moteur de broderie et référence EOS3
### À utiliser avec MEGA_PROMPT_MAITRE_DEVELOPPEMENT_LOGICIEL.md

Ce document complète le méga-prompt universel. Il ne le remplace pas. En cas de conflit, respecter d'abord la sécurité et la préservation des données, puis les exigences métier validées de CRÉABROD DIGITIZER. Ne jamais interpréter ce document comme une autorisation de réécrire l'application entière.

---

# 1. IDENTITÉ ET OBJECTIF DU PROJET

Nom du projet : **CRÉABROD DIGITIZER**.

Il s'agit d'un logiciel de bureau de numérisation de broderie, développé principalement en Python. Le projet est déjà commencé et demeure incomplet. Il comprend plusieurs modules et son travail doit continuer à partir de l'état réel des fichiers présents dans le dossier du projet.

Objectif général : faire évoluer progressivement le logiciel vers un outil fiable permettant de créer ou de modifier des objets de broderie, de générer des points de couture, de visualiser la séquence et d'exporter des fichiers machine, notamment DST lorsque cette fonctionnalité est prévue par le code existant.

Ne présume pas que toutes les fonctions décrites sont déjà implémentées. Vérifie l'état réel du code avant d'affirmer qu'une fonction existe, fonctionne ou est terminée.

# 2. ENVIRONNEMENT DE TRAVAIL CONNU — À REVÉRIFIER

Informations communiquées sur l'environnement :
- Windows.
- Visual Studio Code déjà installé.
- Projet local avec plusieurs fichiers et modules Python.
- Gemma 4 31B est utilisé comme assistant IA.
- Le projet est incomplet et doit être poursuivi progressivement.
- L'utilisateur débute en programmation et a besoin d'instructions simples et exactes.

Ces informations sont un point de départ, pas une preuve de l'état actuel de l'environnement. Vérifie les versions, les chemins, les dépendances et les outils disponibles avant toute opération qui en dépend.

Ne suppose pas que Gemma, Claude, VS Code ou un outil externe partagent automatiquement les mêmes fichiers, la même mémoire ou le même contexte. Le fichier de règles et les notes de reprise doivent servir de référence commune lorsque plusieurs assistants interviennent.

# 3. RÈGLE PRIORITAIRE : CONTINUER, NE PAS RECOMMENCER

Le projet existe déjà. Le but est de poursuivre son évolution, pas de créer un nouveau logiciel à côté ni de remplacer l'architecture sans nécessité démontrée.

Avant de toucher au code :
1. Lire l'arborescence réelle.
2. Examiner le point d'entrée et les modules impliqués dans la tâche.
3. Lire la documentation, les notes et les tests disponibles.
4. Identifier ce qui fonctionne, ce qui est incomplet et ce qui a déjà été corrigé.
5. Vérifier les dépendances entre les fichiers.
6. Présenter un audit concis et la prochaine étape recommandée.

Ne remplace jamais un module complet uniquement parce qu'une nouvelle implémentation paraît plus simple. Ne supprime aucune logique existante avant d'avoir compris son rôle et ses dépendances.

Ne modifie aucun fichier durant l'audit initial en lecture seule. Après l'audit, effectue seulement les changements nécessaires à l'étape autorisée.

# 4. RÈGLE DE PROGRESSION ET VALIDATION PAR L'UTILISATEUR

Le développement se déroule en étapes limitées et indépendantes autant que possible.

Pour chaque étape :
1. Décrire le problème.
2. Indiquer les fichiers concernés.
3. Expliquer la modification minimale proposée.
4. Identifier les risques de régression.
5. Sauvegarder ou confirmer le moyen de retour arrière.
6. Réaliser la modification autorisée.
7. Exécuter les tests disponibles.
8. Fournir les résultats réels et les instructions de test manuel.
9. Attendre la confirmation de l'utilisateur avant de commencer l'étape suivante.

Ne passe pas à l'étape suivante simplement parce que le code a été généré. L'étape est considérée comme vérifiée uniquement selon les critères définis et les tests réellement réalisés.

Si l'utilisateur signale un problème pendant le test, arrêter l'avancement et diagnostiquer ce problème avant toute autre modification.

# 5. RÈGLES MÉTIER DE NUMÉRISATION À PRÉSERVER

Les règles suivantes sont des exigences métier communiquées pour ce projet. Toute modification qui les affecte doit être évaluée explicitement.

## 5.1 Objets et connexions

- La numérisation doit être comprise en termes d'objets ou de blocs de broderie ayant un début, une fin et une séquence de couture.
- Les points générés doivent respecter la logique de connexion prévue entre les blocs.
- Un déplacement sans couture (*jump*) ne doit pas être créé entre des parties qui doivent être reliées par des points de couture.
- La visualisation, la simulation et l'export doivent rester cohérents sur la séquence de points et les déplacements.
- Ne déduis pas qu'une connexion est correcte uniquement parce que deux objets sont visuellement proches. Vérifie la séquence réelle des points et les règles métier.

## 5.2 Sous-couches et ordre de couture

Règle métier communiquée pour les sous-couches d'un même objet ou d'une même branche :
- La première sous-couche, dite « centraux », suit le trajet du début A vers la fin B.
- La deuxième sous-couche, par exemple zigzag ou marche à suivre, doit relier B vers A lorsque c'est le comportement défini pour cet objet.
- Si une troisième sous-couche de satin est nécessaire après cette séquence, le retour de B vers A doit se faire par des points de couture simples au centre, sans saut visible.
- Les sous-couches appartenant à un même objet doivent respecter leur séquence de connexion définie.
- Les sauts sont réservés aux déplacements réellement nécessaires entre des blocs qui ne sont pas connectés par la logique de couture.

Cette règle a fait l'objet d'une correction antérieure rapportée comme résolue. **Ne la considère pas comme un bug à corriger à nouveau sans reproduire un défaut réel.** Avant de toucher à ce mécanisme, rechercher les changements et tests existants, reproduire le problème et préserver la correction.

Si une future décision technique nécessite de modifier ce comportement, expliquer l'impact et obtenir la validation de l'utilisateur avant de changer la règle métier.

# 6. MANUEL EOS3 : RÉFÉRENCE, PAS AUTORISATION DE RÉÉCRITURE

Un manuel EOS3 a été fourni comme source de référence technique. Il doit aider à comprendre les principes de numérisation et à comparer les comportements, mais ne doit pas être traité comme une spécification complète de toutes les fonctionnalités de CRÉABROD DIGITIZER.

Principes EOS3 signalés dans les notes du projet :
- Le contour ou vecteur est une entité géométrique structurante.
- Les points de contrôle servent à définir la géométrie ; ils ne sont pas nécessairement équivalents à une simple liste de points de couture.
- Les courbes doivent être lisses là où c'est nécessaire, tout en préservant les angles explicites.
- Il faut distinguer les objets ouverts en satin et les objets fermés remplis.
- La longueur du point de marche influence le résultat textile, les boucles et le comportement dans les angles.
- Les angles peuvent demander un traitement pointu ou arrondi.
- La compensation de tirage doit être considérée comme un problème lié au comportement du tissu et du fil, et non comme un simple détail esthétique.

Ces éléments sont des sujets à étudier et à vérifier dans le manuel disponible. Ne prétends pas qu'une règle détaillée a été confirmée par le manuel si tu n'as pas consulté le passage correspondant.

## 6.1 Méthode d'utilisation du manuel

Avant d'appliquer une idée du manuel :
1. Identifier le principe exact et la section du manuel qui le décrit.
2. Reformuler le principe en termes simples.
3. Déterminer si ce principe correspond à une exigence actuelle du logiciel ou à une amélioration future.
4. Examiner le code existant concerné.
5. Décrire les différences constatées, sans supposer que toute différence est un bug.
6. Proposer une modification limitée et un test permettant de la valider.
7. Ne pas modifier le moteur global pour intégrer une règle locale.

Ne copie pas aveuglément l'architecture supposée d'EOS3. Le but est de tirer des enseignements pertinents, en respectant le code actuel et les besoins du projet.

# 7. CONNAISSANCES TECHNIQUES DÉJÀ SIGNALÉES — À CONFIRMER DANS LE CODE

Des analyses précédentes ont décrit le fonctionnement suivant :
- `core/stitches/fill.py` contient ou a contenu une fonction `fill_stitch(contour, angle_deg, spacing)`.
- Cette fonction a été décrite comme aplatissant ou fermant le contour, le faisant tourner selon un angle, recherchant les intersections avec des lignes espacées, puis associant les intersections en segments de remplissage.
- Des fichiers cités dans les analyses antérieures comprennent `objects.py`, `engine.py`, `fill.py`, `satin.py`, `underlays.py` et `dst_io.py`.
- Une fonction `build_pattern(objects)` dans `exporters/dst_io.py` a été mentionnée dans un travail d'export DST.

**Attention :** ces noms et descriptions viennent de notes antérieures. Ils doivent être vérifiés dans le dossier courant avant de les utiliser comme description certaine du code. Les fichiers peuvent avoir changé, avoir été déplacés ou ne pas avoir le même contenu.

Ne modifie pas la logique de fermeture des contours, le calcul des intersections, la génération de satin, les sous-couches ou l'export DST sans analyser les effets sur les autres modules et les tests.

# 8. COHÉRENCE ENTRE GÉOMÉTRIE, POINTS, SIMULATION ET EXPORT

Pour toute fonctionnalité qui touche aux points de broderie, examiner les quatre niveaux lorsqu'ils existent :
1. **Géométrie de l'objet** : contours, courbes, angles, orientation, dimensions.
2. **Génération des points** : ordre, densité, longueur des points, connexions, sous-couches et déplacements.
3. **Simulation et affichage** : ordre visuel, mouvements, sauts, limites de l'objet et cohérence avec la séquence.
4. **Export machine** : ordre des points, déplacements, commandes de coupe ou de changement si prises en charge, limites de format et conformité du fichier.

Une correction d'affichage ne prouve pas que les points exportés sont corrects. Une exportation sans erreur ne prouve pas que le motif sera brodé correctement. Tester les niveaux concernés séparément.

# 9. TESTS SPÉCIFIQUES À PRIVILÉGIER

Créer ou conserver une collection de motifs de test simples et reproductibles, en fonction des fonctions réellement prises en charge :
- Ligne ou contour ouvert.
- Contour fermé.
- Forme avec un angle net.
- Courbe.
- Remplissage à différents angles.
- Satin sur une forme adaptée.
- Objet avec une ou plusieurs sous-couches.
- Plusieurs blocs connectés.
- Plusieurs blocs non connectés.
- Motif comprenant un changement de direction.
- Motif proche des limites de taille du format d'export.

Pour les règles de sous-couches :
- Vérifier que la première sous-couche suit A vers B.
- Vérifier que la seconde suit B vers A lorsque cette séquence s'applique.
- Vérifier qu'un éventuel retour central avant le satin utilise des points de couture simples et non un saut.
- Vérifier qu'un saut n'apparaît que lorsqu'il est réellement nécessaire.
- Vérifier que simulation et export suivent le même ordre logique.

Pour l'export DST, lorsque la fonction est disponible :
- Tester un motif simple dont la séquence attendue est connue.
- Vérifier les déplacements et limites de format prises en charge.
- Réimporter ou analyser le fichier avec un outil approprié si cet outil est disponible.
- Ne pas affirmer la compatibilité avec toutes les machines sans tests suffisants sur les formats et équipements ciblés.

Les tests doivent s'adapter aux capacités réelles du logiciel. Ne crée pas une fausse attente qu'une fonction encore inexistante doit déjà passer.

# 10. QUALITÉ TEXTILE ET LIMITES DE SIMULATION

Distinguer clairement :
- Exactitude géométrique.
- Exactitude de la séquence de points.
- Conformité du format d'export.
- Qualité visuelle de la simulation à l'écran.
- Résultat physique réel sur tissu.

La simulation à l'écran ne permet pas, à elle seule, de prouver le comportement réel du fil et du tissu. Les effets de tension, de tirage, de stabilisation, de matière et de machine nécessitent des modèles appropriés et, pour une validation complète, des essais physiques.

Ne prétends pas reproduire intégralement le comportement d'EOS3 ni garantir un résultat industriel sans spécification, mesures et essais suffisants.

# 11. PRÉSERVER LA SIMPLICITÉ DU PROJET

L'utilisateur débute en programmation. Les solutions doivent être expliquées simplement, avec :
- Le chemin exact du fichier.
- Le rôle du fichier.
- Le problème observé.
- La modification proposée.
- Les étapes de test.
- Le résultat attendu.
- La procédure à suivre en cas d'échec.

Ne transforme pas une petite correction en refonte de l'architecture. N'ajoute pas de dépendance lourde sans raison. Préfère une correction ciblée, testable et facile à annuler.

# 12. FORMAT DU RAPPORT POUR CHAQUE ÉTAPE

Utilise ce format adapté au projet :

**Étape :** numéro et intitulé.

**Objectif :** problème exact à résoudre.

**État initial vérifié :** fichiers et comportement observés.

**Règles métier concernées :** notamment connexions, sous-couches, simulation ou export si pertinent.

**Fichiers concernés :** chemins exacts.

**Modification prévue :** solution minimale et raison.

**Sauvegarde / retour arrière :** méthode disponible.

**Tests :** commandes exécutées et résultats réels, ou mention claire si non exécutés.

**Résultat :** terminé et vérifié / implémenté mais non vérifié / bloqué / échec.

**Test utilisateur :** actions simples à effectuer dans l'application et résultat attendu.

**Validation requise :** attendre la confirmation de l'utilisateur avant de continuer.

# 13. NOTE DE REPRISE POUR PLUSIEURS ASSISTANTS IA

Si plusieurs assistants sont utilisés, ne suppose pas qu'ils partagent l'historique ou les fichiers modifiés. Maintenir, si le projet le permet, une note de reprise concise qui contient :
- L'objectif du projet.
- L'étape actuelle.
- Les fichiers réellement modifiés.
- Les décisions validées.
- Les tests réellement exécutés et leurs résultats.
- Les bugs connus.
- Les règles métier à préserver.
- La prochaine action proposée.
- Les actions à ne pas répéter.

Ne marque une étape comme terminée que si les éléments de validation sont disponibles. Ne laisse pas un assistant suivant refaire une correction déjà validée sans preuve qu'elle a été perdue ou qu'un bug subsiste.

# 14. COMPORTEMENT AU DÉMARRAGE

Lorsqu'on ouvre une nouvelle session de travail sur CRÉABROD DIGITIZER :
1. Lire le méga-prompt universel et ce complément s'ils sont accessibles.
2. Examiner les notes de reprise et l'état réel du projet.
3. Réaliser un audit en lecture seule des éléments nécessaires.
4. Résumer ce qui est confirmé et ce qui doit encore être vérifié.
5. Identifier une seule prochaine étape prioritaire.
6. Présenter la modification envisagée et les tests avant de toucher aux fichiers.
7. Attendre l'autorisation lorsque les règles de travail ou le risque l'exigent.
8. Après la modification, tester, documenter et attendre la validation de l'utilisateur.

**Règle finale :** la priorité est de faire progresser CRÉABROD DIGITIZER sans perdre le travail existant, sans réintroduire les bugs déjà corrigés et sans confondre une amélioration théorique avec une amélioration vérifiée.
