"""
Orange County FL – Infrastructure Engineering Lookup Tool
=========================================================
A one-stop research tool for engineers planning to design and construct
new infrastructure in Orange County, Florida.

Input methods: Address, Coordinates, Polygon Drawing, GeoJSON Upload
Output: Parcel data, resource URLs, contacts, jurisdiction info
"""

import streamlit as st
import json
import re
import os
import math
import requests
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# ── Page Configuration ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="OC Infrastructure Lookup",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load Data Files ─────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent / "data"

@st.cache_data
def load_contacts():
    with open(BASE_DIR / "contacts.json", "r") as f:
        return json.load(f)

@st.cache_data
def load_resources():
    with open(BASE_DIR / "resources.json", "r") as f:
        return json.load(f)

CONTACTS = load_contacts()
RESOURCES = load_resources()

# ── Styling ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Global */
    .stApp { font-family: 'DM Sans', sans-serif; }
    .block-container { max-width: 1400px; padding-top: 1.5rem; }

    /* Header */
    .app-header {
        background: linear-gradient(135deg, #0c1b2a 0%, #1a3a5c 50%, #0f4c75 100%);
        padding: 1.8rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        border-left: 5px solid #f7a325;
        position: relative;
        overflow: hidden;
    }
    .app-header::before {
        content: '';
        position: absolute;
        top: 0; right: 0; bottom: 0; left: 0;
        background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
        pointer-events: none;
    }
    .app-header h1 {
        color: #ffffff;
        font-size: 1.65rem;
        font-weight: 700;
        margin: 0 0 0.3rem 0;
        letter-spacing: -0.02em;
    }
    .app-header p {
        color: #a8c7e2;
        font-size: 0.92rem;
        margin: 0;
        font-weight: 400;
    }
    .app-header .badge {
        display: inline-block;
        background: #f7a325;
        color: #0c1b2a;
        font-size: 0.7rem;
        font-weight: 700;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }

    /* Cards */
    .info-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        transition: box-shadow 0.2s;
    }
    .info-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .info-card h3 {
        color: #0f4c75;
        font-size: 1rem;
        font-weight: 700;
        margin: 0 0 0.3rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .info-card .role {
        color: #64748b;
        font-size: 0.82rem;
        margin-bottom: 0.5rem;
    }
    .info-card .detail {
        font-size: 0.82rem;
        color: #334155;
        margin: 0.15rem 0;
        font-family: 'JetBrains Mono', monospace;
    }
    .info-card a {
        color: #0f4c75;
        text-decoration: none;
        font-weight: 500;
    }
    .info-card a:hover { text-decoration: underline; }

    /* Resource link cards */
    .resource-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-left: 3px solid #0f4c75;
        border-radius: 8px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.7rem;
        transition: all 0.15s;
    }
    .resource-card:hover {
        background: #f0f7ff;
        border-left-color: #f7a325;
    }
    .resource-card .res-name {
        font-weight: 600;
        font-size: 0.88rem;
        color: #1e293b;
    }
    .resource-card .res-desc {
        font-size: 0.78rem;
        color: #64748b;
        margin: 0.2rem 0;
    }
    .resource-card .res-url {
        font-size: 0.75rem;
        font-family: 'JetBrains Mono', monospace;
        color: #0f4c75;
        word-break: break-all;
    }

    /* Section headers */
    .section-hdr {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        border-bottom: 2px solid #0f4c75;
        padding-bottom: 0.5rem;
        margin: 1.5rem 0 1rem 0;
    }
    .section-hdr h2 {
        color: #0f4c75;
        font-size: 1.15rem;
        font-weight: 700;
        margin: 0;
    }

    /* Parcel result */
    .parcel-result {
        background: linear-gradient(135deg, #f0f7ff 0%, #e8f4f8 100%);
        border: 1px solid #bdd8f1;
        border-radius: 10px;
        padding: 1.3rem 1.5rem;
        margin-bottom: 1rem;
    }
    .parcel-result h3 {
        color: #0c1b2a;
        font-size: 1.05rem;
        font-weight: 700;
        margin: 0 0 0.6rem 0;
    }
    .parcel-result .field {
        display: flex;
        gap: 0.5rem;
        margin: 0.25rem 0;
        font-size: 0.85rem;
    }
    .parcel-result .label {
        font-weight: 600;
        color: #475569;
        min-width: 130px;
    }
    .parcel-result .value {
        color: #1e293b;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
    }

    /* Status badges */
    .status-ok {
        display: inline-block;
        background: #dcfce7;
        color: #166534;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
    }
    .status-warn {
        display: inline-block;
        background: #fef3c7;
        color: #92400e;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
    }
    .status-info {
        display: inline-block;
        background: #dbeafe;
        color: #1e40af;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #f8fafc;
    }
    section[data-testid="stSidebar"] .stRadio label {
        font-weight: 500;
    }

    /* Map container */
    .map-container {
        border: 2px solid #e2e8f0;
        border-radius: 12px;
        overflow: hidden;
        margin-bottom: 1rem;
    }

    /* Disclaimer */
    .disclaimer {
        background: #fffbeb;
        border: 1px solid #fde68a;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        font-size: 0.78rem;
        color: #92400e;
        margin-top: 1rem;
    }

    /* Dark mode overrides */
    @media (prefers-color-scheme: dark) {
        .info-card { background: #1e293b; border-color: #334155; }
        .info-card h3 { color: #7dd3fc; }
        .info-card .role { color: #94a3b8; }
        .info-card .detail { color: #cbd5e1; }
        .resource-card { background: #1e293b; border-color: #334155; }
        .resource-card .res-name { color: #e2e8f0; }
        .parcel-result { background: linear-gradient(135deg, #1e293b 0%, #1a3a5c 100%); border-color: #334155; }
        .parcel-result h3 { color: #e2e8f0; }
        .parcel-result .value { color: #cbd5e1; }
    }
</style>
""", unsafe_allow_html=True)


# ── Coordinate & Address Parsing ────────────────────────────────────────────

def parse_coordinates(text: str) -> Optional[tuple]:
    """Parse coordinates from many formats:
    28.5383, -81.3792
    28.5383° N, 81.3792° W
    28°32'17.9"N 81°22'45.1"W
    N28.5383 W81.3792
    (28.5383, -81.3792)
    28.5383/-81.3792
    """
    text = text.strip().strip("()")

    # DMS format: 28°32'17.9"N 81°22'45.1"W
    dms_pattern = r"""(\d{1,3})[°]\s*(\d{1,2})['\u2019]\s*([\d.]+)["\u201d]?\s*([NSns])\s*[,/\s]+\s*(\d{1,3})[°]\s*(\d{1,2})['\u2019]\s*([\d.]+)["\u201d]?\s*([EWew])"""
    m = re.search(dms_pattern, text)
    if m:
        lat = int(m.group(1)) + int(m.group(2)) / 60 + float(m.group(3)) / 3600
        lon = int(m.group(5)) + int(m.group(6)) / 60 + float(m.group(7)) / 3600
        if m.group(4).upper() == 'S':
            lat = -lat
        if m.group(8).upper() == 'W':
            lon = -lon
        return (lat, lon)

    # Decimal with N/S/E/W prefix or suffix
    nsew_pattern = r'[NSEWnsew]?\s*([-]?\d+\.?\d*)\s*[°]?\s*([NSEWnsew]?)\s*[,/\s]+\s*[NSEWnsew]?\s*([-]?\d+\.?\d*)\s*[°]?\s*([NSEWnsew]?)'
    m = re.search(nsew_pattern, text)
    if m:
        lat = float(m.group(1))
        lon = float(m.group(3))
        dirs = (m.group(2) + m.group(4)).upper()
        if 'S' in dirs:
            lat = -abs(lat)
        if 'W' in dirs:
            lon = -abs(lon)
        # Sanity check for Orange County area
        if 27.5 < abs(lat) < 29.5 and 80 < abs(lon) < 82.5:
            if lon > 0:
                lon = -lon
            return (lat, lon)
        elif 27.5 < abs(lon) < 29.5 and 80 < abs(lat) < 82.5:
            return (lon, -abs(lat) if lat > 0 else lat)

    # Simple decimal: 28.5383, -81.3792 or 28.5383 -81.3792
    simple_pattern = r'([-]?\d+\.?\d*)\s*[,/\s]+\s*([-]?\d+\.?\d*)'
    m = re.search(simple_pattern, text)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        # Determine which is lat and which is lon
        if 27.0 < a < 30.0 and -83.0 < b < -80.0:
            return (a, b)
        elif 27.0 < b < 30.0 and -83.0 < a < -80.0:
            return (b, a)
        elif 27.0 < a < 30.0 and 80.0 < b < 83.0:
            return (a, -b)
        elif 27.0 < b < 30.0 and 80.0 < a < 83.0:
            return (b, -a)
        # Fallback
        return (a, b)

    return None


def geocode_address(address: str) -> Optional[dict]:
    """Geocode an address using Nominatim (OSM) – free, no API key needed."""
    try:
        # Append Orange County FL if not already specified
        addr_lower = address.lower()
        if 'orange county' not in addr_lower and 'orlando' not in addr_lower and ', fl' not in addr_lower and 'florida' not in addr_lower:
            address = f"{address}, Orange County, FL"

        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": address,
            "format": "json",
            "addressdetails": 1,
            "limit": 5,
            "countrycodes": "us",
        }
        headers = {"User-Agent": "OC-InfraLookup/1.0"}
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        results = resp.json()
        if results:
            best = results[0]
            return {
                "lat": float(best["lat"]),
                "lon": float(best["lon"]),
                "display_name": best.get("display_name", address),
                "address_parts": best.get("address", {}),
            }
    except Exception as e:
        st.warning(f"Geocoding error: {e}")
    return None


def query_oc_parcels(lat: float, lon: float, radius_m: float = 50) -> list:
    """Query Orange County ArcGIS REST service for parcel data near a point."""
    parcels = []
    try:
        # Orange County Property Appraiser / GIS parcel service
        url = "https://maps.ocpafl.org/arcgis/rest/services/DynamicOCPA/MapServer/0/query"
        params = {
            "geometry": f"{lon},{lat}",
            "geometryType": "esriGeometryPoint",
            "spatialRel": "esriSpatialRelIntersects",
            "inSR": "4326",
            "outSR": "4326",
            "outFields": "*",
            "returnGeometry": "true",
            "f": "json",
        }
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        if "features" in data:
            for feat in data["features"]:
                parcels.append(feat.get("attributes", {}))
    except Exception:
        pass

    # Fallback: try Orange County Government GIS
    if not parcels:
        try:
            url = "https://gis.orangecountyfl.net/arcgis/rest/services/Dynamic/Parcels/MapServer/0/query"
            params = {
                "geometry": f"{lon},{lat}",
                "geometryType": "esriGeometryPoint",
                "spatialRel": "esriSpatialRelIntersects",
                "inSR": "4326",
                "outSR": "4326",
                "outFields": "*",
                "returnGeometry": "true",
                "f": "json",
            }
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()
            if "features" in data:
                for feat in data["features"]:
                    parcels.append(feat.get("attributes", {}))
        except Exception:
            pass

    return parcels


def query_parcels_by_envelope(min_lon, min_lat, max_lon, max_lat) -> list:
    """Query parcels within a bounding box."""
    parcels = []
    try:
        url = "https://maps.ocpafl.org/arcgis/rest/services/DynamicOCPA/MapServer/0/query"
        params = {
            "geometry": f"{min_lon},{min_lat},{max_lon},{max_lat}",
            "geometryType": "esriGeometryEnvelope",
            "spatialRel": "esriSpatialRelIntersects",
            "inSR": "4326",
            "outSR": "4326",
            "outFields": "*",
            "returnGeometry": "true",
            "resultRecordCount": 100,
            "f": "json",
        }
        resp = requests.get(url, params=params, timeout=20)
        data = resp.json()
        if "features" in data:
            for feat in data["features"]:
                parcels.append(feat.get("attributes", {}))
    except Exception:
        pass
    return parcels


def query_parcels_by_polygon(rings: list) -> list:
    """Query parcels intersecting a polygon (ArcGIS geometry format)."""
    parcels = []
    try:
        geom = json.dumps({"rings": rings, "spatialReference": {"wkid": 4326}})
        url = "https://maps.ocpafl.org/arcgis/rest/services/DynamicOCPA/MapServer/0/query"
        params = {
            "geometry": geom,
            "geometryType": "esriGeometryPolygon",
            "spatialRel": "esriSpatialRelIntersects",
            "inSR": "4326",
            "outSR": "4326",
            "outFields": "*",
            "returnGeometry": "true",
            "resultRecordCount": 200,
            "f": "json",
        }
        resp = requests.get(url, params=params, timeout=20)
        data = resp.json()
        if "features" in data:
            for feat in data["features"]:
                parcels.append(feat.get("attributes", {}))
    except Exception:
        pass
    return parcels


def determine_jurisdiction(lat: float, lon: float) -> dict:
    """Determine municipal jurisdiction for a point – affects which contacts are primary."""
    # Approximate bounding boxes for major Orange County municipalities
    jurisdictions = {
        "City of Orlando": {"lat_range": (28.40, 28.62), "lon_range": (-81.50, -81.30)},
        "City of Winter Park": {"lat_range": (28.57, 28.62), "lon_range": (-81.38, -81.33)},
        "City of Maitland": {"lat_range": (28.61, 28.65), "lon_range": (-81.40, -81.35)},
        "City of Apopka": {"lat_range": (28.65, 28.72), "lon_range": (-81.55, -81.47)},
        "City of Ocoee": {"lat_range": (28.54, 28.60), "lon_range": (-81.58, -81.52)},
        "City of Winter Garden": {"lat_range": (28.54, 28.60), "lon_range": (-81.62, -81.55)},
    }
    matches = []
    for name, bounds in jurisdictions.items():
        if (bounds["lat_range"][0] <= lat <= bounds["lat_range"][1] and
                bounds["lon_range"][0] <= lon <= bounds["lon_range"][1]):
            matches.append(name)

    if not matches:
        return {
            "jurisdiction": "Unincorporated Orange County",
            "note": "Subject to Orange County development regulations. Verify with OC Planning Division.",
            "primary_permit_authority": "Orange County Building Safety / Development Engineering",
        }
    return {
        "jurisdiction": matches[0],
        "note": f"Within {matches[0]} limits – verify with municipal planning department.",
        "primary_permit_authority": f"{matches[0]} Permitting Department",
    }


def determine_water_management_district(lat: float) -> str:
    """Orange County straddles SJRWMD (north) and SFWMD (south)."""
    # The dividing line is approximately at latitude 28.46
    if lat > 28.46:
        return "St. Johns River Water Management District (SJRWMD)"
    else:
        return "South Florida Water Management District (SFWMD)"


# ── Rendering Helpers ───────────────────────────────────────────────────────

def render_parcel_card(parcel: dict, idx: int = 0):
    """Render a single parcel result card."""
    # Common field name mappings (ArcGIS field names vary)
    field_map = {
        "parcel_id": ["PARCELNO", "PARCEL_ID", "PARCELID", "PARCEL", "PIN", "OBJECTID"],
        "owner": ["OWNER", "OWNER1", "OWN_NAME", "OWNERNAME"],
        "address": ["SITEADDR", "SITE_ADDR", "ADDRESS", "SITUS", "SITUS_ADDR", "SITUSADDRESS"],
        "city": ["SITUSCITY", "CITY", "SITUS_CITY"],
        "zip": ["SITUSZIP", "ZIP", "ZIPCODE", "SITUS_ZIP"],
        "use_code": ["USECODE", "USE_CODE", "LANDUSE", "DESSION", "DOR_UC"],
        "zoning": ["ZONING", "ZONE", "ZONE_CODE"],
        "acreage": ["ACREAGE", "ACRES", "AREA_ACRES", "GISACRES"],
        "legal": ["LEGAL", "LEGALDESC", "LEGAL_DESC", "LEGAL1"],
        "subdivision": ["SUBDIVISION", "SUBDIV", "PLATNAME"],
        "plat_book": ["PLATBOOK", "PLAT_BOOK", "PB"],
        "plat_page": ["PLATPAGE", "PLAT_PAGE", "PP"],
        "just_value": ["JUSTVALUE", "JUST_VALUE", "JV", "MARKET_VAL"],
    }

    def find_field(key):
        for candidate in field_map.get(key, []):
            for pk, pv in parcel.items():
                if pk.upper() == candidate.upper() and pv:
                    return str(pv)
        return None

    pid = find_field("parcel_id") or "N/A"
    owner = find_field("owner") or "N/A"
    addr = find_field("address") or "N/A"
    city = find_field("city") or ""
    zipcode = find_field("zip") or ""
    use = find_field("use_code") or "N/A"
    zoning = find_field("zoning") or "—"
    acres = find_field("acreage") or "—"
    legal = find_field("legal") or "—"
    subdiv = find_field("subdivision") or "—"
    pb = find_field("plat_book") or ""
    pp = find_field("plat_page") or ""
    jv = find_field("just_value") or "—"

    plat_ref = f"PB {pb} / PG {pp}" if pb and pp else "—"
    full_addr = f"{addr}, {city} {zipcode}".strip(", ")

    # Build property appraiser URL
    ocpa_url = f"https://www.ocpafl.org/Searches/ParcelSearch.aspx"

    st.markdown(f"""
    <div class="parcel-result">
        <h3>📋 Parcel #{idx + 1}: {pid}</h3>
        <div class="field"><span class="label">Owner:</span><span class="value">{owner}</span></div>
        <div class="field"><span class="label">Site Address:</span><span class="value">{full_addr}</span></div>
        <div class="field"><span class="label">Use Code:</span><span class="value">{use}</span></div>
        <div class="field"><span class="label">Zoning:</span><span class="value">{zoning}</span></div>
        <div class="field"><span class="label">Acreage:</span><span class="value">{acres}</span></div>
        <div class="field"><span class="label">Subdivision:</span><span class="value">{subdiv}</span></div>
        <div class="field"><span class="label">Plat Reference:</span><span class="value">{plat_ref}</span></div>
        <div class="field"><span class="label">Legal Desc:</span><span class="value">{legal[:120]}{'...' if len(legal) > 120 else ''}</span></div>
        <div class="field"><span class="label">Just Value:</span><span class="value">${jv:,}</span></div>
        <div class="field"><span class="label">OCPA Lookup:</span><span class="value"><a href="{ocpa_url}" target="_blank">Search on OCPA →</a></span></div>
    </div>
    """, unsafe_allow_html=True)


def render_contact_card(contact: dict):
    phone_line = f'<div class="detail">📞 {contact["phone"]}</div>' if contact.get("phone") else ""
    email_line = f'<div class="detail">✉️ <a href="mailto:{contact["email"]}">{contact["email"]}</a></div>' if contact.get("email") else ""
    addr_line = f'<div class="detail">📍 {contact["address"]}</div>' if contact.get("address") else ""
    url_line = f'<div class="detail">🔗 <a href="{contact["url"]}" target="_blank">{contact["url"]}</a></div>' if contact.get("url") else ""
    note_line = f'<div class="detail" style="color:#92400e; font-style:italic;">⚠️ {contact["service_area_note"]}</div>' if contact.get("service_area_note") else ""

    st.markdown(f"""
    <div class="info-card">
        <h3>{contact["name"]}</h3>
        <div class="role">{contact["role"]}</div>
        {phone_line}{email_line}{addr_line}{url_line}{note_line}
    </div>
    """, unsafe_allow_html=True)


def render_resource_card(resource: dict):
    st.markdown(f"""
    <div class="resource-card">
        <div class="res-name">{resource["name"]}</div>
        <div class="res-desc">{resource["description"]}</div>
        <div class="res-url"><a href="{resource["url"]}" target="_blank">{resource["url"]}</a></div>
    </div>
    """, unsafe_allow_html=True)


def render_section_header(icon: str, title: str):
    st.markdown(f"""
    <div class="section-hdr">
        <h2>{icon} {title}</h2>
    </div>
    """, unsafe_allow_html=True)


# ── Map Generation with Folium ──────────────────────────────────────────────

def build_map_html(center_lat=28.5383, center_lon=-81.3792, zoom=11, markers=None, polygon_coords=None):
    """Generate a Leaflet map as HTML with draw tools and click-to-get-coords."""
    markers = markers or []
    marker_js = ""
    for m in markers:
        popup = m.get("popup", "").replace("'", "\\'").replace("\n", "<br>")
        marker_js += f"""
        L.marker([{m['lat']}, {m['lon']}], {{
            icon: L.divIcon({{
                html: '<div style="background:#0f4c75;color:white;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:bold;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3);">📍</div>',
                iconSize: [28, 28],
                iconAnchor: [14, 14],
                className: ''
            }})
        }}).addTo(map).bindPopup('{popup}');
        """

    poly_js = ""
    if polygon_coords:
        poly_points = json.dumps([[c[0], c[1]] for c in polygon_coords])
        poly_js = f"""
        var polygon = L.polygon({poly_points}, {{
            color: '#f7a325',
            weight: 3,
            fillColor: '#f7a325',
            fillOpacity: 0.15
        }}).addTo(map);
        map.fitBounds(polygon.getBounds().pad(0.1));
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.css" />
        <style>
            #map {{ width: 100%; height: 550px; border-radius: 10px; }}
            .coord-display {{
                position: absolute; bottom: 10px; left: 10px; z-index: 1000;
                background: rgba(12,27,42,0.85); color: #a8c7e2;
                padding: 6px 12px; border-radius: 6px; font-family: 'JetBrains Mono', monospace;
                font-size: 12px; backdrop-filter: blur(4px);
            }}
            .draw-instructions {{
                position: absolute; top: 10px; right: 10px; z-index: 1000;
                background: rgba(12,27,42,0.9); color: white;
                padding: 10px 14px; border-radius: 8px; font-size: 12px;
                max-width: 220px; line-height: 1.4; font-family: 'DM Sans', sans-serif;
            }}
            .draw-instructions strong {{ color: #f7a325; }}
            #geojson-output {{
                display: none;
            }}
        </style>
    </head>
    <body style="margin:0;padding:0;">
        <div id="map"></div>
        <div class="coord-display" id="coords">Hover over map for coordinates</div>
        <div class="draw-instructions">
            <strong>Drawing Tools</strong><br>
            Use the toolbar (left) to draw polygons or rectangles.<br><br>
            <strong>Click</strong> the map to see coordinates.<br>
            Drawn shapes appear below as GeoJSON.
        </div>
        <textarea id="geojson-output" rows="4" style="width:100%;font-family:monospace;font-size:11px;margin-top:4px;"></textarea>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.js"></script>
        <script>
            var map = L.map('map').setView([{center_lat}, {center_lon}], {zoom});

            // Tile layers
            var osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '© OpenStreetMap contributors',
                maxZoom: 19
            }});
            var esriImagery = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                attribution: '© Esri',
                maxZoom: 19
            }});
            var esriTopo = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                attribution: '© Esri',
                maxZoom: 19
            }});
            osm.addTo(map);

            L.control.layers({{
                "Street Map": osm,
                "Satellite": esriImagery,
                "Topographic": esriTopo
            }}).addTo(map);

            // Draw control
            var drawnItems = new L.FeatureGroup();
            map.addLayer(drawnItems);
            var drawControl = new L.Control.Draw({{
                draw: {{
                    polygon: {{
                        allowIntersection: false,
                        shapeOptions: {{ color: '#f7a325', weight: 3, fillOpacity: 0.12 }}
                    }},
                    rectangle: {{
                        shapeOptions: {{ color: '#f7a325', weight: 3, fillOpacity: 0.12 }}
                    }},
                    circle: false,
                    circlemarker: false,
                    marker: true,
                    polyline: false
                }},
                edit: {{
                    featureGroup: drawnItems,
                    remove: true
                }}
            }});
            map.addControl(drawControl);

            map.on(L.Draw.Event.CREATED, function (e) {{
                drawnItems.addLayer(e.layer);
                updateGeoJSON();
            }});
            map.on(L.Draw.Event.EDITED, function () {{ updateGeoJSON(); }});
            map.on(L.Draw.Event.DELETED, function () {{ updateGeoJSON(); }});

            function updateGeoJSON() {{
                var geojson = drawnItems.toGeoJSON();
                var output = document.getElementById('geojson-output');
                output.style.display = 'block';
                output.value = JSON.stringify(geojson, null, 2);
                // Send to Streamlit
                try {{
                    window.parent.postMessage({{
                        type: 'drawn_geojson',
                        data: geojson
                    }}, '*');
                }} catch(e) {{}}
            }}

            // Coordinate display
            map.on('mousemove', function(e) {{
                document.getElementById('coords').innerHTML =
                    'Lat: ' + e.latlng.lat.toFixed(6) + '  |  Lon: ' + e.latlng.lng.toFixed(6);
            }});

            map.on('click', function(e) {{
                document.getElementById('coords').innerHTML =
                    '<strong style="color:#f7a325;">CLICKED:</strong> ' + e.latlng.lat.toFixed(6) + ', ' + e.latlng.lng.toFixed(6);
            }});

            // Add markers
            {marker_js}

            // Add polygon if provided
            {poly_js}

            // If markers exist, fit bounds
            {"map.setView([" + str(markers[0]['lat']) + "," + str(markers[0]['lon']) + "], 16);" if len(markers) == 1 else ""}
        </script>
    </body>
    </html>
    """
    return html


# ── App Header ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <div class="badge">Orange County, Florida</div>
    <h1>🏗️ Infrastructure Engineering Lookup Tool</h1>
    <p>Parcel data · Utility contacts · Permits · Plats · HOA/CDD info · Jurisdiction lookup</p>
</div>
""", unsafe_allow_html=True)


# ── Sidebar: Input Methods ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📍 Location Input")
    input_method = st.radio(
        "Select input method:",
        ["Address Search", "Coordinates", "GeoJSON Upload"],
        label_visibility="collapsed",
    )

    query_lat = None
    query_lon = None
    polygon_coords = None
    multi_point = False

    if input_method == "Address Search":
        st.markdown("#### 🏠 Address Lookup")
        st.caption("Accepts many formats: full address, street + city, intersection, etc.")
        address_input = st.text_input(
            "Enter address:",
            placeholder="e.g., 400 S Orange Ave, Orlando FL 32801",
        )
        if st.button("🔍 Search Address", use_container_width=True):
            if address_input:
                with st.spinner("Geocoding address..."):
                    result = geocode_address(address_input)
                if result:
                    query_lat = result["lat"]
                    query_lon = result["lon"]
                    st.session_state["query_lat"] = query_lat
                    st.session_state["query_lon"] = query_lon
                    st.session_state["query_label"] = result["display_name"]
                    st.success(f"Found: {result['display_name'][:80]}")
                else:
                    st.error("Address not found. Try adding city/state or check spelling.")

    elif input_method == "Coordinates":
        st.markdown("#### 🌐 Coordinate Input")
        st.caption("""Accepted formats:
• 28.5383, -81.3792
• 28°32'17.9"N 81°22'45.1"W
• N28.5383 W81.3792
• (28.5383, -81.3792)""")
        coord_input = st.text_input(
            "Enter coordinates:",
            placeholder="28.5383, -81.3792",
        )
        if st.button("🔍 Search Coordinates", use_container_width=True):
            if coord_input:
                parsed = parse_coordinates(coord_input)
                if parsed:
                    query_lat, query_lon = parsed
                    st.session_state["query_lat"] = query_lat
                    st.session_state["query_lon"] = query_lon
                    st.session_state["query_label"] = f"{query_lat:.6f}, {query_lon:.6f}"
                    st.success(f"Parsed: {query_lat:.6f}, {query_lon:.6f}")
                else:
                    st.error("Could not parse coordinates. Check format.")

    elif input_method == "GeoJSON Upload":
        st.markdown("#### 📂 GeoJSON / KML File")
        st.caption("Upload a .geojson, .json, or .kml file with project boundaries.")
        uploaded = st.file_uploader(
            "Upload file:",
            type=["geojson", "json", "kml"],
            label_visibility="collapsed",
        )
        if uploaded:
            try:
                content = json.loads(uploaded.read())
                st.session_state["uploaded_geojson"] = content

                # Extract coordinates from GeoJSON
                features = content.get("features", [content] if content.get("type") == "Feature" else [])
                if not features and content.get("type") in ["Polygon", "MultiPolygon", "Point"]:
                    features = [{"type": "Feature", "geometry": content}]

                all_coords = []
                for feat in features:
                    geom = feat.get("geometry", {})
                    gtype = geom.get("type", "")
                    coords = geom.get("coordinates", [])

                    if gtype == "Point":
                        all_coords.append((coords[1], coords[0]))
                    elif gtype == "Polygon":
                        for ring in coords:
                            for c in ring:
                                all_coords.append((c[1], c[0]))
                    elif gtype == "MultiPolygon":
                        for poly in coords:
                            for ring in poly:
                                for c in ring:
                                    all_coords.append((c[1], c[0]))

                if all_coords:
                    avg_lat = sum(c[0] for c in all_coords) / len(all_coords)
                    avg_lon = sum(c[1] for c in all_coords) / len(all_coords)
                    st.session_state["query_lat"] = avg_lat
                    st.session_state["query_lon"] = avg_lon
                    st.session_state["query_label"] = f"GeoJSON centroid: {avg_lat:.6f}, {avg_lon:.6f}"

                    # If it's a polygon, store for envelope query
                    if len(all_coords) > 2:
                        polygon_coords = all_coords
                        st.session_state["polygon_coords"] = polygon_coords
                        multi_point = True
                        st.session_state["multi_point"] = True

                    st.success(f"Loaded {len(features)} feature(s), {len(all_coords)} coordinate(s)")

                    # Show preview
                    with st.expander("GeoJSON Preview"):
                        st.json(content)
                else:
                    st.warning("No coordinates found in file.")
            except Exception as e:
                st.error(f"Error parsing file: {e}")

    # Drawn polygon input from map
    st.markdown("---")
    st.markdown("#### ✏️ Draw on Map")
    st.caption("Use the polygon/rectangle tools on the map to define an area. Then paste the GeoJSON output here.")
    drawn_json = st.text_area(
        "Paste drawn GeoJSON:",
        height=100,
        placeholder='Paste the GeoJSON from the map textarea here...',
        label_visibility="collapsed",
    )
    if st.button("📐 Process Drawn Area", use_container_width=True):
        if drawn_json:
            try:
                gj = json.loads(drawn_json)
                features = gj.get("features", [])
                all_coords = []
                for feat in features:
                    geom = feat.get("geometry", {})
                    gtype = geom.get("type", "")
                    coords = geom.get("coordinates", [])
                    if gtype == "Polygon":
                        for ring in coords:
                            for c in ring:
                                all_coords.append((c[1], c[0]))
                    elif gtype == "Point":
                        all_coords.append((coords[1], coords[0]))

                if all_coords:
                    avg_lat = sum(c[0] for c in all_coords) / len(all_coords)
                    avg_lon = sum(c[1] for c in all_coords) / len(all_coords)
                    st.session_state["query_lat"] = avg_lat
                    st.session_state["query_lon"] = avg_lon
                    st.session_state["query_label"] = f"Drawn area centroid"
                    if len(all_coords) > 2:
                        st.session_state["polygon_coords"] = all_coords
                        st.session_state["multi_point"] = True
                    st.success(f"Processed {len(all_coords)} vertices")
                    st.rerun()
            except Exception as e:
                st.error(f"Invalid GeoJSON: {e}")

    # Use session state
    if query_lat is None and "query_lat" in st.session_state:
        query_lat = st.session_state["query_lat"]
        query_lon = st.session_state["query_lon"]
    if polygon_coords is None and "polygon_coords" in st.session_state:
        polygon_coords = st.session_state["polygon_coords"]
        multi_point = st.session_state.get("multi_point", False)


# ── Main Content ────────────────────────────────────────────────────────────

# Map
map_markers = []
if query_lat and query_lon:
    label = st.session_state.get("query_label", f"{query_lat:.6f}, {query_lon:.6f}")
    map_markers.append({"lat": query_lat, "lon": query_lon, "popup": label})

map_html = build_map_html(
    center_lat=query_lat or 28.5383,
    center_lon=query_lon or -81.3792,
    zoom=16 if query_lat else 11,
    markers=map_markers,
    polygon_coords=polygon_coords,
)

st.markdown('<div class="map-container">', unsafe_allow_html=True)
st.components.v1.html(map_html, height=570, scrolling=False)
st.markdown('</div>', unsafe_allow_html=True)


# ── Results ─────────────────────────────────────────────────────────────────

if query_lat and query_lon:
    # Jurisdiction determination
    jurisdiction = determine_jurisdiction(query_lat, query_lon)
    wmd = determine_water_management_district(query_lat)

    col_j1, col_j2 = st.columns(2)
    with col_j1:
        st.markdown(f"""
        <div class="info-card">
            <h3>🏛️ Jurisdiction</h3>
            <div class="role">{jurisdiction['jurisdiction']}</div>
            <div class="detail">{jurisdiction['note']}</div>
            <div class="detail" style="margin-top:6px;"><strong>Primary Permit Authority:</strong> {jurisdiction['primary_permit_authority']}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_j2:
        st.markdown(f"""
        <div class="info-card">
            <h3>💧 Water Management District</h3>
            <div class="role">{wmd}</div>
            <div class="detail">Environmental Resource Permits (ERP) for stormwater and wetland impacts are issued by this district.</div>
            <div class="detail" style="margin-top:4px;">
                <span class="status-info">Lat: {query_lat:.6f}</span>
                <span class="status-info">Lon: {query_lon:.6f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Parcel Query
    render_section_header("📋", "Parcel Data")

    with st.spinner("Querying Orange County parcel data..."):
        if multi_point and polygon_coords:
            # Envelope query
            lats = [c[0] for c in polygon_coords]
            lons = [c[1] for c in polygon_coords]
            parcels = query_parcels_by_envelope(min(lons), min(lats), max(lons), max(lats))
        else:
            parcels = query_oc_parcels(query_lat, query_lon)

    if parcels:
        st.markdown(f'<span class="status-ok">✓ {len(parcels)} parcel(s) found</span>', unsafe_allow_html=True)
        # Show parcels with expanders for large sets
        if len(parcels) <= 5:
            for i, p in enumerate(parcels):
                render_parcel_card(p, i)
        else:
            for i, p in enumerate(parcels[:3]):
                render_parcel_card(p, i)
            with st.expander(f"Show {len(parcels) - 3} more parcels"):
                for i, p in enumerate(parcels[3:], start=3):
                    render_parcel_card(p, i)

        # Raw data expander
        with st.expander("📊 Raw Parcel Data (JSON)"):
            st.json(parcels)
    else:
        st.markdown('<span class="status-warn">⚠ No parcel data returned – the ArcGIS service may be unavailable or coordinates are outside Orange County. Use the OCPA link below for manual lookup.</span>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="resource-card">
            <div class="res-name">Manual Parcel Search – Orange County Property Appraiser</div>
            <div class="res-desc">Search by address, owner name, or parcel ID directly on the OCPA website.</div>
            <div class="res-url"><a href="https://www.ocpafl.org/Searches/ParcelSearch.aspx" target="_blank">https://www.ocpafl.org/Searches/ParcelSearch.aspx</a></div>
        </div>
        """, unsafe_allow_html=True)

    # ── Resource URLs ───────────────────────────────────────────────────────
    render_section_header("🔗", "Engineering Resource URLs")
    st.caption("Direct links to the tools, portals, and databases you need for project research.")

    resource_tabs = st.tabs([
        "📐 GIS & Mapping",
        "🏗️ Permits & Dev",
        "📄 Plats & Surveys",
        "⚡ Utilities",
        "🌿 Environmental",
        "🏘️ HOA / CDD",
        "🚗 Transportation",
    ])

    resource_keys = [
        "gis_and_mapping",
        "permits_and_development",
        "plats_and_surveys",
        "utilities_and_infrastructure",
        "environmental_and_stormwater",
        "hoa_and_cdd",
        "transportation",
    ]

    for tab, key in zip(resource_tabs, resource_keys):
        with tab:
            for res in RESOURCES.get(key, []):
                render_resource_card(res)

    # ── Contacts ────────────────────────────────────────────────────────────
    render_section_header("📞", "Key Contacts")

    contact_tabs = st.tabs([
        "🏛️ Municipal Offices",
        "⚡ Utility Providers",
        "🌊 State & Regional",
    ])

    with contact_tabs[0]:
        for c in CONTACTS["municipal_offices"]:
            render_contact_card(c)

    with contact_tabs[1]:
        for c in CONTACTS["utility_providers"]:
            render_contact_card(c)

    with contact_tabs[2]:
        for c in CONTACTS["state_and_regional"]:
            render_contact_card(c)

else:
    # No query yet – show instructions
    st.markdown("---")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("""
        <div class="info-card">
            <h3>🏠 Address Search</h3>
            <div class="role">Enter any address format in the sidebar. Supports street address, city/state, partial addresses, and intersections.</div>
        </div>
        """, unsafe_allow_html=True)
    with col_b:
        st.markdown("""
        <div class="info-card">
            <h3>🌐 Coordinates</h3>
            <div class="role">Paste coordinates in decimal degrees, DMS, or with N/S/E/W indicators. The parser handles many formats automatically.</div>
        </div>
        """, unsafe_allow_html=True)
    with col_c:
        st.markdown("""
        <div class="info-card">
            <h3>📂 GeoJSON Upload</h3>
            <div class="role">Upload a .geojson or .json file with project boundaries. Polygon areas will query all intersecting parcels.</div>
        </div>
        """, unsafe_allow_html=True)

    st.info("👈 **Select an input method** in the sidebar to begin your research. You can also use the drawing tools on the map above to define an area.")

    # Still show resources and contacts even without a query
    render_section_header("🔗", "Engineering Resource URLs")
    st.caption("Browse available resources for Orange County infrastructure projects.")

    resource_tabs = st.tabs([
        "📐 GIS & Mapping",
        "🏗️ Permits & Dev",
        "📄 Plats & Surveys",
        "⚡ Utilities",
        "🌿 Environmental",
        "🏘️ HOA / CDD",
        "🚗 Transportation",
    ])

    resource_keys = [
        "gis_and_mapping",
        "permits_and_development",
        "plats_and_surveys",
        "utilities_and_infrastructure",
        "environmental_and_stormwater",
        "hoa_and_cdd",
        "transportation",
    ]

    for tab, key in zip(resource_tabs, resource_keys):
        with tab:
            for res in RESOURCES.get(key, []):
                render_resource_card(res)

    render_section_header("📞", "Key Contacts")
    contact_tabs = st.tabs([
        "🏛️ Municipal Offices",
        "⚡ Utility Providers",
        "🌊 State & Regional",
    ])
    with contact_tabs[0]:
        for c in CONTACTS["municipal_offices"]:
            render_contact_card(c)
    with contact_tabs[1]:
        for c in CONTACTS["utility_providers"]:
            render_contact_card(c)
    with contact_tabs[2]:
        for c in CONTACTS["state_and_regional"]:
            render_contact_card(c)


# ── Disclaimer ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="disclaimer">
    <strong>⚠️ Disclaimer:</strong> This tool provides reference information to assist with preliminary research.
    All data should be independently verified with the authoritative sources linked above before use in
    engineering design or permit applications. Parcel boundaries, zoning, and jurisdiction data are
    approximate. Contact the relevant municipal office to confirm all regulatory requirements for your
    specific project. Data sourced from Orange County Property Appraiser GIS, OpenStreetMap Nominatim,
    and publicly available government websites as of 2025.
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center; padding:1.5rem 0 0.5rem; color:#94a3b8; font-size:0.75rem;">
    OC Infrastructure Engineering Lookup Tool v1.0 · Orange County, Florida<br>
    Built for engineers, by engineers · Not an official government application
</div>
""", unsafe_allow_html=True)
