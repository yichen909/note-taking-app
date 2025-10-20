import calendar
import json
import re
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from src.models.note import Note, db

note_bp = Blueprint("note", __name__)


def _add_months(base_date, months):
    month = base_date.month - 1 + months
    year = base_date.year + month // 12
    month = month % 12 + 1
    day = min(base_date.day, calendar.monthrange(year, month)[1])
    return base_date.replace(year=year, month=month, day=day)


def _safe_add_years(base_date, years):
    try:
        return base_date.replace(year=base_date.year + years)
    except ValueError:
        # Handle Feb 29 gracefully by falling back to Feb 28
        return base_date.replace(month=2, day=28, year=base_date.year + years)


def _parse_date(value):
    if not value:
        return None

    if isinstance(value, datetime):
        base_local = value + timedelta(hours=8)
        return base_local.date()

    text = str(value).strip()

    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except (ValueError, TypeError):
            continue

    today = (datetime.utcnow() + timedelta(hours=8)).date()
    lowered = text.lower()

    keyword_offsets = {
        "today": 0,
        "tomorrow": 1,
        "yesterday": -1,
    }
    if lowered in keyword_offsets:
        return today + timedelta(days=keyword_offsets[lowered])

    if lowered in {"next week", "in a week"}:
        return today + timedelta(weeks=1)
    if lowered in {"next month", "in a month"}:
        return _add_months(today, 1)
    if lowered in {"next year", "in a year"}:
        return _safe_add_years(today, 1)

    in_days = re.match(r"in\s+(\d+)\s+day", lowered)
    if in_days:
        return today + timedelta(days=int(in_days.group(1)))

    in_weeks = re.match(r"in\s+(\d+)\s+week", lowered)
    if in_weeks:
        return today + timedelta(weeks=int(in_weeks.group(1)))

    in_months = re.match(r"in\s+(\d+)\s+month", lowered)
    if in_months:
        return _add_months(today, int(in_months.group(1)))

    in_years = re.match(r"in\s+(\d+)\s+year", lowered)
    if in_years:
        return _safe_add_years(today, int(in_years.group(1)))

    next_weekday = re.match(r"next\s+([a-z]+)", lowered)
    if next_weekday:
        target = next_weekday.group(1)
        weekday_map = {day.lower(): idx for idx, day in enumerate(calendar.day_name)}
        if target in weekday_map:
            current = today.weekday()
            desired = weekday_map[target]
            days_ahead = (desired - current) % 7
            days_ahead = days_ahead or 7
            return today + timedelta(days=days_ahead)

    return None


def _parse_time(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%H:%M").time()
    except (ValueError, TypeError):
        return None


def _normalize_tags(tags_value):
    if not tags_value:
        return ""
    if isinstance(tags_value, list):
        return ", ".join(tag.strip() for tag in tags_value if tag and tag.strip())
    return ", ".join(part.strip() for part in tags_value.split(",") if part.strip())


def _extract_json_payload(raw_text):
    """Best-effort JSON parsing for LLM responses."""
    if not raw_text:
        return {}

    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if "\n" in cleaned:
            cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.strip()
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start : end + 1]

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {}


@note_bp.route("/notes", methods=["GET"])
def get_notes():
    """Get all notes, ordered by most recent update."""
    notes = Note.query.order_by(Note.updated_at.desc()).all()
    return jsonify([note.to_dict() for note in notes])


@note_bp.route("/notes", methods=["POST"])
def create_note():
    """Create a new note."""
    try:
        data = request.json or {}
        title = (data.get("title") or "").strip()
        content = (data.get("content") or "").strip()

        if not title and not content:
            return jsonify({"error": "Title and content are required"}), 400

        note = Note(
            title=title or "Untitled",
            content=content,
            tags=_normalize_tags(data.get("tags")),
            event_date=_parse_date(data.get("event_date")),
            event_time=_parse_time(data.get("event_time")),
        )
        db.session.add(note)
        db.session.commit()
        return jsonify(note.to_dict()), 201
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500


@note_bp.route("/notes/<int:note_id>", methods=["GET"])
def get_note(note_id):
    """Get a specific note by ID."""
    note = Note.query.get_or_404(note_id)
    return jsonify(note.to_dict())


@note_bp.route("/notes/<int:note_id>", methods=["PUT"])
def update_note(note_id):
    """Update a specific note."""
    try:
        note = Note.query.get_or_404(note_id)
        data = request.json or {}

        if not data:
            return jsonify({"error": "No data provided"}), 400

        if "title" in data:
            note.title = (data.get("title") or "").strip() or note.title
        if "content" in data:
            note.content = data.get("content", note.content)
        if "tags" in data:
            note.tags = _normalize_tags(data.get("tags"))
        if "event_date" in data:
            note.event_date = _parse_date(data.get("event_date"))
        if "event_time" in data:
            note.event_time = _parse_time(data.get("event_time"))

        db.session.commit()
        return jsonify(note.to_dict())
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500


@note_bp.route("/notes/<int:note_id>/translate", methods=["POST"])
def translate_note(note_id):
    """Translate a note's content to a target language using the LLM helper."""
    try:
        data = request.json or {}
        if "target_language" not in data:
            return jsonify({"error": "target_language is required"}), 400

        target_language = data["target_language"]
        note = Note.query.get_or_404(note_id)

        from src.llm import translate as llm_translate

        translated_title = llm_translate(note.title or "", target_language)
        translated_content = llm_translate(note.content or "", target_language)

        return jsonify(
            {
                "translated_title": translated_title,
                "translated_content": translated_content,
            }
        ), 200
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500


@note_bp.route("/notes/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    """Delete a specific note."""
    try:
        note = Note.query.get_or_404(note_id)
        db.session.delete(note)
        db.session.commit()
        return "", 204
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500


@note_bp.route("/notes/search", methods=["GET"])
def search_notes():
    """Search notes by title, content, or tags."""
    query = request.args.get("q", "")
    if not query:
        return jsonify([])

    notes = (
        Note.query.filter(
            (Note.title.contains(query))
            | (Note.content.contains(query))
            | (Note.tags.contains(query))
        )
        .order_by(Note.updated_at.desc())
        .all()
    )

    return jsonify([note.to_dict() for note in notes])


@note_bp.route("/notes/generate", methods=["POST"])
def generate_note():
    """Generate structured note data from natural language input."""
    payload = request.json or {}
    prompt = (payload.get("prompt") or "").strip()
    language = (payload.get("language") or "english").strip() or "english"

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    try:
        from src.llm import extract_structured_notes

        llm_response = extract_structured_notes(prompt, lang=language)
        structured = _extract_json_payload(llm_response)

        if not structured:
            raise ValueError("Unable to parse generated note. Please try again.")

        title = structured.get("Title") or structured.get("title") or ""
        notes_content = structured.get("Notes") or structured.get("content") or ""
        tags = structured.get("Tags") or structured.get("tags") or ""
        event_date = structured.get("Event Date") or structured.get("event_date")
        event_time = structured.get("Event Time") or structured.get("event_time")

        normalized_tags = _normalize_tags(tags)
        parsed_event_date = _parse_date(event_date)
        parsed_event_time = _parse_time(event_time)

        if parsed_event_date is None:
            parsed_event_date = (datetime.utcnow() + timedelta(hours=8)).date()

        if parsed_event_time is None:
            now = datetime.utcnow() + timedelta(hours=8)
            parsed_event_time = now.replace(second=0, microsecond=0).time()

        response_payload = {
            "title": title,
            "content": notes_content,
            "tags": normalized_tags,
            "event_date": parsed_event_date.isoformat() if parsed_event_date else None,
            "event_time": parsed_event_time.strftime("%H:%M") if parsed_event_time else None,
        }
        return jsonify(response_payload), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
