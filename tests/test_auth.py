"""
Tests for authentication routes: login, logout, registration.
"""

from models import User


class TestLogin:

    def test_login_page_loads(self, client):
        response = client.get('/auth/login')
        assert response.status_code == 200

    def test_login_success_redirects_to_dashboard(self, client, admin_user):
        response = client.post('/auth/login', data={
            'email': admin_user.email,
            'password': 'Password123!',
        }, follow_redirects=True)

        assert response.status_code == 200
        assert response.request.path == '/dashboard/'

    def test_login_wrong_password_shows_error(self, client, admin_user):
        response = client.post('/auth/login', data={
            'email': admin_user.email,
            'password': 'totally-wrong',
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Invalid email or password' in response.data

    def test_login_unknown_email_shows_error(self, client):
        response = client.post('/auth/login', data={
            'email': 'nobody@nowhere.com',
            'password': 'whatever123',
        }, follow_redirects=True)

        assert b'Invalid email or password' in response.data

    def test_login_inactive_account_is_blocked(self, client, db, admin_user):
        admin_user.is_active = False
        db.session.commit()

        response = client.post('/auth/login', data={
            'email': admin_user.email,
            'password': 'Password123!',
        }, follow_redirects=True)

        assert b'deactivated' in response.data

    def test_authenticated_user_redirected_away_from_login(self, client, login_as, admin_user):
        login_as(client, admin_user)
        response = client.get('/auth/login', follow_redirects=True)
        assert response.request.path == '/dashboard/'


class TestLogout:

    def test_logout_requires_login(self, client):
        response = client.get('/auth/logout', follow_redirects=True)
        # Redirected to login page since not authenticated
        assert response.request.path == '/auth/login'

    def test_logout_clears_session(self, client, login_as, admin_user):
        login_as(client, admin_user)
        client.get('/auth/logout')

        # Any protected page should now redirect to login
        response = client.get('/dashboard/', follow_redirects=True)
        assert response.request.path == '/auth/login'


class TestRegister:

    def test_register_page_loads(self, client):
        response = client.get('/auth/register')
        assert response.status_code == 200

    def test_register_creates_new_user(self, client, db):
        response = client.post('/auth/register', data={
            'email': 'newdoc@test.com',
            'first_name': 'New',
            'last_name': 'Doctor',
            'phone': '555-1234',
            'role': 'doctor',
            'specialization': 'Cardiology',
            'license_number': 'MD5000',
            'password': 'StrongPass123',
            'password2': 'StrongPass123',
        }, follow_redirects=True)

        assert response.status_code == 200
        user = User.query.filter_by(email='newdoc@test.com').first()
        assert user is not None
        assert user.role == 'doctor'
        assert user.check_password('StrongPass123')

    def test_register_duplicate_email_rejected(self, client, admin_user):
        response = client.post('/auth/register', data={
            'email': admin_user.email,
            'first_name': 'Dup',
            'last_name': 'User',
            'phone': '555-0000',
            'role': 'receptionist',
            'password': 'StrongPass123',
            'password2': 'StrongPass123',
        }, follow_redirects=True)

        assert b'already registered' in response.data

    def test_register_accountant_role_supported(self, client, db):
        client.post('/auth/register', data={
            'email': 'acct@test.com',
            'first_name': 'Money',
            'last_name': 'Person',
            'phone': '555-4321',
            'role': 'accountant',
            'password': 'StrongPass123',
            'password2': 'StrongPass123',
        }, follow_redirects=True)

        user = User.query.filter_by(email='acct@test.com').first()
        assert user is not None
        assert user.is_accountant() is True
