from typing import List

from _recipe_utils import Recipe

# Define the categories display order, optional
categories_sort: List[str] = []

# Define your custom recipes list here
# Example: https://github.com/ping/newsrack-fork-test/blob/custom/_recipes_custom.py

recipes: List[Recipe] = [
    Recipe(
        recipe="atlantic-magazine",
        slug="atlantic-magazine",
        src_ext="epub",
        category="news"
    ),
    Recipe(
        recipe="atlantic",
        slug="atlantic-web",
        src_ext="epub",
        category="news"
    ),
    Recipe(
        recipe="atlantic",
        slug="atlantic-web",
        src_ext="epub",
        category="news"
    ),
    Recipe(
        recipe="The Economist",
        slug="economist",
        src_ext="epub",
        category="news"
    ),
    Recipe(
        recipe="nytimes",
        slug="nytimes",
        src_ext="epub",
        category="news"
    ),
]
