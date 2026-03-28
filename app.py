from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
from datetime import datetime, date

app = Flask(__name__)
DATABASE = "budget.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            icon TEXT DEFAULT '📁'
        );

        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            period TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            transaction_date TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );
    """)

    # Seed default categories if empty
    existing = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    if existing == 0:
        default_categories = [
            ("Operasional", "⚙️"),
            ("Marketing", "📢"),
            ("HR & Payroll", "👥"),
            ("IT & Teknologi", "💻"),
            ("Logistik", "🚚"),
            ("Umum & Admin", "🏢"),
        ]
        conn.executemany(
            "INSERT INTO categories (name, icon) VALUES (?, ?)",
            default_categories,
        )

        # Seed sample budgets for current period
        current_period = date.today().strftime("%Y-%m")
        sample_budgets = [
            (1, 50000000, current_period),
            (2, 30000000, current_period),
            (3, 80000000, current_period),
            (4, 25000000, current_period),
            (5, 15000000, current_period),
            (6, 10000000, current_period),
        ]
        conn.executemany(
            "INSERT INTO budgets (category_id, amount, period) VALUES (?, ?, ?)",
            sample_budgets,
        )

        # Seed sample transactions
        sample_transactions = [
            (1, 12000000, "Sewa kantor bulan ini", f"{current_period}-05"),
            (1, 3500000, "Listrik & air", f"{current_period}-10"),
            (1, 2000000, "Internet & telepon", f"{current_period}-10"),
            (2, 8000000, "Google Ads campaign", f"{current_period}-03"),
            (2, 5000000, "Social media management", f"{current_period}-07"),
            (2, 3000000, "Event sponsorship", f"{current_period}-15"),
            (3, 45000000, "Gaji karyawan", f"{current_period}-25"),
            (3, 5000000, "BPJS & asuransi", f"{current_period}-25"),
            (4, 8000000, "Cloud server", f"{current_period}-01"),
            (4, 4500000, "Software licenses", f"{current_period}-05"),
            (4, 7000000, "Perangkat baru", f"{current_period}-12"),
            (5, 6000000, "Pengiriman barang", f"{current_period}-08"),
            (5, 3500000, "Packaging supplies", f"{current_period}-14"),
            (6, 2000000, "ATK & supplies", f"{current_period}-06"),
            (6, 1500000, "Maintenance gedung", f"{current_period}-18"),
        ]
        conn.executemany(
            "INSERT INTO transactions (category_id, amount, description, transaction_date) VALUES (?, ?, ?, ?)",
            sample_transactions,
        )

    conn.commit()
    conn.close()


def format_rupiah(value):
    """Format number to Indonesian Rupiah."""
    return f"Rp {value:,.0f}".replace(",", ".")


app.jinja_env.filters["rupiah"] = format_rupiah


@app.route("/")
def dashboard():
    conn = get_db()
    current_period = date.today().strftime("%Y-%m")

    # Get budget summary per category
    summary = conn.execute("""
        SELECT
            c.id,
            c.name,
            c.icon,
            COALESCE(b.amount, 0) as budget_amount,
            COALESCE(SUM(t.amount), 0) as spent_amount
        FROM categories c
        LEFT JOIN budgets b ON c.id = b.category_id AND b.period = ?
        LEFT JOIN transactions t ON c.id = t.category_id
            AND strftime('%Y-%m', t.transaction_date) = ?
        GROUP BY c.id
        ORDER BY c.name
    """, (current_period, current_period)).fetchall()

    # Calculate totals
    total_budget = sum(row["budget_amount"] for row in summary)
    total_spent = sum(row["spent_amount"] for row in summary)
    total_remaining = total_budget - total_spent

    # Recent transactions
    recent_transactions = conn.execute("""
        SELECT t.*, c.name as category_name, c.icon
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        ORDER BY t.transaction_date DESC, t.created_at DESC
        LIMIT 10
    """).fetchall()

    # Monthly trend (last 6 months)
    monthly_trend = conn.execute("""
        SELECT
            strftime('%Y-%m', transaction_date) as month,
            SUM(amount) as total
        FROM transactions
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
    """).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        summary=summary,
        total_budget=total_budget,
        total_spent=total_spent,
        total_remaining=total_remaining,
        recent_transactions=recent_transactions,
        monthly_trend=list(reversed(monthly_trend)),
        current_period=current_period,
    )


@app.route("/transactions")
def transactions():
    conn = get_db()
    period = request.args.get("period", date.today().strftime("%Y-%m"))
    category_id = request.args.get("category", "")

    query = """
        SELECT t.*, c.name as category_name, c.icon
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE strftime('%Y-%m', t.transaction_date) = ?
    """
    params = [period]

    if category_id:
        query += " AND t.category_id = ?"
        params.append(category_id)

    query += " ORDER BY t.transaction_date DESC, t.created_at DESC"

    txns = conn.execute(query, params).fetchall()
    categories = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    conn.close()

    return render_template(
        "transactions.html",
        transactions=txns,
        categories=categories,
        current_period=period,
        selected_category=category_id,
    )


@app.route("/transactions/add", methods=["POST"])
def add_transaction():
    conn = get_db()
    conn.execute(
        "INSERT INTO transactions (category_id, amount, description, transaction_date) VALUES (?, ?, ?, ?)",
        (
            request.form["category_id"],
            float(request.form["amount"]),
            request.form["description"],
            request.form["transaction_date"],
        ),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("transactions"))


@app.route("/transactions/delete/<int:txn_id>", methods=["POST"])
def delete_transaction(txn_id):
    conn = get_db()
    conn.execute("DELETE FROM transactions WHERE id = ?", (txn_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("transactions"))


@app.route("/budgets")
def budgets():
    conn = get_db()
    period = request.args.get("period", date.today().strftime("%Y-%m"))

    budget_list = conn.execute("""
        SELECT b.*, c.name as category_name, c.icon
        FROM budgets b
        JOIN categories c ON b.category_id = c.id
        WHERE b.period = ?
        ORDER BY c.name
    """, (period,)).fetchall()

    categories = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    conn.close()

    return render_template(
        "budgets.html",
        budgets=budget_list,
        categories=categories,
        current_period=period,
    )


@app.route("/budgets/set", methods=["POST"])
def set_budget():
    conn = get_db()
    category_id = request.form["category_id"]
    amount = float(request.form["amount"])
    period = request.form["period"]

    existing = conn.execute(
        "SELECT id FROM budgets WHERE category_id = ? AND period = ?",
        (category_id, period),
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE budgets SET amount = ? WHERE id = ?",
            (amount, existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO budgets (category_id, amount, period) VALUES (?, ?, ?)",
            (category_id, amount, period),
        )

    conn.commit()
    conn.close()
    return redirect(url_for("budgets", period=period))


@app.route("/api/summary")
def api_summary():
    conn = get_db()
    period = request.args.get("period", date.today().strftime("%Y-%m"))

    summary = conn.execute("""
        SELECT
            c.name,
            c.icon,
            COALESCE(b.amount, 0) as budget,
            COALESCE(SUM(t.amount), 0) as spent
        FROM categories c
        LEFT JOIN budgets b ON c.id = b.category_id AND b.period = ?
        LEFT JOIN transactions t ON c.id = t.category_id
            AND strftime('%Y-%m', t.transaction_date) = ?
        GROUP BY c.id
        ORDER BY c.name
    """, (period, period)).fetchall()

    conn.close()

    return jsonify([
        {
            "name": row["name"],
            "icon": row["icon"],
            "budget": row["budget"],
            "spent": row["spent"],
            "remaining": row["budget"] - row["spent"],
            "percentage": round((row["spent"] / row["budget"] * 100), 1) if row["budget"] > 0 else 0,
        }
        for row in summary
    ])


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
