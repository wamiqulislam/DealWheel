"""
src/features/feature_groups.py

Reference data used by scores.py.

The feature dictionary defines equipment_score as "sum of all feat_*
columns" (unambiguous), but only gives examples for the other four
category scores ("ABS, airbags, TPMS, cameras, etc." for safety;
"AC, climate, seats, cruise, etc." for comfort; "HUD, panoramic roof,
CarPlay, etc." for luxury; "HUD, infotainment, cameras, TPMS, etc."
for technology). There's no single objectively-correct split of 35
equipment flags into those four buckets, so the groupings below are a
reasonable, explicit judgment call -- edit these lists if you'd
categorize a feature differently.

A feature can (and does, e.g. feat_head_up_display_hud) appear in
more than one category -- that's expected, since "luxury" and
"technology" genuinely overlap. It only does NOT count twice within
equipment_score, which sums the raw feat_* flags directly rather than
summing the four category scores.

Similarly, SELLER_POSITIVE / SELLER_NEGATIVE / SELLER_URGENCY are a
judgment call about which seller_* flags read as reassuring,
concerning, or urgency/negotiability signals respectively. Flags that
are purely informational (fuel type, import status, army-officer
provenance, contact hours) are deliberately left out of all three --
they stay as standalone boolean columns without feeding a composite
score.
"""

SAFETY_FEATURES = [
    "feat_abs",
    "feat_air_bags",
    "feat_tyre_pressure_monitoring_system_tpms",
    "feat_rear_camera",
    "feat_front_camera",
    "feat_360_camera",
    "feat_traction_control",
    "feat_immobilizer_key",
    "feat_parking_sensors",
    "feat_front_fog_lights",
    "feat_led_headlights",
    "feat_drls",
]

COMFORT_FEATURES = [
    "feat_air_conditioning",
    "feat_climate_control",
    "feat_rear_ac_vents",
    "feat_power_seats",
    "feat_heated_seats",
    "feat_ventilated_seats",
    "feat_cruise_control",
    "feat_power_locks",
    "feat_keyless_entry",
    "feat_power_steering",
    "feat_power_mirrors",
    "feat_push_start",
    "feat_sun_roof",
    "feat_panoramic_sunroof",
]

LUXURY_FEATURES = [
    "feat_head_up_display_hud",
    "feat_panoramic_sunroof",
    "feat_apple_carplay",
    "feat_android_auto",
    "feat_ventilated_seats",
    "feat_heated_seats",
    "feat_paddle_shifters",
    "feat_power_seats",
    "feat_360_camera",
    "feat_sun_roof",
]

TECHNOLOGY_FEATURES = [
    "feat_head_up_display_hud",
    "feat_infotainment_system",
    "feat_rear_camera",
    "feat_front_camera",
    "feat_360_camera",
    "feat_tyre_pressure_monitoring_system_tpms",
    "feat_android_auto",
    "feat_apple_carplay",
    "feat_steering_switches",
    "feat_cruise_control",
    "feat_push_start",
    "feat_paddle_shifters",
]

# Seller flags that read as reassuring / trust-building
SELLER_POSITIVE_FLAGS = [
    "seller_genuine_condition",
    "seller_like_new",
    "seller_non_accidental",
    "seller_service_history",
    "seller_authorized_workshop",
    "seller_original_book",
    "seller_original_file",
    "seller_auction_sheet",
    "seller_new_tyres",
    "seller_token_paid",
    "seller_lifetime_token",
    "seller_sealed_engine",
]

# Seller flags that read as a concern / reduced condition or paperwork risk
SELLER_NEGATIVE_FLAGS = [
    "seller_minor_accident",
    "seller_minor_touchups",
    "seller_engine_repaired",
    "seller_engine_swapped",
    "seller_duplicate_book",
    "seller_duplicate_file",
    "seller_missing_file",
    "seller_duplicate_plate",
]

# Seller flags that signal urgency / willingness to negotiate
SELLER_URGENCY_FLAGS = [
    "seller_urgent_sale",
    "seller_price_negotiable",
    "seller_exchange_possible",
]
