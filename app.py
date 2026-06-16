from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_bcrypt import Bcrypt
from functools import wraps
import mysql.connector
from dotenv import load_dotenv
load_dotenv()
import os
from datetime import datetime, date
import json

app = Flask(__name__)
# import os

# base_dir = os.path.abspath(os.path.dirname(__file__))

# app = Flask(
#     __name__,
#     template_folder=os.path.join(base_dir, "templates"),
#     static_folder=os.path.join(base_dir, "static")
# )
# print("TEMPLATE PATH:", os.path.join(base_dir, "templates"))
app.secret_key = os.environ.get('SECRET_KEY', 'clinic-secret-key-change-in-production')
bcrypt = Bcrypt(app)

# ── DB Config ──────────────────────────────────────────────────────────────────
DB_CONFIG = {
    'host':     os.environ.get('DB_HOST', 'localhost'),
    'user':     os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'clinic_db'),
    'autocommit': True
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)


# ── Auth Decorator ──────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ── DB Init ────────────────────────────────────────────────────────────────────
def init_db():
    """Create tables and default admin user if they don't exist."""
    config = {k: v for k, v in DB_CONFIG.items() if k != 'database'}
    config['autocommit'] = True
    conn = mysql.connector.connect(**config)
    cur = conn.cursor()
    cur.execute("CREATE DATABASE IF NOT EXISTS clinic_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.execute("USE clinic_db")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            username    VARCHAR(80)  NOT NULL UNIQUE,
            password    VARCHAR(255) NOT NULL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            first_name VARCHAR(100) NOT NULL,
            last_name  VARCHAR(100) NOT NULL,
            age        INT          NOT NULL,
            gender     ENUM('Male','Female','Other') NOT NULL,
            phone      VARCHAR(20),
            address    TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            patient_id   INT          NOT NULL,
            visit_date   DATE         NOT NULL,
            complaint    TEXT,
            diagnosis    TEXT,
            treatment    TEXT,
            total_amount DECIMAL(10,2) DEFAULT 0.00,
            paid_amount  DECIMAL(10,2) DEFAULT 0.00,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
        )
    """)

    # Default admin: admin / clinic123
    cur.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cur.fetchone():
        hashed = bcrypt.generate_password_hash('clinic123').decode('utf-8')
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", ('admin', hashed))

    cur.close()
    conn.close()


# ── Auth Routes ────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() or request.form
        username = data.get('username', '').strip()
        password = data.get('password', '')

        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and bcrypt.check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            if request.is_json:
                return jsonify({'success': True})
            return redirect(url_for('dashboard'))
        else:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
            return render_template('login.html', error='Invalid credentials')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ── Page Routes ────────────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/patients')
@login_required
def patients_page():
    return render_template('patients.html')


@app.route('/patient/<int:patient_id>')
@login_required
def patient_detail(patient_id):
    return render_template('patient_detail.html', patient_id=patient_id)


# ── API: Dashboard Stats ───────────────────────────────────────────────────────
@app.route('/api/stats')
@login_required
def api_stats():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) AS total FROM patients")
    total_patients = cur.fetchone()['total']
    cur.execute("""
        SELECT COALESCE(SUM(paid_amount), 0) AS total FROM visits
        WHERE visit_date = CURDATE()
    """)
    today_revenue = float(cur.fetchone()['total'])
    cur.execute("""
        SELECT COALESCE(SUM(total_amount - paid_amount), 0) AS total FROM visits
        WHERE visit_date = CURDATE()
    """)
    today_due = float(cur.fetchone()['total'])
    cur.execute("""
        SELECT COUNT(*) AS total FROM visits
        WHERE visit_date = CURDATE()
    """)
    today_visits = cur.fetchone()['total']
    cur.close()
    conn.close()
    return jsonify({
        'total_patients': total_patients,
        'today_revenue':  today_revenue,
        'today_due':      today_due,
        'today_visits':   today_visits
    })

# ── API: Patients ──────────────────────────────────────────────────────────────
@app.route('/api/patients', methods=['GET', 'POST'])
@login_required
def api_patients():
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    if request.method == 'GET':
        search = request.args.get('search', '').strip()
        if search:
            like = f'%{search}%'
            cur.execute("""
                SELECT p.*,
                       COALESCE(SUM(v.total_amount), 0)  AS total_billed,
                       COALESCE(SUM(v.paid_amount), 0)   AS total_paid,
                       COALESCE(SUM(v.total_amount - v.paid_amount), 0) AS total_due,
                       COUNT(v.id) AS visit_count
                FROM patients p
                LEFT JOIN visits v ON v.patient_id = p.id
                WHERE p.first_name LIKE %s OR p.last_name LIKE %s
                GROUP BY p.id
                ORDER BY p.created_at DESC
            """, (like, like))
        else:
            cur.execute("""
                SELECT p.*,
                       COALESCE(SUM(v.total_amount), 0)  AS total_billed,
                       COALESCE(SUM(v.paid_amount), 0)   AS total_paid,
                       COALESCE(SUM(v.total_amount - v.paid_amount), 0) AS total_due,
                       COUNT(v.id) AS visit_count
                FROM patients p
                LEFT JOIN visits v ON v.patient_id = p.id
                GROUP BY p.id
                ORDER BY p.created_at DESC
            """)
        rows = cur.fetchall()
        # Convert decimals
        for r in rows:
            r['total_billed'] = float(r['total_billed'])
            r['total_paid']   = float(r['total_paid'])
            r['total_due']    = float(r['total_due'])
            r['created_at']   = r['created_at'].strftime('%Y-%m-%d %H:%M') if r['created_at'] else ''
        cur.close(); conn.close()
        return jsonify(rows)

    # POST – add patient
    data = request.get_json()
    required = ['first_name', 'last_name', 'age', 'gender']
    for f in required:
        if not data.get(f):
            return jsonify({'error': f'{f} is required'}), 400

    cur.execute("""
        INSERT INTO patients (first_name, last_name, age, gender, phone, address)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        data['first_name'].strip(),
        data['last_name'].strip(),
        int(data['age']),
        data['gender'],
        data.get('phone', '').strip(),
        data.get('address', '').strip()
    ))
    new_id = cur.lastrowid
    cur.close(); conn.close()
    return jsonify({'success': True, 'id': new_id}), 201

 
 
# ── API: Today's Patients ──────────────────────────────────────────────────────
@app.route('/api/patients/today')
@login_required
def api_patients_today():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT p.*,
               COALESCE(SUM(v.total_amount), 0)                 AS total_billed,
               COALESCE(SUM(v.paid_amount), 0)                  AS total_paid,
               COALESCE(SUM(v.total_amount - v.paid_amount), 0) AS total_due,
               COUNT(v.id) AS visit_count
        FROM patients p
        INNER JOIN visits v ON v.patient_id = p.id
        WHERE v.visit_date = CURDATE()
        GROUP BY p.id
        ORDER BY MAX(v.created_at) DESC
    """)
    rows = cur.fetchall()
    for r in rows:
        r['total_billed'] = float(r['total_billed'])
        r['total_paid']   = float(r['total_paid'])
        r['total_due']    = float(r['total_due'])
        r['created_at']   = r['created_at'].strftime('%Y-%m-%d %H:%M') if r['created_at'] else ''
    cur.close()
    conn.close()
    return jsonify(rows)
@app.route('/api/patients/<int:pid>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_patient(pid):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    if request.method == 'GET':
        cur.execute("""
            SELECT p.*,
                   COALESCE(SUM(v.total_amount), 0)  AS total_billed,
                   COALESCE(SUM(v.paid_amount), 0)   AS total_paid,
                   COALESCE(SUM(v.total_amount - v.paid_amount), 0) AS total_due,
                   COUNT(v.id) AS visit_count
            FROM patients p
            LEFT JOIN visits v ON v.patient_id = p.id
            WHERE p.id = %s
            GROUP BY p.id
        """, (pid,))
        patient = cur.fetchone()
        if not patient:
            cur.close(); conn.close()
            return jsonify({'error': 'Patient not found'}), 404
        patient['total_billed'] = float(patient['total_billed'])
        patient['total_paid']   = float(patient['total_paid'])
        patient['total_due']    = float(patient['total_due'])
        patient['created_at']   = patient['created_at'].strftime('%Y-%m-%d %H:%M') if patient['created_at'] else ''
        cur.close(); conn.close()
        return jsonify(patient)
    if request.method == 'PUT':
        data = request.get_json()
        cur.execute("""
            UPDATE patients SET first_name=%s, last_name=%s, age=%s, gender=%s, phone=%s, address=%s
            WHERE id=%s
        """, (
            data['first_name'], data['last_name'], int(data['age']),
            data['gender'], data.get('phone', ''), data.get('address', ''), pid
        ))
        cur.close(); conn.close()
        return jsonify({'success': True})
    if request.method == 'DELETE':
        cur.execute("DELETE FROM patients WHERE id = %s", (pid,))
        cur.close(); conn.close()
        return jsonify({'success': True})

# ── API: Visits ────────────────────────────────────────────────────────────────
@app.route('/api/patients/<int:pid>/visits', methods=['GET', 'POST'])
@login_required
def api_visits(pid):
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    if request.method == 'GET':
        cur.execute("""
            SELECT * FROM visits WHERE patient_id = %s ORDER BY visit_date DESC, created_at DESC
        """, (pid,))
        rows = cur.fetchall()
        for r in rows:
            r['total_amount'] = float(r['total_amount'])
            r['paid_amount']  = float(r['paid_amount'])
            r['due_amount']   = round(r['total_amount'] - r['paid_amount'], 2)
            r['visit_date']   = r['visit_date'].strftime('%Y-%m-%d') if r['visit_date'] else ''
            r['created_at']   = r['created_at'].strftime('%Y-%m-%d %H:%M') if r['created_at'] else ''
        cur.close(); conn.close()
        return jsonify(rows)

    # POST
    data = request.get_json()
    total  = float(data.get('total_amount', 0))
    paid   = float(data.get('paid_amount', 0))
    vdate  = data.get('visit_date') or date.today().isoformat()

    cur.execute("""
        INSERT INTO visits (patient_id, visit_date, complaint, diagnosis, treatment, total_amount, paid_amount)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (pid, vdate, data.get('complaint',''), data.get('diagnosis',''),
          data.get('treatment',''), total, paid))
    new_id = cur.lastrowid
    cur.close(); conn.close()
    return jsonify({'success': True, 'id': new_id}), 201


@app.route('/api/visits/<int:vid>', methods=['PUT', 'DELETE'])
@login_required
def api_visit(vid):
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    if request.method == 'PUT':
        data   = request.get_json()
        total  = float(data.get('total_amount', 0))
        paid   = float(data.get('paid_amount', 0))
        cur.execute("""
            UPDATE visits SET visit_date=%s, complaint=%s, diagnosis=%s, treatment=%s,
                              total_amount=%s, paid_amount=%s
            WHERE id=%s
        """, (data.get('visit_date'), data.get('complaint',''), data.get('diagnosis',''),
              data.get('treatment',''), total, paid, vid))
        cur.close(); conn.close()
        return jsonify({'success': True})

    if request.method == 'DELETE':
        cur.execute("DELETE FROM visits WHERE id = %s", (vid,))
        cur.close(); conn.close()
        return jsonify({'success': True})


# ── API: Due Report ────────────────────────────────────────────────────────────
@app.route('/api/due-report')
@login_required
def api_due_report():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT p.id, p.first_name, p.last_name, p.phone,
               COALESCE(SUM(v.total_amount), 0)                  AS total_billed,
               COALESCE(SUM(v.paid_amount), 0)                   AS total_paid,
               COALESCE(SUM(v.total_amount - v.paid_amount), 0)  AS total_due,
               COUNT(v.id) AS visit_count,
               MAX(v.visit_date) AS last_visit
        FROM patients p
        JOIN visits v ON v.patient_id = p.id
        GROUP BY p.id
        HAVING total_due > 0
        ORDER BY total_due DESC
    """)
    rows = cur.fetchall()
    for r in rows:
        r['total_billed'] = float(r['total_billed'])
        r['total_paid']   = float(r['total_paid'])
        r['total_due']    = float(r['total_due'])
        r['last_visit']   = r['last_visit'].strftime('%Y-%m-%d') if r['last_visit'] else ''
    cur.close(); conn.close()
    return jsonify(rows)
# code is added for password setting
@app.route('/api/change-password', methods=['POST'])
@login_required
def api_change_password():
    data = request.get_json()
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    if not current_password or not new_password or not confirm_password:
        return jsonify({'success': False, 'message': 'All fields are required'}), 400

    if new_password != confirm_password:
        return jsonify({'success': False, 'message': 'New passwords do not match'}), 400

    if len(new_password) < 6:
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters'}), 400

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cur.fetchone()

    if not user or not bcrypt.check_password_hash(user['password'], current_password):
        cur.close(); conn.close()
        return jsonify({'success': False, 'message': 'Current password is incorrect'}), 401

    hashed = bcrypt.generate_password_hash(new_password).decode('utf-8')
    cur.execute("UPDATE users SET password = %s WHERE id = %s", (hashed, session['user_id']))
    cur.close(); conn.close()
    return jsonify({'success': True, 'message': 'Password changed successfully'})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)

# # extra code for run and get browser on one click [pyinstaller --onefile app.py]
# import webbrowser
# import threading

# def open_browser():
#     webbrowser.open("http://127.0.0.1:5000")

# if __name__ == "__main__":
#     threading.Timer(1, open_browser).start()
#     app.run(host="127.0.0.1", port=5000)

# @app.route('/test')
# def test():
#     return render_template("login.html")