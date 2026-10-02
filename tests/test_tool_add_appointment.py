"""Tool: add_appointment_arguments  ->  Database.add_new_app."""
from database import Database
from helpers import assert_params_match_method, assert_strict_schema, bug
from conftest import read_rows

NO_INIT = ("Database has no __init__ (it is named 'init'), so check_conflicts raises "
           "AttributeError on self.og_app; find_student also searches the phone column")


class TestAddAppointmentSchema:
    def test_strict_schema(self, tools_by_name):
        assert_strict_schema(tools_by_name["add_appointment_arguments"])

    def test_properties(self, tools_by_name):
        props = tools_by_name["add_appointment_arguments"].parameters["properties"]
        assert set(props) == {"student_name", "app_day", "start_time", "end_time"}

    @bug("tool sends 'app_day' but add_new_app's parameter is 'day'")
    def test_arguments_bind_to_add_new_app(self, tools_by_name):
        assert_params_match_method(tools_by_name["add_appointment_arguments"],
                                   Database.add_new_app)


class TestAddNewApp:
    @bug(NO_INIT)
    def test_adds_row_and_confirms(self, tutor_db):
        msg = tutor_db.add_new_app("Alice", "tuesday", "10:00", "11:00")
        assert msg == "Appointment for Alice on tuesday, 10:00 AM-11:00 AM added."
        assert read_rows("mock_schedule.csv")[-1] == ["4", "2", "tuesday", "10:00", "11:00"]

    @bug(NO_INIT)
    def test_conflict_is_rejected_and_nothing_written(self, tutor_db):
        before = read_rows("mock_schedule.csv")
        msg = tutor_db.add_new_app("Alice", "monday", "14:30", "15:30")
        assert "conflict" in msg
        assert read_rows("mock_schedule.csv") == before

    @bug(NO_INIT)
    def test_back_to_back_is_allowed(self, tutor_db):
        msg = tutor_db.add_new_app("Alice", "monday", "15:00", "16:00")
        assert "added" in msg

    @bug(NO_INIT)
    def test_unknown_student_is_rejected(self, tutor_db):
        before = read_rows("mock_schedule.csv")
        msg = tutor_db.add_new_app("Zed", "tuesday", "10:00", "11:00")
        assert "not found" in msg
        assert read_rows("mock_schedule.csv") == before

    @bug(NO_INIT)
    def test_new_appointment_appears_in_schedule_view(self, tutor_db):
        tutor_db.add_new_app("Bob", "thursday", "16:00", "17:00")
        rows = tutor_db.process_view(3, "Bob")
        assert any("thursday" in r for r in rows)
