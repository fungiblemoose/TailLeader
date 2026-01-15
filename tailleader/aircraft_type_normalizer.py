"""
Aircraft Type Normalizer

Normalizes aircraft type strings to canonical display names for deduplication.
Groups similar variants while preserving meaningful distinctions (e.g., NEO vs CEO, MAX vs NG).
"""

import re
from typing import Optional, Tuple

# Manufacturer name normalization mapping
MANUFACTURER_ALIASES = {
    "AIRBUS": "Airbus",
    "AIRBUS INDUSTRIE": "Airbus",
    "THE BOEING COMPANY": "Boeing",
    "BOEING": "Boeing",
    "BOEING COMPANY": "Boeing",
    "EMBRAER": "Embraer",
    "EMBRAER S.A.": "Embraer",
    "EMBRAER-EMPRESA BRASILEIRA DE AERONAUTICA": "Embraer",
    "BOMBARDIER": "Bombardier",
    "BOMBARDIER INC": "Bombardier",
    "BOMBARDIER INC.": "Bombardier",
    "CESSNA": "Cessna",
    "CESSNA AIRCRAFT": "Cessna",
    "CESSNA AIRCRAFT COMPANY": "Cessna",
    "TEXTRON AVIATION": "Cessna",
    "TEXTRON AVIATION INC": "Cessna",
    "TEXTRON AVIATION INC.": "Cessna",
    "PIPER": "Piper",
    "PIPER AIRCRAFT": "Piper",
    "PIPER AIRCRAFT INC": "Piper",
    "PIPER AIRCRAFT, INC.": "Piper",
    "CIRRUS": "Cirrus",
    "CIRRUS DESIGN": "Cirrus",
    "CIRRUS DESIGN CORP": "Cirrus",
    "CIRRUS DESIGN CORPORATION": "Cirrus",
    "BEECH": "Beechcraft",
    "BEECHCRAFT": "Beechcraft",
    "BEECH AIRCRAFT": "Beechcraft",
    "BEECH AIRCRAFT CORP": "Beechcraft",
    "HAWKER BEECHCRAFT": "Beechcraft",
    "HAWKER BEECHCRAFT CORP": "Beechcraft",
    "RAYTHEON AIRCRAFT": "Beechcraft",
    "RAYTHEON AIRCRAFT COMPANY": "Beechcraft",
    "GULFSTREAM": "Gulfstream",
    "GULFSTREAM AEROSPACE": "Gulfstream",
    "GULFSTREAM AEROSPACE CORP": "Gulfstream",
    "DASSAULT": "Dassault",
    "DASSAULT AVIATION": "Dassault",
    "DASSAULT-BREGUET": "Dassault",
    "LEARJET": "Learjet",
    "LEARJET INC": "Learjet",
    "MCDONNELL DOUGLAS": "McDonnell Douglas",
    "MCDONNELL DOUGLAS CORPORATION": "McDonnell Douglas",
    "LOCKHEED": "Lockheed",
    "LOCKHEED MARTIN": "Lockheed",
    "LOCKHEED CORPORATION": "Lockheed",
    "ATR": "ATR",
    "ATR - GIE AVIONS DE TRANSPORT REGIONAL": "ATR",
    "AVIONS DE TRANSPORT REGIONAL": "ATR",
    "DE HAVILLAND": "De Havilland",
    "DE HAVILLAND CANADA": "De Havilland Canada",
    "DIAMOND": "Diamond",
    "DIAMOND AIRCRAFT": "Diamond",
    "DIAMOND AIRCRAFT INDUSTRIES": "Diamond",
    "MOONEY": "Mooney",
    "MOONEY AIRCRAFT": "Mooney",
    "MOONEY INTERNATIONAL": "Mooney",
    "PILATUS": "Pilatus",
    "PILATUS AIRCRAFT": "Pilatus",
    "PILATUS AIRCRAFT LTD": "Pilatus",
    "ROBINSON": "Robinson",
    "ROBINSON HELICOPTER": "Robinson",
    "ROBINSON HELICOPTER COMPANY": "Robinson",
    "BELL": "Bell",
    "BELL HELICOPTER": "Bell",
    "BELL TEXTRON": "Bell",
    "SIKORSKY": "Sikorsky",
    "SIKORSKY AIRCRAFT": "Sikorsky",
    "EUROCOPTER": "Airbus Helicopters",
    "AIRBUS HELICOPTERS": "Airbus Helicopters",
    "LEONARDO": "Leonardo",
    "LEONARDO HELICOPTERS": "Leonardo",
    "AGUSTA": "Leonardo",
    "AGUSTAWESTLAND": "Leonardo",
    "DAHER": "Daher",
    "DAHER-SOCATA": "Daher",
    "SOCATA": "Daher",
}


def normalize_manufacturer(manufacturer: Optional[str]) -> Optional[str]:
    """Normalize manufacturer name to canonical form."""
    if not manufacturer:
        return None
    key = manufacturer.upper().strip()
    return MANUFACTURER_ALIASES.get(key, manufacturer.strip())


# Aircraft model normalization patterns
# Each tuple: (compiled_regex, canonical_name, manufacturer_override)
# manufacturer_override is optional and used when the model implies the manufacturer
AIRCRAFT_PATTERNS = []

def _init_patterns():
    """Initialize compiled regex patterns for aircraft normalization."""
    global AIRCRAFT_PATTERNS
    
    patterns = [
        # ============ AIRBUS NARROWBODY ============
        # A318
        (r"A\s*318.*", "A318", "Airbus"),
        
        # A319 - distinguish NEO
        (r"A\s*319.*N(?:EO)?.*|A\s*319.*(?:17[1-9]|18\d)N.*", "A319neo", "Airbus"),
        (r"A\s*319.*", "A319", "Airbus"),
        
        # A320 - distinguish NEO
        (r"A\s*320.*N(?:EO)?.*|A\s*320.*(?:27\d)N.*|A\s*320.*251N.*|A\s*320.*271N.*", "A320neo", "Airbus"),
        (r"A\s*320.*", "A320", "Airbus"),
        
        # A321 - distinguish NEO, LR, XLR
        (r"A\s*321.*XLR.*", "A321XLR", "Airbus"),
        (r"A\s*321.*LR.*", "A321LR", "Airbus"),
        (r"A\s*321.*N(?:EO)?.*|A\s*321.*(?:25\d|27\d)N.*", "A321neo", "Airbus"),
        (r"A\s*321.*", "A321", "Airbus"),
        
        # ============ AIRBUS WIDEBODY ============
        # A330 - distinguish NEO
        (r"A\s*330.*N(?:EO)?.*|A\s*330.*(?:8|9)00N.*|A\s*330-8.*|A\s*330-9.*", "A330neo", "Airbus"),
        (r"A\s*330.*300.*|A\s*330-3.*", "A330-300", "Airbus"),
        (r"A\s*330.*200.*|A\s*330-2.*", "A330-200", "Airbus"),
        (r"A\s*330.*", "A330", "Airbus"),
        
        # A340
        (r"A\s*340.*600.*|A\s*340-6.*", "A340-600", "Airbus"),
        (r"A\s*340.*500.*|A\s*340-5.*", "A340-500", "Airbus"),
        (r"A\s*340.*300.*|A\s*340-3.*", "A340-300", "Airbus"),
        (r"A\s*340.*200.*|A\s*340-2.*", "A340-200", "Airbus"),
        (r"A\s*340.*", "A340", "Airbus"),
        
        # A350
        (r"A\s*350.*1000.*|A\s*350-10.*", "A350-1000", "Airbus"),
        (r"A\s*350.*900.*|A\s*350-9.*", "A350-900", "Airbus"),
        (r"A\s*350.*", "A350", "Airbus"),
        
        # A380
        (r"A\s*380.*", "A380", "Airbus"),
        
        # ============ BOEING 737 ============
        # 737 NG (Next Generation) - must come before MAX to catch -8xx, -7xx, etc. customer codes
        # These have 3-character suffixes after the series number (737-823, 737-8H4, etc.)
        (r"737-9[0-9A-Z]{2}.*|737.*NG.*900.*|737.*900.*", "737-900", "Boeing"),
        (r"737-8[0-9A-Z]{2}.*|737.*NG.*800.*|737.*800.*", "737-800", "Boeing"),
        (r"737-7[0-9A-Z]{2}.*|737.*NG.*700.*|737.*700.*", "737-700", "Boeing"),
        (r"737-6[0-9A-Z]{2}.*|737.*NG.*600.*|737.*600.*", "737-600", "Boeing"),
        
        # 737 MAX variants - these have short codes (737-8, 737-9) or explicit MAX
        (r"737.*MAX\s*10.*|737-10(?:\s|$).*", "737 MAX 10", "Boeing"),
        (r"737.*MAX\s*9.*|737-9\s*MAX.*|737-9(?:[\s/]|$)(?![0-9A-Z]{2}).*", "737 MAX 9", "Boeing"),
        (r"737.*MAX\s*8.*|737-8\s*MAX.*|737-8(?:[\s/]|$)(?![0-9A-Z]{2}).*", "737 MAX 8", "Boeing"),
        (r"737.*MAX\s*7.*|737-7\s*MAX.*|737-7(?:[\s/]|$)(?![0-9A-Z]{2}).*", "737 MAX 7", "Boeing"),
        (r"737.*MAX.*", "737 MAX", "Boeing"),
        
        # 737 Classic - 300/400/500 series
        (r"737-5\d{2}.*|737.*500.*", "737-500", "Boeing"),
        (r"737-4\d{2}.*|737.*400.*", "737-400", "Boeing"),
        (r"737-3\d{2}.*|737.*300.*", "737-300", "Boeing"),
        
        # 737 Original - 100/200 series
        (r"737-2\d{2}.*|737.*200.*", "737-200", "Boeing"),
        (r"737-1\d{2}.*|737.*100.*", "737-100", "Boeing"),
        
        # Generic 737
        (r"737.*", "737", "Boeing"),
        
        # ============ BOEING 747 ============
        (r"747-8.*|747.*8[IF].*", "747-8", "Boeing"),
        (r"747-400.*|747-4\d{2}.*", "747-400", "Boeing"),
        (r"747-300.*|747-3\d{2}.*", "747-300", "Boeing"),
        (r"747-200.*|747-2\d{2}.*", "747-200", "Boeing"),
        (r"747-100.*|747-1\d{2}.*|747SP.*", "747-100", "Boeing"),
        (r"747.*", "747", "Boeing"),
        
        # ============ BOEING 757 ============
        (r"757-300.*|757-3\d{2}.*", "757-300", "Boeing"),
        (r"757-200.*|757-2\d{2}.*", "757-200", "Boeing"),
        (r"757.*", "757", "Boeing"),
        
        # ============ BOEING 767 ============
        (r"767-400.*|767-4\d{2}.*", "767-400", "Boeing"),
        (r"767-300.*|767-3\d{2}.*", "767-300", "Boeing"),
        (r"767-200.*|767-2\d{2}.*", "767-200", "Boeing"),
        (r"767.*", "767", "Boeing"),
        
        # ============ BOEING 777 ============
        (r"777-9.*|777X.*9.*", "777-9", "Boeing"),
        (r"777-8.*|777X.*8.*", "777-8", "Boeing"),
        (r"777.*300ER.*|777-3\d{2}ER.*|777F.*", "777-300ER", "Boeing"),
        (r"777-300.*|777-3\d{2}(?!ER).*", "777-300", "Boeing"),
        (r"777.*200ER.*|777-2\d{2}ER.*", "777-200ER", "Boeing"),
        (r"777.*200LR.*|777-2\d{2}LR.*", "777-200LR", "Boeing"),
        (r"777-200.*|777-2\d{2}.*", "777-200", "Boeing"),
        (r"777.*", "777", "Boeing"),
        
        # ============ BOEING 787 ============
        (r"787-10.*|787.*10.*", "787-10", "Boeing"),
        (r"787-9.*|787.*9.*", "787-9", "Boeing"),
        (r"787-8.*|787.*8.*", "787-8", "Boeing"),
        (r"787.*", "787", "Boeing"),
        
        # ============ MCDONNELL DOUGLAS ============
        (r"MD-?11.*", "MD-11", "McDonnell Douglas"),
        (r"MD-?90.*", "MD-90", "McDonnell Douglas"),
        (r"MD-?88.*", "MD-88", "McDonnell Douglas"),
        (r"MD-?87.*", "MD-87", "McDonnell Douglas"),
        (r"MD-?83.*", "MD-83", "McDonnell Douglas"),
        (r"MD-?82.*", "MD-82", "McDonnell Douglas"),
        (r"MD-?81.*", "MD-81", "McDonnell Douglas"),
        (r"MD-?80.*", "MD-80", "McDonnell Douglas"),
        (r"DC-?10.*", "DC-10", "McDonnell Douglas"),
        (r"DC-?9.*", "DC-9", "McDonnell Douglas"),
        (r"DC-?8.*", "DC-8", "McDonnell Douglas"),
        
        # ============ EMBRAER E-JETS ============
        # E2 variants first
        (r"E195-E2.*|E195.*E2.*|ERJ.*195.*E2.*|190-400.*", "E195-E2", "Embraer"),
        (r"E190-E2.*|E190.*E2.*|ERJ.*190.*E2.*|190-300.*", "E190-E2", "Embraer"),
        (r"E175-E2.*|E175.*E2.*|ERJ.*175.*E2.*", "E175-E2", "Embraer"),
        
        # E-Jet E1
        (r"E195.*|ERJ.*195.*|EMB.*195.*", "E195", "Embraer"),
        (r"E190.*|ERJ.*190.*|EMB.*190.*", "E190", "Embraer"),
        (r"E175.*|ERJ.*175.*|EMB.*175.*", "E175", "Embraer"),
        (r"E170.*|ERJ.*170.*|EMB.*170.*", "E170", "Embraer"),
        
        # ERJ regional jets
        (r"ERJ.*145.*|EMB.*145.*|E145.*", "ERJ-145", "Embraer"),
        (r"ERJ.*140.*|EMB.*140.*|E140.*", "ERJ-140", "Embraer"),
        (r"ERJ.*135.*|EMB.*135.*|E135.*", "ERJ-135", "Embraer"),
        
        # ============ BOMBARDIER/CANADAIR ============
        # CRJ Series
        (r"CRJ.*1000.*|CL-?600.*2E25.*", "CRJ-1000", "Bombardier"),
        (r"CRJ.*900.*|CL-?600.*2D24.*", "CRJ-900", "Bombardier"),
        (r"CRJ.*700.*|CL-?600.*2C10.*", "CRJ-700", "Bombardier"),
        (r"CRJ.*550.*", "CRJ-550", "Bombardier"),
        (r"CRJ.*200.*|CL-?600.*2B19.*", "CRJ-200", "Bombardier"),
        (r"CRJ.*100.*", "CRJ-100", "Bombardier"),
        (r"CRJ.*", "CRJ", "Bombardier"),
        
        # Dash 8 / Q Series
        (r"DHC-?8.*400.*|Q400.*|DASH\s*8.*400.*", "Dash 8-400", "De Havilland Canada"),
        (r"DHC-?8.*300.*|Q300.*|DASH\s*8.*300.*", "Dash 8-300", "De Havilland Canada"),
        (r"DHC-?8.*200.*|Q200.*|DASH\s*8.*200.*", "Dash 8-200", "De Havilland Canada"),
        (r"DHC-?8.*100.*|Q100.*|DASH\s*8.*100.*", "Dash 8-100", "De Havilland Canada"),
        (r"DHC-?8.*|DASH\s*8.*", "Dash 8", "De Havilland Canada"),
        
        # ============ ATR ============
        (r"ATR.*72.*", "ATR 72", "ATR"),
        (r"ATR.*42.*", "ATR 42", "ATR"),
        
        # ============ CESSNA JETS ============
        (r"CITATION\s*X\+?.*|C?750.*", "Citation X", "Cessna"),
        (r"CITATION\s*SOVEREIGN.*|C?680.*", "Citation Sovereign", "Cessna"),
        (r"CITATION\s*LATITUDE.*|C?680A.*", "Citation Latitude", "Cessna"),
        (r"CITATION\s*LONGITUDE.*|C?700.*", "Citation Longitude", "Cessna"),
        (r"CITATION\s*EXCEL.*|C?560XL.*", "Citation Excel", "Cessna"),
        (r"CITATION\s*CJ4.*|C?525C.*", "Citation CJ4", "Cessna"),
        (r"CITATION\s*CJ3.*|C?525B.*", "Citation CJ3", "Cessna"),
        (r"CITATION\s*CJ2.*|C?525A.*", "Citation CJ2", "Cessna"),
        (r"CITATION\s*CJ1.*|C?525.*", "Citation CJ1", "Cessna"),
        (r"CITATION\s*MUSTANG.*|C?510.*", "Citation Mustang", "Cessna"),
        (r"CITATION\s*M2.*", "Citation M2", "Cessna"),
        (r"CITATION.*", "Citation", "Cessna"),
        
        # ============ CESSNA PROPS ============
        (r"(?:CESSNA\s*)?172.*|C172.*", "172 Skyhawk", "Cessna"),
        (r"(?:CESSNA\s*)?182.*|C182.*", "182 Skylane", "Cessna"),
        (r"(?:CESSNA\s*)?206.*|C206.*|T206.*|U206.*", "206 Stationair", "Cessna"),
        (r"(?:CESSNA\s*)?208.*|C208.*CARAVAN.*|CARAVAN.*", "208 Caravan", "Cessna"),
        (r"(?:CESSNA\s*)?210.*|C210.*|T210.*", "210 Centurion", "Cessna"),
        (r"(?:CESSNA\s*)?150.*|C150.*", "150", "Cessna"),
        (r"(?:CESSNA\s*)?152.*|C152.*", "152", "Cessna"),
        
        # ============ PIPER ============
        (r"PA-?28.*CHEROKEE.*|CHEROKEE.*", "Cherokee", "Piper"),
        (r"PA-?28.*WARRIOR.*|WARRIOR.*", "Warrior", "Piper"),
        (r"PA-?28.*ARCHER.*|ARCHER.*", "Archer", "Piper"),
        (r"PA-?28.*ARROW.*|ARROW.*", "Arrow", "Piper"),
        (r"PA-?28.*", "PA-28", "Piper"),
        (r"PA-?32.*SARATOGA.*|SARATOGA.*", "Saratoga", "Piper"),
        (r"PA-?32.*LANCE.*|LANCE.*", "Lance", "Piper"),
        (r"PA-?32.*CHEROKEE\s*SIX.*|CHEROKEE\s*SIX.*", "Cherokee Six", "Piper"),
        (r"PA-?32.*", "PA-32", "Piper"),
        (r"PA-?34.*SENECA.*|SENECA.*", "Seneca", "Piper"),
        (r"PA-?34.*", "PA-34", "Piper"),
        (r"PA-?44.*SEMINOLE.*|SEMINOLE.*", "Seminole", "Piper"),
        (r"PA-?46.*MALIBU.*|MALIBU.*|M350.*|M500.*|M600.*", "Malibu", "Piper"),
        (r"PA-?46.*", "PA-46", "Piper"),
        (r"CUB.*|PA-?18.*", "Cub", "Piper"),
        
        # ============ CIRRUS ============
        (r"SR22T?.*G6.*", "SR22 G6", "Cirrus"),
        (r"SR22T.*", "SR22T", "Cirrus"),
        (r"SR22.*", "SR22", "Cirrus"),
        (r"SR20.*", "SR20", "Cirrus"),
        (r"SF50.*|VISION\s*JET.*", "Vision Jet", "Cirrus"),
        
        # ============ PILATUS ============
        # Must come before Beechcraft section to prevent PC-12 matching B350
        (r"PC-?24.*", "PC-24", "Pilatus"),
        (r"PC-?12.*", "PC-12", "Pilatus"),
        (r"PC-?6.*", "PC-6", "Pilatus"),
        
        # ============ BEECHCRAFT ============
        (r"KING\s*AIR\s*350.*|B350.*|BE350.*|C-12.*", "King Air 350", "Beechcraft"),
        (r"KING\s*AIR\s*250.*|B250.*|BE250.*", "King Air 250", "Beechcraft"),
        (r"KING\s*AIR\s*200.*|B200.*|BE200.*", "King Air 200", "Beechcraft"),
        (r"KING\s*AIR\s*90.*|C90.*|BE9[0-9]?.*", "King Air 90", "Beechcraft"),
        (r"KING\s*AIR.*", "King Air", "Beechcraft"),
        (r"BONANZA.*|V35.*|A36.*|G36.*|BE35.*|BE36.*", "Bonanza", "Beechcraft"),
        (r"BARON.*|BE58.*|BE55.*", "Baron", "Beechcraft"),
        (r"PREMIER.*|BE390.*", "Premier", "Beechcraft"),
        
        # ============ GULFSTREAM ============
        (r"G700.*|GVII.*", "G700", "Gulfstream"),
        (r"G650.*|GVI.*", "G650", "Gulfstream"),
        (r"G600.*|G-?VI.*", "G600", "Gulfstream"),
        (r"G550.*|GV.*550.*", "G550", "Gulfstream"),
        (r"G500.*", "G500", "Gulfstream"),
        (r"G450.*|GIV.*450.*", "G450", "Gulfstream"),
        (r"G280.*", "G280", "Gulfstream"),
        (r"GV(?!I).*|G-?V(?!I).*", "G-V", "Gulfstream"),
        (r"GIV.*|G-?IV.*", "G-IV", "Gulfstream"),
        (r"GIII.*|G-?III.*", "G-III", "Gulfstream"),
        
        # ============ DASSAULT FALCON ============
        (r"FALCON\s*10X.*", "Falcon 10X", "Dassault"),
        (r"FALCON\s*8X.*", "Falcon 8X", "Dassault"),
        (r"FALCON\s*7X.*", "Falcon 7X", "Dassault"),
        (r"FALCON\s*900.*", "Falcon 900", "Dassault"),
        (r"FALCON\s*2000.*", "Falcon 2000", "Dassault"),
        (r"FALCON\s*50.*", "Falcon 50", "Dassault"),
        (r"FALCON.*", "Falcon", "Dassault"),
        
        # ============ LEARJET ============
        (r"LEARJET\s*75.*|LJ75.*", "Learjet 75", "Learjet"),
        (r"LEARJET\s*70.*|LJ70.*", "Learjet 70", "Learjet"),
        (r"LEARJET\s*60.*|LJ60.*", "Learjet 60", "Learjet"),
        (r"LEARJET\s*45.*|LJ45.*", "Learjet 45", "Learjet"),
        (r"LEARJET\s*40.*|LJ40.*", "Learjet 40", "Learjet"),
        (r"LEARJET\s*35.*|LJ35.*", "Learjet 35", "Learjet"),
        (r"LEARJET\s*31.*|LJ31.*", "Learjet 31", "Learjet"),
        (r"LEARJET.*", "Learjet", "Learjet"),
        
        # ============ DIAMOND ============
        (r"DA-?62.*", "DA62", "Diamond"),
        (r"DA-?42.*", "DA42", "Diamond"),
        (r"DA-?40.*", "DA40", "Diamond"),
        (r"DA-?20.*", "DA20", "Diamond"),
        
        # ============ HELICOPTERS ============
        # Robinson
        (r"R44.*", "R44", "Robinson"),
        (r"R22.*", "R22", "Robinson"),
        (r"R66.*", "R66", "Robinson"),
        
        # Bell
        (r"BELL\s*206.*|206B.*|JETRANGER.*", "206 JetRanger", "Bell"),
        (r"BELL\s*407.*|407.*", "407", "Bell"),
        (r"BELL\s*412.*|412.*", "412", "Bell"),
        (r"BELL\s*429.*|429.*", "429", "Bell"),
        (r"BELL\s*505.*|505.*", "505", "Bell"),
        (r"BELL\s*525.*|525.*", "525 Relentless", "Bell"),
        
        # Airbus Helicopters / Eurocopter
        (r"H125.*|AS350.*|ECUREUIL.*|ASTAR.*", "H125", "Airbus Helicopters"),
        (r"H130.*|EC130.*", "H130", "Airbus Helicopters"),
        (r"H135.*|EC135.*", "H135", "Airbus Helicopters"),
        (r"H145.*|EC145.*|BK117.*", "H145", "Airbus Helicopters"),
        (r"H160.*", "H160", "Airbus Helicopters"),
        (r"H175.*|EC175.*", "H175", "Airbus Helicopters"),
        (r"H215.*|AS332.*|SUPER\s*PUMA.*", "H215", "Airbus Helicopters"),
        (r"H225.*|EC225.*", "H225", "Airbus Helicopters"),
        
        # Sikorsky
        (r"S-?76.*", "S-76", "Sikorsky"),
        (r"S-?92.*", "S-92", "Sikorsky"),
        (r"S-?70.*|UH-?60.*|BLACK\s*HAWK.*", "S-70/UH-60", "Sikorsky"),
        
        # Leonardo/AgustaWestland
        (r"AW139.*", "AW139", "Leonardo"),
        (r"AW109.*", "AW109", "Leonardo"),
        (r"AW169.*", "AW169", "Leonardo"),
        (r"AW189.*", "AW189", "Leonardo"),
    ]
    
    AIRCRAFT_PATTERNS = [
        (re.compile(pattern, re.IGNORECASE), canonical, mfr)
        for pattern, canonical, mfr in patterns
    ]
    return AIRCRAFT_PATTERNS


def normalize_aircraft_type(manufacturer: Optional[str], aircraft_type: Optional[str], icao_type: Optional[str] = None) -> str:
    """
    Normalize an aircraft type to a canonical display name.
    
    Args:
        manufacturer: Raw manufacturer name from database
        aircraft_type: Raw aircraft type/model from database
        icao_type: ICAO type code (optional, used as fallback)
    
    Returns:
        Normalized display string like "Boeing 737-800" or "Cessna 172 Skyhawk"
    """
    global AIRCRAFT_PATTERNS
    if not AIRCRAFT_PATTERNS:
        AIRCRAFT_PATTERNS = _init_patterns()
    
    # Start with normalized manufacturer
    norm_mfr = normalize_manufacturer(manufacturer)
    
    # Try to match the aircraft type against known patterns
    type_str = aircraft_type or icao_type or ""
    
    for pattern, canonical, mfr_override in AIRCRAFT_PATTERNS:
        if pattern.fullmatch(type_str) or pattern.search(type_str):
            # Use pattern's manufacturer if specified, otherwise use normalized manufacturer
            final_mfr = mfr_override or norm_mfr
            if final_mfr:
                return f"{final_mfr} {canonical}"
            return canonical
    
    # No pattern match - return cleaned up original
    if norm_mfr and type_str:
        # Clean up the type string
        clean_type = re.sub(r'\s+', ' ', type_str).strip()
        return f"{norm_mfr} {clean_type}"
    elif type_str:
        return re.sub(r'\s+', ' ', type_str).strip()
    elif icao_type:
        if norm_mfr:
            return f"{norm_mfr} {icao_type}"
        return icao_type
    
    return "Unknown"


def normalize_type_display(type_display: str) -> str:
    """
    Normalize a pre-formatted type display string (e.g., "BOEING 737-800").
    
    This is useful when the manufacturer and type are already concatenated.
    
    Args:
        type_display: Combined manufacturer + type string
        
    Returns:
        Normalized display string
    """
    if not type_display or type_display == "Unknown":
        return "Unknown"
    
    # Try to split into manufacturer and type
    parts = type_display.split(None, 1)
    if len(parts) == 2:
        mfr, model = parts
        return normalize_aircraft_type(mfr, model)
    else:
        # Single word - treat as type only
        return normalize_aircraft_type(None, type_display)
