"""
Tests that error pages render without raising TemplateNotFound.
"""


class TestErrorPages:

    def test_404_page_renders(self, client):
        response = client.get('/this-route-does-not-exist')
        assert response.status_code == 404
        assert b'404' in response.data

    def test_403_page_renders_on_forbidden_action(self, client, login_as, doctor_user):
        """A doctor hitting an admin/receptionist-only route triggers the
        role_required redirect+flash, not a raw 403 page - but we can hit
        the 403 template directly to make sure it at least renders."""
        login_as(client, doctor_user)
        with client.application.test_request_context():
            from flask import render_template
            html = render_template('errors/403.html')
            assert '403' in html

    def test_400_template_renders(self, app):
        with app.test_request_context():
            from flask import render_template
            html = render_template('errors/400.html')
            assert '400' in html

    def test_500_template_renders(self, app):
        with app.test_request_context():
            from flask import render_template
            html = render_template('errors/500.html')
            assert '500' in html
