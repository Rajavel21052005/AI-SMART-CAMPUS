# ============================================================
# app/__init__.py — Flask Application Factory
# ============================================================
import os
import logging
import warnings
from logging.handlers import RotatingFileHandler

os.environ.setdefault('TF_USE_LEGACY_KERAS', '1')
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
os.environ.setdefault('TF_ENABLE_ONEDNN_OPTS', '0')
os.environ.setdefault('GLOG_minloglevel', '2')

warnings.filterwarnings('ignore', message='.*urllib3.*doesn.*match a supported version.*')
warnings.filterwarnings('ignore', message='.*SymbolDatabase.GetPrototype\\(\\) is deprecated.*')

from flask import Flask
from flask.logging import default_handler
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

from config.config import ActiveConfig

db            = SQLAlchemy()
login_manager = LoginManager()
mail          = Mail()
migrate       = Migrate()
csrf          = CSRFProtect()


def create_app(config_class=ActiveConfig):
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config_class)
    os.environ.setdefault('DEEPFACE_HOME', app.config['DEEPFACE_HOME'])

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    login_manager.login_view            = 'auth.login'
    login_manager.login_message         = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    for folder in [
        app.config['UPLOAD_FOLDER'],
        app.config['SECURITY_FOLDER'],
        app.config['LOG_FOLDER'],
        app.config['DEEPFACE_HOME'],
        'ai_models',
    ]:
        os.makedirs(folder, exist_ok=True)

    _configure_logging(app)

    # ── Register all Blueprints ──────────────────────────────
    from app.routes.auth      import auth_bp
    from app.routes.student   import student_bp
    from app.routes.faculty   import faculty_bp
    from app.routes.admin     import admin_bp
    from app.routes.api       import api_bp
    from app.routes.face      import face_bp
    from app.routes.analytics import analytics_bp

    app.register_blueprint(auth_bp,      url_prefix='/auth')
    app.register_blueprint(student_bp,   url_prefix='/student')
    app.register_blueprint(faculty_bp,   url_prefix='/faculty')
    app.register_blueprint(admin_bp,     url_prefix='/admin')
    app.register_blueprint(api_bp,       url_prefix='/api/v1')
    app.register_blueprint(face_bp,      url_prefix='/face')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')

    from flask import redirect, url_for

    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    # ── Error handlers ───────────────────────────────────────
    @app.errorhandler(403)
    def forbidden(e):
        from flask import render_template
        return render_template('shared/error.html', code=403,
                               msg='You do not have permission to view this page.'), 403

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('shared/error.html', code=404,
                               msg='The page you requested was not found.'), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import render_template
        return render_template('shared/error.html', code=500,
                               msg='An internal server error occurred.'), 500

    from app.models.student import Student
    from app.models.faculty import Faculty, Admin

    @login_manager.user_loader
    def load_user(user_id):
        if not user_id or '_' not in user_id:
            return None
        role, uid = user_id.split('_', 1)
        try:
            uid = int(uid)
        except ValueError:
            return None
        if role == 'student':
            return Student.query.get(uid)
        elif role == 'faculty':
            return Faculty.query.get(uid)
        elif role == 'admin':
            return Admin.query.get(uid)
        return None

    @app.shell_context_processor
    def make_shell_context():
        return {'db': db, 'Student': Student, 'Faculty': Faculty, 'Admin': Admin}

    app.logger.info('Smart Campus application started.')
    return app


def _configure_logging(app):
    log_folder = app.config.get('LOG_FOLDER', 'logs')
    os.makedirs(log_folder, exist_ok=True)
    log_level  = getattr(logging, app.config.get('LOG_LEVEL', 'DEBUG').upper(), logging.DEBUG)

    if default_handler in app.logger.handlers:
        app.logger.removeHandler(default_handler)

    for handler in list(app.logger.handlers):
        app.logger.removeHandler(handler)
        handler.close()

    file_handler = RotatingFileHandler(
        os.path.join(log_folder, 'app.log'),
        maxBytes=5 * 1024 * 1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    ))
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))

    app.logger.setLevel(log_level)
    app.logger.propagate = False
    app.logger.addHandler(file_handler)
    app.logger.addHandler(stream_handler)

    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('tensorflow').setLevel(logging.ERROR)
    logging.getLogger('absl').setLevel(logging.ERROR)
