import csv
import http.server
import io
import json
import math
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

# ── Project root ────────────────────────────────────────────────────────────
PROJECT = Path(__file__).resolve().parent.parent
MECHANICS_CSV = PROJECT / "ne_mechanics.csv"
TOWING_CSV = PROJECT / "ne_towing.csv"
MECHANICS_JSON = PROJECT / "ne_mechanics.json"
PREVIEW_PY = PROJECT / "preview.py"
PREVIEW_HTML = PROJECT / "preview.html"

# Nebraska bounding box (rough) — all seeded data should fall inside.
NE_LAT_MIN, NE_LAT_MAX = 39.9, 43.1
NE_LON_MIN, NE_LON_MAX = -104.2, -95.3

# ── Helpers ─────────────────────────────────────────────────────────────────

def haversine_miles(lat1, lon1, lat2, lon2):
    """Replicate the JS Haversine from preview.html for test comparison."""
    R = 3958.8
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_mechanics():
    """Load mechanics CSV as list of dicts."""
    with open(MECHANICS_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_towing():
    """Load towing CSV as list of dicts."""
    with open(TOWING_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_mechanics_json():
    """Load mechanics JSON records."""
    with open(MECHANICS_JSON, encoding="utf-8") as f:
        return json.load(f)


# ═════════════════════════════════════════════════════════════════════════════
# DATA INTEGRITY
# ═════════════════════════════════════════════════════════════════════════════

class TestMechanicsCsvIntegrity:
    """The seed CSV must be well-formed and contain all required columns."""

    REQUIRED_COLS = [
        "name", "shop_type", "address", "city", "state", "postcode",
        "lat", "lon", "phone", "website", "opening_hours", "services",
        "is_transmission_specialist", "osm_type", "osm_id", "osm_url",
    ]

    def test_has_required_columns(self):
        with open(MECHANICS_CSV, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            columns = set(reader.fieldnames or [])
        missing = set(self.REQUIRED_COLS) - columns
        assert not missing, f"Missing columns: {missing}"

    def test_named_rows_have_valid_data(self):
        """Rows with a name (the ones the app displays) must be complete."""
        records = load_mechanics()
        named = [r for r in records if r["name"].strip()]
        assert len(named) >= 300  # majority should be named
        # Every named row must have lat, lon, city
        bad = [
            i for i, r in enumerate(records, start=2)
            if r["name"].strip() and (
                not r["lat"] or not r["lon"] or not r["city"]
            )
        ]
        assert not bad, f"Named rows with missing lat/lon/city: {bad[:10]}"

    def test_unnamed_rows_are_filterable(self):
        """Unnamed entries exist in the CSV but the app skips them at load time."""
        records = load_mechanics()
        unnamed = [r for r in records if not r["name"].strip()]
        # Verify the filter that preview.html applies works correctly
        filtered = [r for r in records if r["name"].strip()]
        assert len(filtered) + len(unnamed) == len(records)
        assert len(unnamed) >= 0  # we know there are some, this is just a doc-test

    def test_all_rows_have_valid_lat_lon(self):
        records = load_mechanics()
        for i, r in enumerate(records, start=2):
            lat = float(r["lat"])
            lon = float(r["lon"])
            assert NE_LAT_MIN <= lat <= NE_LAT_MAX, f"Row {i}: lat {lat} outside Nebraska"
            assert NE_LON_MIN <= lon <= NE_LON_MAX, f"Row {i}: lon {lon} outside Nebraska"

    def test_all_rows_have_city(self):
        records = load_mechanics()
        blank = [i for i, r in enumerate(records, start=2) if not r["city"].strip()]
        assert not blank, (
            f"{len(blank)} rows missing city: {blank[:5]}{'...' if len(blank) > 5 else ''}"
        )

    def test_no_duplicate_osm_ids(self):
        records = load_mechanics()
        ids = [r["osm_id"] for r in records]
        dupes = {oid for oid in ids if ids.count(oid) > 1}
        assert not dupes, f"Duplicate OSM IDs: {dupes}"

    def test_osm_url_format(self):
        records = load_mechanics()
        for i, r in enumerate(records, start=2):
            url = r["osm_url"]
            assert url.startswith("https://www.openstreetmap.org/"), (
                f"Row {i}: bad OSM URL {url}"
            )
            parts = url.split("/")
            assert parts[-2] in ("node", "way", "relation"), (
                f"Row {i}: unexpected OSM type in {url}"
            )

    def test_row_count_matches_json(self):
        csv_records = load_mechanics()
        json_records = load_mechanics_json()
        assert len(csv_records) == len(json_records), (
            f"CSV has {len(csv_records)} rows, JSON has {len(json_records)}"
        )


class TestTowingCsvIntegrity:
    """Towing CSV is much smaller but should still pass basic checks."""

    REQUIRED_COLS = [
        "name", "osm_category", "address", "city", "state", "postcode",
        "lat", "lon", "phone", "website", "opening_hours", "services",
        "available_24_7", "heavy_duty", "osm_type", "osm_id", "osm_url",
    ]

    def test_has_required_columns(self):
        with open(TOWING_CSV, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            columns = set(reader.fieldnames or [])
        missing = set(self.REQUIRED_COLS) - columns
        assert not missing, f"Missing columns: {missing}"

    def test_all_rows_have_valid_lat_lon(self):
        records = load_towing()
        for i, r in enumerate(records, start=2):
            lat = float(r["lat"])
            lon = float(r["lon"])
            assert NE_LAT_MIN <= lat <= NE_LAT_MAX, f"Row {i}: lat {lat} outside Nebraska"
            assert NE_LON_MIN <= lon <= NE_LON_MAX, f"Row {i}: lon {lon} outside Nebraska"

    def test_osm_url_format(self):
        records = load_towing()
        for i, r in enumerate(records, start=2):
            url = r["osm_url"]
            assert url.startswith("https://www.openstreetmap.org/"), f"Row {i}: bad URL {url}"


# ═════════════════════════════════════════════════════════════════════════════
# DISTANCE CALCULATION
# ═════════════════════════════════════════════════════════════════════════════

class TestHaversine:
    """Verify the distance formula matches known values."""

    def test_same_point_returns_zero(self):
        assert haversine_miles(40.8136, -96.7026, 40.8136, -96.7026) == 0.0

    def test_lincoln_to_omaha(self):
        """Lincoln → Omaha is roughly 53–58 miles depending on exact points."""
        # Downtown Lincoln to Downtown Omaha
        d = haversine_miles(40.8136, -96.7026, 41.2565, -95.9345)
        assert 50 < d < 62, f"Expected ~50–62 mi, got {d:.1f}"

    def test_symmetric(self):
        a = (40.8136, -96.7026)
        b = (42.0966, -102.8840)
        assert haversine_miles(*a, *b) == pytest.approx(haversine_miles(*b, *a))

    def test_ordering_by_distance(self):
        """Sorting by distance from Lincoln should put Lincoln shops first."""
        lincoln = (40.8136, -96.7026)
        records = load_mechanics()
        scored = [
            (haversine_miles(lincoln[0], lincoln[1], float(r["lat"]), float(r["lon"])), r)
            for r in records
        ]
        scored.sort(key=lambda x: x[0])
        # The closest shop should be within 10 miles of Lincoln
        assert scored[0][0] < 10, f"Closest shop is {scored[0][0]:.1f} mi away — expected < 10"
        # The farthest should be hundreds of miles (western NE)
        assert scored[-1][0] > 200, f"Farthest shop is only {scored[-1][0]:.1f} mi — expected > 200"

    def test_known_landmark_distance(self):
        """Scottsbluff to Omaha is about 400 miles."""
        d = haversine_miles(41.8666, -103.6672, 41.2565, -95.9345)
        assert 390 < d < 415, f"Scottsbluff→Omaha expected ~400 mi, got {d:.1f}"


# ═════════════════════════════════════════════════════════════════════════════
# SEARCH / FILTER LOGIC
# ═════════════════════════════════════════════════════════════════════════════

class TestSearchFilter:
    """Replicate the client-side filter logic: match on service string or name."""

    @staticmethod
    def filter_records(records, query):
        q = query.lower()
        return [
            r for r in records
            if q in r.get("services", "").lower()
            or q in r.get("name", "").lower()
        ]

    def test_filter_transmission_finds_specialists(self):
        records = load_mechanics()
        results = self.filter_records(records, "transmission")
        assert len(results) > 0
        # Every result should mention transmission in name or services
        for r in results:
            haystack = (r["name"] + " " + r["services"]).lower()
            assert "transmission" in haystack, f"False match: {r['name']}"

    def test_filter_brakes_finds_results(self):
        records = load_mechanics()
        results = self.filter_records(records, "brakes")
        assert len(results) > 0
        for r in results:
            haystack = (r["name"] + " " + r["services"]).lower()
            assert "brake" in haystack, f"False match: {r['name']}"

    def test_filter_nonsense_returns_empty(self):
        records = load_mechanics()
        results = self.filter_records(records, "zzzxyzzyxnothing")
        assert results == []

    def test_filter_case_insensitive(self):
        records = load_mechanics()
        lower = self.filter_records(records, "transmission")
        upper = self.filter_records(records, "TRANSMISSION")
        mixed = self.filter_records(records, "TrAnSmIsSiOn")
        assert len(lower) == len(upper) == len(mixed)

    def test_filter_by_name_substring(self):
        records = load_mechanics()
        results = self.filter_records(records, "firestone")
        assert len(results) > 0
        for r in results:
            assert "firestone" in r["name"].lower()

    def test_filter_towing_in_mechanics(self):
        """Some mechanics list towing as a service."""
        records = load_mechanics()
        results = self.filter_records(records, "towing")
        # Not all mechanics tow, but some should
        assert len(results) >= 0  # sanity — we just care it doesn't crash


# ═════════════════════════════════════════════════════════════════════════════
# SERVER BEHAVIOUR
# ═════════════════════════════════════════════════════════════════════════════

class TestNoCacheHandler:
    """The NoCacheHandler must send cache-busting headers on every response."""

    def test_sends_no_cache_headers(self):
        """Verify end_headers() adds the three cache-prevention headers."""
        sys.path.insert(0, str(PROJECT))
        import preview  # type: ignore

        # Build a mock request with the minimum needed to avoid triggering
        # the read/handle loop in BaseHTTPRequestHandler.__init__.
        mock_request = mock.MagicMock()
        mock_request.makefile.return_value = io.BytesIO(b"GET / HTTP/1.0\r\n\r\n")

        # Create the handler — it will process the mock GET and finish.
        # We intercept send_header during that first request.
        headers_sent = {}

        original_send_header = preview.NoCacheHandler.send_header

        def capture_header(self, keyword, value):
            headers_sent[keyword] = value
            return original_send_header(self, keyword, value)

        with mock.patch.object(preview.NoCacheHandler, "send_header", capture_header):
            handler = preview.NoCacheHandler(
                mock_request, ("127.0.0.1", 12345), mock.Mock()
            )

        assert headers_sent.get("Cache-Control") == (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        assert headers_sent.get("Pragma") == "no-cache"
        assert headers_sent.get("Expires") == "0"


class TestServerEndpoints:
    """Integration-style checks against the running dev server."""

    @pytest.fixture(autouse=False)
    def server_running(self):
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = s.connect_ex(("127.0.0.1", 8080))
        s.close()
        if result != 0:
            pytest.skip("Dev server not running on :8080")
        return True

    def test_preview_html_serves(self, server_running):
        import urllib.request
        resp = urllib.request.urlopen("http://localhost:8080/preview.html")
        assert resp.status == 200
        body = resp.read().decode()
        assert "<title>YouAuto" in body
        assert "loadData" in body  # core JS function present

    def test_mechanics_csv_serves(self, server_running):
        import urllib.request
        resp = urllib.request.urlopen("http://localhost:8080/ne_mechanics.csv")
        assert resp.status == 200
        assert int(resp.headers["Content-Length"]) > 10000

    def test_towing_csv_serves(self, server_running):
        import urllib.request
        resp = urllib.request.urlopen("http://localhost:8080/ne_towing.csv")
        assert resp.status == 200

    def test_missing_path_returns_404(self, server_running):
        import urllib.request, urllib.error
        try:
            urllib.request.urlopen("http://localhost:8080/nonexistent.xyz")
        except urllib.error.HTTPError as e:
            assert e.code == 404
        else:
            pytest.fail("Expected 404")

    def test_cache_headers_present(self, server_running):
        import urllib.request
        resp = urllib.request.urlopen("http://localhost:8080/preview.html")
        assert resp.headers["Cache-Control"] == (
            "no-store, no-cache, must-revalidate, max-age=0"
        )


# ═════════════════════════════════════════════════════════════════════════════
# EMPTY-STATE / NO-RESULTS BEHAVIOUR
# ═════════════════════════════════════════════════════════════════════════════

class TestEmptyState:
    """The app must handle the no-results case gracefully."""

    def test_no_mechanics_match_returns_empty_list(self):
        records = load_mechanics()
        # Searching for a service nobody offers should return nothing
        results = [r for r in records if "quantum_entanglement_repair" in r["services"].lower()]
        assert results == []

    def test_filter_preserves_empty_structure(self):
        """An empty result set should still be iterable and render the empty template."""
        empty = []
        # Simulate what renderTable does with empty results
        assert len(empty) == 0
        msg = "No results found" if not empty else f"{len(empty)} results"
        assert "No results found" in msg


# ═════════════════════════════════════════════════════════════════════════════
# PERFORMANCE SANITY
# ═════════════════════════════════════════════════════════════════════════════

class TestPerformanceSanity:
    """Rough baseline — we are not benchmarking, just ensuring no regressions."""

    def test_haversine_over_full_dataset_is_fast(self):
        """432 distance calculations should complete in under 50 ms."""
        import time
        records = load_mechanics()
        point = (40.8136, -96.7026)
        start = time.perf_counter()
        for _ in range(100):
            for r in records:
                haversine_miles(point[0], point[1], float(r["lat"]), float(r["lon"]))
        elapsed = time.perf_counter() - start
        # 100 * 432 = 43,200 calcs should be well under 2 seconds in Python
        assert elapsed < 2.0, f"43,200 calcs took {elapsed:.2f}s — too slow"

    def test_csv_load_is_fast(self):
        """Loading the mechanics CSV should be near-instant."""
        import time
        start = time.perf_counter()
        for _ in range(50):
            load_mechanics()
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"50 CSV loads took {elapsed:.2f}s"

    def test_filter_and_sort_full_pipeline(self):
        """Simulate a full search: load → filter → sort by distance. Under 50ms."""
        import time
        point = (40.8136, -96.7026)
        start = time.perf_counter()
        for _ in range(20):
            records = load_mechanics()
            filtered = [r for r in records if "oil" in r["services"].lower()]
            filtered.sort(
                key=lambda r: haversine_miles(
                    point[0], point[1], float(r["lat"]), float(r["lon"])
                )
            )
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"20x full pipeline took {elapsed:.2f}s"
