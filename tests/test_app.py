"""Integration tests for CampusConnect. Run: python -m unittest discover -s tests -v"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from app import app, db, init_db


class CampusConnectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        app.config.update(TESTING=True, DATABASE=str(Path(self.tmp.name) / "test.sqlite3"),
                          SECRET_KEY="test-only-secret")
        with app.app_context():
            init_db(seed=True)
        self.client = app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def token(self):
        self.client.get("/")
        with self.client.session_transaction() as sess:
            return sess["csrf_token"]

    def post(self, url, data=None, follow_redirects=True):
        return self.client.post(url, data={"csrf_token": self.token(), **(data or {})},
                                follow_redirects=follow_redirects)

    def login(self, leader=False):
        return self.post("/login", {
            "email": "leader@campusconnect.test" if leader else "student@campusconnect.test",
            "password": "Demo1234!"
        })

    def test_public_pages_and_seed(self):
        self.assertIn(b"Find your people", self.client.get("/").data)
        self.assertIn(b"Business Club", self.client.get("/clubs").data)
        self.assertIn(b"Business &amp; AI Networking Mixer", self.client.get("/events").data)
        with app.app_context():
            self.assertEqual(db().execute("SELECT COUNT(*) FROM clubs").fetchone()[0], 4)

    def test_registration_login_logout(self):
        response = self.post("/register", {
            "full_name": "New Student", "email": "new@university.edu", "password": "Test12345!"
        })
        self.assertIn(b"Hello, New", response.data)
        self.assertIn(b"Log in", self.post("/logout").data)
        self.assertIn(b"My dashboard", self.login().data)

    def test_membership_join_and_leave(self):
        self.login()
        response = self.post("/clubs/2/membership")
        self.assertIn(b"You&#39;ve joined this club", response.data)
        with app.app_context():
            self.assertEqual(db().execute("SELECT COUNT(*) FROM club_memberships WHERE club_id=2 AND user_id=1").fetchone()[0], 1)
        response = self.post("/clubs/2/membership")
        self.assertIn(b"You left this club", response.data)

    def test_registration_and_cancellation(self):
        self.login()
        response = self.post("/events/2/registration")
        self.assertIn(b"You are registered", response.data)
        with app.app_context():
            self.assertEqual(db().execute("SELECT COUNT(*) FROM registrations WHERE user_id=1 AND event_id=2").fetchone()[0], 1)
        self.assertIn(b"Campus Leadership Forum", self.client.get("/dashboard").data)
        response = self.post("/events/2/registration")
        self.assertIn(b"registration was cancelled", response.data)

    def test_leader_only_controls_and_attendance(self):
        self.login()
        event_at = (datetime.now() + timedelta(days=14)).isoformat(timespec="minutes")
        values = {"title": "Leadership Workshop", "description": "Practical leadership training",
                  "location": "Room 12", "start_at": event_at, "capacity": "25"}
        self.assertEqual(self.post("/clubs/1/events/new", values).status_code, 403)
        self.assertEqual(self.client.get("/events/1/attendance").status_code, 403)
        self.post("/logout")
        self.login(leader=True)
        created = self.post("/clubs/1/events/new", values)
        self.assertIn(b"Leadership Workshop", created.data)
        with app.app_context():
            event_id = db().execute("SELECT id FROM events WHERE title='Leadership Workshop'").fetchone()[0]
        self.assertEqual(self.client.get(f"/events/{event_id}/edit").status_code, 200)
        attendance_page = self.client.get("/events/1/attendance")
        self.assertIn(b"Alex Rivera", attendance_page.data)
        with app.app_context():
            reg_id = db().execute("SELECT id FROM registrations WHERE event_id=1 AND user_id=1").fetchone()[0]
        self.post("/events/1/attendance", {"registration_id": str(reg_id)})
        with app.app_context():
            self.assertIsNotNone(db().execute("SELECT attended_at FROM registrations WHERE id=?", (reg_id,)).fetchone()[0])
        self.post(f"/events/{event_id}/cancel")
        with app.app_context():
            self.assertEqual(db().execute("SELECT is_cancelled FROM events WHERE id=?", (event_id,)).fetchone()[0], 1)

    def test_csrf_mandatory(self):
        self.assertEqual(self.client.post("/login", data={"email": "fake@campus.test"}).status_code, 400)

    def test_capacity_not_exceeded(self):
        self.login(leader=True)
        date = (datetime.now() + timedelta(days=10)).isoformat(timespec="minutes")
        self.post("/clubs/1/events/new", {"title": "Tiny Meetup", "description": "A very small group",
                      "location": "Room B", "start_at": date, "capacity": "1"})
        with app.app_context():
            event_id = db().execute("SELECT id FROM events WHERE title='Tiny Meetup'").fetchone()[0]
        self.post("/logout")
        self.login()
        self.post(f"/events/{event_id}/registration")
        self.post("/logout")
        self.login(leader=True)
        self.assertIn(b"This event is full", self.post(f"/events/{event_id}/registration").data)
        with app.app_context():
            self.assertEqual(db().execute("SELECT COUNT(*) FROM registrations WHERE event_id=?", (event_id,)).fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
