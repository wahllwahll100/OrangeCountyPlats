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
import urllib.parse
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
# Robust path resolution: try multiple locations so it works locally,
# on Streamlit Community Cloud, and in any deployment layout.

def _find_data_dir():
    """Search common locations for the data/ folder."""
    candidates = [
        Path(__file__).parent / "data",                    # same dir as app.py
        Path(__file__).resolve().parent / "data",          # resolved symlinks
        Path.cwd() / "data",                               # working directory
        Path("/mount/src/orangecountyplats/data"),         # Streamlit Cloud mount
    ]
    for p in candidates:
        if p.is_dir() and (p / "contacts.json").exists():
            return p
    return None

BASE_DIR = _find_data_dir()

@st.cache_data
def load_json_file(filename):
    """Load a JSON file from the data directory, or return None."""
    if BASE_DIR and (BASE_DIR / filename).exists():
        with open(BASE_DIR / filename, "r") as f:
            return json.load(f)
    return None

# ── Embedded fallback data (used when data/ dir is missing from repo) ───────
_CONTACTS_FALLBACK = {
  "municipal_offices": [
    {"name": "Orange County Development Engineering Division", "role": "Development review, permitting, and infrastructure approval", "phone": "(407) 836-7974", "email": "OCDevelopmentEng@ocfl.net", "address": "201 S. Rosalind Ave., 3rd Floor, Orlando, FL 32801", "url": "https://www.orangecountyfl.net/PlanningDevelopment/DevelopmentEngineering.aspx"},
    {"name": "Orange County Public Works Department", "role": "Road maintenance, stormwater, right-of-way permits", "phone": "(407) 836-7900", "email": "", "address": "4200 S. John Young Pkwy, Orlando, FL 32839", "url": "https://www.orangecountyfl.net/TrafficTransportation/PublicWorks.aspx"},
    {"name": "Orange County Planning Division", "role": "Zoning, land use, comprehensive plan", "phone": "(407) 836-5600", "email": "", "address": "201 S. Rosalind Ave., 1st Floor, Orlando, FL 32801", "url": "https://www.orangecountyfl.net/PlanningDevelopment/PlanningDivision.aspx"},
    {"name": "Orange County Property Appraiser", "role": "Parcel data, ownership records, property values", "phone": "(407) 836-5044", "email": "", "address": "200 S. Orange Ave., Suite 1700, Orlando, FL 32801", "url": "https://ocpaweb.ocpafl.org/"},
    {"name": "Orange County Comptroller – Official Records", "role": "Recorded plats, deeds, liens, easements", "phone": "(407) 836-5115", "email": "", "address": "109 E. Church St., Suite 300, Orlando, FL 32801", "url": "https://www.occompt.com/services/official-records/"},
    {"name": "Orange County Utilities Department", "role": "County water, wastewater, and reclaimed water services", "phone": "(407) 836-5515", "email": "", "address": "9150 Curry Ford Road, Orlando, FL 32825", "url": "https://www.orangecountyfl.net/NeighborsEnvironment/Utilities.aspx"},
    {"name": "Orange County Environmental Protection Division", "role": "Wetlands, environmental permits, stormwater compliance", "phone": "(407) 836-1400", "email": "", "address": "3165 McCrory Pl., Suite 200, Orlando, FL 32803", "url": "https://www.orangecountyfl.net/NeighborsEnvironment/EnvironmentalProtection.aspx"},
    {"name": "Orange County Building Safety Division", "role": "Building permits, inspections, code compliance", "phone": "(407) 836-5550", "email": "", "address": "201 S. Rosalind Ave., 2nd Floor, Orlando, FL 32801", "url": "https://www.orangecountyfl.net/PlanningDevelopment/BuildingSafety.aspx"},
    {"name": "City of Orlando – Permitting Services Division", "role": "City permits for projects within Orlando city limits", "phone": "(407) 246-2271", "email": "permits@orlando.gov", "address": "400 S. Orange Ave., Orlando, FL 32801", "url": "https://www.orlando.gov/Building-Development/Permitting"},
    {"name": "City of Orlando – Transportation Engineering", "role": "City roadway design, traffic studies, ROW within Orlando", "phone": "(407) 246-3347", "email": "", "address": "400 S. Orange Ave., Orlando, FL 32801", "url": "https://www.orlando.gov/Our-Government/Departments-Offices/Executive-Offices/Public-Works/Transportation-Engineering"}
  ],
  "utility_providers": [
    {"name": "Orlando Utilities Commission (OUC)", "role": "Electric & water for Orlando, parts of unincorporated OC", "phone": "(407) 423-9018", "email": "", "address": "100 W. Anderson St., Orlando, FL 32801", "url": "https://www.ouc.com/", "service_area_note": "City of Orlando and surrounding areas – call to confirm service territory"},
    {"name": "Duke Energy Florida", "role": "Electric service for parts of Orange County", "phone": "1-800-700-8744", "email": "", "address": "", "url": "https://www.duke-energy.com/home", "service_area_note": "Western and southern portions of Orange County"},
    {"name": "Toho Water Authority", "role": "Water and wastewater in Kissimmee area (bordering OC)", "phone": "(407) 944-5000", "email": "", "address": "951 Martin Luther King Blvd., Kissimmee, FL 34741", "url": "https://www.tohowater.com/", "service_area_note": "Primarily Osceola County – serves some areas near OC border"},
    {"name": "Orange County Utilities (Water/Wastewater)", "role": "Water, wastewater, and reclaimed water in unincorporated OC", "phone": "(407) 836-5515", "email": "", "address": "9150 Curry Ford Road, Orlando, FL 32825", "url": "https://www.orangecountyfl.net/NeighborsEnvironment/Utilities.aspx", "service_area_note": "Unincorporated Orange County service areas"},
    {"name": "City of Orlando Wastewater Division", "role": "Wastewater collection and treatment within Orlando", "phone": "(407) 246-2213", "email": "", "address": "5100 L.B. McLeod Road, Orlando, FL 32811", "url": "https://www.orlando.gov/Our-Government/Departments-Offices/Executive-Offices/Public-Works/Wastewater", "service_area_note": "Within Orlando city limits"},
    {"name": "Florida Gas Utility (FGU) / TECO Peoples Gas", "role": "Natural gas distribution", "phone": "1-877-832-6747", "email": "", "address": "", "url": "https://www.peoplesgas.com/", "service_area_note": "Gas service in Orange County"},
    {"name": "Summit Broadband / Spectrum / AT&T", "role": "Telecommunications & fiber", "phone": "", "email": "", "address": "", "url": "", "service_area_note": "Contact 811 (Sunshine 811) for telecom locate requests"},
    {"name": "Sunshine 811 (Florida One-Call)", "role": "Utility locate requests – REQUIRED before excavation", "phone": "811", "email": "", "address": "", "url": "https://www.sunshine811.com/", "service_area_note": "Statewide – required 2 full business days before digging"}
  ],
  "state_and_regional": [
    {"name": "Florida Department of Transportation – District 5", "role": "State road ROW, utility permits on state roads, drainage", "phone": "(386) 943-5000", "email": "", "address": "719 S. Woodland Blvd., DeLand, FL 32720", "url": "https://www.fdot.gov/programmanagement/district5.shtm"},
    {"name": "FDOT Utility Permits", "role": "Permits for utility work within FDOT right-of-way", "phone": "(386) 943-5393", "email": "", "address": "", "url": "https://www.fdot.gov/rightofway/utilitypage.shtm"},
    {"name": "South Florida Water Management District (SFWMD)", "role": "Environmental Resource Permits (ERP) for stormwater, wetlands", "phone": "(561) 686-8800", "email": "", "address": "3301 Gun Club Road, West Palm Beach, FL 33406", "url": "https://www.sfwmd.gov/doing-business-with-us/permits", "service_area_note": "Southern portion of Orange County"},
    {"name": "St. Johns River Water Management District (SJRWMD)", "role": "ERP for stormwater, wetlands, consumptive use permits", "phone": "(386) 329-4500", "email": "", "address": "4049 Reid St., Palatka, FL 32177", "url": "https://www.sjrwmd.com/permitting/", "service_area_note": "Northern portion of Orange County"},
    {"name": "Florida Department of Environmental Protection (FDEP)", "role": "Water quality, contamination, underground storage tanks", "phone": "(850) 245-2118", "email": "", "address": "", "url": "https://floridadep.gov/", "service_area_note": "Statewide environmental oversight"},
    {"name": "Central Florida Expressway Authority (CFX)", "role": "Toll roads, expressway ROW and utility crossings", "phone": "(407) 690-5000", "email": "", "address": "4974 ORL Tower Road, Orlando, FL 32807", "url": "https://www.cfxway.com/"}
  ]
}

_RESOURCES_FALLBACK = {
  "gis_and_mapping": [
    {"name": "Orange County GIS Interactive Map (OCGIS)", "url": "https://ocfl.maps.arcgis.com/home/index.html", "description": "Official Orange County ArcGIS portal – parcels, zoning, floodplains, aerial imagery"},
    {"name": "OCPA Property Search (New Site)", "url": "https://ocpaweb.ocpafl.org/parcelsearch", "description": "Search by address, owner, or parcel ID for ownership, legal description, assessed values – this is the current live site"},
    {"name": "OCPA Interactive GIS Map", "url": "https://maps.ocpafl.org/webmap/", "description": "Visual parcel map with ownership data, building footprints, aerials – click any parcel for details"},
    {"name": "OCPA Public GIS Map (Alternate)", "url": "https://vgispublic.ocpafl.org/webmapjs/", "description": "Alternate OCPA map viewer with boundary, reference, and redevelopment map layers"},
    {"name": "Orange County Comptroller – Official Records Search", "url": "https://or.occompt.com/recorder/web/", "description": "Search recorded plats, deeds, easements, liens, declarations of covenants (HOA docs) by book/page or name"},
    {"name": "FEMA Flood Map Service Center", "url": "https://msc.fema.gov/portal/home", "description": "FIRM maps, flood zones, Letters of Map Change for Orange County"},
    {"name": "Florida Geographic Data Library (FGDL)", "url": "https://www.fgdl.org/metadataexplorer/explorer.jsp", "description": "Statewide GIS data layers – parcels, soils, hydrology, land use"}
  ],
  "permits_and_development": [
    {"name": "Orange County ePlan / Accela Portal", "url": "https://aca-prod.accela.com/ORANGE/Default.aspx", "description": "Online permitting portal – submit and track development, building, and ROW permits"},
    {"name": "Orange County Development Engineering Standards", "url": "https://www.orangecountyfl.net/PlanningDevelopment/DevelopmentEngineering.aspx", "description": "Design standards, typical sections, stormwater management, subdivision requirements"},
    {"name": "Orange County Right-of-Way Use Permits", "url": "https://www.orangecountyfl.net/TrafficTransportation/PublicWorks.aspx", "description": "Permits for work within county right-of-way – utility installations, driveway connections"},
    {"name": "Orange County Zoning / Land Development Code", "url": "https://www.orangecountyfl.net/PlanningDevelopment/ComprehensivePlanning.aspx", "description": "Zoning regulations, future land use map, comprehensive plan documents"},
    {"name": "City of Orlando – ePlans Portal", "url": "https://aca-prod.accela.com/Orlando/", "description": "City of Orlando online permitting – for projects within city limits"},
    {"name": "FDOT District 5 – Utility Permit Application", "url": "https://www.fdot.gov/rightofway/utilitypage.shtm", "description": "Application for utility work within FDOT right-of-way (state roads, I-4, SR 408, etc.)"},
    {"name": "CFX Utility Permit Information", "url": "https://www.cfxway.com/agency-information/doing-business-with-cfx/", "description": "Permits for utility crossings of expressway authority roads (408, 417, 429, etc.)"}
  ],
  "plats_and_surveys": [
    {"name": "OCPA Property Card – Direct Parcel Lookup", "url": "https://ocpaweb.ocpafl.org/parcelsearch", "description": "New OCPA site: search by parcel ID, address, or owner name. Direct links to property cards are auto-generated per-parcel in results above."},
    {"name": "OCPA Interactive GIS Map", "url": "https://maps.ocpafl.org/webmap/", "description": "Interactive map with parcel boundaries, aerial imagery, zoning overlays. Click any parcel to view ownership and plat data."},
    {"name": "Orange County Comptroller – Official Records Search", "url": "https://or.occompt.com/recorder/web/", "description": "Search recorded plats by book/page, deeds, easements, liens, and HOA declarations. Use plat book/page from parcel data above."},
    {"name": "Orange County Comptroller – Plat & Document Search Tips", "url": "https://www.occompt.com/official-records/search-official-records/", "description": "Help page for searching official records including plats, deeds, and covenants. Includes video tutorial."},
    {"name": "Florida Board of Professional Surveyors & Mappers", "url": "https://floridasurveyingandmapping.org/", "description": "Licensed surveyor lookup, survey standards, boundary dispute resources"}
  ],
  "utilities_and_infrastructure": [
    {"name": "OUC – Development Services / New Construction", "url": "https://www.ouc.com/builders-and-developers", "description": "OUC requirements for new electric and water service, line extensions, fees"},
    {"name": "Orange County Utilities – Developer Handbook", "url": "https://www.orangecountyfl.net/NeighborsEnvironment/Utilities.aspx", "description": "County water/sewer extension policies, tap fees, availability letters"},
    {"name": "Sunshine 811 – Utility Locate Request", "url": "https://www.sunshine811.com/", "description": "REQUIRED before excavation – submit locate requests 2 full business days in advance"},
    {"name": "Duke Energy – Builder/Developer Services", "url": "https://www.duke-energy.com/business/products/builder-services", "description": "Electric service requests for new construction in Duke Energy territory"},
    {"name": "Peoples Gas – New Service / Line Extension", "url": "https://www.peoplesgas.com/business/builders-developers/", "description": "Natural gas service availability and new service requests"}
  ],
  "environmental_and_stormwater": [
    {"name": "SJRWMD – ePermitting Portal", "url": "https://permitting.sjrwmd.com/epermitting/", "description": "Environmental Resource Permits for stormwater and wetland impacts (north OC)"},
    {"name": "SFWMD – ePermitting Portal", "url": "https://my.sfwmd.gov/ePermitting/", "description": "Environmental Resource Permits for stormwater and wetland impacts (south OC)"},
    {"name": "Orange County Stormwater Management", "url": "https://www.orangecountyfl.net/NeighborsEnvironment/Stormwater.aspx", "description": "County stormwater design criteria, MS4 permit, drainage requirements"},
    {"name": "FDEP – Map Direct (Contamination, Tanks, etc.)", "url": "https://ca.dep.state.fl.us/mapdirect/", "description": "Search for contamination sites, underground storage tanks, cleanup sites"},
    {"name": "USFWS National Wetlands Inventory", "url": "https://www.fws.gov/program/national-wetlands-inventory/wetlands-mapper", "description": "Wetland boundaries and classifications for environmental screening"}
  ],
  "hoa_and_cdd": [
    {"name": "Florida DBPR – HOA / Condo Search", "url": "https://www.myfloridalicense.com/wl11.asp", "description": "Search registered HOAs, condominiums, and cooperatives by name or location"},
    {"name": "Orange County Comptroller – Covenant Search", "url": "https://www.occompt.com/services/official-records/search-official-records/", "description": "Search recorded Declarations of Covenants, Conditions & Restrictions (CC&Rs)"},
    {"name": "Florida Special District Accountability Program", "url": "https://specialdistrictreports.floridajobs.org/webreports/main.aspx", "description": "Search Community Development Districts (CDDs) – governance, boundaries, financials"},
    {"name": "Orange County Special Districts", "url": "https://www.orangecountyfl.net/BoardCommissions/SpecialDistricts.aspx", "description": "County-managed special districts, CDDs, and dependent districts"}
  ],
  "transportation": [
    {"name": "Orange County Traffic Engineering", "url": "https://www.orangecountyfl.net/TrafficTransportation/TrafficEngineering.aspx", "description": "Traffic counts, signal information, road classifications, speed studies"},
    {"name": "FDOT – Traffic Online / Florida Traffic Online", "url": "https://tdaappsprod.dot.state.fl.us/fto/", "description": "Statewide traffic counts, road characteristics, AADT data"},
    {"name": "Orange County Road Network / GIS", "url": "https://ocfl.maps.arcgis.com/home/index.html", "description": "Road classifications, maintenance responsibility, ROW widths"},
    {"name": "MetroPlan Orlando", "url": "https://metroplanorlando.org/", "description": "Regional transportation planning, long-range plans, funded project lists"}
  ]
}

CONTACTS = load_json_file("contacts.json") or _CONTACTS_FALLBACK
RESOURCES = load_json_file("resources.json") or _RESOURCES_FALLBACK

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
    """Geocode an address using multiple services for parcel-level accuracy.
    
    Priority:
      1. US Census Bureau Geocoder – most precise for US street addresses,
         returns rooftop-level coordinates. Free, no API key.
      2. Nominatim (OSM) – broader coverage but less precise for parcels.
    """
    addr_lower = address.lower()
    # Normalize: ensure state is present for Census geocoder
    if ', fl' not in addr_lower and 'florida' not in addr_lower:
        if 'orlando' in addr_lower or 'orange county' in addr_lower:
            if ', fl' not in addr_lower:
                address = address.rstrip().rstrip(',') + ", FL"
        else:
            address = address.rstrip().rstrip(',') + ", Orlando, FL"

    # ── Try 1: US Census Bureau Geocoder ────────────────────────────────
    try:
        url = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
        params = {
            "address": address,
            "benchmark": "Public_AR_Current",
            "format": "json",
        }
        resp = requests.get(url, params=params, timeout=12)
        data = resp.json()
        matches = data.get("result", {}).get("addressMatches", [])
        if matches:
            best = matches[0]
            coords = best.get("coordinates", {})
            matched_addr = best.get("matchedAddress", address)
            return {
                "lat": float(coords["y"]),
                "lon": float(coords["x"]),
                "display_name": matched_addr,
                "address_parts": best.get("addressComponents", {}),
                "source": "US Census Bureau",
                "match_quality": "rooftop",
            }
    except Exception:
        pass  # Fall through to Nominatim

    # ── Try 2: Nominatim (OSM) ──────────────────────────────────────────
    try:
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
                "source": "Nominatim (OSM)",
                "match_quality": best.get("type", "unknown"),
            }
    except Exception as e:
        st.warning(f"Geocoding error: {e}")

    return None


def _query_arcgis(endpoint_url: str, params: dict, timeout: int = 20) -> list:
    """Helper: query a single ArcGIS REST endpoint and return feature attributes."""
    try:
        headers = {"User-Agent": "OC-InfraLookup/1.0 (Streamlit)"}
        resp = requests.get(endpoint_url, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            return []
        if "features" in data and len(data["features"]) > 0:
            return [feat.get("attributes", {}) for feat in data["features"]]
    except Exception:
        pass
    return []


# ── Endpoint definitions ────────────────────────────────────────────────────
# Priority 1: Florida Statewide Cadastral on ArcGIS Online (Esri-hosted, public)
#   Fields: PARCEL_ID, CO_NO (Orange=95), ASMNT_YR, PHY_ADDR1, PHY_CITY, 
#           PHY_ZIPCD, OWN_NAME, JV, AV_SD, TV_SD, etc.
_STATEWIDE_PARCELS_URL = (
    "https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/"
    "Florida_Statewide_Cadastral/FeatureServer/0/query"
)

# Priority 2: OCPA endpoints (may block cloud server IPs)
_OCPA_ENDPOINTS = [
    "https://vgispublic.ocpafl.org/server/rest/services/DynamicForJs/OCPA/MapServer/3/query",
    "https://vgispublic.ocpafl.org/server/rest/services/Oakland/PARCEL/MapServer/0/query",
    "https://maps.ocpafl.org/arcgis/rest/services/DynamicOCPA/MapServer/0/query",
]


def query_oc_parcels(lat: float, lon: float, radius_m: float = 50) -> list:
    """Query parcel data near a point. Tries ArcGIS Online first, then OCPA."""
    parcels = []

    # ── Try 1: Florida Statewide Cadastral (ArcGIS Online – always accessible) ──
    # No WHERE filter needed — the spatial intersection constrains to this location.
    parcels = _query_arcgis(_STATEWIDE_PARCELS_URL, {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "spatialRel": "esriSpatialRelIntersects",
        "inSR": "4326",
        "outSR": "4326",
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "false",
        "f": "json",
    }, timeout=20)

    if parcels:
        return parcels

    # ── Try 2: OCPA direct endpoints (fallback) ──
    for ep in _OCPA_ENDPOINTS:
        parcels = _query_arcgis(ep, {
            "geometry": f"{lon},{lat}",
            "geometryType": "esriGeometryPoint",
            "spatialRel": "esriSpatialRelIntersects",
            "inSR": "4326",
            "outSR": "4326",
            "outFields": "*",
            "returnGeometry": "false",
            "f": "json",
        }, timeout=15)
        if parcels:
            return parcels

    return []


def query_parcels_by_envelope(min_lon, min_lat, max_lon, max_lat) -> list:
    """Query parcels within a bounding box."""
    parcels = _query_arcgis(_STATEWIDE_PARCELS_URL, {
        "geometry": f"{min_lon},{min_lat},{max_lon},{max_lat}",
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "inSR": "4326",
        "outSR": "4326",
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "false",
        "resultRecordCount": 100,
        "f": "json",
    }, timeout=25)

    if parcels:
        return parcels

    for ep in _OCPA_ENDPOINTS:
        parcels = _query_arcgis(ep, {
            "geometry": f"{min_lon},{min_lat},{max_lon},{max_lat}",
            "geometryType": "esriGeometryEnvelope",
            "spatialRel": "esriSpatialRelIntersects",
            "inSR": "4326",
            "outSR": "4326",
            "outFields": "*",
            "returnGeometry": "false",
            "resultRecordCount": 100,
            "f": "json",
        }, timeout=20)
        if parcels:
            return parcels

    return []


def query_parcels_by_polygon(rings: list) -> list:
    """Query parcels intersecting a polygon."""
    geom = json.dumps({"rings": rings, "spatialReference": {"wkid": 4326}})

    parcels = _query_arcgis(_STATEWIDE_PARCELS_URL, {
        "geometry": geom,
        "geometryType": "esriGeometryPolygon",
        "spatialRel": "esriSpatialRelIntersects",
        "inSR": "4326",
        "outSR": "4326",
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "false",
        "resultRecordCount": 200,
        "f": "json",
    }, timeout=25)

    if parcels:
        return parcels

    for ep in _OCPA_ENDPOINTS:
        parcels = _query_arcgis(ep, {
            "geometry": geom,
            "geometryType": "esriGeometryPolygon",
            "spatialRel": "esriSpatialRelIntersects",
            "inSR": "4326",
            "outSR": "4326",
            "outFields": "*",
            "returnGeometry": "false",
            "resultRecordCount": 200,
            "f": "json",
        }, timeout=20)
        if parcels:
            return parcels

    return []


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
    """Render a single parcel result card with direct deep-links.

    Key URL patterns (verified):
      OCPA GIS Map  → https://vgispublic.ocpafl.org/webmapjs/?pid={PARCEL_ID}
      OCPA Prop Card → https://ocpaweb.ocpafl.org/parcelsearch/Parcel%20ID/{PARCEL_ID}
      OCPA Mobile    → https://maps.ocpafl.org/m/Home/ParcelInfo?para=&pid={PARCEL_ID}
    """
    # Field aliases: maps our keys to ArcGIS field names from both
    # the Florida Statewide Cadastral service AND OCPA's own GIS layers.
    field_map = {
        "parcel_id": ["PARCEL_ID", "PARCELNO", "PARCELID", "PARCEL", "PIN",
                       "PARNO", "PARCEL_NUMBER", "PARID", "PARCEL_NUM", "PID"],
        "owner":     ["OWN_NAME", "OWNER", "OWNER1", "OWN_NAME1", "OWNERNAME",
                       "NAME1"],
        "address":   ["PHY_ADDR1", "SITEADDR", "SITE_ADDR", "ADDRESS", "SITUS",
                       "SITUS_ADDR", "SITUSADDRESS", "SITUS_ADDRESS"],
        "city":      ["PHY_CITY", "SITUSCITY", "CITY", "SITUS_CITY"],
        "zip":       ["PHY_ZIPCD", "SITUSZIP", "ZIP", "ZIPCODE", "SITUS_ZIP"],
        "use_code":  ["DOR_UC", "USECODE", "USE_CODE", "LANDUSE", "DESSION",
                       "DOR_CODE"],
        "zoning":    ["ZONING", "ZONE", "ZONE_CODE", "ZONING_CODE"],
        "acreage":   ["ACREAGE", "ACRES", "AREA_ACRES", "GISACRES", "TOT_LND_AR",
                       "LND_SQFOOT"],
        "legal":     ["LEGAL", "LEGALDESC", "LEGAL_DESC", "LEGAL1"],
        "subdivision": ["SUBDIVISION", "SUBDIV", "PLATNAME", "PLAT_NAME"],
        "plat_book": ["PLATBOOK", "PLAT_BOOK", "PB"],
        "plat_page": ["PLATPAGE", "PLAT_PAGE", "PP"],
        "just_value": ["JV", "JUSTVALUE", "JUST_VALUE", "MARKET_VAL", "JV_HMSTD"],
        "assessed":  ["AV_SD", "TOTAL_ASSD"],
        "taxable":   ["TV_SD", "TAXABLE", "TV_NSD"],
        "deed_book": ["DEED_BK", "DEEDBOOK"],
        "deed_page": ["DEED_PG", "DEEDPAGE"],
        "deed_inst": ["DEED_INST", "INSTRUMENT", "INST_NUM"],
    }

    def find_field(key):
        for candidate in field_map.get(key, []):
            for pk, pv in parcel.items():
                if pk.upper() == candidate.upper() and pv is not None and str(pv).strip():
                    val = str(pv).strip()
                    if val and val != "0" and val != "None":
                        return val
        return None

    pid       = find_field("parcel_id") or "N/A"
    owner     = find_field("owner") or "N/A"
    addr      = find_field("address") or "N/A"
    city      = find_field("city") or ""
    zipcode   = find_field("zip") or ""
    use       = find_field("use_code") or "N/A"
    zoning    = find_field("zoning") or "—"
    acres     = find_field("acreage") or "—"
    legal     = find_field("legal") or "—"
    subdiv    = find_field("subdivision") or "—"
    pb        = find_field("plat_book") or ""
    pp        = find_field("plat_page") or ""
    jv        = find_field("just_value") or "—"
    deed_bk   = find_field("deed_book") or ""
    deed_pg   = find_field("deed_page") or ""
    deed_inst = find_field("deed_inst") or ""

    plat_ref  = f"PB {pb} / PG {pp}" if pb and pp else "—"
    deed_ref  = f"BK {deed_bk} / PG {deed_pg}" if deed_bk and deed_pg else ""
    full_addr = f"{addr}, {city} {zipcode}".strip(", ")

    # ── Build DIRECT deep-links (parcel-specific) ────────────────────────
    has_pid = pid and pid != "N/A"
    pid_clean = pid.replace("-", "").replace(" ", "") if has_pid else ""

    # 1. OCPA GIS Map → opens the map zoomed to this exact parcel
    #    VERIFIED pattern: https://vgispublic.ocpafl.org/webmapjs/?pid=292235309203120
    if has_pid:
        gis_map_url = f"https://vgispublic.ocpafl.org/webmapjs/?pid={urllib.parse.quote(pid_clean)}"
        gis_map_link = f'<a href="{gis_map_url}" target="_blank">{gis_map_url}</a>'
    else:
        gis_map_url = "https://vgispublic.ocpafl.org/webmapjs/"
        gis_map_link = f'<a href="{gis_map_url}" target="_blank">Open OCPA GIS Map (no parcel ID available) →</a>'

    # 2. OCPA Property Card → full valuation detail for this parcel
    #    Pattern: https://ocpaweb.ocpafl.org/parcelsearch/Parcel%20ID/{PARCEL_ID}
    if has_pid:
        prop_card_url = f"https://ocpaweb.ocpafl.org/parcelsearch/Parcel%20ID/{urllib.parse.quote(pid_clean)}"
        prop_card_link = f'<a href="{prop_card_url}" target="_blank">{prop_card_url}</a>'
    else:
        prop_card_url = "https://ocpaweb.ocpafl.org/parcelsearch"
        prop_card_link = f'<a href="{prop_card_url}" target="_blank">Search OCPA manually →</a>'

    # 3. OCPA Mobile Parcel Info
    #    Pattern: https://maps.ocpafl.org/m/Home/ParcelInfo?para=&pid={PARCEL_ID}
    if has_pid:
        mobile_url = f"https://maps.ocpafl.org/m/Home/ParcelInfo?para=&pid={urllib.parse.quote(pid_clean)}"
        mobile_link = f'<a href="{mobile_url}" target="_blank">OCPA Mobile View →</a>'
    else:
        mobile_link = ""

    # 4. Comptroller Official Records – plat book/page lookup
    comptroller_base = "https://or.occompt.com/recorder/web/"
    if pb and pp:
        comptroller_plat_link = f'<a href="{comptroller_base}" target="_blank">Search Comptroller Records (PB {pb} / PG {pp}) →</a>'
    else:
        comptroller_plat_link = f'<a href="{comptroller_base}" target="_blank">Search Official Records →</a>'

    # 5. Deed lookup
    if deed_inst:
        comptroller_deed_link = f'<a href="{comptroller_base}" target="_blank">Look Up Deed (Inst# {deed_inst}) →</a>'
    elif deed_bk and deed_pg:
        comptroller_deed_link = f'<a href="{comptroller_base}" target="_blank">Look Up Deed (BK {deed_bk}/PG {deed_pg}) →</a>'
    else:
        comptroller_deed_link = ""

    # 6. Tax Collector
    tax_link = f'<a href="https://www.octaxcol.com/" target="_blank">Tax Collector Lookup →</a>' if has_pid else ""

    # ── Assemble the links block ─────────────────────────────────────────
    links_html = f"""
        <div class="field" style="margin-top:10px; padding-top:8px; border-top:2px solid #0f4c75;">
            <span class="label" style="color:#0f4c75; font-weight:700; font-size:0.9rem;">🔗 Direct Links for This Parcel:</span>
        </div>
        <div class="field"><span class="label">📍 OCPA GIS Map:</span><span class="value">{gis_map_link}</span></div>
        <div class="field"><span class="label">📄 Property Card:</span><span class="value">{prop_card_link}</span></div>
    """
    if mobile_link:
        links_html += f'<div class="field"><span class="label">📱 Mobile View:</span><span class="value">{mobile_link}</span></div>'
    links_html += f'<div class="field"><span class="label">📑 Plat Records:</span><span class="value">{comptroller_plat_link}</span></div>'
    if comptroller_deed_link:
        links_html += f'<div class="field"><span class="label">📜 Deed Records:</span><span class="value">{comptroller_deed_link}</span></div>'
    if tax_link:
        links_html += f'<div class="field"><span class="label">💰 Tax Info:</span><span class="value">{tax_link}</span></div>'

    # ── Render the card ──────────────────────────────────────────────────
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
        {"<div class='field'><span class='label'>Deed Reference:</span><span class='value'>" + deed_ref + "</span></div>" if deed_ref else ""}
        {"<div class='field'><span class='label'>Instrument #:</span><span class='value'>" + deed_inst + "</span></div>" if deed_inst else ""}
        <div class="field"><span class="label">Legal Desc:</span><span class="value">{legal[:150]}{'...' if len(legal) > 150 else ''}</span></div>
        <div class="field"><span class="label">Just Value:</span><span class="value">${jv}</span></div>
        {links_html}
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
    """Generate a Leaflet map with CLIENT-SIDE parcel querying.
    
    The user's browser calls OCPA ArcGIS endpoints directly, bypassing
    any bot detection that blocks server-side requests from Streamlit Cloud.
    """
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
            color: '#f7a325', weight: 3, fillColor: '#f7a325', fillOpacity: 0.15
        }}).addTo(map);
        map.fitBounds(polygon.getBounds().pad(0.1));
        """

    # Auto-query on load if we have a marker
    auto_query_js = ""
    if len(markers) == 1:
        auto_query_js = f"setTimeout(function(){{ queryParcel({markers[0]['lat']}, {markers[0]['lon']}); }}, 800);"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.css" />
        <style>
            @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
            * {{ margin:0; padding:0; box-sizing:border-box; }}
            body {{ font-family:'DM Sans',sans-serif; background:transparent; }}
            #map {{ width:100%; height:450px; border-radius:10px 10px 0 0; }}
            .coord-display {{
                position:absolute; bottom:10px; left:10px; z-index:1000;
                background:rgba(12,27,42,0.85); color:#a8c7e2;
                padding:6px 12px; border-radius:6px; font-family:'JetBrains Mono',monospace;
                font-size:11px; backdrop-filter:blur(4px);
            }}
            .map-instructions {{
                position:absolute; top:10px; right:10px; z-index:1000;
                background:rgba(12,27,42,0.92); color:white;
                padding:10px 14px; border-radius:8px; font-size:11px;
                max-width:200px; line-height:1.4;
            }}
            .map-instructions strong {{ color:#f7a325; }}

            /* Results panel below the map */
            #results-panel {{
                background:#f8fafc; border:1px solid #e2e8f0;
                border-top:3px solid #0f4c75;
                border-radius:0 0 10px 10px;
                padding:16px 20px; min-height:60px;
                font-size:13px; color:#334155;
            }}
            #results-panel.loading {{
                background:repeating-linear-gradient(-45deg,#f8fafc,#f8fafc 10px,#f0f4f8 10px,#f0f4f8 20px);
                background-size:28px 28px;
                animation:barberpole 1s linear infinite;
            }}
            @keyframes barberpole {{ 0%{{background-position:0 0}} 100%{{background-position:28px 0}} }}

            .parcel-card {{
                background:linear-gradient(135deg,#f0f7ff,#e8f4f8);
                border:1px solid #bdd8f1; border-radius:8px;
                padding:14px 16px; margin-bottom:10px;
            }}
            .parcel-card h3 {{
                color:#0c1b2a; font-size:15px; font-weight:700; margin:0 0 8px 0;
            }}
            .parcel-card .row {{
                display:flex; gap:6px; margin:3px 0; font-size:12px;
            }}
            .parcel-card .lbl {{
                font-weight:600; color:#475569; min-width:110px; flex-shrink:0;
            }}
            .parcel-card .val {{
                color:#1e293b; font-family:'JetBrains Mono',monospace; font-size:11.5px;
                word-break:break-all;
            }}
            .parcel-card a {{ color:#0f4c75; font-weight:500; text-decoration:none; }}
            .parcel-card a:hover {{ text-decoration:underline; }}
            .links-section {{
                margin-top:10px; padding-top:10px;
                border-top:2px solid #0f4c75;
            }}
            .links-section .link-title {{
                font-weight:700; color:#0f4c75; font-size:13px; margin-bottom:6px;
            }}
            .links-section .link-row {{
                display:flex; gap:6px; margin:4px 0; font-size:12px; align-items:baseline;
            }}
            .links-section .link-label {{
                font-weight:600; color:#475569; min-width:120px; flex-shrink:0;
            }}
            .links-section a {{
                color:#0f4c75; font-family:'JetBrains Mono',monospace; font-size:11px;
                word-break:break-all;
            }}
            .status-msg {{
                padding:8px 12px; border-radius:6px; font-size:12px; margin:4px 0;
            }}
            .status-msg.ok {{ background:#dcfce7; color:#166534; }}
            .status-msg.warn {{ background:#fef3c7; color:#92400e; }}
            .status-msg.info {{ background:#dbeafe; color:#1e40af; }}

            #geojson-output {{ display:none; }}
        </style>
    </head>
    <body>
        <div id="map"></div>
        <div class="coord-display" id="coords">Click the map to query a parcel</div>
        <div class="map-instructions">
            <strong>Click map</strong> to query parcel data.<br>
            <strong>Draw tools</strong> (left) for polygon areas.<br>
            Deep links auto-generated below.
        </div>
        <div id="results-panel">
            <div class="status-msg info">👆 Click anywhere on the map to query parcel data, or use the sidebar to search by address.</div>
        </div>
        <textarea id="geojson-output"></textarea>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.js"></script>
        <script>
        var map = L.map('map').setView([{center_lat}, {center_lon}], {zoom});

        // ── Tile layers ──
        var osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution:'© OpenStreetMap', maxZoom:19
        }});
        var esriImg = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            attribution:'© Esri', maxZoom:19
        }});
        var esriTopo = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            attribution:'© Esri', maxZoom:19
        }});
        osm.addTo(map);
        L.control.layers({{"Street Map":osm,"Satellite":esriImg,"Topographic":esriTopo}}).addTo(map);

        // ── Draw control ──
        var drawnItems = new L.FeatureGroup();
        map.addLayer(drawnItems);
        map.addControl(new L.Control.Draw({{
            draw:{{
                polygon:{{ allowIntersection:false, shapeOptions:{{color:'#f7a325',weight:3,fillOpacity:0.12}} }},
                rectangle:{{ shapeOptions:{{color:'#f7a325',weight:3,fillOpacity:0.12}} }},
                circle:false, circlemarker:false, marker:true, polyline:false
            }},
            edit:{{ featureGroup:drawnItems, remove:true }}
        }}));
        map.on(L.Draw.Event.CREATED, function(e){{ drawnItems.addLayer(e.layer); updateGeoJSON(); }});
        map.on(L.Draw.Event.EDITED, function(){{ updateGeoJSON(); }});
        map.on(L.Draw.Event.DELETED, function(){{ updateGeoJSON(); }});
        function updateGeoJSON(){{
            var gj = drawnItems.toGeoJSON();
            document.getElementById('geojson-output').style.display='block';
            document.getElementById('geojson-output').value=JSON.stringify(gj,null,2);
        }}

        // ── Coordinate display ──
        map.on('mousemove', function(e){{
            document.getElementById('coords').innerHTML='Lat: '+e.latlng.lat.toFixed(6)+'  |  Lon: '+e.latlng.lng.toFixed(6);
        }});

        // ── CLIENT-SIDE PARCEL QUERY ENGINE ──
        // These endpoints run from YOUR BROWSER, not from the server.
        // OCPA allows browser requests (same as their own web map).

        var ENDPOINTS = [
            // OCPA DynamicForJs – has PID, ACREAGE, DOR_CODE, ZONING_CODE
            'https://vgispublic.ocpafl.org/server/rest/services/DynamicForJs/OCPA/MapServer/3/query',
            // OCPA Oakland parcel layer
            'https://vgispublic.ocpafl.org/server/rest/services/Oakland/PARCEL/MapServer/0/query',
            // OCPA Dynamic via maps subdomain
            'https://maps.ocpafl.org/arcgis/rest/services/DynamicOCPA/MapServer/0/query',
            // Florida Statewide Cadastral (ArcGIS Online, always public)
            'https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/Florida_Statewide_Cadastral/FeatureServer/0/query'
        ];

        var queryMarker = null;

        function showPanel(html) {{
            document.getElementById('results-panel').className = '';
            document.getElementById('results-panel').innerHTML = html;
        }}

        function showLoading() {{
            document.getElementById('results-panel').className = 'loading';
            document.getElementById('results-panel').innerHTML = '<div class="status-msg info">⏳ Querying OCPA parcel data from your browser...</div>';
        }}

        // Try each endpoint in sequence until one returns features
        async function queryParcel(lat, lon) {{
            showLoading();

            // Place/move marker
            if(queryMarker) map.removeLayer(queryMarker);
            queryMarker = L.marker([lat, lon], {{
                icon: L.divIcon({{
                    html:'<div style="background:#e63946;color:white;width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:bold;border:2px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.4);">📍</div>',
                    iconSize:[30,30], iconAnchor:[15,15], className:''
                }})
            }}).addTo(map);

            var features = null;
            var successEndpoint = '';

            for (var i = 0; i < ENDPOINTS.length; i++) {{
                try {{
                    var url = ENDPOINTS[i]
                        + '?geometry=' + lon + ',' + lat
                        + '&geometryType=esriGeometryPoint'
                        + '&spatialRel=esriSpatialRelIntersects'
                        + '&inSR=4326&outSR=4326'
                        + '&where=1%3D1'
                        + '&outFields=*'
                        + '&returnGeometry=false'
                        + '&f=json';

                    var resp = await fetch(url, {{ signal: AbortSignal.timeout(12000) }});
                    var data = await resp.json();

                    if (data.features && data.features.length > 0) {{
                        features = data.features;
                        successEndpoint = ENDPOINTS[i];
                        break;
                    }}
                }} catch(e) {{
                    // Try next endpoint
                    continue;
                }}
            }}

            if (!features || features.length === 0) {{
                showPanel(
                    '<div class="status-msg warn">⚠ No parcel data returned from any endpoint at this location. '
                    + 'This may be outside Orange County or on unplatted land.</div>'
                    + '<div class="status-msg info" style="margin-top:8px;">'
                    + '🔗 Try manual lookup: <a href="https://vgispublic.ocpafl.org/webmapjs/" target="_blank">OCPA GIS Map</a>'
                    + ' · <a href="https://ocpaweb.ocpafl.org/parcelsearch" target="_blank">OCPA Property Search</a></div>'
                );
                return;
            }}

            // ── Build results HTML ──
            var html = '<div class="status-msg ok">✓ ' + features.length + ' parcel(s) found via ' + extractHost(successEndpoint) + '</div>';

            for (var f = 0; f < features.length; f++) {{
                var a = features[f].attributes;
                var pid = findAttr(a, ['PARCEL_ID','PARCELNO','PARCELID','PIN','PID','PARNO']) || 'N/A';
                var owner = findAttr(a, ['OWN_NAME','OWNER','OWNER1','NAME1','OWNERNAME']) || 'N/A';
                var addr = findAttr(a, ['PHY_ADDR1','SITEADDR','SITE_ADDR','ADDRESS','SITUS_ADDR']) || 'N/A';
                var city = findAttr(a, ['PHY_CITY','SITUSCITY','CITY']) || '';
                var zip = findAttr(a, ['PHY_ZIPCD','SITUSZIP','ZIP']) || '';
                var dorCode = findAttr(a, ['DOR_UC','DOR_CODE','USECODE','USE_CODE']) || '—';
                var zoning = findAttr(a, ['ZONING','ZONING_CODE','ZONE','ZONE_CODE']) || '—';
                var acreage = findAttr(a, ['ACREAGE','ACRES','LND_SQFOOT']) || '—';
                var jv = findAttr(a, ['JV','JUSTVALUE','JUST_VALUE','TOTAL_MKT']) || '—';

                var pidClean = pid.replace(/[-\\s]/g, '');
                var fullAddr = addr + (city ? ', ' + city : '') + (zip ? ' ' + zip : '');

                // Deep links
                var gisMapUrl  = 'https://vgispublic.ocpafl.org/webmapjs/?pid=' + encodeURIComponent(pidClean);
                var propCardUrl = 'https://ocpaweb.ocpafl.org/parcelsearch/Parcel%20ID/' + encodeURIComponent(pidClean);
                var mobileUrl  = 'https://maps.ocpafl.org/m/Home/ParcelInfo?para=&pid=' + encodeURIComponent(pidClean);
                var comptUrl   = 'https://or.occompt.com/recorder/web/';

                html += '<div class="parcel-card">';
                html += '<h3>📋 Parcel #' + (f+1) + ': ' + pid + '</h3>';
                html += row('Owner', owner);
                html += row('Site Address', fullAddr);
                html += row('DOR Use Code', dorCode);
                html += row('Zoning', zoning);
                html += row('Acreage', acreage);
                html += row('Just Value', jv !== '—' ? '$' + Number(jv).toLocaleString() : '—');

                if (pid !== 'N/A') {{
                    html += '<div class="links-section">';
                    html += '<div class="link-title">🔗 Direct Links for This Parcel:</div>';
                    html += linkRow('📍 OCPA GIS Map', gisMapUrl);
                    html += linkRow('📄 Property Card', propCardUrl);
                    html += linkRow('📱 Mobile View', mobileUrl);
                    html += linkRow('📑 Official Records', comptUrl);
                    html += '</div>';
                }}
                html += '</div>';
            }}

            // Show raw field names for diagnostics
            html += '<details style="margin-top:8px;font-size:11px;color:#64748b;"><summary>Debug: raw fields from GIS</summary>';
            html += '<pre style="font-size:10px;max-height:150px;overflow:auto;background:#f1f5f9;padding:8px;border-radius:4px;">';
            html += JSON.stringify(features[0].attributes, null, 2);
            html += '</pre></details>';

            showPanel(html);

            // Also send parcel data up to Streamlit parent
            try {{
                window.parent.postMessage({{
                    type: 'parcel_result',
                    parcels: features.map(function(f){{ return f.attributes; }}),
                    endpoint: successEndpoint
                }}, '*');
            }} catch(e) {{}}
        }}

        // Helpers
        function findAttr(attrs, keys) {{
            for (var i = 0; i < keys.length; i++) {{
                // Try exact match first, then case-insensitive
                if (attrs[keys[i]] !== undefined && attrs[keys[i]] !== null && String(attrs[keys[i]]).trim() !== '' && String(attrs[keys[i]]) !== '0') {{
                    return String(attrs[keys[i]]).trim();
                }}
                for (var k in attrs) {{
                    if (k.toUpperCase() === keys[i].toUpperCase() && attrs[k] !== null && String(attrs[k]).trim() !== '' && String(attrs[k]) !== '0') {{
                        return String(attrs[k]).trim();
                    }}
                }}
            }}
            return null;
        }}
        function extractHost(url) {{
            try {{ return new URL(url).hostname; }} catch(e) {{ return url; }}
        }}
        function row(label, value) {{
            return '<div class="row"><span class="lbl">' + label + ':</span><span class="val">' + value + '</span></div>';
        }}
        function linkRow(label, url) {{
            return '<div class="link-row"><span class="link-label">' + label + '</span><a href="' + url + '" target="_blank">' + url + '</a></div>';
        }}

        // ── Click to query ──
        map.on('click', function(e) {{
            document.getElementById('coords').innerHTML =
                '<strong style="color:#f7a325;">QUERYING:</strong> ' + e.latlng.lat.toFixed(6) + ', ' + e.latlng.lng.toFixed(6);
            queryParcel(e.latlng.lat, e.latlng.lng);
        }});

        // ── Markers and polygons from server ──
        {marker_js}
        {poly_js}

        // If a marker was placed, zoom and auto-query
        {"map.setView([" + str(markers[0]['lat']) + "," + str(markers[0]['lon']) + "], 16);" if len(markers) == 1 else ""}
        {auto_query_js}
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
                    source = result.get("source", "unknown")
                    st.success(f"✓ {result['display_name'][:90]}")
                    st.caption(f"📡 Source: **{source}** · `{query_lat:.6f}, {query_lon:.6f}`")
                    if source == "Nominatim (OSM)":
                        st.warning("⚠ OSM geocoding may be less precise. Verify the pin lands on the correct parcel in the map, or click the correct parcel directly.")
                else:
                    st.error("Address not found. Try a more complete format like: 909 Randall St, Orlando, FL 32805")

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
st.components.v1.html(map_html, height=850, scrolling=True)
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

    # Parcel data is now queried CLIENT-SIDE in the map above
    render_section_header("📋", "Parcel Data")
    st.markdown("""
    <div class="info-card">
        <h3>📍 Parcel results appear in the map panel above</h3>
        <div class="role">
            Parcel queries run directly from <strong>your browser</strong> to the OCPA GIS servers — 
            bypassing bot detection that blocks server-side requests. Click anywhere on the map to 
            query a parcel, or use the sidebar to search an address (results auto-load in the map).
            <br><br>
            Each parcel card includes direct deep links to:
            <strong>OCPA GIS Map</strong> · <strong>Property Card</strong> · <strong>Mobile View</strong> · <strong>Official Records</strong>
        </div>
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
