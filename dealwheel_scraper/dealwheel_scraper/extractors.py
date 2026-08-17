"""
Raw extraction from a PakWheels ad detail page. Spiders only call
extract_listing_data(response) — no cleaning/typing happens here, that's
CleaningPipeline's job (per the "spider only scrapes" split requested).

Three layers, each only filling in what the previous one missed:
  1. JSON-LD (primary) — mirrors the field names the old BeautifulSoup
     scraper used successfully.
  2. The on-page spec list (#scroll_car_detail) — backfills mileage, fuel,
     transmission, color, body type, engine capacity, year if JSON-LD didn't
     have them. Never used to invent new DB columns — only the separate
     feature list (.car-feature-list) drives dynamic feature_* columns.
     registered_in and assembly (Local/Imported) are read directly from this
     list too — JSON-LD doesn't carry them, so they're always spec-list-sourced.
  3. The <meta name="description"> tag and the <title> tag — used as a last
     resort ONLY for whatever's still missing after 1+2, since some listing
     templates apparently ship with no JSON-LD and an on-page structure that
     doesn't match #scroll_car_detail either (both engine cc/color/mileage/
     transmission from the description sentence, and a "Brand Model ..."
     title-based guess for brand/model/year).
"""
from __future__ import annotations

import json
import logging
import re

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

LISTING_ID_RE = re.compile(r"-(\d+)/?(?:[?#].*)?$")

_SPEC_FALLBACK_MAP = {
    "mileage_raw": ["Mileage"],
    "fuel_type": ["Fuel"],
    "transmission": ["Transmission"],
    "color": ["Color", "Colour"],
    "body_type": ["Body Type"],
    "engine_capacity_raw": ["Engine Capacity", "Engine Type"],
    "year_raw": ["Registration Year", "Model Year"],
}

# Matches the pattern seen in PakWheels' generated meta descriptions, e.g.
# "...for PKR 42.7 lacs . Buy this 1300 cc, Silver 130200 KM Driven, Manual Car."
_META_DETAILS_RE = re.compile(
    r"(?P<engine>\d+)\s*cc,\s*(?P<color>[A-Za-z][\w\-]*)\s+(?P<mileage>[\d,]+)\s*KM\s*Driven,\s*(?P<transmission>[A-Za-z]+)\s*Car",
    re.IGNORECASE,
)
_META_PRICE_RE = re.compile(r"for\s+PKR\s+([\d,.]+\s*(?:lacs?|lakhs?|crores?|cr)?)", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def extract_listing_id(url: str) -> int | None:
    match = LISTING_ID_RE.search(url)
    return int(match.group(1)) if match else None


def extract_listing_data(response) -> dict:
    data: dict = {
        "ad_url": response.url,
        "listing_id": extract_listing_id(response.url),
    }

    if data["listing_id"] is None:
        # fallback: some ad pages expose the numeric ID via a hidden form field
        hidden_id = response.css("input#id::attr(value)").get()
        if hidden_id and hidden_id.strip().isdigit():
            data["listing_id"] = int(hidden_id.strip())

    raw_title = (response.css("title::text").get("") or "").strip()
    data["title"] = raw_title.split("|")[0].strip() if raw_title else None

    if data["title"] and "for sale in" in data["title"].lower():
        idx = data["title"].lower().rfind("for sale in")
        data["city"] = data["title"][idx + len("for sale in"):].strip()
    else:
        data["city"] = None

    json_ld = _find_json_ld(response)
    if json_ld:
        _apply_json_ld(data, json_ld)
    else:
        logger.warning("No usable JSON-LD found on %s — falling back to spec-list/meta-description.", response.url)

    specs = _extract_spec_list(response)
    _backfill_from_specs(data, specs)
    data["registered_in"] = specs.get("Registered In")
    data["assembly"] = specs.get("Assembly")

    meta_description = response.css('meta[name="description"]::attr(content)').get()
    _backfill_from_meta_description(data, meta_description)

    if not data.get("brand") or not data.get("model") or not data.get("year_raw"):
        _backfill_from_title(data)

    data["features"] = _extract_features(response)
    data["seller_comments"] = _extract_seller_comments(response)
    data["is_featured"] = _extract_is_featured(response)

    return data


def _find_json_ld(response) -> dict | None:
    for raw in response.css('script[type="application/ld+json"]::text').getall():
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        # Some templates emit multiple structured-data objects as a single
        # top-level JSON array (e.g. [BreadcrumbList, Product]) instead of
        # one object per <script> tag — check each entry, not just a bare dict.
        candidates = parsed if isinstance(parsed, list) else [parsed]
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            type_val = candidate.get("@type")
            types = type_val if isinstance(type_val, list) else [type_val]
            if any(t in ("Product", "Car", "Vehicle") for t in types):
                return candidate
    return None


def _apply_json_ld(data: dict, json_ld: dict) -> None:
    brand = json_ld.get("brand")
    if isinstance(brand, dict):
        data["brand"] = brand.get("name")
    elif isinstance(brand, str):
        data["brand"] = brand
    else:
        data["brand"] = None

    data["model"] = json_ld.get("model")
    data["year_raw"] = json_ld.get("modelDate")
    data["mileage_raw"] = json_ld.get("mileageFromOdometer")
    data["fuel_type"] = json_ld.get("fuelType")
    data["transmission"] = json_ld.get("vehicleTransmission")

    engine = json_ld.get("vehicleEngine")
    data["engine_capacity_raw"] = engine.get("engineDisplacement") if isinstance(engine, dict) else None

    data["color"] = json_ld.get("color")
    data["body_type"] = json_ld.get("bodyType")
    data["description"] = json_ld.get("description")

    offers = json_ld.get("offers")
    if isinstance(offers, dict):
        data["price_raw"] = offers.get("price")
        data["price_currency"] = offers.get("priceCurrency")


def _extract_spec_list(response) -> dict:
    """Parses the alternating key/value <li> pairs in #scroll_car_detail."""
    items = response.css("ul#scroll_car_detail li")
    texts = [" ".join(li.css("::text").getall()).strip() for li in items]
    texts = [t for t in texts if t]

    specs = {}
    # -1 (not just len(texts)) guards against an odd-length list, which the
    # original alternating-pairs approach would otherwise index out of range on
    for i in range(0, len(texts) - 1, 2):
        key, val = texts[i], texts[i + 1]
        if key:
            specs[key] = val
    return specs


def _backfill_from_specs(data: dict, specs: dict) -> None:
    for field, possible_keys in _SPEC_FALLBACK_MAP.items():
        if data.get(field):
            continue
        for key in possible_keys:
            if specs.get(key):
                data[field] = specs[key]
                break


def _backfill_from_meta_description(data: dict, meta_description: str | None) -> None:
    """Last-resort source for engine/color/mileage/transmission/price/
    description, parsed out of PakWheels' generated meta description
    sentence. Only fills fields still missing after JSON-LD + spec-list."""
    if not meta_description:
        return

    match = _META_DETAILS_RE.search(meta_description)
    if match:
        if not data.get("engine_capacity_raw"):
            data["engine_capacity_raw"] = match.group("engine")
        if not data.get("color"):
            data["color"] = match.group("color")
        if not data.get("mileage_raw"):
            data["mileage_raw"] = match.group("mileage")
        if not data.get("transmission"):
            data["transmission"] = match.group("transmission")

    if not data.get("price_raw"):
        price_match = _META_PRICE_RE.search(meta_description)
        if price_match:
            data["price_raw"] = price_match.group(1)

    if not data.get("description"):
        data["description"] = meta_description


def _backfill_from_title(data: dict) -> None:
    """Best-effort ONLY: used when JSON-LD (and, for year, the spec list too)
    didn't supply brand/model/year. Assumes the title reads
    "<Brand> <Model...> <Year> for sale in <City>" — correct for the common
    single-word-brand case (Toyota, Honda, Suzuki, MG, ...), but will
    mis-split genuine two-word brands (e.g. "Land Rover", "Mercedes Benz")
    into a wrong brand/model boundary. Worth checking those specifically if
    you deal in such brands."""
    title = data.get("title")
    if not title:
        return

    text = re.split(r"\bfor sale in\b", title, flags=re.IGNORECASE)[0].strip()

    year_match = _YEAR_RE.search(text)
    if year_match and not data.get("year_raw"):
        data["year_raw"] = year_match.group(0)
    text = _YEAR_RE.sub("", text).strip()

    tokens = text.split()
    if not tokens:
        return
    if not data.get("brand"):
        data["brand"] = tokens[0]
    if not data.get("model") and len(tokens) > 1:
        data["model"] = " ".join(tokens[1:])


def _extract_features(response) -> list[str]:
    # Keyed off the feature icon's alt text rather than the parent <ul>'s
    # class or nesting, because PakWheels uses at least two different
    # feature-list layouts: a flat <ul class="car-feature-list"> on some
    # listings, and one grouped under category headings (Interior / Safety &
    # Security / Comfort & Convenience) on others — seen on newer/dealer
    # listings, which also tend to be the ones missing JSON-LD. The icon's
    # alt attribute (alt="ABS", alt="Air Bags", ...) holds the feature name
    # reliably in both layouts.
    alts = [a.strip() for a in response.css("img.feature-icon::attr(alt)").getall() if a and a.strip()]
    if alts:
        return alts
    # Fallback for any template that doesn't use feature-icon images at all.
    return [" ".join(li.css("::text").getall()).strip() for li in response.css("ul.car-feature-list li")]


def _extract_seller_comments(response) -> str | None:
    # XPath "following" (not a CSS sibling combinator) to mirror the old
    # BeautifulSoup .find_next("div") behaviour, which isn't restricted to
    # direct siblings of the heading.
    container_html = response.xpath('//h2[@id="scroll_seller_comments"]/following::div[1]').get()
    if not container_html:
        return None
    text = BeautifulSoup(container_html, "html.parser").get_text(separator=" ", strip=True)
    return text or None


def _extract_is_featured(response) -> bool | None:
    """Whether the seller paid to feature this ad. None means the page
    didn't have the expected carousel at all (structure changed, or the
    page didn't load right) — distinct from a confirmed non-featured (False)."""
    carousel = response.css("#myCarousel")
    if not carousel:
        return None
    return carousel.css("div.featured-ribbon").get() is not None
