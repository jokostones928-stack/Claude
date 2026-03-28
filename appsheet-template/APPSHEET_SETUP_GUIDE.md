# AppSheet Budget Monitoring — Setup Guide

## Overview

Template ini membuat Google Spreadsheet yang siap di-connect ke AppSheet.
AppSheet akan auto-detect struktur table dan generate mobile app.

## Struktur Table

```
Divisions        → Lookup: daftar divisi
Categories       → Lookup: kategori pengeluaran
Employees        → Daftar karyawan + role + approval limit
Budgets          → Budget allocation per divisi per periode
Transactions     → Input pengeluaran harian (MAIN TABLE)
Approvals        → Audit log approval workflow
Dashboard_Data   → Summary formulas (auto-calculated)
```

## Relasi Antar Table (AppSheet akan auto-detect)

```
Divisions ←── Employees.Division
Divisions ←── Budgets.Division
Divisions ←── Transactions.Division
Categories ←── Budgets.Category
Categories ←── Transactions.Category
Employees ←── Transactions.SubmittedBy (via Email)
Transactions ←── Approvals.TransactionID
```

## Step-by-Step Setup

### Step 1: Generate Spreadsheet Template

```bash
# Set environment variables
export GOOGLE_CREDENTIALS="credentials.json"
export GOOGLE_SPREADSHEET_ID="your-spreadsheet-id"

# Install dependencies
pip install gspread google-auth python-dotenv

# Run generator
python appsheet-template/generate_appsheet_template.py
```

### Step 2: Connect ke AppSheet

1. Buka https://www.appsheet.com
2. Login pakai email Google Workspace kantor
3. Klik **"Create"** → **"App"** → **"Start with existing data"**
4. Pilih spreadsheet yang sudah di-generate
5. AppSheet auto-detect semua table

### Step 3: Configure di AppSheet

#### 3a. Set Table Relationships
- Buka **Data** → klik tiap table
- AppSheet biasanya auto-detect, tapi verify:
  - Transactions.Division → Ref ke Divisions.DivisionName
  - Transactions.Category → Ref ke Categories.CategoryName
  - Approvals.TransactionID → Ref ke Transactions.TransactionID

#### 3b. Set Column Types
- `ReceiptPhoto` → Type: **Image** (bisa foto dari HP)
- `Date` → Type: **Date**
- `Amount` / `AllocatedAmount` → Type: **Price**
- `Email` → Type: **Email**
- `Status` → Type: **Enum** (Paid, Pending, Forecast, Cancelled)
- `ApprovalStatus` → Type: **Enum** (Pending, Approved, Rejected)

#### 3c. Enable Approval Workflow
1. **Behavior** → **Actions** → Add Action:
   - Name: "Approve Transaction"
   - Do this: Set column values
   - Set ApprovalStatus = "Approved", ApprovedBy = USEREMAIL()
   - Condition: [ApprovalStatus] = "Pending"

2. **Behavior** → **Actions** → Add Action:
   - Name: "Reject Transaction"
   - Do this: Set column values
   - Set ApprovalStatus = "Rejected"
   - Condition: [ApprovalStatus] = "Pending"

#### 3d. Set User Roles (Security)
- **Security** → **Require sign-in** → ON
- **Domain**: perusahaan.com
- Filter rows:
  - Staff hanya lihat data divisi sendiri
  - Manager lihat semua data divisinya
  - Admin lihat semua

Formula filter (di AppSheet):
```
[Division] = LOOKUP(USEREMAIL(), Employees, Email, Division)
```

#### 3e. Views yang Direkomendasikan
1. **Dashboard** → Chart view dari Dashboard_Data
2. **Input Expense** → Form view dari Transactions
3. **My Expenses** → Deck/Table view filtered by USEREMAIL()
4. **Pending Approvals** → Table view, filter [ApprovalStatus]="Pending"
5. **Budget Overview** → Chart view (budget vs actual)

### Step 4: Setup Notifications (Opsional)

- **Automation** → **Bot** → Add:
  - Event: Transactions table, adds only
  - Condition: [Amount] > 5000000
  - Action: Send email to Manager of that Division
  - Subject: "Expense > 5jt perlu approval: [Description]"

### Step 5: Deploy

1. **Manage** → **Deploy** → klik **"Move app to deployed state"**
2. Share link ke tim
3. Tim install dari browser atau **AppSheet app** di Play Store / App Store

## Gemini AI di AppSheet

Kalau Google Workspace plan support Gemini:
- Bisa generate formula dari deskripsi bahasa Indonesia
- Auto-suggest column types
- Natural language query: "Berapa total pengeluaran Marketing bulan ini?"

## Tips

- Selalu gunakan email kantor (@perusahaan.com), bukan @gmail.com
- Minta IT admin enable AppSheet di Google Workspace Admin Console
- Backup spreadsheet secara berkala (File → Version history)
- Jangan hapus/rename kolom setelah app deployed — bisa break app
