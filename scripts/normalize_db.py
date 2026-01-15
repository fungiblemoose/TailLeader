#!/usr/bin/env python3
"""
Normalize Aircraft Registry

This script normalizes all aircraft types in the database using the aircraft_type_normalizer module.
It updates the normalized_type column for all aircraft in the registry.

Usage:
    python scripts/normalize_db.py /path/to/tailleader.sqlite [--dry-run]
"""

import sqlite3
import sys
import argparse
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tailleader.aircraft_type_normalizer import normalize_aircraft_type


def main():
    parser = argparse.ArgumentParser(description="Normalize aircraft types in the database.")
    parser.add_argument("db_path", help="Path to the SQLite database file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without making changes")
    parser.add_argument("--limit", type=int, help="Limit number of records to process")
    args = parser.parse_args()

    if not os.path.exists(args.db_path):
        print(f"Error: Database file '{args.db_path}' not found.")
        sys.exit(1)

    print(f"Connecting to database at {args.db_path}...")
    try:
        conn = sqlite3.connect(args.db_path)
        cur = conn.cursor()
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

    # Check if normalized_type column exists, add it if not
    cur.execute("PRAGMA table_info(aircraft_registry)")
    columns = [col[1] for col in cur.fetchall()]
    if "normalized_type" not in columns:
        print("Adding normalized_type column to aircraft_registry table...")
        cur.execute("ALTER TABLE aircraft_registry ADD COLUMN normalized_type TEXT")
        conn.commit()

    print("Fetching aircraft registry...")
    try:
        query = "SELECT hex, manufacturer, aircraft_type, icao_type FROM aircraft_registry"
        if args.limit:
            query += f" LIMIT {args.limit}"
        cur.execute(query)
        rows = cur.fetchall()
    except sqlite3.Error as e:
        print(f"Error reading registry: {e}")
        conn.close()
        sys.exit(1)

    updated_count = 0
    skipped_count = 0
    print(f"Processing {len(rows)} records...")

    for hex_code, manufacturer, aircraft_type, icao_type in rows:
        # Compute normalized type
        normalized = normalize_aircraft_type(manufacturer, aircraft_type, icao_type)
        
        if normalized == "Unknown":
            skipped_count += 1
            continue
        
        if args.dry_run:
            old_display = f"{manufacturer or ''} {aircraft_type or ''}".strip() or icao_type or "None"
            print(f"  {hex_code}: '{old_display}' -> '{normalized}'")
            updated_count += 1
        else:
            try:
                cur.execute(
                    "UPDATE aircraft_registry SET normalized_type = ? WHERE hex = ?",
                    (normalized, hex_code)
                )
                updated_count += 1
            except sqlite3.Error as e:
                print(f"Error updating hex {hex_code}: {e}")

        if updated_count % 500 == 0 and not args.dry_run:
            print(f"  Updated {updated_count} records...", end='\r')

    if not args.dry_run:
        print("Committing changes...")
        conn.commit()
    
    conn.close()
    
    action = "Would update" if args.dry_run else "Updated"
    print(f"\nDone! {action} {updated_count} records. Skipped {skipped_count} unknown types.")


if __name__ == "__main__":
    main()
