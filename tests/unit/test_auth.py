from types import SimpleNamespace
from unittest import mock

import flask
import pytest

import Utilities.AuthenticateRequest as auth


@pytest.fixture
def clerk_state(monkeypatch):
    """Makes the Clerk SDK report the given request state."""
    def set_state(payload=None, is_signed_in=False, error=None):
        clerk = mock.Mock()
        clerk.authenticate_request.return_value = SimpleNamespace(payload=payload, is_signed_in=is_signed_in)
        clerk.authenticate_request.side_effect = error
        monkeypatch.setattr(auth, "Clerk", mock.Mock(return_value=clerk))
        return clerk
    return set_state


@pytest.fixture
def app():
    app = flask.Flask("auth_test")

    @app.route("/ok")
    @auth.authenticated_endpoint
    def ok(user_id=None):
        return flask.jsonify({"user_id": user_id})

    @app.route("/crash")
    @auth.authenticated_endpoint
    def crash(user_id=None):
        raise RuntimeError("handler bug")

    return app


def test_skip_auth_returns_the_dev_user(monkeypatch):  # U-AUTH-1
    monkeypatch.setenv("SKIP_AUTH", "true")
    monkeypatch.setenv("DEV_USER_ID", "dev_1")
    assert auth.is_signed_in(None) == "dev_1"


def test_skip_auth_has_a_default_user(monkeypatch):  # U-AUTH-1
    monkeypatch.setenv("SKIP_AUTH", "true")
    assert auth.is_signed_in(None) == "test_user_dev"


def test_empty_skip_auth_enforces_auth(monkeypatch, clerk_state):  # U-AUTH-2
    monkeypatch.setenv("SKIP_AUTH", "")
    clerk_state(error=RuntimeError("checked"))
    with pytest.raises(RuntimeError):
        auth.is_signed_in(mock.Mock())


@pytest.mark.xfail(reason="B5: any non-empty SKIP_AUTH disables authentication")
@pytest.mark.parametrize("value", ["false", "0"])
def test_false_skip_auth_values_enforce_auth(monkeypatch, clerk_state, value):  # U-AUTH-2
    monkeypatch.setenv("SKIP_AUTH", value)
    clerk_state(error=RuntimeError("checked"))
    with pytest.raises(RuntimeError):
        auth.is_signed_in(mock.Mock())


def test_signed_in_requests_return_the_subject(clerk_state):  # U-AUTH-3
    clerk = clerk_state(payload={"sub": "user_1"}, is_signed_in=True)
    assert auth.is_signed_in(mock.Mock()) == "user_1"
    clerk.authenticate_request.assert_called_once()


@pytest.mark.xfail(reason="B15: payload.get on a None payload produces a NoneType error instead of an auth message")
def test_signed_out_requests_get_a_clear_message(clerk_state):  # U-AUTH-4
    clerk_state(payload=None, is_signed_in=False)
    with pytest.raises(Exception) as caught:
        auth.is_signed_in(mock.Mock())
    assert "authenticated" in str(caught.value).lower()


@pytest.mark.xfail(reason="B15: ClerkError is a pydantic model, so raising it with a message is a TypeError")
def test_unsigned_payload_gets_a_clear_message(clerk_state):  # U-AUTH-4
    clerk_state(payload={"sub": "user_1"}, is_signed_in=False)
    with pytest.raises(Exception) as caught:
        auth.is_signed_in(mock.Mock())
    assert "authenticated" in str(caught.value).lower()


def test_clerk_errors_become_a_standard_401(app, clerk_state):  # U-AUTH-5
    clerk_state(error=RuntimeError("clerk unavailable"))
    response = app.test_client().get("/ok")
    assert response.status_code == 401
    assert response.get_json() == {"status": "FAILURE", "data": [], "err_msg": "clerk unavailable", "next_page": ""}


def test_decorator_injects_user_id_and_preserves_the_name(app, monkeypatch):  # U-AUTH-6
    monkeypatch.setenv("SKIP_AUTH", "true")
    monkeypatch.setenv("DEV_USER_ID", "dev_1")
    assert app.test_client().get("/ok").get_json() == {"user_id": "dev_1"}
    assert app.view_functions["ok"].__name__ == "ok"


def test_handler_exceptions_are_not_reported_as_auth_failures(app, monkeypatch):  # U-AUTH-7
    monkeypatch.setenv("SKIP_AUTH", "true")
    assert app.test_client().get("/crash").status_code != 401
