"""
backend/database/db.py - Database Interface & Parameterized Tool Functions

Provides secure, parameterized SQL helper functions for querying college database tables.
NEVER exposes raw SQL execution to LLM input strings.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger("campusai.database.db")

DB_FILE_PATH: Path = settings.BASE_DIR / "data" / "campusai.db"


def get_db_connection() -> sqlite3.Connection:
    """Create and return a row-factory connection to SQLite database."""
    if not DB_FILE_PATH.exists():
        logger.warning("Database file missing at %s. Initializing DB...", DB_FILE_PATH)
        from backend.database.seed import seed_database
        seed_database()

    conn = sqlite3.connect(DB_FILE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_course_fees(course_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve tuition and total annual fees for courses.

    Args:
        course_name: Optional partial or full course name filter (e.g. 'CSE', 'AI').
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if course_name:
        query = """
            SELECT c.name as course_name, c.code, f.year, f.tuition_fee, f.other_fee, f.total_fee, c.eligibility_summary
            FROM fees f
            JOIN courses c ON f.course_id = c.id
            WHERE c.name LIKE ? OR c.code LIKE ?
        """
        param = f"%{course_name.strip()}%"
        rows = cursor.execute(query, (param, param)).fetchall()
    else:
        query = """
            SELECT c.name as course_name, c.code, f.year, f.tuition_fee, f.other_fee, f.total_fee, c.eligibility_summary
            FROM fees f
            JOIN courses c ON f.course_id = c.id
        """
        rows = cursor.execute(query).fetchall()

    conn.close()
    return [dict(r) for r in rows]


def get_admission_dates() -> List[Dict[str, Any]]:
    """Retrieve important admission notices and dates."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT title, body, date, category FROM notices WHERE category = 'admission' ORDER BY date DESC"
    rows = cursor.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def find_room(name: str) -> Optional[Dict[str, Any]]:
    """Find room details, floor, building, and directions by room name or code."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT id, name, type, building, floor, directions_text, capacity FROM rooms WHERE name LIKE ?"
    param = f"%{name.strip()}%"
    row = cursor.execute(query, (param,)).fetchone()
    conn.close()
    return dict(row) if row else None


def room_free_now(room_name: str, target_time: Optional[str] = None) -> Dict[str, Any]:
    """
    Check if a specific room or hall is currently free or booked.

    Args:
        room_name: Name of room/hall (e.g. 'Seminar Hall A', 'Lab C-302').
        target_time: Optional HH:MM time string. Defaults to current local time.
    """
    room = find_room(room_name)
    if not room:
        return {"room_name": room_name, "found": False, "is_free": False, "reason": "Room not found in database."}

    room_id = room["id"]
    now_str = target_time or datetime.now().strftime("%H:%M")
    today_date = datetime.now().strftime("%Y-%m-%d")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check active bookings
    query_b = """
        SELECT booked_by, start_time, end_time FROM bookings
        WHERE room_id = ? AND booking_date = ? AND start_time <= ? AND end_time > ?
    """
    booking = cursor.execute(query_b, (room_id, today_date, now_str, now_str)).fetchone()

    # Check timetable classes
    day_name = datetime.now().strftime("%A")
    query_t = """
        SELECT class_or_faculty, subject, start_time, end_time FROM timetable
        WHERE room_id = ? AND day = ? AND start_time <= ? AND end_time > ?
    """
    class_occupied = cursor.execute(query_t, (room_id, day_name, now_str, now_str)).fetchone()

    conn.close()

    if booking:
        return {
            "room_name": room["name"],
            "found": True,
            "is_free": False,
            "reason": f"Booked for '{booking['booked_by']}' until {booking['end_time']}.",
            "room_details": room
        }
    elif class_occupied:
        return {
            "room_name": room["name"],
            "found": True,
            "is_free": False,
            "reason": f"Occupied by '{class_occupied['class_or_faculty']}' for subject '{class_occupied['subject']}' until {class_occupied['end_time']}.",
            "room_details": room
        }

    return {
        "room_name": room["name"],
        "found": True,
        "is_free": True,
        "reason": f"Room '{room['name']}' is currently FREE for use.",
        "room_details": room
    }


def get_timetable(entity: str, day: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve schedule timetable for a class or faculty member."""
    conn = get_db_connection()
    cursor = conn.cursor()
    param = f"%{entity.strip()}%"

    if day:
        query = """
            SELECT t.class_or_faculty, t.day, t.start_time, t.end_time, t.subject, r.name as room_name, r.building, r.floor
            FROM timetable t
            JOIN rooms r ON t.room_id = r.id
            WHERE t.class_or_faculty LIKE ? AND LOWER(t.day) = LOWER(?)
            ORDER BY t.start_time ASC
        """
        rows = cursor.execute(query, (param, day.strip())).fetchall()
    else:
        query = """
            SELECT t.class_or_faculty, t.day, t.start_time, t.end_time, t.subject, r.name as room_name, r.building, r.floor
            FROM timetable t
            JOIN rooms r ON t.room_id = r.id
            WHERE t.class_or_faculty LIKE ?
            ORDER BY t.day, t.start_time ASC
        """
        rows = cursor.execute(query, (param,)).fetchall()

    conn.close()
    return [dict(r) for r in rows]


def get_exam_schedule(subject_or_course: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve upcoming examination schedule."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if subject_or_course:
        param = f"%{subject_or_course.strip()}%"
        query = """
            SELECT e.subject, e.course, e.exam_date, e.start_time, r.name as room_name, r.building, r.floor
            FROM exams e
            JOIN rooms r ON e.room_id = r.id
            WHERE e.subject LIKE ? OR e.course LIKE ?
            ORDER BY e.exam_date ASC
        """
        rows = cursor.execute(query, (param, param)).fetchall()
    else:
        query = """
            SELECT e.subject, e.course, e.exam_date, e.start_time, r.name as room_name, r.building, r.floor
            FROM exams e
            JOIN rooms r ON e.room_id = r.id
            ORDER BY e.exam_date ASC
        """
        rows = cursor.execute(query).fetchall()

    conn.close()
    return [dict(r) for r in rows]


def latest_notices(n: int = 5, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve latest N college announcements and notices."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if category:
        query = "SELECT title, body, date, category FROM notices WHERE category = ? ORDER BY date DESC LIMIT ?"
        rows = cursor.execute(query, (category.strip(), n)).fetchall()
    else:
        query = "SELECT title, body, date, category FROM notices ORDER BY date DESC LIMIT ?"
        rows = cursor.execute(query, (n,)).fetchall()

    conn.close()
    return [dict(r) for r in rows]


def find_faculty(name_or_dept: str) -> List[Dict[str, Any]]:
    """Search faculty members by name or department."""
    conn = get_db_connection()
    cursor = conn.cursor()
    param = f"%{name_or_dept.strip()}%"

    query = """
        SELECT name, department, designation, cabin, email, phone
        FROM faculty
        WHERE name LIKE ? OR department LIKE ?
    """
    rows = cursor.execute(query, (param, param)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_contact(department: str) -> Optional[Dict[str, Any]]:
    """Retrieve contact details for a specific administrative department."""
    conn = get_db_connection()
    cursor = conn.cursor()
    param = f"%{department.strip()}%"

    query = "SELECT department, name, phone, email, location FROM contacts WHERE department LIKE ?"
    row = cursor.execute(query, (param,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_directions(place: str) -> Optional[Dict[str, Any]]:
    """Retrieve navigation directions to a room, lab, or office."""
    room = find_room(place)
    if not room:
        return None

    steps = [
        f"Start at Main Reception Desk.",
        f"Proceed to {room['building']}.",
        f"Go to Floor {room['floor']}.",
        f"Follow directions: {room['directions_text']}"
    ]

    return {
        "place": room["name"],
        "building": room["building"],
        "floor": room["floor"],
        "directions_text": room["directions_text"],
        "steps": steps,
        "map_id": f"MAP_{room['building'].replace(' ', '_').upper()}_F{room['floor']}",
        "qr_payload": f"CAMPUS_NAV:{room['name']}:{room['building']}:F{room['floor']}"
    }
