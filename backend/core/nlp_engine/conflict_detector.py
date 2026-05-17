"""
Bengal RAWR — Conflict Detection Engine
Detects overloaded academic weeks by analyzing event workload distribution.

Supports:
- Per-week threshold detection
- Cross-course conflict identification  
- Consecutive overloaded week detection
- Daily overload detection
"""

import logging
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Thresholds
# ─────────────────────────────────────────────

WEEKLY_THRESHOLD = 7        # Total weight in a week = "conflict"
CRITICAL_THRESHOLD = 12     # Critical overload
DAILY_THRESHOLD = 5         # Single-day overload
CONSECUTIVE_WEEKS_ALERT = 2 # Alert if N+ consecutive heavy weeks


def get_iso_week_key(d: date) -> str:
    """Return ISO week key string like '2026-W11'."""
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def get_week_start(d: date) -> date:
    """Return Monday of the week containing date d."""
    return d - timedelta(days=d.weekday())


def get_week_end(d: date) -> date:
    """Return Sunday of the week containing date d."""
    return get_week_start(d) + timedelta(days=6)


class ConflictDetectionEngine:
    """
    Analyzes a list of structured event dicts and identifies
    conflict periods (overloaded weeks/days).
    """

    def __init__(
        self,
        weekly_threshold: int = WEEKLY_THRESHOLD,
        critical_threshold: int = CRITICAL_THRESHOLD,
        daily_threshold: int = DAILY_THRESHOLD,
    ):
        self.weekly_threshold = weekly_threshold
        self.critical_threshold = critical_threshold
        self.daily_threshold = daily_threshold

    def analyze(self, events: list) -> dict:
        """
        Main analysis method.

        Args:
            events: List of event dicts with 'date', 'weight', 'course', 'event_type'

        Returns:
            Analysis results dict with:
                - weekly_loads: {week_key: {load, events, courses, ...}}
                - daily_loads: {date_str: {load, events}}
                - conflicts: list of conflict records
                - summary: overall summary stats
        """
        # Filter events with valid dates
        dated_events = [e for e in events if e.get('date')]

        if not dated_events:
            return self._empty_result()

        # ── Aggregate by week ──────────────────────────────────────────────
        weekly_data = defaultdict(lambda: {
            'load': 0,
            'events': [],
            'courses': set(),
            'week_start': None,
            'week_end': None,
        })

        daily_data = defaultdict(lambda: {'load': 0, 'events': []})

        for event in dated_events:
            d = event['date']
            weight = event.get('weight', 1)
            week_key = get_iso_week_key(d)
            date_str = str(d)

            # Weekly accumulation
            weekly_data[week_key]['load'] += weight
            weekly_data[week_key]['events'].append(event)
            weekly_data[week_key]['courses'].add(event.get('course', 'Unknown'))
            weekly_data[week_key]['week_start'] = get_week_start(d)
            weekly_data[week_key]['week_end'] = get_week_end(d)

            # Daily accumulation
            daily_data[date_str]['load'] += weight
            daily_data[date_str]['events'].append(event)

        # Convert sets to lists for serialization
        for wk in weekly_data.values():
            wk['courses'] = list(wk['courses'])
            wk['week_start'] = str(wk['week_start']) if wk['week_start'] else None
            wk['week_end'] = str(wk['week_end']) if wk['week_end'] else None

        # ── Conflict detection ─────────────────────────────────────────────
        conflicts = []

        # Weekly conflicts
        for week_key, data in sorted(weekly_data.items()):
            load = data['load']
            if load >= self.weekly_threshold:
                severity = 'critical' if load >= self.critical_threshold else 'warning'
                conflicts.append({
                    'type': 'weekly_overload',
                    'week_key': week_key,
                    'week_start': data['week_start'],
                    'week_end': data['week_end'],
                    'total_load': load,
                    'threshold': self.weekly_threshold,
                    'severity': severity,
                    'courses_affected': data['courses'],
                    'event_count': len(data['events']),
                    'event_types': list({e['event_type'] for e in data['events']}),
                    'message': self._build_weekly_message(week_key, load, severity, data['courses']),
                })

        # Daily conflicts
        for date_str, data in sorted(daily_data.items()):
            if data['load'] >= self.daily_threshold:
                conflicts.append({
                    'type': 'daily_overload',
                    'date': date_str,
                    'total_load': data['load'],
                    'threshold': self.daily_threshold,
                    'severity': 'warning',
                    'event_count': len(data['events']),
                    'event_types': list({e['event_type'] for e in data['events']}),
                    'message': f"Heavy day on {date_str}: {data['load']} workload points",
                })

        # Cross-course same-day exam conflicts
        exam_types = {'exam', 'midterm', 'final', 'quiz'}
        exams_by_date = defaultdict(list)
        for event in dated_events:
            if event.get('event_type') in exam_types:
                exams_by_date[str(event['date'])].append(event)

        for date_str, day_exams in exams_by_date.items():
            unique_courses = {e.get('course') for e in day_exams}
            if len(unique_courses) >= 2:
                conflicts.append({
                    'type': 'exam_collision',
                    'date': date_str,
                    'courses': list(unique_courses),
                    'severity': 'critical',
                    'event_count': len(day_exams),
                    'message': f"Multiple exams/tests on {date_str}: {', '.join(unique_courses)}",
                })

        # Consecutive heavy weeks
        sorted_weeks = sorted(weekly_data.keys())
        heavy_streak = []
        for week_key in sorted_weeks:
            if weekly_data[week_key]['load'] >= self.weekly_threshold:
                heavy_streak.append(week_key)
                if len(heavy_streak) >= CONSECUTIVE_WEEKS_ALERT:
                    conflicts.append({
                        'type': 'consecutive_overload',
                        'weeks': list(heavy_streak),
                        'severity': 'warning',
                        'message': f"{len(heavy_streak)} consecutive heavy weeks: {', '.join(heavy_streak)}",
                    })
            else:
                heavy_streak = []

        # ── Summary stats ──────────────────────────────────────────────────
        all_loads = [d['load'] for d in weekly_data.values()]
        summary = {
            'total_events': len(dated_events),
            'events_without_date': len(events) - len(dated_events),
            'total_weeks_tracked': len(weekly_data),
            'conflict_weeks': sum(1 for d in weekly_data.values() if d['load'] >= self.weekly_threshold),
            'critical_weeks': sum(1 for d in weekly_data.values() if d['load'] >= self.critical_threshold),
            'max_weekly_load': max(all_loads) if all_loads else 0,
            'avg_weekly_load': round(sum(all_loads) / len(all_loads), 2) if all_loads else 0,
            'total_conflicts_detected': len(conflicts),
        }

        return {
            'weekly_loads': dict(weekly_data),
            'daily_loads': dict(daily_data),
            'conflicts': conflicts,
            'summary': summary,
        }

    def _build_weekly_message(self, week_key: str, load: int, severity: str, courses: list) -> str:
        emoji = '🔥' if severity == 'critical' else '⚠️'
        label = 'CRITICAL OVERLOAD' if severity == 'critical' else 'Heavy Week'
        return f"{emoji} {label} — {week_key}: {load} workload points across {', '.join(courses)}"

    def _empty_result(self) -> dict:
        return {
            'weekly_loads': {},
            'daily_loads': {},
            'conflicts': [],
            'summary': {
                'total_events': 0,
                'events_without_date': 0,
                'total_weeks_tracked': 0,
                'conflict_weeks': 0,
                'critical_weeks': 0,
                'max_weekly_load': 0,
                'avg_weekly_load': 0,
                'total_conflicts_detected': 0,
            }
        }

    def generate_heatmap_data(self, events: list) -> dict:
        """
        Generate daily workload data for heatmap visualization.
        Returns {date_str: total_weight} for all dated events.

        Compatible with GitHub-contribution-style heatmap format.
        """
        daily_load = defaultdict(int)
        for event in events:
            if event.get('date'):
                daily_load[str(event['date'])] += event.get('weight', 1)

        return dict(daily_load)
