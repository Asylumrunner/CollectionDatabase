from types import SimpleNamespace

import pytest

import Utilities.AuthenticateRequest as auth

from tests.helpers import item_payload, make_item, signed_webhook

ITEM = item_payload()
REQUIRED_FIELDS = ["title", "media_type", "release_year", "img_link", "original_api_id", "created_by"]
OK_PAGE = {"passed": True, "not_found": False, "items": [], "next_page": None}
OK_LISTS = {"passed": True, "lists": []}
OK = {"passed": True, "not_found": False}

# method, path, body, worker, worker method, worker's success result
ROUTES = [
    ("GET", "/search/dune?media_type=book", None, "SEARCH", "search_item", OK_PAGE),
    ("GET", "/collection", None, "ITEM", "get_user_collection", OK_PAGE),
    ("PUT", "/collection/item", ITEM, "ITEM", "add_item_to_collection", OK),
    ("DELETE", "/collection/item", {"id": 1}, "ITEM", "remove_item_from_collection", OK),
    ("PUT", "/collection/items", [ITEM], "ITEM", "add_items_to_collection", OK),
    ("DELETE", "/collection/items", {"ids": [1]}, "ITEM", "remove_items_from_collection", OK),
    ("GET", "/lists/names", None, "LIST", "get_list_names", OK_LISTS),
    ("PUT", "/lists/3/item", ITEM, "LIST", "add_item_to_list", OK),
    ("GET", "/lists/item/5", None, "LIST", "get_lists_containing_item", OK_LISTS),
    ("DELETE", "/lists/3/item", {"id": 1}, "LIST", "remove_item_from_list", OK),
    ("GET", "/lists/3", None, "LIST", "get_list", OK_PAGE),
    ("PUT", "/lists/3/rename", {"list_name": "x"}, "LIST", "change_list_name", OK),
    ("DELETE", "/lists/3", None, "LIST", "delete_list", OK),
    ("GET", "/lists", None, "LIST", "get_user_lists", OK_LISTS),
    ("POST", "/lists", {"list_name": "x"}, "LIST", "create_list", OK),
]
ROUTE_IDS = [f"{r[0]} {r[1]}" for r in ROUTES]
USER_SCOPED_ROUTES = [r for r in ROUTES if r[3] != "SEARCH"]
USER_SCOPED_IDS = [f"{r[0]} {r[1]}" for r in USER_SCOPED_ROUTES]


def send(client, method, path, body=None):
    return client.open(path, method=method, json=body) if body is not None else client.open(path, method=method)


def stub_success(mock_workers, worker, method, result):
    getattr(mock_workers[worker], method).return_value = result
    # PUT /lists/<id>/item adds the catalog item first
    mock_workers["ITEM"].add_item.return_value = {"passed": True, "Item": SimpleNamespace(id="9")}


def test_create_response_shape(api_module):  # U-API-1
    with api_module.app.app_context():
        response = api_module.create_response(True, 201, 2, ["a"])
        failure = api_module.create_response(False, 400, None, [], "bad")
    assert response.status_code == 201
    assert response.get_json() == {"status": "SUCCESS", "data": ["a"], "err_msg": "", "next_page": 2}
    assert failure.get_json() == {"status": "FAILURE", "data": [], "err_msg": "bad", "next_page": None}


def test_health_check_needs_no_auth(api_module, mock_workers):  # U-API-2
    response = api_module.app.test_client().get("/")
    assert response.status_code == 200
    assert response.get_json()["status"] == "SUCCESS"


@pytest.mark.parametrize("method, path, body, worker, worker_method, ok", ROUTES, ids=ROUTE_IDS)
def test_auth_failure_is_401_and_never_reaches_a_worker(
        api_module, mock_workers, monkeypatch, method, path, body, worker, worker_method, ok):  # U-API-3
    def reject(_request):
        raise RuntimeError("not signed in")
    monkeypatch.setattr(auth, "is_signed_in", reject)
    response = send(api_module.app.test_client(), method, path, body)
    assert response.status_code == 401
    for mock_worker in mock_workers.values():
        assert mock_worker.method_calls == []


@pytest.mark.parametrize("method, path, body, worker, worker_method, ok", USER_SCOPED_ROUTES, ids=USER_SCOPED_IDS)
def test_worker_gets_the_authenticated_user_not_one_from_the_body(
        client, mock_workers, method, path, body, worker, worker_method, ok):  # U-API-4
    stub_success(mock_workers, worker, worker_method, ok)
    if isinstance(body, dict):
        body = {**body, "user_id": "someone_else"}
    assert send(client, method, path, body).status_code == 200
    assert getattr(mock_workers[worker], worker_method).call_args.args[0] == "user_1"


@pytest.mark.parametrize("path", ["/collection/item", "/lists/3/item"])
@pytest.mark.parametrize("missing", REQUIRED_FIELDS)
def test_missing_required_field_is_named(client, path, missing):  # U-API-5
    body = {k: v for k, v in ITEM.items() if k != missing}
    response = client.put(path, json=body)
    assert response.status_code == 400
    assert missing in response.get_json()["err_msg"]


@pytest.mark.parametrize("path", ["/collection/item", "/lists/3/item"])
def test_empty_item_body_is_rejected(client, path):  # U-API-5
    assert client.put(path, json={}).status_code == 400


@pytest.mark.parametrize("body", [[], {"a": 1}, "text"])
def test_bulk_add_needs_a_non_empty_list(client, body):  # U-API-6
    assert client.put("/collection/items", json=body).status_code == 400


def test_bulk_add_names_the_invalid_index(client):  # U-API-6
    bad_item = {k: v for k, v in ITEM.items() if k != "title"}
    response = client.put("/collection/items", json=[ITEM, bad_item])
    assert response.status_code == 400
    assert "index 1" in response.get_json()["err_msg"]
    assert "title" in response.get_json()["err_msg"]


@pytest.mark.parametrize("path, body", [
    ("/collection/item", {}),
    ("/collection/item", {"other": 1}),
    ("/lists/3/item", {"other": 1}),
    ("/collection/items", {}),
    ("/collection/items", {"ids": []}),
    ("/collection/items", {"ids": 5}),
])
def test_delete_routes_validate_their_bodies(client, path, body):  # U-API-7
    assert client.delete(path, json=body).status_code == 400


@pytest.mark.parametrize("method, path", [("POST", "/lists"), ("PUT", "/lists/3/rename")])
def test_list_name_is_required(client, method, path):  # U-API-8
    response = client.open(path, method=method, json={"other": 1})
    assert response.status_code == 400
    assert "list_name" in response.get_json()["err_msg"]


def test_all_item_fields_reach_the_worker(client, mock_workers):  # U-API-9
    mock_workers["ITEM"].add_item_to_collection.return_value = OK
    payload = item_payload(
        id="ignored", isbn="123", printing_year=1990, lang="en", summary="s", duration=9,
        min_players=1, max_players=2, episodes=3, platforms=["PC"], tracklist=["t"], genres=["g"],
    )
    assert client.put("/collection/item", json=payload).status_code == 200
    item = mock_workers["ITEM"].add_item_to_collection.call_args.args[1]
    for field, value in payload.items():
        assert getattr(item, field) == value


def test_absent_optional_fields_are_none(client, mock_workers):  # U-API-9
    mock_workers["ITEM"].add_item_to_collection.return_value = OK
    payload = {field: ITEM[field] for field in REQUIRED_FIELDS}
    assert client.put("/collection/item", json=payload).status_code == 200
    item = mock_workers["ITEM"].add_item_to_collection.call_args.args[1]
    assert item.isbn is None and item.platforms is None and item.genres is None
    assert item.id == ""


@pytest.mark.parametrize("method, path, body, worker, worker_method, ok", ROUTES, ids=ROUTE_IDS)
def test_worker_failure_is_a_500(client, mock_workers, method, path, body, worker, worker_method, ok):  # U-API-10
    stub_success(mock_workers, worker, worker_method, ok)
    getattr(mock_workers[worker], worker_method).return_value = {"passed": False, "exception": "boom"}
    response = send(client, method, path, body)
    assert response.status_code == 500
    assert response.get_json()["status"] == "FAILURE"


def test_catalog_failure_on_add_to_list_is_a_500_and_skips_the_list(client, mock_workers):  # U-API-10
    mock_workers["ITEM"].add_item.return_value = {"passed": False, "exception": "boom"}
    assert client.put("/lists/3/item", json=ITEM).status_code == 500
    mock_workers["LIST"].add_item_to_list.assert_not_called()


@pytest.mark.parametrize("method, path, body, worker_method", [
    ("PUT", "/lists/3/item", ITEM, "add_item_to_list"),
    ("DELETE", "/lists/3/item", {"id": 1}, "remove_item_from_list"),
    ("GET", "/lists/3", None, "get_list"),
    ("DELETE", "/lists/3", None, "delete_list"),
])
def test_not_found_is_a_404(client, mock_workers, method, path, body, worker_method):  # U-API-11
    stub_success(mock_workers, "LIST", worker_method, {"passed": True, "not_found": True})
    assert send(client, method, path, body).status_code == 404


@pytest.mark.parametrize("path", ["/collection?page=abc", "/lists/3?page=abc"])
def test_non_integer_page_is_a_400(client, path):  # U-API-12
    assert client.get(path).status_code == 400


def test_non_integer_list_id_is_a_404(client):  # U-API-12
    assert client.get("/lists/abc").status_code == 404


def test_wrong_method_is_a_405(client):  # U-API-12
    assert client.post("/collection").status_code == 405


@pytest.mark.xfail(reason="B10: page below 1 is not rejected and becomes a negative OFFSET")
@pytest.mark.parametrize("path", ["/collection", "/lists/3"])
@pytest.mark.parametrize("page", [0, -1])
def test_page_below_one_is_a_400(client, mock_workers, path, page):  # U-API-13
    mock_workers["ITEM"].get_user_collection.return_value = OK_PAGE
    mock_workers["LIST"].get_list.return_value = OK_PAGE
    assert client.get(f"{path}?page={page}").status_code == 400


def test_malformed_json_is_a_400(client):  # U-API-14
    response = client.put("/collection/item", data="{not json", content_type="application/json")
    assert response.status_code == 400


def test_wrong_content_type_is_a_415(client):  # U-API-14
    assert client.put("/collection/item", data="x", content_type="text/plain").status_code == 415


@pytest.mark.xfail(reason="non-dict bulk elements are not validated, so the TypeError becomes a 500")
def test_non_dict_bulk_element_is_a_400(client):  # U-API-14
    assert client.put("/collection/items", json=[1]).status_code == 400


@pytest.mark.xfail(reason="B7: created_by is not validated, and a string is iterated per character")
def test_string_created_by_is_a_400(client, mock_workers):  # U-API-15
    mock_workers["ITEM"].add_item_to_collection.return_value = OK
    assert client.put("/collection/item", json=item_payload(created_by="Frank Herbert")).status_code == 400


def test_search_without_media_type_is_a_400(client, mock_workers):  # U-API-16
    assert client.get("/search/dune").status_code == 400
    mock_workers["SEARCH"].search_item.assert_not_called()


@pytest.mark.xfail(reason="B8: create_response arguments are misplaced, so the message lands in data")
def test_search_without_media_type_explains_in_err_msg(client):  # U-API-16
    assert "media_type" in client.get("/search/dune").get_json()["err_msg"]


@pytest.mark.xfail(reason="B8: an unknown media_type is reported as a 500")
def test_search_with_unknown_media_type_is_a_400(client, mock_workers):  # U-API-17
    mock_workers["SEARCH"].search_item.return_value = {"passed": False, "exception": "media_type nope not recognized"}
    assert client.get("/search/dune?media_type=nope").status_code == 400


@pytest.mark.xfail(reason="B8: create_response arguments are misplaced, so the page key lands in data")
def test_search_upstream_failure_has_empty_data(client, mock_workers):  # U-API-17
    mock_workers["SEARCH"].search_item.return_value = {"passed": False, "exception": {"error_type": "X"}}
    response = client.get("/search/dune?media_type=book&page=2")
    assert response.status_code == 500
    assert response.get_json()["data"] == []


def test_search_forwards_filters_and_next_page(client, mock_workers):  # U-API-18
    mock_workers["SEARCH"].search_item.return_value = {"passed": True, "items": [make_item()], "next_page": 3}
    response = client.get("/search/dune?media_type=book&page=2&author=herbert&year=1965")
    mock_workers["SEARCH"].search_item.assert_called_once_with("dune", "book", "2", {"author": "herbert", "year": "1965"})
    body = response.get_json()
    assert response.status_code == 200
    assert body["next_page"] == 3
    assert body["data"][0]["media_type"] == "book"


@pytest.mark.xfail(reason="B4: 500 responses return the worker's traceback and context to the client")
@pytest.mark.parametrize("method, path, body, worker, worker_method, ok", USER_SCOPED_ROUTES, ids=USER_SCOPED_IDS)
def test_500_bodies_do_not_leak_internals(client, mock_workers, method, path, body, worker, worker_method, ok):  # U-API-19
    stub_success(mock_workers, worker, worker_method, ok)
    getattr(mock_workers[worker], worker_method).return_value = {
        "passed": False,
        "step_failed": "fetch",
        "exception": {"traceback": "Traceback (most recent call last)", "context": {"user_id": "user_1"}},
    }
    response = send(client, method, path, body)
    assert response.status_code == 500
    assert "Traceback" not in response.get_data(as_text=True)
    assert "user_1" not in response.get_data(as_text=True)


# Webhook handler. Signatures are real, so these also cover the decorator wiring.

def post_webhook(client, payload):
    body, headers = signed_webhook(payload, msg_id="msg_42")
    return client.post("/webhooks/clerk", data=body, headers=headers)


def created_event(**data):
    return {"type": "user.created", "data": {"id": "clerk_1", **data}}


@pytest.mark.parametrize("data, username", [
    ({"email_addresses": [{"email_address": "a@example.test"}, {"email_address": "b@example.test"}]}, "a@example.test"),
    ({"email_addresses": [], "first_name": "Ada", "last_name": "Lovelace"}, "Ada Lovelace"),
    ({"first_name": "Ada"}, "Ada"),
    ({"email_addresses": [{}]}, "Unknown"),
    ({}, "Unknown"),
])
def test_user_created_chooses_a_username(client, mock_workers, data, username):  # U-API-20
    mock_workers["USER"].create_user.return_value = {"passed": True}
    assert post_webhook(client, created_event(**data)).status_code == 200
    mock_workers["USER"].create_user.assert_called_once_with("clerk_1", username, "msg_42")


@pytest.mark.xfail(reason="B12: .get's default doesn't apply to null values, giving the username 'None None'")
def test_user_created_with_null_names_is_unknown(client, mock_workers):  # U-API-21
    mock_workers["USER"].create_user.return_value = {"passed": True}
    post_webhook(client, created_event(email_addresses=[], first_name=None, last_name=None))
    mock_workers["USER"].create_user.assert_called_once_with("clerk_1", "Unknown", "msg_42")


def test_user_deleted_calls_the_worker(client, mock_workers):  # U-API-22
    mock_workers["USER"].delete_user.return_value = {"passed": True}
    assert post_webhook(client, {"type": "user.deleted", "data": {"id": "clerk_1"}}).status_code == 200
    mock_workers["USER"].delete_user.assert_called_once_with("clerk_1", "msg_42")


def test_other_events_are_ignored(client, mock_workers):  # U-API-22
    assert post_webhook(client, {"type": "session.created", "data": {}}).status_code == 200
    assert mock_workers["USER"].method_calls == []


def test_empty_payload_is_a_400(client):  # U-API-22
    assert post_webhook(client, {}).status_code == 400


@pytest.mark.parametrize("event_type, worker_method", [("user.created", "create_user"), ("user.deleted", "delete_user")])
def test_webhook_worker_failure_is_a_500(client, mock_workers, event_type, worker_method):  # U-API-22
    getattr(mock_workers["USER"], worker_method).return_value = {"passed": False, "exception": "boom"}
    assert post_webhook(client, {"type": event_type, "data": {"id": "clerk_1"}}).status_code == 500
