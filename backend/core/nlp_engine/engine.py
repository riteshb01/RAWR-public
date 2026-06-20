"""
Bengal RAWR — NLP Engine
Core module for extracting academic events from syllabus text.
Uses spaCy + regex + keyword heuristics. No external AI APIs.
"""

import re
import logging
from datetime import datetime, date
from typing import Optional
import dateparser

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Event keyword taxonomy with weights
# ─────────────────────────────────────────────
EVENT_KEYWORDS = {
    'homework': {
        'keywords': ['homework', 'hw', 'take-home', 'take home'],
        'weight': 1,
    },
    'assignment': {
        'keywords': ['assignment', 'deliverable', 'submission', 'submit', 'due'],
        'weight': 2,
    },
    'quiz': {
        'keywords': ['quiz', 'pop quiz', 'in-class quiz'],
        'weight': 2,
    },
    'presentation': {
        'keywords': ['presentation', 'present', 'demo', 'showcase', 'poster'],
        'weight': 3,
    },
    'project': {
        'keywords': ['project', 'group project', 'team project', 'final project'],
        'weight': 3,
    },
    'midterm': {
        'keywords': ['midterm', 'mid-term', 'midterm exam', 'mid term'],
        'weight': 5,
    },
    'exam': {
        'keywords': ['exam', 'test', 'assessment', 'evaluation'],
        'weight': 5,
    },
    'final': {
        'keywords': ['final', 'final exam', 'finals', 'comprehensive exam'],
        'weight': 8,
    },
    'lab': {
        'keywords': ['lab', 'laboratory', 'lab report'],
        'weight': 2,
    },
    'reading': {
        'keywords': ['reading', 'read chapter', 'read pp', 'read pages'],
        'weight': 1,
    },
}

# ─────────────────────────────────────────────
# Date patterns covering most syllabus formats
# ─────────────────────────────────────────────
DATE_PATTERNS = [
    # ISO: 2026-03-12
    r'\b(\d{4}-\d{2}-\d{2})\b',
    # Slashes: 03/12/2026 or 3/12/26 or 3/12
    r'\b(\d{1,2}/\d{1,2}(?:/\d{2,4})?)\b',
    # Month name full: March 12, 2026 or March 12
    r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(\d{4}))?\b',
    # Month name abbreviated: Mar 12, 2026 or Mar 12
    r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(\d{4}))?\b',
    # Day Month: 12 March or 12th March
    r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December)\b',
    # Week reference: Week 11, Week of March 10
    r'\bWeek\s+(\d{1,2})\b',
    # "Due by/on" phrase hints
    r'\bdue\s+(?:on\s+|by\s+)?([A-Za-z]+\s+\d{1,2}(?:,\s*\d{4})?|\d{1,2}/\d{1,2}(?:/\d{2,4})?)\b',
]

COMBINED_DATE_REGEX = re.compile(
    r'(?:'
    r'\d{4}-\d{2}-\d{2}'                                   # ISO
    r'|\d{1,2}/\d{1,2}(?:/\d{2,4})?'                      # slashes
    r'|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
    r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
    r'\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s*\d{4})?'      # Month DD, YYYY
    r'|\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|'
    r'Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|'
    r'Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'            # DD Month
    r')',
    re.IGNORECASE,
)


def parse_date_string(date_str: str, reference_year: int = None) -> Optional[date]:
    """
    Parse a date string into a Python date object using dateparser.
    Falls back to current year if none specified.
    """
    if not date_str or not date_str.strip():
        return None

    settings = {
        'RETURN_AS_TIMEZONE_AWARE': False,
        'PREFER_DAY_OF_MONTH': 'first',
    }
    if reference_year:
        settings['PREFER_DATES_FROM'] = 'future'

    try:
        parsed = dateparser.parse(date_str.strip(), settings=settings)
        if parsed:
            # If no year in original string, use reference_year if provided
            if reference_year and str(reference_year) not in date_str:
                parsed = parsed.replace(year=reference_year)
            return parsed.date()
    except Exception as e:
        logger.debug(f"dateparser failed on '{date_str}': {e}")

    return None


def extract_dates_from_line(line: str, reference_year: int = None) -> list:
    """
    Extract all date mentions from a single text line.
    Returns list of (raw_string, parsed_date) tuples.
    """
    results = []
    matches = COMBINED_DATE_REGEX.findall(line)

    for match in matches:
        parsed = parse_date_string(match, reference_year)
        if parsed:
            results.append((match, parsed))

    return results


def detect_event_type(line: str) -> Optional[dict]:
    """
    Detect what type of academic event a line describes.
    Returns dict with event_type and weight, or None if no event found.
    """
    line_lower = line.lower()

    # Order matters — more specific first
    priority_order = ['final', 'midterm', 'exam', 'presentation', 'project', 'quiz', 'assignment', 'homework', 'lab', 'reading']

    for event_type in priority_order:
        meta = EVENT_KEYWORDS[event_type]
        for keyword in meta['keywords']:
            if keyword in line_lower:
                return {
                    'event_type': event_type,
                    'weight': meta['weight'],
                    'matched_keyword': keyword,
                }
    return None


def extract_event_title(line: str, event_type: str) -> str:
    """
    Attempt to extract a meaningful title from the line.
    Strips dates and common prefixes to get clean title text.
    """
    # Remove date strings
    title = COMBINED_DATE_REGEX.sub('', line).strip()

    # Remove common noise
    noise_patterns = [
        r'\b(due|by|on|at|before|after|submit|turn in|hand in)\b',
        r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
        r'^\s*[-•*]\s*',  # bullet points
        r'\s{2,}',        # extra whitespace → single space
        r'[()[\]]',       # brackets
    ]
    for pat in noise_patterns:
        title = re.sub(pat, ' ', title, flags=re.IGNORECASE).strip()

    title = re.sub(r'\s{2,}', ' ', title).strip()

    # If too short, fall back to event_type capitalized
    if len(title) < 3:
        return event_type.capitalize()

    # Truncate at a reasonable length
    return title[:120]


# Minimum ML confidence required to accept a classifier prediction.
# Lines where the top label confidence is below this are treated as non-events.
ML_CONFIDENCE_THRESHOLD = 0.65


class SyllabusNLPEngine:
    """
    Main NLP engine that processes raw syllabus text and returns
    structured academic event records.

    Detection strategy (two-pass per line):
      1. Keyword heuristics via detect_event_type()  — fast, high precision
      2. ML classifier fallback                      — catches lines keywords miss
         (only if confidence >= ML_CONFIDENCE_THRESHOLD)
    """

    def __init__(self, reference_year: int = None, use_classifier: bool = True):
        self.reference_year = reference_year or datetime.now().year
        self.spacy_nlp = None
        self.classifier = None
        self._try_load_spacy()
        if use_classifier:
            self._try_load_classifier()

    def _try_load_spacy(self):
        """Attempt to load spaCy model; degrade gracefully if unavailable."""
        try:
            import spacy
            self.spacy_nlp = spacy.load('en_core_web_sm')
            logger.info("spaCy model loaded successfully")
        except Exception as e:
            logger.warning(f"spaCy not available, using regex-only mode: {e}")
            self.spacy_nlp = None

    def _try_load_classifier(self):
        """Load the ML event classifier singleton; degrade gracefully if unavailable."""
        try:
            from core.event_classifier.classifier import get_classifier
            self.classifier = get_classifier()
            logger.info("ML classifier loaded into NLP engine")
        except Exception as e:
            logger.warning(f"ML classifier unavailable, keyword-only mode active: {e}")
            self.classifier = None

    def _spacy_extract_dates(self, text: str) -> list:
        """Use spaCy NER to extract DATE entities for a higher recall pass."""
        if not self.spacy_nlp:
            return []

        doc = self.spacy_nlp(text)
        dates = []
        for ent in doc.ents:
            if ent.label_ == 'DATE':
                parsed = parse_date_string(ent.text, self.reference_year)
                if parsed:
                    dates.append((ent.text, parsed, ent.start_char, ent.end_char))
        return dates

    def process(self, text: str, course_name: str = 'Unknown') -> list:
        """
        Main entry point: takes raw text, returns list of event dicts.

        Returns:
            List of dicts with keys:
                course, event_type, title, date, weight, raw_line
        """
        if not text or not text.strip():
            logger.warning("Empty text passed to NLP engine")
            return []

        events = []
        lines = text.split('\n')

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 5:
                continue

            # Step 1: Detect event type via keyword heuristics
            event_info = detect_event_type(line)

            # Step 1b: ML classifier fallback — only fires when keywords miss
            if event_info is None and self.classifier:
                ml_label = self.classifier.predict(line)
                if ml_label:
                    proba = self.classifier.predict_proba(line)
                    confidence = proba.get(ml_label, 0.0)
                    if confidence >= ML_CONFIDENCE_THRESHOLD:
                        event_info = {
                            'event_type': ml_label,
                            'weight': 1,  # conservative weight for ML-sourced hits
                            'matched_keyword': None,
                            'ml_confidence': round(confidence, 3),
                            'source': 'ml_classifier',
                        }
                        logger.debug(
                            f"ML classifier caught line (label={ml_label}, "
                            f"confidence={confidence:.2f}): {line[:80]}"
                        )

            if not event_info:
                continue

            # Step 2: Extract dates from same line
            dates_found = extract_dates_from_line(line, self.reference_year)

            # Step 3: If no date on this line, check surrounding lines (±2)
            if not dates_found:
                context_lines = lines[max(0, line_num - 2): min(len(lines), line_num + 3)]
                for ctx_line in context_lines:
                    dates_found = extract_dates_from_line(ctx_line, self.reference_year)
                    if dates_found:
                        break

            # Step 4: Produce event record for each date found
            ml_confidence = event_info.get('ml_confidence')  # None for keyword hits
            detection_source = event_info.get('source', 'keyword')

            if dates_found:
                for raw_date_str, parsed_date in dates_found:
                    title = extract_event_title(line, event_info['event_type'])
                    event_dict = {
                        'course': course_name,
                        'event_type': event_info['event_type'],
                        'title': title,
                        'date': parsed_date,
                        'weight': event_info['weight'],
                        'matched_keyword': event_info['matched_keyword'],
                        'source': detection_source,
                        'raw_line': line[:300],
                    }
                    if ml_confidence is not None:
                        event_dict['ml_confidence'] = ml_confidence
                    events.append(event_dict)
            else:
                # Record event without a date (still useful for warnings)
                title = extract_event_title(line, event_info['event_type'])
                event_dict = {
                    'course': course_name,
                    'event_type': event_info['event_type'],
                    'title': title,
                    'date': None,
                    'weight': event_info['weight'],
                    'matched_keyword': event_info['matched_keyword'],
                    'source': detection_source,
                    'raw_line': line[:300],
                }
                if ml_confidence is not None:
                    event_dict['ml_confidence'] = ml_confidence
                events.append(event_dict)

        # Deduplicate events on same date with same type
        events = self._deduplicate_events(events)
        logger.info(f"NLP engine extracted {len(events)} events from course '{course_name}'")
        return events

    def _deduplicate_events(self, events: list) -> list:
        """Remove duplicate events (same date + same event_type + same course)."""
        seen = set()
        unique = []
        for e in events:
            key = (e['course'], e['event_type'], str(e['date']))
            if key not in seen:
                seen.add(key)
                unique.append(e)
        return unique
