import os
import unittest
from datetime import date, timedelta
from app import create_app, db
from app.models import User, Workout
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-key-for-pulse-track"
    SERVER_NAME = "localhost"

class BaseTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def get_csrf_token(self, path="/login"):
        """Performs a GET to ensure session csrf_token exists, then extracts it from session."""
        self.client.get(path)
        with self.client.session_transaction() as sess:
            return sess.get("csrf_token", "")

    def register_user(self, name="Test Runner", email="runner@example.com", password="password123"):
        csrf = self.get_csrf_token("/register")
        return self.client.post(
            "/register",
            data={"name": name, "email": email, "password": password, "csrf_token": csrf},
            follow_redirects=True,
        )

    def login_user(self, email="runner@example.com", password="password123"):
        csrf = self.get_csrf_token("/login")
        return self.client.post(
            "/login",
            data={"email": email, "password": password, "csrf_token": csrf},
            follow_redirects=True,
        )

    def logout_user(self):
        with self.client.session_transaction() as sess:
            csrf = sess.get("csrf_token", "")
        return self.client.post("/logout", data={"csrf_token": csrf}, follow_redirects=True)


class Test1_RouteProtectionAndUnauthenticated(BaseTestCase):
    """Verifies that unauthenticated visitors are properly redirected or blocked."""

    def test_possibility_01_index_redirects_unauthenticated_to_login(self):
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/login"))

    def test_possibility_02_dashboard_redirects_unauthenticated_to_login(self):
        response = self.client.get("/dashboard", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/login"))

    def test_possibility_03_dashboard_post_redirects_unauthenticated_to_login(self):
        response = self.client.post("/dashboard", data={"title": "Hack", "workout_type": "Cardio", "duration": 30, "calories": 200, "completed_on": "2026-09-08"}, follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/login"))

    def test_possibility_04_delete_workout_post_redirects_unauthenticated_to_login(self):
        response = self.client.post("/workouts/1/delete", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/login"))

    def test_possibility_05_api_workouts_get_unauthenticated_returns_401(self):
        response = self.client.get("/api/workouts")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {"error": "Authentication required"})

    def test_possibility_06_api_workouts_post_unauthenticated_returns_401(self):
        response = self.client.post("/api/workouts", json={"title": "Run", "workout_type": "Cardio", "duration": 30, "calories": 200, "completed_on": "2026-09-08"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {"error": "Authentication required"})

    def test_possibility_07_api_health_is_public_and_returns_ok(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})


class Test2_RegistrationPossibilities(BaseTestCase):
    """Tests all registration inputs, boundary conditions, validations, and successes."""

    def test_possibility_08_get_register_page_loads_with_csrf(self):
        response = self.client.get("/register")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Create your account", response.data)
        with self.client.session_transaction() as sess:
            self.assertIn("csrf_token", sess)

    def test_possibility_09_registration_missing_or_invalid_csrf_fails(self):
        response = self.client.post(
            "/register",
            data={"name": "Alice Valid", "email": "alice@example.com", "password": "password123", "csrf_token": "fake_token"},
            follow_redirects=True,
        )
        self.assertIn(b"Your form expired. Please try again.", response.data)
        self.assertIsNone(User.query.filter_by(email="alice@example.com").first())

    def test_possibility_10a_registration_name_too_short(self):
        csrf = self.get_csrf_token("/register")
        response = self.client.post(
            "/register",
            data={"name": "A", "email": "shortname@example.com", "password": "password123", "csrf_token": csrf},
            follow_redirects=True,
        )
        self.assertIn(b"Please enter a name between 2 and 80 characters.", response.data)
        self.assertIsNone(User.query.filter_by(email="shortname@example.com").first())

    def test_possibility_10b_registration_name_too_long(self):
        csrf = self.get_csrf_token("/register")
        long_name = "X" * 81
        response = self.client.post(
            "/register",
            data={"name": long_name, "email": "longname@example.com", "password": "password123", "csrf_token": csrf},
            follow_redirects=True,
        )
        self.assertIn(b"Please enter a name between 2 and 80 characters.", response.data)
        self.assertIsNone(User.query.filter_by(email="longname@example.com").first())

    def test_possibility_11_registration_invalid_email_formats(self):
        csrf = self.get_csrf_token("/register")
        invalid_emails = ["notanemail", "user@", "@domain.com", "user@domain", "user space@domain.com"]
        for bad_email in invalid_emails:
            response = self.client.post(
                "/register",
                data={"name": "Alice Test", "email": bad_email, "password": "password123", "csrf_token": csrf},
                follow_redirects=True,
            )
            self.assertIn(b"Please enter a valid email address.", response.data, f"Failed to reject invalid email: {bad_email}")

    def test_possibility_12_registration_password_too_short(self):
        csrf = self.get_csrf_token("/register")
        response = self.client.post(
            "/register",
            data={"name": "Alice Short", "email": "aliceshort@example.com", "password": "short", "csrf_token": csrf},
            follow_redirects=True,
        )
        self.assertIn(b"Password must be at least 8 characters.", response.data)

    def test_possibility_13_registration_duplicate_email_case_insensitive(self):
        self.register_user(name="First User", email="unique@example.com", password="password123")
        # Log out so the second registration attempt is made by an unauthenticated visitor
        self.logout_user()
        csrf = self.get_csrf_token("/register")
        response = self.client.post(
            "/register",
            data={"name": "Duplicate User", "email": "UNIQUE@EXAMPLE.COM", "password": "password456", "csrf_token": csrf},
            follow_redirects=True,
        )
        self.assertIn(b"An account with that email already exists.", response.data)

    def test_possibility_14_registration_successful(self):
        response = self.register_user(name="Bob Athlete", email="bob@example.com", password="securepassword123")
        self.assertIn(b"Welcome to PulseTrack.", response.data)
        self.assertIn(b"Good morning, Bob.", response.data)
        user = User.query.filter_by(email="bob@example.com").first()
        self.assertIsNotNone(user)
        self.assertTrue(user.check_password("securepassword123"))
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("user_id"), user.id)

    def test_possibility_15_authenticated_user_accessing_register_redirects_to_dashboard(self):
        self.register_user()
        response = self.client.get("/register", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/dashboard"))


class Test3_LoginPossibilities(BaseTestCase):
    """Tests all login scenarios, credential checks, and session behaviors."""

    def setUp(self):
        super().setUp()
        user = User(name="Test LoginUser", email="loginuser@example.com")
        user.set_password("correctpassword")
        db.session.add(user)
        db.session.commit()
        self.user_id = user.id

    def test_possibility_16_get_login_page_renders_form(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Welcome back", response.data)
        self.assertIn(b"Sign in", response.data)

    def test_possibility_17_login_invalid_csrf_token_fails(self):
        self.client.get("/login")
        response = self.client.post(
            "/login",
            data={"email": "loginuser@example.com", "password": "correctpassword", "csrf_token": "wrong_csrf"},
            follow_redirects=True,
        )
        self.assertIn(b"Your form expired. Please try again.", response.data)
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

    def test_possibility_18_login_nonexistent_email_fails(self):
        csrf = self.get_csrf_token("/login")
        response = self.client.post(
            "/login",
            data={"email": "nonexistent@example.com", "password": "correctpassword", "csrf_token": csrf},
            follow_redirects=True,
        )
        self.assertIn(b"Email or password is incorrect.", response.data)
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

    def test_possibility_19_login_wrong_password_fails(self):
        csrf = self.get_csrf_token("/login")
        response = self.client.post(
            "/login",
            data={"email": "loginuser@example.com", "password": "wrongpassword", "csrf_token": csrf},
            follow_redirects=True,
        )
        self.assertIn(b"Email or password is incorrect.", response.data)
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

    def test_possibility_20_login_case_insensitive_email_succeeds(self):
        csrf = self.get_csrf_token("/login")
        response = self.client.post(
            "/login",
            data={"email": "LOGINUSER@EXAMPLE.COM", "password": "correctpassword", "csrf_token": csrf},
            follow_redirects=True,
        )
        self.assertIn(b"Good morning, Test.", response.data)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("user_id"), self.user_id)

    def test_possibility_21_login_successful(self):
        response = self.login_user(email="loginuser@example.com", password="correctpassword")
        self.assertIn(b"Good morning, Test.", response.data)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("user_id"), self.user_id)

    def test_possibility_22_authenticated_user_accessing_login_redirects_to_dashboard(self):
        self.login_user(email="loginuser@example.com", password="correctpassword")
        response = self.client.get("/login", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/dashboard"))


class Test4_DashboardAndMetrics(BaseTestCase):
    """Tests dashboard views and weekly aggregation calculations."""

    def setUp(self):
        super().setUp()
        self.register_user(name="Metric User", email="metrics@example.com", password="password123")
        self.user = User.query.filter_by(email="metrics@example.com").first()

    def test_possibility_23_empty_dashboard_renders_zeros_and_empty_state(self):
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your log is ready", response.data)
        self.assertIn(b"ALL-TIME SESSIONS", response.data)
        self.assertIn(b"<strong>0</strong>", response.data)  # 0 sessions
        self.assertIn(b"<strong>0 <b>min</b></strong>", response.data)
        self.assertIn(b"<strong>0 <b>kcal</b></strong>", response.data)

    def test_possibility_24_metrics_calculation_weekly_and_older(self):
        today = date.today()
        # Workout 1: Today (Cardio, 45 min, 400 kcal)
        w1 = Workout(user_id=self.user.id, title="Morning Run", workout_type="Cardio", duration=45, calories=400, completed_on=today)
        # Workout 2: 3 days ago (Strength, 60 min, 350 kcal)
        w2 = Workout(user_id=self.user.id, title="Upper Body", workout_type="Strength", duration=60, calories=350, completed_on=today - timedelta(days=3))
        # Workout 3: 15 days ago (older than 7-day window, 50 min, 300 kcal)
        w3 = Workout(user_id=self.user.id, title="Old Run", workout_type="Cardio", duration=50, calories=300, completed_on=today - timedelta(days=15))
        db.session.add_all([w1, w2, w3])
        db.session.commit()

        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        # Total sessions = 3
        self.assertIn(b"<strong>3</strong>", response.data)
        # Week minutes = 45 + 60 = 105 min (w3 excluded)
        self.assertIn(b"<strong>105 <b>min</b></strong>", response.data)
        # Week calories = 400 + 350 = 750 kcal (w3 excluded)
        self.assertIn(b"<strong>750 <b>kcal</b></strong>", response.data)


class Test5_WorkoutCreationAndValidation(BaseTestCase):
    """Tests web form workout creation validations and REST API endpoints."""

    def setUp(self):
        super().setUp()
        self.register_user(name="Worker User", email="worker@example.com", password="password123")
        self.user = User.query.filter_by(email="worker@example.com").first()

    def test_possibility_25_workout_creation_missing_invalid_csrf_fails(self):
        response = self.client.post(
            "/dashboard",
            data={"title": "Leg Day", "workout_type": "Strength", "duration": 45, "calories": 300, "completed_on": date.today().isoformat(), "csrf_token": "invalid_csrf"},
            follow_redirects=True,
        )
        self.assertIn(b"Your form expired. Please try again.", response.data)
        self.assertEqual(Workout.query.count(), 0)

    def test_possibility_26a_workout_creation_empty_title(self):
        csrf = self.get_csrf_token("/dashboard")
        response = self.client.post(
            "/dashboard",
            data={"title": "   ", "workout_type": "Strength", "duration": 45, "calories": 300, "completed_on": date.today().isoformat(), "csrf_token": csrf},
            follow_redirects=True,
        )
        self.assertIn(b"Add a title and choose a valid workout type.", response.data)
        self.assertEqual(Workout.query.count(), 0)

    def test_possibility_26b_workout_creation_invalid_type(self):
        csrf = self.get_csrf_token("/dashboard")
        response = self.client.post(
            "/dashboard",
            data={"title": "Gaming", "workout_type": "InvalidType", "duration": 45, "calories": 300, "completed_on": date.today().isoformat(), "csrf_token": csrf},
            follow_redirects=True,
        )
        self.assertIn(b"Add a title and choose a valid workout type.", response.data)
        self.assertEqual(Workout.query.count(), 0)

    def test_possibility_26c_workout_creation_invalid_duration_and_calories(self):
        csrf = self.get_csrf_token("/dashboard")
        # Duration 0 (out of bounds 1-1440)
        res1 = self.client.post(
            "/dashboard",
            data={"title": "Zero duration", "workout_type": "Cardio", "duration": 0, "calories": 100, "completed_on": date.today().isoformat(), "csrf_token": csrf},
            follow_redirects=True,
        )
        self.assertIn(b"Check the duration, calories, and date values.", res1.data)

        # Calories negative
        res2 = self.client.post(
            "/dashboard",
            data={"title": "Neg calories", "workout_type": "Cardio", "duration": 30, "calories": -5, "completed_on": date.today().isoformat(), "csrf_token": csrf},
            follow_redirects=True,
        )
        self.assertIn(b"Check the duration, calories, and date values.", res2.data)

    def test_possibility_27_workout_creation_success(self):
        csrf = self.get_csrf_token("/dashboard")
        response = self.client.post(
            "/dashboard",
            data={"title": "Morning HIIT", "workout_type": "Cardio", "duration": 40, "calories": 380, "completed_on": date.today().isoformat(), "csrf_token": csrf},
            follow_redirects=True,
        )
        self.assertIn(b"Workout added to your history.", response.data)
        self.assertIn(b"Morning HIIT", response.data)
        self.assertIn(b"40 min", response.data)
        self.assertIn(b"380 kcal", response.data)
        self.assertEqual(Workout.query.count(), 1)
        w = Workout.query.first()
        self.assertEqual(w.user_id, self.user.id)
        self.assertEqual(w.title, "Morning HIIT")

    def test_possibility_28_api_workout_creation_validation_and_success(self):
        # Missing fields
        res_missing = self.client.post("/api/workouts", json={"title": "Yoga"})
        self.assertEqual(res_missing.status_code, 400)
        self.assertEqual(res_missing.get_json(), {"error": "Missing workout fields"})

        # Invalid values (duration = 0)
        res_invalid = self.client.post("/api/workouts", json={"title": "Yoga", "workout_type": "Mobility", "duration": 0, "calories": 50, "completed_on": "2026-09-08"})
        self.assertEqual(res_invalid.status_code, 400)

        # Valid creation
        res_valid = self.client.post("/api/workouts", json={"title": "Yoga Flow", "workout_type": "Mobility", "duration": 45, "calories": 150, "completed_on": "2026-09-08"})
        self.assertEqual(res_valid.status_code, 201)
        data = res_valid.get_json()
        self.assertEqual(data["title"], "Yoga Flow")
        self.assertEqual(data["workout_type"], "Mobility")
        self.assertEqual(data["duration"], 45)

    def test_possibility_29_api_workout_list_returns_user_workouts(self):
        w = Workout(user_id=self.user.id, title="Cycling", workout_type="Sport", duration=60, calories=500, completed_on=date.today())
        db.session.add(w)
        db.session.commit()

        response = self.client.get("/api/workouts")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("data", payload)
        self.assertEqual(len(payload["data"]), 1)
        self.assertEqual(payload["data"][0]["title"], "Cycling")


class Test6_SearchAndFiltering(BaseTestCase):
    """Tests workout search by title, type, no matches, and query clearing."""

    def setUp(self):
        super().setUp()
        self.register_user(name="Searcher", email="searcher@example.com", password="password123")
        self.user = User.query.filter_by(email="searcher@example.com").first()
        today = date.today()
        w1 = Workout(user_id=self.user.id, title="Heavy Bench Press", workout_type="Strength", duration=50, calories=320, completed_on=today)
        w2 = Workout(user_id=self.user.id, title="Treadmill Sprint", workout_type="Cardio", duration=30, calories=350, completed_on=today)
        w3 = Workout(user_id=self.user.id, title="Evening Stretch", workout_type="Mobility", duration=20, calories=80, completed_on=today)
        db.session.add_all([w1, w2, w3])
        db.session.commit()

    def test_possibility_30_search_by_title_substring(self):
        response = self.client.get("/dashboard?q=bench")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Heavy Bench Press", response.data)
        self.assertNotIn(b"Treadmill Sprint", response.data)
        self.assertNotIn(b"Evening Stretch", response.data)

    def test_possibility_31_search_by_workout_type(self):
        response = self.client.get("/dashboard?q=cardio")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Treadmill Sprint", response.data)
        self.assertNotIn(b"Heavy Bench Press", response.data)

    def test_possibility_32_search_no_matches_displays_empty_message(self):
        response = self.client.get("/dashboard?q=nonexistentquery")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No workouts found", response.data)
        self.assertIn(b"Try a different search term.", response.data)

    def test_possibility_33_search_empty_query_shows_all_workouts(self):
        response = self.client.get("/dashboard?q=")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Heavy Bench Press", response.data)
        self.assertIn(b"Treadmill Sprint", response.data)
        self.assertIn(b"Evening Stretch", response.data)


class Test7_WorkoutDeletion(BaseTestCase):
    """Tests workout deletion, CSRF protection, and error handling."""

    def setUp(self):
        super().setUp()
        self.register_user(name="Deleter", email="deleter@example.com", password="password123")
        self.user = User.query.filter_by(email="deleter@example.com").first()
        self.workout = Workout(user_id=self.user.id, title="Session to delete", workout_type="Cardio", duration=30, calories=200, completed_on=date.today())
        db.session.add(self.workout)
        db.session.commit()
        self.workout_id = self.workout.id

    def test_possibility_34_delete_workout_invalid_csrf_fails(self):
        response = self.client.post(f"/workouts/{self.workout_id}/delete", data={"csrf_token": "wrong_token"}, follow_redirects=True)
        self.assertIn(b"Unable to remove that workout.", response.data)
        self.assertIsNotNone(db.session.get(Workout, self.workout_id))

    def test_possibility_35_delete_nonexistent_workout_id_fails(self):
        csrf = self.get_csrf_token("/dashboard")
        response = self.client.post("/workouts/99999/delete", data={"csrf_token": csrf}, follow_redirects=True)
        self.assertIn(b"Unable to remove that workout.", response.data)

    def test_possibility_36_delete_workout_success(self):
        csrf = self.get_csrf_token("/dashboard")
        response = self.client.post(f"/workouts/{self.workout_id}/delete", data={"csrf_token": csrf}, follow_redirects=True)
        self.assertIn(b"Workout removed.", response.data)
        self.assertIsNone(db.session.get(Workout, self.workout_id))


class Test8_DataIsolationAndSecurity(BaseTestCase):
    """Tests multi-tenant security: cross-user data isolation and unauthorized deletion protection."""

    def setUp(self):
        super().setUp()
        # User A
        self.user_a = User(name="User A", email="user_a@example.com")
        self.user_a.set_password("password123")
        db.session.add(self.user_a)
        db.session.commit()
        self.workout_a = Workout(user_id=self.user_a.id, title="Private Workout A", workout_type="Strength", duration=60, calories=400, completed_on=date.today())
        db.session.add(self.workout_a)
        db.session.commit()

        # User B
        self.user_b = User(name="User B", email="user_b@example.com")
        self.user_b.set_password("password123")
        db.session.add(self.user_b)
        db.session.commit()
        self.workout_b = Workout(user_id=self.user_b.id, title="Private Workout B", workout_type="Cardio", duration=30, calories=250, completed_on=date.today())
        db.session.add(self.workout_b)
        db.session.commit()

    def test_possibility_37_user_b_cannot_see_user_a_workouts(self):
        # Login as User B
        self.login_user(email="user_b@example.com", password="password123")

        # Check dashboard
        dash_response = self.client.get("/dashboard")
        self.assertIn(b"Private Workout B", dash_response.data)
        self.assertNotIn(b"Private Workout A", dash_response.data)

        # Check API
        api_response = self.client.get("/api/workouts")
        api_data = api_response.get_json()["data"]
        titles = [w["title"] for w in api_data]
        self.assertIn("Private Workout B", titles)
        self.assertNotIn("Private Workout A", titles)

    def test_possibility_38_user_b_cannot_delete_user_a_workout_idor_prevention(self):
        # Login as User B
        self.login_user(email="user_b@example.com", password="password123")
        csrf_b = self.get_csrf_token("/dashboard")

        # User B attempts to delete Workout A (owned by User A)
        response = self.client.post(f"/workouts/{self.workout_a.id}/delete", data={"csrf_token": csrf_b}, follow_redirects=True)
        self.assertIn(b"Unable to remove that workout.", response.data)

        # Confirm Workout A still exists intact in the database
        db_workout_a = db.session.get(Workout, self.workout_a.id)
        self.assertIsNotNone(db_workout_a)
        self.assertEqual(db_workout_a.title, "Private Workout A")


class Test9_LogoutPossibilities(BaseTestCase):
    """Tests logout CSRF requirements, session clearing, and post-logout access denial."""

    def setUp(self):
        super().setUp()
        self.register_user(name="Logout Tester", email="logout@example.com", password="password123")

    def test_possibility_39_logout_without_valid_csrf_retains_session(self):
        # POST to /logout with invalid CSRF token
        response = self.client.post("/logout", data={"csrf_token": "bad_token"}, follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        # Session user_id should still exist because csrf_valid() failed
        with self.client.session_transaction() as sess:
            self.assertIsNotNone(sess.get("user_id"))

    def test_possibility_40_logout_with_valid_csrf_clears_session_and_redirects(self):
        response = self.logout_user()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Welcome back", response.data)
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

    def test_possibility_41_post_logout_access_denied(self):
        # Log out
        self.logout_user()

        # Access /dashboard
        dash_response = self.client.get("/dashboard", follow_redirects=False)
        self.assertEqual(dash_response.status_code, 302)
        self.assertTrue(dash_response.headers["Location"].endswith("/login"))

        # Access /api/workouts
        api_response = self.client.get("/api/workouts")
        self.assertEqual(api_response.status_code, 401)
        self.assertEqual(api_response.get_json(), {"error": "Authentication required"})


if __name__ == "__main__":
    unittest.main()
