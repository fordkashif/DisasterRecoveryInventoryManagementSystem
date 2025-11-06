import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, case
import pandas as pd

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")
db_url = os.environ.get("DATABASE_URL", "sqlite:///db.sqlite3")
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ---------- Models ----------
class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)  # e.g., Parish depot / shelter

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(64), unique=True, nullable=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    category = db.Column(db.String(120), nullable=True, index=True)       # e.g., Food, Water, Hygiene, Medical
    unit = db.Column(db.String(32), nullable=False, default="unit")        # e.g., pcs, kg, L
    min_qty = db.Column(db.Integer, nullable=False, default=0)             # threshold for "low stock"
    notes = db.Column(db.Text, nullable=True)

class Donor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=False)
    contact = db.Column(db.String(200), nullable=True)

class Beneficiary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    contact = db.Column(db.String(200), nullable=True)
    parish = db.Column(db.String(120), nullable=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("item.id"), nullable=False)
    ttype = db.Column(db.String(8), nullable=False)  # "IN" or "OUT"
    qty = db.Column(db.Integer, nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey("location.id"), nullable=True)
    donor_id = db.Column(db.Integer, db.ForeignKey("donor.id"), nullable=True)
    beneficiary_id = db.Column(db.Integer, db.ForeignKey("beneficiary.id"), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    item = db.relationship("Item")
    location = db.relationship("Location")
    donor = db.relationship("Donor")
    beneficiary = db.relationship("Beneficiary")

# ---------- Utility ----------
def normalize_name(s: str) -> str:
    return " ".join((s or "").strip().lower().split())

def get_stock_query():
    # Stock = sum(IN) - sum(OUT) grouped by item
    stock_expr = func.sum(
        case((Transaction.ttype == "IN", Transaction.qty), else_=-Transaction.qty)
    ).label("stock")
    return db.session.query(Item, stock_expr).join(Transaction, Item.id == Transaction.item_id, isouter=True).group_by(Item.id)

def ensure_seed_data():
    # Seed locations
    if Location.query.count() == 0:
        for name in ["Kingston & St. Andrew Depot", "St. Catherine Depot", "St. James Depot", "Clarendon Depot"]:
            db.session.add(Location(name=name))
    # Seed categories via a sample item (not necessary, categories are free text)
    db.session.commit()

# ---------- Routes ----------
@app.route("/")
def dashboard():
    # KPIs
    total_items = Item.query.count()
    stock_rows = get_stock_query().all()
    total_in_stock = sum((row[1] or 0) for row in stock_rows)
    # Low stock
    low = []
    for item, stock in stock_rows:
        stock = stock or 0
        if item.min_qty and stock < item.min_qty:
            low.append((item, stock))
    low.sort(key=lambda x: x[1])

    # Recent transactions
    recent = Transaction.query.order_by(Transaction.created_at.desc()).limit(10).all()
    return render_template("dashboard.html",
                           total_items=total_items,
                           total_in_stock=total_in_stock,
                           low_stock=low,
                           recent=recent)

@app.route("/items")
def items():
    q = request.args.get("q", "").strip()
    cat = request.args.get("category", "").strip()
    query = get_stock_query()
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(func.lower(Item.name).like(like) | func.lower(Item.sku).like(like))
    if cat:
        query = query.filter(func.lower(Item.category) == cat.lower())
    rows = query.order_by(Item.name.asc()).all()
    return render_template("items.html", rows=rows, q=q, cat=cat)

@app.route("/items/new", methods=["GET", "POST"])
def item_new():
    if request.method == "POST":
        name = request.form["name"].strip()
        category = request.form.get("category", "").strip() or None
        unit = request.form.get("unit", "unit").strip() or "unit"
        sku = request.form.get("sku", "").strip() or None
        min_qty = int(request.form.get("min_qty", "0") or 0)
        notes = request.form.get("notes", "").strip() or None

        # Duplicate suggestion by normalized name+category+unit
        norm = normalize_name(name)
        existing = Item.query.filter(func.lower(Item.name) == norm, Item.category == category, Item.unit == unit).first()
        if existing:
            flash(f"Possible duplicate found: '{existing.name}' in category '{existing.category or '—'}' (unit: {existing.unit}). Consider editing that item instead.", "warning")
            return redirect(url_for("item_edit", item_id=existing.id))

        item = Item(name=name, category=category, unit=unit, sku=sku, min_qty=min_qty, notes=notes)
        db.session.add(item)
        db.session.commit()
        flash("Item created.", "success")
        return redirect(url_for("items"))
    return render_template("item_form.html", item=None)

@app.route("/items/<int:item_id>/edit", methods=["GET", "POST"])
def item_edit(item_id):
    item = Item.query.get_or_404(item_id)
    if request.method == "POST":
        item.name = request.form["name"].strip()
        item.category = request.form.get("category", "").strip() or None
        item.unit = request.form.get("unit", "unit").strip() or "unit"
        item.sku = request.form.get("sku", "").strip() or None
        item.min_qty = int(request.form.get("min_qty", "0") or 0)
        item.notes = request.form.get("notes", "").strip() or None
        db.session.commit()
        flash("Item updated.", "success")
        return redirect(url_for("items"))
    return render_template("item_form.html", item=item)

@app.route("/intake", methods=["GET", "POST"])
def intake():
    items = Item.query.order_by(Item.name.asc()).all()
    locations = Location.query.order_by(Location.name.asc()).all()
    if request.method == "POST":
        item_id = int(request.form["item_id"])
        qty = int(request.form["qty"])
        location_id = int(request.form["location_id"]) if request.form.get("location_id") else None
        donor_name = request.form.get("donor_name", "").strip() or None
        donor = None
        if donor_name:
            donor = Donor.query.filter_by(name=donor_name).first()
            if not donor:
                donor = Donor(name=donor_name)
                db.session.add(donor)
                db.session.flush()
        notes = request.form.get("notes", "").strip() or None

        tx = Transaction(item_id=item_id, ttype="IN", qty=qty, location_id=location_id,
                         donor_id=donor.id if donor else None, notes=notes)
        db.session.add(tx)
        db.session.commit()
        flash("Intake recorded.", "success")
        return redirect(url_for("dashboard"))
    return render_template("intake.html", items=items, locations=locations)

@app.route("/distribute", methods=["GET", "POST"])
def distribute():
    items = Item.query.order_by(Item.name.asc()).all()
    locations = Location.query.order_by(Location.name.asc()).all()
    if request.method == "POST":
        item_id = int(request.form["item_id"])
        qty = int(request.form["qty"])
        location_id = int(request.form["location_id"]) if request.form.get("location_id") else None
        beneficiary_name = request.form.get("beneficiary_name", "").strip() or None
        parish = request.form.get("parish", "").strip() or None
        beneficiary = None
        if beneficiary_name:
            beneficiary = Beneficiary.query.filter_by(name=beneficiary_name).first()
            if not beneficiary:
                beneficiary = Beneficiary(name=beneficiary_name, parish=parish)
                db.session.add(beneficiary)
                db.session.flush()
        notes = request.form.get("notes", "").strip() or None

        # Check stock
        stock_map = {i.id: s for i, s in get_stock_query().all()}
        if stock_map.get(item_id, 0) < qty:
            flash("Insufficient stock to distribute that quantity.", "danger")
            return redirect(url_for("distribute"))

        tx = Transaction(item_id=item_id, ttype="OUT", qty=qty, location_id=location_id,
                         beneficiary_id=beneficiary.id if beneficiary else None, notes=notes)
        db.session.add(tx)
        db.session.commit()
        flash("Distribution recorded.", "success")
        return redirect(url_for("dashboard"))
    return render_template("distribute.html", items=items, locations=locations)

@app.route("/transactions")
def transactions():
    rows = Transaction.query.order_by(Transaction.created_at.desc()).limit(500).all()
    return render_template("transactions.html", rows=rows)

@app.route("/reports/stock")
def report_stock():
    rows = get_stock_query().order_by(Item.category.asc(), Item.name.asc()).all()
    return render_template("report_stock.html", rows=rows)

@app.route("/export/items.csv")
def export_items():
    items = Item.query.all()
    df = pd.DataFrame([{
        "sku": it.sku or "",
        "name": it.name,
        "category": it.category or "",
        "unit": it.unit,
        "min_qty": it.min_qty,
        "notes": it.notes or "",
    } for it in items])
    csv_path = "items_export.csv"
    df.to_csv(csv_path, index=False)
    return send_file(csv_path, as_attachment=True, download_name="items.csv", mimetype="text/csv")

@app.route("/import/items", methods=["GET", "POST"])
def import_items():
    if request.method == "POST":
        f = request.files.get("file")
        if not f:
            flash("No file uploaded.", "warning")
            return redirect(url_for("import_items"))
        df = pd.read_csv(f)
        created, skipped = 0, 0
        for _, row in df.iterrows():
            name = str(row.get("name", "")).strip()
            if not name:
                continue
            category = str(row.get("category", "")).strip() or None
            unit = str(row.get("unit", "unit")).strip() or "unit"
            sku = str(row.get("sku", "")).strip() or None
            min_qty = int(row.get("min_qty", 0) or 0)
            notes = str(row.get("notes", "")).strip() or None

            norm = normalize_name(name)
            existing = Item.query.filter(func.lower(Item.name) == norm, Item.category == category, Item.unit == unit).first()
            if existing:
                skipped += 1
                continue
            item = Item(name=name, category=category, unit=unit, sku=sku, min_qty=min_qty, notes=notes)
            db.session.add(item)
            created += 1
        db.session.commit()
        flash(f"Import complete. Created {created}, skipped {skipped} duplicates.", "info")
        return redirect(url_for("items"))
    return render_template("import_items.html")

# ---------- CLI for DB ----------
@app.cli.command("init-db")
def init_db():
    db.create_all()
    ensure_seed_data()
    print("Database initialized.")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        ensure_seed_data()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
