#!/usr/bin/env python3
"""
ne_parts_osm.py
===============

Collate a database of auto parts stores in Nebraska (or any US state) from
OpenStreetMap via the Overpass API.

For each store it captures:
    - name
    - brand (OSM brand tag — useful for chains like AutoZone, NAPA, O'Reilly)
    - address (assembled from addr:* tags, plus the raw components)
    - latitude / longitude
    - phone, website, opening hours
    - a list of services / specialities derived from OSM tags
    - flags for chain stores, delivery, and 24/7 availability

WHY OPENSTREETMAP
    - Free, no API key required.
    - Data is licensed under the ODbL: you may reuse and redistribute it,
      as long as you attribute "© OpenStreetMap contributors".
    - Parts chains (AutoZone, O'Reilly, NAPA, Advance Auto) tend to be
      well-mapped in metro areas; rural independent stores are sparser.

USAGE
    pip install requests
    python ne_parts_osm.py                 # defaults to Nebraska (US-NE)
    python ne_parts_osm.py --state US-IA   # a different state
    python ne_parts_osm.py --out mydata    # custom output filename stem
    python ne_parts_osm.py --no-enrich     # skip Nominatim address fill-in

OUTPUT
    <out>.csv   - one row per store, spreadsheet-friendly
    <out>.json  - same records plus the complete raw OSM tag set (for audit)

POLITE USAGE
    The public Overpass endpoints are a shared, donated resource. Run this
    infrequently (the whole state is one query) and don't hammer it in a loop.
"""

import argparse
import csv
import json
import sys
import time
from urllib.parse import urlencode

import requests

# Public Overpass mirrors, tried in order if one is busy/unavailable.
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

# OSM "shop" values we treat as auto parts stores.
SHOP_TYPES = ["car_parts", "car_accessories"]

# Human-readable labels for OSM service / speciality tags.
SERVICE_LABELS = {
    "car_parts": "Auto parts",
    "car_accessories": "Accessories",
    "tyres": "Tires",
    "battery": "Batteries",
    "oil": "Oil & fluids",
    "paint": "Paint & body supplies",
    "tools": "Tools",
    "performance": "Performance parts",
    "audio": "Car audio",
    "alarm": "Alarms & security",
    "air_conditioning": "A/C parts",
    "brakes": "Brake parts",
    "exhaust": "Exhaust parts",
    "suspension": "Suspension parts",
    "electrical": "Electrical parts",
    "filters": "Filters",
    "transmission": "Transmission parts",
    "radiator": "Radiators",
    "wipers": "Wipers",
    "lighting": "Lighting",
    "chemicals": "Chemicals & fluids",
    "truck_parts": "Truck parts",
    "motorcycle_parts": "Motorcycle parts",
    "agricultural_parts": "Agricultural parts",
    "used_parts": "Used parts",
    "recycled_parts": "Recycled parts",
    "delivery": "Delivery",
    "charging_station": "EV charging",
}

# Well-known US parts chains for the is_chain heuristic.
CHAIN_BRANDS = {
    "autozone", "oreilly", "o'reilly", "o reilly", "oreilly auto parts",
    "advance auto parts", "advance auto", "napa", "napa auto parts",
    "carquest", "carquest auto parts", "pep boys", "pep boys auto",
    "bumper to bumper", "fisher auto parts", "arnold motor supply",
    "keystone automotive", "lkq", "4 wheel parts", "jegs", "summit racing",
}


def build_query(state_code: str) -> str:
    """Build an Overpass QL query for all target shops within a US state."""
    shop_filters = "\n".join(
        f'  node["shop"="{s}"](area.state);\n'
        f'  way["shop"="{s}"](area.state);'
        for s in SHOP_TYPES
    )
    return f"""
[out:json][timeout:180];
area["ISO3166-2"="{state_code}"][admin_level=4]->.state;
(
{shop_filters}
);
out center tags;
"""


def fetch(query: str) -> dict:
    """POST the query to Overpass, trying each mirror until one responds."""
    last_error = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            print(f"Querying {endpoint} ...", file=sys.stderr)
            resp = requests.post(endpoint, data={"data": query}, timeout=200)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            print(f"  failed: {exc}", file=sys.stderr)
            last_error = exc
            time.sleep(2)
    raise RuntimeError(f"All Overpass endpoints failed. Last error: {last_error}")


def assemble_address(tags: dict) -> str:
    """Join addr:* tags into a single human-readable address string."""
    house = tags.get("addr:housenumber", "")
    street = tags.get("addr:street", "")
    line1 = " ".join(p for p in [house, street] if p).strip()
    city = tags.get("addr:city", "")
    state = tags.get("addr:state", "")
    postcode = tags.get("addr:postcode", "")
    city_line = ", ".join(p for p in [city, state] if p)
    if postcode:
        city_line = f"{city_line} {postcode}".strip()
    return ", ".join(p for p in [line1, city_line] if p)


def extract_services(tags: dict) -> list:
    """Pull services / specialities from service:vehicle:* and similar tags."""
    services = []
    for key, value in tags.items():
        for prefix in ("service:vehicle:", "service:", "speciality:"):
            if key.startswith(prefix):
                sub = key.split(prefix, 1)[1]
                if value.lower() in ("yes", "only"):
                    services.append(
                        SERVICE_LABELS.get(sub, sub.replace("_", " ").title())
                    )
                break
    seen = set()
    return [s for s in services if not (s in seen or seen.add(s))]


def is_chain(name: str, brand: str) -> bool:
    """Heuristic: recognised brand name or the store name matches a chain."""
    combined = f"{brand} {name}".lower()
    for c in CHAIN_BRANDS:
        if c in combined:
            return True
    return False


def is_24_7(tags: dict) -> bool:
    """True if opening_hours advertises round-the-clock availability."""
    hours = tags.get("opening_hours", "").lower()
    return "24/7" in hours or "24 hours" in hours or "00:00-24:00" in hours


# ── Nominatim reverse geocoding for address enrichment ──────────────────────

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
CITY_KEYS = ("city", "town", "village", "hamlet", "municipality", "county")


def _nominatim_reverse(lat: float, lon: float, max_retries: int = 4) -> dict | None:
    """Call Nominatim reverse geocoding with retry+backoff on 429."""
    params = {"format": "json", "lat": lat, "lon": lon, "addressdetails": 1}
    url = f"{NOMINATIM_URL}?{urlencode(params)}"
    for attempt in range(max_retries):
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": "YouAuto/1.0 (parts_scrape; OSM data enrichment)"},
                timeout=30,
            )
            if resp.status_code == 429:
                wait = (attempt + 1) * 3
                print(f"  rate-limited, retrying in {wait}s…", file=sys.stderr)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            return data.get("address") or None
        except requests.RequestException as exc:
            print(f"  Nominatim error ({lat:.5f},{lon:.5f}): {exc}", file=sys.stderr)
            return None
    print(f"  Nominatim: gave up after {max_retries} retries", file=sys.stderr)
    return None


def _extract_locality(address: dict) -> str:
    """Pull the best city/town/village name from a Nominatim address dict."""
    for key in CITY_KEYS:
        val = address.get(key, "").strip()
        if val:
            return val
    return ""


def _assemble_from_parts(r: dict) -> str:
    """Rebuild the address string from (possibly enriched) components."""
    house = r.get("housenumber", "")
    street = r.get("street", "")
    line1 = " ".join(p for p in [house, street] if p).strip()
    city = r.get("city", "")
    state = r.get("state", "")
    postcode = r.get("postcode", "")
    city_line = ", ".join(p for p in [city, state] if p)
    if postcode:
        city_line = f"{city_line} {postcode}".strip()
    return ", ".join(p for p in [line1, city_line] if p)


def enrich_addresses(records: list, delay: float = 2.5) -> list:
    """For every record missing a city, reverse-geocode via Nominatim."""
    cache: dict[tuple[int, int], dict | None] = {}
    enriched = 0
    total_missing = sum(1 for r in records if not r["city"])

    if total_missing == 0:
        return records

    print(f"\nEnriching {total_missing} records missing city via Nominatim…",
          file=sys.stderr)

    for r in records:
        if r["city"]:
            continue

        cache_key = (round(r["lat"] * 10000), round(r["lon"] * 10000))
        if cache_key not in cache:
            time.sleep(delay)
            cache[cache_key] = _nominatim_reverse(r["lat"], r["lon"])

        addr = cache[cache_key]
        if addr is None:
            continue

        if not r["city"]:
            locality = _extract_locality(addr)
            if locality:
                r["city"] = locality
        if not r["state"]:
            r["state"] = addr.get("state", "")
        if not r["postcode"]:
            r["postcode"] = addr.get("postcode", "")
        if not r["housenumber"]:
            r["housenumber"] = addr.get("house_number", "")
        if not r["street"]:
            r["street"] = addr.get("road", addr.get("pedestrian", ""))

        r["address"] = _assemble_from_parts(r)
        enriched += 1
        if enriched % 50 == 0:
            print(f"  ... {enriched}/{total_missing} enriched", file=sys.stderr)

    print(f"  ✓ enriched {enriched} records", file=sys.stderr)
    return records


# ── Element parsing ─────────────────────────────────────────────────────────

def parse_elements(data: dict) -> list:
    """Transform raw Overpass elements into flat, tidy records."""
    records = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")

        services = extract_services(tags)
        name = tags.get("name", "")
        brand = tags.get("brand", "")

        record = {
            "osm_type": el.get("type"),
            "osm_id": el.get("id"),
            "name": name,
            "brand": brand,
            "shop_type": tags.get("shop", ""),
            "address": assemble_address(tags),
            "housenumber": tags.get("addr:housenumber", ""),
            "street": tags.get("addr:street", ""),
            "city": tags.get("addr:city", ""),
            "state": tags.get("addr:state", ""),
            "postcode": tags.get("addr:postcode", ""),
            "lat": lat,
            "lon": lon,
            "phone": tags.get("phone", tags.get("contact:phone", "")),
            "website": tags.get("website", tags.get("contact:website", "")),
            "opening_hours": tags.get("opening_hours", ""),
            "services": "; ".join(services),
            "is_chain": is_chain(name, brand),
            "available_24_7": is_24_7(tags),
            "osm_url": f"https://www.openstreetmap.org/{el.get('type')}/{el.get('id')}",
            "raw_tags": tags,  # kept for JSON output / auditing
        }
        records.append(record)

    records.sort(key=lambda r: (r["name"] == "", r["name"].lower()))
    return records


def write_csv(records: list, path: str) -> None:
    """Write the flat records to CSV (excludes the bulky raw_tags field)."""
    columns = [
        "name", "brand", "shop_type", "address", "housenumber", "street",
        "city", "state", "postcode", "lat", "lon", "phone", "website",
        "opening_hours", "services", "is_chain", "available_24_7",
        "osm_type", "osm_id", "osm_url",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for r in records:
            writer.writerow(r)


def write_json(records: list, path: str) -> None:
    """Write full records, including raw OSM tags, for auditing."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def summarize(records: list) -> None:
    """Print a short summary to the console."""
    total = len(records)
    named = sum(1 for r in records if r["name"])
    with_addr = sum(1 for r in records if r["address"])
    with_services = sum(1 for r in records if r["services"])
    chains = sum(1 for r in records if r["is_chain"])
    day_night = sum(1 for r in records if r["available_24_7"])

    print("\n--- Summary ---", file=sys.stderr)
    print(f"Total parts stores found:     {total}", file=sys.stderr)
    print(f"  with a name:                {named}", file=sys.stderr)
    print(f"  with a parsed address:      {with_addr}", file=sys.stderr)
    print(f"  with tagged services:       {with_services}", file=sys.stderr)
    print(f"  flagged as chain stores:    {chains}", file=sys.stderr)
    print(f"  advertising 24/7:           {day_night}", file=sys.stderr)

    # Brand breakdown
    brands = {}
    for r in records:
        b = r["brand"].strip() or r["name"].strip()
        if b:
            brands[b] = brands.get(b, 0) + 1
    if brands:
        print("  top brands:", file=sys.stderr)
        for b, n in sorted(brands.items(), key=lambda kv: -kv[1])[:10]:
            print(f"    {n:>4}  {b}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--state", default="US-NE",
                        help="ISO 3166-2 state code (default: US-NE for Nebraska)")
    parser.add_argument("--out", default="ne_parts",
                        help="Output filename stem (default: ne_parts)")
    parser.add_argument("--no-enrich", action="store_true",
                        help="Skip Nominatim reverse-geocoding to fill missing addresses")
    args = parser.parse_args()

    query = build_query(args.state)
    data = fetch(query)
    records = parse_elements(data)

    if not args.no_enrich:
        records = enrich_addresses(records)

    csv_path = f"{args.out}.csv"
    json_path = f"{args.out}.json"
    write_csv(records, csv_path)
    write_json(records, json_path)

    summarize(records)
    print(f"\nWrote {csv_path} and {json_path}", file=sys.stderr)
    print("Remember to attribute: © OpenStreetMap contributors (ODbL).",
          file=sys.stderr)


if __name__ == "__main__":
    main()
