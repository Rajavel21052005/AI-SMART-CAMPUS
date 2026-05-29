# ============================================================
# app/routes/face.py — Face Recognition & Camera Blueprint
# Handles MJPEG streaming, photo registration, model training
# ============================================================
import os
import io
import tempfile
import uuid
from flask import (Blueprint, Response, render_template, request,
                   jsonify, redirect, url_for, flash, current_app,
                   stream_with_context)
from flask_login import login_required, current_user
from utils.decorators import faculty_required, admin_required
from app.models.student import Student
from app import db

face_bp = Blueprint('face', __name__)


# ── Live camera stream (MJPEG) ────────────────────────────────

@face_bp.route('/stream/<int:subject_id>')
@login_required
@faculty_required
def video_stream(subject_id):
    """MJPEG stream for live face-recognition attendance."""
    from app.services.camera_service import generate_frames
    mode = request.args.get('mode', 'attendance')
    return Response(
        stream_with_context(generate_frames(subject_id, mode=mode)),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@face_bp.route('/live/<int:subject_id>')
@login_required
@faculty_required
def live_view(subject_id):
    """Page that embeds the MJPEG stream for a subject."""
    from app.models.subject import Subject
    subject = Subject.query.get_or_404(subject_id)
    return render_template('face/live_feed.html', subject=subject)


# ── Security-only stream (admin) ──────────────────────────────

@face_bp.route('/security-stream')
@login_required
@admin_required
def security_stream():
    """MJPEG stream for campus security monitoring (unknown faces only)."""
    from app.services.camera_service import generate_frames
    return Response(
        stream_with_context(generate_frames(subject_id=0, mode='security')),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@face_bp.route('/security-monitor')
@login_required
@admin_required
def security_monitor():
    return render_template('face/security_monitor.html')


# ── Photo registration (single student) ──────────────────────

@face_bp.route('/register/<int:student_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def register_face(student_id):
    """Upload / capture a photo and generate face encoding for a student."""
    student = Student.query.get_or_404(student_id)

    if request.method == 'POST':
        # ── Option A: file upload ──────────────────────────────
        photo = request.files.get('photo')
        if photo and photo.filename:
            from utils.helpers import save_uploaded_photo
            path = save_uploaded_photo(photo, subfolder=f'students/{student.reg_number}')
            if path:
                student.photo_path = path
                db.session.commit()

                # Generate and store encoding immediately
                from app.services.face_service import FaceService
                encoding = FaceService.generate_encoding(path)
                if encoding is not None:
                    import pickle
                    from app.models.face_encoding import FaceEncoding
                    FaceEncoding.query.filter_by(student_id=student.student_id).delete()
                    fe = FaceEncoding(
                        user_type='student',
                        user_id=student.student_id,
                        student_id=student.student_id,
                        encoding_data=pickle.dumps(encoding),
                        model_used='Facenet512',
                        image_path=path,
                    )
                    db.session.add(fe)
                    db.session.commit()
                    flash(f'Face registered successfully for {student.name}.', 'success')
                else:
                    flash('No face detected in the uploaded photo. Please use a clear front-facing photo.', 'danger')
            else:
                flash('Invalid file type. Use JPG or PNG.', 'danger')

        # ── Option B: base64 snapshot from webcam ─────────────
        elif request.form.get('snapshot_data'):
            import base64
            import uuid
            data_url = request.form['snapshot_data']
            header, encoded = data_url.split(',', 1)
            img_bytes = base64.b64decode(encoded)

            upload_dir = os.path.join(
                current_app.config['UPLOAD_FOLDER'],
                f'students/{student.reg_number}'
            )
            os.makedirs(upload_dir, exist_ok=True)
            fname = f'{uuid.uuid4().hex}.jpg'
            path  = os.path.join(upload_dir, fname)

            with open(path, 'wb') as f:
                f.write(img_bytes)

            student.photo_path = path
            db.session.commit()

            from app.services.face_service import FaceService
            import pickle
            from app.models.face_encoding import FaceEncoding
            encoding = FaceService.generate_encoding(path)
            if encoding is not None:
                FaceEncoding.query.filter_by(student_id=student.student_id).delete()
                fe = FaceEncoding(
                    user_type='student',
                    user_id=student.student_id,
                    student_id=student.student_id,
                    encoding_data=pickle.dumps(encoding),
                    model_used='Facenet512',
                    image_path=path,
                )
                db.session.add(fe)
                db.session.commit()
                flash(f'Webcam snapshot registered for {student.name}.', 'success')
            else:
                flash('No face detected in snapshot. Try again with better lighting.', 'danger')

        return redirect(url_for('admin.students'))

    return render_template('face/register_face.html', student=student)


# ── Bulk model training API ───────────────────────────────────

@face_bp.route('/train', methods=['POST'])
@login_required
@admin_required
def train_model():
    """Re-train all face encodings. Returns JSON progress summary."""
    from app.services.face_service import FaceService
    try:
        result = FaceService.train_encodings()
        return jsonify({'status': 'success', **result})
    except Exception as e:
        current_app.logger.error(f'Training error: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ── Identity check API (single image) ────────────────────────

@face_bp.route('/identify', methods=['POST'])
@login_required
def identify():
    """
    POST a base64 image or file upload → returns identity + confidence.
    Used by the JS frontend for async identification checks.
    """
    from app.services.face_service import FaceService
    import base64

    # Accept either file upload or base64 data URL
    photo = request.files.get('photo')
    tmp = os.path.join(tempfile.gettempdir(), f'_sc_identify_{uuid.uuid4().hex}.jpg')
    if photo:
        photo.save(tmp)
    elif request.json and request.json.get('image'):
        data  = request.json['image'].split(',', 1)[-1]
        with open(tmp, 'wb') as f:
            f.write(base64.b64decode(data))
    else:
        return jsonify({'error': 'No image provided'}), 400

    try:
        result = FaceService.identify_face(tmp)
        return jsonify(result)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
