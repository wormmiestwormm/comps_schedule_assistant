"""Tool: view_app_arguments  ->  Database.process_view and the return_*_list helpers."""
import pytest

from database import Database
from helpers import (assert_params_match_method, assert_strict_schema,
                     data_rows)


# ------------------------------ schema ------------------------------------
class TestViewAppSchema:
    def test_strict_schema(self, tools_by_name):
        assert_strict_schema(tools_by_name["view_app_arguments"])

    def test_properties(self, tools_by_name):
        props = tools_by_name["view_app_arguments"].parameters["properties"]
        assert props["specificity"]["type"] == "integer"
        assert "null" in props["student_name"]["type"]  # only used when specificity == 3

    def test_arguments_bind_to_process_view(self, tools_by_name):
        assert_params_match_method(tools_by_name["view_app_arguments"], Database.process_view)


# --------------------- specificity 0: user's own schedule -----------------
class TestOwnSchedule:
    def test_user_without_reschedule_sees_standard_appointment(self, db):
        db.find_user("13107810954")  # Bob
        rows = data_rows(db.process_view(0))
        assert rows == [["3", "3", "wednesday", "01:00 PM", "02:00 PM"]]

    def test_user_with_no_appointments_gets_empty_list(self, db, data_dir):
        # a student that exists but has no schedule rows
        with open("mock_people_database.csv", "a", newline="") as f:
            f.write("4,Cara,15550001111,student,\n")
        db.find_user("15550001111")
        assert data_rows(db.process_view(0)) == []

    def test_approved_reschedule_replaces_original(self, student_db):
        rows = data_rows(student_db.process_view(0))  # Alice: app 2 moved to friday
        assert len(rows) == 1
        assert rows[0][3] == "friday"
        assert rows[0][4:6] == ["09:00 AM", "10:00 AM"]

    def test_times_are_12_hour_format(self, db):
        db.find_user("13104069080")  # Jim
        row = data_rows(db.process_view(0))[0]
        assert row[3:5] == ["02:00 PM", "03:00 PM"]


# ------------------------ specificity 1: everything -----------------------
class TestCompleteSchedule:
    def test_includes_every_unmoved_appointment(self, tutor_db):
        ids = {r[0] for r in data_rows(tutor_db.process_view(1))}
        assert {"1", "3"} <= ids  # Jim's and Bob's standard appointments

    def test_moved_appointment_shown_once_at_new_time(self, tutor_db):
        rows = data_rows(tutor_db.process_view(1))
        alice = [r for r in rows if "2" in (r[1], r[2]) and r[0] in ("2", "0")]
        assert len(alice) == 1, alice
        assert "friday" in alice[0]

    def test_pending_requests_are_not_shown(self, tutor_db):
        with open("mock_temp_apps.csv", "a", newline="") as f:
            f.write("5,3,3,thursday,10:00,11:00,0,0\r\n")  # Bob, pending
        rows = data_rows(tutor_db.process_view(1))
        assert not any("thursday" in r for r in rows)


# --------------------------- specificity 2: today -------------------------
class TestDaySchedule:
    # 2026-10-05 is a Monday, 2026-10-07 a Wednesday, 2026-10-09 a Friday
    def test_monday_shows_only_unmoved_monday_appointments(self, tutor_db, fake_now):
        fake_now(2026, 10, 5)
        ids = [r[0] for r in data_rows(tutor_db.process_view(2))]
        assert ids == ["1"]  # app 2 was moved to friday

    def test_wednesday(self, tutor_db, fake_now):
        fake_now(2026, 10, 7)
        assert [r[0] for r in data_rows(tutor_db.process_view(2))] == ["3"]

    def test_friday_shows_the_approved_temp_appointment(self, tutor_db, fake_now):
        fake_now(2026, 10, 9)
        rows = data_rows(tutor_db.process_view(2))
        assert [r[0] for r in rows] == ["0"]
        assert rows[0][4:6] == ["09:00 AM", "10:00 AM"]

    def test_empty_day(self, tutor_db, fake_now):
        fake_now(2026, 10, 6)  # Tuesday
        assert data_rows(tutor_db.process_view(2)) == []


# ------------------------ specificity 3: a student ------------------------
class TestStudentSchedule:
    def test_by_student_name(self, tutor_db):
        rows = data_rows(tutor_db.process_view(3, "Bob"))
        assert rows == [["3", "3", "wednesday", "01:00 PM", "02:00 PM"]]

    def test_unknown_student(self, tutor_db):
        msg = tutor_db.process_view(3, "Zed")
        assert "Zed" in msg and "not found" in msg


# ------------------------------ bad input ---------------------------------
@pytest.mark.parametrize("bad", [-1, 4, 99])
def test_invalid_specificity_returns_error_message(tutor_db, bad):
    assert tutor_db.process_view(bad).startswith("Error")


def test_default_arguments_return_complete_schedule(tutor_db):
    assert tutor_db.process_view() == tutor_db.return_complete_app_list()
