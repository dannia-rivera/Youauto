#!/usr/bin/env python3
"""
USAGE
    pip install requests
    python ne_mechanics_osm.py                 # defaults to Nebraska (US-NE)
    python ne_mechanics_osm.py --state US-IA   # a different state
    python ne_mechanics_osm.py --out mydata    # custom output filename stem

OUTPUT
    <out>.csv   - one row per shop, spreadsheet-friendly
    <out>.json  - same records plus the complete raw OSM tag set (for audit)
"""

import argparse
import csv
import json
import sys
import time
from urllib.parse import urlencode

import requests

# Public Overpass mirrors. We try them in order if one is busy/unavailable.
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

# OSM "shop" values we treat as auto mechanics. Extend if you want, e.g.
# add "car_parts" for parts stores. "car_repair" is the core tag; many tire
# shops (which also do brakes/alignment) are tagged "tyres".
SHOP_TYPES = ["car_repair", "tyres"]

# Human-readable labels for the OSM service:vehicle:* sub-tags.
SERVICE_LABELS = {
    "transmission": "Transmission",
    "brake_repair": "Brakes",
    "brakes": "Brakes",
    "tyres": "Tires",
    "oil_change": "Oil change",
    "air_conditioning": "A/C",
    "battery": "Battery",
    "diagnostics": "Diagnostics",
    "car_diagnostics": "Diagnostics",
    "body_repair": "Body work",
    "painting": "Painting",
    "electrical": "Electrical",
    "exhaust": "Exhaust",
    "suspension": "Suspension",
    "wheel_alignment": "Wheel alignment",
    "glass": "Glass",
    "inspection": "Inspection",
    "tuning": "Tuning",
    "diesel_repair": "Diesel",
    "repairs": "General repairs",
    "car_repair": "General repairs",
}


def build_query(state_code: str) -> str:
    """Build an Overpass QL query for all target shops within a US state.

    state_code is an ISO 3166-2 code, e.g. "US-NE" for Nebraska. The
    area(...) filter selects the state boundary, then we grab matching
    nodes AND ways (buildings) inside it. `out center tags` returns a
    representative coordinate for ways so every result has a lat/lon.
    """
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
            time.sleep(2)  # brief pause before trying the next mirror
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
    """Pull services from service:vehicle:* tags whose value is yes/only.

    OSM encodes offered services as e.g. service:vehicle:transmission=yes.
    A value of "no" means explicitly NOT offered, so we skip those.
    """
    services = []
    for key, value in tags.items():
        if not key.startswith("service:vehicle:"):
            continue
        if value.lower() not in ("yes", "only"):
            continue
        sub = key.split("service:vehicle:", 1)[1]
        services.append(SERVICE_LABELS.get(sub, sub.replace("_", " ").title()))
    # Deduplicate while preserving order
    seen = set()
    return [s for s in services if not (s in seen or seen.add(s))]


def is_transmission_specialist(tags: dict, services: list) -> bool:
    """Heuristic: name mentions transmission, or transmission is the ONLY
    vehicle service flagged, indicating a dedicated shop rather than a
    general garage that happens to do transmissions."""
    name = tags.get("name", "").lower()
    if "transmission" in name:
        return True
    if tags.get("service:vehicle:transmission", "").lower() == "only":
        return True
    if services == ["Transmission"]:
        return True
    return False


# ── Nominatim reverse geocoding to fill in missing addresses ──────────

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"

# Nominatim's address dict uses different keys depending on place size.
# We try these in order to find the most specific locality name.
CITY_KEYS = ("city", "town", "village", "hamlet", "municipality", "county")


def _nominatim_reverse(lat: float, lon: float, max_retries: int = 4) -> dict | None:
    """Call Nominatim reverse geocoding with retry+backoff on 429.
    Returns the 'address' sub-dict or None."""
    params = {"format": "json", "lat": lat, "lon": lon, "addressdetails": 1}
    url = f"{NOMINATIM_URL}?{urlencode(params)}"
    for attempt in range(max_retries):
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": "YouAuto/1.0 (mechanic_scrape; OSM data enrichment)"},
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


def enrich_addresses(records: list, delay: float = 2.5) -> list:
    """For every record missing a city, reverse-geocode via Nominatim and
    fill in any missing address fields (city, state, postcode, street, etc.).

    Respects Nominatim's 1 req/s rate limit with a configurable *delay*.
    Results are cached by a rounded-coordinate key so duplicate locations
    only trigger one API call.
    """
    cache: dict[tuple[int, int], dict | None] = {}
    enriched = 0
    total_missing = sum(1 for r in records if not r["city"])

    if total_missing == 0:
        return records

    print(f"\nEnriching {total_missing} records missing city via Nominatim…",
          file=sys.stderr)

    for i, r in enumerate(records):
        if r["city"]:
            continue

        # Round to ~10 m to deduplicate nearby points
        cache_key = (round(r["lat"] * 10000), round(r["lon"] * 10000))
        if cache_key not in cache:
            time.sleep(delay)
            cache[cache_key] = _nominatim_reverse(r["lat"], r["lon"])

        addr = cache[cache_key]
        if addr is None:
            continue

        # Fill city
        if not r["city"]:
            locality = _extract_locality(addr)
            if locality:
                r["city"] = locality

        # Fill other missing fields
        if not r["state"]:
            r["state"] = addr.get("state", "")
        if not r["postcode"]:
            r["postcode"] = addr.get("postcode", "")
        if not r["housenumber"]:
            r["housenumber"] = addr.get("house_number", "")
        if not r["street"]:
            r["street"] = addr.get("road", addr.get("pedestrian", ""))

        # Rebuild the full address string
        r["address"] = assemble_address_from_parts(r)

        enriched += 1
        if enriched % 50 == 0:
            print(f"  ... {enriched}/{total_missing} enriched", file=sys.stderr)

    print(f"  ✓ enriched {enriched} records", file=sys.stderr)
    return records


def assemble_address_from_parts(r: dict) -> str:
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


def parse_elements(data: dict) -> list:
    """Transform raw Overpass elements into flat, tidy records."""
    records = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        # Ways carry their coordinate under "center"; nodes carry lat/lon directly.
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")

        services = extract_services(tags)
        record = {
            "osm_type": el.get("type"),
            "osm_id": el.get("id"),
            "name": tags.get("name", ""),
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
            "is_transmission_specialist": is_transmission_specialist(tags, services),
            "osm_url": f"https://www.openstreetmap.org/{el.get('type')}/{el.get('id')}",
            "raw_tags": tags,  # kept for the JSON output / auditing
        }
        records.append(record)

    # Sort: named shops first (alphabetical), unnamed ones last.
    records.sort(key=lambda r: (r["name"] == "", r["name"].lower()))
    return records


def write_csv(records: list, path: str) -> None:
    """Write the flat records to CSV (excludes the bulky raw_tags field)."""
    columns = [
        "name", "shop_type", "address", "housenumber", "street", "city",
        "state", "postcode", "lat", "lon", "phone", "website",
        "opening_hours", "services", "is_transmission_specialist",
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
    transmission = sum(1 for r in records if r["is_transmission_specialist"])
    print("\n--- Summary ---", file=sys.stderr)
    print(f"Total shops found:            {total}", file=sys.stderr)
    print(f"  with a name:                {named}", file=sys.stderr)
    print(f"  with a parsed address:      {with_addr}", file=sys.stderr)
    print(f"  with tagged services:       {with_services}", file=sys.stderr)
    print(f"  flagged transmission shops: {transmission}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--state", default="US-NE",
                        help="ISO 3166-2 state code (default: US-NE for Nebraska)")
    parser.add_argument("--out", default="ne_mechanics",
                        help="Output filename stem (default: ne_mechanics)")
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