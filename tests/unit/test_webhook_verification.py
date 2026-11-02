"""Signatures here are real: Svix signing and verification are local computations."""
import base64
import datetime

import flask
import pytest

from Utilities.VerifyClerkWebhook import verify_clerk_webhook
from Workers.secrets import secrets

from tests.helpers import signed_webhook

PAYLOAD = {"type": "user.created", "data": {"id": "user_1"}}


@pytest.fixture
def received():
    return []


@pytest.fixture
def client(received):
    app = flask.Flask("webhook_test")

    @app.route("/hook", methods=["POST"])
    @verify_clerk_webhook
    def hook(payload=None):
        received.append(payload)
        return flask.jsonify({"status": "SUCCESS"})

    @app.route("/crash", methods=["POST"])
    @verify_clerk_webhook
    def crash(payload=None):
        raise RuntimeError("handler bug with secret detail")

    return app.test_client()


@pytest.mark.parametrize("header", ["svix-id", "svix-timestamp", "svix-signature"])
def test_missing_headers_are_named(client, received, header):  # U-HOOK-1
    body, headers = signed_webhook(PAYLOAD)
    del headers[header]
    response = client.post("/hook", data=body, headers=headers)
    assert response.status_code == 400
    assert header in response.get_json()["err_msg"]
    assert received == []


def test_unconfigured_secret_is_a_server_error(client, received, monkeypatch):  # U-HOOK-2
    body, headers = signed_webhook(PAYLOAD)
    monkeypatch.delitem(secrets, "CLERK_WEBHOOK_SECRET")
    assert client.post("/hook", data=body, headers=headers).status_code == 500
    assert received == []


def test_signature_from_another_secret_is_rejected(client, received):  # U-HOOK-3
    other_secret = "whsec_" + base64.b64encode(b"a-completely-different-secret-!!").decode()
    body, headers = signed_webhook(PAYLOAD, secret=other_secret)
    response = client.post("/hook", data=body, headers=headers)
    assert response.status_code == 400
    assert response.get_json()["err_msg"] == "Invalid webhook signature"
    assert received == []


def test_tampered_body_is_rejected(client, received):  # U-HOOK-3
    body, headers = signed_webhook(PAYLOAD)
    assert client.post("/hook", data=body.replace("user_1", "user_2"), headers=headers).status_code == 400
    assert received == []


def test_stale_timestamp_is_rejected(client, received):  # U-HOOK-3
    ten_minutes_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=10)
    body, headers = signed_webhook(PAYLOAD, timestamp=ten_minutes_ago)
    assert client.post("/hook", data=body, headers=headers).status_code == 400
    assert received == []


def test_valid_webhook_reaches_the_handler_parsed(client, received):  # U-HOOK-4
    body, headers = signed_webhook(PAYLOAD)
    assert client.post("/hook", data=body, headers=headers).status_code == 200
    assert received == [PAYLOAD]


def test_handler_errors_return_a_generic_500(client):  # U-HOOK-5
    body, headers = signed_webhook(PAYLOAD)
    response = client.post("/crash", data=body, headers=headers)
    assert response.status_code == 500
    assert response.get_json()["err_msg"] == "Error processing webhook"
