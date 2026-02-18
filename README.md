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

Create `tailleader/config.yaml` (or set `TL_CONFIG` to your config path), then edit:
```yaml
feeder:
  mode: file
  path: /run/dump1090-fa/aircraft.json
```

**Hardware**: Any Raspberry Pi with an RTL-SDR or similar ADS-B receiver. TailLeader itself is lightweight and works alongside existing feeders.

**Python**: 3.9+ (works with the default Python on Raspberry Pi OS bullseye).

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
- App config is YAML-based: default is `tailleader/config.yaml` (falls back to `tailleader/config.example.yaml`).
- Set `TL_CONFIG=/path/to/config.yaml` to use a different config file.
- `.env` is not auto-loaded by the app; export env vars in your shell/service instead.

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

The included compose file points `TL_CONFIG` at `/app/config.yaml` using `config.yaml.example`.
For real deployments, mount your own config file and set `TL_CONFIG` accordingly.

## System Controls (optional)

The restart/reboot API endpoints are disabled by default.

To enable them safely:
1. Set `admin.enable_system_controls: true` in config (or `TL_ENABLE_SYSTEM_CONTROLS=true`).
2. Set a strong admin key via `admin.api_key` or `TL_ADMIN_KEY`.
3. Send the key in the `x-tailleader-admin-key` request header.

Without these settings, `/api/restart_service` and `/api/restart_pi` will reject requests.

## Packaging Notes
- SQLite DB path: ~/tailleader/data/tailleader.sqlite
- Static assets: tailleader/static/
- APIs: /api/top, /api/recent, /api/live, /api/stats, /api/lookup_stats, /api/system_controls

## License
MIT License - see LICENSE file.

## Feeder Location Marker

The map displays your feeder station location as a small neon green house icon. **The location is automatically detected from your `/etc/default/adsbexchange` configuration**, so no additional setup is needed!

### Custom Location (Optional)

If you want to override the auto-detected location, edit `tailleader/config.yaml`:

```yaml
station:
  latitude: 40.7128      # Your latitude
  longitude: -74.0060    # Your longitude
  name: "My ADS-B Station"
```

Restart the service to apply changes:
```bash
sudo systemctl restart tailleader.service
```
