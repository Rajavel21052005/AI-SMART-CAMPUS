# ============================================================
# config/config.py — Application Configuration
# Loads all settings from environment variables (.env)
# ============================================================

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file into environment
load_dotenv()


class Config:
    """Base configuration — shared across all environments."""

    # --- Flask core ---
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    WTF_CSRF_ENABLED = True

    # --- SQLAlchemy / MySQL ---
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_NAME = os.environ.get('DB_NAME', 'smart_campus_db')
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Set True to log all SQL queries

    # --- Flask-Login ---
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    SESSION_PROTECTION = 'strong'

    # --- JWT ---
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-change-me')
    JWT_EXPIRY_HOURS = int(os.environ.get('JWT_EXPIRY_HOURS', 24))

    # --- Flask-Mail (SMTP) ---
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'Smart Campus <noreply@campus.edu>')

    # --- File uploads ---
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'app/static/images/uploads')
    SECURITY_FOLDER = os.environ.get('UNKNOWN_SAVE_PATH', 'app/static/images/security')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_PHOTO_SIZE_MB', 5)) * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

    # --- Face Recognition ---
    DEEPFACE_HOME = os.environ.get('DEEPFACE_HOME', 'ai_models/deepface')
    FACE_RECOGNITION_THRESHOLD = float(os.environ.get('FACE_RECOGNITION_THRESHOLD', 0.60))
    FACE_MODEL = os.environ.get('FACE_MODEL', 'Facenet512')
    FACE_DETECTOR = os.environ.get('FACE_DETECTOR', 'retinaface')

    # --- Liveness Detection ---
    LIVENESS_BLINK_THRESHOLD = int(os.environ.get('LIVENESS_BLINK_THRESHOLD', 3))

    # --- Attendance Rules ---
    LATE_THRESHOLD_MINUTES = int(os.environ.get('LATE_THRESHOLD_MINUTES', 10))
    MIN_ATTENDANCE_PERCENT = float(os.environ.get('MIN_ATTENDANCE_PERCENT', 75.0))

    # --- ML Models ---
    RISK_MODEL_PATH = os.environ.get('RISK_MODEL_PATH', 'ai_models/risk_model.pkl')
    RISK_RETRAIN_INTERVAL_DAYS = int(os.environ.get('RISK_RETRAIN_INTERVAL_DAYS', 7))

    # --- Logging ---
    LOG_FOLDER = 'logs'
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')


class DevelopmentConfig(Config):
    """Development-specific settings."""
    DEBUG = True
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    """Production-specific settings — stricter and optimized."""
    DEBUG = False
    TESTING = False
    SQLALCHEMY_ECHO = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = True


class TestingConfig(Config):
    """Test-specific settings — uses in-memory SQLite."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True


# Map environment name → config class
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}

# Active config — defaults to development
ActiveConfig = config_map.get(os.environ.get('FLASK_ENV', 'development'), DevelopmentConfig)
