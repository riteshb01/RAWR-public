# 🐯 Bengal RAWR

Bengal RAWR is an academic conflict and workload detection system. It automatically parses course syllabi, extracts course task deadlines (such as homework, quizzes, and exams), identifies student workload bottlenecks (overloaded weeks or back-to-back exams), and visualizes the results on an interactive dashboard.

---

## 🏗️ Project Architecture

The project is structured as follows:

```
bengal_rawr/
├── backend/                   # Django REST Framework backend application
│   ├── backend/               # Project configuration files
│   ├── apps/
│   │   └── syllabus/          # Core Django application containing models, views, and tests
│   └── core/                  # Processing engines (NLP engine, parser, classifier)
├── frontend/                  # React dashboard client (Create React App)
├── requirements.txt           # Python backend dependencies
└── venv/                      # Python virtual environment
```

---

## 🚀 Getting Started

### Backend Setup

1. **Activate the Virtual Environment:**
   ```bash
   source venv/bin/python
   # or simply use the environment interpreter
   ```

2. **Run Django Database Migrations:**
   ```bash
   cd backend
   python manage.py migrate
   ```

3. **Start the Development Server:**
   ```bash
   python manage.py runserver
   ```

### Running Tests

We have a comprehensive test suite of **129 tests** covering NLP engines, document parsing, conflict detection, models, and API views. To run the tests, execute:

```bash
cd backend
python -m pytest apps/syllabus/tests/ -v
```

---

## 📈 Project Status & Roadmap

To read a detailed, non-technical overview of the achievements and the upcoming roadmap, please refer to:
* [Project Status Summary](file:///Users/riteshbastola/.gemini/antigravity-ide/brain/d54c7567-36da-4bb7-88e7-580bc0bf532c/project_status_summary.md)
