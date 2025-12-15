"""Simple aircraft registration lookup using multiple sources."""
import httpx
import asyncio
from typing import Optional, Dict, Tuple

# In-memory cache: hex -> (registration, aircraft_type, manufacturer, icao_type)
_cache = {}

async def lookup_registration(hex_code: str) -> Optional[Tuple[str, Optional[str], Optional[str], Optional[str]]]:
    """
    Look up aircraft registration and type by ICAO hex code.
    Uses ADSBdb database API (free).
    Returns: (registration, aircraft_type, manufacturer, icao_type) or None
    """
    hex_code = hex_code.upper()
    
    # Check cache first
    if hex_code in _cache:
        return _cache[hex_code]
    
    try:
        # Try ADSBdb aircraft database
        url = f"https://api.adsbdb.com/v0/aircraft/{hex_code.lower()}"
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(url)
            if r.status_code == 200:
                data = r.json()
                # API returns nested structure: response.aircraft
                aircraft = data.get('response', {}).get('aircraft', {})
                reg = aircraft.get('registration') or aircraft.get('regid')
                if reg:
                    reg = reg.strip().upper()
                    # Extract aircraft type information
                    aircraft_type = aircraft.get('type')
                    manufacturer = aircraft.get('manufacturer')
                    icao_type = aircraft.get('icao_type')
                    
                    result = (reg, aircraft_type, manufacturer, icao_type)
                    _cache[hex_code] = result
                    print(f"Looked up {hex_code} -> {reg} ({manufacturer} {aircraft_type})")
                    return result
    except Exception as e:
        print(f"Lookup error for {hex_code}: {e}")
    
    # If lookup fails, cache None to avoid repeated lookups
    _cache[hex_code] = None
    return None

def get_cached_registration(hex_code: str) -> Optional[str]:
    """Get registration from cache only (non-async). Returns just the registration string."""
    cached = _cache.get(hex_code.upper())
    if cached and isinstance(cached, tuple):
        return cached[0]
    return cached

def get_cached_aircraft_data(hex_code: str) -> Optional[Tuple[str, Optional[str], Optional[str], Optional[str]]]:
    """Get full aircraft data from cache only (non-async)."""
    return _cache.get(hex_code.upper())

def load_cache_from_db(registry: dict):
    """Preload cache from database registry.
    registry should be dict of hex -> (registration, aircraft_type, manufacturer, icao_type)
    """
    global _cache
    _cache.update(registry)
