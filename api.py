import flask
from flask_cors import CORS
from flask import request
from Workers.SearchWorker import SearchWorker
from Workers.ItemWorker import ItemWorker
from Workers.UserWorker import UserWorker
from DataClasses.item import Item
from Utilities.AuthenticateRequest import authenticated_endpoint
from Utilities.VerifyClerkWebhook import verify_clerk_webhook

import logging

app = flask.Flask(__name__)
app.config['DEBUG'] = True
CORS(app)

def init():
    workers = {}
    workers['SEARCH'] = SearchWorker()
    workers['ITEM'] = ItemWorker()
    workers['USER'] = UserWorker()
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
        return create_response(False, 400, [], "No media_type provided with request")

    # Collect all query params except media_type and page as search filter options
    search_options = {}
    for key, value in request.args.items():
        if key not in ['media_type', 'page']:
            search_options[key] = value

    logging.info(f'Search options collected: {search_options}')

    lookup_response = workers['SEARCH'].search_item(title, media_type, pagination_key, search_options)

    if not lookup_response['passed']:
        return create_response(False, 500, [], pagination_key, lookup_response['exception'])
    else:
        return create_response(True, 200, lookup_response['next_page'], lookup_response['items'])

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
        tracklist=data.get('tracklist'),
        genres=data.get('genres')
    )

    result = workers['ITEM'].add_item_to_collection(user_id, item)

    if not result['passed']:
        return create_response(False, 500, None, [], result)
    else:
        return create_response(True, 200, None, result)


@app.route('/webhooks/clerk', methods=['POST'])
@verify_clerk_webhook
def clerk_webhook(payload=None):
    if not payload:
        return create_response(False, 400, None, [], "No payload provided")

    event_type = payload.get('type')
    data = payload.get('data', {})

    if event_type == 'user.created':
        clerk_user_id = data.get('id')
        email_addresses = data.get('email_addresses', [])
        if email_addresses:
            username = email_addresses[0].get('email_address', 'Unknown')
        else:
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            username = f"{first_name} {last_name}".strip() or 'Unknown'

        result = workers['USER'].create_user(clerk_user_id, username)

        if result['passed']:
            return create_response(True, 200, None, result)
        else:
            return create_response(False, 500, None, [], result)

    elif event_type == 'user.deleted':
        clerk_user_id = data.get('id')

        result = workers['USER'].delete_user(clerk_user_id)

        if result['passed']:
            return create_response(True, 200, None, result)
        else:
            return create_response(False, 500, None, [], result)

    else:
        # Ignore other event types
        logging.info(f"Ignoring unhandled Clerk webhook event: {event_type}")
        return create_response(True, 200, None, {'message': f'Event {event_type} ignored'})


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