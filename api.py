import flask
from flask_cors import CORS
from flask import request
from Workers.SearchWorker import SearchWorker
import logging

app = flask.Flask(__name__)
app.config['DEBUG'] = True
CORS(app)

def init():
    workers = {}
    workers['SEARCH'] = SearchWorker()
    return workers

workers = init()

@app.route('/', methods=['GET'])
def health_check():
    return create_response(True, 200, ["Health Check Passed!"])


@app.route('/search/<title>', methods=['GET'])
def lookup_data(title):
    media_type = request.args.get("media_type")
    pagination_key = request.args.get("page", None)
    logging.info(f'media_type provided with search request {media_type}')
    if media_type == None:
        logging.error("No media_type provided with request")
        return create_response(False, 400, [], "No media_type provided with request")

    lookup_response = workers['SEARCH'].search_item(title, media_type, pagination_key)

    if not lookup_response['passed']:
        return create_response(False, 500, [], pagination_key, lookup_response['exception'])
    else:
        return create_response(True, 200, lookup_response['next_page'], lookup_response['items'])

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