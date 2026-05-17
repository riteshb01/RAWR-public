# 🐯 Bengal RAWR
### Academic Conflict Detection System
> Upload course syllabi → extract events → detect impossible weeks → visualize workload

---

## Architecture Overview

```
User Uploads Syllabi (PDF/TXT/DOCX)
        ↓
  Django Upload API  (POST /api/v1/upload-syllabus/)
        ↓
  Document Parser    (pdfplumber / pytesseract / python-docx)
        ↓
  NLP Event Engine   (spaCy + regex + dateparser)
        ↓
  ML Classifier      (scikit-learn Logistic Regression — Phase 2)
        ↓
  Event Structuring  (JSON events with workload weights)
        ↓
  Conflict Detection (Weekly threshold analysis)
        ↓
  Django Database    (SQLite → PostgreSQL in production)
        ↓
  React Dashboard    (Heatmap + Charts + Conflict Alerts)
```

---

## Quick Start

```bash
# 1. Clone & setup
git clone <repo>
cd bengal_rawr
bash scripts/setup.sh

# 2. Start Django backend
source venv/bin/activate
cd backend
python manage.py runserver

# 3. Start React frontend (separate terminal)
cd frontend
npm start

# 4. (Optional) Seed test data
cd backend
python manage.py seed_test_data
```

Open:
- **Frontend**: http://localhost:3000
- **Django Admin**: http://localhost:8000/admin (admin / admin)
- **API**: http://localhost:8000/api/v1/

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/upload-syllabus/` | Upload and process a syllabus file |
| `GET` | `/api/v1/courses/` | List all courses |
| `POST` | `/api/v1/courses/` | Create a course |
| `GET` | `/api/v1/events/` | List all events (supports filters) |
| `GET` | `/api/v1/events/?course_id=1` | Filter events by course |
| `GET` | `/api/v1/events/?event_type=midterm` | Filter by event type |
| `POST` | `/api/v1/events/<id>/verify/` | Mark event as human-verified |
| `GET` | `/api/v1/conflicts/` | List conflict weeks |
| `POST` | `/api/v1/conflicts/analyze/` | Re-run full conflict analysis |
| `GET` | `/api/v1/dashboard/` | Dashboard summary data |
| `GET` | `/api/v1/dashboard/heatmap/` | Full heatmap dataset |
| `GET` | `/api/v1/dashboard/weekly-workload/` | Weekly bar chart data |

### Upload Example (curl)
```bash
curl -X POST http://localhost:8000/api/v1/upload-syllabus/ \
  -F "file=@CS101_Syllabus.pdf" \
  -F "course_name=Introduction to Computer Science" \
  -F "course_code=CS101" \
  -F "professor=Dr. Zhang" \
  -F "semester=Spring 2026"
```

### Response
```json
{
  "status": "processed",
  "syllabus_id": 1,
  "course_id": 1,
  "course_name": "Introduction to Computer Science",
  "events_extracted": 12,
  "conflicts_detected": 2
}
```

---

## Workload Weight System

| Event Type | Weight |
|------------|--------|
| Homework / Reading | 1 |
| Assignment / Lab / Quiz | 2 |
| Presentation / Project | 3 |
| Midterm / Exam | 5 |
| Final Exam | 8 |

**Conflict threshold**: ≥ 7 points/week → Warning  
**Critical threshold**: ≥ 12 points/week → Critical 🔥

---

## Module Details

### Module 1 — Document Parser (`core/date_parser/document_parser.py`)
- Handles PDF (pdfplumber), TXT, DOCX
- OCR fallback via pytesseract for scanned PDFs
- Text cleaning: removes page numbers, headers, whitespace normalization

### Module 2 — NLP Engine (`core/nlp_engine/engine.py`)
- spaCy NER for DATE entity extraction (high recall)
- Regex date patterns (ISO, slashes, month names, ordinals)
- Keyword taxonomy for 10 event types
- Context window scanning (±2 lines) for orphaned dates

### Module 3 — Event Structuring
- Converts raw NLP output → structured JSON with course, type, date, weight
- Deduplication on (course, type, date) triple

### Module 4 — Conflict Detection (`core/nlp_engine/conflict_detector.py`)
- Weekly aggregation via ISO calendar weeks
- Daily aggregation for single-day overload detection
- Cross-course exam collision detection
- Consecutive heavy-week streak detection

### Module 5 — ML Classifier (`core/event_classifier/classifier.py`)
- Scikit-learn Logistic Regression on hand-crafted features
- Bootstrap training data built-in (27 labeled examples)
- Retrains from human-verified DB events via `retrain_from_db()`
- Persists model to disk (pickle)

### Module 6 — Django Backend
- DRF REST API with full CRUD
- Bulk event creation via `bulk_create`
- Atomic transactions for data integrity
- File validation: extension + 10MB size limit

### Module 7 — React Dashboard
- Heatmap (GitHub-contribution style, 26 weeks)
- Weekly bar chart with conflict indicators
- Stat cards: courses, events, conflicts, critical weeks
- Upcoming events panel (next 30 days)
- Drag-and-drop upload with progress feedback

---

## Project Structure

```
bengal_rawr/
├── backend/
│   ├── manage.py
│   ├── backend/
│   │   ├── settings.py
│   │   └── urls.py
│   ├── apps/
│   │   └── syllabus/          # Main app (models, views, serializers, admin)
│   │       ├── models.py      # Course, SyllabusFile, Event, ConflictWeek
│   │       ├── views.py       # All API views
│   │       ├── serializers.py # DRF serializers
│   │       ├── urls.py        # URL routing
│   │       └── admin.py       # Rich admin interface
│   └── core/
│       ├── nlp_engine/
│       │   ├── engine.py          # SyllabusNLPEngine
│       │   └── conflict_detector.py  # ConflictDetectionEngine
│       ├── date_parser/
│       │   └── document_parser.py    # DocumentParser (PDF/TXT/DOCX)
│       └── event_classifier/
│           └── classifier.py         # ML EventClassifier
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Full dashboard UI
│   │   └── index.js
│   └── public/index.html
├── requirements.txt
└── scripts/setup.sh
```

---

## Phase 2 Roadmap

- [ ] BERT fine-tuned event classifier
- [ ] Email/calendar export (ICS format)
- [ ] Multi-user authentication
- [ ] Celery async processing for large uploads
- [ ] PostgreSQL migration scripts
- [ ] Docker Compose for one-command deployment
- [ ] Study schedule suggestions based on conflict data
