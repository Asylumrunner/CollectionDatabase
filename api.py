import flask
import time
import uuid
from flask_cors import CORS
from flask import request
from flask import g
from Workers.SearchWorker import SearchWorker
from Workers.ItemWorker import ItemWorker
from Workers.UserWorker import UserWorker
from Workers.ListWorker import ListWorker
from Utilities.AuthenticateRequest import authenticated_endpoint
from Utilities.VerifyClerkWebhook import verify_clerk_webhook
from Utilities.ExceptionStack import exception_stack
from Utilities.RequestParsing import missing_item_fields, item_from_payload, parse_page
from Utilities.Responses import create_response, public_error_message, worker_failure, respond, respond_with_page
from Utilities.LoggingSetup import configure_logging
from werkzeug.exceptions import HTTPException

import logging

configure_logging()

app = flask.Flask(__name__)
# Browsers hide non-standard response headers from cross-origin JavaScript unless they're exposed,
# so the frontend can only read Request-Id (to report it with an error) if it's listed here
CORS(app, expose_headers=["Request-Id"])

def init():
    workers = {}
    workers['SEARCH'] = SearchWorker()
    workers['ITEM'] = ItemWorker()
    workers['USER'] = UserWorker()
    workers['LIST'] = ListWorker()
    return workers

workers = init()

######################################
##### REQUEST-WRAPPING FUNCTIONS #####
######################################


@app.before_request
def generate_request_id():
    g.request_id = uuid.uuid4().hex[:16]
    g.request_start = time.perf_counter()

@app.after_request
def log_and_tag_response(response):
    # Also runs for unhandled exceptions, once Flask has turned them into a 500 response
    response.headers['Request-Id'] = g.get("request_id", "-")
    start = g.get("request_start")
    duration_ms = f"{(time.perf_counter() - start) * 1000:.0f}" if start is not None else "-"
    # The route template (/lists/<int:list_id>) rather than the path, so requests group by route.
    # There's no rule when nothing matched, as for a 404
    route = request.url_rule.rule if request.url_rule else None
    logging.info(f"Request finished: method={request.method} route={route} status={response.status_code} duration_ms={duration_ms}")
    return response

@app.errorhandler(Exception)
def handle_unexpected_exception(e):
    # Without this, Flask's default handling logs the full exception message, which can echo row values
    # or other user data. In debug mode (FLASK_DEBUG=1, as the VS Code launch config sets) it also
    # re-raises to the server instead of building a 500, skipping the summary line and the request ID.
    # This logs only the error type and code locations, and keeps the traceback out of the response body
    if isinstance(e, HTTPException):
        # 404s, 405s and the like are already proper responses
        return e
    logging.error(f"Unhandled exception: route={request.url_rule.rule if request.url_rule else None} error_type={type(e).__name__} stack={exception_stack(e)}")
    return create_response(False, 500, None, [], "Internal server error")


######################################
######## STANDALONE ENDPOINTS ########
######################################


@app.route('/', methods=['GET'])
def health_check():
    return create_response(True, 200, ["Health Check Passed!"])

@app.route('/search/<title>', methods=['GET'])
@authenticated_endpoint
def search_for_item(title, user_id=None):
    media_type = request.args.get("media_type")
    pagination_key = request.args.get("page", None)
    if media_type == None:
        logging.error("No media_type provided with request")
        return create_response(False, 400, None, [], "No media_type provided with request")
    if media_type not in SearchWorker.MEDIA_TYPES:
        logging.error(f"Unrecognized media_type provided with request: {media_type}")
        return create_response(False, 400, None, [], f"media_type must be one of [{', '.join(SearchWorker.MEDIA_TYPES)}]")

    # Collect all query params except media_type and page as search filter options
    search_options = {}
    for key, value in request.args.items():
        if key not in ['media_type', 'page']:
            search_options[key] = value

    lookup_response = workers['SEARCH'].search_item(title, media_type, pagination_key, search_options)

    if not lookup_response['passed']:
        return worker_failure(lookup_response)
    else:
        return create_response(True, 200, lookup_response['next_page'], lookup_response['items'])
    

######################################
######## COLLECTION ENDPOINTS ########
######################################


@app.route('/collection', methods=['GET'])
@authenticated_endpoint
def get_collection(user_id=None):
    page = parse_page(request.args)
    if page is None:
        return create_response(False, 400, None, [], "page must be an integer")

    return respond_with_page(workers['ITEM'].get_user_collection(user_id, page))


@app.route('/collection/item', methods=['PUT'])
@authenticated_endpoint
def add_item_to_collection(user_id=None):
    data = request.get_json()
    if not data:
        return create_response(False, 400, None, [], "No JSON body provided")

    missing_fields = missing_item_fields(data)
    if missing_fields:
        return create_response(False, 400, None, [], f"Missing required fields: {', '.join(missing_fields)}")

    item = item_from_payload(data)

    result = workers['ITEM'].add_item_to_collection(user_id, item)
    return respond(result)


@app.route('/collection/items', methods=['PUT'])
@authenticated_endpoint
def add_items_to_collection(user_id=None):
    data = request.get_json()
    if not data or not isinstance(data, list) or len(data) == 0:
        return create_response(False, 400, None, [], "Request body must be a non-empty list of items")

    items = []
    for i, item_data in enumerate(data):
        missing_fields = missing_item_fields(item_data)
        if missing_fields:
            return create_response(False, 400, None, [], f"Item at index {i} missing required fields: {', '.join(missing_fields)}")
        items.append(item_from_payload(item_data))

    result = workers['ITEM'].add_items_to_collection(user_id, items)

    if not result['passed']:
        return worker_failure(result)
    # Per-item failures carry full failure objects; only send the client a summary of each
    for failure in result.get('failed', []):
        failure['error'] = public_error_message(failure['error'])
    return create_response(True, 200, None, result)


@app.route('/collection/item', methods=['DELETE'])
@authenticated_endpoint
def remove_item_from_collection(user_id=None):
    data = request.get_json()
    if not data or 'id' not in data:
        return create_response(False, 400, None, [], "Missing required field: id")

    result = workers['ITEM'].remove_item_from_collection(user_id, data['id'])
    return respond(result)


@app.route('/collection/items', methods=['DELETE'])
@authenticated_endpoint
def remove_items_from_collection(user_id=None):
    data = request.get_json()
    if not data or 'ids' not in data or not isinstance(data['ids'], list) or len(data['ids']) == 0:
        return create_response(False, 400, None, [], "Request body must contain a non-empty 'ids' list")

    result = workers['ITEM'].remove_items_from_collection(user_id, data['ids'])
    return respond(result)


################################
######## LIST ENDPOINTS ########
################################


@app.route('/lists', methods=['POST'])
@authenticated_endpoint
def create_list(user_id=None):
    data = request.get_json()
    if not data or 'list_name' not in data:
        return create_response(False, 400, None, [], "Missing required field: list_name")

    result = workers['LIST'].create_list(user_id, data['list_name'])
    return respond(result)


@app.route('/lists/<int:list_id>', methods=['GET'])
@authenticated_endpoint
def get_list(list_id, user_id=None):
    page = parse_page(request.args)
    if page is None:
        return create_response(False, 400, None, [], "page must be an integer")

    result = workers['LIST'].get_list(user_id, list_id, page)
    return respond_with_page(result, not_found_msg="List not found")


@app.route('/lists', methods=['GET'])
@authenticated_endpoint
def get_all_lists(user_id=None):
    result = workers['LIST'].get_user_lists(user_id)
    return respond(result, key='lists')


@app.route('/lists/item/<int:item_id>', methods=['GET'])
@authenticated_endpoint
def get_lists_containing_item(item_id, user_id=None):
    result = workers['LIST'].get_lists_containing_item(user_id, item_id)
    return respond(result, key='lists')


@app.route('/lists/names', methods=['GET'])
@authenticated_endpoint
def get_list_names(user_id=None):
    result = workers['LIST'].get_list_names(user_id)
    return respond(result, key='lists')


@app.route('/lists/<int:list_id>/item', methods=['PUT'])
@authenticated_endpoint
def add_item_to_list(list_id, user_id=None):
    data = request.get_json()
    if not data:
        return create_response(False, 400, None, [], "No JSON body provided")

    missing_fields = missing_item_fields(data)
    if missing_fields:
        return create_response(False, 400, None, [], f"Missing required fields: {', '.join(missing_fields)}")

    item = item_from_payload(data)

    add_item_result = workers['ITEM'].add_item(item)
    if not add_item_result['passed']:
        return worker_failure(add_item_result)

    item_id = add_item_result['Item'].id

    list_result = workers['LIST'].add_item_to_list(user_id, list_id, item_id)
    return respond(list_result, not_found_msg="List not found")


@app.route('/lists/<int:list_id>/item', methods=['DELETE'])
@authenticated_endpoint
def remove_item_from_list(list_id, user_id=None):
    data = request.get_json()
    if not data or 'id' not in data:
        return create_response(False, 400, None, [], "Missing required field: id")

    list_result = workers['LIST'].remove_item_from_list(user_id, list_id, data['id'])
    return respond(list_result, not_found_msg="List not found")


@app.route('/lists/<int:list_id>/rename', methods=['PUT'])
@authenticated_endpoint
def rename_list(list_id, user_id=None):
    data = request.get_json()
    if not data or 'list_name' not in data:
        return create_response(False, 400, None, [], "Missing required field: list_name")

    result = workers['LIST'].change_list_name(user_id, list_id, data['list_name'])
    return respond(result, not_found_msg="List not found")


@app.route('/lists/<int:list_id>', methods=['DELETE'])
@authenticated_endpoint
def delete_list(list_id, user_id=None):
    result = workers['LIST'].delete_list(user_id, list_id)

    if not result['passed']:
        return worker_failure(result)
    if result['not_found']:
        return create_response(False, 404, None, [], "List not found")
    return create_response(True, 200, None, [])


################################
########### WEBHOOKS ###########
################################


@app.route('/webhooks/clerk', methods=['POST'])
@verify_clerk_webhook
def clerk_webhook(payload=None):
    if not payload:
        return create_response(False, 400, None, [], "No payload provided")

    event_type = payload.get('type')
    data = payload.get('data', {})
    # Svix message ID; stable across retries and not tied to the user's identity
    webhook_id = request.headers.get('svix-id')

    if event_type == 'user.created':
        clerk_user_id = data.get('id')
        email_addresses = data.get('email_addresses', [])
        if email_addresses:
            username = email_addresses[0].get('email_address', 'Unknown')
        else:
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            username = f"{first_name} {last_name}".strip() or 'Unknown'

        return respond(workers['USER'].create_user(clerk_user_id, username, webhook_id))

    elif event_type == 'user.deleted':
        clerk_user_id = data.get('id')
        return respond(workers['USER'].delete_user(clerk_user_id, webhook_id))

    else:
        # Ignore other event types
        logging.info(f"Ignoring unhandled Clerk webhook event: {event_type}")
        return create_response(True, 200, None, {'message': f'Event {event_type} ignored'})


if __name__ == "__main__":
    app.run(host='0.0.0.0')