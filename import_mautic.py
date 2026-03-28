#!/usr/bin/env python3
"""
Auto import verified emails to Mautic
Removes duplicates, verifies format, imports to database
"""

import csv
import sys
import re
import mysql.connector
from datetime import datetime
from pathlib import Path

CONFIG_PATH = Path('/root/lead-system/config/settings.json')

def load_config():
    import json
    with open(CONFIG_PATH) as f:
        return json.load(f)

def is_valid_email(email):
    if not email or '@' not in email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def import_csv(csv_path):
    config = load_config()
    conn = mysql.connector.connect(**config['mautic'])
    cur = conn.cursor()
    
    imported = 0
    skipped = 0
    invalid = 0
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get('email', '').strip().lower()
            
            if not is_valid_email(email):
                invalid += 1
                continue
            
            # Check exists
            cur.execute("SELECT id FROM leads WHERE email = %s", (email,))
            if cur.fetchone():
                skipped += 1
                continue
            
            # Insert
            cur.execute("""
                INSERT INTO leads (email, company, website, country, date_added, is_published)
                VALUES (%s, %s, %s, %s, NOW(), 1)
            """, (
                email,
                row.get('website', '').split('//')[-1].split('/')[0].replace('www.', ''),
                row.get('website', ''),
                row.get('country', 'FR')
            ))
            imported += 1
            print(f"IMPORTED: {email}")
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*50}")
    print(f"Imported: {imported} | Skipped (exists): {skipped} | Invalid: {invalid}")
    print(f"{'='*50}")
    
    return imported

if __name__ == '__main__':
    if len(sys.argv) < 2:
        # Auto-find today's CSV
        today = datetime.now().strftime('%Y%m%d')
        csv_path = f"/root/lead-system/outputs/verified/verified_leads_{today}.csv"
    else:
        csv_path = sys.argv[1]
    
    print(f"Importing: {csv_path}")
    import_csv(csv_path)
