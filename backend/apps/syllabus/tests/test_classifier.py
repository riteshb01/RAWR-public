"""
Tests for the ML Event Classifier — training, prediction, feature extraction.
"""
import pytest

from core.event_classifier.classifier import (
    EventClassifier,
    extract_features,
    features_to_vector,
    get_classifier,
    BOOTSTRAP_TRAINING_DATA,
)


# ─────────────────────────────────────────────────────
# Feature extraction
# ─────────────────────────────────────────────────────

class TestFeatureExtraction:
    """Tests for hand-crafted feature engineering."""

    def test_keyword_features(self):
        features = extract_features("Midterm exam due March 12")
        assert features['has_exam'] == 1
        assert features['has_midterm'] == 1
        assert features['has_due'] == 1

    def test_structural_features(self):
        features = extract_features("- Assignment 2: 20% of grade")
        assert features['line_length'] > 0
        assert features['word_count'] > 0
        assert features['has_colon'] == 1
        assert features['has_percent'] == 1
        assert features['starts_with_bullet'] == 1

    def test_date_pattern_feature(self):
        features = extract_features("Quiz on 3/12")
        assert features['has_date_pattern'] == 1

    def test_no_keywords_for_generic_line(self):
        features = extract_features("This is the course description")
        assert features['has_exam'] == 0
        assert features['has_midterm'] == 0
        assert features['has_quiz'] == 0

    def test_features_to_vector_ordering(self):
        features = {'a': 1, 'b': 0, 'c': 1}
        names = ['a', 'b', 'c']
        vec = features_to_vector(features, names)
        assert vec == [1, 0, 1]

    def test_features_to_vector_missing_keys(self):
        features = {'a': 1}
        names = ['a', 'b', 'c']
        vec = features_to_vector(features, names)
        assert vec == [1, 0, 0]


# ─────────────────────────────────────────────────────
# EventClassifier
# ─────────────────────────────────────────────────────

class TestEventClassifier:
    """Tests for the ML classifier training and prediction."""

    def test_train_with_bootstrap_data(self):
        classifier = EventClassifier()
        success = classifier.train()
        assert success is True
        assert classifier.is_trained is True
        assert classifier.model is not None

    def test_predict_after_training(self):
        classifier = EventClassifier()
        classifier.train()
        prediction = classifier.predict("Midterm Exam March 15")
        assert prediction is not None
        assert prediction in classifier.EVENT_LABELS

    def test_predict_returns_none_when_untrained(self):
        classifier = EventClassifier()
        classifier.is_trained = False
        classifier.model = None
        result = classifier.predict("Midterm Exam")
        assert result is None

    def test_predict_proba_returns_dict(self):
        classifier = EventClassifier()
        classifier.train()
        proba = classifier.predict_proba("Quiz on Chapter 3")
        assert isinstance(proba, dict)
        assert len(proba) > 0
        # Probabilities should sum to ~1.0
        total = sum(proba.values())
        assert abs(total - 1.0) < 0.01

    def test_predict_proba_untrained_returns_empty(self):
        classifier = EventClassifier()
        classifier.is_trained = False
        classifier.model = None
        result = classifier.predict_proba("anything")
        assert result == {}

    def test_too_little_training_data_fails(self):
        classifier = EventClassifier()
        success = classifier.train(training_data=[("one", "label")])
        assert success is False

    def test_none_line_classified_correctly(self):
        """Lines like 'Office hours: Tuesdays 2-4pm' should return None (classified as 'none')."""
        classifier = EventClassifier()
        classifier.train()
        result = classifier.predict("Office hours: Tuesdays 2-4pm")
        # 'none' predictions are returned as None
        assert result is None

    def test_bootstrap_data_has_enough_samples(self):
        assert len(BOOTSTRAP_TRAINING_DATA) >= 10


# ─────────────────────────────────────────────────────
# get_classifier() singleton
# ─────────────────────────────────────────────────────

class TestGetClassifier:
    """Tests for the module-level classifier singleton."""

    def test_returns_trained_classifier(self):
        classifier = get_classifier()
        assert classifier is not None
        assert classifier.is_trained is True

    def test_returns_same_instance(self):
        c1 = get_classifier()
        c2 = get_classifier()
        assert c1 is c2
