import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "bookkeeping.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Categories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Accounts table (bank accounts, credit cards, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            account_type TEXT NOT NULL,
            balance REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Transactions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category_id INTEGER,
            account_id INTEGER,
            transaction_type TEXT NOT NULL CHECK(transaction_type IN ('income', 'expense', 'transfer')),
            reference TEXT,
            notes TEXT,
            reconciled INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    """)

    # Import history to track imported files
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS import_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_hash TEXT NOT NULL UNIQUE,
            rows_imported INTEGER,
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert default categories
    default_categories = [
        ('Software Sales', 'income'),
        ('Consulting', 'income'),
        ('Subscriptions', 'income'),
        ('Other Income', 'income'),
        ('Hosting & Infrastructure', 'expense'),
        ('Software & Tools', 'expense'),
        ('Contractors', 'expense'),
        ('Marketing', 'expense'),
        ('Office Supplies', 'expense'),
        ('Professional Services', 'expense'),
        ('Bank Fees', 'expense'),
        ('Taxes', 'expense'),
        ('Uncategorized', 'expense'),
    ]

    for name, cat_type in default_categories:
        cursor.execute(
            "INSERT OR IGNORE INTO categories (name, type) VALUES (?, ?)",
            (name, cat_type)
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
