"""
Google Sheets Integration for Budget Monitoring App
Hub & Spoke Architecture — supports multi-division budget tracking.

Spreadsheet Structure (auto-created by setup_spreadsheet):
- Sheet "Settings":     Division list + Category list (for dropdowns)
- Sheet "Transactions": Date | Division | Category | Description | Amount | Status
- Sheet "Budget":       Division | Category | Budget Allocated | Period
- Sheet "Dashboard":    Auto-calculated summary with formulas

Setup:
1. Google Cloud Console → Enable "Google Sheets API" + "Google Drive API"
2. Create Service Account → Download JSON key → save as "credentials.json"
3. Share spreadsheet to service account email (xxx@xxx.iam.gserviceaccount.com)
4. Set environment variables:
   export GOOGLE_CREDENTIALS="credentials.json"
   export GOOGLE_SPREADSHEET_ID="your-spreadsheet-id"
"""

import gspread
from google.oauth2.service_account import Credentials
import sqlite3
import os
from datetime import datetime, date

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS", "credentials.json")
SPREADSHEET_ID = os.environ.get("GOOGLE_SPREADSHEET_ID", "")
DATABASE = "budget.db"

# Default divisions and categories
DEFAULT_DIVISIONS = ["Sales", "Marketing", "IT", "HR", "Finance", "Operations"]
DEFAULT_CATEGORIES = [
    "Operasional", "Marketing", "HR & Payroll", "IT & Teknologi",
    "Logistik", "Umum & Admin", "Travel", "Software", "Equipment",
]


def get_gsheet_client():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_or_create_category(conn, name):
    row = conn.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]
    conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
    conn.commit()
    return conn.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()["id"]


# ---------------------------------------------------------------------------
# SETUP: Auto-create spreadsheet structure
# ---------------------------------------------------------------------------

def setup_spreadsheet():
    """
    Auto-setup the Google Spreadsheet with proper structure:
    Settings, Transactions, Budget, Dashboard tabs + formulas + dropdowns.
    """
    client = get_gsheet_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    results = {
        "settings": _setup_settings_sheet(spreadsheet),
        "transactions": _setup_transactions_sheet(spreadsheet),
        "budget": _setup_budget_sheet(spreadsheet),
        "dashboard": _setup_dashboard_sheet(spreadsheet),
    }

    return results


def _get_or_create_sheet(spreadsheet, title, rows=200, cols=10):
    try:
        return spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)


def _setup_settings_sheet(spreadsheet):
    sheet = _get_or_create_sheet(spreadsheet, "Settings", rows=30, cols=4)
    sheet.clear()

    # Divisions list
    data = [["Divisions", "", "Categories", ""]]
    max_len = max(len(DEFAULT_DIVISIONS), len(DEFAULT_CATEGORIES))
    for i in range(max_len):
        div = DEFAULT_DIVISIONS[i] if i < len(DEFAULT_DIVISIONS) else ""
        cat = DEFAULT_CATEGORIES[i] if i < len(DEFAULT_CATEGORIES) else ""
        data.append([div, "", cat, ""])

    sheet.update(f"A1:D{len(data)}", data)

    # Bold headers
    sheet.format("A1:D1", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.85, "green": 0.92, "blue": 1.0}})

    return "Settings sheet created with divisions & categories"


def _setup_transactions_sheet(spreadsheet):
    sheet = _get_or_create_sheet(spreadsheet, "Transactions", rows=500, cols=6)

    # Only set headers if sheet is empty
    existing = sheet.get_all_values()
    if not existing or existing[0][0] != "Date":
        sheet.update("A1:F1", [["Date", "Division", "Category", "Description", "Amount", "Status"]])
        sheet.format("A1:F1", {
            "textFormat": {"bold": True},
            "backgroundColor": {"red": 0.2, "green": 0.66, "blue": 0.33},
            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
        })

    # Add data validation (dropdowns) for Division (col B) and Category (col C)
    div_range = f"Settings!$A$2:$A${len(DEFAULT_DIVISIONS) + 1}"
    cat_range = f"Settings!$C$2:$C${len(DEFAULT_CATEGORIES) + 1}"

    # Division dropdown (B2:B500)
    sheet.add_validation(
        "B2:B500",
        gspread.validation.DataValidationRule(
            gspread.validation.BooleanCondition("ONE_OF_RANGE", [div_range]),
            showCustomUi=True,
        ),
    )

    # Category dropdown (C2:C500)
    sheet.add_validation(
        "C2:C500",
        gspread.validation.DataValidationRule(
            gspread.validation.BooleanCondition("ONE_OF_RANGE", [cat_range]),
            showCustomUi=True,
        ),
    )

    # Status dropdown (F2:F500)
    sheet.add_validation(
        "F2:F500",
        gspread.validation.DataValidationRule(
            gspread.validation.BooleanCondition("ONE_OF_LIST", ["Paid", "Pending", "Forecast"]),
            showCustomUi=True,
        ),
    )

    return "Transactions sheet created with dropdowns"


def _setup_budget_sheet(spreadsheet):
    sheet = _get_or_create_sheet(spreadsheet, "Budget", rows=100, cols=4)

    existing = sheet.get_all_values()
    if not existing or existing[0][0] != "Division":
        sheet.update("A1:D1", [["Division", "Category", "Budget Allocated", "Period"]])
        sheet.format("A1:D1", {
            "textFormat": {"bold": True},
            "backgroundColor": {"red": 0.96, "green": 0.8, "blue": 0.26},
        })

    # Division dropdown
    div_range = f"Settings!$A$2:$A${len(DEFAULT_DIVISIONS) + 1}"
    cat_range = f"Settings!$C$2:$C${len(DEFAULT_CATEGORIES) + 1}"

    sheet.add_validation(
        "A2:A100",
        gspread.validation.DataValidationRule(
            gspread.validation.BooleanCondition("ONE_OF_RANGE", [div_range]),
            showCustomUi=True,
        ),
    )
    sheet.add_validation(
        "B2:B100",
        gspread.validation.DataValidationRule(
            gspread.validation.BooleanCondition("ONE_OF_RANGE", [cat_range]),
            showCustomUi=True,
        ),
    )

    return "Budget sheet created with dropdowns"


def _setup_dashboard_sheet(spreadsheet):
    sheet = _get_or_create_sheet(spreadsheet, "Dashboard", rows=50, cols=8)
    sheet.clear()

    current_period = date.today().strftime("%Y-%m")

    # Title
    sheet.update("A1", [[f"Budget Dashboard - {current_period}"]])
    sheet.format("A1", {"textFormat": {"bold": True, "fontSize": 14}})

    # --- Section 1: Budget vs Actual by Division ---
    headers_div = ["Division", "Budget Allocated", "Actual Spent", "Remaining", "% Used", "Status"]
    sheet.update("A3:F3", [headers_div])
    sheet.format("A3:F3", {
        "textFormat": {"bold": True},
        "backgroundColor": {"red": 0.85, "green": 0.92, "blue": 1.0},
    })

    # Fill division rows with SUMIFS formulas
    for i, div in enumerate(DEFAULT_DIVISIONS):
        row = i + 4
        sheet.update(f"A{row}", [[div]])
        # Budget Allocated = SUM from Budget sheet where Division matches
        sheet.update(f"B{row}", [[f'=SUMIFS(Budget!C:C, Budget!A:A, A{row})']])
        # Actual Spent = SUM from Transactions where Division matches & Status="Paid"
        sheet.update(f"C{row}", [[f'=SUMIFS(Transactions!E:E, Transactions!B:B, A{row})']])
        # Remaining
        sheet.update(f"D{row}", [[f"=B{row}-C{row}"]])
        # % Used
        sheet.update(f"E{row}", [[f"=IFERROR(C{row}/B{row}, 0)"]])
        # Status (conditional text)
        sheet.update(f"F{row}", [[f'=IF(E{row}>=0.95,"OVER LIMIT",IF(E{row}>=0.8,"WARNING","OK"))']])

    # Total row
    total_row = len(DEFAULT_DIVISIONS) + 4
    sheet.update(f"A{total_row}", [["TOTAL"]])
    sheet.update(f"B{total_row}", [[f"=SUM(B4:B{total_row-1})"]])
    sheet.update(f"C{total_row}", [[f"=SUM(C4:C{total_row-1})"]])
    sheet.update(f"D{total_row}", [[f"=B{total_row}-C{total_row}"]])
    sheet.update(f"E{total_row}", [[f"=IFERROR(C{total_row}/B{total_row}, 0)"]])
    sheet.format(f"A{total_row}:F{total_row}", {"textFormat": {"bold": True}})

    # Format % column
    sheet.format(f"E3:E{total_row}", {"numberFormat": {"type": "PERCENT", "pattern": "0.0%"}})
    # Format currency columns
    sheet.format(f"B3:D{total_row}", {"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}})

    # --- Section 2: Spending by Category ---
    cat_start = total_row + 2
    sheet.update(f"A{cat_start}", [["Spending by Category"]])
    sheet.format(f"A{cat_start}", {"textFormat": {"bold": True, "fontSize": 12}})

    cat_header_row = cat_start + 1
    sheet.update(f"A{cat_header_row}:B{cat_header_row}", [["Category", "Total Spent"]])
    sheet.format(f"A{cat_header_row}:B{cat_header_row}", {
        "textFormat": {"bold": True},
        "backgroundColor": {"red": 0.96, "green": 0.8, "blue": 0.26},
    })

    for j, cat in enumerate(DEFAULT_CATEGORIES):
        row = cat_header_row + 1 + j
        sheet.update(f"A{row}", [[cat]])
        sheet.update(f"B{row}", [[f'=SUMIFS(Transactions!E:E, Transactions!C:C, A{row})']])

    # Format currency
    cat_end = cat_header_row + len(DEFAULT_CATEGORIES)
    sheet.format(f"B{cat_header_row}:B{cat_end}", {"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}})

    # --- Section 3: Monthly Filter (current month only) ---
    month_start = cat_end + 2
    sheet.update(f"A{month_start}", [["This Month's Transactions (auto-filtered)"]])
    sheet.format(f"A{month_start}", {"textFormat": {"bold": True, "fontSize": 12}})

    filter_row = month_start + 1
    sheet.update(f"A{filter_row}", [[
        f'=FILTER(Transactions!A2:F, MONTH(Transactions!A2:A)=MONTH(TODAY()), YEAR(Transactions!A2:A)=YEAR(TODAY()))'
    ]])

    return "Dashboard sheet created with SUMIFS formulas, % Used, and status indicators"


# ---------------------------------------------------------------------------
# IMPORT: Google Sheets → App Database
# ---------------------------------------------------------------------------

def import_transactions_from_sheet():
    """
    Import from "Transactions" sheet (Hub & Spoke format).
    Columns: Date | Division | Category | Description | Amount | Status
    """
    client = get_gsheet_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    try:
        sheet = spreadsheet.worksheet("Transactions")
    except gspread.WorksheetNotFound:
        return {"imported": 0, "skipped": 0, "errors": ["Sheet 'Transactions' not found. Run Setup first."]}

    records = sheet.get_all_records()
    conn = get_db()

    imported = 0
    skipped = 0
    errors = []

    for i, row in enumerate(records, start=2):
        try:
            tanggal = str(row.get("Date", "")).strip()
            division = str(row.get("Division", "")).strip()
            kategori = str(row.get("Category", "")).strip()
            deskripsi = str(row.get("Description", "")).strip()
            jumlah = row.get("Amount", 0)
            status = str(row.get("Status", "Paid")).strip()

            if not tanggal or not kategori or not jumlah:
                skipped += 1
                continue

            # Parse amount
            if isinstance(jumlah, str):
                jumlah = jumlah.replace("Rp", "").replace(".", "").replace(",", "").strip()
            jumlah = float(jumlah)

            if jumlah <= 0:
                skipped += 1
                continue

            # Parse date (DD/MM/YYYY or YYYY-MM-DD)
            if "/" in tanggal:
                parsed_date = datetime.strptime(tanggal, "%d/%m/%Y").strftime("%Y-%m-%d")
            else:
                parsed_date = tanggal

            # Prepend division to description if present
            full_desc = f"[{division}] {deskripsi}" if division else deskripsi

            category_id = get_or_create_category(conn, kategori)

            # Check duplicate
            existing = conn.execute(
                """SELECT id FROM transactions
                   WHERE category_id = ? AND amount = ? AND description = ? AND transaction_date = ?""",
                (category_id, jumlah, full_desc, parsed_date),
            ).fetchone()

            if existing:
                skipped += 1
                continue

            conn.execute(
                "INSERT INTO transactions (category_id, amount, description, transaction_date) VALUES (?, ?, ?, ?)",
                (category_id, jumlah, full_desc, parsed_date),
            )
            imported += 1

        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")

    conn.commit()
    conn.close()

    return {"imported": imported, "skipped": skipped, "errors": errors}


def import_budgets_from_sheet():
    """
    Import from "Budget" sheet.
    Columns: Division | Category | Budget Allocated | Period
    """
    client = get_gsheet_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    try:
        sheet = spreadsheet.worksheet("Budget")
    except gspread.WorksheetNotFound:
        return {"imported": 0, "skipped": 0, "errors": ["Sheet 'Budget' not found. Run Setup first."]}

    records = sheet.get_all_records()
    conn = get_db()

    imported = 0
    skipped = 0
    errors = []

    for i, row in enumerate(records, start=2):
        try:
            kategori = str(row.get("Category", "")).strip()
            budget = row.get("Budget Allocated", 0)
            periode = str(row.get("Period", "")).strip()

            if not kategori or not budget or not periode:
                skipped += 1
                continue

            if isinstance(budget, str):
                budget = budget.replace("Rp", "").replace(".", "").replace(",", "").strip()
            budget = float(budget)

            category_id = get_or_create_category(conn, kategori)

            existing = conn.execute(
                "SELECT id FROM budgets WHERE category_id = ? AND period = ?",
                (category_id, periode),
            ).fetchone()

            if existing:
                conn.execute("UPDATE budgets SET amount = ? WHERE id = ?", (budget, existing["id"]))
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


# ---------------------------------------------------------------------------
# EXPORT: App Database → Google Sheets
# ---------------------------------------------------------------------------

def export_transactions_to_sheet():
    """Export transactions to the Transactions sheet."""
    client = get_gsheet_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    try:
        sheet = spreadsheet.worksheet("Transactions")
        # Clear data rows but keep header
        sheet.batch_clear(["A2:F500"])
    except gspread.WorksheetNotFound:
        sheet = _get_or_create_sheet(spreadsheet, "Transactions", rows=500, cols=6)
        sheet.update("A1:F1", [["Date", "Division", "Category", "Description", "Amount", "Status"]])

    conn = get_db()
    txns = conn.execute("""
        SELECT t.transaction_date, c.name as category, t.description, t.amount
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        ORDER BY t.transaction_date DESC
    """).fetchall()
    conn.close()

    if not txns:
        return {"exported": 0}

    rows = []
    for txn in txns:
        desc = txn["description"]
        # Extract division from "[Division] description" format
        division = ""
        if desc.startswith("[") and "]" in desc:
            division = desc[1:desc.index("]")]
            desc = desc[desc.index("]") + 2:]

        rows.append([
            txn["transaction_date"],
            division,
            txn["category"],
            desc,
            txn["amount"],
            "Paid",
        ])

    sheet.update(f"A2:F{len(rows) + 1}", rows)

    return {"exported": len(rows)}


def export_summary_to_sheet():
    """Refresh the Dashboard sheet with latest data from the app."""
    client = get_gsheet_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    # The Dashboard uses live SUMIFS formulas from Transactions & Budget sheets,
    # so exporting transactions is enough to refresh the dashboard.
    # But we also update the title with current period.
    try:
        sheet = spreadsheet.worksheet("Dashboard")
        current_period = date.today().strftime("%Y-%m")
        sheet.update("A1", [[f"Budget Dashboard - {current_period}"]])
    except gspread.WorksheetNotFound:
        _setup_dashboard_sheet(spreadsheet)

    return {"exported": 0, "period": date.today().strftime("%Y-%m"), "note": "Dashboard uses live formulas"}


def sync_all():
    """Full sync: import from sheets, then export summary."""
    results = {
        "transactions": import_transactions_from_sheet(),
        "budgets": import_budgets_from_sheet(),
        "summary_export": export_summary_to_sheet(),
    }
    return results
