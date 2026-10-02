"""
Shared fixtures for the scheduling-assistant test suite.

* Every test runs inside a throw-away temp directory containing fresh copies of
  the three CSV "tables", because database.py opens them via relative paths.
* If the Azure / OpenAI SDKs aren't installed, tiny stand-ins are registered so
  foundry_module / init_tools can still be imported (no network is ever used).
"""
import csv
import sys
import types
from datetime import datetime
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# --------------------------------------------------------------------------
# Optional SDK stubs
# --------------------------------------------------------------------------
def _install_sdk_stubs():
    try:
        import azure.ai.projects.models  # noqa: F401
        import azure.identity  # noqa: F401
        import openai  # noqa: F401
        return
    except ImportError:
        pass

    class FunctionTool:
        def __init__(self, name, parameters, description=None, strict=None):
            self.name, self.parameters = name, parameters
            self.description, self.strict = description, strict

    class PromptAgentDefinition:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    def mod(name, **attrs):
        m = types.ModuleType(name)
        m.__dict__.update(attrs)
        sys.modules[name] = m
        return m

    mod("azure")
    mod("azure.ai")
    mod("azure.ai.projects", AIProjectClient=object)
    mod("azure.ai.projects.models", FunctionTool=FunctionTool, Tool=object,
        PromptAgentDefinition=PromptAgentDefinition)
    mod("azure.identity", DefaultAzureCredential=object)
    mod("openai", OpenAI=object)
    mod("openai.types")
    mod("openai.types.responses")
    mod("openai.types.responses.response_input_param",
        FunctionCallOutput=dict, ResponseInputParam=list)


_install_sdk_stubs()


# --------------------------------------------------------------------------
# CSV fixtures (same shape as the mock_*.csv files in the project)
# --------------------------------------------------------------------------
PEOPLE_HEADER = ["id", "name", "number", "role", "convo_id"]
PEOPLE_ROWS = [
    ["1", "Jim", "13104069080", "tutor", ""],
    ["2", "Alice", "14242120987", "student", ""],
    ["3", "Bob", "13107810954", "student", "conv_existing"],
]

SCHEDULE_HEADER = ["app_id", "student_id", "day", "start_time", "end_time"]
SCHEDULE_ROWS = [
    ["1", "1", "monday", "14:00", "15:00"],
    ["2", "2", "monday", "12:00", "13:00"],
    ["3", "3", "wednesday", "13:00", "14:00"],
]

TEMP_HEADER = ["temp_id", "app_id", "student_id", "new_day", "new_start",
               "new_end", "approval", "completed"]
# one approved reschedule of Alice's appointment (app 2) -> friday 09:00-10:00
TEMP_ROWS = [
    ["0", "2", "2", "friday", "09:00", "10:00", "1", "0"],
]


def _write(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def read_rows(path):
    """Return a CSV file as a list of lists (header included)."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Fresh CSVs in a temp dir that is also the current working directory."""
    _write(tmp_path / "mock_people_database.csv", PEOPLE_HEADER, PEOPLE_ROWS)
    _write(tmp_path / "mock_schedule.csv", SCHEDULE_HEADER, SCHEDULE_ROWS)
    _write(tmp_path / "mock_temp_apps.csv", TEMP_HEADER, TEMP_ROWS)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def db(data_dir):
    """A Database with no user selected yet."""
    from database import Database
    return Database()


@pytest.fixture
def tutor_db(db):
    """Database acting on behalf of the tutor (Jim, id 1)."""
    assert db.find_user("13104069080")
    return db


@pytest.fixture
def student_db(db):
    """Database acting on behalf of student Alice (id 2)."""
    assert db.find_user("14242120987")
    return db


@pytest.fixture
def fake_now(monkeypatch):
    """Freeze datetime.now() inside database.py. Usage: fake_now(2026, 10, 5)."""
    import database

    def _set(year, month, day):
        class FakeDT(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(year, month, day, 12, 0)
        monkeypatch.setattr(database, "datetime", FakeDT)
    return _set


@pytest.fixture
def tools_by_name():
    """The FunctionTool definitions from init_tools, keyed by tool name."""
    import init_tools
    return {t.name: t for t in init_tools.build_tools()}
