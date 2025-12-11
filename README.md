# TailLeader

TailLeader is a lightweight FastAPI app for tracking ADS-B aircraft tail numbers (registrations) and displaying a tail-only leaderboard with a live map and system stats.

- Backend: FastAPI + SQLite (async via aiosqlite)
- Poller: Reads ADS-B feed (file or HTTP) every 10s, session-based dedup (10 min gap)
- Registry: Resolves tails via ADSBdb and caches hex→registration
- Frontend: Vanilla JS + Chart.js + Leaflet

## Quick Start (Raspberry Pi)

```bash
# Install dependencies
pip3 install --break-system-packages fastapi uvicorn httpx aiosqlite pydantic python-dotenv PyYAML psutil

# Run
cd /home/pi/tailleader
python3 -m uvicorn tailleader.app:app --host 0.0.0.0 --port 8088
```

Visit: http://<pi-ip>:8088

## Config

- ADS-B feed file default: /run/adsbexchange-feed/aircraft.json
- Port: 8088
- Edit config.yaml or .env (see examples below).

## Systemd (auto-start on boot)

See packaging/tailleader.service for a unit that:
- runs as user pi
- restarts on crash
- enforces MemoryMax=500M

Enable it:
```bash
sudo cp packaging/tailleader.service /etc/systemd/system/tailleader.service
sudo systemctl daemon-reload
sudo systemctl enable tailleader.service
sudo systemctl start tailleader.service
```

## Docker (optional)

```bash
docker build -t tailleader:latest .
docker compose up -d
```

## Packaging Notes
- SQLite DB path: ~/tailleader/data/tailleader.sqlite
- Static assets: tailleader/static/
- APIs: /api/top, /api/recent, /api/live, /api/stats, /api/lookup_stats

## License
Add your preferred license in LICENSE.
