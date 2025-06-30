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

# ICAO to city name mapping for major airports
ICAO_TO_CITY = {
    "KSFO": "San Francisco",
    "KLAX": "Los Angeles",
    "KSJC": "San Jose",
    "KSEA": "Seattle/Tacoma",
    "KDEN": "Denver",
    "KORD": "Chicago (O'Hare)",
    "KDFW": "Dallas/Fort Worth",
    "KPHX": "Phoenix",
    "KJFK": "New York",
    "KATL": "Atlanta",
    "KPDX": "Portland",
    "KLAS": "Las Vegas",
    "KOAK": "Oakland",
    "KSAN": "San Diego",
    "KDAL": "Dallas (Love Field)",
    "KMDW": "Chicago (Midway)",
    "KDTW": "Detroit",
    "KGEG": "Spokane",
    "KSTL": "St. Louis",
    "KMSP": "Minneapolis/St. Paul",
    "KONT": "Ontario",
    "KSNA": "Orange County (Santa Ana)",
    "KPSP": "Palm Springs",
    "KLGB": "Long Beach",
    "KBOI": "Boise",
    "KBUR": "Burbank",
    "KEUG": "Eugene",
    "KHOU": "Houston (Hobby)",
    "KIAH": "Houston (Intercontinental)",
    "KBNA": "Nashville",
    "KAUS": "Austin",
    "KBWI": "Baltimore/Washington",
    "KRNO": "Reno/Tahoe",
    "KSLC": "Salt Lake City",
    "PHOG": "Kahului (Maui)",
    "PHKO": "Kona (Big Island)",
    "KLIH": "Lihue",
    "MMGL": "Guadalajara",
    "MMLO": "León (Guanajuato)",
    "MMMM": "Morelia",
    "MMPR": "Puerto Vallarta",
    "MMSD": "San José del Cabo (Los Cabos)",
    "MMZC": "Zacatecas",
    "RJAA": "Tokyo–Narita",
}

# ==== AUTH CONFIG ====
# No authentication (use free OpenSky API, subject to rate limits)

# ==== FUNCTIONS ====

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def get_flights():
    import time
    now = time.time()
    cache_key = "flight_cache"
    cache_time_key = "flight_cache_time"
    cache_ttl = 30  # seconds
    if cache_key in st.session_state and cache_time_key in st.session_state:
        if now - st.session_state[cache_time_key] < cache_ttl:
            return st.session_state[cache_key]
    url = "https://opensky-network.org/api/states/all"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        flights = r.json().get("states", [])
        st.session_state[cache_key] = flights
        st.session_state[cache_time_key] = now
        return flights
    except Exception as e:
        st.error(f"Error fetching flight data: {e}")
        return []

def is_near_home(lat, lon):
    if lat is None or lon is None:
        return False
    return haversine(HOME_LAT, HOME_LON, lat, lon) <= MAX_DISTANCE_KM

def is_sjc_flight(callsign):
    # This function is not useful as flight callsigns don't contain airport codes
    # Keeping for potential future use or removal
    return False

def extract_details(callsign, icao24):
    cs = callsign.strip() if callsign else ""
    airline_code = cs[:3]
    flight_number = cs[3:].strip() if len(cs) > 3 else "Unknown"
    airline = AIRLINE_CODES.get(airline_code, "Private")

    # destination is now handled in the main loop using get_flight_route and ICAO_TO_CITY

    aircraft_type = "Unknown Type"
    for prefix, type_name in AIRCRAFT_TYPES.items():
        if prefix in cs:
            aircraft_type = type_name
            break

    return airline, f"{airline_code}{flight_number}", aircraft_type

def lookup_aircraft_type(icao24):
    """Lookup aircraft type/model from OpenSky aircraft database using icao24. Cache results in session state."""
    if not icao24:
        return "Unknown Type"
    cache_key = f"aircraft_type_{icao24}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    url = f"https://opensky-network.org/api/metadata/aircraft/icao24/{icao24}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        # Try to get model or type
        ac_type = data.get("model") or data.get("type") or "Unknown Type"
        st.session_state[cache_key] = ac_type
        return ac_type
    except Exception:
        return "Unknown Type"

def get_flight_route(icao24):
    import time
    now = int(time.time())
    begin = now - 2 * 3600  # last 2 hours
    end = now
    cache_key = f"route_{icao24}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    url = f"https://opensky-network.org/api/flights/aircraft?icao24={icao24}&begin={begin}&end={end}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        flights = r.json()
        if flights:
            flight = flights[-1]  # most recent
            dep = flight.get('estDepartureAirport')
            arr = flight.get('estArrivalAirport')
            st.session_state[cache_key] = (dep, arr)
            return dep, arr
    except Exception as e:
        return None, None
    return None, None

# ==== UI ====

st.set_page_config(page_title="Flights Overhead from SJC", layout="centered")
st.title("🛫 Flights Overhead")
now_pst = datetime.now(ZoneInfo("America/Los_Angeles"))
st.caption(f"Live from SJC | {now_pst.strftime('%Y-%m-%d %I:%M:%S %p')} PST")

flights = get_flights()

visible = []

for f in flights:
    callsign = f[1]
    icao24 = f[0]
    lon, lat = f[5], f[6]
    on_ground = f[8]

    if lat and lon and is_near_home(lat, lon):
        dep, arr = get_flight_route(icao24)
        label = None
        if arr and arr in ICAO_TO_CITY:
            label = f"To {ICAO_TO_CITY[arr]}"
        elif dep and dep in ICAO_TO_CITY:
            label = f"From {ICAO_TO_CITY[dep]}"
        else:
            label = callsign or "Unknown Flight"
        airline, flight_no, ac_type = extract_details(callsign, icao24)
        visible.append({
            "CityLabel": label,
            "Airline": airline,
            "Flight Number": flight_no,
            "Aircraft Type": ac_type
        })

if visible:
    for flight in visible:
        st.markdown(f"""
        <div style="padding:15px; margin-bottom:15px; border-radius:10px; background-color:#343434;">
            <div style="font-size:2rem; font-weight:bold;">{flight['CityLabel']}</div>
            <div style="font-size:1rem;">{flight['Airline']} | {flight['Flight Number']}</div>
            <div style="font-size:1rem;">{flight['Aircraft Type']}</div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="padding:20px; margin-top:20px; text-align:left; font-size:1.5rem; color:#555;">
        🌤️ Clear skies!
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
