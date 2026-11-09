import flask
from flask_cors import CORS
from flask import request
from Workers.SearchWorker import SearchWorker
from Workers.ItemWorker import ItemWorker
from Workers.UserWorker import UserWorker
from Workers.ListWorker import ListWorker
from DataClasses.item import Item
from Utilities.AuthenticateRequest import authenticated_endpoint
from Utilities.VerifyClerkWebhook import verify_clerk_webhook
from dataclasses import asdict

import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

app = flask.Flask(__name__)
app.config['DEBUG'] = True
CORS(app)

def init():
    workers = {}
    workers['SEARCH'] = SearchWorker()
    workers['ITEM'] = ItemWorker()
    workers['USER'] = UserWorker()
    workers['LIST'] = ListWorker()
    return workers

workers = init()

@app.route('/', methods=['GET'])
def health_check():
    return create_response(True, 200, ["Health Check Passed!"])


@app.route('/search/<title>', methods=['GET'])
@authenticated_endpoint
def lookup_data(title, user_id=None):
    media_type = request.args.get("media_type")
    pagination_key = request.args.get("page", None)
    logging.info(f'media_type provided with search request {media_type}')
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

    logging.info(f'Search options collected: {search_options}')

    lookup_response = workers['SEARCH'].search_item(title, media_type, pagination_key, search_options)

    if not lookup_response['passed']:
        return worker_failure(lookup_response)
    else:
        return create_response(True, 200, lookup_response['next_page'], lookup_response['items'])

@app.route('/collection', methods=['GET'])
@authenticated_endpoint
def get_collection(user_id=None):
    try:
        logging.info("Collecting user collection")
        page = int(request.args.get('page', 1))
    except ValueError:
        return create_response(False, 400, None, [], "page must be an integer")

    result = workers['ITEM'].get_user_collection(user_id, page)

    if not result['passed']:
        return worker_failure(result)

    return create_response(True, 200, result['next_page'], [asdict(item) for item in result['items']])


@app.route('/collection/item', methods=['PUT'])
@authenticated_endpoint
def add_item_to_collection(user_id=None):
    data = request.get_json()
    if not data:
        return create_response(False, 400, None, [], "No JSON body provided")

    required_fields = ['title', 'media_type', 'release_year', 'img_link', 'original_api_id', 'created_by']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return create_response(False, 400, None, [], f"Missing required fields: {', '.join(missing_fields)}")

    item = Item(
        id=data.get('id', ''),
        title=data['title'],
        media_type=data['media_type'],
        release_year=data['release_year'],
        img_link=data['img_link'],
        original_api_id=data['original_api_id'],
        created_by=data['created_by'],
        isbn=data.get('isbn'),
        printing_year=data.get('printing_year'),
        lang=data.get('lang'),
        summary=data.get('summary'),
        duration=data.get('duration'),
        min_players=data.get('min_players'),
        max_players=data.get('max_players'),
        episodes=data.get('episodes'),
        platforms=data.get('platforms'),
        platform_igdb_ids=data.get('platform_igdb_ids'),
        tracklist=data.get('tracklist'),
        genres=data.get('genres')
    )

    result = workers['ITEM'].add_item_to_collection(user_id, item)

    if not result['passed']:
        return worker_failure(result)
    else:
        return create_response(True, 200, None, result)


@app.route('/collection/item', methods=['DELETE'])
@authenticated_endpoint
def remove_item_from_collection(user_id=None):
    data = request.get_json()
    if not data or 'id' not in data:
        return create_response(False, 400, None, [], "Missing required field: id")

    result = workers['ITEM'].remove_item_from_collection(user_id, data['id'])

    if not result['passed']:
        return worker_failure(result)
    else:
        return create_response(True, 200, None, result)


@app.route('/collection/items', methods=['PUT'])
@authenticated_endpoint
def add_items_to_collection(user_id=None):
    data = request.get_json()
    if not data or not isinstance(data, list) or len(data) == 0:
        return create_response(False, 400, None, [], "Request body must be a non-empty list of items")

    required_fields = ['title', 'media_type', 'release_year', 'img_link', 'original_api_id', 'created_by']
    items = []
    for i, item_data in enumerate(data):
        missing_fields = [field for field in required_fields if field not in item_data]
        if missing_fields:
            return create_response(False, 400, None, [], f"Item at index {i} missing required fields: {', '.join(missing_fields)}")
        items.append(Item(
            id=item_data.get('id', ''),
            title=item_data['title'],
            media_type=item_data['media_type'],
            release_year=item_data['release_year'],
            img_link=item_data['img_link'],
            original_api_id=item_data['original_api_id'],
            created_by=item_data['created_by'],
            isbn=item_data.get('isbn'),
            printing_year=item_data.get('printing_year'),
            lang=item_data.get('lang'),
            summary=item_data.get('summary'),
            duration=item_data.get('duration'),
            min_players=item_data.get('min_players'),
            max_players=item_data.get('max_players'),
            episodes=item_data.get('episodes'),
            platforms=item_data.get('platforms'),
            platform_igdb_ids=item_data.get('platform_igdb_ids'),
            tracklist=item_data.get('tracklist'),
            genres=item_data.get('genres')
        ))

    result = workers['ITEM'].add_items_to_collection(user_id, items)

    if not result['passed']:
        return worker_failure(result)
    # Per-item failures carry full failure objects; only send the client a summary of each
    for failure in result.get('failed', []):
        failure['error'] = public_error_message(failure['error'])
    return create_response(True, 200, None, result)


@app.route('/collection/items', methods=['DELETE'])
@authenticated_endpoint
def remove_items_from_collection(user_id=None):
    data = request.get_json()
    if not data or 'ids' not in data or not isinstance(data['ids'], list) or len(data['ids']) == 0:
        return create_response(False, 400, None, [], "Request body must contain a non-empty 'ids' list")

    result = workers['ITEM'].remove_items_from_collection(user_id, data['ids'])

    if not result['passed']:
        return worker_failure(result)
    return create_response(True, 200, None, result)


@app.route('/lists/names', methods=['GET'])
@authenticated_endpoint
def get_list_names(user_id=None):
    result = workers['LIST'].get_list_names(user_id)

    if not result['passed']:
        return worker_failure(result)
    return create_response(True, 200, None, result['lists'])


@app.route('/lists/<int:list_id>/item', methods=['PUT'])
@authenticated_endpoint
def add_item_to_list(list_id, user_id=None):
    data = request.get_json()
    if not data:
        return create_response(False, 400, None, [], "No JSON body provided")

    required_fields = ['title', 'media_type', 'release_year', 'img_link', 'original_api_id', 'created_by']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return create_response(False, 400, None, [], f"Missing required fields: {', '.join(missing_fields)}")

    item = Item(
        id=data.get('id', ''),
        title=data['title'],
        media_type=data['media_type'],
        release_year=data['release_year'],
        img_link=data['img_link'],
        original_api_id=data['original_api_id'],
        created_by=data['created_by'],
        isbn=data.get('isbn'),
        printing_year=data.get('printing_year'),
        lang=data.get('lang'),
        summary=data.get('summary'),
        duration=data.get('duration'),
        min_players=data.get('min_players'),
        max_players=data.get('max_players'),
        episodes=data.get('episodes'),
        platforms=data.get('platforms'),
        platform_igdb_ids=data.get('platform_igdb_ids'),
        tracklist=data.get('tracklist'),
        genres=data.get('genres')
    )

    add_item_result = workers['ITEM'].add_item(item)
    if not add_item_result['passed']:
        return worker_failure(add_item_result)

    item_id = add_item_result['Item'].id

    list_result = workers['LIST'].add_item_to_list(user_id, list_id, item_id)
    if not list_result['passed']:
        return worker_failure(list_result)
    if list_result['not_found']:
        return create_response(False, 404, None, [], "List not found")
    return create_response(True, 200, None, list_result)


@app.route('/lists/item/<int:item_id>', methods=['GET'])
@authenticated_endpoint
def get_lists_containing_item(item_id, user_id=None):
    result = workers['LIST'].get_lists_containing_item(user_id, item_id)

    if not result['passed']:
        return worker_failure(result)
    return create_response(True, 200, None, result['lists'])


@app.route('/lists/<int:list_id>/item', methods=['DELETE'])
@authenticated_endpoint
def remove_item_from_list(list_id, user_id=None):
    data = request.get_json()
    if not data or 'id' not in data:
        return create_response(False, 400, None, [], "Missing required field: id")

    list_result = workers['LIST'].remove_item_from_list(user_id, list_id, data['id'])
    if not list_result['passed']:
        return worker_failure(list_result)
    if list_result['not_found']:
        return create_response(False, 404, None, [], "List not found")
    return create_response(True, 200, None, list_result)


@app.route('/lists/<int:list_id>', methods=['GET'])
@authenticated_endpoint
def get_list(list_id, user_id=None):
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        return create_response(False, 400, None, [], "page must be an integer")

    result = workers['LIST'].get_list(user_id, list_id, page)

    if not result['passed']:
        return worker_failure(result)
    if result['not_found']:
        return create_response(False, 404, None, [], "List not found")
    return create_response(True, 200, result['next_page'], [asdict(item) for item in result['items']])

@app.route('/lists/<int:list_id>/rename', methods=['PUT'])
@authenticated_endpoint
def rename_list(list_id, user_id=None):
    data = request.get_json()
    if not data or 'list_name' not in data:
        return create_response(False, 400, None, [], "Missing required field: list_name")

    result = workers['LIST'].change_list_name(user_id, list_id, data['list_name'])

    if not result['passed']:
        return worker_failure(result)
    if result['not_found']:
        return create_response(False, 404, None, [], "List not found")
    return create_response(True, 200, None, result)



@app.route('/lists/<int:list_id>', methods=['DELETE'])
@authenticated_endpoint
def delete_list(list_id, user_id=None):
    result = workers['LIST'].delete_list(user_id, list_id)

    if not result['passed']:
        return worker_failure(result)
    if result['not_found']:
        return create_response(False, 404, None, [], "List not found")
    return create_response(True, 200, None, [])


@app.route('/lists', methods=['GET'])
@authenticated_endpoint
def get_user_lists(user_id=None):
    result = workers['LIST'].get_user_lists(user_id)

    if not result['passed']:
        return worker_failure(result)
    return create_response(True, 200, None, result['lists'])


@app.route('/lists', methods=['POST'])
@authenticated_endpoint
def create_list(user_id=None):
    data = request.get_json()
    if not data or 'list_name' not in data:
        return create_response(False, 400, None, [], "Missing required field: list_name")

    result = workers['LIST'].create_list(user_id, data['list_name'])

    if not result['passed']:
        return worker_failure(result)
    return create_response(True, 200, None, result)


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

        result = workers['USER'].create_user(clerk_user_id, username, webhook_id)

        if result['passed']:
            return create_response(True, 200, None, result)
        else:
            return worker_failure(result)

    elif event_type == 'user.deleted':
        clerk_user_id = data.get('id')

        result = workers['USER'].delete_user(clerk_user_id, webhook_id)

        if result['passed']:
            return create_response(True, 200, None, result)
        else:
            return worker_failure(result)

    else:
        # Ignore other event types
        logging.info(f"Ignoring unhandled Clerk webhook event: {event_type}")
        return create_response(True, 200, None, {'message': f'Event {event_type} ignored'})


def public_error_message(failure):
    # Worker failure objects hold tracebacks and call arguments (including user IDs), which stay
    # in the server logs. Clients only get the step that failed.
    step = failure.get('step_failed') if isinstance(failure, dict) else None
    return f"Internal server error at step '{step}'" if step else "Internal server error"


def worker_failure(failure):
    return create_response(False, 500, None, [], public_error_message(failure))


def create_response(passed, status_code, page, data=[], err_msg=''):
    response_object = {
        'status': 'SUCCESS' if passed else 'FAILURE',
        'data': data,
        'err_msg': err_msg,
        'next_page': page
    }
    response = flask.jsonify(response_object)
    response.status_code = status_code
    return response

if __name__ == "__main__":
    app.run(host='0.0.0.0')