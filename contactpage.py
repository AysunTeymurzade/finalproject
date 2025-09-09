from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import datetime, timedelta
import re
from pathlib import Path
from ipaddress import ip_address
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

DB_PATH = Path("contact.db")
PRIMARY = "#2A314D"

last_submit_by_ip = {}

# DB
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

# validasiya
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
NAME_RE = re.compile(r"^[A-ZƏİÖÜÇŞĞ][a-zəiöüçşğ]+ [A-ZƏİÖÜÇŞĞ][a-zəiöüçşğ]+(?: [A-ZƏİÖÜÇŞĞ][a-zəiöüçşğ]+)*$")

def validate_payload(data: dict):
    errors = {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    message = (data.get("message") or "").strip()
    hp = (data.get("hp") or "").strip()
    
    if not NAME_RE.match(name):
        errors["name"] = "Ad və soyad yalnız hərflərdən ibarət olmalı və düzgün formatda olmalıdır (məs: Aysun Rəsulova)."
    if not EMAIL_RE.match(email):
        errors["email"] = "Email düzgün formatda deyil."
    if not (10 <= len(message) <= 2000):
        errors["message"] = "Mesaj 10–2000 simvol aralığında olmalıdır."
    if hp:
        errors["hp"] = "Honeypot dolu gəlib (bot şübhəsi)."
    return errors

# email
SMTP_SERVER = "smtp.aesma.edu.az"   # AESMA SMTP server
SMTP_PORT = 587
EMAIL_USER = "info@aesma.edu.az"  # AESMA emaili
EMAIL_PASS = "email_sifresi"             # email sifresi
EMAIL_TO = "info@aesma.edu.az"   # mesajlarin gedeceyi AESMA emaili

def send_email(name, email, message):
    subject = f"Yeni mesaj: {name}"
    body = f"Ad və Soyad: {name}\nEmail: {email}\nMesaj:\n{message}"
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO
    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())
    except Exception as e:
        print("Email göndərilərkən xəta:", e)

# routlar
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

    # DB-de saxlama
    save_message(name=data["name"].strip(),
                 email=data["email"].strip(),
                 message=data["message"].strip(),
                 ip=str(client_ip))
    
    # email gonderme
    send_email(name=data["name"].strip(),
               email=data["email"].strip(),
               message=data["message"].strip())

    return jsonify({"ok": True})

# admin paneli
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
