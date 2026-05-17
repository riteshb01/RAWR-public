"""
Bengal RAWR — DRF Serializers
"""

from rest_framework import serializers
from apps.syllabus.models import Course, SyllabusFile, Event, ConflictWeek, AnalysisSession


class CourseSerializer(serializers.ModelSerializer):
    event_count = serializers.SerializerMethodField()
    conflict_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'name', 'code', 'professor', 'semester', 'event_count', 'conflict_count', 'created_at']
        read_only_fields = ['id', 'created_at', 'event_count', 'conflict_count']

    def get_event_count(self, obj):
        return obj.events.filter(date__isnull=False).count()

    def get_conflict_count(self, obj):
        # Count weeks with events from this course that are flagged as conflicts
        return 0  # Placeholder - computed separately


class SyllabusUploadSerializer(serializers.ModelSerializer):
    """Used for file upload endpoint."""
    file = serializers.FileField()
    course_name = serializers.CharField(write_only=True, required=False)
    course_code = serializers.CharField(write_only=True, required=False)
    professor = serializers.CharField(write_only=True, required=False)
    semester = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = SyllabusFile
        fields = ['id', 'file', 'original_filename', 'status', 'course_name',
                  'course_code', 'professor', 'semester', 'uploaded_at']
        read_only_fields = ['id', 'original_filename', 'status', 'uploaded_at']

    def validate_file(self, value):
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError("File size must not exceed 10MB.")

        allowed_extensions = ['.pdf', '.txt', '.docx']
        import os
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"Invalid file type '{ext}'. Allowed: {', '.join(allowed_extensions)}"
            )
        return value


class SyllabusFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyllabusFile
        fields = ['id', 'original_filename', 'file_size', 'status',
                  'error_message', 'uploaded_at', 'processed_at']


class EventSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    iso_week_key = serializers.ReadOnlyField()
    week_number = serializers.ReadOnlyField()

    class Meta:
        model = Event
        fields = [
            'id', 'course', 'course_name', 'course_code',
            'title', 'event_type', 'date', 'workload',
            'raw_line', 'is_verified', 'notes',
            'week_number', 'iso_week_key', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'course_name', 'course_code']


class ConflictWeekSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConflictWeek
        fields = [
            'id', 'week_key', 'week_start', 'week_end',
            'total_load', 'threshold', 'severity',
            'conflict_type', 'courses_affected', 'message', 'detected_at',
        ]


class AnalysisSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisSession
        fields = [
            'id', 'status', 'total_events', 'total_conflicts',
            'max_weekly_load', 'avg_weekly_load',
            'summary_json', 'started_at', 'completed_at',
        ]


class HeatmapDataSerializer(serializers.Serializer):
    """Serializer for heatmap endpoint response."""
    heatmap = serializers.DictField(child=serializers.IntegerField())
    weekly_loads = serializers.DictField()
    conflicts = serializers.ListField()
    summary = serializers.DictField()


class DashboardSummarySerializer(serializers.Serializer):
    """Serializer for the main dashboard summary endpoint."""
    total_courses = serializers.IntegerField()
    total_events = serializers.IntegerField()
    total_conflicts = serializers.IntegerField()
    critical_weeks = serializers.IntegerField()
    upcoming_events = EventSerializer(many=True)
    recent_conflicts = ConflictWeekSerializer(many=True)
    heatmap_data = serializers.DictField(child=serializers.IntegerField())
