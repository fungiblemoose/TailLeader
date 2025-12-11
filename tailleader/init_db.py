import asyncio
import os
import yaml
from .db import ensure_db

def load_config() -> dict:
    cfg_path = os.environ.get("TL_CONFIG", os.path.join(os.path.dirname(__file__), "config.yaml"))
    if not os.path.exists(cfg_path):
        cfg_path = os.path.join(os.path.dirname(__file__), "config.example.yaml")
    with open(cfg_path, "r") as f:
        return yaml.safe_load(f)

async def main():
    config = load_config()
    data_dir = config.get("server", {}).get("data_dir", "./data")
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, "tailleader.sqlite")
    await ensure_db(db_path)
    print(f"Initialized DB at {db_path}")

if __name__ == "__main__":
    asyncio.run(main())
