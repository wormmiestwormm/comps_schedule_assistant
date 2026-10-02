"""Shared Database helpers used by several agent tools."""
import csv
from pathlib import Path

import pytest

from database import Database
from helpers import bug
from conftest import PROJECT_ROOT, read_rows


# ----------------------------- find_user ---------------------------------
class TestFindUser:
    def test_found_sets_user_and_phone(self, db):
        assert db.find_user("14242120987") is True
        assert db.phone_num == "14242120987"
        assert db.user[0] == "2" and db.user[1] == "Alice"

    def test_unknown_number_returns_false(self, db):
        assert db.find_user("19999999999") is False


# ---------------------------- find_student -------------------------------
class TestFindStudent:
    def test_finds_by_name(self, tutor_db):
        assert tutor_db.find_student("Alice") is True
        assert tutor_db.student[0] == "2"

    def test_finds_by_first_name_fragment(self, tutor_db):
        assert tutor_db.find_student("Bo") is True
        assert tutor_db.student[1] == "Bob"

    def test_unknown_name_returns_false(self, tutor_db):
        assert tutor_db.find_student("Zed") is False

    def test_phone_number_fragment_is_not_a_name_match(self, tutor_db):
        assert tutor_db.find_student("1310") is False


# ----------------------------- convo ids ---------------------------------
class TestConversationId:
    def test_empty_when_none_set(self, student_db):
        assert student_db.get_convo_id() == ""

    def test_returns_existing_id(self, db):
        db.find_user("13107810954")  # Bob
        assert db.get_convo_id() == "conv_existing"

    def test_set_persists_and_is_found_by_a_new_instance(self, student_db):
        student_db.set_convo_id("conv_new")

        fresh = Database()
        assert fresh.find_user("14242120987")
        assert fresh.get_convo_id() == "conv_new"

    def test_set_only_changes_the_current_user(self, student_db):
        student_db.set_convo_id("conv_new")
        rows = {r[1]: r for r in read_rows("mock_people_database.csv")[1:]}
        assert rows["Alice"][4] == "conv_new"
        assert rows["Bob"][4] == "conv_existing"
        assert rows["Jim"][4] == ""

    @bug("the real mock_people_database.csv header has ' convo_id' (leading space) AND "
         "'convo_id', so get_convo_id() (index 4) never sees the saved id")
    def test_real_people_csv_header_is_clean(self):
        path = Path(PROJECT_ROOT) / "mock_people_database.csv"
        if not path.exists():
            pytest.skip("mock_people_database.csv not found next to the tests")
        with open(path, newline="", encoding="utf-8") as f:
            header = next(csv.reader(f))
        assert header == [h.strip() for h in header], f"whitespace in header: {header}"
        assert len(header) == len(set(header)), f"duplicate columns: {header}"


# ------------------------- time conversion -------------------------------
class TestConvert24To12h:
    @pytest.mark.parametrize("start,end,expected", [
        ("14:00", "15:30", ("02:00 PM", "03:30 PM")),
        ("09:05", "10:00", ("09:05 AM", "10:00 AM")),
        ("00:00", "12:00", ("12:00 AM", "12:00 PM")),
        ("23:59", "23:59", ("11:59 PM", "11:59 PM")),
    ])
    def test_conversion(self, db, start, end, expected):
        assert db.convert_24_to_12h(start, end) == expected

    @pytest.mark.parametrize("bad", ["25:00", "2pm", "", "14-00"])
    def test_bad_input_raises(self, db, bad):
        with pytest.raises(ValueError):
            db.convert_24_to_12h(bad, "10:00")


class TestConvertAppListTimes:
    def test_standard_and_temp_rows_and_headers(self, db):
        rows = [
            ["app_id", "student_id", "day", "start_time", "end_time"],   # header
            ["1", "1", "monday", "14:00", "15:00"],                      # 5 cols
            ["temp_id", "app_id", "student_id", "new_day", "new_start",
             "new_end", "approval", "completed"],                        # header
            ["0", "2", "2", "friday", "09:00", "10:00", "1", "0"],       # 8 cols
        ]
        out = db._convert_app_list_times(rows)
        assert out[0][3] == "start_time"
        assert out[1][3:5] == ["02:00 PM", "03:00 PM"]
        assert out[2][4] == "new_start"
        assert out[3][4:6] == ["09:00 AM", "10:00 AM"]
        assert out[3][3] == "friday" and out[3][6:] == ["1", "0"]


# --------------------------- check_conflicts -----------------------------
class TestCheckConflicts:
    """
    check_conflicts reads self.og_app, which is only set by _find_og_app().
    These tests set it explicitly so the overlap logic is tested in isolation.
    """

    @pytest.fixture
    def cdb(self, db):
        db.og_app = None
        return db

    def test_free_slot_returns_none(self, cdb):
        assert cdb.check_conflicts("tuesday", "10:00", "11:00") is None

    def test_overlap_with_standard_appointment(self, cdb):
        assert cdb.check_conflicts("monday", "14:30", "15:30") == \
            "conflict with standard appointment 1"

    def test_new_slot_fully_inside_existing(self, cdb):
        assert "standard appointment 1" in cdb.check_conflicts("monday", "14:15", "14:45")

    def test_new_slot_fully_around_existing(self, cdb):
        assert "standard appointment 1" in cdb.check_conflicts("monday", "13:30", "16:00")

    @pytest.mark.parametrize("start,end", [("15:00", "16:00"), ("13:30", "14:00")])
    def test_back_to_back_is_not_a_conflict(self, cdb, start, end):
        assert cdb.check_conflicts("monday", start, end) is None

    def test_same_time_other_day_is_fine(self, cdb):
        assert cdb.check_conflicts("tuesday", "14:00", "15:00") is None

    def test_overlap_with_temporary_appointment(self, cdb):
        assert cdb.check_conflicts("friday", "09:30", "10:30") == \
            "conflict with temporary appointment 0"

    def test_ignores_its_own_original_appointment(self, cdb):
        cdb.og_app = ["2", "2", "monday", "12:00", "13:00"]
        assert cdb.check_conflicts("monday", "12:00", "13:00") is None

    def test_ignores_temp_appointments_of_its_own_original(self, cdb):
        cdb.og_app = ["2", "2", "monday", "12:00", "13:00"]  # temp 0 belongs to app 2
        assert cdb.check_conflicts("friday", "09:00", "10:00") is None
