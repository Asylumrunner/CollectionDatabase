import importlib
import os
import sys
import time
import types
from unittest import mock

import pytest

# These run at collection time, before anything can import application code.
# The fake module also guarantees tests never load real credentials from Workers/secrets.py.
os.environ["TZ"] = "UTC"
time.tzset()

import Workers  # noqa: E402

from tests.helpers import FAKE_SECRETS  # noqa: E402

_fake_secrets_module = types.ModuleType("Workers.secrets")
_fake_secrets_module.secrets = dict(FAKE_SECRETS)
sys.modules["Workers.secrets"] = _fake_secrets_module
Workers.secrets = _fake_secrets_module


def fake_twitch_token():
    response = mock.Mock()
    response.json.return_value = {"access_token": "fake-igdb-token", "expires_in": 3600}
    return response


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # pytest counts a fixture error on an xfail test as the expected failure. That would make
    # tests that never ran, say because Docker is down, look fine, so report them as errors.
    outcome = yield
    report = outcome.get_result()
    if call.when == "setup" and hasattr(report, "wasxfail"):
        del report.wasxfail
        report.outcome = "failed"


@pytest.fixture(scope="session")
def api_module():
    """Imports api.py, which builds SearchWorker and so requests an IGDB token at import time."""
    with mock.patch("requests.post", return_value=fake_twitch_token()):
        return importlib.import_module("api")


@pytest.fixture(autouse=True)
def clean_auth_env(monkeypatch):
    # launch.json sets these, so they can leak in when tests run from the editor
    monkeypatch.delenv("SKIP_AUTH", raising=False)
    monkeypatch.delenv("DEV_USER_ID", raising=False)
