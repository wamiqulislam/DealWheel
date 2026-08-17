"""
color_maps.py

Reference data used by color_cleaner.py:
    - CANONICAL_COLORS: the standard color set
    - SPECIAL_COLORS: color names that map to a canonical color but don't
      contain the canonical word itself (e.g. "olive" -> "Green")
    - URDU_COLORS: Urdu color words -> canonical color
    - SPELLING_FIXES: common misspellings -> correct spelling

Only add a color word to SPECIAL_COLORS if the canonical color word is
NOT present in the raw value (e.g. "metallic blue" already contains
"blue", so it does not need an entry here).
"""

CANONICAL_COLORS = [
    "white", "black", "silver", "grey", "gray", "blue", "red", "green",
    "brown", "beige", "gold", "yellow", "orange", "purple", "pink", "bronze",
]

SPECIAL_COLORS = {
    # RED
    "wine": "Red", "wine red": "Red", "redwine": "Red", "red wine": "Red",
    "burgundy": "Red", "burgandy": "Red", "burgendy": "Red",
    "maroon": "Red", "mahroon": "Red", "mehroon": "Red", "mehron": "Red",
    "mehnroon": "Red", "mahrun": "Red", "bordeaux": "Red", "carmine": "Red",
    "carnelian": "Red", "scarlet": "Red", "ruby": "Red", "cherry": "Red",
    "vine": "Red",

    # GREEN
    "olive": "Green", "emerald": "Green", "jade": "Green", "forest": "Green",
    "mint": "Green", "khaki": "Green", "army": "Green", "british": "Green",
    "verde": "Green", "sage": "Green",

    # GREY
    "graphite": "Grey", "charcoal": "Grey", "gunmetal": "Grey",
    "gun metal": "Grey", "gunmatalic": "Grey", "gun matalic": "Grey",
    "gun matallic": "Grey", "gun matelic": "Grey", "gun mettalic": "Grey",
    "gun mattelic": "Grey", "titanium": "Grey", "steel": "Grey", "ash": "Grey",
    "smoke": "Grey", "space": "Grey", "slate": "Grey",

    # WHITE
    "ivory": "White", "porcelain": "White", "alabaster": "White",
    "opalite": "White", "howlite": "White", "taffeta": "White",
    "tafetta": "White", "teffeta": "White", "tetta": "White",
    "superwhite": "White",

    # BLUE
    "navy": "Blue", "indigo": "Blue", "turquoise": "Blue", "aqua": "Blue",
    "cyan": "Blue", "azure": "Blue", "cavansite": "Blue", "tanzanite": "Blue",
    "neptune": "Blue", "portimao": "Blue", "scuba": "Blue", "orion": "Blue",
    "astra": "Blue", "royal": "Blue",

    # PURPLE
    "violet": "Purple", "lilac": "Purple", "lavender": "Purple",
    "mauve": "Purple", "amethyst": "Purple",

    # PINK
    "rose": "Pink", "rosemist": "Pink", "rose mist": "Pink",
    "magenta": "Pink", "shalimar": "Pink",

    # BROWN
    "mocha": "Brown", "coffee": "Brown", "cappuccino": "Brown",
    "cinnamon": "Brown", "plum": "Brown",

    # BEIGE
    "sand": "Beige", "cashmere": "Beige", "flaxen": "Beige",

    # GOLD
    "golden": "Gold", "champagne": "Gold", "dorado": "Gold",
    "sun gold": "Gold", "sunshine gold": "Gold",

    # ORANGE
    "copper": "Orange",

    # BRONZE
    "copper bronze": "Bronze",
}

URDU_COLORS = {
    "سفید": "White", "وائٹ": "White",
    "کالا": "Black", "کالی": "Black", "سیاہ": "Black", "بلیک": "Black",
    "چاندی": "Silver", "نقرئی": "Silver", "سلور": "Silver",
    "سرمئی": "Grey", "گرے": "Grey",
    "نیلا": "Blue", "نیلی": "Blue", "بلیو": "Blue", "فیروزی": "Blue",
    "سرخ": "Red", "لال": "Red", "ریڈ": "Red", "مہرون": "Red",
    "مہروں": "Red", "شرابی": "Red",
    "سبز": "Green", "ہرا": "Green", "ہری": "Green", "گرین": "Green",
    "بھورا": "Brown", "بھوری": "Brown", "براؤن": "Brown",
    "بیج": "Beige",
    "سنہری": "Gold", "سونا": "Gold", "گولڈ": "Gold",
    "پیلا": "Yellow", "پیلی": "Yellow",
    "نارنجی": "Orange", "اورنج": "Orange",
    "جامنی": "Purple", "بنفشی": "Purple", "پرپل": "Purple",
    "گلابی": "Pink", "پنک": "Pink", "روز": "Pink",
    "برونز": "Bronze",
}

SPELLING_FIXES = {
    # WHITE
    "wite": "white", "whie": "white", "whilte": "white",
    "wahite": "white", "whitle": "white",

    # BLACK
    "blak": "black", "blk": "black",

    # GREY
    "gery": "grey", "gary": "grey", "gre": "grey", "gray": "grey",
    "gr ey": "grey",

    # BLUE
    "bule": "blue", "blu": "blue", "bleu": "blue", "bilu": "blue",

    # RED
    "read": "red",

    # GREEN
    "greed": "green", "greene": "green", "gareen": "green", "grern": "green",

    # BEIGE
    "beig": "beige", "beign": "beige", "bage": "beige", "beage": "beige",
    "beaje": "beige", "beigh": "beige", "baige": "beige", "baje": "beige",

    # SILVER
    "sliver": "silver", "sllver": "silver",

    # PURPLE
    "purle": "purple",

    # PINK
    "roze": "rose",

    # GOLD
    "goldan": "gold",

    # BRONZE
    "bronze": "bronze",
}
