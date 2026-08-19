"""
DISHA Geocoding & Geographic Entity Resolution Service
Provides offline deterministic geocoding for Indian States, Union Territories,
districts, disaster hotspots, and high-speed compiled entity extraction.
"""

import re
from typing import Optional, Tuple, List, Dict, Any

# ============================================================
# CENTROIDS FOR ALL INDIAN STATES & UNION TERRITORIES
# ============================================================

STATE_CENTROIDS = {
    "Andhra Pradesh": (15.9129, 79.7400),
    "Arunachal Pradesh": (28.2180, 94.7278),
    "Assam": (26.2006, 92.9376),
    "Bihar": (25.0961, 85.3131),
    "Chhattisgarh": (21.2787, 81.8661),
    "Goa": (15.2993, 74.1240),
    "Gujarat": (22.2587, 71.1924),
    "Haryana": (29.0588, 76.0856),
    "Himachal Pradesh": (31.1048, 77.1734),
    "Jharkhand": (23.6102, 85.2799),
    "Karnataka": (15.3173, 75.7139),
    "Kerala": (10.8505, 76.2711),
    "Madhya Pradesh": (22.9734, 78.6569),
    "Maharashtra": (19.7515, 75.7139),
    "Manipur": (24.6637, 93.9063),
    "Meghalaya": (25.4670, 91.3662),
    "Mizoram": (23.1645, 92.9376),
    "Nagaland": (26.1584, 94.5624),
    "Odisha": (20.9517, 85.0985),
    "Punjab": (31.1471, 75.3412),
    "Rajasthan": (27.0238, 74.2179),
    "Sikkim": (27.5330, 88.5122),
    "Tamil Nadu": (11.1271, 78.6569),
    "Telangana": (18.1124, 79.0193),
    "Tripura": (23.9408, 91.9882),
    "Uttar Pradesh": (26.8467, 80.9462),
    "Uttarakhand": (30.0668, 79.0193),
    "West Bengal": (22.9868, 87.8550),
    "Delhi": (28.7041, 77.1025),
    "Jammu and Kashmir": (33.7782, 76.5762),
    "Ladakh": (34.1526, 77.5771),
    "Puducherry": (11.9416, 79.8083),
    "Chandigarh": (30.7333, 76.7794),
    "Andaman and Nicobar": (11.7401, 92.6586),
    "Dadra and Nagar Haveli and Daman and Diu": (20.4283, 72.8397),
    "Lakshadweep": (10.5667, 72.6417),
}

# Mapping of State Aliases & Sub-regions
STATE_ALIASES = {
    "Andhra Pradesh": ["andhra pradesh", "andhra", "visakhapatnam", "vizag", "vijayawada", "guntur", "tirupati", "kurnool", "nellore", "anantapur", "kakinada"],
    "Arunachal Pradesh": ["arunachal pradesh", "arunachal", "itanagar", "tawang", "pasighat", "ziro", "changlang"],
    "Assam": ["assam", "guwahati", "silchar", "dibrugarh", "jorhat", "nagaon", "kaziranga", "brahmaputra", "dhemaji", "barpeta", "morigaon", "cachar", "sivasagar", "golaghat", "lakhimpur", "tezpur", "karimganj", "dhubri", "goalpara", "baksa", "chirang", "kamrup", "hailakandi", "sonitpur"],
    "Bihar": ["bihar", "patna", "gaya", "bhagalpur", "muzaffarpur", "purnia", "darbhanga", "kosi", "supaul", "madhepura", "saharsa", "katihar", "araria", "kishanganj", "motihari", "sitamarhi"],
    "Chhattisgarh": ["chhattisgarh", "raipur", "bilaspur", "durg", "bastar", "korba", "rajnandgaon", "surguja", "dantewada"],
    "Goa": ["goa", "panaji", "margao", "vasco", "mapusa"],
    "Gujarat": ["gujarat", "ahmedabad", "surat", "vadodara", "rajkot", "bhavnagar", "kutch", "bhuj", "morbi", "jamnagar", "junagadh", "gandhinagar", "anand", "navsari", "valsad", "porbandar", "patan", "mehsana", "amreli", "surendranagar"],
    "Haryana": ["haryana", "gurgaon", "gurugram", "faridabad", "panipat", "ambala", "karnal", "rohtak", "hisar", "sonipat", "panchkula"],
    "Himachal Pradesh": ["himachal pradesh", "himachal", "shimla", "manali", "kullu", "mandi", "dharamshala", "kinnaur", "lahaul", "spiti", "chamba", "solan", "bilaspur", "kangra", "una", "hamirpur", "sirmaur"],
    "Jharkhand": ["jharkhand", "ranchi", "jamshedpur", "dhanbad", "bokaro", "deoghar", "hazaribagh", "dumka"],
    "Karnataka": ["karnataka", "bengaluru", "bangalore", "mysore", "mysuru", "hubli", "dharwad", "mangalore", "mangaluru", "belagavi", "belgaum", "udupi", "kodagu", "coorg", "shivamogga", "shimoga", "uttara kannada", "dakshina kannada", "hassan", "chikkamagaluru", "kalaburagi", "gulbarga", "bellary"],
    "Kerala": ["kerala", "wayanad", "idukki", "kochi", "cochin", "thiruvananthapuram", "trivandrum", "kozhikode", "calicut", "munnar", "alappuzha", "alleppey", "kottayam", "malappuram", "thrissur", "palakkad", "kannur", "kollam", "pathanamthitta", "kasaragod", "ernakulam", "kalladi"],
    "Madhya Pradesh": ["madhya pradesh", "bhopal", "indore", "gwalior", "jabalpur", "ujjain", "sagar", "rewa", "satna", "hoshangabad", "narmadapuram", "sehore"],
    "Maharashtra": ["maharashtra", "mumbai", "pune", "nagpur", "thane", "nashik", "aurangabad", "chhatrapati sambhajinagar", "kolhapur", "konkan", "raigad", "ratnagiri", "sindhudurg", "satara", "solapur", "amravati", "nanded", "palghar", "jawhar", "marathwada", "vidarbha", "sangli", "akola", "latur", "dhule", "jalgaon", "chandrapur"],
    "Manipur": ["manipur", "imphal", "churachandpur", "thoubal", "bishnupur", "senapati", "ukhrul"],
    "Meghalaya": ["meghalaya", "shillong", "cherrapunji", "mawsynram", "tura", "jowai", "east khasi hills", "west garo hills"],
    "Mizoram": ["mizoram", "aizawl", "lunglei", "champhai"],
    "Nagaland": ["nagaland", "kohima", "dimapur", "mokokchung", "mon", "tuensang", "wokha"],
    "Odisha": ["odisha", "orissa", "bhubaneswar", "cuttack", "puri", "balasore", "rourkela", "bhadrak", "kendrapara", "jagatsinghpur", "ganjam", "berhampur", "sambalpur", "koraput", "mayurbhanj", "kalahandi", "bolangir", "balangir", "angul", "dhenkanal", "jajpur", "khordha"],
    "Punjab": ["punjab", "ludhiana", "amritsar", "jalandhar", "patiala", "bathinda", "mohali", "pathankot", "hoshiarpur", "gurdaspur", "ferozepur", "rupnagar", "ropar"],
    "Rajasthan": ["rajasthan", "jaipur", "jodhpur", "udaipur", "kota", "bikaner", "ajmer", "bharatpur", "alwar", "sikar", "pali", "barmer", "jaisalmer", "nagaur", "chittorgarh", "sri ganganagar", "bhilwara"],
    "Sikkim": ["sikkim", "gangtok", "namchi", "teesta", "mangan", "gyalshing", "singtam", "chungthang", "lhonak"],
    "Tamil Nadu": ["tamil nadu", "tamilnadu", "chennai", "coimbatore", "madurai", "salem", "tiruchirappalli", "trichy", "tirunelveli", "tiruppur", "vellore", "thoothukudi", "tuticorin", "cuddalore", "nilgiris", "ooty", "kanchipuram", "thanjavur", "dindigul", "erode", "kanyakumari", "nagapattinam", "chengalpattu"],
    "Telangana": ["telangana", "hyderabad", "warangal", "nizamabad", "karimnagar", "khammam", "ramagundam", "mahbubnagar", "nalgonda", "adilabad", "bhadradri kothagudem", "mancherial"],
    "Tripura": ["tripura", "agartala", "udaipur", "dharmanagar", "kailashahar"],
    "Uttar Pradesh": ["uttar pradesh", "lucknow", "kanpur", "varanasi", "agra", "noida", "ghaziabad", "prayagraj", "allahabad", "gorakhpur", "meerut", "bareilly", "aligarh", "moradabad", "saharanpur", "ayodhya", "faizabad", "jhansi", "muzaffarnagar", "mathura", "budaun", "rampur", "shahjahanpur", "firozabad", "etawah"],
    "Uttarakhand": ["uttarakhand", "uttaranchal", "dehradun", "rishikesh", "haridwar", "chamoli", "joshimath", "nainital", "kedarnath", "badrinath", "uttarkashi", "rudraprayag", "pithoragarh", "tehri", "almora", "haldwani", "roorkee", "pauri", "champawat", "bageshwar", "udham singh nagar"],
    "West Bengal": ["west bengal", "bengal", "kolkata", "howrah", "darjeeling", "siliguri", "birbhum", "durgapur", "asansol", "sunderbans", "jalpaiguri", "kalimpong", "malda", "murshidabad", "nadia", "north 24 parganas", "south 24 parganas", "hooghly", "paschim medinipur", "purba medinipur", "bankura", "purulia", "cooch behar", "alipurduar"],
    "Delhi": ["delhi", "new delhi", "nct of delhi", "delhi-ncr", "ncr"],
    "Jammu and Kashmir": ["jammu and kashmir", "jammu & kashmir", "jammu kashmir", "j&k", "kashmir", "jammu", "srinagar", "anantnag", "baramulla", "budgam", "pulwama", "kupwara", "shopian", "ganderbal", "bandipora", "kulgam", "poonch", "rajouri", "kathua", "udhampur", "doda", "ramban", "reasi", "kishtwar", "samba", "bhalesa"],
    "Ladakh": ["ladakh", "leh", "kargil", "nubra", "drass", "zanskar"],
    "Puducherry": ["puducherry", "pondicherry", "karaikal", "mahe", "yanam"],
    "Chandigarh": ["chandigarh"],
    "Andaman and Nicobar": ["andaman and nicobar", "andaman & nicobar", "port blair", "andaman", "nicobar", "havelock"],
    "Dadra and Nagar Haveli and Daman and Diu": ["daman", "diu", "silvassa", "dadra and nagar haveli"],
    "Lakshadweep": ["lakshadweep", "kavaratti", "agatti", "minicoy"],
}

CITY_DISTRICT_COORDINATES = {
    # Assam
    "guwahati": (26.1445, 91.7362),
    "dibrugarh": (27.4728, 94.9120),
    "silchar": (24.8333, 92.7789),
    "jorhat": (26.7509, 94.2037),
    "nagaon": (26.3464, 92.6840),
    "tezpur": (26.6528, 92.7926),
    "dhemaji": (27.4833, 94.5833),
    "barpeta": (26.3200, 91.0000),
    "morigaon": (26.2500, 92.3333),
    "cachar": (24.8333, 92.7789),
    "sivasagar": (26.9826, 94.6425),
    "golaghat": (26.5167, 93.9667),
    "lakhimpur": (27.3600, 94.1000),
    "kaziranga": (26.5775, 93.1711),
    "dhubri": (26.0200, 89.9700),
    "karimganj": (24.8700, 92.3500),

    # Uttarakhand
    "dehradun": (30.3165, 78.0322),
    "chamoli": (30.4000, 79.3333),
    "joshimath": (30.5564, 79.5658),
    "uttarkashi": (30.7268, 78.4354),
    "rudraprayag": (30.2844, 78.9811),
    "kedarnath": (30.7346, 79.0669),
    "badrinath": (30.7433, 79.4938),
    "haridwar": (29.9457, 78.1642),
    "rishikesh": (30.0869, 78.2676),
    "nainital": (29.3919, 79.4542),
    "pithoragarh": (29.5829, 80.2182),
    "tehri": (30.3800, 78.4800),
    "almora": (29.5971, 79.6591),
    "haldwani": (29.2183, 79.5130),
    "roorkee": (29.8543, 77.8880),

    # Himachal Pradesh
    "shimla": (31.1048, 77.1734),
    "manali": (32.2432, 77.1892),
    "kullu": (31.9579, 77.1095),
    "mandi": (31.7087, 76.9320),
    "dharamshala": (32.2190, 76.3234),
    "kinnaur": (31.6510, 78.4754),
    "lahaul": (32.5534, 77.0047),
    "spiti": (32.2461, 78.0349),
    "chamba": (32.5534, 76.1258),
    "solan": (30.9045, 77.0967),
    "kangra": (32.0998, 76.2691),

    # Kerala
    "wayanad": (11.6854, 76.1320),
    "idukki": (9.8494, 76.9810),
    "munnar": (10.0889, 77.0595),
    "kochi": (9.9312, 76.2673),
    "thiruvananthapuram": (8.5241, 76.9366),
    "kozhikode": (11.2588, 75.7804),
    "alappuzha": (9.4981, 76.3388),
    "kottayam": (9.5916, 76.5222),
    "malappuram": (11.0732, 76.0740),
    "thrissur": (10.5276, 76.2144),
    "palakkad": (10.7867, 76.6548),
    "kannur": (11.8745, 75.3704),
    "kalladi": (11.5300, 76.1500),

    # Odisha
    "bhubaneswar": (20.2961, 85.8245),
    "cuttack": (20.4625, 85.8828),
    "puri": (19.8135, 85.8312),
    "balasore": (21.4934, 86.9135),
    "bhadrak": (21.0543, 86.4955),
    "kendrapara": (20.5000, 86.4200),
    "jagatsinghpur": (20.2700, 86.1700),
    "ganjam": (19.3800, 85.0500),
    "rourkela": (22.2604, 84.8536),
    "sambalpur": (21.4669, 83.9812),
    "koraput": (18.8135, 82.7118),

    # West Bengal
    "kolkata": (22.5726, 88.3639),
    "howrah": (22.5958, 88.2636),
    "darjeeling": (27.0410, 88.2663),
    "siliguri": (26.7271, 88.3953),
    "birbhum": (23.8400, 87.6100),
    "asansol": (23.6889, 86.9661),
    "durgapur": (23.5204, 87.3119),
    "jalpaiguri": (26.5400, 88.7200),
    "kalimpong": (27.0600, 88.4700),
    "malda": (25.0108, 88.1411),
    "sunderbans": (21.9497, 89.1833),

    # Maharashtra
    "mumbai": (19.0760, 72.8777),
    "pune": (18.5204, 73.8567),
    "nagpur": (21.1458, 79.0882),
    "thane": (19.2183, 72.9781),
    "nashik": (19.9975, 73.7898),
    "kolhapur": (16.7050, 74.2433),
    "raigad": (18.5158, 73.1822),
    "ratnagiri": (16.9902, 73.3120),
    "sindhudurg": (16.1179, 73.7042),
    "satara": (17.6805, 74.0183),
    "palghar": (19.6967, 72.7654),
    "jawhar": (19.9142, 73.2322),
    "nanded": (19.1383, 77.3210),

    # Gujarat
    "ahmedabad": (23.0225, 72.5714),
    "surat": (21.1702, 72.8311),
    "vadodara": (22.3072, 73.1812),
    "rajkot": (22.3039, 70.8022),
    "bhavnagar": (21.7645, 72.1519),
    "jamnagar": (22.4707, 70.0577),
    "kutch": (23.7337, 69.8597),
    "bhuj": (23.2420, 69.6669),
    "morbi": (22.8173, 70.8370),

    # Bihar
    "patna": (25.5941, 85.1376),
    "gaya": (24.7914, 85.0002),
    "bhagalpur": (25.2425, 86.9842),
    "muzaffarpur": (26.1209, 85.3647),
    "purnia": (25.7771, 87.4753),
    "darbhanga": (26.1542, 85.8918),
    "supaul": (26.1260, 86.6053),
    "madhepura": (25.9265, 86.7906),

    # Jammu and Kashmir & Ladakh
    "srinagar": (34.0837, 74.7973),
    "jammu": (32.7266, 74.8570),
    "anantnag": (33.7311, 75.1522),
    "baramulla": (34.1980, 74.3636),
    "leh": (34.1526, 77.5771),
    "kargil": (34.5539, 76.1349),
    "doda": (33.1450, 75.5460),
    "bhalesa": (33.0000, 75.8000),

    # Tamil Nadu
    "chennai": (13.0827, 80.2707),
    "coimbatore": (11.0168, 76.9558),
    "madurai": (9.9252, 78.1198),
    "tiruchirappalli": (10.7905, 78.7047),
    "salem": (11.6643, 78.1460),
    "cuddalore": (11.7480, 79.7714),
    "nilgiris": (11.4916, 76.7337),

    # Andhra Pradesh & Telangana
    "visakhapatnam": (17.6868, 83.2185),
    "vijayawada": (16.5062, 80.6480),
    "guntur": (16.3067, 80.4365),
    "hyderabad": (17.3850, 78.4867),
    "warangal": (17.9689, 79.5941),

    # Uttar Pradesh
    "lucknow": (26.8467, 80.9462),
    "kanpur": (26.4499, 80.3319),
    "varanasi": (25.3176, 82.9739),
    "agra": (27.1767, 78.0081),
    "prayagraj": (25.4358, 81.8463),
    "gorakhpur": (26.7606, 83.3732),
    "noida": (28.5355, 77.3910),
    "ghaziabad": (28.6692, 77.4538),

    # Other States
    "delhi": (28.7041, 77.1025),
    "new delhi": (28.6139, 77.2090),
    "jaipur": (26.9124, 75.7873),
    "jodhpur": (26.2389, 73.0243),
    "bhopal": (23.2599, 77.4126),
    "indore": (22.7196, 75.8577),
    "ranchi": (23.3441, 85.3096),
    "raipur": (21.2514, 81.6296),
    "gangtok": (27.3389, 88.6065),
    "shillong": (25.5788, 91.8933),
    "imphal": (24.8170, 93.9368),
    "aizawl": (23.7271, 92.7176),
    "kohima": (25.6751, 94.1086),
    "agartala": (23.8315, 91.2868),
    "chandigarh": (30.7333, 76.7794),
    "port blair": (11.6234, 92.7265),
}

# Pre-compile fast lookup structures
_ALIAS_TO_STATE: Dict[str, str] = {}
for canonical_state, aliases in STATE_ALIASES.items():
    for alias in aliases:
        _ALIAS_TO_STATE[alias.lower()] = canonical_state

_ALL_LOC_KEYS = sorted(
    list(set(_ALIAS_TO_STATE.keys()) | set(CITY_DISTRICT_COORDINATES.keys())),
    key=len,
    reverse=True,
)

_LOC_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _ALL_LOC_KEYS) + r")\b",
    re.IGNORECASE,
)

_INDIA_CONTEXT_PATTERN = re.compile(
    r"\b(india|indian|national disaster|imd|ndrf|sdrf|cwc|ndma|mha|delhi-ncr|national highway|nh-\d+|state highway)\b",
    re.IGNORECASE,
)


def detect_locations(text: str) -> Dict[str, Any]:
    """
    High-speed deterministic extraction of Indian states, union territories, districts,
    and cities from normalized text using compiled dictionary automaton.
    Returns: {"states": [...], "cities": [...], "locations": [...], "has_india": bool}
    """
    if not text:
        return {"states": [], "cities": [], "locations": [], "has_india": False}

    matches = _LOC_PATTERN.findall(text)
    found_states = []
    found_cities = []

    for match in matches:
        m_lower = match.lower()
        # Check state alias mapping
        if m_lower in _ALIAS_TO_STATE:
            state = _ALIAS_TO_STATE[m_lower]
            if state not in found_states:
                found_states.append(state)
        # Check city/district coordinates mapping
        if m_lower in CITY_DISTRICT_COORDINATES:
            city_name = m_lower.title()
            if city_name not in found_cities:
                found_cities.append(city_name)

    has_india = bool(
        found_states
        or found_cities
        or bool(_INDIA_CONTEXT_PATTERN.search(text))
    )

    return {
        "states": found_states,
        "cities": found_cities,
        "locations": found_states + found_cities,
        "has_india": has_india,
    }


def geocode_location(
    country: str = "India",
    state: Optional[str] = None,
    city: Optional[str] = None,
    district: Optional[str] = None,
) -> Tuple[Optional[float], Optional[float], str]:
    """
    Deterministically resolves location coordinates with precision metadata.
    Returns: (latitude, longitude, precision)
    precision can be 'city', 'district', 'state', 'country', or 'unknown'.
    """
    # 1. City lookup (highest precision)
    if city:
        city_norm = city.strip().lower()
        if city_norm in CITY_DISTRICT_COORDINATES:
            lat, lon = CITY_DISTRICT_COORDINATES[city_norm]
            return lat, lon, "city"

    # 2. District lookup
    if district:
        dist_norm = district.strip().lower()
        if dist_norm in CITY_DISTRICT_COORDINATES:
            lat, lon = CITY_DISTRICT_COORDINATES[dist_norm]
            return lat, lon, "district"

    # 3. State lookup
    if state:
        state_clean = state.strip()
        if state_clean in STATE_CENTROIDS:
            lat, lon = STATE_CENTROIDS[state_clean]
            return lat, lon, "state"

        # Case-insensitive check
        for canonical_state, (lat, lon) in STATE_CENTROIDS.items():
            if canonical_state.lower() == state_clean.lower():
                return lat, lon, "state"

    # 4. Country centroid default for India
    if country and country.strip().lower() == "india":
        return 20.5937, 78.9629, "country"

    return None, None, "unknown"
