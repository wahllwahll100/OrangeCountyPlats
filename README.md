# 🏗️ Orange County FL – Infrastructure Engineering Lookup Tool

A one-stop research tool for engineers planning to design and construct new infrastructure in **Orange County, Florida**.

## Features

### Input Methods
- **Address Search** – Flexible parser accepts full addresses, partial addresses, intersections. Auto-appends Orange County/FL context.
- **Coordinate Input** – Supports decimal degrees, DMS, N/S/E/W prefixes/suffixes, parenthesized pairs, and more.
- **Polygon Drawing** – Interactive Leaflet map with draw tools (polygon, rectangle, marker). GeoJSON output can be pasted back to query parcels within the area.
- **GeoJSON Upload** – Upload `.geojson` or `.json` files with project boundaries. Extracts all features and queries intersecting parcels.

### Data Returned
- **Parcel Data** – Queried live from Orange County Property Appraiser ArcGIS REST services (owner, address, zoning, acreage, plat reference, legal description, just value).
- **Jurisdiction Detection** – Determines if a point is within Orlando, Winter Park, Maitland, Apopka, Ocoee, Winter Garden, or unincorporated Orange County.
- **Water Management District** – Identifies whether SJRWMD or SFWMD applies.
- **Resource URLs** – 30+ direct links organized by category:
  - GIS & Mapping
  - Permits & Development
  - Plats & Surveys
  - Utilities & Infrastructure
  - Environmental & Stormwater
  - HOA / CDD
  - Transportation
- **Contacts Directory** – Phone, email, address, and website for:
  - Municipal offices (OC Development Engineering, Planning, Building Safety, City of Orlando, etc.)
  - Utility providers (OUC, Duke Energy, OC Utilities, Peoples Gas, Sunshine 811)
  - State & regional agencies (FDOT District 5, SJRWMD, SFWMD, FDEP, CFX)

## Deployment to Streamlit Community Cloud

1. **Push to GitHub:**
   ```bash
   cd oc-engineer-tool
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/oc-engineer-tool.git
   git push -u origin main
   ```

2. **Deploy on Streamlit:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Select your repository, branch `main`, and file `app.py`
   - Click "Deploy"

3. **Your app will be live** at `https://YOUR_APP_NAME.streamlit.app`

## Local Development

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project Structure

```
oc-engineer-tool/
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── .streamlit/
│   └── config.toml           # Streamlit theme and server config
└── data/
    ├── contacts.json         # Municipal, utility, and agency contacts
    └── resources.json        # Categorized resource URLs
```

## Data Sources

| Source | Usage |
|--------|-------|
| Orange County Property Appraiser GIS | Parcel data (live ArcGIS REST query) |
| OpenStreetMap Nominatim | Address geocoding |
| Leaflet + Leaflet.Draw | Interactive map with drawing tools |
| Esri World Imagery/Topo | Satellite and topographic basemaps |

## Disclaimer

This tool provides **reference information** for preliminary research only. All data must be independently verified with authoritative sources before use in engineering design or permit applications. This is not an official government application.
