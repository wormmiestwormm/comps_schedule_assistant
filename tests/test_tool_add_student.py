"""Tool: add_student_arguments  ->  Database.add_new_student."""
from database import Database
from helpers import assert_params_match_method, assert_strict_schema, bug
from conftest import PEOPLE_HEADER, read_rows


class TestAddStudentSchema:
    def test_properties_present(self, tools_by_name):
        props = tools_by_name["add_student_arguments"].parameters["properties"]
        assert {"name", "phone_number"} <= set(props)
        assert all(p["type"] == "string" for p in props.values())

    @bug("'required' lists 'student_name' but the property is called 'name'; strict "
         "schemas must have required == properties")
    def test_strict_schema(self, tools_by_name):
        assert_strict_schema(tools_by_name["add_student_arguments"])

    @bug("tool sends 'phone_number' but add_new_student's parameter is 'phone_num'")
    def test_arguments_bind_to_add_new_student(self, tools_by_name):
        assert_params_match_method(tools_by_name["add_student_arguments"],
                                   Database.add_new_student)


class TestAddNewStudent:
    def test_appends_row_with_next_id(self, tutor_db):
        tutor_db.add_new_student("Dave", "15551234567")
        last = read_rows("mock_people_database.csv")[-1]
        assert last[:3] == ["4", "Dave", "15551234567"]

    def test_returns_confirmation(self, tutor_db):
        assert tutor_db.add_new_student("Dave", "15551234567") == "New student Dave added."

    def test_existing_rows_untouched(self, tutor_db):
        before = read_rows("mock_people_database.csv")
        tutor_db.add_new_student("Dave", "15551234567")
        assert read_rows("mock_people_database.csv")[:len(before)] == before

    def test_ids_stay_unique_over_several_adds(self, tutor_db):
        for i in range(3):
            tutor_db.add_new_student(f"S{i}", f"1555000000{i}")
        ids = [r[0] for r in read_rows("mock_people_database.csv")[1:]]
        assert len(ids) == len(set(ids)) == 6

    @bug("new row only has 3 columns (id, name, number); role and convo_id are missing")
    def test_row_has_every_column_and_student_role(self, tutor_db):
        tutor_db.add_new_student("Dave", "15551234567")
        rows = read_rows("mock_people_database.csv")
        assert len(rows[-1]) == len(PEOPLE_HEADER)
        assert rows[-1][3] == "student"

    @bug("find_user reads u[3] (role), which doesn't exist on the short row -> IndexError")
    def test_new_student_can_text_the_bot_immediately(self, tutor_db):
        tutor_db.add_new_student("Dave", "15551234567")
        fresh = Database()
        assert fresh.find_user("15551234567") is True
