"""Tool: approve_request_arguments -> Database.approve_appointment and _find_temp_app."""
import pytest

from database import Database
from helpers import (assert_params_match_method, assert_strict_schema, bug,
                     data_rows)
from conftest import read_rows

FIND_STUDENT = "find_student searches the phone-number column, so the student is never found"
FIND_TEMP = ("_find_temp_app is defined twice; the 2nd (no-arg, reads data.csv) overrides the "
             "1st (temp_id lookup) -> TypeError")
STUDENT_ID_TYPE = ("_find_temp_app() compares an int column to the string student id, so it "
                   "finds nothing, and temp_app_list[0][0] on a DataFrame raises KeyError")

BOB_PENDING_1 = "1,3,3,thursday,10:00,11:00,0,0\r\n"
BOB_PENDING_2 = "2,3,3,friday,15:00,16:00,0,0\r\n"


def add_temp_rows(*lines):
    with open("mock_temp_apps.csv", "a", newline="") as f:
        f.write("".join(lines))


def temp_row(temp_id):
    return next(r for r in read_rows("mock_temp_apps.csv")[1:] if r[0] == str(temp_id))


class TestApproveSchema:
    def test_strict_schema(self, tools_by_name):
        assert_strict_schema(tools_by_name["approve_request_arguments"])

    def test_property_types(self, tools_by_name):
        props = tools_by_name["approve_request_arguments"].parameters["properties"]
        assert props["student_name"]["type"] == "string"
        assert props["approval"]["type"] == "boolean"
        assert set(props["temp_id"]["type"]) == {"integer", "null"}

    def test_arguments_bind_to_approve_appointment(self, tools_by_name):
        assert_params_match_method(tools_by_name["approve_request_arguments"],
                                   Database.approve_appointment)

    @bug("student_name's description was copy-pasted ('the day the original appointment "
         "was scheduled for'), which misleads the model")
    def test_student_name_description_mentions_student(self, tools_by_name):
        desc = tools_by_name["approve_request_arguments"].parameters["properties"]["student_name"]["description"]
        assert "student" in desc.lower()


class TestFindTempApp:
    @bug(FIND_TEMP)
    def test_found_by_id(self, tutor_db):
        assert tutor_db._find_temp_app("0") is True
        assert tutor_db.temp_app[0] == "0"

    @bug(FIND_TEMP)
    def test_missing_id(self, tutor_db):
        assert tutor_db._find_temp_app("42") is False


class TestApproveAppointment:
    def test_unknown_student(self, tutor_db):
        msg = tutor_db.approve_appointment("Zed", True)
        assert "Zed" in msg and "not found" in msg

    # ---- explicit temp_id (what the model sends once the student is ambiguous) ----
    @bug(f"{FIND_STUDENT}; also {FIND_TEMP}")
    def test_approve_by_temp_id(self, tutor_db):
        add_temp_rows(BOB_PENDING_1, BOB_PENDING_2)
        msg = tutor_db.approve_appointment("Bob", True, temp_id=1)  # tool sends an int

        assert temp_row(1)[6] in ("1", "True")
        assert temp_row(2)[6] == "0"      # other request untouched
        assert temp_row(0)[6] == "1"      # pre-approved row untouched
        assert "1" in msg and "not found" not in msg

    @bug(f"{FIND_STUDENT}; also {FIND_TEMP}")
    def test_deny_by_temp_id(self, tutor_db):
        # temp 0 (Alice) starts out approved; denying it must flip it
        assert temp_row(0)[6] == "1"
        tutor_db.approve_appointment("Alice", False, temp_id=0)
        assert temp_row(0)[6] in ("0", "False")

    @bug(f"{FIND_STUDENT}; also {FIND_TEMP}")
    def test_unknown_temp_id(self, tutor_db):
        msg = tutor_db.approve_appointment("Bob", True, temp_id=99)
        assert "99" in msg and "not found" in msg

    # ---- no temp_id: resolve through the student name ----
    @bug(f"{FIND_STUDENT}; also {STUDENT_ID_TYPE}")
    def test_single_pending_request_is_approved_without_id(self, tutor_db):
        add_temp_rows(BOB_PENDING_1)
        tutor_db.approve_appointment("Bob", True)
        assert temp_row(1)[6] in ("1", "True")

    @bug(f"{FIND_STUDENT}; also {STUDENT_ID_TYPE}")
    def test_several_requests_asks_for_clarification_and_changes_nothing(self, tutor_db):
        add_temp_rows(BOB_PENDING_1, BOB_PENDING_2)
        before = read_rows("mock_temp_apps.csv")
        msg = tutor_db.approve_appointment("Bob", True)
        assert "clarify" in msg and "id" in msg
        assert read_rows("mock_temp_apps.csv") == before

    @bug(f"{FIND_STUDENT}; also {STUDENT_ID_TYPE}")
    def test_student_with_no_requests_gets_a_message_not_an_exception(self, tutor_db):
        msg = tutor_db.approve_appointment("Bob", True)
        assert isinstance(msg, str)
        assert "request" in msg.lower() and "not found in database" not in msg

    # ---- end to end ----
    @bug(f"{FIND_STUDENT}; also {FIND_TEMP}; and views compare approval with ints")
    def test_approved_request_shows_up_in_students_schedule(self, tutor_db):
        add_temp_rows(BOB_PENDING_1)
        tutor_db.approve_appointment("Bob", True, temp_id=1)
        rows = data_rows(tutor_db.process_view(3, "Bob"))
        assert len(rows) == 1 and rows[0][3] == "thursday"
