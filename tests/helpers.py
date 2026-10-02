import inspect

import pytest


def bug(reason):
    """
    Mark a test that documents a KNOWN BUG in the current code.

    The test asserts the *intended* behaviour, so it fails today and is reported
    as XFAIL (suite stays green). strict=True means that once you fix the bug
    the test XPASSes -> reported as a failure -> delete the marker.
    See every bug with:  pytest --runxfail
    """
    return pytest.mark.xfail(strict=True, reason=f"BUG: {reason}")


def assert_strict_schema(tool):
    """Azure/OpenAI strict function schemas: every property must be required."""
    params = tool.parameters
    assert tool.strict is True
    assert params["type"] == "object"
    assert params.get("additionalProperties") is False
    props, required = set(params["properties"]), set(params["required"])
    assert required == props, (
        f"'required' {sorted(required)} must equal properties {sorted(props)}"
    )


def assert_params_match_method(tool, method):
    """The model calls  method(**json.loads(arguments)) -> names must bind."""
    names = list(tool.parameters["properties"])
    try:
        inspect.signature(method).bind(object(), **{n: None for n in names})
    except TypeError as exc:
        pytest.fail(f"{tool.name} args {names} don't fit {method.__qualname__}: {exc}")


def data_rows(rows):
    """Drop the header row(s) that the schedule views pass through."""
    return [r for r in rows if r[0] not in ("app_id", "temp_id")]
