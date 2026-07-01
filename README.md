# Social Media Content Planner

A web-based content planning system for small businesses built with Flask, SQLite for local development, and PostgreSQL on Render for deployment.

## Features

- User registration and login
- Profile and settings dropdown
- Campaign management
- Post creation, editing, deletion
- Search, filter, pagination, and CSV export
- Calendar view with date-range filtering
- Dashboard summary cards and chart
- Responsive split-screen login/register pages
- Light and dark theme support

## Technology Stack

- Python
- Flask
- Flask-SQLAlchemy
- Flask-Login
- SQLite
- PostgreSQL
- Bootstrap 5
- Chart.js
- Gunicorn
- Render

## Project Structure

```text
app/
├── __init__.py
├── config.py
├── models.py
├── routes/
│   └── main.py
├── templates/
└── static/
    └── css/
        └── style.css
database/
tests/
run.py
requirements.txt
.python-version
```

## Local Setup

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```

### 2. Create a virtual environment
```bash
python -m venv .venv
```

### 3. Activate the virtual environment

**Git Bash**
```bash
source .venv/Scripts/activate
```

**PowerShell**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Command Prompt**
```cmd
.\.venv\Scripts\activate.bat
```

### 4. Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Run the application
```bash
python run.py
```

Open:
```text
http://127.0.0.1:5000
```

## Database

The app uses SQLite locally and PostgreSQL in production.

If needed, the Flask config reads the connection string from:
```text
DATABASE_URL
```

For Render, use the internal PostgreSQL connection string from your Render database settings.

## Deployment on Render

### Build Command
```bash
pip install -r requirements.txt
```

### Start Command
```bash
gunicorn run:app --bind 0.0.0.0:$PORT
```

### Environment Variables
Set these in Render:

- `SECRET_KEY`
- `DATABASE_URL`
- `PYTHON_VERSION` (optional if using `.python-version`)

## Updating the Project

When you change the README or stylesheet, commit and push the files to GitHub:

```bash
git add README.md app/static/css/style.css
git commit -m "Update README and responsive styling"
git push origin main
```

If your stylesheet file is currently named `style_updated.css`, rename or copy it to `app/static/css/style.css` before committing.

## Notes

- The application is responsive for mobile view.
- The login and register screens use a split-screen design on desktop and stack on smaller screens.
- The profile dropdown includes Profile, Settings, and Logout actions.
