# TailLeader

TailLeader is a lightweight FastAPI app that tracks ADS-B aircraft by tail number (registration) and displays a live leaderboard showing which aircraft visit your airspace most. Built for home ADS-B setups.

- **Backend:** FastAPI + SQLite (async via aiosqlite)
- **Poller:** Reads ADS-B feed every 10s with session-based deduplication (10-min gap)
- **Registry:** Resolves tail numbers via ADSBdb with local hex→registration cache
- **Frontend:** Vanilla JS + Chart.js + Leaflet — no build step required

## Features

- **Live Leaderboard** — Top tail numbers ranked by visit frequency, updated in real-time
- **Live Map** — Leaflet map showing all aircraft currently in range, with your feeder station marked
- **Recent Activity** — A rolling feed of aircraft seen in the last session window
- **Registration Lookup** — Auto-resolves hex codes to readable tail numbers (e.g. `N12345`) via ADSBdb
- **System Stats** — Uptime, database size, feed health at a glance
- **Systemd Integration** — Runs as a service, auto-restarts on crash

## Requirements

TailLeader needs an **ADS-B receiver** feeding aircraft data. It reads from a JSON file written by feeder software like:
- **dump1090** (FlightAware, Mutability, or FA version)
- **readsb** (modern dump1090 fork)
- **tar1090** (includes readsb)
- **ADSBx feeder** (adsbexchange-feed package)

**Default data path**: `/run/adsbexchange-feed/aircraft.json`

Common paths for other feeders:
- FlightAware: `/run/dump1090-fa/aircraft.json`
- Readsb: `/run/readsb/aircraft.json`
- tar1090: `/run/tar1090/aircraft.json`

**Hardware**: Any Raspberry Pi with an RTL-SDR or similar ADS-B receiver.  
**Python**: 3.9+ (works with default Python on Raspberry Pi OS bullseye).

## Quick Start (Raspberry Pi)

```bash
# 1. Clone the repo
git clone https://github.com/fungiblemoose/TailLeader.git
cd TailLeader

# 2. Install dependencies
pip3 install --break-system-packages fastapi uvicorn httpx aiosqlite pydantic python-dotenv PyYAML psutil

# 3. Copy and edit config
cp tailleader/config.example.yaml tailleader/config.yaml
nano tailleader/config.yaml   # Set your feeder path and location

# 4. Run
python3 -m uvicorn tailleader.app:app --host 0.0.0.0 --port 8088
```

Then open `http://<pi-ip>:8088` in your browser.

## Configuration

Config lives at `tailleader/config.yaml` (set `TL_CONFIG` to override the path):

```yaml
feeder:
  mode: file
  path: /run/adsbexchange-feed/aircraft.json   # Path to your aircraft.json

station:
  latitude: 40.7128       # Your latitude (auto-detected from adsbexchange config if blank)
  longitude: -74.0060     # Your longitude
  name: "My ADS-B Station"

admin:
  enable_system_controls: false   # Set true to enable restart API (requires api_key)
  api_key: ""
```

**Note:** `.env` is not auto-loaded by the app. Export environment variables in your shell or systemd unit.

## Auto-Start with Systemd

```bash
sudo cp packaging/tailleader.service /etc/systemd/system/tailleader.service
sudo systemctl daemon-reload
sudo systemctl enable tailleader.service
sudo systemctl start tailleader.service

# Check status
sudo systemctl status tailleader.service
```

The included unit file runs as user `pi`, restarts on crash, and enforces a 500MB memory cap.

## Docker (optional)

```bash
docker build -t tailleader:latest .
docker compose up -d
```

Mount your own config file for real deployments:

```yaml
# docker-compose.yml
volumes:
  - ./config.yaml:/app/config.yaml
environment:
  - TL_CONFIG=/app/config.yaml
```

## Feeder Location

The map shows your station as a neon green house icon. Location is **auto-detected from `/etc/default/adsbexchange`** if you use the ADSBx feeder — no extra setup needed.

To override, set `station.latitude`, `station.longitude`, and `station.name` in `config.yaml`, then restart the service.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/top` | Top tail numbers by visit count |
| `GET /api/recent` | Recently seen aircraft |
| `GET /api/live` | Aircraft currently in range |
| `GET /api/stats` | Database and feed statistics |
| `GET /api/lookup_stats` | Registration lookup cache stats |
| `POST /api/restart_service` | Restart TailLeader (requires admin key) |
| `POST /api/restart_pi` | Reboot the Pi (requires admin key) |

## System Controls (Optional)

Restart/reboot endpoints are disabled by default. To enable:

1. Set `admin.enable_system_controls: true` in config
2. Set a strong `admin.api_key`
3. Pass the key in the `x-tailleader-admin-key` request header

## License

MIT License — see LICENSE file.
