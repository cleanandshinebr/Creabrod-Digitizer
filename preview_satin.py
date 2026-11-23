"""Génère une image de contrôle du satin : output/satin_test.png"""
import math
import os

from PIL import Image, ImageDraw

from core.objects import Contour, CORNER, CURVE
from core.stitches.satin import satin_stitch

PIXELS_PAR_MM = 16
MARGE_MM = 8
COULEUR_FIL = (27, 58, 107)
COULEUR_LIGNE = (214, 40, 40)


def exemples():
    s = Contour(satin_width=3.0, satin_spacing=0.4)
    for x, y, kind in [(0, 0, CORNER), (15, -10, CURVE), (30, 10, CURVE), (45, 0, CORNER)]:
        s.add_point(x, y, kind)

    angle = Contour(satin_width=3.0, satin_spacing=0.4)
    for x, y in [(60, -10), (80, -10), (80, 10)]:
        angle.add_point(x, y, CORNER)

    pointe = Contour(satin_width=3.0, satin_spacing=0.4)
    for x, y in [(95, -10), (105, 10), (115, -10)]:
        pointe.add_point(x, y, CORNER)

    largeurs = []
    for y, largeur in [(-12, 1.5), (0, 3.0), (12, 6.0)]:
        c = Contour(satin_width=largeur, satin_spacing=0.4)
        c.add_point(130, y, CORNER)
        c.add_point(160, y, CORNER)
        largeurs.append(c)

    return [
        ("courbe en S (largeur 3 mm)", s),
        ("angle droit", angle),
        ("pointe très aiguë", pointe),
        ("largeur 1,5 mm", largeurs[0]),
        ("largeur 3 mm", largeurs[1]),
        ("largeur 6 mm", largeurs[2]),
    ]


def main():
    calculs = []
    for nom, contour in exemples():
        points = satin_stitch(contour, contour.satin_width, contour.satin_spacing)
        calculs.append((nom, contour, points))

    xs = [x for _, _, pts in calculs for x, _ in pts]
    ys = [y for _, _, pts in calculs for _, y in pts]
    x_min, y_min = min(xs) - MARGE_MM, min(ys) - MARGE_MM
    largeur = round((max(xs) + MARGE_MM - x_min) * PIXELS_PAR_MM)
    hauteur = round((max(ys) + MARGE_MM - y_min) * PIXELS_PAR_MM)

    def convertir(point):
        return ((point[0] - x_min) * PIXELS_PAR_MM, (point[1] - y_min) * PIXELS_PAR_MM)

    image = Image.new("RGB", (largeur, hauteur), "white")
    dessin = ImageDraw.Draw(image)

    print("Résultats du calcul :")
    for nom, contour, points in calculs:
        dessin.line([convertir(p) for p in points], fill=COULEUR_FIL, width=1)
        dessin.line([convertir(p) for p in contour.flatten()], fill=COULEUR_LIGNE, width=1)
        plus_long = max(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:]))
        print(f"  {nom} : {len(points)} points, point le plus long = {plus_long:.1f} mm")

    os.makedirs("output", exist_ok=True)
    chemin = os.path.join("output", "satin_test.png")
    image.save(chemin)
    print(f"\nImage enregistrée : {os.path.abspath(chemin)}")


if __name__ == "__main__":
    main()