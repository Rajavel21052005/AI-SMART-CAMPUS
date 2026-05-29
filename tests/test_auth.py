# ============================================================
# tests/test_auth.py — Authentication Unit Tests
# ============================================================
import pytest
from app import create_app, db
from app.models.faculty import Admin
from config.config import TestingConfig


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        # Seed a test admin
        admin = Admin(username='testadmin', name='Test Admin', email='test@campus.edu')
        admin.set_password('Test@1234')
        db.session.add(admin)
        db.session.commit()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_login_page_loads(client):
    """GET /auth/login should return 200."""
    resp = client.get('/auth/login')
    assert resp.status_code == 200
    assert b'SmartCampus' in resp.data or b'Sign In' in resp.data


def test_login_wrong_password(client):
    """Login with wrong password should fail and stay on login page."""
    resp = client.post('/auth/login', data={
        'role': 'admin', 'username': 'testadmin', 'password': 'wrong'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Invalid credentials' in resp.data


def test_login_success_admin(client):
    """Correct admin credentials should redirect to admin dashboard."""
    resp = client.post('/auth/login', data={
        'role': 'admin', 'username': 'testadmin', 'password': 'Test@1234'
    }, follow_redirects=True)
    assert resp.status_code == 200
    # Should land on admin dashboard
    assert b'Admin' in resp.data or b'dashboard' in resp.data.lower()


def test_logout(client):
    """Logout should redirect to login."""
    # Log in first
    client.post('/auth/login', data={
        'role': 'admin', 'username': 'testadmin', 'password': 'Test@1234'
    })
    resp = client.get('/auth/logout', follow_redirects=True)
    assert resp.status_code == 200


def test_protected_route_redirects_unauthenticated(client):
    """Unauthenticated access to dashboard should redirect to login."""
    resp = client.get('/admin/dashboard', follow_redirects=False)
    assert resp.status_code in (302, 308)
