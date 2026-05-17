"""
Bengal RAWR — Django Admin Configuration
Rich admin interface for managing all models.
"""

from django.contrib import admin
from django.utils.html import format_html
from apps.syllabus.models import Course, SyllabusFile, Event, ConflictWeek, AnalysisSession


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'professor', 'semester', 'event_count', 'created_at']
    list_filter = ['semester']
    search_fields = ['name', 'code', 'professor']
    readonly_fields = ['created_at', 'updated_at']

    def event_count(self, obj):
        return obj.events.count()
    event_count.short_description = 'Events'


@admin.register(SyllabusFile)
class SyllabusFileAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'course', 'status_badge', 'file_size_display', 'uploaded_at']
    list_filter = ['status']
    search_fields = ['original_filename', 'course__name']
    readonly_fields = ['status', 'uploaded_at', 'processed_at', 'file_size', 'extracted_text']

    def status_badge(self, obj):
        colors = {
            'completed': '#22c55e', 'processing': '#3b82f6',
            'failed': '#ef4444', 'uploaded': '#f59e0b',
        }
        color = colors.get(obj.status, '#94a3b8')
        return format_html(
            '<span style="color:{};font-weight:600;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def file_size_display(self, obj):
        if obj.file_size < 1024:
            return f"{obj.file_size} B"
        elif obj.file_size < 1024 * 1024:
            return f"{obj.file_size // 1024} KB"
        return f"{obj.file_size // (1024 * 1024)} MB"
    file_size_display.short_description = 'Size'


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'event_type_badge', 'date', 'workload', 'is_verified']
    list_filter = ['event_type', 'is_verified', 'date']
    search_fields = ['title', 'course__name', 'course__code']
    list_editable = ['is_verified']
    readonly_fields = ['created_at']
    date_hierarchy = 'date'

    def event_type_badge(self, obj):
        colors = {
            'final': '#dc2626', 'midterm': '#ea580c', 'exam': '#d97706',
            'quiz': '#ca8a04', 'presentation': '#7c3aed', 'project': '#2563eb',
            'assignment': '#0891b2', 'homework': '#059669',
        }
        color = colors.get(obj.event_type, '#94a3b8')
        return format_html(
            '<span style="color:{};font-weight:600;text-transform:uppercase;">{}</span>',
            color, obj.event_type
        )
    event_type_badge.short_description = 'Type'


@admin.register(ConflictWeek)
class ConflictWeekAdmin(admin.ModelAdmin):
    list_display = ['week_key', 'severity_badge', 'conflict_type', 'total_load', 'threshold', 'detected_at']
    list_filter = ['severity', 'conflict_type']

    def severity_badge(self, obj):
        color = '#dc2626' if obj.severity == 'critical' else '#f59e0b'
        icon = '🔥' if obj.severity == 'critical' else '⚠️'
        return format_html(
            '{} <span style="color:{};font-weight:600;">{}</span>',
            icon, color, obj.get_severity_display()
        )
    severity_badge.short_description = 'Severity'


@admin.register(AnalysisSession)
class AnalysisSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'total_events', 'total_conflicts', 'max_weekly_load', 'started_at']
    list_filter = ['status']
    readonly_fields = ['started_at', 'completed_at']
