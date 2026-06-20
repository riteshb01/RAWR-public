"""
Tests for Django Models — Course, SyllabusFile, Event, ConflictWeek, AnalysisSession.
Uses pytest-django markers for database access.
"""
import pytest
from datetime import date

from apps.syllabus.models import Course, SyllabusFile, Event, ConflictWeek, AnalysisSession


# ─────────────────────────────────────────────────────
# Course model
# ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCourseModel:

    def test_create_course(self):
        course = Course.objects.create(
            name="Introduction to Computer Science",
            code="CS101",
            professor="Dr. Zhang",
            semester="Spring 2026",
        )
        assert course.pk is not None
        assert course.name == "Introduction to Computer Science"
        assert course.code == "CS101"

    def test_course_str_with_code(self):
        course = Course.objects.create(name="Algorithms", code="CS301")
        assert "CS301" in str(course)
        assert "Algorithms" in str(course)

    def test_course_str_without_code(self):
        course = Course.objects.create(name="Algorithms", code="")
        assert str(course) == "Algorithms"

    def test_course_ordering(self):
        c1 = Course.objects.create(name="First", code="CS100")
        c2 = Course.objects.create(name="Second", code="CS200")
        courses = list(Course.objects.all())
        # Ordered by -created_at, so second created should appear first
        assert courses[0] == c2

    def test_course_created_by_nullable(self):
        course = Course.objects.create(name="Test", code="T100", created_by=None)
        assert course.created_by is None


# ─────────────────────────────────────────────────────
# Event model
# ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestEventModel:

    def setup_method(self):
        self.course = Course.objects.create(name="CS 101", code="CS101")

    def test_create_event_with_date(self):
        event = Event.objects.create(
            course=self.course,
            title="Midterm Exam",
            event_type="midterm",
            date=date(2026, 3, 15),
            workload=5,
        )
        assert event.pk is not None
        assert event.date == date(2026, 3, 15)
        assert event.workload == 5

    def test_create_event_without_date(self):
        event = Event.objects.create(
            course=self.course,
            title="Weekly Quiz",
            event_type="quiz",
            date=None,
            workload=2,
        )
        assert event.date is None

    def test_week_number_property(self):
        event = Event.objects.create(
            course=self.course,
            title="Test",
            event_type="exam",
            date=date(2026, 3, 15),
            workload=5,
        )
        assert event.week_number is not None
        assert isinstance(event.week_number, int)

    def test_week_number_none_when_no_date(self):
        event = Event.objects.create(
            course=self.course,
            title="Test",
            event_type="exam",
            date=None,
            workload=5,
        )
        assert event.week_number is None

    def test_iso_week_key_property(self):
        event = Event.objects.create(
            course=self.course,
            title="Test",
            event_type="exam",
            date=date(2026, 3, 15),
            workload=5,
        )
        assert event.iso_week_key is not None
        assert event.iso_week_key.startswith("2026-W")

    def test_event_str(self):
        event = Event.objects.create(
            course=self.course,
            title="Midterm",
            event_type="midterm",
            date=date(2026, 3, 15),
            workload=5,
        )
        s = str(event)
        assert "Midterm" in s
        assert "CS101" in s

    def test_event_is_verified_default_false(self):
        event = Event.objects.create(
            course=self.course,
            title="Test",
            event_type="homework",
            workload=1,
        )
        assert event.is_verified is False

    def test_filter_events_by_course(self):
        c2 = Course.objects.create(name="Math", code="MATH311")
        Event.objects.create(course=self.course, title="E1", event_type="quiz", workload=2)
        Event.objects.create(course=c2, title="E2", event_type="exam", workload=5)
        cs_events = Event.objects.filter(course=self.course)
        assert cs_events.count() == 1

    def test_filter_events_by_date_range(self):
        Event.objects.create(course=self.course, title="E1", event_type="quiz",
                             date=date(2026, 3, 10), workload=2)
        Event.objects.create(course=self.course, title="E2", event_type="exam",
                             date=date(2026, 5, 10), workload=5)
        march_events = Event.objects.filter(date__gte=date(2026, 3, 1), date__lte=date(2026, 3, 31))
        assert march_events.count() == 1


# ─────────────────────────────────────────────────────
# ConflictWeek model
# ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestConflictWeekModel:

    def test_create_conflict(self):
        conflict = ConflictWeek.objects.create(
            week_key="2026-W11",
            week_start=date(2026, 3, 9),
            week_end=date(2026, 3, 15),
            total_load=10,
            threshold=7,
            severity="warning",
            conflict_type="weekly_overload",
            courses_affected=["CS101", "MATH311"],
            message="Heavy week",
        )
        assert conflict.pk is not None
        assert conflict.severity == "warning"

    def test_conflict_unique_together(self):
        ConflictWeek.objects.create(
            week_key="2026-W11",
            conflict_type="weekly_overload",
            total_load=10,
        )
        with pytest.raises(Exception):  # IntegrityError
            ConflictWeek.objects.create(
                week_key="2026-W11",
                conflict_type="weekly_overload",
                total_load=15,
            )

    def test_conflict_str(self):
        conflict = ConflictWeek.objects.create(
            week_key="2026-W11",
            conflict_type="weekly_overload",
            total_load=10,
            severity="critical",
        )
        s = str(conflict)
        assert "2026-W11" in s
        assert "10" in s


# ─────────────────────────────────────────────────────
# AnalysisSession model
# ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAnalysisSessionModel:

    def test_create_session(self):
        session = AnalysisSession.objects.create(
            status="completed",
            total_events=25,
            total_conflicts=3,
            max_weekly_load=15,
            avg_weekly_load=4.2,
        )
        assert session.pk is not None
        assert session.total_events == 25

    def test_session_str(self):
        session = AnalysisSession.objects.create(status="pending")
        assert "Pending" in str(session)
