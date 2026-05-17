"""
Bengal RAWR — ML Event Classifier (Phase 2)
Logistic Regression classifier trained on labeled syllabus lines
to improve event extraction accuracy beyond keyword matching.

Training data is stored in the database and can be bootstrapped
from human-corrected events.
"""

import os
import re
import logging
import pickle
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Model persistence path
MODEL_PATH = Path(__file__).parent / 'trained_model.pkl'
VECTORIZER_PATH = Path(__file__).parent / 'vectorizer.pkl'

# ─────────────────────────────────────────────────────
# Feature engineering
# ─────────────────────────────────────────────────────

FEATURE_KEYWORDS = [
    'due', 'submit', 'deadline', 'exam', 'quiz', 'test',
    'midterm', 'final', 'assignment', 'homework', 'hw',
    'project', 'presentation', 'paper', 'report', 'lab',
    'reading', 'chapter', 'week', '%', 'points', 'grade',
    'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
    'january', 'february', 'march', 'april', 'may', 'june',
    'july', 'august', 'september', 'october', 'november', 'december',
]

DATE_HINT_PATTERN = re.compile(
    r'\b(\d{1,2}[/-]\d{1,2}|\w+\s\d{1,2}(?:,\s*\d{4})?)\b',
    re.IGNORECASE
)


def extract_features(line: str) -> dict:
    """
    Hand-crafted feature extraction for a single text line.
    Returns a feature dict for the vectorizer.
    """
    line_lower = line.lower()
    features = {}

    # Keyword presence features
    for kw in FEATURE_KEYWORDS:
        features[f'has_{kw.replace(" ", "_")}'] = int(kw in line_lower)

    # Structural features
    features['line_length'] = len(line)
    features['word_count'] = len(line.split())
    features['has_date_pattern'] = int(bool(DATE_HINT_PATTERN.search(line)))
    features['has_number'] = int(bool(re.search(r'\d+', line)))
    features['has_percent'] = int('%' in line)
    features['starts_with_bullet'] = int(bool(re.match(r'^\s*[-•*]\s+', line)))
    features['has_colon'] = int(':' in line)

    return features


def features_to_vector(features: dict, feature_names: list) -> list:
    """Convert feature dict to ordered list using known feature_names."""
    return [features.get(name, 0) for name in feature_names]


# ─────────────────────────────────────────────────────
# Bootstrap training data
# ─────────────────────────────────────────────────────

BOOTSTRAP_TRAINING_DATA = [
    # (line_text, label)
    ("Homework 3 due March 12", "assignment"),
    ("HW 4 due by Friday April 5", "homework"),
    ("Assignment 2 submit before midnight", "assignment"),
    ("Midterm Exam - Week 8", "midterm"),
    ("MIDTERM: October 15th in class", "midterm"),
    ("Final Exam - December 18, 2026", "final"),
    ("Comprehensive Final: May 2", "final"),
    ("Quiz 1 on Chapter 3 — Feb 14", "quiz"),
    ("In-class quiz every Monday", "quiz"),
    ("Project proposal due March 1", "project"),
    ("Group project final submission April 20", "project"),
    ("Presentation: Week 13", "presentation"),
    ("Student presentations March 28-30", "presentation"),
    ("Lab report due Sunday night", "lab"),
    ("Lab 4 due before next session", "lab"),
    ("Read Chapter 5 for Tuesday", "reading"),
    ("Reading: pp. 44-88 before class", "reading"),
    ("Office hours: Tuesdays 2-4pm", "none"),
    ("Course description: Introduction to CS", "none"),
    ("Professor: Dr. Smith", "none"),
    ("Textbook: Operating Systems, 3rd ed.", "none"),
    ("Class meets MWF 10am-11am", "none"),
    ("Syllabus subject to change", "none"),
    ("Week 1: Introduction and overview", "none"),
    ("Grading breakdown: Exams 50%", "none"),
]


class EventClassifier:
    """
    Scikit-learn based event classifier.
    Falls back to keyword matching if model not trained.
    """

    EVENT_LABELS = ['none', 'homework', 'assignment', 'quiz', 'project',
                    'presentation', 'midterm', 'exam', 'final', 'lab', 'reading']

    def __init__(self):
        self.model = None
        self.feature_names = None
        self.is_trained = False
        self._try_load_model()

    def _try_load_model(self):
        """Load pre-trained model from disk if available."""
        if MODEL_PATH.exists() and VECTORIZER_PATH.exists():
            try:
                with open(MODEL_PATH, 'rb') as f:
                    self.model = pickle.load(f)
                with open(VECTORIZER_PATH, 'rb') as f:
                    self.feature_names = pickle.load(f)
                self.is_trained = True
                logger.info("ML classifier loaded from disk")
            except Exception as e:
                logger.warning(f"Could not load ML model: {e}")

    def train(self, training_data: list = None):
        """
        Train the Logistic Regression classifier.

        Args:
            training_data: List of (text_line, label) tuples.
                           Defaults to bootstrap data.
        """
        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.preprocessing import LabelEncoder
        except ImportError:
            logger.error("scikit-learn not installed: pip install scikit-learn")
            return False

        data = training_data or BOOTSTRAP_TRAINING_DATA

        if len(data) < 10:
            logger.warning("Too little training data — skipping ML training")
            return False

        # Build feature matrix
        all_features = [extract_features(line) for line, _ in data]
        self.feature_names = sorted(set(k for f in all_features for k in f.keys()))

        X = [features_to_vector(f, self.feature_names) for f in all_features]
        y = [label for _, label in data]

        # Train model
        self.model = LogisticRegression(
            max_iter=1000,
            class_weight='balanced',
            solver='lbfgs',
            multi_class='multinomial',
        )
        self.model.fit(X, y)
        self.is_trained = True

        # Persist to disk
        try:
            with open(MODEL_PATH, 'wb') as f:
                pickle.dump(self.model, f)
            with open(VECTORIZER_PATH, 'wb') as f:
                pickle.dump(self.feature_names, f)
            logger.info(f"ML model trained on {len(data)} samples and saved")
        except Exception as e:
            logger.warning(f"Could not save ML model: {e}")

        return True

    def predict(self, line: str) -> Optional[str]:
        """
        Predict event type for a text line.
        Returns label string, or None if model not ready.
        """
        if not self.is_trained or not self.model:
            return None

        try:
            features = extract_features(line)
            x = [features_to_vector(features, self.feature_names)]
            prediction = self.model.predict(x)[0]
            if prediction == 'none':
                return None
            return prediction
        except Exception as e:
            logger.debug(f"ML prediction failed: {e}")
            return None

    def predict_proba(self, line: str) -> dict:
        """Return confidence scores for each label."""
        if not self.is_trained or not self.model:
            return {}

        try:
            features = extract_features(line)
            x = [features_to_vector(features, self.feature_names)]
            proba = self.model.predict_proba(x)[0]
            return dict(zip(self.model.classes_, proba))
        except Exception as e:
            logger.debug(f"ML proba failed: {e}")
            return {}

    def retrain_from_db(self):
        """
        Pull verified events from the database and retrain.
        Call this periodically to improve the model as users correct events.
        """
        try:
            # Import here to avoid circular imports
            from apps.events.models import Event

            db_events = Event.objects.filter(is_verified=True).values('raw_line', 'event_type')
            training_data = [(e['raw_line'], e['event_type']) for e in db_events if e['raw_line']]

            if training_data:
                all_data = BOOTSTRAP_TRAINING_DATA + training_data
                return self.train(all_data)
        except Exception as e:
            logger.warning(f"DB retraining failed: {e}")
        return False


# Module-level singleton
_classifier_instance = None


def get_classifier() -> EventClassifier:
    """Return (and lazily initialize) the module-level classifier."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = EventClassifier()
        if not _classifier_instance.is_trained:
            _classifier_instance.train()  # Bootstrap from default data
    return _classifier_instance
