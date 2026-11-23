# Règles de travail pour CRÉABROD DIGITIZER

Ce fichier est obligatoire pour tout agent, modèle ou assistant qui intervient
dans ce dépôt.

## Démarrage obligatoire

Avant toute modification :

1. lire `PROJECT_STATUS.md` ;
2. lire `MEGA_PROMPT_MAITRE_DEVELOPPEMENT_LOGICIEL.md` ;
3. lire `COMPLEMENT_CREADROD_DIGITIZER.md` ;
4. consulter `README.md` ;
5. vérifier `git status` et les tests existants ;
6. examiner le code réel avant de proposer une solution.

Ne jamais recommencer le projet depuis zéro et ne jamais remplacer
l'architecture existante sans preuve qu'elle est inadéquate.

## Architecture fondatrice

Les documents suivants sont des **documents de référence métier** et font
autorité sur le code :

- `docs/ARCHITECTURE_FONDATRICE.md` — consolidation officielle : vision du
  brodeur, concepts validés, règles fondamentales, invariants, décisions
  architecturales ;
- `docs/BRODEUR_VISION_MODEL.md` — vocabulaire officiel de la perception ;
- `docs/G2_CARTE_CONCEPTUELLE.md` — architecture conceptuelle du cerveau ;
- **G0_RAPPORT** — lecture des cinq formes par un brodeur (rapport de session du
  2026-11-17). Il n'existe pas de fichier séparé : sa substance est reprise au
  § « Vision du Brodeur » de `docs/ARCHITECTURE_FONDATRICE.md`, qui fait foi.

Règles associées :

- **le code doit s'adapter à ces documents**, jamais l'inverse ;
- **ces documents ne doivent jamais être modifiés pour justifier le comportement
  du code** : un écart entre le code et un document fondateur est un défaut du
  code ;
- toute évolution du moteur doit pouvoir être relue avec ce vocabulaire
  (zone, passage, couloir, cul-de-sac, accès, reprise, couverture future) ;
- les invariants listés dans `docs/ARCHITECTURE_FONDATRICE.md` ne doivent être
  violés par aucune implémentation.

## Règles métier validées

- Le canvas de travail est libre.
- Le dessin ne doit pas être limité par un cadre fixe.
- La machine, le plateau et leurs dimensions sont des paramètres séparés.
- L'utilisateur reste maître de la taille et de la composition du motif.
- EOS3 est une référence technique et philosophique, pas une architecture à copier.
- Les contours, points d'entrée/sortie, angles, sous-couches, connexions,
  densités et compensations doivent être traités comme des éléments distincts.
- Toute modification du moteur de broderie doit être accompagnée de tests.

## Règles de progression

- Travailler par une seule étape cohérente à la fois.
- Décrire l'objectif, les fichiers concernés, les risques et les tests avant
  une modification importante.
- Ne pas modifier le code pendant un audit en lecture seule.
- Après chaque modification, exécuter les tests pertinents et mettre à jour
  `PROJECT_STATUS.md`.
- Attendre la confirmation de l'utilisateur avant de commencer l'étape suivante,
  sauf autorisation explicite contraire.
- Ne jamais supprimer ou écraser le travail existant.

## Reprise par un nouvel agent

Le nouvel agent doit commencer par répondre à ces questions à partir des fichiers
du dépôt :

- Quelle est l'étape actuelle ?
- Qu'est-ce qui est déjà validé ?
- Quels tests ont réellement été exécutés ?
- Quelle est l'unique prochaine étape ?
- Quelles décisions ne doivent pas être annulées ?

La réponse doit venir de `PROJECT_STATUS.md` et du code, jamais de la mémoire
d'un ancien chat.

## Fin d'étape

À la fin d'une étape validée :

1. mettre à jour `PROJECT_STATUS.md` ;
2. exécuter les tests ;
3. vérifier `git diff --check` ;
4. enregistrer un commit Git descriptif ;
5. indiquer clairement ce qui reste à faire.
