import asyncio
import os
import yaml
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from .db import ensure_db, top_registrations, recent_events
from .poller import run_poller
from .poller import periodic_lookup_refresher

def load_config() -> dict:
    cfg_path = os.environ.get("TL_CONFIG", os.path.join(os.path.dirname(__file__), "config.yaml"))
    if not os.path.exists(cfg_path):
        # fall back to example
        cfg_path = os.path.join(os.path.dirname(__file__), "config.example.yaml")
    with open(cfg_path, "r") as f:
        return yaml.safe_load(f)

config = load_config()
data_dir = config.get("server", {}).get("data_dir", "./data")
db_path = os.path.join(data_dir, "tailleader.sqlite")

app = FastAPI()

@app.on_event("startup")
async def startup():
    await ensure_db(db_path)
    # start poller
    asyncio.create_task(run_poller(config, db_path))
    # start periodic tail lookup refresher
    asyncio.create_task(periodic_lookup_refresher(db_path))

@app.get("/api/top")
async def api_top(window: str = Query("24h", pattern="^(24h|30d|all)$"), limit: int = 20):
    return await top_registrations(db_path, window, limit)

@app.get("/api/all_registrations")
async def api_all_registrations(window: str = Query("all", pattern="^(24h|30d|all)$")):
    """Return all registrations for a given time window, ranked by frequency"""
    import aiosqlite
    async with aiosqlite.connect(db_path) as db:
        if window == "24h":
            import time
            since = int(time.time()) - 24 * 3600
            q = (
                "SELECT ar.registration as tail, COUNT(*) as c "
                "FROM events e "
                "JOIN aircraft_registry ar ON e.hex = ar.hex "
                "WHERE e.observed_at >= ? AND ar.registration IS NOT NULL "
                "GROUP BY ar.registration ORDER BY c DESC"
            )
            async with db.execute(q, (since,)) as cur:
                rows = await cur.fetchall()
        elif window == "30d":
            import time
            since = int(time.time()) - 30 * 24 * 3600
            q = (
                "SELECT ar.registration as tail, COUNT(*) as c "
                "FROM events e "
                "JOIN aircraft_registry ar ON e.hex = ar.hex "
                "WHERE e.observed_at >= ? AND ar.registration IS NOT NULL "
                "GROUP BY ar.registration ORDER BY c DESC"
            )
            async with db.execute(q, (since,)) as cur:
                rows = await cur.fetchall()
        else:  # all
            q = (
                "SELECT ar.registration as tail, COUNT(*) as c "
                "FROM events e "
                "JOIN aircraft_registry ar ON e.hex = ar.hex "
                "WHERE ar.registration IS NOT NULL "
                "GROUP BY ar.registration ORDER BY c DESC"
            )
            async with db.execute(q) as cur:
                rows = await cur.fetchall()
        
        return [dict(rank=i+1, registration=tail, count=c) for i, (tail, c) in enumerate(rows)]

@app.get("/api/all_aircraft_types")
async def api_all_aircraft_types(window: str = Query("all", pattern="^(24h|30d|all)$")):
    """Return all aircraft types for a given time window, ranked by frequency"""
    import aiosqlite
    import time
    
    async with aiosqlite.connect(db_path) as db:
        if window == "24h":
            since = int(time.time()) - 24 * 3600
            q = (
                "SELECT "
                "CASE "
                "  WHEN ar.manufacturer IS NOT NULL AND ar.aircraft_type IS NOT NULL "
                "    THEN ar.manufacturer || ' ' || ar.aircraft_type "
                "  WHEN ar.icao_type IS NOT NULL "
                "    THEN ar.icao_type "
                "  ELSE 'Unknown' "
                "END as type_display, "
                "COUNT(*) as c "
                "FROM events e "
                "JOIN aircraft_registry ar ON e.hex = ar.hex "
                "WHERE e.observed_at >= ? "
                "GROUP BY type_display "
                "HAVING type_display != 'Unknown' "
                "ORDER BY c DESC"
            )
            async with db.execute(q, (since,)) as cur:
                rows = await cur.fetchall()
        elif window == "30d":
            since = int(time.time()) - 30 * 24 * 3600
            q = (
                "SELECT "
                "CASE "
                "  WHEN ar.manufacturer IS NOT NULL AND ar.aircraft_type IS NOT NULL "
                "    THEN ar.manufacturer || ' ' || ar.aircraft_type "
                "  WHEN ar.icao_type IS NOT NULL "
                "    THEN ar.icao_type "
                "  ELSE 'Unknown' "
                "END as type_display, "
                "COUNT(*) as c "
                "FROM events e "
                "JOIN aircraft_registry ar ON e.hex = ar.hex "
                "WHERE e.observed_at >= ? "
                "GROUP BY type_display "
                "HAVING type_display != 'Unknown' "
                "ORDER BY c DESC"
            )
            async with db.execute(q, (since,)) as cur:
                rows = await cur.fetchall()
        else:  # all
            q = (
                "SELECT "
                "CASE "
                "  WHEN ar.manufacturer IS NOT NULL AND ar.aircraft_type IS NOT NULL "
                "    THEN ar.manufacturer || ' ' || ar.aircraft_type "
                "  WHEN ar.icao_type IS NOT NULL "
                "    THEN ar.icao_type "
                "  ELSE 'Unknown' "
                "END as type_display, "
                "COUNT(*) as c "
                "FROM events e "
                "JOIN aircraft_registry ar ON e.hex = ar.hex "
                "GROUP BY type_display "
                "HAVING type_display != 'Unknown' "
                "ORDER BY c DESC"
            )
            async with db.execute(q) as cur:
                rows = await cur.fetchall()
        
        return [dict(rank=i+1, aircraft_type=type_display, count=c) for i, (type_display, c) in enumerate(rows)]

@app.get("/api/recent")
async def api_recent(limit: int = 50):
    return await recent_events(db_path, limit)

@app.get("/api/live")
async def api_live():
    """Return currently visible aircraft from the poller cache"""
    from .poller import seen_aircraft
    live = []
    for hex_id, (reg, rssi, lat, lon, track, last_seen) in seen_aircraft.items():
        if lat and lon:  # Only include aircraft with valid positions
            live.append({
                "hex": hex_id,
                "registration": reg,
                "lat": lat,
                "lon": lon,
                "track": track,
                "rssi": rssi,
                "last_seen": last_seen
            })
    return live

@app.get("/api/stats")
async def api_stats():
    """Return system stats (CPU, RAM, temp)"""
    import psutil
    stats = {
        "cpu_percent": round(psutil.cpu_percent(interval=0.1), 1),
        "memory_percent": round(psutil.virtual_memory().percent, 1),
        "memory_used_mb": round(psutil.virtual_memory().used / 1024 / 1024, 0),
        "memory_total_mb": round(psutil.virtual_memory().total / 1024 / 1024, 0),
    }
    
    # Try to get CPU temperature (Raspberry Pi specific)
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp_c = int(f.read().strip()) / 1000
            stats["temp_c"] = round(temp_c, 1)
    except:
        stats["temp_c"] = None
    
    return stats

@app.get("/api/lookup_stats")
async def api_lookup_stats():
    """Return tail lookup stats: known tails in registry and pending seen aircraft without tails."""
    import aiosqlite
    from .poller import seen_aircraft
    known = 0
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT COUNT(*) FROM aircraft_registry") as cur:
            row = await cur.fetchone()
            known = row[0] or 0
    pending = sum(1 for _, (reg, *_rest) in seen_aircraft.items() if not reg)
    return {"known": known, "pending": pending}

@app.get("/api/feed_status")
async def api_feed_status():
    """Check status of connected feed services"""
    import subprocess
    import json
    
    services = {
        "fr24": "fr24feed.service",
        "piaware": "piaware.service",
        "adsbexchange": "adsbexchange-feed.service",
    }
    
    status = {}
    for name, service in services.items():
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True,
                text=True,
                timeout=2
            )
            is_active = result.stdout.strip() == "active"
            status[name] = {"online": is_active}
        except Exception as e:
            status[name] = {"online": False}
    
    return status


@app.get("/api/station")
async def api_station():
    """Return feeder station location"""
    # First try config.yaml
    station = config.get("station") or {}
    lat = station.get("latitude")
    lon = station.get("longitude")
    
    # If not in config, try to read from adsbexchange config
    if not lat or not lon:
        try:
            with open('/etc/default/adsbexchange', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('LATITUDE='):
                        lat = float(line.split('=')[1].strip('"'))
                    elif line.startswith('LONGITUDE='):
                        lon = float(line.split('=')[1].strip('"'))
        except:
            pass
    
    return {
        "latitude": lat,
        "longitude": lon,
        "name": (station.get("name") if station else None) or "ADS-B Station"
    }

@app.post("/api/restart_service")
async def restart_service():
    """Restart the tailleader systemd service"""
    import subprocess
    try:
        subprocess.run(["sudo", "systemctl", "restart", "tailleader.service"], check=True)
        return {"status": "success", "message": "Service restart initiated"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/restart_pi")
async def restart_pi():
    """Restart the Raspberry Pi"""
    import subprocess
    try:
        subprocess.run(["sudo", "shutdown", "-r", "now"], check=True)
        return {"status": "success", "message": "Pi restart initiated"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Static frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def index():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.get("/all-registrations")
async def all_registrations_page():
    return FileResponse(os.path.join(static_dir, "all-registrations.html"))
