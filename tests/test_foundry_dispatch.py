"""
Agent <-> database wiring:
  * FoundryModel.read_message routes every tool call to the right Database method
    (the Database is an *autospec*, so wrong keyword names raise TypeError just like
    they would in production)
  * conversation handling and the follow-up request that returns tool output
  * init_agents registers the tools and tells the model about them
"""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, create_autospec

import pytest

import init_tools
from database import Database
from helpers import bug

# tool name -> Database method it must call
DISPATCH = {
    "view_app_arguments": "process_view",
    "add_student_arguments": "add_new_student",
    "add_appointment_arguments": "add_new_app",
    "add_reschedule_request_arguments": "process_reschedule",
    "approve_request_arguments": "approve_appointment",
}
SCHEMA_MISMATCH = {
    "add_student_arguments": "tool arg 'phone_number' vs method param 'phone_num'",
    "add_appointment_arguments": "tool arg 'app_day' vs method param 'day'",
    "add_reschedule_request_arguments": "tool arg names differ from process_reschedule params",
}


# ------------------------------ helpers -----------------------------------
def tool_call(name, args, call_id="call_1"):
    return SimpleNamespace(type="function_call", name=name, call_id=call_id,
                           arguments=json.dumps(args))


def response(output=(), text=""):
    return SimpleNamespace(output=list(output), output_text=text)


def dummy_args(tool):
    """Build arguments exactly the way the model would, from the tool's own schema."""
    sample = {"string": "x", "integer": 1, "boolean": True, "null": None}
    args = {}
    for name, spec in tool.parameters["properties"].items():
        t = spec["type"]
        t = next(x for x in t if x != "null") if isinstance(t, list) else t
        args[name] = sample[t]
    return args


@pytest.fixture
def agent(monkeypatch):
    """(FoundryModel, autospec'd Database instance) with every network client mocked."""
    import foundry_module
    monkeypatch.setenv("FOUNDRYPROJECTENDPOINT", "https://example.test")
    monkeypatch.setattr(foundry_module, "AIProjectClient", MagicMock())
    monkeypatch.setattr(foundry_module, "DefaultAzureCredential", MagicMock())

    fake_db = create_autospec(Database, instance=True)
    fake_db.find_user.return_value = True
    fake_db.get_convo_id.return_value = "conv_1"
    monkeypatch.setattr(foundry_module, "Database", MagicMock(return_value=fake_db))

    return foundry_module.FoundryModel(), fake_db


# ----------------------- read_message: basic flow --------------------------
class TestReadMessage:
    def test_unknown_phone_number_is_ignored(self, agent):
        model, db = agent
        db.find_user.return_value = False
        assert model.read_message("hi", "1999") is None
        model.openai.responses.create.assert_not_called()

    def test_plain_answer_is_returned_without_follow_up(self, agent):
        model, _ = agent
        model.openai.responses.create.return_value = response(text="Hello!")
        assert model.read_message("hi", "1310") == "Hello!"
        assert model.openai.responses.create.call_count == 1

    def test_existing_conversation_is_reused(self, agent):
        model, db = agent
        model.openai.responses.create.return_value = response(text="ok")
        model.read_message("hi", "1310")
        model.openai.conversations.create.assert_not_called()
        kwargs = model.openai.responses.create.call_args.kwargs
        assert kwargs["conversation"] == "conv_1"
        assert kwargs["input"] == "hi"
        assert kwargs["extra_body"]["agent_reference"]["name"] == "message-reader"

    def test_new_conversation_is_created_and_saved(self, agent):
        model, db = agent
        db.get_convo_id.return_value = ""
        model.openai.conversations.create.return_value = SimpleNamespace(id="conv_new")
        model.openai.responses.create.return_value = response(text="ok")

        model.read_message("hi", "1310")

        db.set_convo_id.assert_called_once_with("conv_new")
        assert model.openai.responses.create.call_args.kwargs["conversation"] == "conv_new"


# ------------------------ read_message: tool routing -----------------------
def _routing_params():
    for tool_name, method in DISPATCH.items():
        marks = [bug(SCHEMA_MISMATCH[tool_name])] if tool_name in SCHEMA_MISMATCH else []
        yield pytest.param(tool_name, method, id=tool_name, marks=marks)


class TestToolRouting:
    @pytest.mark.parametrize("tool_name,method", list(_routing_params()))
    def test_tool_call_reaches_database_method(self, agent, tools_by_name, tool_name, method):
        model, db = agent
        args = dummy_args(tools_by_name[tool_name])
        getattr(db, method).return_value = "DB RESULT"
        model.openai.responses.create.side_effect = [
            response([tool_call(tool_name, args)]),
            response(text="final answer"),
        ]

        assert model.read_message("do it", "1310") == "final answer"

        getattr(db, method).assert_called_once_with(**args)

    def test_every_tool_in_init_tools_has_a_dispatch_case(self):
        assert set(DISPATCH) == {t.name for t in init_tools.build_tools()}

    def test_tool_output_is_sent_back_with_matching_call_id(self, agent):
        model, db = agent
        db.process_view.return_value = [["3", "3", "wednesday", "01:00 PM", "02:00 PM"]]
        model.openai.responses.create.side_effect = [
            response([tool_call("view_app_arguments",
                                {"specificity": 0, "student_name": None}, "abc")]),
            response(text="done"),
        ]
        model.read_message("my schedule", "1310")

        follow_up = model.openai.responses.create.call_args_list[1].kwargs
        assert follow_up["conversation"] == "conv_1"
        call, output = follow_up["input"]
        assert call["type"] == "function_call" and call["call_id"] == "abc"
        assert call["name"] == "view_app_arguments"
        assert output["type"] == "function_call_output" and output["call_id"] == "abc"
        assert json.loads(output["output"]) == {
            "result": [["3", "3", "wednesday", "01:00 PM", "02:00 PM"]]}

    def test_several_tool_calls_in_one_response(self, agent):
        model, db = agent
        db.process_view.return_value = "view"
        db.approve_appointment.return_value = "approve"
        model.openai.responses.create.side_effect = [
            response([
                tool_call("view_app_arguments", {"specificity": 1, "student_name": None}, "a"),
                tool_call("approve_request_arguments",
                          {"student_name": "Bob", "approval": True, "temp_id": None}, "b"),
            ]),
            response(text="both done"),
        ]
        assert model.read_message("x", "1310") == "both done"

        items = model.openai.responses.create.call_args_list[1].kwargs["input"]
        outputs = [i for i in items if i["type"] == "function_call_output"]
        assert [(o["call_id"], json.loads(o["output"])["result"]) for o in outputs] == \
            [("a", "view"), ("b", "approve")]

    def test_unknown_tool_name_is_reported_to_the_model(self, agent):
        model, _ = agent
        model.openai.responses.create.side_effect = [
            response([tool_call("delete_everything", {})]),
            response(text="sorry"),
        ]
        model.read_message("x", "1310")
        output = model.openai.responses.create.call_args_list[1].kwargs["input"][1]
        assert "not a function call: delete_everything" in json.loads(output["output"])["result"]

    def test_non_function_output_items_are_ignored(self, agent):
        model, _ = agent
        model.openai.responses.create.return_value = response(
            [SimpleNamespace(type="message")], text="just text")
        assert model.read_message("x", "1310") == "just text"
        assert model.openai.responses.create.call_count == 1


# ------------------------------ init_agents --------------------------------
class TestInitAgents:
    @pytest.fixture
    def created(self, monkeypatch):
        import init_agents
        monkeypatch.setenv("FOUNDRYPROJECTENDPOINT", "https://example.test")
        client = MagicMock()
        monkeypatch.setattr(init_agents, "AIProjectClient", MagicMock(return_value=client))
        monkeypatch.setattr(init_agents, "DefaultAzureCredential", MagicMock())
        init_agents.init_agents()
        return client.agents.create_version.call_args.kwargs

    def test_agent_name_matches_the_name_foundry_module_calls(self, created):
        assert created["agent_name"] == "message-reader"

    def test_all_tools_are_registered(self, created):
        names = [t.name for t in created["definition"].tools]
        assert sorted(names) == sorted(DISPATCH)

    @pytest.mark.parametrize("tool_name", [
        "view_app_arguments", "add_student_arguments", "add_appointment_arguments",
        pytest.param("add_reschedule_request_arguments", marks=bug(
            "instructions never mention the reschedule tool, so the model has no guidance")),
        pytest.param("approve_request_arguments", marks=bug(
            "instructions never mention the approve tool, so the model has no guidance")),
    ])
    def test_instructions_mention_tool(self, created, tool_name):
        assert tool_name in created["definition"].instructions
