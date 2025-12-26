import asyncio
import logging
import time
import httpx
import yaml
import os
from typing import Optional
from .db import insert_event
from .aircraft_db import lookup_registration, get_cached_registration

# Global cache: hex -> (registration, last_rssi, last_lat, last_lon, last_track, last_observed_at)
# Used to detect when an aircraft enters/leaves coverage
# Only one event logged per continuous flight session
seen_aircraft = {}

logger = logging.getLogger(__name__)

def normalize_registration(reg: Optional[str]) -> Optional[str]:
    """Extract and normalize flight/callsign from the registration field."""
    if not reg:
        return None
    s = reg.strip().upper()
    # Keep registration as-is (e.g., AAL1945, DAL895)
    # Filter out very short/invalid callsigns
    if len(s) >= 2:
        return s
    return None

async def lookup_and_cache(hex_id: str, db_path: Optional[str] = None):
    """Background task to lookup and cache registration and aircraft type."""
    try:
        result = await lookup_registration(hex_id)
        if result and db_path:
            from .db import store_registration
            reg, aircraft_type, manufacturer, icao_type = result
            await store_registration(db_path, hex_id, reg, aircraft_type, manufacturer, icao_type)
    except Exception:
        pass

async def periodic_lookup_refresher(db_path: str):
    """Periodically retry tail lookups for aircraft without a known registration."""
    while True:
        try:
            # collect hexes without registration
            unknown_hexes = [hex_id for hex_id, (reg, *_rest) in seen_aircraft.items() if not reg]
            # limit per cycle to avoid hammering the API
            for hex_id in unknown_hexes[:20]:
                asyncio.create_task(lookup_and_cache(hex_id, db_path))
        except Exception:
            pass
        await asyncio.sleep(60)

async def poll_once(config: dict, db_path: str):
    global seen_aircraft
    feeder = config.get("feeder", {})
    mode = feeder.get("mode", "http")
    now = int(time.time())

    if mode == "http":
        url = feeder.get("url")
        if not url:
            return
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(url)
                r.raise_for_status()
                data = r.json()
        except Exception:
            return
    elif mode == "file":
        path = feeder.get("path")
        if not path or not os.path.exists(path):
            return
        import json
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except Exception:
            return
    else:
        return

    ac_list = data.get("aircraft") or data.get("ac") or []
    current_hexes = set()

    # Track currently visible aircraft
    for ac in ac_list:
        hex_id = ac.get("hex") or ac.get("icao")
        if not hex_id:
            continue
        
        hex_id = hex_id.upper()
        current_hexes.add(hex_id)
        rssi = ac.get("rssi")
        lat = ac.get("lat")
        lon = ac.get("lon")
        track = ac.get("track") or ac.get("heading")  # Track/heading in degrees
        reg = normalize_registration(ac.get("reg")) or normalize_registration(ac.get("flight"))
        
        # If no registration broadcast, try to look it up
        if not reg:
            cached_reg = get_cached_registration(hex_id)
            if cached_reg:
                reg = cached_reg
            else:
                # Async lookup (don't block the poller)
                asyncio.create_task(lookup_and_cache(hex_id, db_path))
        
        # If we haven't seen this aircraft before, log arrival with registration
        if hex_id not in seen_aircraft:
            event = {
                "observed_at": now,
                "hex": hex_id,
                "registration": reg,
                "rssi": rssi,
                "lat": lat,
                "lon": lon,
            }
            await insert_event(db_path, event)
            seen_aircraft[hex_id] = (reg, rssi, lat, lon, track, now)
        else:
            # Update cache only; no additional inserts during continuous session.
            old_reg, old_rssi, old_lat, old_lon, old_track, old_time = seen_aircraft[hex_id]
            
            # Always update the cache
            seen_aircraft[hex_id] = (reg or old_reg, rssi, lat, lon, track, now)

    # Check for aircraft that disappeared (last seen > 10 minutes ago)
    disappeared = [hex_id for hex_id in list(seen_aircraft.keys()) 
                   if hex_id not in current_hexes and (now - seen_aircraft[hex_id][5]) > 600]
    
    for hex_id in disappeared:
        # Aircraft has left coverage; end session so next reappearance logs a new arrival.
        del seen_aircraft[hex_id]

async def run_poller(config: dict, db_path: str):
    global seen_aircraft
    
    # On startup, load recently seen aircraft from DB to avoid duplicate logging
    import aiosqlite
    try:
        async with aiosqlite.connect(db_path) as db:
            # Load registration cache from database
            from .aircraft_db import load_cache_from_db
            async with db.execute("SELECT hex, registration, aircraft_type, manufacturer, icao_type FROM aircraft_registry") as cur:
                registry = {row[0]: (row[1], row[2], row[3], row[4]) for row in await cur.fetchall()}
                if registry:
                    load_cache_from_db(registry)
                    logger.info(f"Loaded {len(registry)} registrations from cache")
            
            # Get aircraft seen in the last 30 minutes to avoid duplicate arrivals after restarts
            import time
            cutoff = int(time.time()) - 1800
            async with db.execute(
                "SELECT hex, registration, MAX(observed_at) FROM events WHERE observed_at > ? GROUP BY hex",
                (cutoff,)
            ) as cur:
                rows = await cur.fetchall()
                for hex_id, reg, last_seen in rows:
                    # Pre-populate cache with placeholder data (will be updated on next poll)
                    seen_aircraft[hex_id.upper()] = (reg, None, None, None, None, last_seen)
    except Exception as e:
        logger.error(f"Startup cache load error: {e}")
    
    interval = int(config.get("feeder", {}).get("interval_seconds", 10))
    while True:
        try:
            await poll_once(config, db_path)
        except Exception:
            pass
        await asyncio.sleep(interval)

