-- CampusAI Database Schema (SQLite)

DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS exams;
DROP TABLE IF EXISTS timetable;
DROP TABLE IF EXISTS rooms;
DROP TABLE IF EXISTS faculty;
DROP TABLE IF EXISTS fees;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS notices;
DROP TABLE IF EXISTS contacts;

-- 1. Courses Table
CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    code TEXT NOT NULL,
    duration_years INTEGER NOT NULL DEFAULT 4,
    seats INTEGER NOT NULL,
    eligibility_summary TEXT NOT NULL
);

-- 2. Fees Table
CREATE TABLE fees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    tuition_fee REAL NOT NULL,
    other_fee REAL NOT NULL,
    total_fee REAL NOT NULL,
    FOREIGN KEY (course_id) REFERENCES courses (id)
);

-- 3. Faculty Table
CREATE TABLE faculty (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    designation TEXT NOT NULL,
    cabin TEXT NOT NULL,
    email TEXT UNIQUE,
    phone TEXT
);

-- 4. Rooms Table (Classrooms, Labs, Halls, Offices)
CREATE TABLE rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL, -- 'classroom', 'lab', 'hall', 'office'
    building TEXT NOT NULL,
    floor INTEGER NOT NULL,
    directions_text TEXT NOT NULL,
    capacity INTEGER NOT NULL
);

-- 5. Timetable Table
CREATE TABLE timetable (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_or_faculty TEXT NOT NULL, -- e.g. 'B.Tech CSE Year 2' or 'Dr. Rajesh Sharma'
    day TEXT NOT NULL, -- 'Monday', 'Tuesday', etc.
    start_time TEXT NOT NULL, -- '09:00'
    end_time TEXT NOT NULL,   -- '10:00'
    subject TEXT NOT NULL,
    room_id INTEGER NOT NULL,
    FOREIGN KEY (room_id) REFERENCES rooms (id)
);

-- 6. Exams Table
CREATE TABLE exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    course TEXT NOT NULL,
    exam_date TEXT NOT NULL, -- 'YYYY-MM-DD'
    start_time TEXT NOT NULL,
    room_id INTEGER NOT NULL,
    FOREIGN KEY (room_id) REFERENCES rooms (id)
);

-- 7. Notices Table
CREATE TABLE notices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    date TEXT NOT NULL,
    category TEXT NOT NULL -- 'admission', 'academics', 'exam', 'general'
);

-- 8. Contacts Table
CREATE TABLE contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    department TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    location TEXT NOT NULL
);

-- 9. Bookings Table
CREATE TABLE bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    booking_date TEXT NOT NULL, -- 'YYYY-MM-DD'
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    booked_by TEXT NOT NULL,
    FOREIGN KEY (room_id) REFERENCES rooms (id)
);
