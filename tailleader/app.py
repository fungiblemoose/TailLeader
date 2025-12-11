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

# Static frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def index():
    return FileResponse(os.path.join(static_dir, "index.html"))
