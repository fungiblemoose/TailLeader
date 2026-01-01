import sqlite3
import re
import sys
import argparse
import os

def normalize_text(text):
    """Normalize text by converting to uppercase, replacing punctuation with spaces, and stripping whitespace."""
    if not text:
        return None
    # Convert to uppercase
    text = text.upper()
    # Replace punctuation (except spaces) with spaces
    text = re.sub(r'[^\w\s]', ' ', text)
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def main():
    parser = argparse.ArgumentParser(description="Normalize aircraft registry data in the database.")
    parser.add_argument("db_path", help="Path to the SQLite database file")
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

    print("Fetching aircraft registry...")
    try:
        # Check if table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='aircraft_registry'")
        if not cur.fetchone():
            print("Error: 'aircraft_registry' table not found in database.")
            conn.close()
            sys.exit(1)

        cur.execute("SELECT hex, aircraft_type, manufacturer, icao_type FROM aircraft_registry")
        rows = cur.fetchall()
    except sqlite3.Error as e:
        print(f"Error reading registry: {e}")
        conn.close()
        sys.exit(1)

    updated_count = 0
    print(f"Scanning {len(rows)} records...")

    for row in rows:
        hex_code, ac_type, manufacturer, icao_type = row
        
        new_ac_type = normalize_text(ac_type)
        new_manufacturer = normalize_text(manufacturer)
        new_icao_type = normalize_text(icao_type)

        # Check if update is needed (handling None values)
        needs_update = False
        if (ac_type or "") != (new_ac_type or ""): needs_update = True
        if (manufacturer or "") != (new_manufacturer or ""): needs_update = True
        if (icao_type or "") != (new_icao_type or ""): needs_update = True

        if needs_update:
            try:
                cur.execute(
                    "UPDATE aircraft_registry SET aircraft_type = ?, manufacturer = ?, icao_type = ? WHERE hex = ?",
                    (new_ac_type, new_manufacturer, new_icao_type, hex_code)
                )
                updated_count += 1
            except sqlite3.Error as e:
                print(f"Error updating hex {hex_code}: {e}")

            if updated_count % 100 == 0:
                print(f"Updated {updated_count} records...", end='\r')

    print(f"Committing changes...")
    conn.commit()
    conn.close()
    print(f"\nDone! Normalized {updated_count} records.")

if __name__ == "__main__":
    main()
