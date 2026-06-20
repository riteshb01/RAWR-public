"""
Tests for the Conflict Detection Engine — weekly overload, exam collision,
daily overload, consecutive weeks, edge cases.
"""
import pytest
from datetime import date

from core.nlp_engine.conflict_detector import (
    ConflictDetectionEngine,
    get_iso_week_key,
    get_week_start,
    get_week_end,
)


# ─────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────

class TestHelperFunctions:
    """Tests for ISO week key and week boundary calculations."""

    def test_iso_week_key_format(self):
        key = get_iso_week_key(date(2026, 3, 12))
        assert key.startswith("2026-W")
        assert len(key) == 8  # e.g. "2026-W11"

    def test_week_start_is_monday(self):
        # March 12, 2026 is a Thursday
        monday = get_week_start(date(2026, 3, 12))
        assert monday.weekday() == 0  # Monday
        assert monday == date(2026, 3, 9)

    def test_week_end_is_sunday(self):
        sunday = get_week_end(date(2026, 3, 12))
        assert sunday.weekday() == 6  # Sunday
        assert sunday == date(2026, 3, 15)

    def test_week_start_on_monday(self):
        monday = get_week_start(date(2026, 3, 9))
        assert monday == date(2026, 3, 9)

    def test_week_end_on_sunday(self):
        sunday = get_week_end(date(2026, 3, 15))
        assert sunday == date(2026, 3, 15)


# ─────────────────────────────────────────────────────
# ConflictDetectionEngine.analyze()
# ─────────────────────────────────────────────────────

class TestConflictDetectionEngine:
    """Tests for the main conflict analysis engine."""

    def setup_method(self):
        self.engine = ConflictDetectionEngine(
            weekly_threshold=7,
            critical_threshold=12,
            daily_threshold=5,
        )

    def test_empty_events(self):
        result = self.engine.analyze([])
        assert result['conflicts'] == []
        assert result['summary']['total_events'] == 0

    def test_no_conflicts_light_week(self):
        events = [
            {'date': date(2026, 3, 9), 'weight': 1, 'course': 'CS101', 'event_type': 'homework'},
            {'date': date(2026, 3, 10), 'weight': 2, 'course': 'CS101', 'event_type': 'quiz'},
        ]
        result = self.engine.analyze(events)
        weekly_conflicts = [c for c in result['conflicts'] if c['type'] == 'weekly_overload']
        assert len(weekly_conflicts) == 0

    def test_weekly_overload_warning(self):
        """Total weight 7+ in one week should trigger warning."""
        events = [
            {'date': date(2026, 3, 9), 'weight': 5, 'course': 'CS101', 'event_type': 'midterm'},
            {'date': date(2026, 3, 11), 'weight': 2, 'course': 'CS201', 'event_type': 'quiz'},
        ]
        result = self.engine.analyze(events)
        weekly_conflicts = [c for c in result['conflicts'] if c['type'] == 'weekly_overload']
        assert len(weekly_conflicts) == 1
        assert weekly_conflicts[0]['severity'] == 'warning'
        assert weekly_conflicts[0]['total_load'] == 7

    def test_weekly_overload_critical(self):
        """Total weight 12+ in one week should trigger critical."""
        events = [
            {'date': date(2026, 3, 9), 'weight': 5, 'course': 'CS101', 'event_type': 'midterm'},
            {'date': date(2026, 3, 10), 'weight': 5, 'course': 'CS201', 'event_type': 'exam'},
            {'date': date(2026, 3, 11), 'weight': 3, 'course': 'CS301', 'event_type': 'project'},
        ]
        result = self.engine.analyze(events)
        weekly_conflicts = [c for c in result['conflicts'] if c['type'] == 'weekly_overload']
        assert len(weekly_conflicts) == 1
        assert weekly_conflicts[0]['severity'] == 'critical'
        assert weekly_conflicts[0]['total_load'] == 13

    def test_cross_course_exam_collision(self):
        """Two exams from different courses on the same day should trigger collision."""
        events = [
            {'date': date(2026, 3, 10), 'weight': 5, 'course': 'CS101', 'event_type': 'midterm'},
            {'date': date(2026, 3, 10), 'weight': 5, 'course': 'CS201', 'event_type': 'exam'},
        ]
        result = self.engine.analyze(events)
        collisions = [c for c in result['conflicts'] if c['type'] == 'exam_collision']
        assert len(collisions) == 1
        assert set(collisions[0]['courses']) == {'CS101', 'CS201'}

    def test_no_collision_same_course(self):
        """Two exams from the SAME course on the same day should NOT be a collision."""
        events = [
            {'date': date(2026, 3, 10), 'weight': 5, 'course': 'CS101', 'event_type': 'midterm'},
            {'date': date(2026, 3, 10), 'weight': 2, 'course': 'CS101', 'event_type': 'quiz'},
        ]
        result = self.engine.analyze(events)
        collisions = [c for c in result['conflicts'] if c['type'] == 'exam_collision']
        assert len(collisions) == 0

    def test_daily_overload(self):
        """5+ weight points on a single day should trigger daily overload."""
        events = [
            {'date': date(2026, 3, 10), 'weight': 5, 'course': 'CS101', 'event_type': 'midterm'},
            {'date': date(2026, 3, 10), 'weight': 2, 'course': 'CS201', 'event_type': 'quiz'},
        ]
        result = self.engine.analyze(events)
        daily = [c for c in result['conflicts'] if c['type'] == 'daily_overload']
        assert len(daily) == 1

    def test_consecutive_heavy_weeks(self):
        """2+ consecutive heavy weeks should trigger consecutive overload."""
        events = [
            # Week 1 heavy
            {'date': date(2026, 3, 9), 'weight': 5, 'course': 'CS101', 'event_type': 'midterm'},
            {'date': date(2026, 3, 11), 'weight': 3, 'course': 'CS201', 'event_type': 'project'},
            # Week 2 heavy
            {'date': date(2026, 3, 16), 'weight': 5, 'course': 'CS101', 'event_type': 'exam'},
            {'date': date(2026, 3, 18), 'weight': 3, 'course': 'CS301', 'event_type': 'presentation'},
        ]
        result = self.engine.analyze(events)
        consecutive = [c for c in result['conflicts'] if c['type'] == 'consecutive_overload']
        assert len(consecutive) >= 1

    def test_events_without_dates_excluded(self):
        """Events with date=None should be excluded from analysis."""
        events = [
            {'date': None, 'weight': 5, 'course': 'CS101', 'event_type': 'midterm'},
            {'date': date(2026, 3, 10), 'weight': 1, 'course': 'CS101', 'event_type': 'homework'},
        ]
        result = self.engine.analyze(events)
        assert result['summary']['total_events'] == 1
        assert result['summary']['events_without_date'] == 1

    def test_summary_stats(self):
        """Summary should contain correct aggregate statistics."""
        events = [
            {'date': date(2026, 3, 9), 'weight': 5, 'course': 'CS101', 'event_type': 'midterm'},
            {'date': date(2026, 3, 10), 'weight': 3, 'course': 'CS201', 'event_type': 'project'},
            {'date': date(2026, 4, 6), 'weight': 1, 'course': 'CS101', 'event_type': 'homework'},
        ]
        result = self.engine.analyze(events)
        summary = result['summary']
        assert summary['total_events'] == 3
        assert summary['total_weeks_tracked'] == 2
        assert summary['max_weekly_load'] == 8  # week with midterm + project

    def test_courses_affected_tracked(self):
        """Conflict records should list which courses contribute to the overload."""
        events = [
            {'date': date(2026, 3, 9), 'weight': 5, 'course': 'CS101', 'event_type': 'midterm'},
            {'date': date(2026, 3, 11), 'weight': 3, 'course': 'MATH311', 'event_type': 'presentation'},
        ]
        result = self.engine.analyze(events)
        weekly = [c for c in result['conflicts'] if c['type'] == 'weekly_overload']
        if weekly:
            assert 'CS101' in weekly[0]['courses_affected']
            assert 'MATH311' in weekly[0]['courses_affected']


# ─────────────────────────────────────────────────────
# Heatmap data generation
# ─────────────────────────────────────────────────────

class TestHeatmapGeneration:
    """Tests for heatmap data output."""

    def setup_method(self):
        self.engine = ConflictDetectionEngine()

    def test_heatmap_daily_aggregation(self):
        events = [
            {'date': date(2026, 3, 10), 'weight': 3, 'course': 'CS101', 'event_type': 'project'},
            {'date': date(2026, 3, 10), 'weight': 2, 'course': 'CS201', 'event_type': 'quiz'},
            {'date': date(2026, 3, 12), 'weight': 1, 'course': 'CS101', 'event_type': 'homework'},
        ]
        heatmap = self.engine.generate_heatmap_data(events)
        assert heatmap['2026-03-10'] == 5  # 3 + 2
        assert heatmap['2026-03-12'] == 1

    def test_heatmap_skips_undated_events(self):
        events = [
            {'date': None, 'weight': 5, 'course': 'CS101', 'event_type': 'midterm'},
        ]
        heatmap = self.engine.generate_heatmap_data(events)
        assert len(heatmap) == 0

    def test_heatmap_empty_events(self):
        heatmap = self.engine.generate_heatmap_data([])
        assert heatmap == {}
