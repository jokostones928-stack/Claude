"""
AppSheet Budget Monitoring Template Generator

Script ini generate Google Spreadsheet yang siap di-connect ke AppSheet.
Struktur table sudah di-optimize untuk AppSheet (relational tables, enum columns, dll).

Cara pakai:
1. Set environment variables (GOOGLE_CREDENTIALS, GOOGLE_SPREADSHEET_ID)
2. python generate_appsheet_template.py
3. Buka AppSheet → Create App → "Start with existing data" → pilih spreadsheet
4. Done — AppSheet auto-detect struktur table

Struktur:
- Settings         → Lookup tables (Division, Category, Status)
- Employees        → Daftar karyawan + role approval
- Budgets          → Budget allocation per division per period
- Transactions     → Pengeluaran harian
- Approvals        → Approval workflow log
- Dashboard_Data   → Summary view (auto-calculated)
"""

from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import date

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS", "credentials.json")
SPREADSHEET_ID = os.environ.get("GOOGLE_SPREADSHEET_ID", "")


def get_client():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)


def get_or_create_sheet(spreadsheet, title, rows=200, cols=10):
    try:
        sheet = spreadsheet.worksheet(title)
        sheet.clear()
        return sheet
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)


def setup_all():
    client = get_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    print("Setting up AppSheet template...")
    setup_divisions(spreadsheet)
    setup_categories(spreadsheet)
    setup_employees(spreadsheet)
    setup_budgets(spreadsheet)
    setup_transactions(spreadsheet)
    setup_approvals(spreadsheet)
    setup_dashboard_data(spreadsheet)
    print("Done! Now connect this spreadsheet to AppSheet.")


def setup_divisions(spreadsheet):
    """Lookup table for divisions."""
    sheet = get_or_create_sheet(spreadsheet, "Divisions", rows=20, cols=3)
    data = [
        ["DivisionID", "DivisionName", "Manager"],
        ["DIV001", "Sales", ""],
        ["DIV002", "Marketing", ""],
        ["DIV003", "IT", ""],
        ["DIV004", "HR", ""],
        ["DIV005", "Finance", ""],
        ["DIV006", "Operations", ""],
    ]
    sheet.update(f"A1:C{len(data)}", data)
    sheet.format("A1:C1", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.8}, "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}})
    print("  ✅ Divisions")


def setup_categories(spreadsheet):
    """Lookup table for expense categories."""
    sheet = get_or_create_sheet(spreadsheet, "Categories", rows=20, cols=3)
    data = [
        ["CategoryID", "CategoryName", "Icon"],
        ["CAT001", "Operasional", "⚙️"],
        ["CAT002", "Marketing & Ads", "📢"],
        ["CAT003", "HR & Payroll", "👥"],
        ["CAT004", "IT & Software", "💻"],
        ["CAT005", "Logistik", "🚚"],
        ["CAT006", "Travel & Transport", "✈️"],
        ["CAT007", "Equipment", "🖥️"],
        ["CAT008", "Umum & Admin", "🏢"],
        ["CAT009", "Training & Education", "📚"],
    ]
    sheet.update(f"A1:C{len(data)}", data)
    sheet.format("A1:C1", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.8}, "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}})
    print("  ✅ Categories")


def setup_employees(spreadsheet):
    """Employee table with approval roles."""
    sheet = get_or_create_sheet(spreadsheet, "Employees", rows=50, cols=7)
    data = [
        ["EmployeeID", "Name", "Email", "Division", "Role", "ApprovalLimit", "IsActive"],
        ["EMP001", "Admin Finance", "admin@company.com", "Finance", "Admin", 999999999, "Y"],
        ["EMP002", "", "", "", "Staff", 0, "Y"],
        ["EMP003", "", "", "", "Manager", 50000000, "Y"],
    ]
    sheet.update(f"A1:G{len(data)}", data)
    sheet.format("A1:G1", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.96, "green": 0.8, "blue": 0.26}})
    print("  ✅ Employees")


def setup_budgets(spreadsheet):
    """Budget allocation per division per period."""
    sheet = get_or_create_sheet(spreadsheet, "Budgets", rows=100, cols=7)

    current_period = date.today().strftime("%Y-%m")

    data = [
        ["BudgetID", "Division", "Category", "AllocatedAmount", "Period", "CreatedBy", "CreatedDate"],
        ["BUD001", "Sales", "Marketing & Ads", 30000000, current_period, "admin@company.com", date.today().isoformat()],
        ["BUD002", "Sales", "Travel & Transport", 15000000, current_period, "admin@company.com", date.today().isoformat()],
        ["BUD003", "Marketing", "Marketing & Ads", 50000000, current_period, "admin@company.com", date.today().isoformat()],
        ["BUD004", "IT", "IT & Software", 25000000, current_period, "admin@company.com", date.today().isoformat()],
        ["BUD005", "IT", "Equipment", 20000000, current_period, "admin@company.com", date.today().isoformat()],
        ["BUD006", "HR", "HR & Payroll", 80000000, current_period, "admin@company.com", date.today().isoformat()],
        ["BUD007", "Operations", "Operasional", 40000000, current_period, "admin@company.com", date.today().isoformat()],
        ["BUD008", "Operations", "Logistik", 15000000, current_period, "admin@company.com", date.today().isoformat()],
        ["BUD009", "Finance", "Umum & Admin", 10000000, current_period, "admin@company.com", date.today().isoformat()],
    ]
    sheet.update(f"A1:G{len(data)}", data)
    sheet.format("A1:G1", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.13, "green": 0.55, "blue": 0.13}, "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}})
    sheet.format(f"D2:D{len(data)}", {"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}})
    print("  ✅ Budgets")


def setup_transactions(spreadsheet):
    """Main transaction table — where teams input expenses."""
    sheet = get_or_create_sheet(spreadsheet, "Transactions", rows=500, cols=12)

    current_period = date.today().strftime("%Y-%m")
    today = date.today().isoformat()

    data = [
        [
            "TransactionID", "Date", "Division", "Category",
            "Description", "Amount", "Status", "SubmittedBy",
            "ReceiptPhoto", "ApprovalStatus", "ApprovedBy", "Notes"
        ],
        ["TXN001", today, "Marketing", "Marketing & Ads", "Google Ads Q1 Campaign", 8000000, "Paid", "staff@company.com", "", "Approved", "manager@company.com", ""],
        ["TXN002", today, "IT", "IT & Software", "AWS Cloud hosting Maret", 5000000, "Paid", "staff@company.com", "", "Approved", "manager@company.com", ""],
        ["TXN003", today, "IT", "Equipment", "Monitor baru untuk dev team", 7500000, "Pending", "staff@company.com", "", "Pending", "", "Menunggu approval manager"],
        ["TXN004", today, "Sales", "Travel & Transport", "Tiket Jakarta-Surabaya client visit", 2500000, "Paid", "staff@company.com", "", "Approved", "manager@company.com", ""],
        ["TXN005", today, "HR", "HR & Payroll", "Gaji karyawan Maret", 45000000, "Paid", "admin@company.com", "", "Approved", "admin@company.com", ""],
        ["TXN006", today, "Operations", "Operasional", "Sewa kantor Maret", 12000000, "Paid", "admin@company.com", "", "Approved", "admin@company.com", ""],
    ]
    sheet.update(f"A1:L{len(data)}", data)
    sheet.format("A1:L1", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.85, "green": 0.2, "blue": 0.2}, "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}})
    sheet.format(f"F2:F{len(data)}", {"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}})

    # Add data validation for Status
    sheet.add_validation(
        "G2:G500",
        gspread.validation.DataValidationRule(
            gspread.validation.BooleanCondition("ONE_OF_LIST", ["Paid", "Pending", "Forecast", "Cancelled"]),
            showCustomUi=True,
        ),
    )
    # ApprovalStatus
    sheet.add_validation(
        "J2:J500",
        gspread.validation.DataValidationRule(
            gspread.validation.BooleanCondition("ONE_OF_LIST", ["Pending", "Approved", "Rejected"]),
            showCustomUi=True,
        ),
    )
    print("  ✅ Transactions")


def setup_approvals(spreadsheet):
    """Approval workflow audit log."""
    sheet = get_or_create_sheet(spreadsheet, "Approvals", rows=200, cols=8)

    today = date.today().isoformat()
    data = [
        ["ApprovalID", "TransactionID", "Action", "ActionBy", "ActionDate", "PreviousStatus", "NewStatus", "Comments"],
        ["APR001", "TXN001", "Approved", "manager@company.com", today, "Pending", "Approved", "OK, sesuai budget"],
        ["APR002", "TXN002", "Approved", "manager@company.com", today, "Pending", "Approved", ""],
    ]
    sheet.update(f"A1:H{len(data)}", data)
    sheet.format("A1:H1", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.6, "green": 0.4, "blue": 0.8}, "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}})
    print("  ✅ Approvals")


def setup_dashboard_data(spreadsheet):
    """Dashboard summary with SUMIFS formulas."""
    sheet = get_or_create_sheet(spreadsheet, "Dashboard_Data", rows=50, cols=8)

    # Budget vs Actual by Division
    divisions = ["Sales", "Marketing", "IT", "HR", "Finance", "Operations"]

    header = ["Division", "Budget Allocated", "Actual Spent", "Remaining", "% Used", "Status", "Pending Amount", "Forecast Amount"]
    rows = [header]

    for i, div in enumerate(divisions):
        r = i + 2
        rows.append([
            div,
            f'=SUMIFS(Budgets!D:D, Budgets!B:B, A{r})',
            f'=SUMIFS(Transactions!F:F, Transactions!C:C, A{r}, Transactions!G:G, "Paid")',
            f'=B{r}-C{r}',
            f'=IFERROR(C{r}/B{r}, 0)',
            f'=IF(E{r}>=0.95, "🔴 OVER LIMIT", IF(E{r}>=0.8, "🟡 WARNING", "🟢 OK"))',
            f'=SUMIFS(Transactions!F:F, Transactions!C:C, A{r}, Transactions!G:G, "Pending")',
            f'=SUMIFS(Transactions!F:F, Transactions!C:C, A{r}, Transactions!G:G, "Forecast")',
        ])

    # Total row
    t = len(divisions) + 2
    rows.append([
        "TOTAL",
        f'=SUM(B2:B{t-1})',
        f'=SUM(C2:C{t-1})',
        f'=B{t}-C{t}',
        f'=IFERROR(C{t}/B{t}, 0)',
        f'=IF(E{t}>=0.95, "🔴 OVER", IF(E{t}>=0.8, "🟡 WARN", "🟢 OK"))',
        f'=SUM(G2:G{t-1})',
        f'=SUM(H2:H{t-1})',
    ])

    sheet.update(f"A1:H{len(rows)}", rows)
    sheet.format("A1:H1", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.15, "green": 0.15, "blue": 0.3}, "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}})
    sheet.format(f"A{t}:H{t}", {"textFormat": {"bold": True}})
    sheet.format(f"E1:E{t}", {"numberFormat": {"type": "PERCENT", "pattern": "0.0%"}})
    sheet.format(f"B1:D{t}", {"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}})
    sheet.format(f"G1:H{t}", {"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}})

    # Section 2: Category Breakdown (below divisions)
    cat_start = t + 2
    categories = ["Operasional", "Marketing & Ads", "HR & Payroll", "IT & Software",
                   "Logistik", "Travel & Transport", "Equipment", "Umum & Admin", "Training & Education"]

    cat_header = ["Category", "Budget", "Spent", "Remaining", "% Used"]
    cat_rows = [cat_header]
    for j, cat in enumerate(categories):
        r = cat_start + 1 + j
        cat_rows.append([
            cat,
            f'=SUMIFS(Budgets!D:D, Budgets!C:C, A{r})',
            f'=SUMIFS(Transactions!F:F, Transactions!D:D, A{r}, Transactions!G:G, "Paid")',
            f'=B{r}-C{r}',
            f'=IFERROR(C{r}/B{r}, 0)',
        ])

    sheet.update(f"A{cat_start}:E{cat_start + len(cat_rows) - 1}", cat_rows)
    sheet.format(f"A{cat_start}:E{cat_start}", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.96, "green": 0.8, "blue": 0.26}})
    cat_end = cat_start + len(cat_rows) - 1
    sheet.format(f"E{cat_start}:E{cat_end}", {"numberFormat": {"type": "PERCENT", "pattern": "0.0%"}})
    sheet.format(f"B{cat_start}:D{cat_end}", {"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}})

    print("  ✅ Dashboard_Data")


if __name__ == "__main__":
    if not SPREADSHEET_ID:
        print("ERROR: Set GOOGLE_SPREADSHEET_ID environment variable first!")
        print("  export GOOGLE_SPREADSHEET_ID='your-spreadsheet-id'")
        exit(1)
    setup_all()
