"""
Configuration for LepSoc Validation System
"""
import os
from typing import List

# Server Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://192.168.51.99:30068")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")
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
