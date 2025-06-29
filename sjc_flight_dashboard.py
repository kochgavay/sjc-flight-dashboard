import streamlit as st
import requests
import math
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

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

# ==== FUNCTIONS ====

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def get_flights():
    url = "https://opensky-network.org/api/states/all"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json().get("states", [])
    except Exception as e:
        st.error(f"Error fetching flight data: {e}")
        return []

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

# ==== UI ====

st.set_page_config(page_title="Flights Overhead from SJC", layout="centered")
st_autorefresh(interval=30000, key="flight_refresh")

st.title("🛫 Flights Overhead")
st.caption(f"Live from SJC | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

flights = get_flights()
visible = []

for f in flights:
    callsign = f[1]
    icao24 = f[0]
    lon, lat = f[5], f[6]
    on_ground = f[8]

    if lat and lon and is_near_home(lat, lon) and is_sjc_flight(callsign):
        dest, airline, flight_no, ac_type = extract_details(callsign, icao24)
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
