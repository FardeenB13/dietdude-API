from django.db.models.functions import Length

from .models import GroceryItem, GroceryList, Ingredient


def _is_word_char(c: str) -> bool:
    return c.isalnum() or c in "'-"


def match_ingredient_ids_from_text(raw_text: str) -> list[int]:
    """
    Find Ingredient rows whose names appear in the grocery list text (case-insensitive,
    word-boundary aware). Longer names are matched first so e.g. "Cooked Rice" wins over "Rice".
    """
    if not raw_text or not raw_text.strip():
        return []

    lower_text = raw_text.lower()
    ingredients = (
        Ingredient.objects.annotate(nlen=Length("name"))
        .order_by("-nlen", "name")
    )

    mask = [False] * len(lower_text)
    matched_ids: list[int] = []

    for ing in ingredients:
        needle = ing.name.lower()
        if not needle:
            continue
        start = 0
        while start <= len(lower_text) - len(needle):
            idx = lower_text.find(needle, start)
            if idx == -1:
                break
            end = idx + len(needle)
            if any(mask[idx:end]):
                start = idx + 1
                continue

            left_ok = idx == 0 or not _is_word_char(lower_text[idx - 1])
            right_ok = end >= len(lower_text) or not _is_word_char(lower_text[end])
            if not (left_ok and right_ok):
                start = idx + 1
                continue

            matched_ids.append(ing.id)
            for i in range(idx, end):
                mask[i] = True
            start = end

    seen: set[int] = set()
    ordered: list[int] = []
    for pk in matched_ids:
        if pk not in seen:
            seen.add(pk)
            ordered.append(pk)
    return ordered


def sync_grocery_items_from_text(grocery_list: GroceryList) -> int:
    """
    Create GroceryItem rows for each database ingredient detected in grocery_list.raw_text.
    Returns the number of items created (0 if none matched).
    """
    ids = match_ingredient_ids_from_text(grocery_list.raw_text)
    created = 0
    for ingredient_id in ids:
        _, was_created = GroceryItem.objects.get_or_create(
            grocery_list=grocery_list,
            ingredient_id=ingredient_id,
        )
        if was_created:
            created += 1
    return created
