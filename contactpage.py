from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import datetime, timedelta
import re
from pathlib import Path
from ipaddress import ip_address

app = Flask(__name__)

DB_PATH = Path("contact.db")
PRIMARY = "#2A314D"

last_submit_by_ip = {}

# DB daxil etme
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            ip TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()

def save_message(name, email, message, ip):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO contact_messages (name, email, message, ip, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, email, message, ip, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

# Email validation
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Ad və soyad yoxlaması (böyük hərflə başlayan sözlər, yalnız hərflər və boşluq)
NAME_RE = re.compile(r"^[A-ZƏİÖÜÇŞĞ][a-zəiöüçşğ]+ [A-ZƏİÖÜÇŞĞ][a-zəiöüçşğ]+(?: [A-ZƏİÖÜÇŞĞ][a-zəiöüçşğ]+)*$")

def validate_payload(data: dict):
    errors = {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    message = (data.get("message") or "").strip()
    hp = (data.get("hp") or "").strip()  # honeypot field
    
    if not NAME_RE.match(name):
        errors["name"] = "Ad və soyad yalnız hərflərdən ibarət olmalı və düzgün formatda olmalıdır (məs: Aysun Rəsulova)."
    if not EMAIL_RE.match(email):
        errors["email"] = "Email düzgün formatda deyil."
    if not (10 <= len(message) <= 2000):
        errors["message"] = "Mesaj 10–2000 simvol aralığında olmalıdır."
    if hp:
        errors["hp"] = "Honeypot dolu gəlib (bot şübhəsi)."
    return errors

# Rout-lar
@app.get("/contact")
def contact_page():
    return render_template("contact.html", primary=PRIMARY) 

@app.post("/api/contact")
def api_contact():
    init_db()
    data = request.get_json(force=True, silent=True) or {}
    
    errors = validate_payload(data)
    if errors:
        return jsonify({"error": "; ".join(f"{k}: {v}" for k, v in errors.items())}), 400

    # Vaxt limiti (15 saniyə)
    try:
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "0.0.0.0"
        client_ip = ip_address(client_ip.split(",")[0].strip())
    except Exception:
        client_ip = "0.0.0.0"
    now = datetime.utcnow()
    last = last_submit_by_ip.get(client_ip)
    if last and (now - last) < timedelta(seconds=15):
        return jsonify({"error": "Çox tez-tez göndərirsiniz. 15 saniyə sonra yenidən cəhd edin."}), 429
    last_submit_by_ip[client_ip] = now

    # DB-ye yaddaşa ver
    save_message(name=data["name"].strip(),
                 email=data["email"].strip(),
                 message=data["message"].strip(),
                 ip=str(client_ip))
    return jsonify({"ok": True})

@app.get("/admin/messages")
def admin_messages():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, message, created_at FROM contact_messages ORDER BY created_at DESC")
    messages = cur.fetchall()
    conn.close()
    return render_template("admin_messages.html", messages=messages, primary=PRIMARY)

if __name__ == "__main__":
    app.run(debug=True, host="localhost", port=5555)
