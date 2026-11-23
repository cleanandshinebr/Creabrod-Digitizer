def move_item(items, item, delta):
    """Déplace 'item' de 'delta' places dans la liste.

    On retrouve l'élément par identité (c'est bien CET objet), pas par ressemblance.
    Retourne True si l'élément a bougé.
    """
    index = next((i for i, x in enumerate(items) if x is item), None)
    if index is None:
        return False
    new_index = index + delta
    if not 0 <= new_index < len(items):
        return False
    items[index], items[new_index] = items[new_index], items[index]
    return True