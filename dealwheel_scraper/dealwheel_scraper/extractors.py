"""
Raw extraction from a PakWheels ad detail page. Spiders only call
extract_listing_data(response) — no cleaning/typing happens here, that's
CleaningPipeline's job (per the "spider only scrapes" split requested).

JSON-LD is the primary source (mirrors the field names the old BeautifulSoup
scraper used successfully: brand, model, modelDate, mileageFromOdometer,
fuelType, vehicleTransmission, vehicleEngine.engineDisplacement, color,
bodyType, offers.price/priceCurrency, description). The on-page spec list
(#scroll_car_detail) is used only as a fallback to backfill anything missing
from JSON-LD, not as a source of new arbitrary DB columns — only the
feature list (.car-feature-list) drives dynamic feature_* columns.
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

    specs = _extract_spec_list(response)
    _backfill_from_specs(data, specs)

    data["features"] = _extract_features(response)
    data["seller_comments"] = _extract_seller_comments(response)

    return data


def _find_json_ld(response) -> dict | None:
    for raw in response.css('script[type="application/ld+json"]::text').getall():
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(parsed, dict):
            continue
        type_val = parsed.get("@type")
        types = type_val if isinstance(type_val, list) else [type_val]
        if any(t in ("Product", "Car", "Vehicle") for t in types):
            return parsed
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


def _extract_features(response) -> list[str]:
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
