-- ============================================================
-- Smart Campus AI System — Full MySQL Schema
-- ============================================================
CREATE DATABASE IF NOT EXISTS smart_campus_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_campus_db;

CREATE TABLE IF NOT EXISTS departments (
  dept_id INT NOT NULL AUTO_INCREMENT, name VARCHAR(100) NOT NULL UNIQUE,
  code VARCHAR(10) NOT NULL UNIQUE, hod_name VARCHAR(100),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (dept_id)) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS students (
  student_id INT NOT NULL AUTO_INCREMENT, reg_number VARCHAR(20) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL, email VARCHAR(150) NOT NULL UNIQUE, phone VARCHAR(15),
  password_hash VARCHAR(256) NOT NULL, dept_id INT NOT NULL,
  semester INT NOT NULL DEFAULT 1, year INT NOT NULL DEFAULT 1,
  photo_path VARCHAR(255), is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (student_id), INDEX ix_students_reg(reg_number), INDEX ix_students_email(email),
  FOREIGN KEY (dept_id) REFERENCES departments(dept_id)) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS faculty (
  faculty_id INT NOT NULL AUTO_INCREMENT, employee_id VARCHAR(20) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL, email VARCHAR(150) NOT NULL UNIQUE, phone VARCHAR(15),
  password_hash VARCHAR(256) NOT NULL, dept_id INT NOT NULL, designation VARCHAR(100),
  is_active TINYINT(1) NOT NULL DEFAULT 1, created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (faculty_id), FOREIGN KEY (dept_id) REFERENCES departments(dept_id)) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS admins (
  admin_id INT NOT NULL AUTO_INCREMENT, username VARCHAR(50) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL, email VARCHAR(150) NOT NULL UNIQUE,
  password_hash VARCHAR(256) NOT NULL, is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (admin_id)) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS subjects (
  subject_id INT NOT NULL AUTO_INCREMENT, code VARCHAR(20) NOT NULL UNIQUE,
  name VARCHAR(150) NOT NULL, credits INT DEFAULT 3, dept_id INT NOT NULL,
  faculty_id INT, semester INT NOT NULL, is_lab TINYINT(1) DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (subject_id),
  FOREIGN KEY (dept_id) REFERENCES departments(dept_id),
  FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id)) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS face_encodings (
  encoding_id INT NOT NULL AUTO_INCREMENT,
  user_type VARCHAR(20) NOT NULL DEFAULT 'student',
  user_id INT NOT NULL,
  student_id INT NOT NULL,
  encoding_data MEDIUMBLOB NOT NULL, model_used VARCHAR(50) DEFAULT 'Facenet512',
  image_path VARCHAR(255), created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (encoding_id),
  FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS attendance (
  attend_id INT NOT NULL AUTO_INCREMENT, student_id INT NOT NULL, subject_id INT NOT NULL,
  date DATE NOT NULL, time_in DATETIME, time_out DATETIME,
  status ENUM('Present','Late','Absent') NOT NULL DEFAULT 'Absent',
  confidence_score FLOAT, is_manual TINYINT(1) DEFAULT 0, notes VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (attend_id),
  UNIQUE KEY uq_student_subject_date (student_id,subject_id,date),
  INDEX ix_attendance_date(date), INDEX ix_attendance_student(student_id),
  FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
  FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS marks (
  mark_id INT NOT NULL AUTO_INCREMENT, student_id INT NOT NULL, subject_id INT NOT NULL,
  semester INT NOT NULL, year INT NOT NULL,
  cia1 FLOAT DEFAULT 0, cia2 FLOAT DEFAULT 0, lab_mark FLOAT DEFAULT 0,
  assignment FLOAT DEFAULT 0, total FLOAT DEFAULT 0, gpa FLOAT DEFAULT 0,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (mark_id),
  UNIQUE KEY uq_marks_student_subject (student_id,subject_id,semester,year),
  FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
  FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS assignments (
  assign_id INT NOT NULL AUTO_INCREMENT, title VARCHAR(200) NOT NULL, description TEXT,
  subject_id INT NOT NULL, student_id INT NOT NULL, due_date DATETIME NOT NULL,
  submitted_at DATETIME, status ENUM('Pending','Submitted','Late','Missing') DEFAULT 'Pending',
  marks_obtained FLOAT DEFAULT 0, max_marks FLOAT DEFAULT 10, file_path VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (assign_id),
  FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
  FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS timetable (
  tt_id INT NOT NULL AUTO_INCREMENT, dept_id INT NOT NULL, semester INT NOT NULL,
  subject_id INT NOT NULL, faculty_id INT,
  day ENUM('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday') NOT NULL,
  period_number INT NOT NULL, start_time TIME NOT NULL, end_time TIME NOT NULL, room VARCHAR(20),
  PRIMARY KEY (tt_id), UNIQUE KEY uq_timetable_slot (dept_id,semester,day,period_number),
  FOREIGN KEY (dept_id) REFERENCES departments(dept_id),
  FOREIGN KEY (subject_id) REFERENCES subjects(subject_id),
  FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id)) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS risk_predictions (
  pred_id INT NOT NULL AUTO_INCREMENT, student_id INT NOT NULL,
  risk_level ENUM('Safe','Moderate','High') NOT NULL,
  attend_pct FLOAT, avg_marks FLOAT, assign_pct FLOAT, prev_gpa FLOAT, lab_score FLOAT,
  model_used VARCHAR(50), accuracy FLOAT, confidence FLOAT,
  predicted_at DATETIME DEFAULT CURRENT_TIMESTAMP, notified TINYINT(1) DEFAULT 0,
  PRIMARY KEY (pred_id),
  FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS security_logs (
  log_id INT NOT NULL AUTO_INCREMENT,
  event_type ENUM('unknown_face','spoof_attempt','forced_entry','system_alert') NOT NULL,
  image_path VARCHAR(255), location VARCHAR(100), camera_id VARCHAR(50), description TEXT,
  timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  alert_sent TINYINT(1) DEFAULT 0, resolved TINYINT(1) DEFAULT 0,
  PRIMARY KEY (log_id), INDEX ix_security_timestamp(timestamp)) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS notifications (
  notif_id INT NOT NULL AUTO_INCREMENT, student_id INT NOT NULL,
  title VARCHAR(200) NOT NULL, message TEXT NOT NULL,
  notif_type ENUM('low_attendance','high_risk','assignment_due','general') DEFAULT 'general',
  is_read TINYINT(1) DEFAULT 0, email_sent TINYINT(1) DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (notif_id),
  FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE) ENGINE=InnoDB;
