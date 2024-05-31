import flask
from flask_cors import CORS
from flask import request
from Workers.SearchWorker import SearchWorker
from Workers.DbGetWorker import DbGetWorker
from Workers.DbDeleteWorker import DbDeleteWorker
from Workers.DbPutWorker import DbPutWorker
from Workers.DbUpdateWorker import DbUpdateWorker
from Utilities.ValidateRequestInput import validate_put_request, validate_update_request
import logging

app = flask.Flask(__name__)
app.config['DEBUG'] = True
CORS(app)

def init():
    workers = {}
    workers['SEARCH'] = SearchWorker()
    workers['GET'] = DbGetWorker()
    workers['DELETE'] = DbDeleteWorker()
    workers['PUT'] = DbPutWorker()
    workers['UPDATE'] = DbUpdateWorker()
    return workers

workers = init()

@app.route('/', methods=['GET'])
def health_check():
    response = flask.jsonify("We're Good!")
    response.status_code = 200
    return response

@app.route('/search/<title>', methods=['GET'])
def lookup_data(title):
    media_type = request.args.get("media_type")
    logging.info(f'media_type provided with search request {media_type}')
    if media_type == None:
        logging.error("No media_type provided with request")
        return create_response(False, 400, [], "No media_type provided with request")
    
    lookup_response = workers['SEARCH'].search_item(title, media_type)

    if not lookup_response['passed']:
        return create_response(False, 500, [], lookup_response['exception'])
    else:
        return create_response(True, 200, lookup_response['items'])

""" @app.route('/lookup/bulk/<media>', methods=['GET'])
def bulk_lookup_data(media):
    if media not in controllers:
        response = flask.jsonify('Invalid media type')
        response.status_code = 400
    else:
        request_dict = flask.request.get_json()
        if "titles" not in request_dict:
            response = flask.jsonify("No titles found. Please insert titles as list under key \'titles\'")
            response.status_code = 400
        else:
            total_results = []
            picky = "picky" in request_dict and request_dict["picky"]
            with concurrent.futures.ThreadPoolExecutor() as executor:
                lookups = [executor.submit(controllers[media].lookup_entry, title, picky) for title in request_dict['titles']]
            for lookup in concurrent.futures.as_completed(lookups):
                total_results.append(lookup.result())
            response = flask.jsonify(total_results)
    return response """


@app.route('/items', methods=['PUT'])
def put_entry():
    req = request.json
    validation_response = validate_put_request(req)
    if not validation_response['valid']:
        return create_response(False, 400, [], validation_response['reason'])
    
    put_response = workers['PUT'].put_item(req)
    if not put_response['passed']:
        return create_response(False, 500, [], put_response['exception'])
    return create_response(True, 200, put_response['database_response'])

@app.route('/items', methods=['GET'])
def get_table():
    incl_media_types = request.args.getlist("media_type")
    if not incl_media_types:
        return create_response(False, 400, [], "Must include at least one \'media_type\' parameter")
    lookup_response = workers['GET'].get_table(incl_media_types)
    if not lookup_response['passed']:
        return create_response(False, 500, [], lookup_response['exception'])
    return create_response(True, 200, lookup_response['items'])
    
@app.route('/items/<key>', methods=['GET'])
def get_entry(key):
    lookup_response = workers['GET'].get_item(key)
    if not lookup_response['passed']:
        return create_response(False, 500, [], lookup_response['exception'])
    return create_response(True, 200, lookup_response['item'])

@app.route('/items/<key>', methods=['PUT'])
def update_entry(key):
    req = request.json
    if not req:
        return create_response(False, 400, [], "Must include at least one field to update")
    validation_response = validate_update_request(req)
    if not validation_response['valid']:
        return create_response(False, 400, [], validation_response['reason'])
    
    update_response = workers['UPDATE'].update_entry(key, req)
    if not update_response['passed']:
        return create_response(False, 500, [], update_response['exception'])
    return create_response(True, 200, update_response['database_response'])


@app.route('/items/<key>', methods=['DELETE'])
def delete_entry(key):
    delete_response = workers['DELETE'].delete_item(key)
    if not delete_response['passed']:
        return create_response(False, 500, [], delete_response['exception'])
    return create_response(True, 200, delete_response['item'])

def create_response(passed, status_code, data=[], err_msg=''):
    response_object = {
        'status': 'SUCCESS' if passed else 'FAILURE',
        'data': data,
        'err_msg': err_msg
    }
    response = flask.jsonify(response_object)
    response.status_code = status_code
    return response

# def call_backup(controller):
#     return controllers[controller].back_up_table()

# @app.route('/backup', methods=['PUT'])
# def backup_tables():

# def call_restore(controller):
#     return controllers[controller].back_up_table()

# @app.route('/restore', methods=['PUT'])
# def restore_tables():

""" @app.route('/lib-compare/<media>', methods=['GET'])
@app.route('/lib-compare/<media>/<key>', methods=['GET'])
def lookup_in_library(media, key=None):
    if media != 'books':
        response = flask.jsonify('Invalid media type')
        response.status_code(400)
    elif not key:
        table_get_result = controllers[media].get_table()
        if('Items' in table_get_result and 'error_message' not in table_get_result):
            items = table_get_result['Items']
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                lookup_results = [executor.submit(controllers[media].library_compare, key) for key in [item['original_guid'] for item in items]]

            results = {"lookup_results": []}
            for controller_response in concurrent.futures.as_completed(lookup_results):
                results['lookup_results'].append(controller_response.result())
            response = flask.jsonify(results)
        else:
            response = flask.jsonify(lookup_result['error_message'] if 'error_message' in lookup_result else "Lookup failed")
            response.status_code = 500
    else:
        lookup_result = controllers[media].library_compare(key)
        if(lookup_result['status'] != 'FAIL'):
            response = flask.jsonify(lookup_result)
        else:
            response = flask.jsonify(lookup_result['error_message'] if 'error_message' in lookup_result else 'Lookup failed')
            response.status_code = 500
    return response """
"""
@app.route('/<media>')
def clear_table(media) """