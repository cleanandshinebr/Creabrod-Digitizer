from core.objects import Contour
from core.ordering import move_item


def test_monter_et_descendre():
    a, b, c = object(), object(), object()
    liste = [a, b, c]
    assert move_item(liste, b, -1) is True
    assert liste == [b, a, c]
    assert move_item(liste, b, 1) is True
    assert liste == [a, b, c]


def test_limites_et_element_inconnu():
    a, b = object(), object()
    liste = [a, b]
    assert move_item(liste, a, -1) is False
    assert move_item(liste, b, 1) is False
    assert move_item(liste, object(), 1) is False
    assert liste == [a, b]


def test_deux_dessins_identiques_ne_sont_pas_confondus():
    x = Contour()
    y = Contour()  # exactement pareil que x
    liste = [x, y]
    assert move_item(liste, y, -1) is True
    assert liste[0] is y
    assert liste[1] is x
