import flask
from flask_cors import CORS
from flask import request
from Workers.SearchWorker import SearchWorker
from Workers.DbGetWorker import DbGetWorker
from Workers.DbDeleteWorker import DbDeleteWorker
from Workers.DbPutWorker import DbPutWorker
from Workers.DbUpdateWorker import DbUpdateWorker
from Utilities.ValidateRequestInput import validate_put_request
import logging
import concurrent.futures

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

@app.route('/search/<title>', methods=['GET'])
def lookup_data(title):
    media_type = request.args.get("media_type")
    logging.info(f'media_type provided with search request {media_type}')
    if media_type == None:
        logging.error("No media_type provided with request")
        response = flask.jsonify("No media_type provided")
        response.status_code = 500
        return response
    
    lookup_response = workers['SEARCH'].search_item(title, media_type)

    if('Exception' in lookup_response[0]):
        response = flask.jsonify(lookup_response[0]['Exception'])
        response.status_code = 500
    else:
        response = flask.jsonify(lookup_response)
    return response

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


@app.route('/put', methods=['POST'])
def put_entry(media, key):
    req = request.json
    validation_response = validate_put_request(req)
    if not validation_response['valid']:
        response = flask.jsonify({'status': 'FAILED', 'reason': validation_response['reason']})
        response.status_code = 400
        return response
    
    put_response = workers['PUT'].put_item(req)
    if put_response['status'] = 'FAIL':
        response = flask.jsonify({'status': 'FAILED', 'reason': put_response['exception']})
        response.status_code = 400
    response = {'status': 'SUCCESS'}
    return response

@app.route('/<media>/bulk', methods=['POST'])
def put_entries_bulk(media):
    if media not in controllers:
        response = flask.jsonify('Invalid media type')
        response.status_code = 400
    else:
        request_dict = flask.request.get_json()
        total_inserts = len(request_dict['keys'])
        successful_inserts = 0
        with concurrent.futures.ThreadPoolExecutor() as executor:
            inserts = [executor.submit(controllers[media].put_key, key) for key in request_dict['keys']]
        for insert in concurrent.futures.as_completed(inserts):
            if insert:
                successful_inserts += 1
        response = flask.jsonify("{} out of {} keys successfully submitted".format(successful_inserts, total_inserts))
    return response

@app.route('/item/<key>', methods=['GET'])
def get_entry(key):
    lookup_result = workers['GET'].get_item(key)
    if(lookup_result['status'] != 'FAIL'):
        response = flask.jsonify(lookup_result['item']) if 'item' in lookup_result else {}
    else:
        response = flask.jsonify(lookup_result['error_message'] if 'error_message' in lookup_result else "Get failed")
        response.status_code = 500
    return response

@app.route('/item/<key>', methods=['PUT'])
def update_entry(key):
    

@app.route('/item/<key>', methods=['DELETE'])
def delete_entry(key):
    delete_result = workers['DELETE'].delete_item(key)
    if(delete_result['status'] != 'FAIL'):
        response = flask.jsonify(delete_result['item']) if 'item' in delete_result else {}
    else:
        response = flask.jsonify(delete_result['error_message'] if 'error_message' in delete_result else "Delete failed")
        response.status_code = 500
    return response

@app.route('/collection', methods=['GET'])
def get_every_table():

        
def call_backup(controller):
    return controllers[controller].back_up_table()

@app.route('/backup', methods=['PUT'])
def backup_tables():

def call_restore(controller):
    return controllers[controller].back_up_table()

@app.route('/restore', methods=['PUT'])
def restore_tables():

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