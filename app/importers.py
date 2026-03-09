import csv
import hashlib
import io
from datetime import datetime
from pathlib import Path

import pandas as pd
import pdfplumber
from dateutil import parser as date_parser

from app.database import get_connection


def compute_file_hash(content):
    """Compute hash of file content to prevent duplicate imports."""
    if isinstance(content, str):
        content = content.encode()
    return hashlib.sha256(content).hexdigest()


def check_already_imported(file_hash):
    """Check if a file has already been imported."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM import_history WHERE file_hash = ?", (file_hash,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def record_import(filename, file_hash, rows_imported, conn=None):
    """
    Record a successful import.

    Args:
        filename: Name of imported file
        file_hash: SHA-256 hash of file content
        rows_imported: Number of rows imported
        conn: Optional database connection. If provided, uses it (caller manages transaction).
              If None, creates own connection with auto-commit.
    """
    should_close = conn is None
    if conn is None:
        conn = get_connection()

    try:
        conn.execute(
            "INSERT INTO import_history (filename, file_hash, rows_imported) VALUES (?, ?, ?)",
            (filename, file_hash, rows_imported)
        )
        if should_close:
            conn.commit()
    finally:
        if should_close:
            conn.close()


def parse_amount(amount_str):
    """Parse amount string, handling various formats."""
    if pd.isna(amount_str) or amount_str == '':
        return None

    if isinstance(amount_str, (int, float)):
        return float(amount_str)

    # Remove currency symbols, spaces, and handle parentheses for negatives
    cleaned = str(amount_str).strip()
    cleaned = cleaned.replace('$', '').replace(',', '').replace(' ', '')

    # Handle parentheses notation for negatives: (100.00) -> -100.00
    if cleaned.startswith('(') and cleaned.endswith(')'):
        cleaned = '-' + cleaned[1:-1]

    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_date(date_str):
    """Parse date string in various formats."""
    if pd.isna(date_str) or date_str == '':
        return None

    try:
        return date_parser.parse(str(date_str)).strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return None


def detect_csv_columns(df):
    """Detect which columns contain date, description, and amount."""
    columns = {
        'date': None,
        'description': None,
        'amount': None,
        'debit': None,
        'credit': None,
    }

    col_lower = {col: col.lower().strip() for col in df.columns}

    for col, lower in col_lower.items():
        # Date detection
        if any(x in lower for x in ['date', 'posted', 'transaction date']):
            columns['date'] = col
        # Description detection
        elif any(x in lower for x in ['description', 'memo', 'narrative', 'details', 'payee']):
            columns['description'] = col
        # Amount detection
        elif lower in ['amount', 'value', 'sum']:
            columns['amount'] = col
        elif lower in ['debit', 'withdrawal', 'withdrawals']:
            columns['debit'] = col
        elif lower in ['credit', 'deposit', 'deposits']:
            columns['credit'] = col

    return columns


def import_csv(file_content, filename, account_id=None):
    """Import transactions from a CSV bank statement."""
    file_hash = compute_file_hash(file_content)

    # Check for duplicate import
    existing = check_already_imported(file_hash)
    if existing:
        return {
            'success': False,
            'error': f"This file was already imported on {existing['imported_at']}",
            'rows_imported': 0,
            'rows_skipped': 0
        }

    try:
        # Try to read CSV
        if isinstance(file_content, bytes):
            file_content = file_content.decode('utf-8')

        df = pd.read_csv(io.StringIO(file_content))

        if df.empty:
            return {'success': False, 'error': 'CSV file is empty', 'rows_imported': 0, 'rows_skipped': 0}

        # Detect columns
        cols = detect_csv_columns(df)

        if not cols['date']:
            return {'success': False, 'error': 'Could not detect date column', 'rows_imported': 0, 'rows_skipped': 0}
        if not cols['description']:
            return {'success': False, 'error': 'Could not detect description column', 'rows_imported': 0, 'rows_skipped': 0}
        if not cols['amount'] and not (cols['debit'] or cols['credit']):
            return {'success': False, 'error': 'Could not detect amount column', 'rows_imported': 0, 'rows_skipped': 0}

        transactions = []
        skipped_rows = 0
        skip_reasons = []

        for idx, row in df.iterrows():
            date = parse_date(row[cols['date']])
            if not date:
                skipped_rows += 1
                skip_reasons.append(f"Row {idx + 2}: Invalid date")
                continue

            description = str(row[cols['description']]).strip()
            if not description or description == 'nan':
                skipped_rows += 1
                skip_reasons.append(f"Row {idx + 2}: Empty description")
                continue

            # Determine amount and type
            if cols['amount']:
                amount = parse_amount(row[cols['amount']])
                if amount is None:
                    skipped_rows += 1
                    skip_reasons.append(f"Row {idx + 2}: Invalid amount")
                    continue
                transaction_type = 'income' if amount >= 0 else 'expense'
                amount = abs(amount)
            else:
                debit = parse_amount(row.get(cols['debit'])) if cols['debit'] else None
                credit = parse_amount(row.get(cols['credit'])) if cols['credit'] else None

                if credit and credit > 0:
                    amount = credit
                    transaction_type = 'income'
                elif debit and debit > 0:
                    amount = debit
                    transaction_type = 'expense'
                else:
                    skipped_rows += 1
                    skip_reasons.append(f"Row {idx + 2}: No valid amount in debit/credit columns")
                    continue

            # Round to 2 decimal places for financial accuracy
            amount = round(amount, 2)

            transactions.append({
                'date': date,
                'description': description,
                'amount': amount,
                'transaction_type': transaction_type,
                'account_id': account_id,
                'reference': None
            })

        if not transactions:
            return {
                'success': False,
                'error': 'No valid transactions found in CSV',
                'rows_imported': 0,
                'rows_skipped': skipped_rows,
                'skip_reasons': skip_reasons[:10]  # First 10 reasons
            }

        # Bulk insert and record import (atomic operation)
        from app.models import Transaction
        from app.database import get_connection

        conn = get_connection()
        try:
            conn.execute("BEGIN TRANSACTION")
            # Pass connection to both operations for true atomicity
            Transaction.bulk_create(transactions, conn=conn)
            record_import(filename, file_hash, len(transactions), conn=conn)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

        return {
            'success': True,
            'rows_imported': len(transactions),
            'rows_skipped': skipped_rows,
            'skip_reasons': skip_reasons[:10] if skip_reasons else None,
            'transactions': transactions[:10]  # Return first 10 for preview
        }

    except Exception as e:
        return {'success': False, 'error': str(e), 'rows_imported': 0, 'rows_skipped': 0}


def parse_mtb_statement(text):
    """Parse M&T Bank statement text format.

    Format example:
    04/07/2025 AMEX EPAYMENT ACH PMT A8530 $796.43 8,274.81
    04/29/2025 WEB PMT CHARLIE SMOTH 3,000.00 5,274.81
    """
    import re
    transactions = []

    # Pattern: date, description, amount (credit or debit), balance
    # M&T format: MM/DD/YYYY DESCRIPTION $AMOUNT or AMOUNT BALANCE
    lines = text.split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Match date at start of line
        date_match = re.match(r'^(\d{2}/\d{2}/\d{4})\s+', line)
        if not date_match:
            continue

        date_str = date_match.group(1)
        rest = line[date_match.end():].strip()

        # Skip "BEGINNING BALANCE" lines
        if 'BEGINNING BALANCE' in rest:
            continue

        # Find amounts - look for dollar amounts (with or without $)
        # Pattern: find all money amounts in the line
        amount_pattern = r'\$?([\d,]+\.\d{2})'
        amounts = re.findall(amount_pattern, rest)

        if len(amounts) >= 1:
            # Get description (everything before the first amount)
            desc_match = re.match(r'^(.+?)\s+\$?[\d,]+\.\d{2}', rest)
            if desc_match:
                description = desc_match.group(1).strip()

                # First amount is the transaction amount, last is balance
                amount_str = amounts[0]
                amount = parse_amount(amount_str)

                if amount and amount > 0 and description:
                    # Determine if income or expense based on column position or keywords
                    # In M&T statements, deposits are in one column, withdrawals in another
                    # Check if this looks like a deposit
                    is_deposit = any(kw in description.upper() for kw in [
                        'DEPOSIT', 'CREDIT', 'TRANSFER FROM', 'ACH CREDIT',
                        'PAYROLL', 'DIRECT DEP', 'STRIPE', 'INTEREST'
                    ])

                    # Check for payment/withdrawal keywords
                    is_withdrawal = any(kw in description.upper() for kw in [
                        'PMT', 'PAYMENT', 'CHECK', 'DEBIT', 'WITHDRAWAL',
                        'ACH PMT', 'EPAYMENT', 'WEB PMT', 'BILL PAY'
                    ])

                    if is_deposit and not is_withdrawal:
                        transaction_type = 'income'
                    else:
                        transaction_type = 'expense'

                    transactions.append({
                        'date': parse_date(date_str),
                        'description': description,
                        'amount': amount,
                        'transaction_type': transaction_type,
                    })

    return transactions


def import_pdf(file_path, account_id=None):
    """Extract transactions from a PDF bank statement."""
    try:
        with open(file_path, 'rb') as f:
            file_hash = compute_file_hash(f.read())

        existing = check_already_imported(file_hash)
        if existing:
            return {
                'success': False,
                'error': f"This file was already imported on {existing['imported_at']}",
                'rows_imported': 0,
                'rows_skipped': 0
            }

        transactions = []
        all_text = []

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text.append(text)

        full_text = '\n'.join(all_text)

        # Try M&T Bank format first
        if 'M&T' in full_text or 'MANUFACTURERS AND TRADERS' in full_text:
            transactions = parse_mtb_statement(full_text)
        else:
            # Generic table extraction fallback
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            if row and len(row) >= 3:
                                for i, cell in enumerate(row):
                                    date = parse_date(cell)
                                    if date and i + 2 < len(row):
                                        desc = row[i + 1]
                                        amt = parse_amount(row[i + 2]) or parse_amount(row[-1])
                                        if desc and amt is not None:
                                            transaction_type = 'income' if amt >= 0 else 'expense'
                                            transactions.append({
                                                'date': date,
                                                'description': str(desc).strip(),
                                                'amount': abs(round(amt, 2)),
                                                'transaction_type': transaction_type,
                                            })
                                        break

        if not transactions:
            return {
                'success': False,
                'error': 'Could not extract transactions from PDF. Try exporting as CSV from your bank.',
                'rows_imported': 0,
                'rows_skipped': 0,
                'raw_text': full_text[:2000]
            }

        # Add account_id and round amounts
        for t in transactions:
            t['account_id'] = account_id
            t['amount'] = round(t['amount'], 2)

        # Bulk insert and record import (atomic operation)
        from app.models import Transaction
        from app.database import get_connection

        conn = get_connection()
        try:
            conn.execute("BEGIN TRANSACTION")
            # Pass connection to both operations for true atomicity
            Transaction.bulk_create(transactions, conn=conn)
            record_import(Path(file_path).name, file_hash, len(transactions), conn=conn)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

        return {
            'success': True,
            'rows_imported': len(transactions),
            'rows_skipped': 0,  # PDF extraction doesn't track skipped rows currently
            'transactions': transactions[:10]
        }

    except Exception as e:
        return {'success': False, 'error': str(e), 'rows_imported': 0, 'rows_skipped': 0}
