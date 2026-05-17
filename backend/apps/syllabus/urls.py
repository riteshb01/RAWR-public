from django.urls import path
from apps.syllabus.views import (
    CourseListCreateView, CourseDetailView,
    UploadSyllabusView, ReprocessSyllabusView,
    EventListView, EventDetailView, VerifyEventView,
    ConflictListView, RunConflictAnalysisView,
    DashboardSummaryView, HeatmapDataView, WeeklyWorkloadView,
)
urlpatterns = [
    path('courses/', CourseListCreateView.as_view()),
    path('courses/<int:pk>/', CourseDetailView.as_view()),
    path('upload-syllabus/', UploadSyllabusView.as_view()),
    path('syllabi/<int:pk>/reprocess/', ReprocessSyllabusView.as_view()),
    path('events/', EventListView.as_view()),
    path('events/<int:pk>/', EventDetailView.as_view()),
    path('events/<int:pk>/verify/', VerifyEventView.as_view()),
    path('conflicts/', ConflictListView.as_view()),
    path('conflicts/analyze/', RunConflictAnalysisView.as_view()),
    path('dashboard/', DashboardSummaryView.as_view()),
    path('dashboard/heatmap/', HeatmapDataView.as_view()),
    path('dashboard/weekly-workload/', WeeklyWorkloadView.as_view()),
]
