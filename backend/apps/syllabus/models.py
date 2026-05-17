"""
Bengal RAWR — Django Models
Defines all database models for the academic schedule system.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator


# ─────────────────────────────────────────────
# Syllabus App Models
# ─────────────────────────────────────────────

class Course(models.Model):
    """Represents an uploaded academic course."""
    name = models.CharField(max_length=200, help_text="e.g. CS101 - Introduction to CS")
    code = models.CharField(max_length=20, blank=True, help_text="e.g. CS101")
    professor = models.CharField(max_length=200, blank=True)
    semester = models.CharField(max_length=50, blank=True, help_text="e.g. Spring 2026")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} — {self.name}" if self.code else self.name


class SyllabusFile(models.Model):
    """Represents an uploaded syllabus file linked to a course."""

    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='syllabus_files')
    file = models.FileField(
        upload_to='syllabi/%Y/%m/',
        validators=[FileExtensionValidator(['pdf', 'txt', 'docx'])],
    )
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0, help_text="Size in bytes")
    extracted_text = models.TextField(blank=True, help_text="Raw extracted text")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    error_message = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.original_filename} ({self.get_status_display()})"

    @property
    def file_extension(self):
        return self.original_filename.rsplit('.', 1)[-1].lower() if '.' in self.original_filename else ''


# ─────────────────────────────────────────────
# Events App Models
# ─────────────────────────────────────────────

class Event(models.Model):
    """Represents a single academic event extracted from a syllabus."""

    EVENT_TYPE_CHOICES = [
        ('homework', 'Homework'),
        ('assignment', 'Assignment'),
        ('quiz', 'Quiz'),
        ('presentation', 'Presentation'),
        ('project', 'Project'),
        ('midterm', 'Midterm'),
        ('exam', 'Exam'),
        ('final', 'Final Exam'),
        ('lab', 'Lab'),
        ('reading', 'Reading'),
        ('other', 'Other'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='events')
    syllabus = models.ForeignKey(
        SyllabusFile, on_delete=models.SET_NULL, null=True, blank=True, related_name='events'
    )
    title = models.CharField(max_length=300)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES)
    date = models.DateField(null=True, blank=True)
    workload = models.IntegerField(default=1, help_text="Workload weight (1-8)")
    raw_line = models.TextField(blank=True, help_text="Original line from syllabus")
    is_verified = models.BooleanField(default=False, help_text="Human verified event")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'workload']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['course', 'date']),
            models.Index(fields=['event_type']),
        ]

    def __str__(self):
        return f"{self.course.code} | {self.title} — {self.date or 'No date'}"

    @property
    def week_number(self):
        if self.date:
            return self.date.isocalendar()[1]
        return None

    @property
    def iso_week_key(self):
        if self.date:
            iso = self.date.isocalendar()
            return f"{iso[0]}-W{iso[1]:02d}"
        return None


# ─────────────────────────────────────────────
# Conflict Engine Models
# ─────────────────────────────────────────────

class ConflictWeek(models.Model):
    """Represents a week detected as having excessive workload."""

    SEVERITY_CHOICES = [
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]

    CONFLICT_TYPE_CHOICES = [
        ('weekly_overload', 'Weekly Overload'),
        ('daily_overload', 'Daily Overload'),
        ('exam_collision', 'Exam Collision'),
        ('consecutive_overload', 'Consecutive Overload'),
    ]

    week_key = models.CharField(max_length=10, help_text="ISO week key, e.g. 2026-W11")
    week_start = models.DateField(null=True, blank=True)
    week_end = models.DateField(null=True, blank=True)
    total_load = models.IntegerField(help_text="Sum of event weights this week")
    threshold = models.IntegerField(default=7)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='warning')
    conflict_type = models.CharField(max_length=30, choices=CONFLICT_TYPE_CHOICES, default='weekly_overload')
    courses_affected = models.JSONField(default=list)
    message = models.TextField(blank=True)
    detected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['week_key']
        unique_together = [['week_key', 'conflict_type']]

    def __str__(self):
        return f"{self.get_severity_display()}: {self.week_key} (load={self.total_load})"


class AnalysisSession(models.Model):
    """Tracks a full analysis run across multiple syllabi."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    courses = models.ManyToManyField(Course, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_events = models.IntegerField(default=0)
    total_conflicts = models.IntegerField(default=0)
    max_weekly_load = models.IntegerField(default=0)
    avg_weekly_load = models.FloatField(default=0.0)
    summary_json = models.JSONField(default=dict)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Analysis #{self.pk} — {self.get_status_display()} ({self.total_events} events)"
