from app.database import get_connection
from datetime import datetime


class Category:
    @staticmethod
    def all():
        conn = get_connection()
        rows = conn.execute("SELECT * FROM categories ORDER BY type, name").fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get(category_id):
        conn = get_connection()
        row = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def create(name, cat_type):
        conn = get_connection()
        cursor = conn.execute(
            "INSERT INTO categories (name, type) VALUES (?, ?)",
            (name, cat_type)
        )
        conn.commit()
        category_id = cursor.lastrowid
        conn.close()
        return category_id


class Account:
    @staticmethod
    def all():
        conn = get_connection()
        rows = conn.execute("SELECT * FROM accounts ORDER BY name").fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get(account_id):
        conn = get_connection()
        row = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def create(name, account_type):
        conn = get_connection()
        cursor = conn.execute(
            "INSERT INTO accounts (name, account_type) VALUES (?, ?)",
            (name, account_type)
        )
        conn.commit()
        account_id = cursor.lastrowid
        conn.close()
        return account_id


class Transaction:
    @staticmethod
    def all(limit=100, offset=0, filters=None):
        conn = get_connection()
        query = """
            SELECT t.*, c.name as category_name, a.name as account_name
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN accounts a ON t.account_id = a.id
        """
        params = []

        if filters:
            conditions = []
            if filters.get('start_date'):
                conditions.append("t.date >= ?")
                params.append(filters['start_date'])
            if filters.get('end_date'):
                conditions.append("t.date <= ?")
                params.append(filters['end_date'])
            if filters.get('category_id'):
                conditions.append("t.category_id = ?")
                params.append(filters['category_id'])
            if filters.get('account_id'):
                conditions.append("t.account_id = ?")
                params.append(filters['account_id'])
            if filters.get('transaction_type'):
                conditions.append("t.transaction_type = ?")
                params.append(filters['transaction_type'])
            if filters.get('reconciled') is not None:
                conditions.append("t.reconciled = ?")
                params.append(1 if filters['reconciled'] else 0)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY t.date DESC, t.id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get(transaction_id):
        conn = get_connection()
        row = conn.execute("""
            SELECT t.*, c.name as category_name, a.name as account_name
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN accounts a ON t.account_id = a.id
            WHERE t.id = ?
        """, (transaction_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def create(date, description, amount, transaction_type, category_id=None, account_id=None, reference=None, notes=None):
        conn = get_connection()
        cursor = conn.execute("""
            INSERT INTO transactions (date, description, amount, transaction_type, category_id, account_id, reference, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (date, description, amount, transaction_type, category_id, account_id, reference, notes))
        conn.commit()
        transaction_id = cursor.lastrowid
        conn.close()
        return transaction_id

    @staticmethod
    def update(transaction_id, **kwargs):
        conn = get_connection()
        fields = []
        values = []
        for key, value in kwargs.items():
            if key in ('date', 'description', 'amount', 'transaction_type', 'category_id', 'account_id', 'reference', 'notes', 'reconciled'):
                fields.append(f"{key} = ?")
                values.append(value)

        if fields:
            values.append(transaction_id)
            conn.execute(f"UPDATE transactions SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()
        conn.close()

    @staticmethod
    def delete(transaction_id):
        conn = get_connection()
        conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def bulk_create(transactions):
        conn = get_connection()
        cursor = conn.cursor()
        for t in transactions:
            cursor.execute("""
                INSERT INTO transactions (date, description, amount, transaction_type, category_id, account_id, reference)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (t['date'], t['description'], t['amount'], t['transaction_type'],
                  t.get('category_id'), t.get('account_id'), t.get('reference')))
        conn.commit()
        conn.close()
        return len(transactions)
