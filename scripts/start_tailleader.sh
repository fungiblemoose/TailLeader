#!/usr/bin/env bash
set -euo pipefail
cd /home/pi/tailleader
exec /usr/bin/python3 -m uvicorn tailleader.app:app --host 0.0.0.0 --port 8088
EOF
chmod +x /home/pi/tailleader/scripts/start_tailleader.sh

# Create systemd unit using wrapper
sudo tee /etc/systemd/system/tailleader.service > /dev/null << EOF
[Unit]
Description=TailLeader FastAPI Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/pi/tailleader
ExecStart=/home/pi/tailleader/scripts/start_tailleader.sh
Restart=always
RestartSec=3
MemoryMax=500M
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable tailleader.service
sudo systemctl restart tailleader.service
sleep 2
sudo systemctl is-active tailleader.service && ss -ltnp | grep 8088 || true
sudo journalctl -u tailleader.service -n 50 --no-pager
