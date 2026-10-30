"""
DISHA Platform - Shared Geographic Filtering & Administrative Resolution Service
Disaster Intelligence and Situational Hazard Awareness Platform

Provides:
1. Canonical administrative hierarchy for India: Country -> States/UTs -> Districts -> Cities.
2. Verified geographic bounding boxes and centroids for all 36 Indian States and Union Territories.
3. Strict coordinate validation (rejection of null, NaN, non-numeric, out-of-bounds, (0,0), and fake India centroids).
4. Reliable non-destructive geographic eligibility evaluation for disaster news and alerts.
5. In-memory geocoding cache with thread safety and fast resolution.
"""

import math
import re
from typing import Dict, List, Any, Optional, Tuple, Set

# ============================================================================
# 1. CANONICAL INDIAN STATES & UNION TERRITORIES WITH BOUNDING BOXES & CENTROIDS
# Bounding box format: (min_lat, min_lon, max_lat, max_lon)
# Centroid format: (lat, lon)
# ============================================================================

INDIA_BBOX = (6.0, 68.0, 37.5, 97.5)
INDIA_CENTROID = (22.5937, 78.9629)

# Standard artificial fallback centroids to strictly reject from map markers
FORBIDDEN_FALLBACK_CENTROIDS = [
    (20.5937, 78.9629),  # Legacy fake India default centroid
    (0.0, 0.0),          # Null island
]

STATE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "Andhra Pradesh": {
        "canonical": "Andhra Pradesh",
        "aliases": ["andhra pradesh", "andhra", "ap", "visakhapatnam", "vizag", "vijayawada", "guntur", "tirupati", "kurnool", "nellore", "anantapur", "kakinada", "rajahmundry", "kadapa", "chittoor"],
        "bbox": (12.6, 76.7, 19.9, 84.8),
        "centroid": (15.9129, 79.7400),
    },
    "Arunachal Pradesh": {
        "canonical": "Arunachal Pradesh",
        "aliases": ["arunachal pradesh", "arunachal", "itanagar", "tawang", "pasighat", "ziro", "changlang", "west kameng", "east siang"],
        "bbox": (26.6, 91.5, 29.5, 97.5),
        "centroid": (28.2180, 94.7278),
    },
    "Assam": {
        "canonical": "Assam",
        "aliases": ["assam", "asom", "guwahati", "silchar", "dibrugarh", "jorhat", "nagaon", "kaziranga", "brahmaputra", "dhemaji", "barpeta", "morigaon", "cachar", "sivasagar", "golaghat", "lakhimpur", "tezpur", "karimganj", "dhubri", "goalpara", "baksa", "chirang", "kamrup", "hailakandi", "sonitpur", "tinsukia", "bongaigaon", "kokrajhar", "majuli"],
        "bbox": (24.1, 89.7, 28.2, 96.1),
        "centroid": (26.2006, 92.9376),
    },
    "Bihar": {
        "canonical": "Bihar",
        "aliases": ["bihar", "patna", "gaya", "bhagalpur", "muzaffarpur", "purnia", "darbhanga", "kosi", "supaul", "madhepura", "saharsa", "katihar", "araria", "kishanganj", "motihari", "sitamarhi", "begusarai", "chhapra", "siwan"],
        "bbox": (24.3, 83.3, 27.5, 88.3),
        "centroid": (25.0961, 85.3131),
    },
    "Chhattisgarh": {
        "canonical": "Chhattisgarh",
        "aliases": ["chhattisgarh", "chattisgarh", "raipur", "bilaspur", "durg", "bastar", "korba", "rajnandgaon", "surguja", "dantewada", "bhilai", "jagdalpur"],
        "bbox": (17.8, 80.2, 24.1, 84.4),
        "centroid": (21.2787, 81.8661),
    },
    "Goa": {
        "canonical": "Goa",
        "aliases": ["goa", "panaji", "panjim", "margao", "vasco", "mapusa", "ponda", "north goa", "south goa"],
        "bbox": (14.9, 73.7, 15.8, 74.4),
        "centroid": (15.2993, 74.1240),
    },
    "Gujarat": {
        "canonical": "Gujarat",
        "aliases": ["gujarat", "gujrat", "ahmedabad", "surat", "vadodara", "baroda", "rajkot", "bhavnagar", "kutch", "kachchh", "bhuj", "morbi", "jamnagar", "junagadh", "gandhinagar", "anand", "navsari", "valsad", "porbandar", "patan", "mehsana", "amreli", "surendranagar", "bharuch", "banaskantha", "sabarkantha", "panchmahal", "dahod", "kheda", "gir somnath", "botad", "dwarka", "tapi", "narmada", "dang", "aravalli", "mahisagar"],
        "bbox": (20.1, 68.1, 24.7, 74.5),
        "centroid": (22.2587, 71.1924),
    },
    "Haryana": {
        "canonical": "Haryana",
        "aliases": ["haryana", "gurgaon", "gurugram", "faridabad", "panipat", "ambala", "karnal", "rohtak", "hisar", "sonipat", "panchkula", "yamunanagar", "kurukshetra", "bhiwani", "rewari"],
        "bbox": (27.6, 74.5, 30.9, 77.6),
        "centroid": (29.0588, 76.0856),
    },
    "Himachal Pradesh": {
        "canonical": "Himachal Pradesh",
        "aliases": ["himachal pradesh", "himachal", "hp", "shimla", "manali", "kullu", "mandi", "dharamshala", "kinnaur", "lahaul", "spiti", "chamba", "solan", "bilaspur", "kangra", "una", "hamirpur", "sirmaur", "sirmour", "paonta sahib"],
        "bbox": (30.4, 75.6, 33.3, 79.1),
        "centroid": (31.1048, 77.1734),
    },
    "Jharkhand": {
        "canonical": "Jharkhand",
        "aliases": ["jharkhand", "ranchi", "jamshedpur", "dhanbad", "bokaro", "deoghar", "hazaribagh", "dumka", "giridih", "ramgarh", "chaibasa", "palamu"],
        "bbox": (21.9, 83.3, 25.3, 87.9),
        "centroid": (23.6102, 85.2799),
    },
    "Karnataka": {
        "canonical": "Karnataka",
        "aliases": ["karnataka", "bengaluru", "bangalore", "mysore", "mysuru", "hubli", "dharwad", "mangalore", "mangaluru", "belagavi", "belgaum", "udupi", "kodagu", "coorg", "shivamogga", "shimoga", "uttara kannada", "dakshina kannada", "hassan", "chikkamagaluru", "kalaburagi", "gulbarga", "bellary", "ballari", "tumakuru", "davangere"],
        "bbox": (11.6, 74.0, 18.5, 78.6),
        "centroid": (15.3173, 75.7139),
    },
    "Kerala": {
        "canonical": "Kerala",
        "aliases": ["kerala", "wayanad", "idukki", "kochi", "cochin", "thiruvananthapuram", "trivandrum", "kozhikode", "calicut", "munnar", "alappuzha", "alleppey", "kottayam", "malappuram", "thrissur", "palakkad", "kannur", "kollam", "pathanamthitta", "kasaragod", "ernakulam", "kalladi", "meppadi", "chooralmala"],
        "bbox": (8.3, 74.8, 12.8, 77.4),
        "centroid": (10.8505, 76.2711),
    },
    "Madhya Pradesh": {
        "canonical": "Madhya Pradesh",
        "aliases": ["madhya pradesh", "mp", "bhopal", "indore", "gwalior", "jabalpur", "ujjain", "sagar", "rewa", "satna", "hoshangabad", "narmadapuram", "sehore", "dewas", "ratlam", "chhindwara", "shivpuri", "khargone"],
        "bbox": (21.1, 74.0, 26.9, 82.8),
        "centroid": (22.9734, 78.6569),
    },
    "Maharashtra": {
        "canonical": "Maharashtra",
        "aliases": ["maharashtra", "mumbai", "bombay", "pune", "nagpur", "thane", "nashik", "aurangabad", "chhatrapati sambhajinagar", "kolhapur", "konkan", "raigad", "ratnagiri", "sindhudurg", "satara", "solapur", "amravati", "nanded", "palghar", "jawhar", "marathwada", "vidarbha", "sangli", "akola", "latur", "dhule", "jalgaon", "chandrapur"],
        "bbox": (15.6, 72.6, 22.0, 80.9),
        "centroid": (19.7515, 75.7139),
    },
    "Manipur": {
        "canonical": "Manipur",
        "aliases": ["manipur", "imphal", "churachandpur", "thoubal", "bishnupur", "senapati", "ukhrul", "chandel", "tamenglong"],
        "bbox": (23.8, 93.0, 25.7, 94.8),
        "centroid": (24.6637, 93.9063),
    },
    "Meghalaya": {
        "canonical": "Meghalaya",
        "aliases": ["meghalaya", "shillong", "cherrapunji", "cherrapunjee", "sohra", "mawsynram", "tura", "jowai", "east khasi hills", "west garo hills", "ri bhoi"],
        "bbox": (25.0, 89.8, 26.1, 92.8),
        "centroid": (25.4670, 91.3662),
    },
    "Mizoram": {
        "canonical": "Mizoram",
        "aliases": ["mizoram", "aizawl", "lunglei", "champhai", "serchhip", "kolasib", "lawngtlai"],
        "bbox": (21.9, 92.2, 24.5, 93.4),
        "centroid": (23.1645, 92.9376),
    },
    "Nagaland": {
        "canonical": "Nagaland",
        "aliases": ["nagaland", "kohima", "dimapur", "mokokchung", "mon", "tuensang", "wokha", "zunheboto", "phek"],
        "bbox": (25.1, 93.3, 27.0, 95.2),
        "centroid": (26.1584, 94.5624),
    },
    "Odisha": {
        "canonical": "Odisha",
        "aliases": ["odisha", "orissa", "bhubaneswar", "cuttack", "puri", "balasore", "bhadrak", "kendrapara", "jagatsinghpur", "ganjam", "berhampur", "sambalpur", "koraput", "mayurbhanj", "kalahandi", "bolangir", "balangir", "angul", "dhenkanal", "jajpur", "khordha", "rourkela", "sundargarh", "rayagada"],
        "bbox": (17.8, 81.4, 22.6, 87.5),
        "centroid": (20.9517, 85.0985),
    },
    "Punjab": {
        "canonical": "Punjab",
        "aliases": ["punjab", "ludhiana", "amritsar", "jalandhar", "patiala", "bathinda", "mohali", "pathankot", "hoshiarpur", "gurdaspur", "ferozepur", "rupnagar", "ropar", "moga", "kapurthala"],
        "bbox": (29.5, 73.8, 32.5, 76.9),
        "centroid": (31.1471, 75.3412),
    },
    "Rajasthan": {
        "canonical": "Rajasthan",
        "aliases": ["rajasthan", "jaipur", "jodhpur", "udaipur", "kota", "bikaner", "ajmer", "bharatpur", "alwar", "sikar", "pali", "barmer", "jaisalmer", "nagaur", "chittorgarh", "sri ganganagar", "bhilwara", "hanumangarh", "churu", "dholpur", "tonk"],
        "bbox": (23.0, 69.5, 30.2, 78.3),
        "centroid": (27.0238, 74.2179),
    },
    "Sikkim": {
        "canonical": "Sikkim",
        "aliases": ["sikkim", "gangtok", "namchi", "teesta", "mangan", "gyalshing", "singtam", "chungthang", "lhonak", "dikchu", "north sikkim", "south sikkim"],
        "bbox": (27.1, 88.0, 28.1, 88.9),
        "centroid": (27.5330, 88.5122),
    },
    "Tamil Nadu": {
        "canonical": "Tamil Nadu",
        "aliases": ["tamil nadu", "tamilnadu", "tn", "chennai", "madras", "coimbatore", "madurai", "salem", "tiruchirappalli", "trichy", "tirunelveli", "tiruppur", "vellore", "thoothukudi", "tuticorin", "cuddalore", "nilgiris", "ooty", "kanchipuram", "thanjavur", "dindigul", "erode", "kanyakumari", "nagapattinam", "chengalpattu"],
        "bbox": (8.1, 76.2, 13.6, 80.4),
        "centroid": (11.1271, 78.6569),
    },
    "Telangana": {
        "canonical": "Telangana",
        "aliases": ["telangana", "hyderabad", "secunderabad", "warangal", "nizamabad", "karimnagar", "khammam", "ramagundam", "mahbubnagar", "nalgonda", "adilabad", "bhadradri kothagudem", "mancherial", "siddipet"],
        "bbox": (15.8, 77.2, 19.9, 81.8),
        "centroid": (18.1124, 79.0193),
    },
    "Tripura": {
        "canonical": "Tripura",
        "aliases": ["tripura", "agartala", "udaipur", "dharmanagar", "kailashahar", "ambassa", "belonia", "gomati", "khowai"],
        "bbox": (22.9, 91.1, 24.5, 92.3),
        "centroid": (23.9408, 91.9882),
    },
    "Uttar Pradesh": {
        "canonical": "Uttar Pradesh",
        "aliases": ["uttar pradesh", "up", "lucknow", "kanpur", "varanasi", "banaras", "kashi", "agra", "noida", "ghaziabad", "prayagraj", "allahabad", "gorakhpur", "meerut", "bareilly", "aligarh", "moradabad", "saharanpur", "ayodhya", "faizabad", "jhansi", "muzaffarnagar", "mathura", "budaun", "rampur", "shahjahanpur", "firozabad", "etawah"],
        "bbox": (23.9, 77.1, 30.4, 84.6),
        "centroid": (26.8467, 80.9462),
    },
    "Uttarakhand": {
        "canonical": "Uttarakhand",
        "aliases": ["uttarakhand", "uttaranchal", "uk", "dehradun", "rishikesh", "haridwar", "chamoli", "joshimath", "nainital", "kedarnath", "badrinath", "uttarkashi", "rudraprayag", "pithoragarh", "tehri", "tehri garhwal", "almora", "haldwani", "roorkee", "pauri", "pauri garhwal", "champawat", "bageshwar", "udham singh nagar"],
        "bbox": (28.7, 77.6, 31.5, 81.1),
        "centroid": (30.0668, 79.0193),
    },
    "West Bengal": {
        "canonical": "West Bengal",
        "aliases": ["west bengal", "bengal", "wb", "kolkata", "calcutta", "howrah", "darjeeling", "siliguri", "birbhum", "durgapur", "asansol", "sunderbans", "sundarbans", "jalpaiguri", "kalimpong", "malda", "murshidabad", "nadia", "north 24 parganas", "south 24 parganas", "hooghly", "paschim medinipur", "purba medinipur", "bankura", "purulia", "cooch behar", "alipurduar"],
        "bbox": (21.5, 85.8, 27.2, 89.9),
        "centroid": (22.9868, 87.8550),
    },
    "Delhi": {
        "canonical": "Delhi",
        "aliases": ["delhi", "new delhi", "nct of delhi", "delhi ncr", "delhi-ncr", "ncr", "national capital territory of delhi"],
        "bbox": (28.4, 76.8, 28.9, 77.4),
        "centroid": (28.7041, 77.1025),
    },
    "Jammu and Kashmir": {
        "canonical": "Jammu and Kashmir",
        "aliases": ["jammu and kashmir", "jammu & kashmir", "jammu kashmir", "j&k", "kashmir", "jammu", "srinagar", "anantnag", "baramulla", "budgam", "pulwama", "kupwara", "shopian", "ganderbal", "bandipora", "kulgam", "poonch", "rajouri", "kathua", "udhampur", "doda", "ramban", "reasi", "kishtwar", "samba", "bhalesa"],
        "bbox": (32.2, 73.4, 36.0, 77.6),
        "centroid": (33.7782, 76.5762),
    },
    "Ladakh": {
        "canonical": "Ladakh",
        "aliases": ["ladakh", "leh", "kargil", "nubra", "drass", "zanskar", "changthang"],
        "bbox": (32.5, 75.5, 36.0, 80.5),
        "centroid": (34.1526, 77.5771),
    },
    "Puducherry": {
        "canonical": "Puducherry",
        "aliases": ["puducherry", "pondicherry", "karaikal", "mahe", "yanam"],
        "bbox": (11.7, 79.6, 12.1, 79.9),
        "centroid": (11.9416, 79.8083),
    },
    "Chandigarh": {
        "canonical": "Chandigarh",
        "aliases": ["chandigarh"],
        "bbox": (30.6, 76.7, 30.8, 76.9),
        "centroid": (30.7333, 76.7794),
    },
    "Andaman and Nicobar Islands": {
        "canonical": "Andaman and Nicobar Islands",
        "aliases": ["andaman and nicobar islands", "andaman and nicobar", "andaman & nicobar", "andaman & nicobar islands", "port blair", "andaman", "nicobar", "havelock", "diglipur"],
        "bbox": (6.7, 92.2, 13.7, 94.0),
        "centroid": (11.7401, 92.6586),
    },
    "Dadra and Nagar Haveli and Daman and Diu": {
        "canonical": "Dadra and Nagar Haveli and Daman and Diu",
        "aliases": ["dadra and nagar haveli and daman and diu", "dadra and nagar haveli", "daman and diu", "daman", "diu", "silvassa"],
        "bbox": (20.0, 72.7, 20.6, 73.2),
        "centroid": (20.4283, 72.8397),
    },
    "Lakshadweep": {
        "canonical": "Lakshadweep",
        "aliases": ["lakshadweep", "kavaratti", "agatti", "minicoy", "amindivi"],
        "bbox": (8.0, 71.5, 12.5, 74.0),
        "centroid": (10.5667, 72.6417),
    },
}

# Fast lookup from alias -> canonical state
_ALIAS_TO_CANONICAL_STATE: Dict[str, str] = {}
for state_name, state_meta in STATE_REGISTRY.items():
    _ALIAS_TO_CANONICAL_STATE[state_name.lower()] = state_name
    for alias in state_meta["aliases"]:
        _ALIAS_TO_CANONICAL_STATE[alias.lower()] = state_name


# ============================================================================
# 2. CANONICAL DISTRICT & CITY REGISTRY WITH CENTROIDS & BOUNDING TOLERANCES
# ============================================================================

DISTRICT_REGISTRY: Dict[str, Dict[str, Any]] = {
    # --- Gujarat ---
    "ahmedabad": {"canonical": "Ahmedabad", "state": "Gujarat", "centroid": (23.0225, 72.5714), "bbox": (21.9, 71.7, 23.6, 72.9), "radius_km": 50},
    "surat": {"canonical": "Surat", "state": "Gujarat", "centroid": (21.1702, 72.8311), "bbox": (20.8, 72.6, 21.6, 73.4), "radius_km": 45},
    "vadodara": {"canonical": "Vadodara", "state": "Gujarat", "centroid": (22.3072, 73.1812), "bbox": (21.8, 72.9, 22.7, 73.6), "radius_km": 40},
    "rajkot": {"canonical": "Rajkot", "state": "Gujarat", "centroid": (22.3039, 70.8022), "bbox": (21.5, 70.3, 22.8, 71.3), "radius_km": 45},
    "bhavnagar": {"canonical": "Bhavnagar", "state": "Gujarat", "centroid": (21.7645, 72.1519), "bbox": (21.3, 71.6, 22.2, 72.4), "radius_km": 45},
    "kutch": {"canonical": "Kutch", "state": "Gujarat", "centroid": (23.7337, 69.8597), "bbox": (22.7, 68.1, 24.7, 71.4), "radius_km": 80},
    "bhuj": {"canonical": "Bhuj", "state": "Gujarat", "centroid": (23.2420, 69.6669), "bbox": (23.0, 69.4, 23.5, 70.0), "radius_km": 30},
    "jamnagar": {"canonical": "Jamnagar", "state": "Gujarat", "centroid": (22.4707, 70.0577), "bbox": (21.9, 69.5, 22.8, 70.6), "radius_km": 45},
    "morbi": {"canonical": "Morbi", "state": "Gujarat", "centroid": (22.8173, 70.8370), "bbox": (22.5, 70.5, 23.2, 71.3), "radius_km": 35},
    "gandhinagar": {"canonical": "Gandhinagar", "state": "Gujarat", "centroid": (23.2156, 72.6369), "bbox": (23.0, 72.5, 23.4, 72.8), "radius_km": 30},
    "junagadh": {"canonical": "Junagadh", "state": "Gujarat", "centroid": (21.5222, 70.4579), "bbox": (21.1, 70.0, 21.8, 70.8), "radius_km": 40},

    # --- Assam ---
    "kamrup": {"canonical": "Kamrup", "state": "Assam", "centroid": (26.1445, 91.7362), "bbox": (25.8, 91.2, 26.5, 92.1), "radius_km": 50},
    "guwahati": {"canonical": "Guwahati", "state": "Assam", "centroid": (26.1445, 91.7362), "bbox": (26.0, 91.6, 26.3, 91.9), "radius_km": 30},
    "dibrugarh": {"canonical": "Dibrugarh", "state": "Assam", "centroid": (27.4728, 94.9120), "bbox": (27.1, 94.6, 27.7, 95.3), "radius_km": 45},
    "silchar": {"canonical": "Silchar", "state": "Assam", "centroid": (24.8333, 92.7789), "bbox": (24.6, 92.6, 25.1, 93.0), "radius_km": 35},
    "cachar": {"canonical": "Cachar", "state": "Assam", "centroid": (24.8333, 92.7789), "bbox": (24.4, 92.5, 25.2, 93.2), "radius_km": 50},
    "jorhat": {"canonical": "Jorhat", "state": "Assam", "centroid": (26.7509, 94.2037), "bbox": (26.5, 94.0, 27.0, 94.5), "radius_km": 40},
    "nagaon": {"canonical": "Nagaon", "state": "Assam", "centroid": (26.3464, 92.6840), "bbox": (26.0, 92.4, 26.7, 93.1), "radius_km": 45},
    "dhemaji": {"canonical": "Dhemaji", "state": "Assam", "centroid": (27.4833, 94.5833), "bbox": (27.2, 94.3, 27.8, 95.1), "radius_km": 45},
    "barpeta": {"canonical": "Barpeta", "state": "Assam", "centroid": (26.3200, 91.0000), "bbox": (26.1, 90.8, 26.6, 91.3), "radius_km": 40},
    "morigaon": {"canonical": "Morigaon", "state": "Assam", "centroid": (26.2500, 92.3333), "bbox": (26.0, 92.1, 26.5, 92.6), "radius_km": 40},
    "tezpur": {"canonical": "Tezpur", "state": "Assam", "centroid": (26.6528, 92.7926), "bbox": (26.4, 92.6, 26.9, 93.0), "radius_km": 35},
    "sivasagar": {"canonical": "Sivasagar", "state": "Assam", "centroid": (26.9826, 94.6425), "bbox": (26.7, 94.4, 27.2, 94.9), "radius_km": 40},

    # --- Uttarakhand ---
    "chamoli": {"canonical": "Chamoli", "state": "Uttarakhand", "centroid": (30.4000, 79.3333), "bbox": (30.0, 79.0, 31.0, 80.1), "radius_km": 60},
    "joshimath": {"canonical": "Joshimath", "state": "Uttarakhand", "centroid": (30.5564, 79.5658), "bbox": (30.4, 79.4, 30.7, 79.7), "radius_km": 25},
    "dehradun": {"canonical": "Dehradun", "state": "Uttarakhand", "centroid": (30.3165, 78.0322), "bbox": (29.9, 77.6, 30.7, 78.3), "radius_km": 45},
    "haridwar": {"canonical": "Haridwar", "state": "Uttarakhand", "centroid": (29.9457, 78.1642), "bbox": (29.7, 77.9, 30.2, 78.4), "radius_km": 35},
    "rishikesh": {"canonical": "Rishikesh", "state": "Uttarakhand", "centroid": (30.0869, 78.2676), "bbox": (29.95, 78.15, 30.2, 78.35), "radius_km": 20},
    "nainital": {"canonical": "Nainital", "state": "Uttarakhand", "centroid": (29.3919, 79.4542), "bbox": (29.0, 79.1, 29.7, 79.8), "radius_km": 40},
    "uttarkashi": {"canonical": "Uttarkashi", "state": "Uttarakhand", "centroid": (30.7268, 78.4354), "bbox": (30.4, 77.9, 31.5, 79.4), "radius_km": 60},
    "rudraprayag": {"canonical": "Rudraprayag", "state": "Uttarakhand", "centroid": (30.2844, 78.9811), "bbox": (30.1, 78.7, 30.7, 79.3), "radius_km": 40},
    "pithoragarh": {"canonical": "Pithoragarh", "state": "Uttarakhand", "centroid": (29.5829, 80.2182), "bbox": (29.2, 79.8, 30.3, 80.6), "radius_km": 50},

    # --- Himachal Pradesh ---
    "shimla": {"canonical": "Shimla", "state": "Himachal Pradesh", "centroid": (31.1048, 77.1734), "bbox": (30.8, 76.9, 31.4, 77.5), "radius_km": 40},
    "kullu": {"canonical": "Kullu", "state": "Himachal Pradesh", "centroid": (31.9579, 77.1095), "bbox": (31.6, 76.8, 32.4, 77.6), "radius_km": 50},
    "manali": {"canonical": "Manali", "state": "Himachal Pradesh", "centroid": (32.2432, 77.1892), "bbox": (32.1, 77.0, 32.4, 77.3), "radius_km": 25},
    "mandi": {"canonical": "Mandi", "state": "Himachal Pradesh", "centroid": (31.7087, 76.9320), "bbox": (31.4, 76.6, 32.0, 77.3), "radius_km": 45},
    "dharamshala": {"canonical": "Dharamshala", "state": "Himachal Pradesh", "centroid": (32.2190, 76.3234), "bbox": (32.1, 76.2, 32.4, 76.5), "radius_km": 25},
    "kangra": {"canonical": "Kangra", "state": "Himachal Pradesh", "centroid": (32.0998, 76.2691), "bbox": (31.8, 75.6, 32.5, 77.0), "radius_km": 50},
    "sirmaur": {"canonical": "Sirmaur", "state": "Himachal Pradesh", "centroid": (30.6500, 77.3000), "bbox": (30.4, 77.0, 31.0, 77.8), "radius_km": 45},

    # --- Kerala ---
    "wayanad": {"canonical": "Wayanad", "state": "Kerala", "centroid": (11.6854, 76.1320), "bbox": (11.4, 75.8, 11.9, 76.4), "radius_km": 40},
    "idukki": {"canonical": "Idukki", "state": "Kerala", "centroid": (9.8494, 76.9810), "bbox": (9.5, 76.6, 10.3, 77.4), "radius_km": 50},
    "kochi": {"canonical": "Kochi", "state": "Kerala", "centroid": (9.9312, 76.2673), "bbox": (9.8, 76.1, 10.1, 76.4), "radius_km": 30},
    "ernakulam": {"canonical": "Ernakulam", "state": "Kerala", "centroid": (9.9816, 76.2999), "bbox": (9.7, 76.1, 10.3, 76.7), "radius_km": 40},
    "thiruvananthapuram": {"canonical": "Thiruvananthapuram", "state": "Kerala", "centroid": (8.5241, 76.9366), "bbox": (8.2, 76.7, 8.8, 77.3), "radius_km": 40},
    "kozhikode": {"canonical": "Kozhikode", "state": "Kerala", "centroid": (11.2588, 75.7804), "bbox": (11.0, 75.5, 11.6, 76.1), "radius_km": 40},
    "thrissur": {"canonical": "Thrissur", "state": "Kerala", "centroid": (10.5276, 76.2144), "bbox": (10.2, 75.9, 10.8, 76.6), "radius_km": 40},
    "alappuzha": {"canonical": "Alappuzha", "state": "Kerala", "centroid": (9.4981, 76.3388), "bbox": (9.1, 76.2, 9.8, 76.6), "radius_km": 35},

    # --- Maharashtra ---
    "mumbai": {"canonical": "Mumbai", "state": "Maharashtra", "centroid": (19.0760, 72.8777), "bbox": (18.8, 72.7, 19.3, 73.1), "radius_km": 35},
    "pune": {"canonical": "Pune", "state": "Maharashtra", "centroid": (18.5204, 73.8567), "bbox": (18.1, 73.4, 19.1, 74.5), "radius_km": 50},
    "nagpur": {"canonical": "Nagpur", "state": "Maharashtra", "centroid": (21.1458, 79.0882), "bbox": (20.6, 78.4, 21.6, 79.6), "radius_km": 50},
    "thane": {"canonical": "Thane", "state": "Maharashtra", "centroid": (19.2183, 72.9781), "bbox": (18.9, 72.8, 19.6, 73.4), "radius_km": 40},
    "nashik": {"canonical": "Nashik", "state": "Maharashtra", "centroid": (19.9975, 73.7898), "bbox": (19.5, 73.2, 20.6, 74.8), "radius_km": 50},
    "kolhapur": {"canonical": "Kolhapur", "state": "Maharashtra", "centroid": (16.7050, 74.2433), "bbox": (16.3, 73.7, 17.2, 74.7), "radius_km": 45},
    "raigad": {"canonical": "Raigad", "state": "Maharashtra", "centroid": (18.5158, 73.1822), "bbox": (17.9, 72.8, 19.1, 73.6), "radius_km": 50},
    "ratnagiri": {"canonical": "Ratnagiri", "state": "Maharashtra", "centroid": (16.9902, 73.3120), "bbox": (16.5, 73.0, 17.8, 73.8), "radius_km": 50},

    # --- Odisha ---
    "bhubaneswar": {"canonical": "Bhubaneswar", "state": "Odisha", "centroid": (20.2961, 85.8245), "bbox": (20.1, 85.6, 20.5, 86.0), "radius_km": 30},
    "cuttack": {"canonical": "Cuttack", "state": "Odisha", "centroid": (20.4625, 85.8828), "bbox": (20.2, 85.6, 20.8, 86.2), "radius_km": 40},
    "puri": {"canonical": "Puri", "state": "Odisha", "centroid": (19.8135, 85.8312), "bbox": (19.6, 85.5, 20.2, 86.3), "radius_km": 40},
    "balasore": {"canonical": "Balasore", "state": "Odisha", "centroid": (21.4934, 86.9135), "bbox": (21.2, 86.5, 21.9, 87.3), "radius_km": 45},
    "rourkela": {"canonical": "Rourkela", "state": "Odisha", "centroid": (22.2604, 84.8536), "bbox": (22.0, 84.6, 22.5, 85.1), "radius_km": 35},

    # --- West Bengal ---
    "kolkata": {"canonical": "Kolkata", "state": "West Bengal", "centroid": (22.5726, 88.3639), "bbox": (22.4, 88.2, 22.8, 88.5), "radius_km": 30},
    "howrah": {"canonical": "Howrah", "state": "West Bengal", "centroid": (22.5958, 88.2636), "bbox": (22.4, 88.1, 22.8, 88.4), "radius_km": 30},
    "darjeeling": {"canonical": "Darjeeling", "state": "West Bengal", "centroid": (27.0410, 88.2663), "bbox": (26.7, 88.0, 27.3, 88.6), "radius_km": 40},
    "siliguri": {"canonical": "Siliguri", "state": "West Bengal", "centroid": (26.7271, 88.3953), "bbox": (26.6, 88.2, 26.9, 88.6), "radius_km": 25},
    "asansol": {"canonical": "Asansol", "state": "West Bengal", "centroid": (23.6889, 86.9661), "bbox": (23.5, 86.8, 23.9, 87.2), "radius_km": 35},
    "durgapur": {"canonical": "Durgapur", "state": "West Bengal", "centroid": (23.5204, 87.3119), "bbox": (23.4, 87.1, 23.7, 87.5), "radius_km": 30},

    # --- Tamil Nadu ---
    "chennai": {"canonical": "Chennai", "state": "Tamil Nadu", "centroid": (13.0827, 80.2707), "bbox": (12.8, 80.0, 13.3, 80.4), "radius_km": 40},
    "coimbatore": {"canonical": "Coimbatore", "state": "Tamil Nadu", "centroid": (11.0168, 76.9558), "bbox": (10.7, 76.6, 11.3, 77.3), "radius_km": 45},
    "madurai": {"canonical": "Madurai", "state": "Tamil Nadu", "centroid": (9.9252, 78.1198), "bbox": (9.6, 77.8, 10.2, 78.4), "radius_km": 40},

    # --- Telangana ---
    "hyderabad": {"canonical": "Hyderabad", "state": "Telangana", "centroid": (17.3850, 78.4867), "bbox": (17.1, 78.2, 17.6, 78.7), "radius_km": 40},
    "warangal": {"canonical": "Warangal", "state": "Telangana", "centroid": (17.9689, 79.5941), "bbox": (17.7, 79.3, 18.2, 79.9), "radius_km": 35},

    # --- Uttar Pradesh ---
    "lucknow": {"canonical": "Lucknow", "state": "Uttar Pradesh", "centroid": (26.8467, 80.9462), "bbox": (26.5, 80.6, 27.2, 81.3), "radius_km": 45},
    "kanpur": {"canonical": "Kanpur", "state": "Uttar Pradesh", "centroid": (26.4499, 80.3319), "bbox": (26.2, 80.0, 26.8, 80.6), "radius_km": 45},
    "varanasi": {"canonical": "Varanasi", "state": "Uttar Pradesh", "centroid": (25.3176, 82.9739), "bbox": (25.1, 82.7, 25.5, 83.2), "radius_km": 35},
    "agra": {"canonical": "Agra", "state": "Uttar Pradesh", "centroid": (27.1767, 78.0081), "bbox": (26.9, 77.7, 27.4, 78.3), "radius_km": 40},
    "noida": {"canonical": "Noida", "state": "Uttar Pradesh", "centroid": (28.5355, 77.3910), "bbox": (28.4, 77.2, 28.7, 77.5), "radius_km": 25},
    "ghaziabad": {"canonical": "Ghaziabad", "state": "Uttar Pradesh", "centroid": (28.6692, 77.4538), "bbox": (28.5, 77.3, 28.9, 77.6), "radius_km": 30},
    "prayagraj": {"canonical": "Prayagraj", "state": "Uttar Pradesh", "centroid": (25.4358, 81.8463), "bbox": (25.1, 81.5, 25.7, 82.2), "radius_km": 45},
}


# ============================================================================
# 3. COORDINATE VALIDATION & DISTANCE CALCULATIONS
# ============================================================================

def is_valid_coordinate(lat: Any, lon: Any) -> bool:
    """
    Validates if coordinates are present, numeric, within real world ranges,
    and NOT artificial fallback coordinates (like India centroid).
    """
    if lat is None or lon is None:
        return False

    try:
        flat = float(lat)
        flon = float(lon)
    except (ValueError, TypeError):
        return False

    if math.isnan(flat) or math.isnan(flon) or math.isinf(flat) or math.isinf(flon):
        return False

    # Real spherical coordinate bounds
    if not (-90.0 <= flat <= 90.0 and -180.0 <= flon <= 180.0):
        return False

    # Reject null island (0, 0)
    if abs(flat) < 0.001 and abs(flon) < 0.001:
        return False

    # Strictly reject known artificial default centroids
    for f_lat, f_lon in FORBIDDEN_FALLBACK_CENTROIDS:
        if abs(flat - f_lat) < 0.01 and abs(flon - f_lon) < 0.01:
            return False

    # Coordinates must be broadly within India's disaster envelope
    # (including offshore EEZ / Andaman / Lakshadweep)
    if not (INDIA_BBOX[0] <= flat <= INDIA_BBOX[2] and INDIA_BBOX[1] <= flon <= INDIA_BBOX[3]):
        return False

    return True


def is_inside_bbox(lat: float, lon: float, bbox: Tuple[float, float, float, float]) -> bool:
    """Checks whether coordinates (lat, lon) lie within a bounding box (min_lat, min_lon, max_lat, max_lon)."""
    min_lat, min_lon, max_lat, max_lon = bbox
    return (min_lat <= lat <= max_lat) and (min_lon <= lon <= max_lon)


def calculate_haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> Optional[float]:
    """Computes great-circle distance between two GPS coordinates in kilometers."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    try:
        r = 6371.0
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = (
            math.sin(d_lat / 2.0) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(d_lon / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return round(r * c, 2)
    except Exception:
        return None


# ============================================================================
# 4. GEOGRAPHIC NORMALIZATION & AREA QUERY PARSING
# ============================================================================

def normalize_state_name(state_raw: Optional[str]) -> Optional[str]:
    """Normalizes any state string or alias into its canonical Indian state name."""
    if not state_raw or not isinstance(state_raw, str):
        return None

    clean = state_raw.strip().lower()
    if not clean or clean in ["all", "india", "all india"]:
        return None

    # Direct match or alias match
    if clean in _ALIAS_TO_CANONICAL_STATE:
        return _ALIAS_TO_CANONICAL_STATE[clean]

    # Substring / partial matching against canonical names
    for state_name in STATE_REGISTRY:
        if state_name.lower() == clean or clean in state_name.lower():
            return state_name

    return None


def normalize_district_name(district_raw: Optional[str], state_norm: Optional[str] = None) -> Optional[Tuple[str, str]]:
    """
    Normalizes a district name. Returns (canonical_district, canonical_state) or None.
    """
    if not district_raw or not isinstance(district_raw, str):
        return None

    clean = district_raw.strip().lower()
    if not clean or clean in ["all", "all districts"]:
        return None

    # Check direct in DISTRICT_REGISTRY
    if clean in DISTRICT_REGISTRY:
        reg = DISTRICT_REGISTRY[clean]
        if state_norm is None or reg["state"].lower() == state_norm.lower():
            return reg["canonical"], reg["state"]

    # Fuzzy check against known districts
    for key, reg in DISTRICT_REGISTRY.items():
        if key in clean or clean in key:
            if state_norm is None or reg["state"].lower() == state_norm.lower():
                return reg["canonical"], reg["state"]

    return None


def normalize_geographic_query(
    country: Optional[str] = "India",
    state: Optional[str] = None,
    district: Optional[str] = None,
    city: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validates and resolves geographic filter query parameters into a structured area context.
    Determines administrative level: 'country', 'state', 'district', or 'city'.
    """
    if not isinstance(country, str):
        country = "India"
    if not isinstance(state, str):
        state = None
    if not isinstance(district, str):
        district = None
    if not isinstance(city, str):
        city = None

    canonical_state = normalize_state_name(state)

    target_district_raw = district or city
    canonical_district = None
    if target_district_raw:
        dist_res = normalize_district_name(target_district_raw, canonical_state)
        if dist_res:
            canonical_district, parent_state = dist_res
            if not canonical_state:
                canonical_state = parent_state
        else:
            canonical_district = target_district_raw.strip().title()

    # Determine administrative level
    if canonical_district:
        level = "district" if not city else "city"
        display_name = f"{canonical_district}, {canonical_state}" if canonical_state else canonical_district
        dist_meta = DISTRICT_REGISTRY.get(canonical_district.lower())
        centroid = dist_meta["centroid"] if dist_meta else None
        bbox = dist_meta["bbox"] if dist_meta else (STATE_REGISTRY.get(canonical_state, {}).get("bbox") if canonical_state else None)
    elif canonical_state:
        level = "state"
        display_name = canonical_state
        state_meta = STATE_REGISTRY.get(canonical_state)
        centroid = state_meta["centroid"] if state_meta else None
        bbox = state_meta["bbox"] if state_meta else None
    else:
        level = "country"
        display_name = "India (All India)"
        centroid = INDIA_CENTROID
        bbox = INDIA_BBOX

    return {
        "level": level,
        "country": "India",
        "state": canonical_state,
        "district": canonical_district,
        "city": city.strip().title() if city else None,
        "display_name": display_name,
        "centroid": centroid,
        "bbox": bbox,
    }


# ============================================================================
# 5. GEOGRAPHIC ELIGIBILITY EVALUATION
# ============================================================================

class GeoMatchResult(dict):
    """
    Dict subclass that allows dictionary key access (e.g. res['is_match'])
    as well as tuple unpacking (is_match, is_mappable = evaluate_event_geographic_match(...)).
    """
    def __iter__(self):
        yield self.get("is_match", False)
        yield self.get("is_mappable", False)


def _evaluate_event_geographic_match_impl(
    event: Dict[str, Any],
    query_area: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluates whether an event/news document belongs to the specified geographic area.
    Never relies on loose substring matching inside unrelated article titles.
    Strictly separates:
    - is_match: whether event logically belongs to the area
    - is_mappable: whether event has valid, verified coordinates appropriate for map display
    - has_coordinates: whether coordinates are present and valid
    - location_status: provenance status ('exact', 'district', 'state', 'unresolved')
    """
    loc = event.get("location")
    raw_lat = None
    raw_lon = None
    if isinstance(loc, dict):
        raw_lat = loc.get("latitude") if loc.get("latitude") is not None else loc.get("lat")
        raw_lon = loc.get("longitude") if loc.get("longitude") is not None else loc.get("lon")

    if raw_lat is None:
        raw_lat = event.get("latitude") if event.get("latitude") is not None else event.get("lat")
    if raw_lon is None:
        raw_lon = event.get("longitude") if event.get("longitude") is not None else event.get("lon")

    # Extract structured metadata
    event_state = None
    event_district = None
    event_city = None

    if isinstance(loc, dict):
        event_state = normalize_state_name(loc.get("state"))
        event_district = loc.get("district")
        event_city = loc.get("city")

    if not event_state and event.get("state"):
        event_state = normalize_state_name(event.get("state"))
    if not event_district and event.get("district"):
        event_district = event.get("district")
    if not event_city and event.get("city"):
        event_city = event.get("city")

    # Validate coordinates
    has_valid_coords = is_valid_coordinate(raw_lat, raw_lon)
    lat = float(raw_lat) if has_valid_coords else None
    lon = float(raw_lon) if has_valid_coords else None

    # Provenance
    location_status = event.get("location_status")
    if not location_status:
        if isinstance(loc, dict) and loc.get("precision"):
            location_status = loc["precision"]
        elif has_valid_coords:
            location_status = "exact"
        else:
            location_status = "unresolved"

    if not has_valid_coords:
        location_status = "unresolved"

    req_level = query_area["level"]
    req_state = query_area["state"]
    req_district = query_area["district"]

    # ------------------------------------------------------------------------
    # LEVEL 1: ALL INDIA
    # ------------------------------------------------------------------------
    if req_level == "country":
        # All events in India database are logically eligible candidates for India
        is_mappable = has_valid_coords
        return {
            "is_match": True,
            "is_mappable": is_mappable,
            "has_coordinates": has_valid_coords,
            "location_status": location_status,
            "latitude": lat,
            "longitude": lon,
            "state": event_state or "",
            "district": event_district or "",
            "city": event_city or "",
            "reason": "country_wide_match",
        }

    # ------------------------------------------------------------------------
    # LEVEL 2: STATE-LEVEL FILTERING (e.g., Gujarat)
    # ------------------------------------------------------------------------
    if req_level == "state":
        state_meta = STATE_REGISTRY.get(req_state)
        state_bbox = state_meta["bbox"] if state_meta else None

        # Rule A: Explicit state mismatch (e.g. event belongs to Assam, query is Gujarat)
        if event_state and event_state.lower() != req_state.lower():
            return {
                "is_match": False,
                "is_mappable": False,
                "has_coordinates": has_valid_coords,
                "location_status": location_status,
                "latitude": lat,
                "longitude": lon,
                "state": event_state,
                "district": event_district or "",
                "city": event_city or "",
                "reason": f"state_mismatch (belongs to {event_state}, requested {req_state})",
            }

        # Rule B: Structured state match
        if event_state and event_state.lower() == req_state.lower():
            is_mappable = False
            if has_valid_coords and state_bbox:
                # Coordinate must be inside the state's bounding box
                is_mappable = is_inside_bbox(lat, lon, state_bbox)
            elif has_valid_coords:
                is_mappable = True

            return {
                "is_match": True,
                "is_mappable": is_mappable,
                "has_coordinates": has_valid_coords,
                "location_status": location_status,
                "latitude": lat,
                "longitude": lon,
                "state": req_state,
                "district": event_district or "",
                "city": event_city or "",
                "reason": "structured_state_match",
            }

        # Rule C: Coordinates inside state bounding box (when structured state was omitted)
        if has_valid_coords and state_bbox and is_inside_bbox(lat, lon, state_bbox):
            return {
                "is_match": True,
                "is_mappable": True,
                "has_coordinates": True,
                "location_status": location_status,
                "latitude": lat,
                "longitude": lon,
                "state": req_state,
                "district": event_district or "",
                "city": event_city or "",
                "reason": "bbox_state_match",
            }

        # Unresolved records without state confirmation do NOT match a specific state
        return {
            "is_match": False,
            "is_mappable": False,
            "has_coordinates": has_valid_coords,
            "location_status": location_status,
            "latitude": lat,
            "longitude": lon,
            "state": event_state or "",
            "district": event_district or "",
            "city": event_city or "",
            "reason": "unresolved_location_insufficient_for_state",
        }

    # ------------------------------------------------------------------------
    # LEVEL 3: DISTRICT / CITY LEVEL FILTERING (e.g., Ahmedabad, Gujarat)
    # ------------------------------------------------------------------------
    if req_level in ["district", "city"]:
        req_dist_norm = req_district.lower() if req_district else ""
        dist_meta = DISTRICT_REGISTRY.get(req_dist_norm)
        dist_bbox = dist_meta["bbox"] if dist_meta else None
        dist_centroid = dist_meta["centroid"] if dist_meta else None
        dist_radius_km = dist_meta.get("radius_km", 45) if dist_meta else 45

        # Check state alignment if state is known
        if req_state and event_state and event_state.lower() != req_state.lower():
            return {
                "is_match": False,
                "is_mappable": False,
                "has_coordinates": has_valid_coords,
                "location_status": location_status,
                "latitude": lat,
                "longitude": lon,
                "reason": f"state_mismatch for district (belongs to {event_state})",
            }

        # Check if event has a DIFFERENT known district in the registry
        if event_district:
            ed_norm = event_district.strip().lower()
            if ed_norm != req_dist_norm and ed_norm in DISTRICT_REGISTRY:
                # Event explicitly belongs to another distinct district (e.g. Surat when Ahmedabad requested)
                return {
                    "is_match": False,
                    "is_mappable": False,
                    "has_coordinates": has_valid_coords,
                    "location_status": location_status,
                    "latitude": lat,
                    "longitude": lon,
                    "reason": f"district_mismatch (belongs to {event_district}, requested {req_district})",
                }

        # Rule A: Structured district or city match
        if (event_district and req_dist_norm in event_district.lower()) or (event_city and req_dist_norm in event_city.lower()):
            is_mappable = False
            if has_valid_coords and dist_bbox:
                is_mappable = is_inside_bbox(lat, lon, dist_bbox)
            elif has_valid_coords and dist_centroid:
                d_km = calculate_haversine_km(lat, lon, dist_centroid[0], dist_centroid[1])
                is_mappable = d_km is not None and d_km <= dist_radius_km
            elif has_valid_coords:
                is_mappable = True

            return {
                "is_match": True,
                "is_mappable": is_mappable,
                "has_coordinates": has_valid_coords,
                "location_status": location_status,
                "latitude": lat,
                "longitude": lon,
                "state": event_state or (dist_meta["state"] if dist_meta else req_state),
                "district": req_district,
                "city": event_city or "",
                "reason": "structured_district_match",
            }

        # Rule B: Coordinate-based district match
        if has_valid_coords and dist_centroid:
            d_km = calculate_haversine_km(lat, lon, dist_centroid[0], dist_centroid[1])
            if d_km is not None and d_km <= dist_radius_km:
                return {
                    "is_match": True,
                    "is_mappable": True,
                    "has_coordinates": True,
                    "location_status": location_status,
                    "latitude": lat,
                    "longitude": lon,
                    "state": dist_meta["state"] if dist_meta else req_state,
                    "district": req_district,
                    "city": event_city or "",
                    "reason": f"proximity_district_match ({d_km}km from centroid)",
                }

        # Did not match district
        return {
            "is_match": False,
            "is_mappable": False,
            "has_coordinates": has_valid_coords,
            "location_status": location_status,
            "latitude": lat,
            "longitude": lon,
            "reason": "district_not_matched",
        }

    return {
        "is_match": False,
        "is_mappable": False,
        "has_coordinates": has_valid_coords,
        "location_status": location_status,
        "latitude": lat,
        "longitude": lon,
        "reason": "unhandled_level",
    }




def evaluate_event_geographic_match(
    event: Dict[str, Any],
    query_area: Optional[Dict[str, Any]] = None,
    country: Optional[str] = "India",
    state: Optional[str] = None,
    district: Optional[str] = None,
    city: Optional[str] = None,
) -> GeoMatchResult:
    """
    Public entry point for evaluating geographic match.
    Accepts either a pre-computed query_area dict or keyword arguments (state, district, city).
    Returns GeoMatchResult supporting dict access and (is_match, is_mappable) tuple unpacking.
    """
    if query_area is None:
        query_area = normalize_geographic_query(
            country=country,
            state=state,
            district=district,
            city=city,
        )
    res = _evaluate_event_geographic_match_impl(event, query_area)
    return GeoMatchResult(res)


# ============================================================================
# 6. GEOCODING CACHE & RESOLUTION
# ============================================================================

_GEOCODE_CACHE: Dict[str, Tuple[Optional[float], Optional[float], str]] = {}

def geocode_with_cache(
    country: str = "India",
    state: Optional[str] = None,
    district: Optional[str] = None,
    city: Optional[str] = None,
) -> Tuple[Optional[float], Optional[float], str]:
    """
    Deterministic cached geocoding helper.
    Returns: (latitude, longitude, precision)
    Never Assigns India Centroid to unknown locations.
    """
    cache_key = f"{country or ''}_{state or ''}_{district or ''}_{city or ''}".strip().lower()
    if cache_key in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[cache_key]

    # 1. District or city lookup
    target_place = (city or district or "").strip().lower()
    if target_place and target_place in DISTRICT_REGISTRY:
        cent = DISTRICT_REGISTRY[target_place]["centroid"]
        res = (cent[0], cent[1], "district" if not city else "city")
        _GEOCODE_CACHE[cache_key] = res
        return res

    # 2. State lookup
    if state:
        st_norm = normalize_state_name(state)
        if st_norm and st_norm in STATE_REGISTRY:
            cent = STATE_REGISTRY[st_norm]["centroid"]
            res = (cent[0], cent[1], "state")
            _GEOCODE_CACHE[cache_key] = res
            return res

    # 3. Country only / unresolved -> Do NOT assign fake coordinates
    res = (None, None, "unresolved")
    _GEOCODE_CACHE[cache_key] = res
    return res


def get_all_states() -> List[str]:
    """Returns sorted list of all 36 canonical Indian states & UTs."""
    return sorted(list(STATE_REGISTRY.keys()))


def get_districts_for_state(state_name: str) -> List[str]:
    """Returns list of all registered districts for a given state."""
    st_norm = normalize_state_name(state_name)
    if not st_norm:
        return []
    return sorted([
        meta["canonical"]
        for meta in DISTRICT_REGISTRY.values()
        if meta["state"].lower() == st_norm.lower()
    ])
