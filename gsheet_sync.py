"""
Google Sheets Integration for Budget Monitoring App

Setup:
1. Buka Google Cloud Console → APIs & Services → Enable "Google Sheets API"
2. Create Service Account → Download JSON key → simpan sebagai "credentials.json"
3. Share spreadsheet ke email service account (xxx@xxx.iam.gserviceaccount.com)
4. Copy Spreadsheet ID dari URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit
5. Set environment variables atau edit config di bawah

Format Spreadsheet yang diharapkan:
- Sheet "Transaksi": Tanggal | Kategori | Deskripsi | Jumlah
- Sheet "Budget":    Kategori | Budget | Periode
"""

import gspread
from google.oauth2.service_account import Credentials
import sqlite3
import os
from datetime import datetime

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS", "credentials.json")
SPREADSHEET_ID = os.environ.get("GOOGLE_SPREADSHEET_ID", "")
DATABASE = "budget.db"


def get_gsheet_client():
    """Authenticate and return gspread client."""
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_or_create_category(conn, name):
    """Get category ID by name, create if not exists."""
    row = conn.execute(
        "SELECT id FROM categories WHERE name = ?", (name,)
    ).fetchone()
    if row:
        return row["id"]
    conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
    conn.commit()
    return conn.execute(
        "SELECT id FROM categories WHERE name = ?", (name,)
    ).fetchone()["id"]


def import_transactions_from_sheet():
    """
    Import transaksi dari Google Sheet ke database.

    Expected Sheet "Transaksi" format:
    Row 1: Header (Tanggal | Kategori | Deskripsi | Jumlah)
    Row 2+: Data
    """
    client = get_gsheet_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    try:
        sheet = spreadsheet.worksheet("Transaksi")
    except gspread.WorksheetNotFound:
        print("Sheet 'Transaksi' tidak ditemukan. Membuat sheet baru...")
        sheet = spreadsheet.add_worksheet(title="Transaksi", rows=100, cols=4)
        sheet.update("A1:D1", [["Tanggal", "Kategori", "Deskripsi", "Jumlah"]])
        return {"imported": 0, "skipped": 0, "errors": []}

    records = sheet.get_all_records()
    conn = get_db()

    imported = 0
    skipped = 0
    errors = []

    for i, row in enumerate(records, start=2):
        try:
            tanggal = str(row.get("Tanggal", "")).strip()
            kategori = str(row.get("Kategori", "")).strip()
            deskripsi = str(row.get("Deskripsi", "")).strip()
            jumlah = row.get("Jumlah", 0)

            if not tanggal or not kategori or not jumlah:
                skipped += 1
                continue

            # Parse amount (handle Rp format)
            if isinstance(jumlah, str):
                jumlah = jumlah.replace("Rp", "").replace(".", "").replace(",", "").strip()
            jumlah = float(jumlah)

            # Parse date (support DD/MM/YYYY or YYYY-MM-DD)
            if "/" in tanggal:
                parsed_date = datetime.strptime(tanggal, "%d/%m/%Y").strftime("%Y-%m-%d")
            else:
                parsed_date = tanggal

            category_id = get_or_create_category(conn, kategori)

            # Check for duplicate (same date, category, amount, description)
            existing = conn.execute(
                """SELECT id FROM transactions
                   WHERE category_id = ? AND amount = ? AND description = ? AND transaction_date = ?""",
                (category_id, jumlah, deskripsi, parsed_date),
            ).fetchone()

            if existing:
                skipped += 1
                continue

            conn.execute(
                "INSERT INTO transactions (category_id, amount, description, transaction_date) VALUES (?, ?, ?, ?)",
                (category_id, jumlah, deskripsi, parsed_date),
            )
            imported += 1

        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")

    conn.commit()
    conn.close()

    return {"imported": imported, "skipped": skipped, "errors": errors}


def import_budgets_from_sheet():
    """
    Import budget dari Google Sheet ke database.

    Expected Sheet "Budget" format:
    Row 1: Header (Kategori | Budget | Periode)
    Row 2+: Data (periode format: YYYY-MM)
    """
    client = get_gsheet_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    try:
        sheet = spreadsheet.worksheet("Budget")
    except gspread.WorksheetNotFound:
        print("Sheet 'Budget' tidak ditemukan. Membuat sheet baru...")
        sheet = spreadsheet.add_worksheet(title="Budget", rows=50, cols=3)
        sheet.update("A1:C1", [["Kategori", "Budget", "Periode"]])
        return {"imported": 0, "skipped": 0, "errors": []}

    records = sheet.get_all_records()
    conn = get_db()

    imported = 0
    skipped = 0
    errors = []

    for i, row in enumerate(records, start=2):
        try:
            kategori = str(row.get("Kategori", "")).strip()
            budget = row.get("Budget", 0)
            periode = str(row.get("Periode", "")).strip()

            if not kategori or not budget or not periode:
                skipped += 1
                continue

            if isinstance(budget, str):
                budget = budget.replace("Rp", "").replace(".", "").replace(",", "").strip()
            budget = float(budget)

            category_id = get_or_create_category(conn, kategori)

            # Upsert budget
            existing = conn.execute(
                "SELECT id FROM budgets WHERE category_id = ? AND period = ?",
                (category_id, periode),
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE budgets SET amount = ? WHERE id = ?",
                    (budget, existing["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO budgets (category_id, amount, period) VALUES (?, ?, ?)",
                    (category_id, budget, periode),
                )
            imported += 1

        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")

    conn.commit()
    conn.close()

    return {"imported": imported, "skipped": skipped, "errors": errors}


def export_transactions_to_sheet():
    """Export semua transaksi dari database ke Google Sheet."""
    client = get_gsheet_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    try:
        sheet = spreadsheet.worksheet("Transaksi")
        sheet.clear()
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title="Transaksi", rows=100, cols=4)

    conn = get_db()
    txns = conn.execute("""
        SELECT t.transaction_date, c.name as category, t.description, t.amount
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        ORDER BY t.transaction_date DESC
    """).fetchall()
    conn.close()

    # Build rows: header + data
    rows = [["Tanggal", "Kategori", "Deskripsi", "Jumlah"]]
    for txn in txns:
        rows.append([
            txn["transaction_date"],
            txn["category"],
            txn["description"],
            txn["amount"],
        ])

    sheet.update(f"A1:D{len(rows)}", rows)

    return {"exported": len(rows) - 1}


def export_summary_to_sheet():
    """Export budget summary (dashboard view) ke Google Sheet."""
    client = get_gsheet_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    try:
        sheet = spreadsheet.worksheet("Summary")
        sheet.clear()
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title="Summary", rows=50, cols=5)

    conn = get_db()
    from datetime import date
    current_period = date.today().strftime("%Y-%m")

    summary = conn.execute("""
        SELECT
            c.name,
            COALESCE(b.amount, 0) as budget,
            COALESCE(SUM(t.amount), 0) as spent
        FROM categories c
        LEFT JOIN budgets b ON c.id = b.category_id AND b.period = ?
        LEFT JOIN transactions t ON c.id = t.category_id
            AND strftime('%Y-%m', t.transaction_date) = ?
        GROUP BY c.id
        ORDER BY c.name
    """, (current_period, current_period)).fetchall()
    conn.close()

    rows = [["Kategori", "Budget", "Terpakai", "Sisa", "Persentase"]]
    for row in summary:
        remaining = row["budget"] - row["spent"]
        pct = round(row["spent"] / row["budget"] * 100, 1) if row["budget"] > 0 else 0
        rows.append([
            row["name"],
            row["budget"],
            row["spent"],
            remaining,
            f"{pct}%",
        ])

    sheet.update(f"A1:E{len(rows)}", rows)

    return {"exported": len(rows) - 1, "period": current_period}


def sync_all():
    """Full sync: import from sheets, then export summary."""
    results = {
        "transactions": import_transactions_from_sheet(),
        "budgets": import_budgets_from_sheet(),
        "summary_export": export_summary_to_sheet(),
    }
    return results
