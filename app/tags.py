ARTICLE_TYPE = [
    "shirt", "t_shirt", "sweater", "hoodie",
    "jacket", "coat", "pants",
    "shorts", "athletic_wear", "shoes",
    "hat", "socks", "accessory",
]

PRIMARY_COLORS = [
    "black", "white", "gray", "navy", "blue", "green",
    "red", "burgundy", "brown", "tan/beige",
    "purple", "pink", "yellow", "orange",
]

PATTERNS = [
    "solid", "striped", "plaid/check", "floral",
    "geometric", "graphic/logo", "tie-dye",
    "camouflage", "texture_only",
]

FORMALITY = [
    "casual", "formal", "pajamas/loungewear", "sportswear",
]

SEASONS = [
    "all-season", "summer/warm", "winter/cold",
    "rain", "windproof", "insulated",
]

FABRICS = [
    "cotton", "wool", "merino", "polyester", "nylon", "denim",
    "linen", "leather", "synthetic/tech_fabric",
]

WEIGHTS = [
    "lightweight", "mid-weight", "heavyweight",
]


ALL_CATEGORIES = {
    "article_type": ARTICLE_TYPE,
    "primary_color": PRIMARY_COLORS,
    "pattern": PATTERNS,
    "formality": FORMALITY,
    "season": SEASONS,
    # "fabric": FABRICS,
    # "weight": WEIGHTS,
}