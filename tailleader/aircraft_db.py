"""Simple aircraft registration lookup using multiple sources."""
import httpx
import asyncio
from typing import Optional

# In-memory cache: hex -> registration
_cache = {}

async def lookup_registration(hex_code: str) -> Optional[str]:
    """
    Look up aircraft registration by ICAO hex code.
    Uses ADSBExchange database API (free).
    """
    hex_code = hex_code.upper()
    
    # Check cache first
    if hex_code in _cache:
        return _cache[hex_code]
    
    try:
        # Try ADSBExchange aircraft database
        url = f"https://api.adsbdb.com/v0/aircraft/{hex_code.lower()}"
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(url)
            if r.status_code == 200:
                data = r.json()
                # API returns nested structure: response.aircraft.registration
                aircraft = data.get('response', {}).get('aircraft', {})
                reg = aircraft.get('registration') or aircraft.get('regid')
                if reg:
                    reg = reg.strip().upper()
                    _cache[hex_code] = reg
                    print(f"Looked up {hex_code} -> {reg}")
                    return reg
    except Exception as e:
        print(f"Lookup error for {hex_code}: {e}")
    
    # If lookup fails, cache None to avoid repeated lookups
    _cache[hex_code] = None
    return None

def get_cached_registration(hex_code: str) -> Optional[str]:
    """Get registration from cache only (non-async)."""
    return _cache.get(hex_code.upper())

def load_cache_from_db(registry: dict):
    """Preload cache from database registry."""
    global _cache
    _cache.update(registry)
