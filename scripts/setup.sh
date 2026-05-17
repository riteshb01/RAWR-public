#!/bin/bash
# ============================================================
# Bengal RAWR — Full Setup Script
# Run this once after cloning the repo
# ============================================================
set -e

echo ""
echo "🐯 BENGAL RAWR — Setup Script"
echo "=============================="
echo ""

# ── Colors ──────────────────────────────────────────────────
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

step() { echo -e "${BLUE}[STEP]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC}   $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERR]${NC}  $1"; }

# ── Check Python ────────────────────────────────────────────
step "Checking Python 3.10+ ..."
python3 --version || { err "Python 3 not found. Install Python 3.10+."; exit 1; }
ok "Python found"

# ── Create virtual environment ──────────────────────────────
step "Creating virtual environment ..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    ok "venv created"
else
    warn "venv already exists, skipping"
fi

# ── Activate venv ──────────────────────────────────────────
step "Activating venv ..."
source venv/bin/activate
ok "venv activated"

# ── Install dependencies ───────────────────────────────────
step "Installing Python dependencies (this may take a minute) ..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
ok "Dependencies installed"

# ── Download spaCy model ───────────────────────────────────
step "Downloading spaCy English model ..."
python -m spacy download en_core_web_sm --quiet
ok "spaCy model ready"

# ── Create Django directories ──────────────────────────────
step "Creating required directories ..."
mkdir -p backend/logs
mkdir -p backend/media/syllabi
mkdir -p backend/staticfiles
ok "Directories created"

# ── Django setup ───────────────────────────────────────────
cd backend

step "Running Django migrations ..."
python manage.py migrate --run-syncdb
ok "Migrations applied"

step "Creating Django superuser (admin/admin) ..."
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@bengalrawr.local', 'admin')
    print('Superuser created: admin / admin')
else:
    print('Superuser already exists')
"
ok "Superuser ready"

step "Collecting static files ..."
python manage.py collectstatic --noinput --quiet
ok "Static files collected"

cd ..

# ── Frontend setup ─────────────────────────────────────────
step "Setting up React frontend ..."
if command -v node &> /dev/null; then
    cd frontend
    if [ ! -d "node_modules" ]; then
        npm install --silent
        ok "npm packages installed"
    else
        warn "node_modules exists, skipping npm install"
    fi
    cd ..
else
    warn "Node.js not found — skipping frontend setup"
    warn "Install Node.js 18+ and run: cd frontend && npm install"
fi

# ── Done ───────────────────────────────────────────────────
echo ""
echo "=============================="
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "To start the system:"
echo ""
echo "  Backend:   source venv/bin/activate && cd backend && python manage.py runserver"
echo "  Frontend:  cd frontend && npm start"
echo ""
echo "  Django Admin:  http://localhost:8000/admin  (admin / admin)"
echo "  API Root:      http://localhost:8000/api/v1/"
echo "  Frontend:      http://localhost:3000"
echo ""
