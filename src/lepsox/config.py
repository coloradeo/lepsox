"""
Configuration for LepSoc Validation System
"""
import os
from typing import List

# Server Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://192.168.51.99:30068")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))  # Timeout in seconds for LLM calls
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "10m")  # Keep model loaded in memory
INAT_MCP_URL = os.getenv("INAT_MCP_URL", "http://192.168.51.99:8811/sse")

# Validation Constants
VALID_ZONES: List[int] = list(range(1, 13))  # 1-12
VALID_COUNTRIES: List[str] = ["USA", "CAN", "MEX"]
DATE_FORMAT: str = r'^\d{1,2}-[A-Z]{3}-\d{2}$'

# US State abbreviations
US_STATES: List[str] = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"
]

# US State abbreviation to full name mapping
US_STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia"
}

# Canadian provinces
CAN_PROVINCES: List[str] = [
    "AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"
]

# Mexican states (abbreviated)
MEX_STATES: List[str] = [
    "AGU", "BCN", "BCS", "CAM", "CHP", "CHH", "COA", "COL", "CMX", "DUR",
    "GUA", "GRO", "HID", "JAL", "MEX", "MIC", "MOR", "NAY", "NLE", "OAX",
    "PUE", "QUE", "ROO", "SLP", "SIN", "SON", "TAB", "TAM", "TLA", "VER", "YUC", "ZAC"
]

# Column names for the 16 data fields
COLUMN_NAMES: List[str] = [
    'Zone', 'Country', 'State', 'Family', 'Genus', 'Species',
    'Sub-species', 'County', 'State Record', 'County Record',
    'Specific Location', 'First Date', 'Last Date', 'Name',
    'Comments', 'Year'
]

# Common Lepidoptera families
COMMON_FAMILIES: List[str] = [
    'Hesperiidae', 'Papilionidae', 'Pieridae', 'Lycaenidae',
    'Riodinidae', 'Nymphalidae', 'Geometridae', 'Erebidae',
    'Noctuidae', 'Notodontidae', 'Sphingidae', 'Saturniidae',
    'Lasiocampidae', 'Megalopygidae', 'Limacodidae', 'Crambidae',
    'Pyralidae', 'Tortricidae', 'Cossidae', 'Sesiidae'
]

# GPS coordinate patterns
GPS_DECIMAL_PATTERN: str = r'[-+]?\d{1,3}\.\d+\s*,\s*[-+]?\d{1,3}\.\d+'
GPS_DMS_PATTERN: str = r'\d{1,3}°\s*\d{1,2}[\'′]\s*\d{1,2}(?:\.\d+)?[\"″]?\s*[NSEW]\s*,?\s*\d{1,3}°\s*\d{1,2}[\'′]\s*\d{1,2}(?:\.\d+)?[\"″]?\s*[NSEW]'

# Standard Lepidopterist Abbreviations
# Used for comment standardization and validation
LEPIDOPTERIST_ABBREVIATIONS = {
    # Location descriptors
    "nr": "near",
    "ca": "circa/approximately",
    "N of": "north of",
    "S of": "south of",
    "E of": "east of",
    "W of": "west of",

    # Collection/observation methods
    "lt": "light trap",
    "mv": "mercury vapor (light)",
    "uv": "ultraviolet (light)",
    "bait": "bait trap/station",
    "net": "aerial net",
    "sweep": "sweep net",
    "reared": "reared from larva/pupa",
    "ex larva": "reared from larva",
    "ex pupa": "reared from pupa",
    "bred": "captive bred",

    # Behaviors
    "nect": "nectaring",
    "puddling": "puddling/mud-puddling",
    "ovipos": "ovipositing",
    "bask": "basking",
    "patrol": "patrolling",
    "hilltopping": "hilltopping behavior",
    "perch": "perching",

    # Life stages
    "L": "larva/larvae",
    "P": "pupa",
    "A": "adult",
    "egg": "egg",
    "cat": "caterpillar",

    # Sex
    "M": "male",
    "F": "female",
    "♂": "male",
    "♀": "female",

    # Specimen condition
    "fresh": "freshly emerged",
    "worn": "worn/old specimen",
    "tattered": "wings tattered",
    "pristine": "perfect condition",

    # Host plants (common)
    "fp": "food plant",
    "hp": "host plant",
    "on": "observed on (plant)",

    # Time of day
    "dawn": "at dawn",
    "dusk": "at dusk",
    "night": "at night",
    "am": "morning",
    "pm": "afternoon/evening",

    # Weather
    "sunny": "sunny conditions",
    "cloudy": "cloudy/overcast",
    "rain": "during/after rain",

    # Quantity
    "1": "single individual",
    "few": "2-5 individuals",
    "sev": "several (5-20)",
    "many": "many (20+)",
    "abund": "abundant",
    "common": "commonly observed",
    "rare": "rarely observed",
}

# Comment Style Guide for AI-powered shortening
COMMENT_STYLE_GUIDE = """
LepSoc Comment Style Guidelines:

Format Rules:
- Maximum 120 characters
- Use standard abbreviations (see LEPIDOPTERIST_ABBREVIATIONS)
- No redundant information from other fields (date, location, species)
- GPS coordinates: Use decimal format (lat,long) or DMS with ° ' "
- Separate distinct observations with semicolon

Preferred Patterns:
- Behavior: "nect on milkweed", "ovipos on oak", "puddling"
- Method: "lt", "uv lt", "net", "reared ex larva"
- Quantity + behavior: "3F nect", "many at bait", "1M patrol"
- Location modifier: "nr stream", "forest edge", "roadside"
- Condition: "fresh", "worn", "tattered"

Examples:
- Good: "2M 1F nect on Asclepias; fresh; lt"
- Good: "reared ex larva on Quercus rubra"
- Good: "puddling nr stream; 42.5834,-87.8294"
- Bad: "Two males and one female nectaring on common milkweed, freshly emerged, captured at light trap"
"""
