#!/usr/bin/env python3
"""SimplyTrust Bookkeeping - A simple bookkeeping app for small businesses."""

from flask import Flask
from pathlib import Path

from app.database import init_db
from app.routes import bp

# Create Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'simplytrust-dev-key-change-in-production'

# Ensure upload folder exists
UPLOAD_FOLDER = Path(__file__).parent / 'uploads'
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Register routes
app.register_blueprint(bp)

# Initialize database on startup
init_db()

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("  SimplyTrust Bookkeeping")
    print("  Open http://localhost:8080 in your browser")
    print("=" * 50 + "\n")
    app.run(debug=True, port=8080)
