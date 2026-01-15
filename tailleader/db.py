import os
import aiosqlite
from typing import Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  observed_at INTEGER NOT NULL, -- epoch seconds UTC
  hex TEXT NOT NULL,
  registration TEXT, -- callsign or tail number
  rssi REAL,
  lat REAL,
  lon REAL
);

CREATE INDEX IF NOT EXISTS idx_events_observed_at ON events(observed_at);
CREATE INDEX IF NOT EXISTS idx_events_registration ON events(registration);
CREATE INDEX IF NOT EXISTS idx_events_hex ON events(hex);

CREATE TABLE IF NOT EXISTS daily_summary (
  date TEXT NOT NULL, -- YYYY-MM-DD UTC
  registration TEXT,
  count_total INTEGER NOT NULL,
  PRIMARY KEY (date, registration)
);

-- Virtual table for hex -> registration lookups
CREATE TABLE IF NOT EXISTS aircraft_registry (
  hex TEXT PRIMARY KEY,
  registration TEXT NOT NULL,
  aircraft_type TEXT,
  manufacturer TEXT,
  icao_type TEXT,
  normalized_type TEXT,  -- cached normalized display name
  last_updated INTEGER
);
"""

async def ensure_db(db_path: str):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(SCHEMA)
        await db.commit()

async def insert_event(db_path: str, event: dict):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO events (observed_at, hex, registration, rssi, lat, lon) VALUES (?,?,?,?,?,?)",
            (
                event.get("observed_at"),
                event.get("hex"),
                event.get("registration"),
                event.get("rssi"),
                event.get("lat"),
                event.get("lon"),
            ),
        )
        await db.commit()

async def top_registrations(db_path: str, window: str, limit: int = 20):
    async with aiosqlite.connect(db_path) as db:
        # For 30d/all, refresh daily_summary on-the-fly from recent events
        if window in ("30d", "all"):
            await rollup_daily(db_path)
        
        if window == "24h":
            # last 24h: leaderboard of tail numbers only
            import time
            since = int(time.time()) - 24 * 3600
            q = (
                "SELECT ar.registration as tail, COUNT(*) as c "
                "FROM events e "
                "JOIN aircraft_registry ar ON e.hex = ar.hex "
                "WHERE e.observed_at >= ? AND ar.registration IS NOT NULL "
                "GROUP BY ar.registration ORDER BY c DESC LIMIT ?"
            )
            async with db.execute(q, (since, limit)) as cur:
                rows = await cur.fetchall()
                return [dict(registration=tail, count=c) for tail, c in rows]
        elif window == "30d":
            # last 30d: leaderboard of tail numbers only
            import time
            since = int(time.time()) - 30 * 24 * 3600
            q = (
                "SELECT ar.registration as tail, COUNT(*) as c "
                "FROM events e "
                "JOIN aircraft_registry ar ON e.hex = ar.hex "
                "WHERE e.observed_at >= ? AND ar.registration IS NOT NULL "
                "GROUP BY ar.registration ORDER BY c DESC LIMIT ?"
            )
            async with db.execute(q, (since, limit)) as cur:
                return [dict(registration=tail, count=c) for tail, c in await cur.fetchall()]
        else:  # all
            # all-time: leaderboard of tail numbers only
            q = (
                "SELECT ar.registration as tail, COUNT(*) as c "
                "FROM events e "
                "JOIN aircraft_registry ar ON e.hex = ar.hex "
                "WHERE ar.registration IS NOT NULL "
                "GROUP BY ar.registration ORDER BY c DESC LIMIT ?"
            )
            async with db.execute(q, (limit,)) as cur:
                return [dict(registration=tail, count=c) for tail, c in await cur.fetchall()]

async def recent_events(db_path: str, limit: int = 50):
    async with aiosqlite.connect(db_path) as db:
        # Join with aircraft_registry to include tail number as 'tail'
        q = (
            "SELECT e.observed_at, e.hex, COALESCE(ar.registration, e.registration) as tail, e.rssi, e.lat, e.lon "
            "FROM events e LEFT JOIN aircraft_registry ar ON e.hex = ar.hex "
            "ORDER BY e.observed_at DESC LIMIT ?"
        )
        async with db.execute(q, (limit,)) as cur:
            rows = await cur.fetchall()
            return [
                dict(
                    observed_at=r[0], hex=r[1], tail=r[2], rssi=r[3], lat=r[4], lon=r[5]
                )
                for r in rows
            ]

async def rollup_daily(db_path: str):
    async with aiosqlite.connect(db_path) as db:
        # Recompute daily_summary from events
        await db.execute("DELETE FROM daily_summary")
        await db.execute(
            "INSERT INTO daily_summary(date, registration, count_total) "
            "SELECT strftime('%Y-%m-%d', datetime(observed_at, 'unixepoch')), registration, COUNT(*) "
            "FROM events WHERE registration IS NOT NULL "
            "GROUP BY strftime('%Y-%m-%d', datetime(observed_at, 'unixepoch')), registration"
        )
        await db.commit()

async def store_registration(db_path: str, hex_code: str, registration: str, 
                           aircraft_type: Optional[str] = None,
                           manufacturer: Optional[str] = None,
                           icao_type: Optional[str] = None):
    """Store a hex -> registration mapping with optional aircraft type data."""
    import time
    from .aircraft_type_normalizer import normalize_aircraft_type
    
    # Compute normalized type for caching
    normalized = None
    if manufacturer or aircraft_type or icao_type:
        normalized = normalize_aircraft_type(manufacturer, aircraft_type, icao_type)
        if normalized == "Unknown":
            normalized = None
    
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT OR REPLACE INTO aircraft_registry (hex, registration, aircraft_type, manufacturer, icao_type, normalized_type, last_updated) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (hex_code.upper(), registration.upper(), aircraft_type, manufacturer, icao_type, normalized, int(time.time()))
        )
        await db.commit()

async def get_registration_for_hex(db_path: str, hex_code: str) -> Optional[str]:
    """Get registration for a hex code from the registry."""
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT registration FROM aircraft_registry WHERE hex = ?",
            (hex_code.upper(),)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None
