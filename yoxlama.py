from flask import Flask, request, jsonify, make_response, render_template_string
import sqlite3
from datetime import datetime, timedelta
import re
from pathlib import Path
from ipaddress import ip_address

app = Flask(__name__)

# ---------------------------
# Config
# ---------------------------
DB_PATH = Path("contact.db")
PRIMARY = "#2a314d"

# Sadə IP-based rate limit yaddaşı
last_submit_by_ip = {}  # { ip: datetime }

# ---------------------------
# DB helpers
# ---------------------------
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

# ---------------------------
# Validators
# ---------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def validate_payload(data: dict):
    errors = {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    message = (data.get("message") or "").strip()
    hp = (data.get("hp") or "").strip()  # honeypot

    if not (2 <= len(name) <= 100):
        errors["name"] = "Ad 2–100 simvol olmalıdır."

    if not EMAIL_RE.match(email):
        errors["email"] = "Email düzgün formatda deyil."

    if not (10 <= len(message) <= 2000):
        errors["message"] = "Mesaj 10–2000 simvol aralığında olmalıdır."

    if hp:
        errors["hp"] = "Honeypot dolu gəlib (bot şübhəsi)."

    return errors

# ---------------------------
# Routes
# ---------------------------
@app.get("/")
def index():
    # HTML + CSS + JS bir faylda (demo üçün)
    html = f"""
<!doctype html>
<html lang="az">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Contact | Project</title>
  <style>
    :root {{
      --primary: {PRIMARY};
      --text: #1f2937;       /* dark gray */
      --muted: #475569;      /* slate-600 */
      --bg: #f5f6fa;         /* soft */
      --card: #ffffff;
      --border: #e5e7eb;
      --success: #16a34a;
      --error: #dc2626;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
      background: linear-gradient(180deg, var(--bg), #eef0f6);
      color: var(--text);
    }}

    .container {{
      min-height: 100dvh;
      display: grid;
      place-items: center;
      padding: 24px;
    }}

    .grid {{
      width: 100%;
      max-width: 1100px;
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 24px;
    }}

    @media (max-width: 900px) {{
      .grid {{ grid-template-columns: 1fr; }}
    }}

    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      box-shadow: 0 10px 28px rgba(42,49,77,0.10);
      overflow: hidden;
    }}

    .form-card {{ padding: 28px; }}

    h1 {{
      font-size: clamp(22px, 2.4vw, 34px);
      color: var(--primary);
      margin: 0 0 8px;
      letter-spacing: 0.2px;
    }}
    .subtitle {{
      color: var(--muted);
      margin-bottom: 22px;
      line-height: 1.5;
    }}

    .field {{
      display: grid;
      gap: 8px;
      margin-bottom: 16px;
    }}
    label {{
      font-weight: 600;
      color: #334155;
      font-size: 14px;
    }}
    input[type="text"], input[type="email"], textarea {{
      width: 100%;
      padding: 14px 14px;
      border: 1px solid var(--border);
      border-radius: 12px;
      font-size: 15px;
      background: #fff;
      outline: none;
      transition: box-shadow .15s ease, border-color .15s ease;
    }}
    input:focus, textarea:focus {{
      border-color: var(--primary);
      box-shadow: 0 0 0 4px rgba(42,49,77,0.16);
    }}
    textarea {{ resize: vertical; min-height: 140px; }}

    .row {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }}
    @media (max-width: 600px) {{
      .row {{ grid-template-columns: 1fr; }}
    }}

    .btn {{
      width: 100%;
      padding: 14px 18px;
      border: none;
      border-radius: 12px;
      background: var(--primary);
      color: white;
      font-weight: 700;
      font-size: 16px;
      cursor: pointer;
      transition: transform .06s ease, filter .2s ease, background .2s ease;
    }}
    .btn:hover {{ filter: brightness(1.06); }}
    .btn:active {{ transform: translateY(1px); }}
    .btn[disabled] {{ opacity: .7; cursor: not-allowed; }}

    .alert {{
      margin-top: 12px;
      padding: 12px 14px;
      border-radius: 12px;
      font-size: 14px;
      line-height: 1.4;
    }}
    .alert.success {{ background: #ecfdf5; color: #065f46; border: 1px solid #d1fae5; }}
    .alert.error   {{ background: #fef2f2; color: #7f1d1d; border: 1px solid #fee2e2; }}

    .info-card {{
      display: grid;
      background: var(--primary);
      color: #fff;
      padding: 28px;
      border-radius: 16px;
      position: relative;
      overflow: hidden;
    }}
    .info-card::after {{
      content: "";
      position: absolute;
      inset: -20% -10% auto auto;
      width: 240px; height: 240px;
      background: radial-gradient(closest-side, rgba(255,255,255,.18), transparent);
      border-radius: 50%;
      pointer-events: none;
    }}
    .info-title {{
      font-size: clamp(18px, 2vw, 24px);
      margin: 0 0 10px;
    }}
    .info-item {{ margin: 8px 0; opacity: .95; }}
    .socials {{ display: flex; gap: 12px; margin-top: 10px; }}
    .chip {{
      display: inline-block;
      font-size: 12px;
      opacity: .9;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(255,255,255,.14);
      border: 1px solid rgba(255,255,255,.24);
      margin-top: 6px;
    }}

    /* Honeypot field – gizlə */
    .hp {{ position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="grid">

      <div class="card form-card">
        <h1>Bizimlə əlaqə saxlayın</h1>
        <p class="subtitle">Sualınız və ya təklifiniz varsa, formanı doldurun — mümkün qədər tez cavab verəcəyik.</p>

        <form id="contact-form" novalidate>
          <div class="row">
            <div class="field">
              <label for="name">Ad</label>
              <input id="name" name="name" type="text" placeholder="Adınız">
            </div>
            <div class="field">
              <label for="email">Email</label>
              <input id="email" name="email" type="email" placeholder="email@misal.com">
            </div>
          </div>

          <div class="field">
            <label for="message">Mesaj</label>
            <textarea id="message" name="message" placeholder="Mesajınız"></textarea>
          </div>

          <!-- Honeypot (botlar üçün tələ) -->
          <div class="hp">
            <label for="hp">Vebsayt</label>
            <input id="hp" name="hp" type="text" tabindex="-1" autocomplete="off">
          </div>

          <button id="submitBtn" class="btn" type="submit">Göndər</button>
          <div id="alert"></div>
        </form>
      </div>

      <div class="info-card">
        <h2 class="info-title">Əlaqə məlumatları</h2>
        <div class="info-item">📍 Bakı, Azərbaycan</div>
        <div class="info-item">📞 +994 50 123 45 67</div>
        <div class="info-item">✉ info@example.com</div>
        <span class="chip">Cavab vaxtı: 24 saat</span>
        <div class="socials">
          <a href="#" title="Vebsayt" style="color:#fff; text-decoration:none;">🌐</a>
          <a href="#" title="Facebook" style="color:#fff; text-decoration:none;">📘</a>
          <a href="#" title="X" style="color:#fff; text-decoration:none;">𝕏</a>
          <a href="#" title="LinkedIn" style="color:#fff; text-decoration:none;">in</a>
        </div>
      </div>

    </div>
  </div>

  <script>
    const form = document.getElementById('contact-form');
    const alertBox = document.getElementById('alert');
    const submitBtn = document.getElementById('submitBtn');

    function showAlert(type, message) {{
      alertBox.className = 'alert ' + (type === 'success' ? 'success' : 'error');
      alertBox.textContent = message;
    }}

    function clearAlert() {{
      alertBox.className = '';
      alertBox.textContent = '';
    }}

    form.addEventListener('submit', async (e) => {{
      e.preventDefault();
      clearAlert();

      const name = document.getElementById('name').value.trim();
      const email = document.getElementById('email').value.trim();
      const message = document.getElementById('message').value.trim();
      const hp = document.getElementById('hp').value.trim(); // honeypot

      // Sadə front validation
      if (name.length < 2) {{
        showAlert('error', 'Ad ən azı 2 simvol olmalıdır.');
        return;
      }}
      if (!/^\\S+@\\S+\\.\\S+$/.test(email)) {{
        showAlert('error', 'Email düzgün formatda deyil.');
        return;
      }}
      if (message.length < 10) {{
        showAlert('error', 'Mesaj 10 simvoldan az olmamalıdır.');
        return;
      }}

      submitBtn.disabled = true;
      const originalText = submitBtn.textContent;
      submitBtn.textContent = 'Göndərilir...';

      try {{
        const res = await fetch('/api/contact', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ name, email, message, hp }}),
        }});

        const data = await res.json();
        if (!res.ok) {{
          const msg = data && data.error ? data.error : 'Xəta baş verdi.';
          showAlert('error', msg);
        }} else {{
          showAlert('success', 'Mesajınız qəbul olundu. Təşəkkür edirik!');
          form.reset();
        }}
      }} catch (err) {{
        showAlert('error', 'Şəbəkə xətası baş verdi. Yenidən cəhd edin.');
      }} finally {{
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
      }}
    }});
  </script>
</body>
</html>
    """
    return make_response(render_template_string(html))

@app.post("/api/contact")
def api_contact():
    init_db()  # ilk sorğuda da hazır olsun
    data = {}
    try:
        data = request.get_json(force=True, silent=False) or {}
    except Exception:
        return jsonify({"error": "Yanlış JSON məlumatı."}), 400

    # Honeypot + doğrulama
    errors = validate_payload(data)
    if errors:
        # Bir xülasə mesajı qaytaraq
        return jsonify({"error": "; ".join(f"{k}: {v}" for k, v in errors.items())}), 400

    # Rate limit (15 saniyə)
    try:
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "0.0.0.0"
        # (təhlükəsiz parse üçün ip_address istifadə edək — invalid olsa, except düşsün)
        ip_address(client_ip.split(",")[0].strip())
    except Exception:
        client_ip = "0.0.0.0"

    now = datetime.utcnow()
    last = last_submit_by_ip.get(client_ip)
    if last and (now - last) < timedelta(seconds=15):
        return jsonify({"error": "Çox tez-tez göndərirsiniz. 15 saniyə sonra yenidən cəhd edin."}), 429
    last_submit_by_ip[client_ip] = now

    # Məlumatları al
    name = data["name"].strip()
    email = data["email"].strip()
    message = data["message"].strip()

    # DB-ə yaz
    save_message(name, email, message, client_ip)

    return jsonify({"ok": True})

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host='localhost', port=5555)
