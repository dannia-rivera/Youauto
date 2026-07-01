#!/usr/bin/env python3
"""
ne_towing_osm.py
================

Collate a database of towing / recovery / roadside-assistance services in
Nebraska (or any US state) from OpenStreetMap via the Overpass API.

For each operator it captures:
    - name
    - address (assembled from addr:* tags, plus the raw components)
    - latitude / longitude
    - phone, website, opening hours
    - a list of services (towing + any vehicle services also tagged)
    - how it was tagged in OSM (data-quality signal)
    - flags for 24/7 availability and heavy-duty capability

>>> IMPORTANT CAVEAT ABOUT TOWING DATA IN OSM <<<
    OpenStreetMap has NO agreed-upon tag for towing companies. A formal
    proposal (amenity=towing) exists but is not yet adopted, so in the wild
    towing operators are tagged inconsistently:
        - shop=car_repair            (most common; often with no actual repair)
        - service:vehicle:towing=yes (a service flag on some shops)
        - amenity=towing / shop=towing / office=towing / towing=yes  (rare)
    This script queries ALL of those, plus a name filter for "towing"/"wrecker".
    Even so, expect SPARSE and PATCHY coverage compared with repair shops.

    Because of that sparseness, for towing specifically the cleaner route is
    often the ReferenceUSA / Data Axle library export filtered on
    NAICS 488410 "Motor Vehicle Towing" -- it will be far more complete.
    Use this OSM script as a free, redistributable supplement.

USAGE
    pip install requests
    python ne_towing_osm.py                 # defaults to Nebraska (US-NE)
    python ne_towing_osm.py --state US-IA   # a different state
    python ne_towing_osm.py --out mydata    # custom output filename stem

OUTPUT
    <out>.csv   - one row per operator, spreadsheet-friendly
    <out>.json  - same records plus the complete raw OSM tag set (for audit)

POLITE USAGE
    The public Overpass endpoints are a shared, donated resource. Run this
    infrequently (the whole state is one query); don't loop over it.
"""

import argparse
import csv
import json
import sys
import time

import requests

# Public Overpass mirrors, tried in order if one is busy/unavailable.
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

# Human-readable labels for service:* sub-tags we may encounter.
SERVICE_LABELS = {
    # towing-specific (some from the amenity=towing proposal)
    "towing": "Towing",
    "light_duty": "Light-duty towing",
    "medium_duty": "Medium-duty towing",
    "heavy_duty": "Heavy-duty towing",
    "motorcycle": "Motorcycle towing",
    "recovery": "Recovery",
    "winching": "Winching",
    "flatbed": "Flatbed",
    "roadside_assistance": "Roadside assistance",
    "jump_start": "Jump start",
    "lockout": "Lockout",
    "fuel_delivery": "Fuel delivery",
    "tyre_change": "Tire change",
    # general vehicle services (present when a repair shop also tows)
    "car_repair": "General repairs",
    "repairs": "General repairs",
    "brake_repair": "Brakes",
    "tyres": "Tires",
    "oil_change": "Oil change",
    "diagnostics": "Diagnostics",
    "body_repair": "Body work",
    "battery": "Battery",
}


def build_query(state_code: str) -> str:
    """Build an Overpass QL query for towing operators within a US state.

    state_code is an ISO 3166-2 code, e.g. "US-NE" for Nebraska.

    Towing has no canonical tag, so we union several possibilities. `nwr`
    matches nodes, ways AND relations in one clause. Overpass sets are keyed
    by element identity, so an operator matching multiple clauses appears
    only once. `out center tags` gives every result a coordinate.
    """
    return f"""
[out:json][timeout:180];
area["ISO3166-2"="{state_code}"][admin_level=4]->.state;
(
  nwr["service:vehicle:towing"~"^(yes|only)$"](area.state);
  nwr["amenity"="towing"](area.state);
  nwr["shop"="towing"](area.state);
  nwr["office"="towing"](area.state);
  nwr["towing"~"^(yes|only)$"](area.state);
  nwr["service:towing"](area.state);
  nwr["name"~"towing|wrecker",i](area.state);
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
    """Collect services from service:vehicle:* and service:towing:* tags
    whose value is yes/only, plus a bare towing=yes."""
    services = []
    for key, value in tags.items():
        if not (key.startswith("service:vehicle:")
                or key.startswith("service:towing:")):
            continue
        if value.lower() not in ("yes", "only"):
            continue
        sub = key.split(":")[-1]
        services.append(SERVICE_LABELS.get(sub, sub.replace("_", " ").title()))
    # A plain towing=yes with no sub-detail still means "Towing".
    if tags.get("towing", "").lower() in ("yes", "only") and "Towing" not in services:
        services.append("Towing")
    seen = set()
    return [s for s in services if not (s in seen or seen.add(s))]


def osm_category(tags: dict) -> str:
    """Report HOW this operator was tagged -- a data-quality signal, since
    towing is tagged so inconsistently in OSM."""
    if tags.get("amenity") == "towing":
        return "amenity=towing"
    if tags.get("shop") == "towing":
        return "shop=towing"
    if tags.get("office") == "towing":
        return "office=towing"
    if tags.get("shop") == "car_repair":
        return "shop=car_repair (repair shop that tows / mistagged)"
    if tags.get("towing", "").lower() in ("yes", "only"):
        return "towing=yes"
    if tags.get("service:vehicle:towing", "").lower() in ("yes", "only"):
        return "service:vehicle:towing=yes"
    return "name match only (verify manually)"


def is_24_7(tags: dict) -> bool:
    """True if opening_hours advertises round-the-clock availability."""
    hours = tags.get("opening_hours", "").lower()
    return "24/7" in hours or "24 hours" in hours or "00:00-24:00" in hours


def is_heavy_duty(tags: dict, services: list) -> bool:
    """Heuristic for heavy-duty capability from tags, services, or name."""
    if tags.get("service:towing:heavy_duty", "").lower() in ("yes", "only"):
        return True
    if "Heavy-duty towing" in services:
        return True
    if "heavy" in tags.get("name", "").lower():
        return True
    return False


def parse_elements(data: dict) -> list:
    """Transform raw Overpass elements into flat, tidy records."""
    records = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")

        services = extract_services(tags)
        record = {
            "osm_type": el.get("type"),
            "osm_id": el.get("id"),
            "name": tags.get("name", ""),
            "osm_category": osm_category(tags),
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
            "available_24_7": is_24_7(tags),
            "heavy_duty": is_heavy_duty(tags, services),
            "osm_url": f"https://www.openstreetmap.org/{el.get('type')}/{el.get('id')}",
            "raw_tags": tags,
        }
        records.append(record)

    records.sort(key=lambda r: (r["name"] == "", r["name"].lower()))
    return records


def write_csv(records: list, path: str) -> None:
    """Write the flat records to CSV (excludes the bulky raw_tags field)."""
    columns = [
        "name", "osm_category", "address", "housenumber", "street", "city",
        "state", "postcode", "lat", "lon", "phone", "website",
        "opening_hours", "services", "available_24_7", "heavy_duty",
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
    """Print a short summary, including a breakdown by how each was tagged."""
    total = len(records)
    named = sum(1 for r in records if r["name"])
    with_addr = sum(1 for r in records if r["address"])
    with_phone = sum(1 for r in records if r["phone"])
    day_night = sum(1 for r in records if r["available_24_7"])

    print("\n--- Summary ---", file=sys.stderr)
    print(f"Total towing operators found: {total}", file=sys.stderr)
    print(f"  with a name:                {named}", file=sys.stderr)
    print(f"  with a parsed address:      {with_addr}", file=sys.stderr)
    print(f"  with a phone number:        {with_phone}", file=sys.stderr)
    print(f"  advertising 24/7:           {day_night}", file=sys.stderr)

    # Tag-source breakdown highlights how messy the underlying data is.
    print("  tagged as:", file=sys.stderr)
    counts = {}
    for r in records:
        counts[r["osm_category"]] = counts.get(r["osm_category"], 0) + 1
    for cat, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"    {n:>4}  {cat}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--state", default="US-NE",
                        help="ISO 3166-2 state code (default: US-NE for Nebraska)")
    parser.add_argument("--out", default="ne_towing",
                        help="Output filename stem (default: ne_towing)")
    args = parser.parse_args()

    query = build_query(args.state)
    data = fetch(query)
    records = parse_elements(data)

    csv_path = f"{args.out}.csv"
    json_path = f"{args.out}.json"
    write_csv(records, csv_path)
    write_json(records, json_path)

    summarize(records)
    print(f"\nWrote {csv_path} and {json_path}", file=sys.stderr)
    print("Because OSM towing data is sparse, cross-check against NAICS 488410 "
          "if you need completeness.", file=sys.stderr)
    print("Remember to attribute: © OpenStreetMap contributors (ODbL).",
          file=sys.stderr)


if __name__ == "__main__":
    main()
