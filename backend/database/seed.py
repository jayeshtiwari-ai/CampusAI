"""
backend/database/seed.py - SQLite Database Seeder for CampusAI

Populates sample college data for courses, fees, faculty, rooms, timetable,
exams, notices, contacts, and room bookings.
"""

import sys
from pathlib import Path

# Add project root directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import sqlite3
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger("campusai.database.seed")

DB_DIR: Path = settings.BASE_DIR / "data"
DB_FILE_PATH: Path = DB_DIR / "campusai.db"
SCHEMA_FILE_PATH: Path = settings.BASE_DIR / "backend" / "database" / "schema.sql"


def seed_database() -> None:
    """Initialize SQLite database schema and seed realistic sample college records."""
    DB_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Initializing database at %s...", DB_FILE_PATH)
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()

    # Read and execute schema script
    with open(SCHEMA_FILE_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    cursor.executescript(schema_sql)

    logger.info("Database schema applied. Inserting sample records...")

    # 1. Courses
    courses_data = [
        ("B.Tech Artificial Intelligence & Data Science", "AI-DS", 4, 120, "10+2 with Physics & Math, min 45% aggregate (40% for reserved)"),
        ("B.Tech Computer Science & Engineering", "CSE", 4, 180, "10+2 with Physics & Math, min 45% aggregate (40% for reserved)"),
        ("B.Tech Electronics & Telecommunication", "ENTC", 4, 60, "10+2 with Physics & Math, min 45% aggregate (40% for reserved)"),
        ("B.Tech Mechanical Engineering", "MECH", 4, 60, "10+2 with Physics & Math, min 45% aggregate (40% for reserved)"),
    ]
    cursor.executemany(
        "INSERT INTO courses (name, code, duration_years, seats, eligibility_summary) VALUES (?, ?, ?, ?, ?)",
        courses_data
    )

    # 2. Fees
    fees_data = [
        (1, 1, 135000.0, 15000.0, 150000.0),
        (2, 1, 130000.0, 15000.0, 145000.0),
        (3, 1, 115000.0, 15000.0, 130000.0),
        (4, 1, 105000.0, 15000.0, 120000.0),
    ]
    cursor.executemany(
        "INSERT INTO fees (course_id, year, tuition_fee, other_fee, total_fee) VALUES (?, ?, ?, ?, ?)",
        fees_data
    )

    # 3. Faculty
    faculty_data = [
        ("Dr. Rajesh Sharma", "Computer Science", "Head of Department (HOD)", "Cabin C-301, 3rd Floor", "r.sharma@campusai-edu.in", "+91 98765 43210"),
        ("Prof. Sunita Patil", "Computer Science", "Assistant Professor", "Cabin C-305, 3rd Floor", "s.patil@campusai-edu.in", "+91 98765 43211"),
        ("Dr. Anand Deshmukh", "AI & Data Science", "HOD AI & DS", "Cabin A-202, 2nd Floor", "a.deshmukh@campusai-edu.in", "+91 98765 43212"),
        ("Prof. Vikram Kulkarni", "Electronics", "Associate Professor", "Cabin E-104, 1st Floor", "v.kulkarni@campusai-edu.in", "+91 98765 43213"),
        ("Dr. Meena Joshi", "Mechanical", "HOD Mechanical", "Cabin M-101, Ground Floor", "m.joshi@campusai-edu.in", "+91 98765 43214"),
    ]
    cursor.executemany(
        "INSERT INTO faculty (name, department, designation, cabin, email, phone) VALUES (?, ?, ?, ?, ?, ?)",
        faculty_data
    )

    # 4. Rooms
    rooms_data = [
        ("Seminar Hall A", "hall", "Main Academic Block", 1, "Enter Main Gate, turn right to Academic Block 1st Floor.", 200),
        ("Auditorium B", "hall", "Central Cultural Block", 0, "Walk straight from Reception for 100 meters.", 500),
        ("Lab C-302 (AI Lab)", "lab", "Academic Block C", 3, "Take Elevator in Block C to 3rd Floor, turn left.", 40),
        ("Lab C-304 (Web Tech Lab)", "lab", "Academic Block C", 3, "Take Elevator in Block C to 3rd Floor, room 304.", 40),
        ("Classroom C-201", "classroom", "Academic Block C", 2, "Block C 2nd Floor, Room 201 opposite elevator.", 70),
        ("Classroom C-202", "classroom", "Academic Block C", 2, "Block C 2nd Floor, Room 202 next to stairs.", 70),
        ("Principal Office", "office", "Administrative Block", 0, "Ground floor Administrative Block right wing.", 20),
        ("Admissions Desk", "office", "Main Reception Lobby", 0, "Main Entrance Lobby Desk #3.", 30),
    ]
    cursor.executemany(
        "INSERT INTO rooms (name, type, building, floor, directions_text, capacity) VALUES (?, ?, ?, ?, ?, ?)",
        rooms_data
    )

    # 5. Timetable
    timetable_data = [
        ("B.Tech CSE Year 2", "Monday", "09:00", "10:00", "Data Structures & Algorithms", 5),
        ("B.Tech CSE Year 2", "Monday", "10:00", "11:00", "Database Management Systems", 5),
        ("B.Tech AI-DS Year 2", "Monday", "09:00", "11:00", "Machine Learning Lab", 3),
        ("Dr. Rajesh Sharma", "Monday", "09:00", "10:00", "Data Structures", 5),
        ("Prof. Sunita Patil", "Monday", "10:00", "11:00", "DBMS Lecture", 5),
        ("B.Tech CSE Year 2", "Tuesday", "11:00", "12:00", "Computer Networks", 6),
    ]
    cursor.executemany(
        "INSERT INTO timetable (class_or_faculty, day, start_time, end_time, subject, room_id) VALUES (?, ?, ?, ?, ?, ?)",
        timetable_data
    )

    # 6. Exams
    exams_data = [
        ("Data Structures & Algorithms", "B.Tech CSE", "2026-11-15", "10:00", 5),
        ("Database Management Systems", "B.Tech CSE", "2026-11-17", "10:00", 6),
        ("Machine Learning", "B.Tech AI-DS", "2026-11-18", "14:00", 3),
    ]
    cursor.executemany(
        "INSERT INTO exams (subject, course, exam_date, start_time, room_id) VALUES (?, ?, ?, ?, ?)",
        exams_data
    )

    # 7. Notices
    notices_data = [
        ("First Year B.Tech Application Deadline", "Online registration for B.Tech closes June 30, 2026.", "2026-05-15", "admission"),
        ("Mid-Semester Exam Timetable Published", "Mid-semester exams begin November 15, 2026. Hall tickets available on portal.", "2026-10-01", "exam"),
        ("Annual Cultural Festival 'CampusPulse 2026'", "Annual fest celebrated on December 20-22, 2026 at Auditorium B.", "2026-10-05", "general"),
    ]
    cursor.executemany(
        "INSERT INTO notices (title, body, date, category) VALUES (?, ?, ?, ?)",
        notices_data
    )

    # 8. Contacts
    contacts_data = [
        ("Admissions", "Mr. Ramesh Kulkarni (Incharge)", "+91 98765 00001", "admissions@campusai-edu.in", "Main Reception Desk 3"),
        ("Accounts & Fees", "Mrs. Priya Shinde", "+91 98765 00002", "accounts@campusai-edu.in", "Admin Block Room 102"),
        ("Exam Cell", "Prof. Vijay Thorat", "+91 98765 00003", "examcell@campusai-edu.in", "Academic Block B Room 205"),
        ("Hostel Office", "Warden Office", "+91 98765 00004", "hostel@campusai-edu.in", "Boys Hostel Building A"),
    ]
    cursor.executemany(
        "INSERT INTO contacts (department, name, phone, email, location) VALUES (?, ?, ?, ?, ?)",
        contacts_data
    )

    # 9. Bookings
    bookings_data = [
        (1, "2026-10-08", "14:00", "16:00", "ACM Student Chapter Meeting"),
        (2, "2026-10-09", "10:00", "13:00", "National Robotics Workshop"),
    ]
    cursor.executemany(
        "INSERT INTO bookings (room_id, booking_date, start_time, end_time, booked_by) VALUES (?, ?, ?, ?, ?)",
        bookings_data
    )

    conn.commit()
    conn.close()
    logger.info("Database seeding completed successfully.")


if __name__ == "__main__":
    seed_database()
