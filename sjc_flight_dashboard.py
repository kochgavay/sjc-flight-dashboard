import streamlit as st
import requests
import math
from datetime import datetime
from zoneinfo import ZoneInfo
from streamlit_autorefresh import st_autorefresh
import os
import time

# ==== CONFIG ====
HOME_LAT = 37.399746   # your home latitude
HOME_LON = -121.962585  # your home longitude
MAX_DISTANCE_KM = 3.2  # 2 miles

# Airline code lookup (callsign prefixes)
AIRLINE_CODES = {
    "UAL": "United Airlines",
    "SWA": "Southwest",
    "DAL": "Delta",
    "ASA": "Alaska",
    "AAL": "American Airlines",
    "JBU": "JetBlue",
    "FFT": "Frontier",
    "SKW": "SkyWest",
    "NKS": "Spirit",
    "HXA": "Hawaiian Airlines",
    "Y4": "Volaris",
    "ZG": "ZIPAIR"
}

# Aircraft type lookup (partial, expand as needed)
AIRCRAFT_TYPES = {
    "A319": "Airbus A319",
    "A320": "Airbus A320",
    "A20N": "Airbus A320neo",
    "A332": "Airbus A330-200",
    "A343": "Airbus A340-300",
    "B712": "Boeing 717-200",
    "B734": "Boeing 737-400",
    "B737": "Boeing 737-700",
    "B738": "Boeing 737-800",
    "B739": "Boeing 737-900",
    "B763": "Boeing 767-300",
    "B788": "Boeing 787-8",
    "B789": "Boeing 787-9",
    "CRJ2": "Bombardier CRJ-200",
    "CRJ7": "Bombardier CRJ-700",
    "CRJ9": "Bombardier CRJ-900",
    "E75L": "Embraer ERJ-175",
    "MD90": "McDonnell Douglas MD-90"
}

# ==== AUTH CONFIG ====
# Use provided OpenSky website credentials directly
OPENSKY_USERNAME = "tushk@umich.edu"
OPENSKY_PASSWORD = "RgX7ZLqKK@sJ58."

# ==== FUNCTIONS ====

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def get_flights(force_refresh=False):
    now = time.time()
    cache_key = "flight_cache"
    cache_time_key = "flight_cache_time"
    cache_ttl = 30  # seconds
    if not force_refresh and cache_key in st.session_state and cache_time_key in st.session_state:
        if now - st.session_state[cache_time_key] < cache_ttl:
            return st.session_state[cache_key], (cache_ttl - int(now - st.session_state[cache_time_key]))
    url = "https://opensky-network.org/api/states/all"
    try:
        auth = (OPENSKY_USERNAME, OPENSKY_PASSWORD)
        r = requests.get(url, timeout=10, auth=auth)
        r.raise_for_status()
        flights = r.json().get("states", [])
        st.session_state[cache_key] = flights
        st.session_state[cache_time_key] = now
        return flights, 0
    except Exception as e:
        st.error(f"Error fetching flight data: {e}")
        return [], 0

def is_near_home(lat, lon):
    if lat is None or lon is None:
        return False
    return haversine(HOME_LAT, HOME_LON, lat, lon) <= MAX_DISTANCE_KM

def is_sjc_flight(callsign):
    # Check if 'SJC' is in the callsign (case-insensitive)
    return callsign and "SJC" in callsign.upper()

def extract_details(callsign, icao24):
    cs = callsign.strip() if callsign else ""
    airline_code = cs[:3]
    flight_number = cs[3:].strip() if len(cs) > 3 else "Unknown"
    airline = AIRLINE_CODES.get(airline_code, "Private")

    destination = f"{airline_code} {flight_number}" if airline != "Private" else "Private Flight"

    aircraft_type = "Unknown Type"
    for prefix, type_name in AIRCRAFT_TYPES.items():
        if prefix in cs:
            aircraft_type = type_name
            break

    return destination, airline, f"{airline_code}{flight_number}", aircraft_type

def lookup_aircraft_type(icao24):
    """Lookup aircraft type/model from OpenSky aircraft database using icao24. Cache results in session state."""
    if not icao24:
        return "Unknown Type"
    cache_key = f"aircraft_type_{icao24}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    url = f"https://opensky-network.org/api/metadata/aircraft/icao24/{icao24}"
    try:
        auth = (OPENSKY_USERNAME, OPENSKY_PASSWORD) if OPENSKY_USERNAME and OPENSKY_PASSWORD else None
        r = requests.get(url, timeout=10, auth=auth)
        r.raise_for_status()
        data = r.json()
        # Try to get model or type
        ac_type = data.get("model") or data.get("type") or "Unknown Type"
        st.session_state[cache_key] = ac_type
        return ac_type
    except Exception:
        return "Unknown Type"

# ==== UI ====

st.set_page_config(page_title="Flights Overhead from SJC", layout="centered")

# --- Manual Refresh Button ---
refresh_clicked = False
if 'flight_cache_time' in st.session_state:
    last_fetch = st.session_state['flight_cache_time']
else:
    last_fetch = 0
now = time.time()
seconds_since_last = int(now - last_fetch)
wait_seconds = 30 - seconds_since_last

refresh_col, _ = st.columns([1, 8])
with refresh_col:
    refresh_clicked = st.button(
        label="\U0001F504",  # Unicode for refresh icon
        help="Refresh flight data",
        key="refresh_button",
        use_container_width=True,
        )
    st.markdown(
        f"""
        <style>
        button[data-testid="baseButton-secondary"] {{
            background-color: #A8C7FA !important;
            color: #fff !important;
            border-radius: 12px !important;
            font-size: 1.5rem !important;
            height: 48px !important;
            width: 48px !important;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# --- Fetch flights only if allowed ---
if refresh_clicked:
    if seconds_since_last < 30:
        st.warning(f"Please wait {wait_seconds} seconds before refreshing to avoid rate limit.")
        flights, _ = get_flights(force_refresh=False)
    else:
        flights, _ = get_flights(force_refresh=True)
else:
    flights, _ = get_flights(force_refresh=False)

visible = []

for f in flights:
    callsign = f[1]
    icao24 = f[0]
    lon, lat = f[5], f[6]
    on_ground = f[8]

    if lat and lon and is_near_home(lat, lon):
        dest, airline, flight_no, _ = extract_details(callsign, icao24)
        ac_type = lookup_aircraft_type(icao24)
        visible.append({
            "Destination": dest,
            "Airline": airline,
            "Flight Number": flight_no,
            "Aircraft Type": ac_type
        })

if visible:
    for flight in visible:
        st.markdown(f"""
        <div style="padding:15px; margin-bottom:15px; border-radius:10px; background-color:#343434;">
            <div style="font-size:2rem; font-weight:bold;">{flight['Destination']}</div>
            <div style="font-size:1rem;">{flight['Airline']} | {flight['Flight Number']}</div>
            <div style="font-size:1rem;">{flight['Aircraft Type']}</div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="padding:20px; margin-top:20px; text-align:center; font-size:1.5rem; color:#555;">
        🌤️ Clear skies above!
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<style>
@media (max-width: 768px) {
    .stApp { padding: 10px; font-size: 16px; }
    h1 { font-size: 1.5rem !important; }
}
</style>
""", unsafe_allow_html=True)
