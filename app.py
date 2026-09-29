"""Kampala Needs — Flask app for Render."""
from __future__ import annotations

import hashlib
import hmac
import math
import os
import secrets
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__, static_folder="frontend", static_url_path="")
CORS(app)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
basedir = os.path.abspath(os.path.dirname(__file__))
data_dir = os.path.join(basedir, "data")
os.makedirs(data_dir, exist_ok=True)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(data_dir, "kampala_needs.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
MIN_PASSWORD = 8


class Setting(db.Model):
    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.Text, nullable=False)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    icon = db.Column(db.String(50), default="📍")
    description = db.Column(db.String(255))


class Provider(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    description = db.Column(db.Text)
    address = db.Column(db.String(300))
    area = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    whatsapp = db.Column(db.String(50))
    email = db.Column(db.String(100))
    website = db.Column(db.String(200))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    rating = db.Column(db.Float, default=4.0)
    verified = db.Column(db.Boolean, default=False)
    featured = db.Column(db.Boolean, default=False)
    featured_until = db.Column(db.DateTime)
    status = db.Column(db.String(20), default="approved")
    submitted_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    category = db.relationship("Category", backref=db.backref("providers", lazy=True))

    def is_featured_now(self):
        if not self.featured:
            return False
        if self.featured_until and self.featured_until < datetime.utcnow():
            return False
        return True

    def to_dict(self, user_lat=None, user_lng=None):
        d = {
            "id": self.id,
            "name": self.name,
            "category": self.category.name if self.category else None,
            "category_id": self.category_id,
            "description": self.description,
            "address": self.address,
            "area": self.area,
            "phone": self.phone,
            "whatsapp": self.whatsapp,
            "email": self.email,
            "website": self.website,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "rating": self.rating,
            "verified": self.verified,
            "featured": self.is_featured_now(),
            "featured_until": self.featured_until.isoformat() if self.featured_until else None,
            "status": self.status,
        }
        if user_lat is not None and user_lng is not None and self.latitude and self.longitude:
            d["distance_km"] = round(haversine(user_lat, user_lng, self.latitude, self.longitude), 2)
        return d


class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    address = db.Column(db.String(300))
    area = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    whatsapp = db.Column(db.String(50))
    email = db.Column(db.String(100))
    website = db.Column(db.String(200))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    submitted_by = db.Column(db.String(100))
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def haversine(lat1, lon1, lat2, lon2):
    r = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_setting(key):
    row = Setting.query.get(key)
    return row.value if row else None


def set_setting(key, value):
    row = Setting.query.get(key)
    if row:
        row.value = value
    else:
        db.session.add(Setting(key=key, value=value))
    db.session.commit()


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def admin_hash():
    return get_setting("admin_password_hash")


def check_admin():
    """Accept session token header or (legacy) password header after setup."""
    h = admin_hash()
    if not h:
        return False
    token = request.headers.get("X-Admin-Token") or request.args.get("token")
    stored = get_setting("admin_session")
    if token and stored and hmac.compare_digest(hash_token(token), stored):
        return True
    password = request.headers.get("X-Admin-Password")
    if password and check_password_hash(h, password):
        return True
    body = request.get_json(silent=True) or {}
    if body.get("token") and stored and hmac.compare_digest(hash_token(body["token"]), stored):
        return True
    return False


def seed_data():
    if Category.query.first():
        return
    cats = [
        ("Mechanics & Auto", "🔧", "Car, motorcycle, and boda repair"),
        ("Brokers & Agents", "🏠", "Property, land, and rental agents"),
        ("Retail & Shops", "🛒", "Shops, markets, and retailers"),
        ("Offices & Services", "🏢", "Government offices, banks, professionals"),
        ("Health & Clinics", "🏥", "Clinics, pharmacies, hospitals"),
        ("Food & Restaurants", "🍽️", "Restaurants, cafes, food suppliers"),
        ("Electronics & Tech", "📱", "Phone repairs, computer shops"),
        ("Beauty & Salon", "💇", "Hair, nails, barbers"),
        ("Transport & Logistics", "🚚", "Delivery, movers, transport"),
        ("Education & Tutors", "📚", "Schools, tutors, training"),
        ("Home Services", "🛠️", "Plumbing, electrical, cleaning"),
        ("Other", "📍", "Everything else"),
    ]
    for name, icon, desc in cats:
        db.session.add(Category(name=name, icon=icon, description=desc))
    db.session.commit()
    by = {c.name: c.id for c in Category.query.all()}
    rows = [
        ("Nakasero Auto Garage", "Mechanics & Auto", "Trusted car and motorcycle repairs. Genuine parts available.", "Plot 12, Nakasero Road", "Nakasero", "+256 700 123456", "+256700123456", 0.3163, 32.5822, 4.5),
        ("Wandegeya Boda Mechanics", "Mechanics & Auto", "Specialists in boda-boda engine and tyre repairs. Fast service.", "Near Wandegeya Market", "Wandegeya", "+256 772 987654", "+256772987654", 0.332, 32.568, 4.3),
        ("Kololo Motors", "Mechanics & Auto", "Full service garage for cars. Diagnostic tools available.", "Kololo Hill Road", "Kololo", "+256 701 555444", "+256701555444", 0.335, 32.59, 4.7),
        ("Kampala Property Brokers", "Brokers & Agents", "Trusted land and house agents. Verified listings.", "Plot 5, Parliament Avenue", "Central", "+256 414 123456", "+256414123456", 0.314, 32.582, 4.4),
        ("Ntinda Homes Agency", "Brokers & Agents", "Rentals and sales in Ntinda, Kisaasi, and surrounding areas.", "Ntinda Shopping Centre", "Ntinda", "+256 700 222333", "+256700222333", 0.355, 32.62, 4.2),
        ("Owino Market (St. Balikuddembe)", "Retail & Shops", "Largest market for clothes, shoes, household items. Bargain prices.", "Kikuubo, Downtown", "Downtown", "", "", 0.311, 32.575, 4.0),
        ("Shoprite Lugogo", "Retail & Shops", "Supermarket with groceries, household goods, and electronics.", "Lugogo Mall", "Lugogo", "+256 414 250000", "", 0.34, 32.605, 4.5),
        ("Game Stores Kampala", "Retail & Shops", "Electronics, appliances, and home goods.", "Acacia Mall, Kisementi", "Kololo", "+256 414 340000", "", 0.338, 32.585, 4.4),
        ("Uganda Registration Services Bureau (URSB)", "Offices & Services", "Business registration, company searches, intellectual property.", "Plot 1, Baskerville Avenue, Kololo", "Kololo", "+256 414 233 219", "", 0.332, 32.588, 4.0),
        ("KCCA City Hall", "Offices & Services", "Kampala Capital City Authority — permits, taxes, city services.", "City Hall, Parliamentary Avenue", "Central", "+256 414 231 000", "", 0.3145, 32.5825, 3.8),
        ("Mulago National Referral Hospital", "Health & Clinics", "Main public hospital. Emergency and specialist care.", "Mulago Hill", "Mulago", "+256 414 554 000", "", 0.338, 32.575, 3.9),
        ("Case Hospital", "Health & Clinics", "Private hospital with modern facilities.", "Plot 69/71, Buganda Road", "Nakasero", "+256 312 250 500", "", 0.32, 32.575, 4.6),
        ("Café Javas Nakasero", "Food & Restaurants", "Popular restaurant chain. Breakfast, lunch, coffee.", "Plot 14, Nakasero Road", "Nakasero", "+256 414 340 000", "", 0.318, 32.582, 4.5),
        ("2K Restaurant Wandegeya", "Food & Restaurants", "Local and international dishes. Student-friendly prices.", "Wandegeya, near Makerere", "Wandegeya", "+256 700 111222", "", 0.333, 32.57, 4.2),
        ("Phone Repair Hub — Kikuubo", "Electronics & Tech", "Screen replacement, battery, software for all phone brands.", "Kikuubo Arcade", "Downtown", "+256 772 333444", "+256772333444", 0.312, 32.576, 4.3),
        ("Computer Point Makerere", "Electronics & Tech", "Laptops, accessories, and repairs near university.", "Makerere Kikoni", "Makerere", "+256 701 444555", "", 0.335, 32.568, 4.1),
        ("Style Lounge Salon", "Beauty & Salon", "Hair, nails, and beauty treatments.", "Acacia Mall", "Kololo", "+256 700 666777", "", 0.3385, 32.5855, 4.6),
        ("SafeBoda Office — Kampala", "Transport & Logistics", "Official SafeBoda support and registration.", "Various hubs in city", "Central", "*255# or app", "", 0.315, 32.58, 4.4),
        ("Kampala Plumbers Network", "Home Services", "Trusted plumbers for homes and offices. 24/7 emergency.", "Serves all Kampala", "Citywide", "+256 700 888999", "+256700888999", 0.32, 32.58, 4.5),
        ("QuickFix Electricians", "Home Services", "Electrical installations and repairs. Licensed.", "Ntinda and surrounding", "Ntinda", "+256 772 000111", "+256772000111", 0.35, 32.615, 4.3),
    ]
    for name, cat, desc, addr, area, phone, wa, lat, lng, rating in rows:
        db.session.add(
            Provider(
                name=name,
                category_id=by[cat],
                description=desc,
                address=addr,
                area=area,
                phone=phone or None,
                whatsapp=wa or None,
                latitude=lat,
                longitude=lng,
                rating=rating,
                verified=True,
                status="approved",
            )
        )
    db.session.commit()


def parse_date(val):
    if not val:
        return None
    try:
        return datetime.fromisoformat(str(val).replace("Z", "")[:19])
    except Exception:
        try:
            return datetime.strptime(str(val)[:10], "%Y-%m-%d")
        except Exception:
            return None


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/admin")
def admin_page():
    return send_from_directory(app.static_folder, "admin.html")


@app.route("/api/categories")
def categories():
    cats = Category.query.all()
    return jsonify(
        [
            {
                "id": c.id,
                "name": c.name,
                "icon": c.icon,
                "description": c.description,
                "count": Provider.query.filter_by(category_id=c.id, status="approved").count(),
            }
            for c in cats
        ]
    )


@app.route("/api/search")
def search():
    q = (request.args.get("q") or "").strip()
    category_id = request.args.get("category_id", type=int)
    area = (request.args.get("area") or "").strip()
    user_lat = request.args.get("lat", type=float)
    user_lng = request.args.get("lng", type=float)
    limit = request.args.get("limit", 40, type=int)
    query = Provider.query.filter_by(status="approved")
    if category_id:
        query = query.filter_by(category_id=category_id)
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Provider.name.ilike(like),
                Provider.description.ilike(like),
                Provider.address.ilike(like),
                Provider.area.ilike(like),
            )
        )
    if area:
        query = query.filter(Provider.area.ilike(f"%{area}%"))
    results = [p.to_dict(user_lat, user_lng) for p in query.all()]

    def sort_key(x):
        feat = 0 if x.get("featured") else 1
        if user_lat is not None and user_lng is not None:
            return (feat, x.get("distance_km") if x.get("distance_km") is not None else 9999)
        return (feat, -x.get("rating", 0))

    results.sort(key=sort_key)
    return jsonify({"count": len(results), "results": results[:limit]})


@app.route("/api/submit", methods=["POST"])
def submit():
    data = request.get_json() or {}
    if not data.get("name") or not data.get("category_name"):
        return jsonify({"error": "name and category_name are required"}), 400
    sub = Submission(
        name=data["name"].strip(),
        category_name=data["category_name"].strip(),
        description=(data.get("description") or "").strip() or None,
        address=(data.get("address") or "").strip() or None,
        area=(data.get("area") or "").strip() or None,
        phone=(data.get("phone") or "").strip() or None,
        whatsapp=(data.get("whatsapp") or "").strip() or None,
        submitted_by=(data.get("submitted_by") or "Anonymous").strip(),
        reason=(data.get("reason") or "").strip() or None,
        status="pending",
    )
    db.session.add(sub)
    db.session.commit()
    return jsonify({"message": "Submitted for review. Thank you.", "id": sub.id}), 201


@app.route("/api/boda-link")
def boda_link():
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)
    name = request.args.get("name") or "destination"
    address = request.args.get("address") or ""
    if lat is None or lng is None:
        return jsonify({"error": "lat and lng required"}), 400
    gmaps = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving"
    wa_text = f"Please take me to {name}" + (f" ({address})" if address else "") + f". Location: https://maps.google.com/?q={lat},{lng}"
    return jsonify(
        {
            "google_maps": gmaps,
            "whatsapp_share": "https://wa.me/?text=" + wa_text.replace(" ", "%20"),
            "tips": [
                "Open SafeBoda, Bolt, or Uber and set this location as destination.",
                "Show the Google Maps pin to your boda rider.",
                "Share the WhatsApp location message with the rider.",
            ],
        }
    )


@app.route("/api/admin/status")
def admin_status():
    return jsonify({"needsSetup": not bool(admin_hash())})


@app.route("/api/admin/setup", methods=["POST"])
def admin_setup():
    if admin_hash():
        return jsonify({"error": "Admin password is already set"}), 400
    data = request.get_json() or {}
    password = data.get("password") or ""
    confirm = data.get("confirm") or ""
    if len(password) < MIN_PASSWORD:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
    if password != confirm:
        return jsonify({"error": "Passwords do not match"}), 400
    set_setting("admin_password_hash", generate_password_hash(password))
    token = secrets.token_hex(32)
    set_setting("admin_session", hash_token(token))
    return jsonify({"ok": True, "token": token})


@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    h = admin_hash()
    if not h:
        return jsonify({"error": "Set up an admin password first", "needsSetup": True}), 400
    data = request.get_json() or {}
    password = data.get("password") or ""
    if not check_password_hash(h, password):
        return jsonify({"error": "Wrong password"}), 401
    token = secrets.token_hex(32)
    set_setting("admin_session", hash_token(token))
    return jsonify({"ok": True, "token": token})


@app.route("/api/admin/change-password", methods=["POST"])
def admin_change_password():
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    current = data.get("current") or ""
    nxt = data.get("next") or ""
    confirm = data.get("confirm") or ""
    h = admin_hash()
    if not h or not check_password_hash(h, current):
        return jsonify({"error": "Current password is wrong"}), 400
    if len(nxt) < MIN_PASSWORD:
        return jsonify({"error": "New password must be at least 8 characters"}), 400
    if nxt != confirm:
        return jsonify({"error": "Passwords do not match"}), 400
    set_setting("admin_password_hash", generate_password_hash(nxt))
    token = secrets.token_hex(32)
    set_setting("admin_session", hash_token(token))
    return jsonify({"ok": True, "token": token, "message": "Password updated"})


@app.route("/api/admin/pending")
def admin_pending():
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401
    subs = Submission.query.filter_by(status="pending").order_by(Submission.created_at.desc()).all()
    return jsonify(
        [
            {
                "id": s.id,
                "name": s.name,
                "category_name": s.category_name,
                "description": s.description,
                "address": s.address,
                "area": s.area,
                "phone": s.phone,
                "whatsapp": s.whatsapp,
                "submitted_by": s.submitted_by,
                "reason": s.reason,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in subs
        ]
    )


@app.route("/api/admin/approve/<int:sid>", methods=["POST"])
def admin_approve(sid):
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401
    sub = Submission.query.get_or_404(sid)
    cat = Category.query.filter_by(name=sub.category_name).first()
    if not cat:
        cat = Category(name=sub.category_name, icon="📍")
        db.session.add(cat)
        db.session.flush()
    p = Provider(
        name=sub.name,
        category_id=cat.id,
        description=sub.description,
        address=sub.address,
        area=sub.area,
        phone=sub.phone,
        whatsapp=sub.whatsapp,
        verified=False,
        status="approved",
        submitted_by=sub.submitted_by,
    )
    db.session.add(p)
    sub.status = "approved"
    db.session.commit()
    return jsonify({"message": "Approved", "provider_id": p.id})


@app.route("/api/admin/reject/<int:sid>", methods=["POST"])
def admin_reject(sid):
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401
    sub = Submission.query.get_or_404(sid)
    sub.status = "rejected"
    db.session.commit()
    return jsonify({"message": "Rejected"})


@app.route("/api/admin/providers")
def admin_providers():
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401
    q = (request.args.get("q") or "").strip()
    query = Provider.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Provider.name.ilike(like),
                Provider.description.ilike(like),
                Provider.address.ilike(like),
                Provider.area.ilike(like),
                Provider.phone.ilike(like),
            )
        )
    return jsonify([p.to_dict() for p in query.order_by(Provider.created_at.desc()).all()])


@app.route("/api/admin/add-provider", methods=["POST"])
def admin_add():
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    if not data.get("name") or not data.get("category_id"):
        return jsonify({"error": "name and category_id required"}), 400
    p = Provider(
        name=data["name"],
        category_id=int(data["category_id"]),
        description=data.get("description"),
        address=data.get("address"),
        area=data.get("area"),
        phone=data.get("phone"),
        whatsapp=data.get("whatsapp"),
        email=data.get("email"),
        website=data.get("website"),
        latitude=data.get("latitude") or None,
        longitude=data.get("longitude") or None,
        rating=float(data.get("rating") or 4),
        verified=bool(data.get("verified", True)),
        featured=bool(data.get("featured")),
        featured_until=parse_date(data.get("featured_until")),
        status="approved",
    )
    db.session.add(p)
    db.session.commit()
    return jsonify({"message": "Provider added", "id": p.id}), 201


@app.route("/api/admin/provider/<int:pid>", methods=["PUT"])
def admin_edit(pid):
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401
    p = Provider.query.get_or_404(pid)
    data = request.get_json() or {}
    for field in ("name", "description", "address", "area", "phone", "whatsapp", "email", "website"):
        if field in data:
            setattr(p, field, data[field] or None)
    if data.get("category_id"):
        p.category_id = int(data["category_id"])
    if "latitude" in data:
        p.latitude = float(data["latitude"]) if data["latitude"] not in (None, "") else None
    if "longitude" in data:
        p.longitude = float(data["longitude"]) if data["longitude"] not in (None, "") else None
    if data.get("rating") is not None:
        p.rating = float(data["rating"])
    if "verified" in data:
        p.verified = bool(data["verified"])
    if "featured" in data:
        p.featured = bool(data["featured"])
    if "featured_until" in data:
        p.featured_until = parse_date(data["featured_until"])
    p.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": "Updated", "provider": p.to_dict()})


@app.route("/api/admin/provider/<int:pid>", methods=["DELETE"])
def admin_delete(pid):
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401
    p = Provider.query.get_or_404(pid)
    name = p.name
    db.session.delete(p)
    db.session.commit()
    return jsonify({"message": f"Deleted {name}"})


with app.app_context():
    db.create_all()
    seed_data()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
