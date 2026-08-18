"""
DISHA Geocoding Service
Provides offline, deterministic geocoding for Indian States, Union Territories,
districts, and disaster-prone cities with precision indicators.
"""

from typing import Optional, Tuple

# Centroids for all Indian States & Union Territories
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

# Coordinates for 120+ key Indian disaster-prone districts and cities
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
