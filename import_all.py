#!/usr/bin/env python3
"""Bulk import script for SimplyTrust Bookkeeping."""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import init_db, get_connection
from app.models import Account
from app.importers import import_csv, import_pdf

# Initialize database
init_db()

# Create accounts
conn = get_connection()

# Check if accounts exist, create if not
existing = conn.execute("SELECT name FROM accounts").fetchall()
existing_names = [r['name'] for r in existing]

if 'Amex Business' not in existing_names:
    Account.create('Amex Business', 'credit_card')
    print("Created account: Amex Business")

if 'M&T Business Checking' not in existing_names:
    Account.create('M&T Business Checking', 'checking')
    print("Created account: M&T Business Checking")

conn.close()

# Get account IDs
conn = get_connection()
amex_id = conn.execute("SELECT id FROM accounts WHERE name = 'Amex Business'").fetchone()['id']
mtb_id = conn.execute("SELECT id FROM accounts WHERE name = 'M&T Business Checking'").fetchone()['id']
conn.close()

print(f"\nAmex ID: {amex_id}, M&T ID: {mtb_id}")

# Import Amex CSV
print("\n--- Importing Amex CSV ---")
amex_csv = Path(__file__).parent / 'uploads' / 'amex_activity.csv'
if amex_csv.exists():
    with open(amex_csv, 'rb') as f:
        content = f.read()
    result = import_csv(content, 'amex_activity.csv', amex_id)
    if result['success']:
        print(f"Imported {result['rows_imported']} transactions from Amex")
    else:
        print(f"Error: {result['error']}")
else:
    print("Amex CSV not found")

# Import M&T PDFs
print("\n--- Importing M&T PDFs ---")
mtb_folder = Path(__file__).parent / 'uploads' / 'MTB Statements 2025'
if mtb_folder.exists():
    for pdf_file in sorted(mtb_folder.glob('*.pdf')):
        print(f"Processing {pdf_file.name}...")
        result = import_pdf(str(pdf_file), mtb_id)
        if result['success']:
            print(f"  Imported {result['rows_imported']} transactions")
        else:
            print(f"  Error: {result['error']}")
            if result.get('raw_text'):
                print(f"  Sample text: {result['raw_text'][:200]}...")
else:
    print("M&T folder not found")

# Summary
print("\n--- Summary ---")
conn = get_connection()
total = conn.execute("SELECT COUNT(*) as count FROM transactions").fetchone()['count']
by_account = conn.execute("""
    SELECT a.name, COUNT(t.id) as count, SUM(t.amount) as total
    FROM transactions t
    JOIN accounts a ON t.account_id = a.id
    GROUP BY a.id
""").fetchall()
conn.close()

print(f"Total transactions: {total}")
for row in by_account:
    print(f"  {row['name']}: {row['count']} transactions, ${row['total']:,.2f}")
