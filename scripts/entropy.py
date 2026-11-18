import numpy as np
from collections import defaultdict
from scripts.utils import get_available_clothes


def shannon_entropy(value_sets, total_articles):
    cum_sum = 0
    for articles_with_value in value_sets.values():  # sets of article ids
        article_ratio = len(articles_with_value) / total_articles
        cum_sum -= article_ratio * np.log2(article_ratio)
    return cum_sum

def next_category(articles, asked_categories):
    category_value_sets = defaultdict(lambda: defaultdict(set))
    for article in articles:
        for category, values in article["tags"].items():
            for value in values:
                # store article ids that have this value for their category
                category_value_sets[category][value].add(article["id"])
    total = len(articles)
    return max(
        category_value_sets,
        key=lambda cat: shannon_entropy(category_value_sets[cat], total) \
        if cat not in asked_categories else -1
    )

def main():
    clothes = get_available_clothes()
    asked_categories = set()
    k = 5
    while True:
        # find next category with highest entropy
        category = next_category(clothes, asked_categories)
        asked_categories.add(category)

        # find all possible options for this category
        options = set()
        for article in clothes:
            if category in article["tags"]:
                options.update(article["tags"][category])

        # ask user to choose an option
        print(f"Choose {category}...")
        for opt in options:
            print(f" - {opt}")
        choice = input()

        # filter clothes based on choice
        clothes = [
            article for article in clothes
            if category in article["tags"] \
            and choice in article["tags"][category]
        ]
        print(f"{len(clothes)} items remain.")

        # stop if few enough clothes remain
        if len(clothes) <= k:
            break
        
        # stop if all categories have been asked
        all_categories = [set(article["tags"].keys()) for article in clothes]
        all_unique_categories = set().union(*all_categories)
        if len(asked_categories) == len(all_unique_categories):
            break


if __name__ == "__main__":
    main()