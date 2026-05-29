# ============================================================
# run.py — Application Entry Point
# Usage:
#   python run.py               (start dev server)
#   flask init-db               (create tables)
#   flask seed-db               (insert demo data)
#   flask train-risk            (train ML model with synthetic data)
# ============================================================
import os

os.environ.setdefault('TF_USE_LEGACY_KERAS', '1')
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
os.environ.setdefault('TF_ENABLE_ONEDNN_OPTS', '0')
os.environ.setdefault('GLOG_minloglevel', '2')

import warnings

warnings.filterwarnings('ignore', message='.*urllib3.*doesn.*match a supported version.*')
warnings.filterwarnings('ignore', message='.*SymbolDatabase.GetPrototype\\(\\) is deprecated.*')

import click
from app import create_app, db
from app.models import *   # noqa — registers all models with SQLAlchemy

app = create_app()


@app.cli.command('init-db')
def init_db():
    """Create all database tables."""
    with app.app_context():
        db.create_all()
        click.echo('✅  Database initialised.')


@app.cli.command('seed-db')
def seed_db():
    """Insert realistic demo data (departments, students, attendance, marks)."""
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, 'database/seed_data.py'],
        capture_output=False
    )
    if result.returncode == 0:
        click.echo('✅  Demo data seeded.')
    else:
        click.echo('❌  Seed failed — check output above.')


@app.cli.command('train-risk')
@click.option('--synthetic', is_flag=True, default=True, help='Use synthetic data')
@click.option('--n', default=600, help='Number of synthetic samples')
def train_risk(synthetic, n):
    """Train the academic risk prediction ML model."""
    import subprocess, sys
    args = [sys.executable, 'training/train_risk_model.py']
    if synthetic:
        args += ['--synthetic', '--n', str(n)]
    subprocess.run(args)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        use_reloader=False
    )
