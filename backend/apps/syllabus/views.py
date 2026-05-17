"""
Bengal RAWR — API Views
All REST API endpoints for the Bengal RAWR system.
"""

import logging
from datetime import datetime, date, timedelta

from django.utils import timezone
from django.db import transaction
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from apps.syllabus.models import Course, SyllabusFile, Event, ConflictWeek, AnalysisSession
from apps.syllabus.serializers import (
    CourseSerializer, SyllabusUploadSerializer, SyllabusFileSerializer,
    EventSerializer, ConflictWeekSerializer, AnalysisSessionSerializer,
    HeatmapDataSerializer, DashboardSummarySerializer,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────
# Processing pipeline (imported at function level to avoid
# circular imports and allow optional dependencies)
# ─────────────────────────────────────────────────────────

def _run_full_pipeline(syllabus_file: SyllabusFile) -> dict:
    """
    Execute the full parse → NLP → conflict detection pipeline
    for a single syllabus file.

    Returns summary dict.
    """
    from core.date_parser.document_parser import DocumentParser
    from core.nlp_engine.engine import SyllabusNLPEngine
    from core.nlp_engine.conflict_detector import ConflictDetectionEngine

    # Mark as processing
    syllabus_file.status = 'processing'
    syllabus_file.save(update_fields=['status'])

    try:
        # Step 1 — Extract text
        parser = DocumentParser()
        file_path = syllabus_file.file.path
        extracted_text = parser.parse(file_path)

        syllabus_file.extracted_text = extracted_text[:50000]  # Cap stored text
        syllabus_file.save(update_fields=['extracted_text'])

        # Step 2 — NLP event extraction
        course = syllabus_file.course
        nlp_engine = SyllabusNLPEngine(reference_year=datetime.now().year)
        raw_events = nlp_engine.process(extracted_text, course_name=course.code or course.name)

        # Step 3 — Persist events to DB
        events_created = []
        with transaction.atomic():
            # Clear old events for this syllabus file
            Event.objects.filter(syllabus=syllabus_file).delete()

            for evt in raw_events:
                event_obj = Event(
                    course=course,
                    syllabus=syllabus_file,
                    title=evt.get('title', 'Untitled'),
                    event_type=evt.get('event_type', 'other'),
                    date=evt.get('date'),
                    workload=evt.get('weight', 1),
                    raw_line=evt.get('raw_line', ''),
                )
                events_created.append(event_obj)

            Event.objects.bulk_create(events_created)

        # Step 4 — Conflict detection across ALL events for this course's user
        all_events = list(
            Event.objects.filter(
                course__created_by=course.created_by,
                date__isnull=False,
            ).values('course__code', 'event_type', 'date', 'workload')
        )

        # Format for conflict engine
        event_dicts = [
            {
                'course': e['course__code'] or 'Unknown',
                'event_type': e['event_type'],
                'date': e['date'],
                'weight': e['workload'],
            }
            for e in all_events
        ]

        conflict_engine = ConflictDetectionEngine()
        analysis = conflict_engine.analyze(event_dicts)

        # Step 5 — Persist conflict weeks
        with transaction.atomic():
            for conflict in analysis['conflicts']:
                if conflict['type'] == 'weekly_overload':
                    ConflictWeek.objects.update_or_create(
                        week_key=conflict['week_key'],
                        conflict_type='weekly_overload',
                        defaults={
                            'week_start': conflict.get('week_start'),
                            'week_end': conflict.get('week_end'),
                            'total_load': conflict['total_load'],
                            'threshold': conflict['threshold'],
                            'severity': conflict['severity'],
                            'courses_affected': conflict.get('courses_affected', []),
                            'message': conflict.get('message', ''),
                        }
                    )

        # Mark complete
        syllabus_file.status = 'completed'
        syllabus_file.processed_at = timezone.now()
        syllabus_file.save(update_fields=['status', 'processed_at'])

        return {
            'events_extracted': len(events_created),
            'conflicts_detected': len([c for c in analysis['conflicts'] if c['type'] == 'weekly_overload']),
            'summary': analysis['summary'],
        }

    except Exception as e:
        logger.exception(f"Pipeline failed for syllabus {syllabus_file.pk}: {e}")
        syllabus_file.status = 'failed'
        syllabus_file.error_message = str(e)[:1000]
        syllabus_file.save(update_fields=['status', 'error_message'])
        raise


# ─────────────────────────────────────────────────────────
# Course Views
# ─────────────────────────────────────────────────────────

class CourseListCreateView(APIView):
    """GET /courses/ — list all | POST /courses/ — create course"""

    def get(self, request):
        courses = Course.objects.all()
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CourseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user if request.user.is_authenticated else None)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CourseDetailView(RetrieveUpdateDestroyAPIView):
    """GET/PUT/DELETE /courses/<id>/"""
    queryset = Course.objects.all()
    serializer_class = CourseSerializer


# ─────────────────────────────────────────────────────────
# Syllabus Upload
# ─────────────────────────────────────────────────────────

class UploadSyllabusView(APIView):
    """
    POST /upload-syllabus/
    Accepts multipart form data with:
        - file: PDF/TXT/DOCX
        - course_name: string
        - course_code: string (optional)
        - professor: string (optional)
        - semester: string (optional)
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response(
                {'error': 'No file provided. Send file as multipart/form-data.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate extension
        allowed = ['.pdf', '.txt', '.docx']
        import os
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in allowed:
            return Response(
                {'error': f"Unsupported file type '{ext}'. Allowed: {', '.join(allowed)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get or create course
        course_name = request.data.get('course_name', file.name.replace(ext, ''))
        course_code = request.data.get('course_code', '')
        professor = request.data.get('professor', '')
        semester = request.data.get('semester', '')

        course, created = Course.objects.get_or_create(
            name=course_name,
            defaults={
                'code': course_code,
                'professor': professor,
                'semester': semester,
                'created_by': request.user if request.user.is_authenticated else None,
            }
        )

        # Save file record
        syllabus_file = SyllabusFile.objects.create(
            course=course,
            file=file,
            original_filename=file.name,
            file_size=file.size,
        )

        # Run pipeline
        try:
            result = _run_full_pipeline(syllabus_file)
            return Response({
                'status': 'processed',
                'syllabus_id': syllabus_file.pk,
                'course_id': course.pk,
                'course_name': course.name,
                'is_new_course': created,
                **result,
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'status': 'failed',
                'syllabus_id': syllabus_file.pk,
                'error': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReprocessSyllabusView(APIView):
    """POST /syllabi/<id>/reprocess/ — Rerun NLP on already uploaded file."""

    def post(self, request, pk):
        try:
            syllabus_file = SyllabusFile.objects.get(pk=pk)
        except SyllabusFile.DoesNotExist:
            return Response({'error': 'Syllabus not found'}, status=404)

        try:
            result = _run_full_pipeline(syllabus_file)
            return Response({'status': 'reprocessed', **result})
        except Exception as e:
            return Response({'status': 'failed', 'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────
# Events Views
# ─────────────────────────────────────────────────────────

class EventListView(APIView):
    """GET /events/ — List all events with optional filters."""

    def get(self, request):
        queryset = Event.objects.select_related('course').all()

        # Filters
        course_id = request.query_params.get('course_id')
        event_type = request.query_params.get('event_type')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        week_key = request.query_params.get('week_key')

        if course_id:
            queryset = queryset.filter(course_id=course_id)
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        if week_key:
            # e.g. 2026-W11
            try:
                year, week = week_key.split('-W')
                queryset = queryset.filter(
                    date__week=int(week), date__year=int(year)
                )
            except (ValueError, AttributeError):
                pass

        serializer = EventSerializer(queryset, many=True)
        return Response(serializer.data)


class EventDetailView(RetrieveUpdateDestroyAPIView):
    """GET/PUT/DELETE /events/<id>/"""
    queryset = Event.objects.select_related('course').all()
    serializer_class = EventSerializer


class VerifyEventView(APIView):
    """POST /events/<id>/verify/ — Mark an event as human-verified."""

    def post(self, request, pk):
        try:
            event = Event.objects.get(pk=pk)
            event.is_verified = True
            event.save(update_fields=['is_verified'])
            return Response({'status': 'verified', 'id': pk})
        except Event.DoesNotExist:
            return Response({'error': 'Event not found'}, status=404)


# ─────────────────────────────────────────────────────────
# Conflict Views
# ─────────────────────────────────────────────────────────

class ConflictListView(APIView):
    """GET /conflicts/ — List all detected conflict weeks."""

    def get(self, request):
        severity = request.query_params.get('severity')
        conflict_type = request.query_params.get('type')

        queryset = ConflictWeek.objects.all()
        if severity:
            queryset = queryset.filter(severity=severity)
        if conflict_type:
            queryset = queryset.filter(conflict_type=conflict_type)

        serializer = ConflictWeekSerializer(queryset, many=True)
        return Response(serializer.data)


class RunConflictAnalysisView(APIView):
    """
    POST /conflicts/analyze/
    Re-run conflict detection across all events in the system.
    """

    def post(self, request):
        from core.nlp_engine.conflict_detector import ConflictDetectionEngine

        all_events = list(
            Event.objects.filter(date__isnull=False).values(
                'course__code', 'event_type', 'date', 'workload'
            )
        )

        if not all_events:
            return Response({'message': 'No events with dates found.'})

        event_dicts = [
            {
                'course': e['course__code'] or 'Unknown',
                'event_type': e['event_type'],
                'date': e['date'],
                'weight': e['workload'],
            }
            for e in all_events
        ]

        engine = ConflictDetectionEngine()
        analysis = engine.analyze(event_dicts)

        # Persist conflicts
        with transaction.atomic():
            ConflictWeek.objects.all().delete()
            for conflict in analysis['conflicts']:
                if conflict['type'] == 'weekly_overload':
                    ConflictWeek.objects.create(
                        week_key=conflict['week_key'],
                        week_start=conflict.get('week_start'),
                        week_end=conflict.get('week_end'),
                        total_load=conflict['total_load'],
                        threshold=conflict['threshold'],
                        severity=conflict['severity'],
                        conflict_type='weekly_overload',
                        courses_affected=conflict.get('courses_affected', []),
                        message=conflict.get('message', ''),
                    )

        return Response({
            'status': 'analysis_complete',
            'summary': analysis['summary'],
            'conflicts_saved': ConflictWeek.objects.count(),
        })


# ─────────────────────────────────────────────────────────
# Dashboard Views
# ─────────────────────────────────────────────────────────

class DashboardSummaryView(APIView):
    """GET /dashboard/ — Main dashboard summary data."""

    def get(self, request):
        from core.nlp_engine.conflict_detector import ConflictDetectionEngine

        # Core counts
        total_courses = Course.objects.count()
        total_events = Event.objects.filter(date__isnull=False).count()
        total_conflicts = ConflictWeek.objects.count()
        critical_weeks = ConflictWeek.objects.filter(severity='critical').count()

        # Upcoming events (next 30 days)
        today = date.today()
        upcoming_cutoff = today + timedelta(days=30)
        upcoming_events = Event.objects.filter(
            date__gte=today,
            date__lte=upcoming_cutoff,
        ).select_related('course').order_by('date')[:10]

        # Recent conflicts
        recent_conflicts = ConflictWeek.objects.order_by('-detected_at')[:5]

        # Heatmap data
        all_events = list(
            Event.objects.filter(date__isnull=False).values('date', 'workload')
        )
        heatmap_data = {}
        for evt in all_events:
            date_str = str(evt['date'])
            heatmap_data[date_str] = heatmap_data.get(date_str, 0) + evt['workload']

        return Response({
            'total_courses': total_courses,
            'total_events': total_events,
            'total_conflicts': total_conflicts,
            'critical_weeks': critical_weeks,
            'upcoming_events': EventSerializer(upcoming_events, many=True).data,
            'recent_conflicts': ConflictWeekSerializer(recent_conflicts, many=True).data,
            'heatmap_data': heatmap_data,
        })


class HeatmapDataView(APIView):
    """GET /dashboard/heatmap/ — Full heatmap dataset."""

    def get(self, request):
        from core.nlp_engine.conflict_detector import ConflictDetectionEngine

        all_events = list(
            Event.objects.filter(date__isnull=False).values(
                'course__code', 'event_type', 'date', 'workload'
            )
        )

        event_dicts = [
            {
                'course': e['course__code'] or 'Unknown',
                'event_type': e['event_type'],
                'date': e['date'],
                'weight': e['workload'],
            }
            for e in all_events
        ]

        engine = ConflictDetectionEngine()
        heatmap = engine.generate_heatmap_data(event_dicts)
        analysis = engine.analyze(event_dicts)

        return Response({
            'heatmap': heatmap,
            'weekly_loads': {
                k: {
                    'load': v['load'],
                    'week_start': v['week_start'],
                    'week_end': v['week_end'],
                    'courses': v['courses'],
                    'event_count': len(v['events']),
                }
                for k, v in analysis['weekly_loads'].items()
            },
            'conflicts': analysis['conflicts'],
            'summary': analysis['summary'],
        })


class WeeklyWorkloadView(APIView):
    """GET /dashboard/weekly-workload/ — Weekly breakdown for bar chart."""

    def get(self, request):
        from collections import defaultdict

        events = Event.objects.filter(date__isnull=False).values(
            'date', 'workload', 'event_type', 'course__code'
        )

        weekly = defaultdict(lambda: {'total': 0, 'by_course': defaultdict(int), 'by_type': defaultdict(int)})

        for e in events:
            d = e['date']
            iso = d.isocalendar()
            week_key = f"{iso[0]}-W{iso[1]:02d}"
            weekly[week_key]['total'] += e['workload']
            weekly[week_key]['by_course'][e['course__code'] or 'Unknown'] += e['workload']
            weekly[week_key]['by_type'][e['event_type']] += e['workload']

        # Convert defaultdicts for JSON serialization
        result = {
            wk: {
                'total': data['total'],
                'by_course': dict(data['by_course']),
                'by_type': dict(data['by_type']),
            }
            for wk, data in sorted(weekly.items())
        }

        threshold = 7
        return Response({
            'weekly_workload': result,
            'threshold': threshold,
        })
