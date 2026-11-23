# CRÉABROD DIGITIZER

Logiciel local de numérisation de broderie, développé en Python avec PySide6.

Le projet est en développement progressif. Il permet déjà de créer des contours,
de générer des points running et satin, de simuler une séquence, de sauvegarder
un projet et d'importer/exporter des motifs machine, notamment DST.

## Principe de travail du canvas

Le canvas de travail est libre : le dessin ne doit pas être limité par un cadre
visuel fixe. Le numériseur reste maître de la taille et de la composition de son
motif.

Les dimensions de la machine, du plateau et du cadre utilisé seront des
paramètres de préparation ou d'export. Elles ne doivent pas empêcher de
travailler sur le canvas ni modifier automatiquement le motif. Les contrôles de
compatibilité machine seront ajoutés séparément, lorsque l'utilisateur choisira
une machine ou un plateau précis.

## Fonctionnalités actuelles

- dessin de contours avec points droits ou courbes ;
- points running stitch ;
- colonnes satin avec réglages de largeur, densité et coins ;
- sous-couches centrale, marche à suivre et zigzag ;
- sélection, déplacement, rotation et redimensionnement ;
- changement de couleur de fil et de mode de connexion ;
- simulation avec lecture, pause, arrêt, avance, retour et vitesse ;
- sauvegarde et relecture de projets JSON ;
- import de motifs machine pris en charge par `pyembroidery` ;
- export DST avec relecture et vérification du fichier produit.
- remplissage de contours fermés par lignes parallèles, avec angle et écart ;
- prise en charge des formes concaves : les zones séparées sont cousues
  séparément et les transitions sont des sauts non cousus.

## Fonctionnalités prévues

- réglages `Fill` intégrés à l'interface ;
- profils de machines et de plateaux ;
- contrôles machine séparés du canvas libre ;
- annuler/rétablir, copier/coller et grille ;
- texte et effets ;
- documentation utilisateur et parcours de test manuel.

## Référence technique EOS3

Le fichier [eos3-fr.pdf](./eos3-fr.pdf) est une référence technique et
philosophique, pas une autorisation de réécrire l'architecture du projet.
Les principes à étudier et à appliquer progressivement sont notamment :

- considérer le contour comme une structure géométrique ;
- distinguer les points de contrôle des points de couture ;
- préserver les courbes et les angles explicites ;
- distinguer les objets satin ouverts des remplissages fermés ;
- traiter la longueur et la densité des points comme des paramètres textiles ;
- prendre en compte les angles, les connexions et la compensation de tirage.

Toute règle tirée du manuel doit être vérifiée dans le code concerné et couverte
par un test avant d'être considérée comme validée.

## Installation

Créer ou sélectionner un environnement Python, puis installer les dépendances :

```powershell
python -m pip install -r requirements.txt
```

Pour installer le projet en mode développement :

```powershell
python -m pip install -e ".[dev]"
```

L'environnement actuellement vérifié pour ce projet est Python 3.14.3 sous
Windows.

## Lancer l'application

```powershell
python main.py
```

## Exécuter les tests

```powershell
python -m pytest -q
```

Les tests vérifient le moteur de points, les sous-couches, la simulation, la
sauvegarde, l'import/export machine et le redimensionnement.

## Documents de référence du projet

- [MEGA_PROMPT_MAITRE_DEVELOPPEMENT_LOGICIEL.md](./MEGA_PROMPT_MAITRE_DEVELOPPEMENT_LOGICIEL.md)
- [COMPLEMENT_CREADROD_DIGITIZER.md](./COMPLEMENT_CREADROD_DIGITIZER.md)
- [eos3-fr.pdf](./eos3-fr.pdf)

Le développement doit rester progressif : une étape ciblée, des tests réels,
une vérification manuelle lorsque nécessaire, puis validation avant l'étape
suivante.
