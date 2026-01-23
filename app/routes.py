import os
from datetime import datetime
from pathlib import Path

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

from app.models import Transaction, Category, Account
from app.importers import import_csv, import_pdf
from app.database import get_connection

bp = Blueprint('main', __name__)

UPLOAD_FOLDER = Path(__file__).parent.parent / 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'pdf'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/')
def index():
    """Dashboard with summary stats."""
    conn = get_connection()

    # Get date range (default: current year)
    year = request.args.get('year', datetime.now().year, type=int)
    start_date = f'{year}-01-01'
    end_date = f'{year}-12-31'

    # Total income
    income = conn.execute("""
        SELECT COALESCE(SUM(amount), 0) as total
        FROM transactions
        WHERE transaction_type = 'income' AND date BETWEEN ? AND ?
    """, (start_date, end_date)).fetchone()['total']

    # Total expenses
    expenses = conn.execute("""
        SELECT COALESCE(SUM(amount), 0) as total
        FROM transactions
        WHERE transaction_type = 'expense' AND date BETWEEN ? AND ?
    """, (start_date, end_date)).fetchone()['total']

    # Expenses by category
    expenses_by_category = conn.execute("""
        SELECT c.name, COALESCE(SUM(t.amount), 0) as total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.transaction_type = 'expense' AND t.date BETWEEN ? AND ?
        GROUP BY c.id
        ORDER BY total DESC
    """, (start_date, end_date)).fetchall()

    # Uncategorized count (for selected year)
    uncategorized = conn.execute("""
        SELECT COUNT(*) as count FROM transactions
        WHERE category_id IS NULL AND date BETWEEN ? AND ?
    """, (start_date, end_date)).fetchone()['count']

    # Recent transactions
    recent = Transaction.all(limit=10)

    conn.close()

    return render_template('index.html',
                           year=year,
                           income=income,
                           expenses=expenses,
                           net=income - expenses,
                           expenses_by_category=[dict(r) for r in expenses_by_category],
                           uncategorized_count=uncategorized,
                           recent_transactions=recent)


@bp.route('/transactions')
def transactions():
    """List all transactions with filtering."""
    filters = {}

    if request.args.get('start_date'):
        filters['start_date'] = request.args.get('start_date')
    if request.args.get('end_date'):
        filters['end_date'] = request.args.get('end_date')
    if request.args.get('category_id'):
        filters['category_id'] = request.args.get('category_id', type=int)
    if request.args.get('account_id'):
        filters['account_id'] = request.args.get('account_id', type=int)
    if request.args.get('type'):
        filters['transaction_type'] = request.args.get('type')
    if request.args.get('reconciled'):
        filters['reconciled'] = request.args.get('reconciled') == '1'

    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page

    txns = Transaction.all(limit=per_page, offset=offset, filters=filters if filters else None)
    categories = Category.all()
    accounts = Account.all()

    return render_template('transactions.html',
                           transactions=txns,
                           categories=categories,
                           accounts=accounts,
                           filters=filters,
                           page=page)


@bp.route('/transactions/add', methods=['GET', 'POST'])
def add_transaction():
    """Add a new transaction manually."""
    if request.method == 'POST':
        Transaction.create(
            date=request.form['date'],
            description=request.form['description'],
            amount=float(request.form['amount']),
            transaction_type=request.form['transaction_type'],
            category_id=request.form.get('category_id') or None,
            account_id=request.form.get('account_id') or None,
            notes=request.form.get('notes')
        )
        flash('Transaction added successfully', 'success')
        return redirect(url_for('main.transactions'))

    categories = Category.all()
    accounts = Account.all()
    return render_template('transaction_form.html',
                           transaction=None,
                           categories=categories,
                           accounts=accounts)


@bp.route('/transactions/<int:id>/edit', methods=['GET', 'POST'])
def edit_transaction(id):
    """Edit a transaction."""
    txn = Transaction.get(id)
    if not txn:
        flash('Transaction not found', 'error')
        return redirect(url_for('main.transactions'))

    if request.method == 'POST':
        Transaction.update(
            id,
            date=request.form['date'],
            description=request.form['description'],
            amount=float(request.form['amount']),
            transaction_type=request.form['transaction_type'],
            category_id=request.form.get('category_id') or None,
            account_id=request.form.get('account_id') or None,
            notes=request.form.get('notes'),
            reconciled=1 if request.form.get('reconciled') else 0
        )
        flash('Transaction updated', 'success')
        return redirect(url_for('main.transactions'))

    categories = Category.all()
    accounts = Account.all()
    return render_template('transaction_form.html',
                           transaction=txn,
                           categories=categories,
                           accounts=accounts)


@bp.route('/transactions/<int:id>/delete', methods=['POST'])
def delete_transaction(id):
    """Delete a transaction."""
    Transaction.delete(id)
    flash('Transaction deleted', 'success')
    return redirect(url_for('main.transactions'))


@bp.route('/transactions/<int:id>/categorize', methods=['POST'])
def categorize_transaction(id):
    """Quick categorize via AJAX."""
    category_id = request.json.get('category_id')
    Transaction.update(id, category_id=category_id)
    return jsonify({'success': True})


@bp.route('/import', methods=['GET', 'POST'])
def import_file():
    """Import transactions from CSV or PDF."""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            account_id = request.form.get('account_id') or None

            if filename.endswith('.csv'):
                content = file.read()
                result = import_csv(content, filename, account_id)
            else:  # PDF
                filepath = UPLOAD_FOLDER / filename
                file.save(filepath)
                result = import_pdf(filepath, account_id)

            if result['success']:
                flash(f"Successfully imported {result['rows_imported']} transactions", 'success')
            else:
                flash(f"Import failed: {result['error']}", 'error')

            return redirect(url_for('main.transactions'))

        flash('Invalid file type. Please upload CSV or PDF.', 'error')
        return redirect(request.url)

    accounts = Account.all()
    return render_template('import.html', accounts=accounts)


@bp.route('/categorize')
def bulk_categorize():
    """Bulk categorize uncategorized transactions."""
    conn = get_connection()
    uncategorized = conn.execute("""
        SELECT t.*, a.name as account_name
        FROM transactions t
        LEFT JOIN accounts a ON t.account_id = a.id
        WHERE t.category_id IS NULL
        ORDER BY t.date DESC
        LIMIT 100
    """).fetchall()
    conn.close()

    categories = Category.all()
    return render_template('categorize.html',
                           transactions=[dict(r) for r in uncategorized],
                           categories=categories)


@bp.route('/categories')
def categories():
    """Manage categories."""
    cats = Category.all()
    return render_template('categories.html', categories=cats)


@bp.route('/categories/add', methods=['POST'])
def add_category():
    """Add a new category."""
    name = request.form['name']
    cat_type = request.form['type']
    Category.create(name, cat_type)
    flash(f'Category "{name}" created', 'success')
    return redirect(url_for('main.categories'))


@bp.route('/accounts')
def accounts():
    """Manage accounts."""
    accts = Account.all()
    return render_template('accounts.html', accounts=accts)


@bp.route('/accounts/add', methods=['POST'])
def add_account():
    """Add a new account."""
    name = request.form['name']
    account_type = request.form['account_type']
    Account.create(name, account_type)
    flash(f'Account "{name}" created', 'success')
    return redirect(url_for('main.accounts'))


@bp.route('/vendors')
def vendors():
    """View payments by vendor/contractor (for 1099 tracking)."""
    year = request.args.get('year', datetime.now().year, type=int)
    start_date = f'{year}-01-01'
    end_date = f'{year}-12-31'

    conn = get_connection()

    # Phillip Reyland payments
    phillip_payments = conn.execute("""
        SELECT t.date, t.description, t.amount, c.name as category
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.notes LIKE '%Phillip%'
        AND t.date BETWEEN ? AND ?
        ORDER BY t.date
    """, (start_date, end_date)).fetchall()

    phillip_reimbursements = conn.execute("""
        SELECT t.date, t.description, t.amount
        FROM transactions t
        WHERE t.category_id = (SELECT id FROM categories WHERE name = 'Reimbursements - Phillip Reyland')
        AND t.date BETWEEN ? AND ?
        ORDER BY t.date
    """, (start_date, end_date)).fetchall()

    phillip_loan = conn.execute("""
        SELECT COALESCE(SUM(amount), 0) as total
        FROM transactions
        WHERE category_id = (SELECT id FROM categories WHERE name = 'Loans - Shareholder')
        AND (description LIKE '%MOBILE%' OR notes LIKE '%Phillip%')
        AND date BETWEEN ? AND ?
    """, (start_date, end_date)).fetchone()['total']

    # Pratik Shekhar payments
    pratik_payments = conn.execute("""
        SELECT t.date, t.description, t.amount
        FROM transactions t
        WHERE t.notes LIKE '%Pratik%'
        AND t.date BETWEEN ? AND ?
        ORDER BY t.date
    """, (start_date, end_date)).fetchall()

    # Charlie Smith payments
    charlie_payments = conn.execute("""
        SELECT t.date, t.description, t.amount
        FROM transactions t
        WHERE t.notes LIKE '%Charlie%'
        AND t.date BETWEEN ? AND ?
        ORDER BY t.date
    """, (start_date, end_date)).fetchall()

    conn.close()

    # Calculate totals
    phillip_contractor_total = sum(r['amount'] for r in phillip_payments if r['category'] == 'Contractors')
    phillip_reimb_total = sum(r['amount'] for r in phillip_reimbursements)
    pratik_total = sum(r['amount'] for r in pratik_payments)
    charlie_total = sum(r['amount'] for r in charlie_payments)

    return render_template('vendors.html',
                           year=year,
                           phillip_payments=[dict(r) for r in phillip_payments],
                           phillip_reimbursements=[dict(r) for r in phillip_reimbursements],
                           phillip_loan=phillip_loan,
                           phillip_contractor_total=phillip_contractor_total,
                           phillip_reimb_total=phillip_reimb_total,
                           pratik_payments=[dict(r) for r in pratik_payments],
                           pratik_total=pratik_total,
                           charlie_payments=[dict(r) for r in charlie_payments],
                           charlie_total=charlie_total)


@bp.route('/reports')
def reports():
    """Generate financial reports."""
    year = request.args.get('year', datetime.now().year, type=int)
    start_date = f'{year}-01-01'
    end_date = f'{year}-12-31'

    conn = get_connection()

    # Monthly breakdown
    monthly = conn.execute("""
        SELECT
            strftime('%Y-%m', date) as month,
            SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END) as income,
            SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END) as expenses
        FROM transactions
        WHERE date BETWEEN ? AND ?
        GROUP BY strftime('%Y-%m', date)
        ORDER BY month
    """, (start_date, end_date)).fetchall()

    # Category breakdown
    by_category = conn.execute("""
        SELECT
            c.name,
            c.type,
            SUM(t.amount) as total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.date BETWEEN ? AND ?
        GROUP BY c.id
        ORDER BY c.type, total DESC
    """, (start_date, end_date)).fetchall()

    conn.close()

    return render_template('reports.html',
                           year=year,
                           monthly=[dict(r) for r in monthly],
                           by_category=[dict(r) for r in by_category])
