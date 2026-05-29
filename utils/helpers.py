# ============================================================
# utils/helpers.py — Reusable utility functions
# ============================================================
import os
import uuid
from datetime import datetime, date
from flask import current_app
from werkzeug.utils import secure_filename


def allowed_file(filename):
    """Return True if the file extension is allowed."""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in current_app.config.get('ALLOWED_EXTENSIONS', {'jpg', 'jpeg', 'png'})


def save_uploaded_photo(file_obj, subfolder=''):
    """
    Save an uploaded photo to UPLOAD_FOLDER.
    Returns the relative file path, or None on failure.
    """
    if not file_obj or not allowed_file(file_obj.filename):
        return None
    ext = file_obj.filename.rsplit('.', 1)[-1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    folder = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(folder, exist_ok=True)
    save_path = os.path.join(folder, unique_name)
    file_obj.save(save_path)
    return save_path


def today_str():
    """Return today's date as ISO string YYYY-MM-DD."""
    return date.today().isoformat()


def now_str():
    """Return current UTC datetime as string."""
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')


def attendance_status_color(status_str):
    """Return Bootstrap color class for an attendance status string."""
    mapping = {
        'Present':  'success',
        'Late':     'warning',
        'Absent':   'danger',
    }
    return mapping.get(status_str, 'secondary')


def risk_level_color(risk_str):
    """Return Bootstrap color class for a risk level string."""
    mapping = {
        'Safe':     'success',
        'Moderate': 'warning',
        'High':     'danger',
    }
    return mapping.get(risk_str, 'secondary')


def paginate_query(query, page, per_page=20):
    """Return a Flask-SQLAlchemy pagination object."""
    return query.paginate(page=page, per_page=per_page, error_out=False)
