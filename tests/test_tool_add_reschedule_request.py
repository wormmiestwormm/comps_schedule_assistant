"""Tool: add_reschedule_request_arguments -> Database.process_reschedule,
_find_og_app, check_conflicts (see test_database_core) and append_new_temp_app."""
import pytest

from database import Database
from helpers import assert_params_match_method, assert_strict_schema, bug
from conftest import read_rows

BOB = "13107810954"  # student, standard appointment: wednesday 13:00-14:00 (app 3)


@pytest.fixture
def bob_db(db):
    assert db.find_user(BOB)
    return db


class TestRescheduleSchema:
    def test_strict_schema(self, tools_by_name):
        assert_strict_schema(tools_by_name["add_reschedule_request_arguments"])

    def test_properties(self, tools_by_name):
        props = tools_by_name["add_reschedule_request_arguments"].parameters["properties"]
        assert set(props) == {"original_appointment_day", "new_appointment_day",
                              "start_time", "end_time"}

    @bug("tool sends original_appointment_day/new_appointment_day/start_time/end_time but "
         "process_reschedule expects o_app_day/new_day/new_start/new_end")
    def test_arguments_bind_to_process_reschedule(self, tools_by_name):
        assert_params_match_method(tools_by_name["add_reschedule_request_arguments"],
                                   Database.process_reschedule)


class TestFindOriginalAppointment:
    def test_found(self, bob_db):
        assert bob_db._find_og_app("wednesday") is True
        assert bob_db.og_app[0] == "3"

    def test_wrong_day(self, bob_db):
        assert bob_db._find_og_app("monday") is False  # monday belongs to Jim / Alice

    def test_day_with_no_appointment(self, bob_db):
        assert bob_db._find_og_app("sunday") is False


class TestProcessReschedule:
    def test_original_not_found_asks_for_clarification(self, bob_db):
        msg = bob_db.process_reschedule("friday", "thursday", "10:00", "11:00")
        assert "friday" in msg and "not found" in msg

    def test_conflict_with_standard_appointment(self, bob_db):
        before = read_rows("mock_temp_apps.csv")
        msg = bob_db.process_reschedule("wednesday", "monday", "14:30", "15:30")
        assert msg == "conflict with standard appointment 1"
        assert read_rows("mock_temp_apps.csv") == before

    def test_conflict_with_existing_temp_appointment(self, bob_db):
        before = read_rows("mock_temp_apps.csv")
        msg = bob_db.process_reschedule("wednesday", "friday", "09:30", "10:30")
        assert msg == "conflict with temporary appointment 0"
        assert read_rows("mock_temp_apps.csv") == before

    @bug("append_new_temp_app calls convert_24_to_12h(new_start) with ONE argument but it "
         "needs two -> TypeError (after the row has already been written)")
    def test_success_writes_pending_request_and_confirms(self, bob_db):
        msg = bob_db.process_reschedule("wednesday", "thursday", "10:00", "11:00")
        assert msg == "Appointment for 3 changed to thursday, 10:00 AM-11:00 AM."

        rows = read_rows("mock_temp_apps.csv")
        new = rows[-1]
        assert new[1:] == ["3", "3", "thursday", "10:00", "11:00", "0", "0"]  # pending
        ids = [r[0] for r in rows[1:]]
        assert len(ids) == len(set(ids)), "temp ids must be unique"

    @bug("same one-argument convert_24_to_12h TypeError as above")
    def test_may_overlap_its_own_original_slot(self, bob_db):
        msg = bob_db.process_reschedule("wednesday", "wednesday", "13:30", "14:30")
        assert "changed to wednesday" in msg

    @bug("same one-argument convert_24_to_12h TypeError as above")
    def test_rescheduled_request_does_not_modify_standard_schedule(self, bob_db):
        before = read_rows("mock_schedule.csv")
        bob_db.process_reschedule("wednesday", "thursday", "10:00", "11:00")
        assert read_rows("mock_schedule.csv") == before
