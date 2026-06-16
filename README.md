# MediTrack — Doctor Patient Management System

A clean, secure, full-stack clinic management system built with **Flask + MySQL**.

## Features
- 🔐 Secure doctor login (bcrypt hashed passwords)
- 👥 Patient registry with auto-increment serial numbers
- 📋 Full visit/medical record tracking per patient
- 💰 Payment tracking with automatic due calculation
- 🔍 Real-time patient search by first/last name
- 📊 Dashboard with revenue, dues, and visit stats
- ⚠️ Highlighted patients with pending dues

---

## Project Structure

```
clinic/
├── app.py                  # Flask application (all routes + APIs)
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
├── static/
│   ├── css/main.css        # All styles
│   └── js/app.js           # Shared JS utilities
└── templates/
    ├── base.html           # Navigation + layout
    ├── login.html          # Login page
    ├── dashboard.html      # Main dashboard
    ├── patients.html       # Patient list + search
    └── patient_detail.html # Individual patient + visits
```

---

## Setup Instructions

### 1. Prerequisites
- Python 3.9+
- MySQL 8.0+

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate          # Linux/Mac
venv\Scripts\activate             # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
# Edit .env with your MySQL credentials

```

### 5. Set Up MySQL
cd C:\Program Files\MySQL\MySQL Server 8.0\bin
mysql -u root -p

```sql
-- Run in MySQL shell (the app auto-creates the database and tables)
CREATE USER 'clinic_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON clinic_db.* TO 'clinic_user'@'localhost';
FLUSH PRIVILEGES;
```

### 6. Run the Application
```bash
python app.py
```

Visit: http://localhost:5000

**Default credentials:**
- Username: `admin`
- Password: `clinic123`

> ⚠️ Change the default password immediately in production!

---

## API Reference

| Method | Endpoint                          | Description              |
|--------|-----------------------------------|--------------------------|
| GET    | `/api/stats`                      | Dashboard statistics     |
| GET    | `/api/patients`                   | List all patients        |
| GET    | `/api/patients?search=name`       | Search patients by name  |
| POST   | `/api/patients`                   | Add new patient          |
| GET    | `/api/patients/<id>`              | Get patient details      |
| PUT    | `/api/patients/<id>`              | Update patient info      |
| DELETE | `/api/patients/<id>`              | Delete patient           |
| GET    | `/api/patients/<id>/visits`       | Get all visits           |
| POST   | `/api/patients/<id>/visits`       | Add visit record         |
| PUT    | `/api/visits/<id>`                | Update visit             |
| DELETE | `/api/visits/<id>`                | Delete visit             |
| GET    | `/api/due-report`                 | Patients with pending dues|

---

## Security Notes
- All routes protected by session-based authentication
- Passwords hashed with bcrypt
- SQL injection prevention via parameterized queries
- Change `SECRET_KEY` in production (use a 32+ char random string)
- Run behind a reverse proxy (nginx) in production
- Use HTTPS in production

## Production Deployment
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```
