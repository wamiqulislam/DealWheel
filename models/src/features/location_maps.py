"""
src/features/location_maps.py

Reference data used by location_features.py.

LARGE_CITIES
------------
Lookup table for is_large_city, as called for by the feature
dictionary ("Lookup table mapping major Pakistani cities"). This is a
judgment call, not scraped data -- it's the set of Pakistani cities
that are provincial capitals, major metro areas, or otherwise have a
large, liquid used-car market on PakWheels. Matching is done against
the *cleaned* city value (see text_cleaning.py), so casing/whitespace
variants of the same city are already unified before this lookup
runs.

Edit this set freely -- it directly controls one boolean feature and
nothing else depends on its exact contents.
"""

LARGE_CITIES = {
    "Karachi",
    "Lahore",
    "Islamabad",
    "Rawalpindi",
    "Faisalabad",
    "Multan",
    "Peshawar",
    "Quetta",
    "Sialkot",
    "Gujranwala",
    "Hyderabad",
    "Sargodha",
    "Bahawalpur",
    "Sukkur",
    "Abbottabad",
    "Mardan",
}
