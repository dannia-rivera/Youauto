#!/usr/bin/env python3
"""
ne_charging_osm.py
==================

Collate a database of EV charging stations in Nebraska (or any US state)
from OpenStreetMap via the Overpass API.

For each station it captures:
    - name, operator (e.g. Tesla, ChargePoint, Electrify America)
    - address (assembled from addr:* tags, plus reverse-geocode enrichment)
    - latitude / longitude
    - phone, website, opening hours, fee, access type
    - connector types with counts (e.g. "CCS x2, CHAdeMO x1, J1772 x4")
    - max power per connector type (kW)
    - total capacity (vehicles that can charge simultaneously)

WHY OPENSTREETMAP
    - Free, no API key required.  OSM charging-station coverage in the US is
      surprisingly good — Tesla Superchargers, ChargePoint, and Electrify
      America locations are well-mapped, especially along interstates.
    - Connector-level detail (socket:ccs=2, socket:type1=4, etc.) lets you
      filter by the plug your vehicle actually uses.

USAGE
    pip install requests
    python ne_charging_osm.py                 # defaults to Nebraska (US-NE)
    python ne_charging_osm.py --state US-IA   # a different state
    python ne_charging_osm.py --out mydata    # custom output filename stem
    python ne_charging_osm.py --no-enrich     # skip Nominatim address fill-in

OUTPUT
    <out>.csv   - one row per station, spreadsheet-friendly
    <out>.json  - same records plus the complete raw OSM tag set (for audit)

POLITE USAGE
    The public Overpass endpoints are a shared, donated resource. Run this
    infrequently (the whole state is one query) and don't hammer it in a loop.
"""

import argparse
import csv
import json
import re
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

# Maps OSM socket:* keys to human-readable connector names.
CONNECTOR_NAMES = {
    "type1": "J1772",
    "type1_combo": "CCS Type 1",
    "type2": "Type 2",
    "type2_combo": "CCS Type 2",
    "ccs": "CCS",
    "chademo": "CHAdeMO",
    "tesla": "Tesla",
    "tesla_supercharger": "Tesla Supercharger",
    "tesla_destination": "Tesla Destination",
    "tesla_ccs": "Tesla CCS",
    "nema_5_15": "NEMA 5-15 (120V)",
    "nema_5_20": "NEMA 5-20 (120V)",
    "nema_14_30": "NEMA 14-30 (240V)",
    "nema_14_50": "NEMA 14-50 (240V)",
    "nema_6_20": "NEMA 6-20 (240V)",
    "nema_6_50": "NEMA 6-50 (240V)",
}

# Default connectors for well-known US networks when OSM has no socket:* tags.
# Based on each network's published specs as of 2026.
# Format: {lowercase_operator_name: "Connector xN; Connector xM; ..."}
KNOWN_OPERATOR_CONNECTORS: dict[str, str] = {
    "electrify america": "CCS x4; CHAdeMO x1",
    "chargepoint": "J1772 x2",
    "tesla": "Tesla x8",
    "tesla, inc.": "Tesla x8",
    "blink": "J1772 x2",
    "evocharge": "J1772 x2",
    "evgo": "CCS x2; CHAdeMO x1",
    "greenlots": "CCS x2; J1772 x2",
    "shell recharge": "CCS x2; CHAdeMO x1",
    "volta": "J1772 x2",
    "sema connect": "J1772 x2",
    "flo": "J1772 x2; CHAdeMO x1",
    "opconnect": "CCS x2; CHAdeMO x1; J1772 x2",
    "woodhouse nissian": "J1772 x1; CHAdeMO x1",
    "nissan": "J1772 x1; CHAdeMO x1",
}


def build_query(state_code: str) -> str:
    """Build an Overpass QL query for charging stations within a US state."""
    return f"""
[out:json][timeout:180];
area["ISO3166-2"="{state_code}"][admin_level=4]->.state;
(
  node["amenity"="charging_station"](area.state);
  way["amenity"="charging_station"](area.state);
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


def extract_connectors(tags: dict) -> dict[str, dict]:
    """Parse socket:* tags into a dict keyed by human-readable connector type.

    Returns e.g. {'CCS': {'count': 2, 'kw': 150}, 'CHAdeMO': {'count': 1, 'kw': 50}}
    """
    # First pass: collect raw socket types and their counts
    raw: dict[str, dict] = {}  # raw_type -> {count, kw, raw_output}
    socket_re = re.compile(r"^socket:(.+)$")

    for key, value in tags.items():
        m = socket_re.match(key)
        if not m:
            continue
        socket_type = m.group(1)

        if ":" in socket_type:
            base, _, attr = socket_type.partition(":")
            if attr == "output":
                entry = raw.setdefault(base, {"count": 0, "kw": None})
                kw_match = re.search(r"(\d+(?:\.\d+)?)\s*kW", str(value), re.IGNORECASE)
                entry["kw"] = float(kw_match.group(1)) if kw_match else None
            # skip other sub-tags like :current, :voltage
            continue

        # Plain socket:<type>=<count>
        try:
            count = int(value)
        except (ValueError, TypeError):
            count = 1 if str(value).lower() in ("yes", "1") else 0
        if count <= 0:
            continue
        entry = raw.setdefault(socket_type, {"count": 0, "kw": None})
        entry["count"] += count

    # Second pass: map to human-readable labels
    connectors: dict[str, dict] = {}
    for raw_type, info in raw.items():
        if info["count"] <= 0:
            continue  # only had :output without a count — skip
        label = CONNECTOR_NAMES.get(raw_type, raw_type.replace("_", " ").title())
        if label in connectors:
            connectors[label]["count"] += info["count"]
            if info.get("kw") and not connectors[label].get("kw"):
                connectors[label]["kw"] = info["kw"]
        else:
            connectors[label] = {"count": info["count"], "kw": info.get("kw")}

    return connectors


def format_connectors(connectors: dict) -> str:
    """Format connector dict as a compact string like 'CCS x2 (150kW), J1772 x4'."""
    parts = []
    for name, info in sorted(connectors.items()):
        s = f"{name} x{info['count']}"
        if info.get("kw"):
            s += f" ({info['kw']:.0f}kW)"
        parts.append(s)
    return "; ".join(parts)


def all_connector_names(connectors: dict) -> list[str]:
    """Return just the connector type names for filtering."""
    return sorted(connectors.keys())


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
                headers={"User-Agent": "YouAuto/1.0 (charging_scrape; OSM data enrichment)"},
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
    for key in CITY_KEYS:
        val = address.get(key, "").strip()
        if val:
            return val
    return ""


def _assemble_from_parts(r: dict) -> str:
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
            loc = _extract_locality(addr)
            if loc:
                r["city"] = loc
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

        connectors = extract_connectors(tags)

        # Fall back to known operator defaults when OSM has no socket data
        if not connectors:
            operator = (tags.get("operator") or tags.get("brand") or tags.get("network") or "").strip().lower()
            default_str = KNOWN_OPERATOR_CONNECTORS.get(operator)
            if default_str:
                # Parse the default string into the same dict shape
                for part in default_str.split(";"):
                    part = part.strip()
                    if not part:
                        continue
                    # "CCS x4" or "J1772 x2 (150kW)" style
                    import re as _re
                    m = _re.match(r"(.+?)\s+x(\d+)\s*(?:\((\d+)kW\))?", part)
                    if m:
                        name = m.group(1).strip()
                        count = int(m.group(2))
                        kw = float(m.group(3)) if m.group(3) else None
                        connectors[name] = {"count": count, "kw": kw}

        connector_names = all_connector_names(connectors)

        # Total capacity from capacity= tag, or sum of socket counts if missing
        capacity_str = tags.get("capacity", "")
        if capacity_str.isdigit():
            capacity = int(capacity_str)
        else:
            capacity = sum(c["count"] for c in connectors.values()) or None

        # Determine max power across all connectors
        max_kw = None
        for c in connectors.values():
            if c.get("kw"):
                if max_kw is None or c["kw"] > max_kw:
                    max_kw = c["kw"]

        record = {
            "osm_type": el.get("type"),
            "osm_id": el.get("id"),
            "name": tags.get("name", ""),
            "operator": tags.get("operator", ""),
            "brand": tags.get("brand", tags.get("network", "")),
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
            "fee": tags.get("fee", ""),
            "access": tags.get("access", "public"),
            "capacity": capacity,
            "max_power_kw": max_kw,
            "connectors": format_connectors(connectors),
            "connector_types": "; ".join(connector_names),
            "osm_url": f"https://www.openstreetmap.org/{el.get('type')}/{el.get('id')}",
            "raw_tags": tags,
        }
        records.append(record)

    records.sort(key=lambda r: (r["name"] == "", r["name"].lower()))
    return records


def write_csv(records: list, path: str) -> None:
    """Write the flat records to CSV."""
    columns = [
        "name", "operator", "brand", "address", "housenumber", "street",
        "city", "state", "postcode", "lat", "lon", "phone", "website",
        "opening_hours", "fee", "access", "capacity", "max_power_kw",
        "connectors", "connector_types",
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
    with_fee = sum(1 for r in records if r["fee"] in ("yes", "no"))
    free = sum(1 for r in records if r["fee"] == "no")
    public = sum(1 for r in records if r["access"] in ("yes", "public", ""))
    fast = sum(1 for r in records if r["max_power_kw"] and r["max_power_kw"] >= 50)

    # Count connector types across all stations
    connector_counts: dict[str, int] = {}
    for r in records:
        for cname in r["connector_types"].split("; "):
            cname = cname.strip()
            if cname:
                connector_counts[cname] = connector_counts.get(cname, 0) + 1

    # Operator breakdown
    operators: dict[str, int] = {}
    for r in records:
        op = r["operator"].strip() or r["brand"].strip() or "(unknown)"
        operators[op] = operators.get(op, 0) + 1

    print("\n--- Summary ---", file=sys.stderr)
    print(f"Total charging stations found: {total}", file=sys.stderr)
    print(f"  with a name:                {named}", file=sys.stderr)
    print(f"  with a parsed address:      {with_addr}", file=sys.stderr)
    print(f"  with fee info:              {with_fee}  ({free} free)", file=sys.stderr)
    print(f"  public access:              {public}", file=sys.stderr)
    print(f"  fast-chargers (≥50 kW):     {fast}", file=sys.stderr)

    print("\n  connector types found:", file=sys.stderr)
    for cname, n in sorted(connector_counts.items(), key=lambda kv: -kv[1]):
        print(f"    {n:>4}  {cname}", file=sys.stderr)

    print("\n  top operators:", file=sys.stderr)
    for op, n in sorted(operators.items(), key=lambda kv: -kv[1])[:10]:
        print(f"    {n:>4}  {op}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--state", default="US-NE",
                        help="ISO 3166-2 state code (default: US-NE for Nebraska)")
    parser.add_argument("--out", default="ne_charging",
                        help="Output filename stem (default: ne_charging)")
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
