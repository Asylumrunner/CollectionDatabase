"""Real signed JWTs through the real Clerk SDK. Only the JWKS download is stubbed, so
signature, expiry and authorized-party checks all run for real."""
import time

import jwt
import pytest
import responses
from clerk_backend_api.security import verifytoken
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from tests.functional_support import load_json_fixture
from tests.helpers import item_payload

KID = "functional-test-key"
AUTHORIZED_PARTY = "http://localhost:8080"

SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)

AUTHENTICATED_ROUTES = [
    ("GET", "/search/dune?media_type=book"),
    ("GET", "/collection"),
    ("PUT", "/collection/item"),
    ("DELETE", "/collection/item"),
    ("PUT", "/collection/items"),
    ("DELETE", "/collection/items"),
    ("GET", "/lists/names"),
    ("PUT", "/lists/3/item"),
    ("GET", "/lists/item/5"),
    ("DELETE", "/lists/3/item"),
    ("GET", "/lists/3"),
    ("PUT", "/lists/3/rename"),
    ("DELETE", "/lists/3"),
    ("GET", "/lists"),
    ("POST", "/lists"),
]


@pytest.fixture(autouse=True)
def stub_jwks(monkeypatch):
    jwk = RSAAlgorithm.to_jwk(SIGNING_KEY.public_key(), as_dict=True)
    monkeypatch.setattr(verifytoken, "_fetch_jwks", lambda options: {"keys": [{**jwk, "kid": KID}]})


def make_token(sub="user_a", key=SIGNING_KEY, **claims):
    now = int(time.time())
    payload = {"sub": sub, "azp": AUTHORIZED_PARTY, "iat": now, "nbf": now, "exp": now + 3600, **claims}
    return jwt.encode(payload, key, algorithm="RS256", headers={"kid": KID})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_valid_token_passes_real_verification(anonymous):  # F-AUTH-1 (no DB needed)
    with responses.RequestsMock() as rsps:
        rsps.get("https://openlibrary.org/search.json", json=load_json_fixture("openlibrary/search.json"))
        response = anonymous.get("/search/dune?media_type=book", headers=bearer(make_token()))
    assert response.status_code == 200


def test_valid_token_is_scoped_to_its_subject(anonymous, client_as, db):  # F-AUTH-1
    db.add_user("user_a")
    client_as("user_a").put("/collection/item", json=item_payload(title="Alice's item"))
    response = anonymous.get("/collection", headers=bearer(make_token("user_a")))
    assert response.status_code == 200
    assert [item["title"] for item in response.get_json()["data"]] == ["Alice's item"]


def test_session_cookie_is_accepted(anonymous, rsps):  # F-AUTH-2
    rsps.get("https://openlibrary.org/search.json", json=load_json_fixture("openlibrary/search.json"))
    anonymous.set_cookie("__session", make_token())
    assert anonymous.get("/search/dune?media_type=book").status_code == 200


@pytest.mark.parametrize("token", [
    pytest.param(lambda: make_token(exp=int(time.time()) - 3600), id="expired"),
    pytest.param(lambda: make_token(nbf=int(time.time()) + 3600), id="not_yet_valid"),
    pytest.param(lambda: make_token(key=OTHER_KEY), id="wrong_key"),
    pytest.param(lambda: "garbage", id="garbage"),
])
def test_bad_tokens_are_rejected(anonymous, token):  # F-AUTH-3
    response = anonymous.get("/collection", headers=bearer(token()))
    assert response.status_code == 401
    assert response.get_json()["data"] == []


@pytest.mark.parametrize("azp", ["https://evil.example.test", None], ids=["other_party", "missing"])
def test_unauthorized_party_is_rejected(anonymous, azp):  # F-AUTH-4
    assert anonymous.get("/collection", headers=bearer(make_token(azp=azp))).status_code == 401


@pytest.mark.parametrize("method, path", AUTHENTICATED_ROUTES)
def test_no_token_is_rejected_on_every_route(anonymous, method, path):  # F-AUTH-5
    assert anonymous.open(path, method=method, json={}).status_code == 401


def test_token_for_one_user_cant_read_anothers_data(anonymous, client_as, db):  # F-AUTH-6
    db.add_user("user_a")
    db.add_user("user_b")
    client_as("user_b").put("/collection/item", json=item_payload(title="Bob's item"))
    response = anonymous.open(
        "/collection", method="GET", headers=bearer(make_token("user_a")), json={"user_id": "user_b"},
    )
    assert response.get_json()["data"] == []


@pytest.mark.xfail(reason="B15: with no token the 401 message is a NoneType AttributeError")
def test_no_token_message_reads_as_an_auth_failure(anonymous):  # F-AUTH-7
    assert "NoneType" not in anonymous.get("/collection").get_json()["err_msg"]


def test_valid_token_with_malformed_json_is_a_400(anonymous):  # F-AUTH-8
    response = anonymous.put(
        "/collection/item", data="{not json", content_type="application/json", headers=bearer(make_token()),
    )
    assert response.status_code == 400


@pytest.mark.xfail(reason="B5: any non-empty SKIP_AUTH disables authentication")
def test_skip_auth_false_still_requires_a_token(anonymous, monkeypatch):  # F-AUTH-9
    monkeypatch.setenv("SKIP_AUTH", "false")
    assert anonymous.get("/collection").status_code == 401
