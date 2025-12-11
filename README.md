# TailLeader

TailLeader is a lightweight FastAPI app for tracking ADS-B aircraft tail numbers (registrations) and displaying a tail-only leaderboard with a live map and system stats.

- Backend: FastAPI + SQLite (async via aiosqlite)
- Poller: Reads ADS-B feed (file or HTTP) every 10s, session-based dedup (10 min gap)
- Registry: Resolves tails via ADSBdb and caches hex→registration
- Frontend: Vanilla JS + Chart.js + Leaflet

## Requirements

TailLeader requires an **ADS-B receiver** feeding aircraft data. It reads from a JSON file written by feeder software like:
- **dump1090** (FlightAware, Mutability, or FA version)
- **readsb** (modern dump1090 fork)
- **tar1090** (includes readsb)
- **ADSBx feeder** (adsbexchange-feed package)

**Default data path**: `/run/adsbexchange-feed/aircraft.json`

Common paths for other feeders:
- FlightAware: `/run/dump1090-fa/aircraft.json`
- Readsb: `/run/readsb/aircraft.json`
- tar1090: `/run/tar1090/aircraft.json`

Edit `config.yaml` or `.env` to change the path:
```yaml
feeder:
  mode: file
  path: /run/dump1090-fa/aircraft.json
```

**Hardware**: Any Raspberry Pi with an RTL-SDR or similar ADS-B receiver. TailLeader itself is lightweight and works alongside existing feeders.

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
MIT License - see LICENSE file.

## Feeder Location Marker

The map displays your feeder station location as a small neon green house icon. **The location is automatically detected from your `/etc/default/adsbexchange` configuration**, so no additional setup is needed!

### Custom Location (Optional)

If you want to override the auto-detected location, edit `config.yaml`:

```yaml
station:
  latitude: 40.7128      # Your latitude
  longitude: -74.0060    # Your longitude
  name: "My ADS-B Station"
```

The marker shows:
- **Neon green glow** for maximum visibility  
- **House icon** (16x16) to distinguish it from aircraft markers
- **Popup label** when clicked

Restart the service to apply changes:
```bash
sudo systemctl restart tailleader.service
```
